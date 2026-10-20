//! Integer raster resampling and blurring, equal to `rnw.fields` (the reference).
//!
//! Floor division by a positive divisor is `div_euclid`, as NumPy's `//` floors.

use rayon::prelude::*;

/// Bilinear interpolation of a grid whose sample `(i, j)` sits at `(i * step, j * step)`.
///
/// `coarse` has `columns` samples per row and at least `height / step + 2` rows.
pub fn upsample(
    coarse: &[i64],
    columns: usize,
    step: usize,
    (height, width): (usize, usize),
) -> Vec<i64> {
    let step = step as i64;
    let denominator = step * step;
    let mut out = vec![0_i64; height * width];
    out.par_chunks_mut(width)
        .enumerate()
        .for_each(|(row, line)| {
            let (i, fy) = ((row as i64 / step) as usize, row as i64 % step);
            let upper = &coarse[i * columns..(i + 1) * columns];
            let lower = &coarse[(i + 1) * columns..(i + 2) * columns];
            for (x, slot) in line.iter_mut().enumerate() {
                let (j, fx) = ((x as i64 / step) as usize, x as i64 % step);
                let top = upper[j] * (step - fx) + upper[j + 1] * fx;
                let bottom = lower[j] * (step - fx) + lower[j + 1] * fx;
                *slot = (top * (step - fy) + bottom * fy).div_euclid(denominator);
            }
        });
    out
}

/// Mean of each `step` x `step` block, partial blocks at the edges included by edge
/// replication. Returns the block grid `(rows, columns, values)`.
pub fn block_mean(
    values: &[i64],
    (height, width): (usize, usize),
    step: usize,
) -> (usize, usize, Vec<i64>) {
    let rows = height.div_ceil(step);
    let columns = width.div_ceil(step);
    let denominator = (step * step) as i64;
    let mut out = vec![0_i64; rows * columns];
    out.par_chunks_mut(columns)
        .enumerate()
        .for_each(|(block_row, line)| {
            for (block_column, slot) in line.iter_mut().enumerate() {
                let mut sum = 0_i64;
                for dy in 0..step {
                    let y = (block_row * step + dy).min(height - 1);
                    for dx in 0..step {
                        let x = (block_column * step + dx).min(width - 1);
                        sum += values[y * width + x];
                    }
                }
                *slot = sum.div_euclid(denominator);
            }
        });
    (rows, columns, out)
}

/// Separable integer box blur with edge replication: vertical pass, then horizontal.
pub fn box_blur(values: &[i64], (height, width): (usize, usize), radius: usize) -> Vec<i64> {
    let size = (2 * radius + 1) as i64;
    let radius = radius as i64;
    let last = height as i64 - 1;
    let mut vertical = vec![0_i64; values.len()];
    let chunk_rows = height.div_ceil(rayon::current_num_threads() * 4).max(1);
    vertical
        .par_chunks_mut(chunk_rows * width)
        .enumerate()
        .for_each(|(chunk, block)| {
            let first = (chunk * chunk_rows) as i64;
            let rows = (block.len() / width) as i64;
            let at = |row: i64, x: usize| values[row.clamp(0, last) as usize * width + x];
            let mut window = vec![0_i64; width];
            for k in -radius..=radius {
                for (x, sum) in window.iter_mut().enumerate() {
                    *sum += at(first + k, x);
                }
            }
            for local in 0..rows {
                for (x, sum) in window.iter().enumerate() {
                    block[local as usize * width + x] = sum.div_euclid(size);
                }
                let row = first + local;
                for (x, sum) in window.iter_mut().enumerate() {
                    *sum += at(row + radius + 1, x) - at(row - radius, x);
                }
            }
        });
    let mut out = vec![0_i64; values.len()];
    out.par_chunks_mut(width)
        .zip(vertical.par_chunks(width))
        .for_each(|(line, source)| {
            let at = |x: i64| source[x.clamp(0, width as i64 - 1) as usize];
            let mut sum: i64 = (-radius..=radius).map(at).sum();
            for (x, slot) in line.iter_mut().enumerate() {
                *slot = sum.div_euclid(size);
                sum += at(x as i64 + radius + 1) - at(x as i64 - radius);
            }
        });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn upsampling_interpolates_between_samples() {
        // 2 x 2 samples, step 2: sample (0,0)=0, (0,1)=8, (1,0)=16, (1,1)=24 spread over 2 x 2
        let coarse = [0, 8, 16, 24, 0, 0];
        // rows needed: height/step + 2 = 3 rows of 2 columns
        let out = upsample(&[0, 8, 16, 24, 32, 40], 2, 2, (2, 2));
        assert_eq!(out, vec![0, 4, 8, 12]);
        assert_eq!(coarse.len(), 6);
    }

    #[test]
    fn blocks_replicate_the_edge() {
        let (rows, columns, out) = block_mean(&[4, 4, 4, 8, 8, 8, 0, 0, 0], (3, 3), 2);
        assert_eq!((rows, columns), (2, 2));
        assert_eq!(out, vec![6, 6, 0, 0]);
    }

    #[test]
    fn a_blur_keeps_a_constant_and_floors_negatives() {
        assert_eq!(box_blur(&[5; 12], (3, 4), 2), vec![5; 12]);
        // -1 spread over three samples with edge replication floors to -1, not 0
        assert_eq!(box_blur(&[-1, 0, 0], (1, 3), 1), vec![-1, -1, 0]);
    }
}
