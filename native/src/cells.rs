//! Touching label pairs and per-cell sums of a labelled raster, equal to `adjacency_pairs`,
//! `adjacency_lengths` of `tests/reference/topology.py` and `cell_sums` of
//! `tests/reference/newworld.py`.
//!
//! A pair is packed as NumPy packs it: `(low << 32) | high` in 64-bit signed arithmetic of the
//! two labels, so a negative label keeps the bits it has there. Rows are scanned in parallel
//! and joined in order; the results do not depend on the number of threads.

use rayon::prelude::*;

fn pack(a: i32, b: i32) -> i64 {
    let (low, high) = (i64::from(a.min(b)), i64::from(a.max(b)));
    (low << 32) | high
}

fn push(found: &mut Vec<i64>, a: i32, b: i32) {
    if a != b {
        found.push(pack(a, b));
    }
}

/// The contacts that row `row` starts: within it, and with the row below.
fn row_contacts(
    labels: &[i32],
    (height, width): (usize, usize),
    row: usize,
    wrap_x: bool,
    diagonal: bool,
) -> Vec<i64> {
    let line = &labels[row * width..(row + 1) * width];
    let below = (row + 1 < height).then(|| &labels[(row + 1) * width..(row + 2) * width]);
    let mut found = Vec::new();
    for column in 1..width {
        push(&mut found, line[column - 1], line[column]);
    }
    if let Some(below) = below {
        for column in 0..width {
            push(&mut found, line[column], below[column]);
        }
        if diagonal {
            for column in 1..width {
                push(&mut found, line[column - 1], below[column]);
                push(&mut found, line[column], below[column - 1]);
            }
        }
    }
    if wrap_x && width > 1 {
        push(&mut found, line[width - 1], line[0]);
        if diagonal && let Some(below) = below {
            push(&mut found, line[width - 1], below[0]);
            push(&mut found, line[0], below[width - 1]);
        }
    }
    found
}

/// Sorted unique touching pairs: 4-neighbour contacts, with `diagonal` the corners too, and
/// with `wrap_x` the first and last columns touching.
pub fn adjacency_pairs(
    labels: &[i32],
    shape: (usize, usize),
    wrap_x: bool,
    diagonal: bool,
) -> Vec<i64> {
    let mut all: Vec<i64> = (0..shape.0)
        .into_par_iter()
        .map(|row| {
            let mut found = row_contacts(labels, shape, row, wrap_x, diagonal);
            found.sort_unstable();
            found.dedup();
            found
        })
        .flatten_iter()
        .collect();
    all.par_sort_unstable();
    all.dedup();
    all
}

/// Sorted unique 4-neighbour pairs and the number of pixel contacts of each.
pub fn adjacency_lengths(labels: &[i32], shape: (usize, usize)) -> (Vec<i64>, Vec<i64>) {
    let mut counted: Vec<(i64, i64)> = (0..shape.0)
        .into_par_iter()
        .map(|row| {
            let mut found = row_contacts(labels, shape, row, false, false);
            found.sort_unstable();
            let mut runs: Vec<(i64, i64)> = Vec::new();
            for pair in found {
                match runs.last_mut() {
                    Some((last, count)) if *last == pair => *count += 1,
                    _ => runs.push((pair, 1)),
                }
            }
            runs
        })
        .flatten_iter()
        .collect();
    counted.par_sort_unstable_by_key(|&(pair, _)| pair);
    let mut pairs: Vec<i64> = Vec::new();
    let mut lengths: Vec<i64> = Vec::new();
    for (pair, count) in counted {
        if pairs.last() == Some(&pair) {
            if let Some(last) = lengths.last_mut() {
                *last += count;
            }
        } else {
            pairs.push(pair);
            lengths.push(count);
        }
    }
    (pairs, lengths)
}

/// A label at or past `count`.
#[derive(Debug, PartialEq, Eq)]
pub struct LabelOutOfRange;

/// Pixels, row sum, column sum, elevation sum and elevation square sum of each of `count`
/// cells (labels below zero belong to none), as five rows of `count`.
pub fn cell_sums(
    labels: &[i32],
    elevation: &[i32],
    (height, width): (usize, usize),
    count: usize,
) -> Result<Vec<i64>, LabelOutOfRange> {
    let chunk_rows = height
        .div_ceil(rayon::current_num_threads().max(1) * 2)
        .max(1);
    let parts: Vec<Result<Vec<i64>, LabelOutOfRange>> = labels
        .par_chunks(chunk_rows * width.max(1))
        .zip(elevation.par_chunks(chunk_rows * width.max(1)))
        .enumerate()
        .map(|(chunk, (labels, elevation))| {
            let mut sums = vec![0_i64; 5 * count];
            for (at, (&label, &height)) in labels.iter().zip(elevation).enumerate() {
                if label < 0 {
                    continue;
                }
                let cell = label as usize;
                if cell >= count {
                    return Err(LabelOutOfRange);
                }
                let row = (chunk * chunk_rows + at / width) as i64;
                let column = (at % width) as i64;
                let value = i64::from(height);
                sums[cell] += 1;
                sums[count + cell] += row;
                sums[2 * count + cell] += column;
                sums[3 * count + cell] += value;
                sums[4 * count + cell] += value * value;
            }
            Ok(sums)
        })
        .collect();
    let mut total = vec![0_i64; 5 * count];
    for part in parts {
        for (slot, value) in total.iter_mut().zip(part?) {
            *slot += value;
        }
    }
    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pairs_are_packed_sorted_and_unique() {
        let labels = [0, 0, 1, 2, 2, 1];
        assert_eq!(
            adjacency_pairs(&labels, (2, 3), false, false),
            vec![1, 2, (1 << 32) | 2]
        );
        let (pairs, lengths) = adjacency_lengths(&labels, (2, 3));
        assert_eq!(pairs, vec![1, 2, (1 << 32) | 2]);
        assert_eq!(lengths, vec![1, 2, 1]);
        // A negative label keeps its sign bits, as NumPy's 64-bit arithmetic does.
        assert_eq!(
            adjacency_pairs(&[-1, 3], (1, 2), false, false),
            vec![(-1_i64 << 32) | 3]
        );
    }

    #[test]
    fn sums_count_each_cell_and_refuse_a_label_past_the_count() {
        let labels = [0, -1, 1, 1];
        let elevation = [5, 9, 2, 3];
        assert_eq!(
            cell_sums(&labels, &elevation, (2, 2), 2).unwrap(),
            vec![1, 2, 0, 2, 0, 1, 5, 5, 25, 13]
        );
        assert_eq!(
            cell_sums(&labels, &elevation, (2, 2), 1),
            Err(LabelOutOfRange)
        );
    }
}
