//! Fixed-point value noise, equal to `rnw.noise` and `rnw.fields` (the references).
//!
//! All arithmetic is `i64`. Divisions floor (`div_euclid` with a positive divisor), as
//! NumPy's `//` does; nothing here can overflow for the sizes the generator uses, and the
//! tests check the limits.

use crate::hash::{GAMMA, hash_point, mix64};
use rayon::prelude::*;

pub const UNIT: i64 = 256;
pub const NOISE_SCALE: i64 = 1 << 15;
const PERMILLE: i64 = 1000;
const SUBPIXEL: i64 = 16;
const ANGLE_SCALE: i64 = 1024;
/// (cos, sin) * 1024 of the lattice rotation per octave.
const ROTATIONS: [(i64, i64); 6] = [
    (-755, 692),
    (90, -1020),
    (623, 813),
    (-1008, -178),
    (864, -550),
    (-266, 989),
];

#[inline]
fn smooth(t: i64) -> i64 {
    (t * t * (3 * UNIT - 2 * t)).div_euclid(UNIT * UNIT)
}

#[inline]
fn lattice_value(key: u64, x: i64, y: i64) -> i64 {
    (hash_point(key, x, y) >> 48) as i64 - NOISE_SCALE
}

#[inline]
fn blend(v00: i64, v10: i64, v01: i64, v11: i64, sx: i64, sy: i64) -> i64 {
    let top = v00 * UNIT + (v10 - v00) * sx;
    let bottom = v01 * UNIT + (v11 - v01) * sx;
    (top * UNIT + (bottom - top) * sy).div_euclid(UNIT * UNIT)
}

/// The key of octave `octave` of a fractal field.
pub fn octave_key(key: u64, octave: u32) -> u64 {
    mix64(key.wrapping_add(u64::from(octave).wrapping_mul(GAMMA)))
}

/// Per-octave lookup tables of one window: cell and smoothed fraction per column and the
/// lattice values around the window.
struct Octave {
    amplitude: i64,
    period: i64,
    y0: i64,
    first_row: i64,
    columns: usize,
    cell: Vec<u32>,
    fraction: Vec<i64>,
    lattice: Vec<i64>,
}

impl Octave {
    fn new(
        key: u64,
        x0: i64,
        y0: i64,
        width: usize,
        height: usize,
        period: i64,
        amplitude: i64,
    ) -> Self {
        let first_column = x0 / period;
        let last_column = (x0 + width as i64 - 1) / period;
        let first_row = y0 / period;
        let last_row = (y0 + height as i64 - 1) / period;
        let columns = (last_column - first_column + 2) as usize;
        let rows = (last_row - first_row + 2) as usize;
        let mut cell = Vec::with_capacity(width);
        let mut fraction = Vec::with_capacity(width);
        for x in x0..x0 + width as i64 {
            let index = x / period;
            cell.push((index - first_column) as u32);
            fraction.push(smooth((x - index * period) * UNIT / period));
        }
        let lattice: Vec<i64> = (0..rows * columns)
            .map(|at| {
                let (j, i) = (at / columns, at % columns);
                lattice_value(key, first_column + i as i64, first_row + j as i64)
            })
            .collect();
        Self {
            amplitude,
            period,
            y0,
            first_row,
            columns,
            cell,
            fraction,
            lattice,
        }
    }

    /// Add this octave's noise of window row `row` to `total`.
    fn add_row(&self, row: usize, total: &mut [i64]) {
        let y = self.y0 + row as i64;
        let index = y / self.period;
        let sy = smooth((y - index * self.period) * UNIT / self.period);
        let top = (index - self.first_row) as usize * self.columns;
        let upper = &self.lattice[top..top + self.columns];
        let lower = &self.lattice[top + self.columns..top + 2 * self.columns];
        for (x, slot) in total.iter_mut().enumerate() {
            let at = self.cell[x] as usize;
            let value = blend(
                upper[at],
                upper[at + 1],
                lower[at],
                lower[at + 1],
                self.fraction[x],
                sy,
            );
            *slot += self.amplitude * value;
        }
    }
}

/// Fractal noise of a window of the world: octaves of halving period summed with
/// geometric amplitudes and divided by their total weight. One octave with amplitude one
/// is plain value noise.
pub fn fractal_window(
    key: u64,
    (x0, y0): (i64, i64),
    (width, height): (usize, usize),
    period: i64,
    octaves: u32,
    persistence_permille: i64,
) -> Vec<i64> {
    let mut stack = Vec::new();
    let mut amplitude = PERMILLE;
    let mut weight = 0;
    for octave in 0..octaves {
        let octave_period = 2.max(period >> octave);
        stack.push(Octave::new(
            octave_key(key, octave),
            x0,
            y0,
            width,
            height,
            octave_period,
            amplitude,
        ));
        weight += amplitude;
        amplitude = 1.max(amplitude * persistence_permille / PERMILLE);
    }
    let weight = 1.max(weight);
    let mut out = vec![0_i64; width * height];
    out.par_chunks_mut(width)
        .enumerate()
        .for_each(|(row, line)| {
            for octave in &stack {
                octave.add_row(row, line);
            }
            for value in line.iter_mut() {
                *value = value.div_euclid(weight);
            }
        });
    out
}

/// One octave of value noise (no key mixing, no amplitude).
pub fn value_window(key: u64, origin: (i64, i64), size: (usize, usize), period: i64) -> Vec<i64> {
    let octave = Octave::new(key, origin.0, origin.1, size.0, size.1, period, 1);
    let mut out = vec![0_i64; size.0 * size.1];
    out.par_chunks_mut(size.0)
        .enumerate()
        .for_each(|(row, line)| octave.add_row(row, line));
    out
}

#[inline]
fn value_at(key: u64, x: i64, y: i64, period: i64) -> i64 {
    let (ix, iy) = (x.div_euclid(period), y.div_euclid(period));
    let sx = smooth((x - ix * period) * UNIT / period);
    let sy = smooth((y - iy * period) * UNIT / period);
    blend(
        lattice_value(key, ix, iy),
        lattice_value(key, ix + 1, iy),
        lattice_value(key, ix, iy + 1),
        lattice_value(key, ix + 1, iy + 1),
        sx,
        sy,
    )
}

/// Rotated-lattice fractal noise at sub-pixel coordinates (units of 1/16 pixel).
pub fn fractal_at(
    key: u64,
    xs: &[i64],
    ys: &[i64],
    period: i64,
    octaves: u32,
    persistence_permille: i64,
) -> Vec<i64> {
    let mut plan = Vec::new();
    let mut amplitude = PERMILLE;
    let mut weight = 0;
    for octave in 0..octaves {
        let (cos, sin) = ROTATIONS[octave as usize % ROTATIONS.len()];
        let octave_period = 2.max(period >> octave) * SUBPIXEL;
        plan.push((cos, sin, octave_key(key, octave), octave_period, amplitude));
        weight += amplitude;
        amplitude = 1.max(amplitude * persistence_permille / PERMILLE);
    }
    let weight = 1.max(weight);
    xs.par_iter()
        .zip(ys.par_iter())
        .map(|(&x, &y)| {
            let mut total = 0_i64;
            for &(cos, sin, key, octave_period, amplitude) in &plan {
                let rx = (x * cos - y * sin).div_euclid(ANGLE_SCALE);
                let ry = (x * sin + y * cos).div_euclid(ANGLE_SCALE);
                total += amplitude * value_at(key, rx, ry, octave_period);
            }
            total.div_euclid(weight)
        })
        .collect()
}

/// Value noise at arbitrary integer coordinates.
pub fn value_noise_at(key: u64, xs: &[i64], ys: &[i64], period: i64) -> Vec<i64> {
    xs.par_iter()
        .zip(ys.par_iter())
        .map(|(&x, &y)| value_at(key, x, y, period))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_window_equals_the_same_pixels_of_a_larger_one() {
        let big = fractal_window(99, (0, 0), (40, 30), 8, 3, 500);
        let small = fractal_window(99, (7, 5), (10, 9), 8, 3, 500);
        for y in 0..9 {
            for x in 0..10 {
                assert_eq!(small[y * 10 + x], big[(y + 5) * 40 + x + 7]);
            }
        }
    }

    #[test]
    fn one_octave_of_fractal_noise_is_value_noise() {
        let single = fractal_window(octave_key(5, 0), (3, 4), (12, 7), 6, 1, 500);
        assert_eq!(
            single,
            value_window(octave_key(octave_key(5, 0), 0), (3, 4), (12, 7), 6)
        );
    }

    #[test]
    fn point_noise_agrees_with_window_noise() {
        let window = value_window(7, (0, 0), (20, 10), 5);
        let xs: Vec<i64> = (0..20).collect();
        for y in 0..10 {
            let ys = vec![y; 20];
            assert_eq!(
                value_noise_at(7, &xs, &ys, 5),
                &window[(y as usize) * 20..][..20]
            );
        }
    }
}
