//! Compact sea cells: the geodesic partition of water the cells are relaxed on, and the exact
//! raster that follows it.
//!
//! A cell of the sea is meant to be a compact piece of water that a ship can cross, never one that
//! reaches round a spit of land or through a strait to the water beyond it. So the cells are made
//! on the *distance through the water*, not on the straight distance: [`geodesic`] measures it on a
//! coarse raster with integer steps (sixteen neighbours, a step of 1000 for a pixel), and
//! [`refine`] then gives every pixel of the full raster to the nearest of the few sites that the
//! coarse partition lets reach it, so that the borders between cells are exact straight bisectors.
//! Nothing here draws a random number or depends on the number of threads.

use rayon::prelude::*;

/// The cost of a step to a side, a diagonal and a knight's move, in thousandths of a pixel.
const STEPS: [(i32, i32, u32); 16] = [
    (0, 1, 1000),
    (0, -1, 1000),
    (1, 0, 1000),
    (-1, 0, 1000),
    (1, 1, 1414),
    (1, -1, 1414),
    (-1, 1, 1414),
    (-1, -1, 1414),
    (1, 2, 2236),
    (1, -2, 2236),
    (-1, 2, 2236),
    (-1, -2, 2236),
    (2, 1, 2236),
    (2, -1, 2236),
    (-2, 1, 2236),
    (-2, -1, 2236),
];
/// More than the dearest step, so a ring of this many buckets holds every pending cost at once.
const RING: usize = 2237;
/// The cost of a pixel that no site reaches.
pub const UNREACHED: u32 = u32::MAX;

/// The distance through water from the nearest site, and which site it is.
pub struct Geodesic {
    pub label: Vec<i32>,
    pub cost: Vec<u32>,
}

/// Whether `(row, column)` is water of the same region as the pixel a step starts from.
fn open(
    mask: &[bool],
    region: &[i32],
    (height, width): (usize, usize),
    (row, column): (i64, i64),
    own: i32,
) -> bool {
    if row < 0 || column < 0 || row as usize >= height || column as usize >= width {
        return false;
    }
    let at = row as usize * width + column as usize;
    mask[at] && region[at] == own
}

/// Whether the step `(dr, dc)` from `(row, column)` keeps to water of the region: a step across
/// a corner or past a spit of land, or past a pixel of another region, is not one.
fn clear(
    mask: &[bool],
    region: &[i32],
    shape: (usize, usize),
    (row, column): (i64, i64),
    (dr, dc): (i32, i32),
) -> bool {
    let own = region[row as usize * shape.1 + column as usize];
    let (dr, dc) = (i64::from(dr), i64::from(dc));
    let at = |r: i64, c: i64| open(mask, region, shape, (r, c), own);
    if !at(row + dr, column + dc) {
        return false;
    }
    let (ar, ac) = (dr.abs(), dc.abs());
    if ar + ac == 1 {
        return true;
    }
    if ar == 1 && ac == 1 {
        return at(row + dr, column) && at(row, column + dc);
    }
    // A knight's move crosses the two squares between its ends.
    let (mr, mc) = (dr / 2, dc / 2);
    if ar == 2 {
        at(row + mr, column) && at(row + mr, column + dc)
    } else {
        at(row, column + mc) && at(row + dr, column + mc)
    }
}

/// Every water pixel's distance through water from the nearest of `sites` (row, column), which
/// start at `start` (0 for a plain partition; a site with a larger start is a smaller cell). A
/// step never leaves its `region`: the water is partitioned region by region.
/// On equal distances the lower site number wins, so the partition does not depend on the order
/// the pixels are met in. Pixels of other components stay `-1` and `UNREACHED`.
pub fn geodesic(
    mask: &[bool],
    region: &[i32],
    height: usize,
    width: usize,
    sites: &[(usize, usize)],
    start: &[u32],
) -> Geodesic {
    let total = mask.len();
    let mut label = vec![-1_i32; total];
    let mut cost = vec![UNREACHED; total];
    let mut buckets: Vec<Vec<u32>> = vec![Vec::new(); RING];
    let mut order: Vec<usize> = (0..sites.len()).collect();
    order.sort_by_key(|&index| (start[index], index));
    let mut next = 0_usize;
    let mut live = 0_usize;
    let mut current = order.first().map_or(0, |&index| u64::from(start[index]));
    loop {
        while next < order.len() && u64::from(start[order[next]]) <= current {
            let index = order[next];
            next += 1;
            let (row, column) = sites[index];
            let at = row * width + column;
            if !mask[at] {
                continue;
            }
            let begin = start[index];
            if begin < cost[at] || (begin == cost[at] && (index as i32) < label[at]) {
                if cost[at] == UNREACHED || begin < cost[at] {
                    buckets[begin as usize % RING].push(at as u32);
                    live += 1;
                }
                cost[at] = begin;
                label[at] = index as i32;
            }
        }
        if live == 0 {
            if next >= order.len() {
                break;
            }
            current = u64::from(start[order[next]]);
            continue;
        }
        let slot = current as usize % RING;
        let mut stack = std::mem::take(&mut buckets[slot]);
        let mut head = 0;
        while head < stack.len() {
            let at = stack[head] as usize;
            head += 1;
            live -= 1;
            if u64::from(cost[at]) != current {
                continue;
            }
            let (row, column) = ((at / width) as i64, (at % width) as i64);
            let here = label[at];
            for &(dr, dc, step) in &STEPS {
                if !clear(mask, region, (height, width), (row, column), (dr, dc)) {
                    continue;
                }
                let to =
                    ((row + i64::from(dr)) as usize) * width + (column + i64::from(dc)) as usize;
                let reach = cost[at] + step;
                if reach < cost[to] {
                    cost[to] = reach;
                    label[to] = here;
                    buckets[reach as usize % RING].push(to as u32);
                    live += 1;
                } else if reach == cost[to] && here < label[to] {
                    label[to] = here;
                }
            }
            // Entries pushed into this very bucket cannot happen: every step costs something.
        }
        stack.clear();
        buckets[slot] = stack;
        current += 1;
    }
    Geodesic { label, cost }
}

/// The site of every label that is nearest to the label's own centre of mass, and the pixel
/// that is farthest from the site (by `cost`): `(medoid, farthest)` per label, `-1` for a label
/// without pixels. Ties go to the pixel first in raster order.
pub fn extremes(
    label: &[i32],
    cost: &[u32],
    width: usize,
    centres: &[(f64, f64)],
) -> (Vec<i64>, Vec<i64>) {
    let count = centres.len();
    let mut near = vec![-1_i64; count];
    let mut near_cost = vec![f64::INFINITY; count];
    let mut far = vec![-1_i64; count];
    let mut far_cost = vec![0_u32; count];
    for (at, (&owner, &reach)) in label.iter().zip(cost).enumerate() {
        if owner < 0 {
            continue;
        }
        let owner = owner as usize;
        let (row, column) = ((at / width) as f64, (at % width) as f64);
        let (cr, cc) = centres[owner];
        let distance = (row - cr) * (row - cr) + (column - cc) * (column - cc);
        if distance < near_cost[owner] {
            near_cost[owner] = distance;
            near[owner] = at as i64;
        }
        if far[owner] < 0 || reach > far_cost[owner] {
            far_cost[owner] = reach;
            far[owner] = at as i64;
        }
    }
    (near, far)
}

/// The smooth distance of a full-raster pixel, in eighths of a coarse pixel, interpolated between
/// the centres of the four coarse pixels round it.
fn smooth_depth(
    depth: &[i32],
    rows: usize,
    columns: usize,
    step: usize,
    row: usize,
    column: usize,
) -> i64 {
    // Twice the offset of the pixel's centre from a coarse centre, in half pixels.
    let span = 2 * step as i64;
    let place = |at: usize, count: usize| -> (usize, i64) {
        let from = (2 * at as i64 + 1) - step as i64;
        let first = from.div_euclid(span).clamp(0, (count as i64 - 2).max(0)) as usize;
        let offset = (from - first as i64 * span).clamp(0, span);
        (first, offset)
    };
    let (r0, a) = place(row, rows);
    let (c0, b) = place(column, columns);
    let r1 = (r0 + 1).min(rows - 1);
    let c1 = (c0 + 1).min(columns - 1);
    let at = |r: usize, c: usize| i64::from(depth[r * columns + c]);
    let total = (span - a) * (span - b) * at(r0, c0)
        + (span - a) * b * at(r0, c1)
        + a * (span - b) * at(r1, c0)
        + a * b * at(r1, c1);
    total / (span * span)
}

/// The bands of the coast and the sites' places in them, for [`refine`].
pub struct Bands<'a> {
    /// The distance from land of every coarse pixel, in eighths of a coarse pixel.
    pub depth: &'a [i32],
    /// The width of a band in the same unit, and the number of bands beyond which water is open.
    pub width: i64,
    pub last: i64,
    /// The band of every site; below zero for a site that belongs to no band (a strait's).
    pub site: &'a [i32],
    /// The square of the radius, in pixels, of the disk that is all of the site's cell or none of
    /// the others' (an island's), 0 for an ordinary site.
    pub claim: &'a [i64],
}

/// The partition of the full raster: each water pixel takes, of the labels that the coarse
/// partition gives to the coarse pixels round it (`reach` of them each way), the label whose site
/// (`sites`, in full-raster pixels) is the nearest in a straight line, the lower label on a tie.
/// A site with a `claim` holds every pixel within that radius of it, whatever else is nearer: the
/// cell of an island is the disk that holds the island and the water round it (the lowest label if
/// two disks overlap); between two ordinary sites the border is a straight one.
/// Only the sites of the pixel's own band compete (a strait's site competes with every band), the
/// band of a pixel being read from the smooth distance, so the border between two bands is a smooth
/// line and the border between two cells of a band a straight one. A pixel that no coarse pixel
/// near it gives a label to stays `-1`.
#[allow(clippy::too_many_arguments)]
pub fn refine(
    mask: &[bool],
    width: usize,
    coarse: &[i32],
    coarse_width: usize,
    step: usize,
    reach: usize,
    sites: &[(i64, i64)],
    bands: &Bands,
) -> Vec<i32> {
    let coarse_height = coarse.len() / coarse_width;
    let mut out = vec![-1_i32; mask.len()];
    out.par_chunks_mut(width)
        .zip(mask.par_chunks(width))
        .enumerate()
        .for_each(|(row, (line, flags))| {
            let cr = row / step;
            let rows = cr.saturating_sub(reach)..=(cr + reach).min(coarse_height - 1);
            for (column, (slot, &inside)) in line.iter_mut().zip(flags).enumerate() {
                if !inside {
                    continue;
                }
                let cc = column / step;
                let columns = cc.saturating_sub(reach)..=(cc + reach).min(coarse_width - 1);
                let depth =
                    smooth_depth(bands.depth, coarse_height, coarse_width, step, row, column);
                let band = (depth / bands.width.max(1)).min(bands.last) as i32;
                let mut best = (i64::MAX, i32::MAX);
                let mut any = (i64::MAX, i32::MAX);
                let mut seen = [-1_i32; 64];
                let mut count = 0;
                let mut claimed = i32::MAX;
                for r in rows.clone() {
                    for c in columns.clone() {
                        let owner = coarse[r * coarse_width + c];
                        if owner < 0 || seen[..count].contains(&owner) {
                            continue;
                        }
                        if count < seen.len() {
                            seen[count] = owner;
                            count += 1;
                        }
                        let (sr, sc) = sites[owner as usize];
                        let (dr, dc) = (row as i64 - sr, column as i64 - sc);
                        let squared = dr * dr + dc * dc;
                        let claim = bands.claim[owner as usize];
                        if claim > 0 && squared <= claim {
                            claimed = claimed.min(owner);
                        }
                        let key = (squared, owner);
                        any = any.min(key);
                        let belongs = bands.site[owner as usize];
                        if belongs < 0 || belongs == band {
                            best = best.min(key);
                        }
                    }
                }
                let chosen = if claimed != i32::MAX {
                    claimed
                } else if best.1 == i32::MAX {
                    any.1
                } else {
                    best.1
                };
                if chosen != i32::MAX {
                    *slot = chosen;
                }
            }
        });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn all(height: usize, width: usize) -> Vec<bool> {
        vec![true; height * width]
    }

    #[test]
    fn a_site_reaches_everything_at_its_distance() {
        let mask = all(5, 7);
        let found = geodesic(&mask, &vec![0; mask.len()], 5, 7, &[(2, 3)], &[0]);
        assert_eq!(found.cost[2 * 7 + 3], 0);
        assert_eq!(found.cost[2 * 7 + 4], 1000);
        assert_eq!(found.cost[3 * 7 + 4], 1414);
        assert_eq!(found.cost[3 * 7 + 5], 2236);
        assert!(found.label.iter().all(|&label| label == 0));
    }

    #[test]
    fn land_is_walked_round_not_across() {
        // A wall of land with one gap: the far side is reached through the gap only.
        let (height, width) = (7, 7);
        let mut mask = all(height, width);
        for row in 0..height {
            if row != 6 {
                mask[row * width + 3] = false;
            }
        }
        let found = geodesic(&mask, &vec![0; mask.len()], height, width, &[(0, 0)], &[0]);
        assert!(found.cost[width + 5] > 6000);
        assert!(found.cost[6 * width + 3] < UNREACHED);
    }

    #[test]
    fn a_corner_is_not_cut() {
        // Two land pixels meeting at a corner leave no way between the two waters.
        let mut mask = all(3, 3);
        mask[1] = false;
        mask[3] = false;
        let found = geodesic(&mask, &vec![0; mask.len()], 3, 3, &[(0, 0)], &[0]);
        assert_eq!(found.label[0], 0);
        assert_eq!(found.cost[4], UNREACHED);
    }

    #[test]
    fn ties_go_to_the_lower_site_whatever_the_order() {
        let mask = all(1, 5);
        let found = geodesic(
            &mask,
            &vec![0; mask.len()],
            1,
            5,
            &[(0, 4), (0, 0)],
            &[0, 0],
        );
        assert_eq!(found.label[2], 0);
        let again = geodesic(
            &mask,
            &vec![0; mask.len()],
            1,
            5,
            &[(0, 0), (0, 4)],
            &[0, 0],
        );
        assert_eq!(again.label[2], 0);
    }

    #[test]
    fn a_later_start_makes_a_smaller_cell() {
        let mask = all(1, 9);
        let found = geodesic(
            &mask,
            &vec![0; mask.len()],
            1,
            9,
            &[(0, 0), (0, 8)],
            &[0, 2000],
        );
        assert_eq!(found.label[5], 0);
        assert_eq!(found.label[6], 1);
    }

    #[test]
    fn a_region_is_never_left() {
        let mask = all(1, 6);
        let region = vec![0, 0, 0, 1, 1, 1];
        let found = geodesic(&mask, &region, 1, 6, &[(0, 0), (0, 5)], &[0, 0]);
        assert_eq!(found.label, vec![0, 0, 0, 1, 1, 1]);
        let lone = geodesic(&mask, &region, 1, 6, &[(0, 0)], &[0]);
        assert_eq!(lone.cost[3], UNREACHED);
    }

    #[test]
    fn refine_cuts_straight_between_the_two_sites() {
        let mask = all(1, 12);
        let coarse = vec![0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1];
        let bands = Bands {
            depth: &[0; 12],
            width: 8000,
            last: 0,
            site: &[0, 0],
            claim: &[0, 0],
        };
        let found = refine(&mask, 12, &coarse, 12, 1, 1, &[(0, 1), (0, 10)], &bands);
        assert_eq!(found, [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]);
    }

    #[test]
    fn refine_keeps_the_bands_apart_along_the_smooth_distance() {
        // Distance rises along the row; sites of band 0 and band 1 sit at either end of the
        // border, which lies where the distance reaches the band's width, not at the bisector.
        let mask = all(1, 12);
        let depth: Vec<i32> = (0..12).map(|c| c * 1000).collect();
        let coarse = vec![0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1];
        let bands = Bands {
            depth: &depth,
            width: 4000,
            last: 2,
            site: &[0, 1],
            claim: &[0, 0],
        };
        let found = refine(&mask, 12, &coarse, 12, 1, 12, &[(0, 1), (0, 4)], &bands);
        // Pixels with distance under 4000 (columns 0..=3, interpolated at their centres) are band 0.
        assert!(found[..3].iter().all(|&label| label == 0));
        assert!(found[6..].iter().all(|&label| label == 1));
    }

    #[test]
    fn refine_gives_a_claimed_disk_to_its_site_whatever_is_nearer() {
        // Site 1 claims the pixels within 3 of column 8, which takes column 5 from site 0 itself.
        let mask = all(1, 12);
        let coarse = vec![0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1];
        let bands = Bands {
            depth: &[0; 12],
            width: 8000,
            last: 0,
            site: &[0, 0],
            claim: &[0, 9],
        };
        let found = refine(&mask, 12, &coarse, 12, 1, 12, &[(0, 5), (0, 8)], &bands);
        assert_eq!(found, [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1]);
        let wide = Bands {
            depth: &[0; 12],
            width: 8000,
            last: 0,
            site: &[0, 0],
            claim: &[0, 25],
        };
        let found = refine(&mask, 12, &coarse, 12, 1, 12, &[(0, 5), (0, 8)], &wide);
        assert_eq!(found[3..], [1, 1, 1, 1, 1, 1, 1, 1, 1]);
        assert_eq!(found[..3], [0, 0, 0]);
    }

    #[test]
    fn extremes_find_the_nearest_pixel_to_the_centre_and_the_farthest_from_the_site() {
        let label = vec![0, 0, 0, 1, 1];
        let cost = vec![0, 1000, 2000, 0, 1000];
        let (near, far) = extremes(&label, &cost, 5, &[(0.0, 1.2), (0.0, 3.9)]);
        assert_eq!(near, vec![1, 4]);
        assert_eq!(far, vec![2, 4]);
    }
}
