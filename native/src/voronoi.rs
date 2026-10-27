//! Euclidean sea-cell partition, with deterministic ties.
use rayon::prelude::*;

#[derive(Clone, Copy)]
struct Site {
    row: i64,
    column: i64,
    label: i32,
}

struct Node {
    site: Site,
    axis: usize,
    left: Option<Box<Node>>,
    right: Option<Box<Node>>,
}

fn build(sites: &mut [Site], depth: usize) -> Option<Box<Node>> {
    if sites.is_empty() {
        return None;
    }
    let axis = depth % 2;
    let middle = sites.len() / 2;
    sites.select_nth_unstable_by_key(middle, |s| {
        if axis == 0 {
            (s.row, s.column, s.label)
        } else {
            (s.column, s.row, s.label)
        }
    });
    let (left, rest) = sites.split_at_mut(middle);
    let (site, right) = rest.split_first_mut().unwrap();
    Some(Box::new(Node {
        site: *site,
        axis,
        left: build(left, depth + 1),
        right: build(right, depth + 1),
    }))
}

fn nearest(node: &Node, row: i64, column: i64, best: &mut (i64, i32)) {
    let dr = row - node.site.row;
    let dc = column - node.site.column;
    *best = (*best).min((dr * dr + dc * dc, node.site.label));
    let delta = if node.axis == 0 { dr } else { dc };
    let (near, far) = if delta <= 0 {
        (&node.left, &node.right)
    } else {
        (&node.right, &node.left)
    };
    if let Some(child) = near {
        nearest(child, row, column, best);
    }
    if delta * delta <= best.0
        && let Some(child) = far
    {
        nearest(child, row, column, best);
    }
}

/// Assign every masked pixel to its nearest seed, measured in squared Euclidean pixels.
pub fn partition(mask: &[bool], seeds: &[i32], width: usize) -> Vec<i32> {
    if width == 0 {
        return Vec::new();
    }
    let mut sites: Vec<Site> = seeds
        .iter()
        .enumerate()
        .filter_map(|(i, &label)| {
            (label >= 0).then_some(Site {
                row: (i / width) as i64,
                column: (i % width) as i64,
                label,
            })
        })
        .collect();
    let tree = build(&mut sites, 0);
    let mut out = vec![-1; mask.len()];
    if let Some(root) = tree {
        out.par_chunks_mut(width)
            .zip(mask.par_chunks(width))
            .enumerate()
            .for_each(|(row, (line, flags))| {
                for (column, (slot, &inside)) in line.iter_mut().zip(flags).enumerate() {
                    if inside {
                        let mut best = (i64::MAX, i32::MAX);
                        nearest(&root, row as i64, column as i64, &mut best);
                        *slot = best.1;
                    }
                }
            });
    }
    out
}
