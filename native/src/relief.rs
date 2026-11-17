//! Fused relief arithmetic with the original order of every division and clamp.

use crate::raster::box_blur;
use rayon::prelude::*;

fn smooth(value: i64, low: i64, high: i64) -> i64 {
    let t = value
        .wrapping_sub(low)
        .wrapping_mul(1000)
        .div_euclid((high - low).max(1))
        .clamp(0, 1000);
    t * t * (3000 - 2 * t) / 1_000_000
}

/// The original chain envelope from its axis, fine wander and width noise.
/// Params: slope reach, blur, floor, fade low/high, wander divisor, noise scale, core/flank.
pub fn chain(
    axis: &[i64],
    wander: &[i64],
    width_noise: &[i64],
    shape: (usize, usize),
    p: [i64; 9],
) -> Vec<i64> {
    let (rows, width) = shape;
    let reach = p[0] as usize;
    let mut slope = vec![0_i64; axis.len()];
    slope
        .par_chunks_mut(width)
        .enumerate()
        .for_each(|(y, line)| {
            for (x, slot) in line.iter_mut().enumerate() {
                let dx = axis[y * width + (x + reach).min(width - 1)]
                    .wrapping_sub(axis[y * width + x.saturating_sub(reach)])
                    .wrapping_mul(16)
                    .div_euclid(2 * p[0]);
                let dy = axis[(y + reach).min(rows - 1) * width + x]
                    .wrapping_sub(axis[y.saturating_sub(reach) * width + x])
                    .wrapping_mul(16)
                    .div_euclid(2 * p[0]);
                let square = dx.wrapping_mul(dx).wrapping_add(dy.wrapping_mul(dy));
                // NumPy casts an invalid square root to int64's minimum. Generated
                // noise is bounded, but keep the same result for overflow fixtures too.
                *slot = if square < 0 {
                    i64::MIN
                } else {
                    (square as f64).sqrt() as i64
                };
            }
        });
    let slope = box_blur(&slope, shape, p[1] as usize);
    let mut out = vec![0_i64; axis.len()];
    out.par_iter_mut().enumerate().for_each(|(at, slot)| {
        let distance = axis[at]
            .wrapping_add(wander[at].div_euclid(p[5]))
            .wrapping_abs()
            .wrapping_mul(256)
            .div_euclid(slope[at].max(p[2]));
        let decisive = smooth(slope[at], p[3], p[4]);
        let scale = 1000_i64.wrapping_add(width_noise[at].wrapping_mul(1000).div_euclid(2 * p[6]));
        let zone = |extent: i64| {
            1000_i64
                .wrapping_sub(
                    distance.wrapping_mul(1000).div_euclid(
                        extent
                            .wrapping_mul(16)
                            .wrapping_mul(scale)
                            .div_euclid(1000)
                            .max(1),
                    ),
                )
                .clamp(0, 1000)
        };
        let inner = zone(p[7]);
        let outer = zone(p[8]);
        let envelope = (smooth(outer, 0, 1000) * 450 + smooth(inner, 0, 1000) * 550) / 1000;
        *slot = envelope * decisive / 1000;
    });
    out
}

/// Owned ridge accumulators: each octave updates the same two buffers.
pub struct Ridges {
    total: Vec<i64>,
    weight: Vec<i64>,
    scale: i64,
    gain: i64,
}

impl Ridges {
    pub fn new(size: usize, scale: i64, gain: i64) -> Self {
        Self {
            total: vec![0; size],
            weight: vec![1000; size],
            scale,
            gain,
        }
    }

    pub fn add(&mut self, noise: &[i64], share: i64) {
        self.total
            .par_iter_mut()
            .zip(self.weight.par_iter_mut())
            .zip(noise.par_iter())
            .for_each(|((total, weight), &noise)| {
                let crest = self
                    .scale
                    .wrapping_sub(noise.wrapping_abs().min(self.scale));
                let crest = crest.wrapping_mul(crest).div_euclid(self.scale);
                *total = total.wrapping_add(
                    crest
                        .wrapping_mul(*weight)
                        .div_euclid(1000)
                        .wrapping_mul(share)
                        .div_euclid(1000),
                );
                *weight = crest
                    .wrapping_mul(self.gain)
                    .div_euclid(self.scale)
                    .min(1000);
            });
    }

    pub fn finish(&mut self, shares: i64) -> Vec<i64> {
        let mut total = std::mem::take(&mut self.total);
        total.par_iter_mut().for_each(|value| {
            *value = value
                .wrapping_mul(1000)
                .wrapping_mul(1000)
                .div_euclid(shares * self.scale)
                .min(1000)
        });
        total
    }
}
