//! Distance fields and label spreading on rasters, equal to `rnw.topology` (the reference).

use rayon::prelude::*;

/// Step distance to the nearest source pixel, capped at `limit`.
///
/// Steps are 4-neighbour; with `octagonal` the diagonal neighbours also count on every
/// second round. Level by level, so a pixel gets the round in which it is first reached.
pub fn distance_from(
    sources: &[bool],
    (height, width): (usize, usize),
    limit: i32,
    octagonal: bool,
) -> Vec<i32> {
    let mut distance = vec![limit; sources.len()];
    let mut frontier: Vec<u32> = Vec::new();
    for (index, &source) in sources.iter().enumerate() {
        if source {
            distance[index] = 0;
            frontier.push(index as u32);
        }
    }
    let mut next: Vec<u32> = Vec::new();
    for step in 1..limit {
        if frontier.is_empty() {
            break;
        }
        let diagonal = octagonal && step % 2 == 0;
        for &at in &frontier {
            let (row, column) = (at as usize / width, at as usize % width);
            let up = row > 0;
            let down = row + 1 < height;
            let left = column > 0;
            let right = column + 1 < width;
            let mut reach = |target: usize| {
                if distance[target] > step {
                    distance[target] = step;
                    next.push(target as u32);
                }
            };
            let at = at as usize;
            if up {
                reach(at - width);
            }
            if down {
                reach(at + width);
            }
            if left {
                reach(at - 1);
            }
            if right {
                reach(at + 1);
            }
            if diagonal {
                if up && left {
                    reach(at - width - 1);
                }
                if up && right {
                    reach(at - width + 1);
                }
                if down && left {
                    reach(at + width - 1);
                }
                if down && right {
                    reach(at + width + 1);
                }
            }
        }
        std::mem::swap(&mut frontier, &mut next);
        next.clear();
    }
    distance
}

/// Why an exact distance cannot be computed.
#[derive(Debug, PartialEq, Eq)]
pub struct LimitTooLarge;

/// Exact Euclidean distance to the nearest source, in eighths of a pixel, capped at
/// `limit` pixels.
///
/// A vertical pass finds each column's nearest source row; a horizontal pass takes the
/// minimum of `vertical² + dx²`. The square root of an exact integer is correctly rounded
/// in IEEE arithmetic, so the result is the same on every platform.
pub fn euclidean_distance(
    sources: &[bool],
    (height, width): (usize, usize),
    limit: usize,
) -> Result<Vec<i64>, LimitTooLarge> {
    let far = limit + 1;
    if far > 65_535 {
        return Err(LimitTooLarge);
    }
    let mut vertical = vec![far as u32; sources.len()];
    let mut last = vec![-(far as i64); width];
    for row in 0..height {
        let (flags, line) = (
            &sources[row * width..][..width],
            &mut vertical[row * width..][..width],
        );
        for x in 0..width {
            if flags[x] {
                last[x] = row as i64;
            }
            line[x] = (row as i64 - last[x]).min(far as i64) as u32;
        }
    }
    last.fill((height + far) as i64);
    for row in (0..height).rev() {
        let (flags, line) = (
            &sources[row * width..][..width],
            &mut vertical[row * width..][..width],
        );
        for x in 0..width {
            if flags[x] {
                last[x] = row as i64;
            }
            line[x] = line[x].min((last[x] - row as i64).min(far as i64) as u32);
        }
    }
    let cap = (far * far) as u64;
    let mut out = vec![0_i64; sources.len()];
    out.par_chunks_mut(width)
        .zip(vertical.par_chunks(width))
        .for_each(|(line, vertical)| {
            let squares: Vec<u64> = vertical
                .iter()
                .map(|&v| u64::from(v) * u64::from(v))
                .collect();
            for (x, slot) in line.iter_mut().enumerate() {
                let mut best = squares[x];
                let mut offset = 1_usize;
                while (offset * offset) as u64 <= best {
                    let extra = (offset * offset) as u64;
                    if x >= offset {
                        best = best.min(squares[x - offset] + extra);
                    }
                    if x + offset < width {
                        best = best.min(squares[x + offset] + extra);
                    }
                    offset += 1;
                }
                *slot = ((best.min(cap) as f64).sqrt() * 8.0).floor() as i64;
            }
        });
    Ok(out)
}

/// Spread the labels of `sources` pixels outwards by up to `limit` 4-steps.
///
/// Pixels farther than `limit` keep -1. A pixel reached by several labels in the same
/// step takes the label of the lowest-index neighbour that reached it: the frontier is
/// kept in index order and a pixel is claimed by the first neighbour that reaches it.
pub fn nearest_label(
    labels: &[i32],
    sources: &[bool],
    (height, width): (usize, usize),
    limit: usize,
) -> Vec<i32> {
    let mut out: Vec<i32> = labels
        .iter()
        .zip(sources)
        .map(|(&l, &s)| if s { l } else { -1 })
        .collect();
    let mut frontier: Vec<u32> = sources
        .iter()
        .enumerate()
        .filter_map(|(index, &source)| source.then_some(index as u32))
        .collect();
    let mut next: Vec<u32> = Vec::new();
    for _ in 0..limit {
        if frontier.is_empty() {
            break;
        }
        for &at in &frontier {
            let at = at as usize;
            let (row, column) = (at / width, at % width);
            let label = out[at];
            let mut claim = |target: usize| {
                if out[target] < 0 {
                    out[target] = label;
                    next.push(target as u32);
                }
            };
            if row > 0 {
                claim(at - width);
            }
            if row + 1 < height {
                claim(at + width);
            }
            if column > 0 {
                claim(at - 1);
            }
            if column + 1 < width {
                claim(at + 1);
            }
        }
        next.sort_unstable();
        std::mem::swap(&mut frontier, &mut next);
        next.clear();
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn steps_spread_from_a_source() {
        let mut sources = vec![false; 25];
        sources[12] = true;
        let d = distance_from(&sources, (5, 5), 4, false);
        assert_eq!(d[12], 0);
        assert_eq!(d[13], 1);
        assert_eq!(d[14], 2);
        assert_eq!(d[0], 4); // 4 steps away is the limit
        let octagon = distance_from(&sources, (5, 5), 4, true);
        assert_eq!(octagon[6], 2); // the diagonal is reached on the second round
    }

    #[test]
    fn euclidean_distance_is_in_eighths() {
        let mut sources = vec![false; 25];
        sources[0] = true;
        let d = euclidean_distance(&sources, (5, 5), 10).unwrap();
        assert_eq!(d[0], 0);
        assert_eq!(d[1], 8);
        assert_eq!(d[6], 11); // sqrt(2) * 8 = 11.31
        assert_eq!(
            euclidean_distance(&sources, (5, 5), 70_000),
            Err(LimitTooLarge)
        );
    }

    #[test]
    fn labels_spread_by_the_lowest_neighbour() {
        let labels = [7, -1, 9];
        let sources = [true, false, true];
        // the middle pixel is reached by both ends; the lower index (7) wins
        assert_eq!(nearest_label(&labels, &sources, (1, 3), 1), vec![7, 7, 9]);
    }
}
