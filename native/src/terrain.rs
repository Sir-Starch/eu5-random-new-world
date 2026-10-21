//! Land mask, coast distances and generated heights of a decal window, equal to
//! `rnw.eu5_terrain._land_and_distances` and `_heights` (the references).
//!
//! The window is given at location resolution (`codes`, `vanilla_water`, `relief`) and
//! the results are at decal resolution, two pixels per location pixel.

use crate::distance::{distance_from, euclidean_distance};
use crate::noise::fractal_window;
use crate::raster::{box_blur, upsample};
use crate::slots::{Core, crop};
use rayon::prelude::*;
use std::collections::HashMap;

const OUTSIDE: i8 = -1;
const WATER_CODE: i8 = 0;
const DETAIL_OCTAVES: u32 = 3;
const PERSISTENCE: i64 = 500;
const PERMILLE: i64 = 1000;
const LAND_THRESHOLD: i64 = 500;

/// Integer constants of the height model, by name.
pub struct Params(HashMap<String, i64>);

impl Params {
    pub fn new(values: HashMap<String, i64>) -> Self {
        Self(values)
    }

    fn get(&self, name: &str) -> Result<i64, String> {
        self.0
            .get(name)
            .copied()
            .ok_or_else(|| format!("missing parameter {name}"))
    }
}

/// Each pixel repeated into a 2 x 2 block.
fn double<T: Copy + Send + Sync>(values: &[T], (height, width): (usize, usize)) -> Vec<T> {
    let mut out = Vec::with_capacity(values.len() * 4);
    for row in 0..height {
        let line = &values[row * width..(row + 1) * width];
        for _ in 0..2 {
            for &value in line {
                out.push(value);
                out.push(value);
            }
        }
    }
    out
}

/// A grid with its last row and column repeated once more (edge padding).
fn pad_edge(values: &[i64], (height, width): (usize, usize)) -> Vec<i64> {
    let mut out = Vec::with_capacity((height + 1) * (width + 1));
    for row in 0..=height {
        let line = &values[row.min(height - 1) * width..][..width];
        out.extend_from_slice(line);
        out.push(line[width - 1]);
    }
    out
}

/// Land mask, canvas mask, inland and offshore distances (eighths of a decal pixel).
pub struct Fields {
    pub land: Vec<bool>,
    pub canvas: Vec<bool>,
    pub inland: Vec<i64>,
    pub offshore: Vec<i64>,
}

pub fn land_and_distances(
    codes: &[i8],
    vanilla_water: &[bool],
    shape: (usize, usize),
    params: &Params,
    profile_end: i32,
) -> Result<Fields, String> {
    let smooth_radius = params.get("coast_smooth")? as usize;
    let cap_reach = params.get("cap_reach")? as usize;
    let eighths = params.get("eighths")?;
    let canvas_location: Vec<bool> = codes.par_iter().map(|&c| c != OUTSIDE).collect();
    let land_location: Vec<bool> = codes
        .par_iter()
        .zip(vanilla_water.par_iter())
        .map(|(&c, &water)| {
            if c == OUTSIDE {
                !water
            } else {
                c != WATER_CODE
            }
        })
        .collect();
    let canvas = double(&canvas_location, shape);
    let raw = double(&land_location, shape);
    let doubled = (shape.0 * 2, shape.1 * 2);
    let weights: Vec<i64> = raw.par_iter().map(|&v| i64::from(v) * PERMILLE).collect();
    let blurred = box_blur(&weights, doubled, smooth_radius);
    drop(weights);
    let land: Vec<bool> = (0..raw.len())
        .into_par_iter()
        .map(|at| {
            if canvas[at] {
                blurred[at] >= LAND_THRESHOLD
            } else {
                raw[at]
            }
        })
        .collect();
    drop((blurred, raw));
    let sources: Vec<bool> = land_location.iter().map(|&v| !v).collect();
    let reach: Vec<i64> = euclidean_distance(&sources, shape, cap_reach)
        .map_err(|_| "distance limit too large".to_string())?
        .into_iter()
        .map(|v| v * 2)
        .collect();
    drop((sources, land_location, canvas_location));
    let (inland, offshore) = rayon::join(
        || {
            let padded = pad_edge(&reach, shape);
            let spread = upsample(&padded, shape.1 + 1, 2, doubled);
            box_blur(&spread, doubled, 2)
        },
        || {
            let steps = distance_from(&land, doubled, profile_end, true);
            let scaled: Vec<i64> = steps.iter().map(|&s| i64::from(s) * eighths).collect();
            box_blur(&scaled, doubled, 2)
        },
    );
    let inland = (0..land.len())
        .into_par_iter()
        .map(|at| if land[at] { inland[at].max(eighths) } else { 0 })
        .collect();
    let offshore = (0..land.len())
        .into_par_iter()
        .map(|at| {
            if land[at] {
                0
            } else {
                offshore[at].max(eighths)
            }
        })
        .collect();
    Ok(Fields {
        land,
        canvas,
        inland,
        offshore,
    })
}

/// Piecewise-linear interpolation of a (distance, height) table; `distance` is in
/// `1 / unit` pixels.
fn profile(distance: i64, table: &[(i64, i64)], unit: i64) -> i64 {
    if distance <= table[0].0 * unit {
        return table[0].1;
    }
    for pair in table.windows(2) {
        let ((d0, h0), (d1, h1)) = (pair[0], pair[1]);
        if distance > d0 * unit && distance <= d1 * unit {
            return h0 + ((distance - d0 * unit) * (h1 - h0)).div_euclid((d1 - d0) * unit);
        }
    }
    table[table.len() - 1].1
}

/// Heights of the `core` of the window (decal pixels; row-major, core-sized): relief plus
/// detail under a coastal cap on land, the shelf profile in water. The fields and the
/// relief cover the whole window; the noise and the per-pixel rules run on the core.
#[allow(clippy::too_many_arguments)]
pub fn heights(
    relief: &[i64],
    shape: (usize, usize),
    core: Core,
    fields: &Fields,
    keys: (u64, u64),
    origin: (i64, i64),
    table: &[(i64, i64)],
    params: &Params,
) -> Result<Vec<i64>, String> {
    let doubled = (shape.0 * 2, shape.1 * 2);
    let coast_height = params.get("coast_height")?;
    let filled: Vec<i64> = relief
        .par_iter()
        .map(|&r| if r > 0 { r } else { coast_height })
        .collect();
    let smooth = crop(
        &upsample(&pad_edge(&filled, shape), shape.1 + 1, 2, doubled),
        doubled.1,
        core,
    );
    drop(filled);
    let (land, inland, offshore) = (
        crop(&fields.land, doubled.1, core),
        crop(&fields.inland, doubled.1, core),
        crop(&fields.offshore, doubled.1, core),
    );
    let origin = (origin.0 + core.column0 as i64, origin.1 + core.row0 as i64);
    let (detail_period, crest_period) = (params.get("detail_period")?, params.get("crest_period")?);
    let (detail, crest) = rayon::join(
        || {
            fractal_window(
                keys.0,
                origin,
                (core.columns, core.rows),
                detail_period,
                DETAIL_OCTAVES,
                PERSISTENCE,
            )
        },
        || {
            fractal_window(
                keys.1,
                origin,
                (core.columns, core.rows),
                crest_period,
                DETAIL_OCTAVES,
                PERSISTENCE,
            )
        },
    );
    let noise_scale = params.get("noise_scale")?;
    let (detail_base, detail_permille) =
        (params.get("detail_base")?, params.get("detail_permille")?);
    let (crest_full, crest_height) = (params.get("crest_full")?, params.get("crest_height")?);
    let (shore, slope, eighths) = (
        params.get("shore_height")?,
        params.get("cap_slope")?,
        params.get("eighths")?,
    );
    Ok((0..smooth.len())
        .into_par_iter()
        .map(|at| {
            if !land[at] {
                return profile(offshore[at], table, eighths);
            }
            let raised = (smooth[at] - coast_height).max(0);
            let amplitude = detail_base + (raised * detail_permille).div_euclid(PERMILLE);
            let ridge = noise_scale - crest[at].abs().min(noise_scale);
            let crests = ((ridge * ridge).div_euclid(noise_scale) * raised.min(crest_full))
                .div_euclid(crest_full);
            let inner = smooth[at]
                + (detail[at] * amplitude).div_euclid(noise_scale)
                + (crests * crest_height).div_euclid(noise_scale);
            let cap = shore + ((inland[at] - eighths) * slope).div_euclid(eighths);
            inner.min(cap).max(shore)
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_profile_interpolates_and_floors() {
        let table = [(1, 5292), (2, 4636), (3, 4028)];
        assert_eq!(profile(0, &table, 8), 5292);
        assert_eq!(profile(8, &table, 8), 5292);
        assert_eq!(
            profile(12, &table, 8),
            5292 + (4_i64 * (4636 - 5292)).div_euclid(8)
        );
        assert_eq!(profile(100, &table, 8), 4028);
    }

    #[test]
    fn edge_padding_repeats_the_last_row_and_column() {
        assert_eq!(
            pad_edge(&[1, 2, 3, 4], (2, 2)),
            vec![1, 2, 2, 3, 4, 4, 3, 4, 4]
        );
        assert_eq!(double(&[1, 2], (1, 2)), vec![1, 1, 2, 2, 1, 1, 2, 2]);
    }
}
