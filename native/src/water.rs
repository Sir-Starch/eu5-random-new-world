//! Integer-exact water colour calibration and rendering in bounded strips.
use crate::noise::{NOISE_SCALE, fractal_window};
use rayon::prelude::*;

const GRID: usize = 32;
const BAND: usize = 64;
const BLUR: usize = 2;
const BLEND: i64 = 16;

fn background(grid: &[i64], shape: (usize, usize), y: usize, x: usize, channel: usize) -> i64 {
    let span = (2 * GRID) as i64;
    let py = 2 * y as i64 + 1 - GRID as i64;
    let px = 2 * x as i64 + 1 - GRID as i64;
    let row = py.div_euclid(span);
    let column = px.div_euclid(span);
    let fy = py.rem_euclid(span);
    let fx = px.rem_euclid(span);
    let at = |r: i64, c: i64| {
        grid[(r.clamp(0, shape.0 as i64 - 1) as usize * shape.1
            + c.rem_euclid(shape.1 as i64) as usize)
            * 4
            + channel]
    };
    let left = at(row, column) * (span - fy) + at(row + 1, column) * fy;
    let right = at(row, column + 1) * (span - fy) + at(row + 1, column + 1) * fy;
    (left * (span - fx) + right * fx + span * span / 2).div_euclid(span * span)
}

pub fn open_cells(
    image: &[u8],
    distance: &[u8],
    width: usize,
    reach: u8,
    first: usize,
    last: usize,
) -> Vec<i64> {
    let columns = width.div_ceil(GRID);
    let mut out = vec![0; (last.div_ceil(GRID) - first / GRID) * columns * 5];
    for y in first..last {
        for x in 0..width {
            let pixel = y * width + x;
            if distance[pixel] < reach {
                continue;
            }
            let block = ((y / GRID - first / GRID) * columns + x / GRID) * 5;
            out[block] += 1;
            for c in 0..4 {
                out[block + 1 + c] += i64::from(image[pixel * 4 + c]);
            }
        }
    }
    out
}

#[allow(clippy::too_many_arguments)]
pub fn profile_sums(
    image: &[u8],
    distance: &[u8],
    shape: (usize, usize),
    grid: &[i64],
    grid_shape: (usize, usize),
    reach: usize,
    first: usize,
    last: usize,
) -> Vec<i64> {
    let bands = shape.0 / BAND;
    let mut out = vec![0; bands * (reach + 1) * 5];
    for y in first..last {
        for x in 0..shape.1 {
            let pixel = y * shape.1 + x;
            let at = ((y / BAND).min(bands - 1) * (reach + 1)
                + usize::from(distance[pixel]).min(reach))
                * 5;
            out[at] += 1;
            for c in 0..4 {
                out[at + 1 + c] +=
                    i64::from(image[pixel * 4 + c]) - background(grid, grid_shape, y, x, c);
            }
        }
    }
    out
}

fn shelf(table: &[i64], bands: usize, reach: usize, y: usize, distance: usize, c: usize) -> i64 {
    let position = (y as i64 * 1000 - BAND as i64 * 500).div_euclid(BAND as i64);
    let lower = position.div_euclid(1000).clamp(0, bands as i64 - 1) as usize;
    let upper = (lower + 1).min(bands - 1);
    let weight = (position - lower as i64 * 1000).clamp(0, 1000);
    let at = |band| table[(band * (reach + 1) + distance.min(reach)) * 4 + c];
    (at(lower) * (1000 - weight) + at(upper) * weight + 500).div_euclid(1000)
}

pub struct Render<'a> {
    pub image: &'a [u8],
    pub old: &'a [u8],
    pub new: &'a [u8],
    pub touched: &'a [bool],
    pub shape: (usize, usize),
    pub table: &'a [i64],
    pub bands: usize,
    pub grid: &'a [i64],
    pub grid_shape: (usize, usize),
    pub first: usize,
    pub last: usize,
    pub reach: usize,
    pub key: u64,
}

pub fn render(p: &Render<'_>) -> Vec<u8> {
    let width = p.shape.1;
    if !p.touched[p.first * width..p.last * width]
        .iter()
        .any(|&v| v)
    {
        return p.image[p.first * width * 4..p.last * width * 4].to_vec();
    }
    let start = p.first.saturating_sub(BLUR);
    let stop = (p.last + BLUR).min(p.shape.0);
    let rows = stop - start;
    let mut raw = vec![0_i64; rows * width * 4];
    raw.par_chunks_mut(width * 4)
        .enumerate()
        .for_each(|(r, line)| {
            let y = start + r;
            for x in 0..width {
                for c in 0..4 {
                    line[x * 4 + c] = shelf(
                        p.table,
                        p.bands,
                        p.reach,
                        y,
                        usize::from(p.new[y * width + x]),
                        c,
                    );
                }
            }
        });
    // box_blur floors vertically, then horizontally. Keep both divisions and the wrapped
    // horizontal padding; the strip includes the same vertical halo as Python.
    let mut vertical = vec![0_i64; raw.len()];
    vertical
        .par_chunks_mut(width * 4)
        .enumerate()
        .for_each(|(r, line)| {
            for x in 0..width {
                for c in 0..4 {
                    let mut sum = 0;
                    for dy in -(BLUR as isize)..=BLUR as isize {
                        let y = (r as isize + dy).clamp(0, rows as isize - 1) as usize;
                        sum += raw[(y * width + x) * 4 + c];
                    }
                    line[x * 4 + c] = sum.div_euclid(5);
                }
            }
        });
    drop(raw);
    let noise = fractal_window(
        p.key,
        (0, p.first as i64),
        (width, p.last - p.first),
        96,
        3,
        500,
    );
    let other = fractal_window(
        p.key,
        (width as i64, p.first as i64),
        (width, p.last - p.first),
        96,
        3,
        500,
    );
    let weights: Vec<i64> = (0..width)
        .map(|x| {
            let position = x as i64 * 1000 / width as i64;
            position * position * (3000 - 2 * position) / 1_000_000
        })
        .collect();
    let mut out = vec![0_u8; (p.last - p.first) * width * 4];
    out.par_chunks_mut(width * 4)
        .enumerate()
        .for_each(|(r, line)| {
            let y = p.first + r;
            for x in 0..width {
                let pixel = y * width + x;
                if !p.touched[pixel] {
                    line[x * 4..x * 4 + 4].copy_from_slice(&p.image[pixel * 4..pixel * 4 + 4]);
                    continue;
                }
                let keep = (i64::from(p.old[pixel].min(p.new[pixel])) - (p.reach as i64 - BLEND))
                    .clamp(0, BLEND);
                let open = (i64::from(p.old[pixel]) - (p.reach as i64 - BLEND)).clamp(0, BLEND);
                let n = (other[r * width + x] * (1000 - weights[x])
                    + noise[r * width + x] * weights[x])
                    .div_euclid(1000);
                for c in 0..4 {
                    let mut sum = 0_i64;
                    for dx in -(BLUR as isize)..=BLUR as isize {
                        let col = (x as isize + dx).rem_euclid(width as isize) as usize;
                        sum += vertical[((y - start) * width + col) * 4 + c];
                    }
                    let smooth = sum.div_euclid(5);
                    let far = shelf(p.table, p.bands, p.reach, y, p.reach, c);
                    let mut synthetic = smooth + background(p.grid, p.grid_shape, y, x, c);
                    if c < 3 {
                        synthetic += (n * 6 + NOISE_SCALE / 2).div_euclid(NOISE_SCALE);
                    }
                    let original = i64::from(p.image[pixel * 4 + c]);
                    let target =
                        ((original + smooth - far) * open + synthetic * (BLEND - open) + BLEND / 2)
                            .div_euclid(BLEND);
                    let blended =
                        (original * keep + target * (BLEND - keep) + BLEND / 2).div_euclid(BLEND);
                    line[x * 4 + c] = blended.clamp(0, 255) as u8;
                }
            }
        });
    out
}
