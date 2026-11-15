//! The nearest training rows of query rows, exact in integers, with deterministic ties.
//!
//! Equal to `rnw.eu5_biomes._nearest`: the `k` training rows with the smallest squared
//! Euclidean distance to each query row, nearest first, ties by the lower training index.
use rayon::prelude::*;
use std::collections::BinaryHeap;

const LEAF: usize = 16;

struct Tree<'a> {
    rows: &'a [i64],
    width: usize,
    order: Vec<usize>,
    nodes: Vec<Node>,
    low: Vec<i64>,
    high: Vec<i64>,
}

struct Node {
    start: usize,
    end: usize,
    children: Option<(usize, usize)>,
}

impl<'a> Tree<'a> {
    fn new(rows: &'a [i64], width: usize) -> Self {
        let count = rows.len().checked_div(width).unwrap_or(0);
        let mut tree = Tree {
            rows,
            width,
            order: (0..count).collect(),
            nodes: Vec::new(),
            low: Vec::new(),
            high: Vec::new(),
        };
        if count > 0 {
            tree.build(0, count);
        }
        tree
    }

    fn value(&self, row: usize, column: usize) -> i64 {
        self.rows[row * self.width + column]
    }

    /// Adds the node of `order[start..end]` and its subtree; returns its index.
    fn build(&mut self, start: usize, end: usize) -> usize {
        let index = self.nodes.len();
        self.nodes.push(Node {
            start,
            end,
            children: None,
        });
        let mut low = vec![i64::MAX; self.width];
        let mut high = vec![i64::MIN; self.width];
        for &row in &self.order[start..end] {
            for column in 0..self.width {
                let value = self.value(row, column);
                low[column] = low[column].min(value);
                high[column] = high[column].max(value);
            }
        }
        let axis = (0..self.width)
            .max_by_key(|&column| (high[column] - low[column], usize::MAX - column))
            .unwrap_or(0);
        let spread = high.get(axis).zip(low.get(axis)).map_or(0, |(h, l)| h - l);
        self.low.extend_from_slice(&low);
        self.high.extend_from_slice(&high);
        if end - start <= LEAF || spread == 0 {
            return index;
        }
        let middle = start + (end - start) / 2;
        let (rows, width) = (self.rows, self.width);
        self.order[start..end]
            .select_nth_unstable_by_key(middle - start, |&row| (rows[row * width + axis], row));
        let left = self.build(start, middle);
        let right = self.build(middle, end);
        self.nodes[index].children = Some((left, right));
        index
    }

    /// The squared distance from `query` to the box of node `index`, a lower bound of the
    /// distance to every row below it.
    fn bound(&self, index: usize, query: &[i64]) -> i64 {
        let mut total = 0;
        for (column, &value) in query.iter().enumerate() {
            let low = self.low[index * self.width + column];
            let high = self.high[index * self.width + column];
            let gap = if value < low {
                low - value
            } else if value > high {
                value - high
            } else {
                0
            };
            total += gap * gap;
        }
        total
    }

    fn search(&self, index: usize, query: &[i64], k: usize, best: &mut BinaryHeap<(i64, usize)>) {
        let node = &self.nodes[index];
        match node.children {
            None => {
                for &row in &self.order[node.start..node.end] {
                    let mut total = 0;
                    for (column, &value) in query.iter().enumerate() {
                        let gap = self.value(row, column) - value;
                        total += gap * gap;
                    }
                    let candidate = (total, row);
                    if best.len() < k {
                        best.push(candidate);
                    } else if best.peek().is_some_and(|worst| candidate < *worst) {
                        best.pop();
                        best.push(candidate);
                    }
                }
            }
            Some((left, right)) => {
                let (near, far) = {
                    let to_left = self.bound(left, query);
                    let to_right = self.bound(right, query);
                    if to_right < to_left {
                        ((right, to_right), (left, to_left))
                    } else {
                        ((left, to_left), (right, to_right))
                    }
                };
                for (child, distance) in [near, far] {
                    // A row as far as the worst kept may still come first by its index.
                    if best.len() < k || best.peek().is_some_and(|worst| distance <= worst.0) {
                        self.search(child, query, k, best);
                    }
                }
            }
        }
    }
}

/// The `k` nearest of the `train` rows (row-major, `width` columns) to each `query` row,
/// row-major `queries * k` training indices, nearest first, ties by index. `k` is at most the
/// training rows.
pub fn nearest(train: &[i64], query: &[i64], width: usize, k: usize) -> Vec<i64> {
    let tree = Tree::new(train, width);
    if width == 0 || k == 0 || tree.order.is_empty() {
        return vec![0; query.len().checked_div(width).unwrap_or(0) * k];
    }
    let mut out = vec![0i64; query.len() / width * k];
    out.par_chunks_mut(k)
        .zip(query.par_chunks(width))
        .for_each(|(found, row)| {
            let mut best = BinaryHeap::with_capacity(k + 1);
            tree.search(0, row, k, &mut best);
            for (slot, (_, index)) in found.iter_mut().zip(best.into_sorted_vec()) {
                *slot = index as i64;
            }
        });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn brute(train: &[i64], query: &[i64], width: usize, k: usize) -> Vec<i64> {
        let mut out = Vec::new();
        for row in query.chunks(width) {
            let mut all: Vec<(i64, usize)> = train
                .chunks(width)
                .enumerate()
                .map(|(index, other)| {
                    let total = other
                        .iter()
                        .zip(row)
                        .map(|(a, b)| (a - b) * (a - b))
                        .sum::<i64>();
                    (total, index)
                })
                .collect();
            all.sort_unstable();
            out.extend(all[..k].iter().map(|&(_, index)| index as i64));
        }
        out
    }

    #[test]
    fn equals_brute_force_with_ties() {
        let mut state = 12345u64;
        let mut next = || {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            (state % 7) as i64 - 3
        };
        for width in [1usize, 2, 4] {
            let train: Vec<i64> = (0..300 * width).map(|_| next()).collect();
            let query: Vec<i64> = (0..60 * width).map(|_| next()).collect();
            for k in [1usize, 5, 32] {
                assert_eq!(
                    nearest(&train, &query, width, k),
                    brute(&train, &query, width, k)
                );
            }
        }
    }
}
