//! LZAV encoding and tiled, mip-mapped decal layers, equal to `rnw.lzav.encode` and
//! `rnw.terrain_tiles.write_layer` (the references).

use rayon::prelude::*;

const FORMAT: u8 = 3;
const MIN_REFERENCE: usize = 5;
const LITERALS_AT_END: usize = 9;
const SHORT_LENGTH: usize = 16;
const SHORT_REFERENCE: usize = 15;
const RUN_DISTANCE: usize = 8;
const MIN_RUN: usize = 32;
pub const TILE: usize = 128;
pub const BORDER: usize = 2;
pub const SIDE: usize = TILE + 2 * BORDER;

fn push_length(out: &mut Vec<u8>, mut value: usize) {
    while value > 0x7F {
        out.push(0x80 | (value & 0x7F) as u8);
        value >>= 7;
    }
    out.push(value as u8);
}

fn push_literals(out: &mut Vec<u8>, chunk: &[u8]) {
    if chunk.len() < SHORT_LENGTH {
        out.push(chunk.len() as u8);
    } else {
        out.push(0);
        push_length(out, chunk.len() - SHORT_LENGTH);
    }
    out.extend_from_slice(chunk);
}

/// Spans `[start, end)` where every byte repeats the byte eight positions earlier and the
/// run is at least `MIN_RUN` long.
fn runs(raw: &[u8]) -> Vec<(usize, usize)> {
    if raw.len() <= RUN_DISTANCE {
        return Vec::new();
    }
    let mut spans = Vec::new();
    let mut start: Option<usize> = None;
    for at in 0..=raw.len() - RUN_DISTANCE {
        let same = at < raw.len() - RUN_DISTANCE && raw[at + RUN_DISTANCE] == raw[at];
        match (same, start) {
            (true, None) => start = Some(at),
            (false, Some(first)) => {
                if at - first >= MIN_RUN {
                    spans.push((first + RUN_DISTANCE, at + RUN_DISTANCE));
                }
                start = None;
            }
            _ => {}
        }
    }
    spans
}

/// Encode with offset-8 reference blocks for repeated runs, literals elsewhere.
pub fn encode(raw: &[u8]) -> Vec<u8> {
    let limit = raw.len() as i64 - LITERALS_AT_END as i64;
    let mut out = vec![FORMAT << 4 | MIN_REFERENCE as u8];
    let mut position = 0_usize;
    for (run_start, run_end) in runs(raw) {
        let start = run_start.max(position);
        let end = (run_end as i64).min(limit);
        if end - (start as i64) < MIN_REFERENCE as i64 + 1 {
            continue;
        }
        let end = end as usize;
        let mut shift = 0;
        if start > position {
            push_literals(&mut out, &raw[position..start]);
            shift = 2;
        }
        let field = (RUN_DISTANCE >> shift) as u8;
        let length = end - start;
        let extra = MIN_REFERENCE - 1;
        if length - extra <= SHORT_REFERENCE {
            out.push((field & 3) << 6 | 0x10 | (length - extra) as u8);
            out.push(field >> 2);
        } else {
            out.push((field & 3) << 6 | 0x10);
            out.push(field >> 2);
            push_length(&mut out, length - extra - SHORT_LENGTH);
        }
        position = end;
    }
    let tail = &raw[position..];
    push_literals(&mut out, tail);
    out
}

/// One mip level, north-down rows as stored on disk.
struct Level {
    rows: usize,
    columns: usize,
    samples: Vec<u16>,
}

fn level_stack(north_up: &[u16], rows: usize, columns: usize) -> Vec<Level> {
    let mut samples = Vec::with_capacity(north_up.len());
    for row in (0..rows).rev() {
        samples.extend_from_slice(&north_up[row * columns..(row + 1) * columns]);
    }
    let mut levels = vec![Level {
        rows,
        columns,
        samples,
    }];
    while levels
        .last()
        .is_some_and(|l| l.rows > TILE || l.columns > TILE)
    {
        let last = levels.last().unwrap();
        let (next_rows, next_columns) = (last.rows / 2, last.columns / 2);
        let mut next = Vec::with_capacity(next_rows * next_columns);
        for i in 0..next_rows {
            for j in 0..next_columns {
                next.push(last.samples[(2 * i + 1) * last.columns + 2 * j + 1]);
            }
        }
        levels.push(Level {
            rows: next_rows,
            columns: next_columns,
            samples: next,
        });
    }
    levels
}

fn tile_bytes(level: &Level, row_tile: usize, column_tile: usize, sample_bytes: usize) -> Vec<u8> {
    let mut raw = Vec::with_capacity(SIDE * SIDE * sample_bytes);
    for i in 0..SIDE {
        let y = (row_tile * TILE + i)
            .saturating_sub(BORDER)
            .min(level.rows - 1);
        for j in 0..SIDE {
            let x = (column_tile * TILE + j)
                .saturating_sub(BORDER)
                .min(level.columns - 1);
            let value = level.samples[y * level.columns + x];
            if sample_bytes == 2 {
                raw.extend_from_slice(&value.to_le_bytes());
            } else {
                raw.push(value as u8);
            }
        }
    }
    raw
}

/// Compressed tiles of every mip level in file order: their sizes and the joined bytes.
pub fn pack_layer(
    north_up: &[u16],
    (rows, columns): (usize, usize),
    sample_bytes: usize,
) -> (Vec<usize>, Vec<u8>) {
    let levels = level_stack(north_up, rows, columns);
    let mut jobs: Vec<(usize, usize, usize)> = Vec::new();
    for (index, level) in levels.iter().enumerate() {
        for r in 0..level.rows.div_ceil(TILE) {
            for c in 0..level.columns.div_ceil(TILE) {
                jobs.push((index, r, c));
            }
        }
    }
    let packed: Vec<Vec<u8>> = jobs
        .par_iter()
        .map(|&(index, r, c)| encode(&tile_bytes(&levels[index], r, c, sample_bytes)))
        .collect();
    let sizes = packed.iter().map(Vec::len).collect();
    (sizes, packed.concat())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lzav;

    #[test]
    fn encoded_streams_decode_to_the_input() {
        let mut raw: Vec<u8> = (0..300).map(|v| (v * 7 % 251) as u8).collect();
        raw.extend(std::iter::repeat_n(9_u8, 400));
        raw.extend(0..50);
        for len in [0_usize, 1, 8, 9, 20, 100, raw.len()] {
            if len == 0 {
                continue; // an empty input has no valid stream
            }
            let stream = encode(&raw[..len]);
            assert_eq!(lzav::decode(&stream, len).unwrap(), &raw[..len]);
        }
    }

    #[test]
    fn a_small_layer_is_one_tile_per_level() {
        let image: Vec<u16> = (0..100 * 90).map(|v| (v % 65_536) as u16).collect();
        let (sizes, bytes) = pack_layer(&image, (100, 90), 2);
        assert_eq!(sizes.len(), 1);
        assert_eq!(bytes.len(), sizes[0]);
        let big: Vec<u16> = vec![5; 300 * 200];
        let (sizes, _) = pack_layer(&big, (300, 200), 1);
        assert_eq!(sizes.len(), 6 + 2 + 1); // 3 x 2 tiles, then 150 x 100 in 2 x 1, then 75 x 50 in one
    }
}
