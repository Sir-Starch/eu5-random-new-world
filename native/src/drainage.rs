//! Priority-flood drainage tree of a coarse land grid, equal to `rnw.rivers.drainage`.

use crate::hash::hash_point;
use std::cmp::Reverse;
use std::collections::BinaryHeap;

const NOISE_BITS: u32 = 16;

/// Downstream cell (-1 for none) and accumulated rain of each cell, in raster order.
pub struct Tree {
    pub parent: Vec<i64>,
    pub flow: Vec<i64>,
}

/// Priority flood from all water over 8-neighbours, then rain accumulated downstream.
///
/// Cells are taken lowest filled height first; equal heights go by hashed noise and then
/// by index, so drainage across flats wanders instead of running straight.
pub fn drainage(
    land: &[bool],
    height: &[i64],
    rain: &[i64],
    (rows, columns): (usize, usize),
    key: u64,
) -> Tree {
    let width = columns + 2;
    let size = (rows + 2) * width;
    let at = |row: usize, column: usize| (row + 1) * width + column + 1;
    let mut is_land = vec![false; size];
    let mut level = vec![0_i64; size];
    let mut flow = vec![0_i64; size];
    let mut border = vec![true; size];
    for row in 0..rows {
        for column in 0..columns {
            let (inner, outer) = (row * columns + column, at(row, column));
            is_land[outer] = land[inner];
            level[outer] = height[inner].max(0);
            flow[outer] = rain[inner].max(0);
            border[outer] = false;
        }
    }
    let ties: Vec<u32> = (0..size)
        .map(|index| {
            (hash_point(key, (index % width) as i64, (index / width) as i64) >> (64 - NOISE_BITS))
                as u32
        })
        .collect();
    let mut closed = border.clone();
    let mut parent = vec![-1_i64; size];
    let mut filled = vec![0_i64; size];
    let offsets: [isize; 8] = [
        -(width as isize) - 1,
        -(width as isize),
        -(width as isize) + 1,
        -1,
        1,
        width as isize - 1,
        width as isize,
        width as isize + 1,
    ];
    let mut heap: BinaryHeap<Reverse<(i64, u32, u32)>> = BinaryHeap::new();
    for index in 0..size {
        if !is_land[index] && !border[index] {
            closed[index] = true;
            heap.push(Reverse((0, ties[index], index as u32)));
        }
    }
    let mut order: Vec<u32> = Vec::new();
    while let Some(Reverse((_, _, popped))) = heap.pop() {
        let index = popped as usize;
        let base = filled[index];
        if is_land[index] {
            order.push(popped);
        }
        for offset in offsets {
            let other = (index as isize + offset) as usize;
            if closed[other] || !is_land[other] {
                continue;
            }
            closed[other] = true;
            parent[other] = index as i64;
            let value = level[other].max(base);
            filled[other] = value;
            heap.push(Reverse((value, ties[other], other as u32)));
        }
    }
    for &index in order.iter().rev() {
        let up = parent[index as usize] as usize;
        flow[up] += flow[index as usize];
    }
    let mut tree = Tree {
        parent: Vec::with_capacity(rows * columns),
        flow: Vec::with_capacity(rows * columns),
    };
    for row in 0..rows {
        for column in 0..columns {
            let outer = at(row, column);
            let up = parent[outer];
            tree.parent.push(if up >= 0 {
                let (up_row, up_column) = (up as usize / width, up as usize % width);
                ((up_row - 1) * columns + up_column - 1) as i64
            } else {
                -1
            });
            tree.flow.push(flow[outer]);
        }
    }
    tree
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn water_drains_downhill_to_the_sea() {
        // one row: sea, land at heights 5, 3, 9 (a ridge at the end), rain 1 each
        let land = [false, true, true, true];
        let height = [0, 5, 3, 9];
        let rain = [0, 1, 1, 1];
        let tree = drainage(&land, &height, &rain, (1, 4), 1);
        assert_eq!(tree.parent[0], -1);
        // the flood reaches cell 1 from the sea, then 2 from 1, then 3 from 2
        assert_eq!(tree.parent[1..], [0, 1, 2]);
        assert_eq!(tree.flow, vec![3, 3, 2, 1]);
    }
}
