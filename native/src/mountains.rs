//! Mountain stamps on a decal window, equal to `stamp` of `tests/reference/mountains.py`
//! (the NumPy specification of `rnw.eu5_mountains.MountainRelief.stamp`).
//!
//! A band of a terrain decal asks for the stamps of its window once; in NumPy that was
//! some thirty array operations per stamp, each waiting for the interpreter while another
//! stage ran Python beside the terrain. Integer arithmetic follows NumPy's: division and
//! remainder round towards negative infinity.

/// The stamps' sources: `count` height images of `height x width` samples and, when
/// `material_count` is not zero, as many slot images of `material_shape`.
pub struct Sources<'a> {
    pub heights: &'a [u16],
    pub count: usize,
    pub shape: (usize, usize),
    pub materials: &'a [u8],
    pub material_count: usize,
    pub material_shape: (usize, usize),
}

/// A placement: centre row and column, extents along and across, source, rotation and
/// strength, as `rnw.eu5_mountains.Mountain` holds them.
pub const FIELDS: usize = 7;

/// Why the stamps were refused.
#[derive(Debug, PartialEq, Eq)]
pub enum Fault {
    Shape,
    Placement,
}

fn floor_div(value: i64, divisor: i64) -> i64 {
    value.div_euclid(divisor)
}

fn floor_mod(value: i64, divisor: i64) -> i64 {
    value.rem_euclid(divisor)
}

/// Additive height and laid slot (`no_material` where none) of a window of `rows x columns`
/// decal pixels whose first pixel is at `origin` (column, row), in row-major order.
#[allow(clippy::too_many_arguments)]
pub fn stamp(
    sources: &Sources,
    placements: &[i64],
    bounds: &[i64],
    rotations: &[(i64, i64)],
    origin: (i64, i64),
    (rows, columns): (usize, usize),
    unit: i64,
    no_material: u8,
) -> Result<(Vec<i64>, Vec<u8>), Fault> {
    let (height, width) = sources.shape;
    let (slot_height, slot_width) = sources.material_shape;
    if height < 2
        || width < 2
        || sources.heights.len() != sources.count * height * width
        || sources.materials.len() != sources.material_count * slot_height * slot_width
        || (sources.material_count != 0 && (slot_height == 0 || slot_width == 0))
        || !placements.len().is_multiple_of(FIELDS)
        || bounds.len() != placements.len() / FIELDS * 4
        || unit <= 0
    {
        return Err(Fault::Shape);
    }
    let (column0, row0) = origin;
    let (rows_i, columns_i) = (rows as i64, columns as i64);
    let mut out = vec![0_i64; rows * columns];
    let mut best = vec![-1_i64; rows * columns];
    let (h, w) = (height as i64, width as i64);
    let (sh, sw) = (slot_height as i64, slot_width as i64);
    let fade_scale = h.max(w) * unit;
    for (index, place) in placements.as_chunks::<FIELDS>().0.iter().enumerate() {
        let edge = &bounds[index * 4..index * 4 + 4];
        if !(edge[0] < row0 + rows_i
            && edge[1] >= row0
            && edge[2] < column0 + columns_i
            && edge[3] >= column0)
        {
            continue;
        }
        let [row, column, along, across, source, rotation, strength] = *place;
        let source = usize::try_from(source).map_err(|_| Fault::Placement)?;
        let rotation = usize::try_from(rotation).map_err(|_| Fault::Placement)?;
        if along <= 0 || across <= 0 || source >= sources.count || rotation >= rotations.len() {
            return Err(Fault::Placement);
        }
        if sources.material_count != 0 && source >= sources.material_count {
            return Err(Fault::Placement);
        }
        let (cosine, sine) = rotations[rotation];
        let top = row0.max(edge[0]);
        let bottom = (row0 + rows_i).min(edge[1] + 1);
        let left = column0.max(edge[2]);
        let right = (column0 + columns_i).min(edge[3] + 1);
        let image = &sources.heights[source * height * width..(source + 1) * height * width];
        let slots = if sources.material_count != 0 {
            let size = slot_height * slot_width;
            Some(&sources.materials[source * size..(source + 1) * size])
        } else {
            None
        };
        for r in top..bottom {
            let yy = r - row;
            let line = (r - row0) as usize * columns;
            for c in left..right {
                let xx = c - column;
                let u = floor_div((xx * cosine + yy * sine) * w, along) + w * unit / 2;
                let v = floor_div((yy * cosine - xx * sine) * h, across) + h * unit / 2;
                let (ix, iy) = (floor_div(u, unit), floor_div(v, unit));
                let valid = ix >= 0 && ix < w - 1 && iy >= 0 && iy < h - 1;
                let x = ix.clamp(0, w - 2) as usize;
                let y = iy.clamp(0, h - 2) as usize;
                let (fx, fy) = (floor_mod(u, unit), floor_mod(v, unit));
                let sample = |yy: usize, xx: usize| i64::from(image[yy * width + xx]);
                let a = sample(y, x) * (unit - fx) + sample(y, x + 1) * fx;
                let b = sample(y + 1, x) * (unit - fx) + sample(y + 1, x + 1) * fx;
                let mut value = floor_div(a * (unit - fy) + b * fy, unit * unit);
                let rim = u.min((w - 1) * unit - u).min(v.min((h - 1) * unit - v));
                let fade = floor_div(rim * 32_000, fade_scale).clamp(0, 1000);
                value = if valid {
                    floor_div(floor_div(value * fade, 1000) * strength, 1000)
                } else {
                    0
                };
                let at = line + (c - column0) as usize;
                if let Some(slots) = slots {
                    let sy = iy.clamp(0, sh - 1) as usize;
                    let sx = ix.clamp(0, sw - 1) as usize;
                    let slot = slots[sy * slot_width + sx];
                    let laid = ix >= 0 && ix < sw && iy >= 0 && iy < sh;
                    if laid && slot != no_material {
                        let key = value * 256 + 255 - i64::from(slot);
                        best[at] = best[at].max(key);
                    }
                }
                out[at] += value;
            }
        }
    }
    let laid = best
        .iter()
        .map(|&key| {
            if key >= 0 {
                (255 - floor_mod(key, 256)) as u8
            } else {
                no_material
            }
        })
        .collect();
    Ok((out, laid))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_stamp_adds_its_source_and_lays_its_slot() {
        let heights = vec![1000_u16; 16 * 16];
        let materials = vec![11_u8; 16 * 16];
        let sources = Sources {
            heights: &heights,
            count: 1,
            shape: (16, 16),
            materials: &materials,
            material_count: 1,
            material_shape: (16, 16),
        };
        let placement = [8, 8, 16, 16, 0, 0, 1000];
        let bounds = [0, 16, 0, 16];
        let (out, laid) = stamp(
            &sources,
            &placement,
            &bounds,
            &[(1024, 0)],
            (0, 0),
            (20, 20),
            1024,
            255,
        )
        .unwrap();
        assert!(out[8 * 20 + 8] > 0);
        assert_eq!(laid[8 * 20 + 8], 11);
        // The rim fades the height to nothing; past the stamp's bounds nothing is laid.
        assert_eq!(out[0], 0);
        assert_eq!(out[19 * 20 + 19], 0);
        assert_eq!(laid[19 * 20 + 19], 255);
    }

    #[test]
    fn refuses_a_placement_outside_its_sources() {
        let heights = vec![0_u16; 4 * 4];
        let sources = Sources {
            heights: &heights,
            count: 1,
            shape: (4, 4),
            materials: &[],
            material_count: 0,
            material_shape: (0, 0),
        };
        let result = stamp(
            &sources,
            &[2, 2, 4, 4, 1, 0, 1000],
            &[0, 4, 0, 4],
            &[(1024, 0)],
            (0, 0),
            (4, 4),
            1024,
            255,
        );
        assert_eq!(result, Err(Fault::Placement));
    }
}
