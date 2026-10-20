//! Terrain material slots of a decal window, equal to `rnw.eu5_slots.synthesize`.
//!
//! One pass of per-pixel rules over distance fields and wobble noise; see the Python
//! module for what each band means. Every threshold is an integer comparison.

use crate::distance::{distance_from, nearest_label};
use crate::noise::fractal_window;
use rayon::prelude::*;

const NO_MATERIAL: u8 = 255;
const COAST_TRANSITION: u8 = 5;
const WATER_EDGE: u8 = 6;
const TOPOGRAPHY_BORDER: u8 = 7;
const VEGETATION_BORDER: u8 = 8;
const CLIMATE_BORDER: u8 = 9;
const VARIATION: i64 = 10;
const LEVELS: i64 = 3;
const SLOTS: i64 = 16;
const PERMILLE: i64 = 1000;
const REACH: i32 = 16;
const LAND_COAST: (i64, i64) = (1, 4);
const LAND_TRANSITION: (i64, i64) = (4, 7);
const WATER_COAST: (i64, i64) = (2, 4);
const WATER_SHELF: (i64, i64) = (5, 5);
const BORDER: (i64, i64) = (3, 6);
const RIVER: (i64, i64) = (0, 3);
const OCTAVES: u32 = 2;
const PERSISTENCE: i64 = 500;

/// Per-label values (index = label).
pub struct Tables<'a> {
    pub water: &'a [bool],
    pub coast_slot: &'a [i64],
    pub topography: &'a [i64],
    pub vegetation: &'a [i64],
    pub climate: &'a [i64],
    pub level_one: &'a [i64],
    pub level_two: &'a [i64],
    pub materials: &'a [i64],
}

/// Wobble noise: one key per stream and the quantile tables of the three periods.
pub struct Wobble<'a> {
    pub coast: u64,
    pub shelf: u64,
    pub border: u64,
    pub family: u64,
    pub level: u64,
    pub periods: [i64; 3],
    pub quantiles: [&'a [i64]; 3],
}

/// Noise remapped to a near-uniform permille through the quantile table of its period.
fn uniform(
    key: u64,
    origin: (i64, i64),
    (height, width): (usize, usize),
    period: i64,
    quantiles: &[i64],
) -> Vec<u16> {
    let raw = fractal_window(key, origin, (width, height), period, OCTAVES, PERSISTENCE);
    raw.par_iter()
        .map(|&value| quantiles.partition_point(|&q| q <= value) as u16)
        .collect()
}

#[inline]
fn within(distance: i64, (lowest, span): (i64, i64), u: u16) -> bool {
    distance * PERMILLE <= lowest * PERMILLE + i64::from(u) * span
}

/// Land pixels with a 4-neighbouring land pixel of a different attribute.
fn border_mask(attribute: &[i64], (height, width): (usize, usize)) -> Vec<bool> {
    let mut out = vec![false; attribute.len()];
    out.par_chunks_mut(width)
        .enumerate()
        .for_each(|(row, line)| {
            for (column, slot) in line.iter_mut().enumerate() {
                let here = attribute[row * width + column];
                if here < 0 {
                    continue;
                }
                let differs = |other: i64| other >= 0 && other != here;
                *slot = (row > 0 && differs(attribute[(row - 1) * width + column]))
                    || (row + 1 < height && differs(attribute[(row + 1) * width + column]))
                    || (column > 0 && differs(attribute[row * width + column - 1]))
                    || (column + 1 < width && differs(attribute[row * width + column + 1]));
            }
        });
    out
}

/// Material slot per pixel of a window whose top-left decal pixel is `origin` (x, y).
///
/// `remap` is the slot table: row `n` gives the slot written for each slot 0-15 on a
/// biome that lists `n` materials (17 rows of 16).
#[allow(clippy::too_many_arguments)]
pub fn synthesize(
    labels: &[i32],
    land: &[bool],
    rivers: &[bool],
    shape: (usize, usize),
    tables: &Tables,
    wobble: &Wobble,
    origin: (i64, i64),
    remap: &[i64],
) -> Vec<u8> {
    let label_land: Vec<bool> = labels
        .par_iter()
        .map(|&l| !tables.water[l as usize])
        .collect();
    let dry: Vec<bool> = land.par_iter().map(|&v| !v).collect();
    let (near, (inland, offshore)) = rayon::join(
        || nearest_label(labels, &label_land, shape, REACH as usize),
        || {
            rayon::join(
                || distance_from(&dry, shape, REACH, true),
                || distance_from(land, shape, REACH, true),
            )
        },
    );
    drop(dry);
    let owner: Vec<usize> = near
        .par_iter()
        .zip(labels.par_iter())
        .map(|(&n, &l)| if n >= 0 { n as usize } else { l as usize })
        .collect();
    drop(near);
    let [period_band, period_family, period_level] = wobble.periods;
    let (u_coast, u_shelf, u_border) = {
        let (a, (b, c)) = rayon::join(
            || {
                uniform(
                    wobble.coast,
                    origin,
                    shape,
                    period_band,
                    wobble.quantiles[0],
                )
            },
            || {
                rayon::join(
                    || {
                        uniform(
                            wobble.shelf,
                            origin,
                            shape,
                            period_band,
                            wobble.quantiles[0],
                        )
                    },
                    || {
                        uniform(
                            wobble.border,
                            origin,
                            shape,
                            period_band,
                            wobble.quantiles[0],
                        )
                    },
                )
            },
        );
        (a, b, c)
    };
    let mut out = vec![NO_MATERIAL; labels.len()];
    // `free` marks land pixels no band has claimed yet.
    let mut free = vec![false; labels.len()];
    out.par_iter_mut()
        .zip(free.par_iter_mut())
        .enumerate()
        .for_each(|(at, (slot, free))| {
            let coast_slot = tables.coast_slot[owner[at]] as u8;
            if !land[at] {
                if within(i64::from(offshore[at]), WATER_SHELF, u_shelf[at]) {
                    *slot = WATER_EDGE;
                }
                if within(i64::from(offshore[at]), WATER_COAST, u_coast[at]) {
                    *slot = coast_slot;
                }
            } else if within(i64::from(inland[at]), LAND_COAST, u_coast[at]) {
                *slot = coast_slot;
            } else if within(i64::from(inland[at]), LAND_TRANSITION, u_shelf[at]) {
                *slot = COAST_TRANSITION;
            } else {
                *free = true;
            }
        });
    drop((inland, offshore, u_coast, u_shelf));
    if rivers.iter().any(|&r| r) {
        let near_river = distance_from(rivers, shape, REACH, true);
        out.par_iter_mut()
            .zip(free.par_iter_mut())
            .enumerate()
            .for_each(|(at, (slot, free))| {
                if *free && within(i64::from(near_river[at]), RIVER, u_border[at]) {
                    *slot = WATER_EDGE;
                    *free = false;
                }
            });
    }
    for (table, band) in [
        (tables.topography, TOPOGRAPHY_BORDER),
        (tables.vegetation, VEGETATION_BORDER),
        (tables.climate, CLIMATE_BORDER),
    ] {
        let attribute: Vec<i64> = labels
            .par_iter()
            .zip(label_land.par_iter())
            .map(|(&l, &on_land)| if on_land { table[l as usize] } else { -1 })
            .collect();
        let edge = border_mask(&attribute, shape);
        drop(attribute);
        let distance = distance_from(&edge, shape, REACH, true);
        out.par_iter_mut()
            .zip(free.par_iter_mut())
            .enumerate()
            .for_each(|(at, (slot, free))| {
                if *free && within(i64::from(distance[at]) * 2, BORDER, u_border[at]) {
                    *slot = band;
                    *free = false;
                }
            });
    }
    drop(u_border);
    let (family, level_u) = rayon::join(
        || {
            uniform(
                wobble.family,
                origin,
                shape,
                period_family,
                wobble.quantiles[1],
            )
        },
        || {
            uniform(
                wobble.level,
                origin,
                shape,
                period_level,
                wobble.quantiles[2],
            )
        },
    );
    out.par_iter_mut().enumerate().for_each(|(at, slot)| {
        let owner = owner[at];
        if free[at] {
            let u = i64::from(level_u[at]);
            let one = tables.level_one[owner];
            let level = if u < one {
                0
            } else if u < one + tables.level_two[owner] {
                1
            } else {
                2
            };
            let family = i64::from(i64::from(family[at]) >= PERMILLE / 2);
            *slot = (VARIATION + LEVELS * family + level) as u8;
        }
        if land[at] && i64::from(*slot) < SLOTS {
            let count = tables.materials[owner].clamp(0, SLOTS);
            *slot = remap[(count * SLOTS + i64::from(*slot)) as usize] as u8;
        }
    });
    out
}
