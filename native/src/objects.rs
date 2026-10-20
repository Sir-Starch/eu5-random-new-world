//! Vegetation instances: material pixels of the canvas, their class counts and the
//! sampling of new instances, equal to `rnw.eu5_objects` (the reference).
//!
//! Material pixels are two per location pixel, row-major. A pixel's key is its label's
//! class times `SLOT_CLASSES` plus its material slot, with slots from `NO_SLOT` up merged.

use crate::hash::hash_point;
use rayon::prelude::*;

pub const SLOT_CLASSES: i64 = 18;
pub const NO_SLOT: u8 = 17;
const DENSITY_BITS: u32 = 24;
const RECORD_FLOATS: usize = 10;
const CHUNK: usize = 1 << 20;
const SECOND_STREAM: u64 = 0x5EED;

/// Why a raster cannot be turned into keys.
#[derive(Debug, PartialEq, Eq)]
pub enum Fault {
    /// A label outside the class tables or a negative key.
    Label,
    /// A raster of the wrong size.
    Shape,
}

/// Row, column, fine key and coarse key of every canvas material pixel, in raster order.
#[derive(Default)]
pub struct Pixels {
    pub rows: Vec<u32>,
    pub columns: Vec<u32>,
    pub fine: Vec<u32>,
    pub coarse: Vec<u32>,
}

/// Borrowed canvas pixels, as `Pixels` holds them.
#[derive(Clone, Copy)]
pub struct PixelView<'a> {
    pub rows: &'a [u32],
    pub columns: &'a [u32],
    pub fine: &'a [u32],
    pub coarse: &'a [u32],
}

impl Pixels {
    pub fn view(&self) -> PixelView<'_> {
        PixelView {
            rows: &self.rows,
            columns: &self.columns,
            fine: &self.fine,
            coarse: &self.coarse,
        }
    }
}

/// The rasters of one world: labels per location pixel, materials per material pixel.
pub struct Raster<'a> {
    pub labels: &'a [i32],
    pub materials: &'a [u8],
    pub shape: (usize, usize),
}

impl Raster<'_> {
    fn check(&self) -> Result<(), Fault> {
        let (height, width) = self.shape;
        if self.labels.len() != height * width || self.materials.len() != 4 * height * width {
            return Err(Fault::Shape);
        }
        Ok(())
    }

    #[inline]
    fn slot(&self, row: usize, column: usize) -> i64 {
        i64::from(self.materials[row * 2 * self.shape.1 + column].min(NO_SLOT))
    }
}

fn class_of(table: &[i64], label: i32) -> Result<i64, Fault> {
    usize::try_from(label)
        .ok()
        .and_then(|at| table.get(at))
        .copied()
        .ok_or(Fault::Label)
}

/// The canvas material pixels with their keys; `canvas` marks replaced location pixels and
/// pixels whose label has no class (a negative fine class) are skipped.
pub fn canvas_pixels(
    raster: &Raster,
    canvas: &[bool],
    fine_classes: &[i64],
    coarse_classes: &[i64],
) -> Result<Pixels, Fault> {
    raster.check()?;
    let (height, width) = raster.shape;
    let starts: Vec<usize> = (0..2 * height)
        .step_by(CHUNK / (2 * width).max(1) + 1)
        .collect();
    let step = CHUNK / (2 * width).max(1) + 1;
    let parts: Result<Vec<Pixels>, Fault> = starts
        .par_iter()
        .map(|&start| {
            let mut part = Pixels::default();
            for row in start..(start + step).min(2 * height) {
                for column in 0..2 * width {
                    let at = (row / 2) * width + column / 2;
                    if !canvas[at] {
                        continue;
                    }
                    let label = raster.labels[at];
                    let fine = class_of(fine_classes, label)?;
                    if fine < 0 {
                        continue;
                    }
                    let slot = raster.slot(row, column);
                    let coarse = class_of(coarse_classes, label)? * SLOT_CLASSES + slot;
                    let fine = fine * SLOT_CLASSES + slot;
                    if coarse < 0 {
                        return Err(Fault::Label);
                    }
                    part.rows.push(row as u32);
                    part.columns.push(column as u32);
                    part.fine.push(fine as u32);
                    part.coarse.push(coarse as u32);
                }
            }
            Ok(part)
        })
        .collect();
    let parts = parts?;
    let total: usize = parts.iter().map(|part| part.rows.len()).sum();
    let mut out = Pixels {
        rows: Vec::with_capacity(total),
        columns: Vec::with_capacity(total),
        fine: Vec::with_capacity(total),
        coarse: Vec::with_capacity(total),
    };
    for part in parts {
        out.rows.extend(part.rows);
        out.columns.extend(part.columns);
        out.fine.extend(part.fine);
        out.coarse.extend(part.coarse);
    }
    Ok(out)
}

/// Material pixels per key among the pixels whose label is in `mask`.
pub fn pixel_counts(
    raster: &Raster,
    table: &[i64],
    mask: &[bool],
    keys: usize,
) -> Result<Vec<i64>, Fault> {
    raster.check()?;
    let (height, width) = raster.shape;
    let step = CHUNK / (2 * width).max(1) + 1;
    let starts: Vec<usize> = (0..2 * height).step_by(step).collect();
    let parts: Result<Vec<Vec<i64>>, Fault> = starts
        .par_iter()
        .map(|&start| {
            let mut counts = vec![0_i64; keys];
            for row in start..(start + step).min(2 * height) {
                for column in 0..2 * width {
                    let label = raster.labels[(row / 2) * width + column / 2];
                    if !mask
                        .get(usize::try_from(label).map_err(|_| Fault::Label)?)
                        .copied()
                        .ok_or(Fault::Label)?
                    {
                        continue;
                    }
                    let key = class_of(table, label)? * SLOT_CLASSES + raster.slot(row, column);
                    *counts
                        .get_mut(usize::try_from(key).map_err(|_| Fault::Label)?)
                        .ok_or(Fault::Label)? += 1;
                }
            }
            Ok(counts)
        })
        .collect();
    let mut total = vec![0_i64; keys];
    for part in parts? {
        for (slot, value) in total.iter_mut().zip(part) {
            *slot += value;
        }
    }
    Ok(total)
}

/// Densities of one instance file per key: fixed point, expected instances per pixel.
pub struct Densities<'a> {
    /// Whether a key's own (fine) density applies; otherwise its coarse key's.
    pub use_fine: &'a [bool],
    pub fine: &'a [i64],
    pub coarse: &'a [i64],
}

/// New records for the canvas pixels: each pixel gets its density's whole part plus one
/// more with the fractional probability, at a hashed offset, copying a donor's rotation
/// and scale. Returns `count * 10` floats in pixel order.
pub fn sample_instances(
    pixels: PixelView,
    density: &Densities,
    donors: &[f32],
    key: u64,
    map_rows: i64,
) -> Vec<f32> {
    let count = donors.len() / RECORD_FLOATS;
    if count == 0 {
        return Vec::new();
    }
    let starts: Vec<usize> = (0..pixels.rows.len()).step_by(CHUNK).collect();
    let parts: Vec<Vec<f32>> = starts
        .par_iter()
        .map(|&start| {
            let mut out: Vec<f32> = Vec::new();
            for at in start..(start + CHUNK).min(pixels.rows.len()) {
                let (row, column) = (i64::from(pixels.rows[at]), i64::from(pixels.columns[at]));
                let (fine, coarse) = (pixels.fine[at] as usize, pixels.coarse[at] as usize);
                let density = if density.use_fine[fine] {
                    density.fine[fine]
                } else {
                    density.coarse[coarse]
                };
                if density <= 0 {
                    continue;
                }
                let fraction = (hash_point(key, column, row) & ((1 << DENSITY_BITS) - 1)) as i64;
                for copy in 0..(density + fraction) >> DENSITY_BITS {
                    let second = hash_point(key ^ SECOND_STREAM, column * 8 + copy, row);
                    let (dx, dz) = ((second & 0xFFFF) as i64, ((second >> 16) & 0xFFFF) as i64);
                    let donor = ((second >> 32) % count as u64) as usize;
                    let record = &donors[donor * RECORD_FLOATS..][..RECORD_FLOATS];
                    out.extend_from_slice(record);
                    let base = out.len() - RECORD_FLOATS;
                    out[base] = ((column * 65536 + dx) as f64 / 131_072.0) as f32;
                    out[base + 1] = 0.0;
                    out[base + 2] =
                        (map_rows as f64 - (row * 65536 + dz) as f64 / 131_072.0) as f32;
                }
            }
            out
        })
        .collect();
    let mut out = Vec::with_capacity(parts.iter().map(Vec::len).sum());
    for part in parts {
        out.extend(part);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn world() -> (Vec<i32>, Vec<u8>) {
        // 2 x 2 location pixels, 4 x 4 material pixels
        (vec![0, 1, 1, 0], (0..16).map(|v| v as u8 * 2).collect())
    }

    #[test]
    fn canvas_pixels_follow_raster_order_with_merged_slots() {
        let (labels, materials) = world();
        let raster = Raster {
            labels: &labels,
            materials: &materials,
            shape: (2, 2),
        };
        let canvas = [true, false, false, true];
        let pixels = canvas_pixels(&raster, &canvas, &[0, 1], &[5, 5]).unwrap();
        assert_eq!(pixels.rows, vec![0, 0, 1, 1, 2, 2, 3, 3]);
        assert_eq!(pixels.columns, vec![0, 1, 0, 1, 2, 3, 2, 3]);
        // the slot of material pixel (0, 1) is 2 and of (1, 1) is 10; (3, 3) holds 30, merged to 17
        assert_eq!(pixels.fine[1], 2);
        assert_eq!(pixels.coarse[1], 5 * 18 + 2);
        assert_eq!(pixels.fine[3], 10);
        assert_eq!(pixels.fine[7], 17);
    }

    #[test]
    fn counts_use_only_masked_labels() {
        let (labels, materials) = world();
        let raster = Raster {
            labels: &labels,
            materials: &materials,
            shape: (2, 2),
        };
        let counts = pixel_counts(&raster, &[0, 1], &[true, false], 2 * 18).unwrap();
        assert_eq!(counts.iter().sum::<i64>(), 8);
        assert_eq!(
            pixel_counts(&raster, &[0, 1], &[true, false], 3),
            Err(Fault::Label)
        );
    }

    #[test]
    fn sampling_is_in_pixel_order_and_reproducible() {
        let pixels = Pixels {
            rows: vec![0, 0],
            columns: vec![0, 1],
            fine: vec![0, 0],
            coarse: vec![0, 0],
        };
        let density = Densities {
            use_fine: &[true],
            fine: &[2 << DENSITY_BITS],
            coarse: &[0],
        };
        let donors: Vec<f32> = (0..20).map(|v| v as f32).collect();
        let first = sample_instances(pixels.view(), &density, &donors, 7, 100);
        assert_eq!(first.len(), 4 * RECORD_FLOATS); // two whole instances per pixel
        assert_eq!(
            first,
            sample_instances(pixels.view(), &density, &donors, 7, 100)
        );
        assert!(sample_instances(pixels.view(), &density, &[], 7, 100).is_empty());
    }
}
