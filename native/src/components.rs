//! 4-connected equal-label components, equal to `rnw.topology.label_components`.
//!
//! Horizontal runs are joined with a union-find whose root is always the smallest run
//! index, and a component takes the rank of its root among all roots, so the numbering is
//! by the first pixel of each component in raster order on every platform.

fn find(parent: &mut [u32], mut item: u32) -> u32 {
    while parent[item as usize] != item {
        let grandparent = parent[parent[item as usize] as usize];
        parent[item as usize] = grandparent;
        item = grandparent;
    }
    item
}

fn join(parent: &mut [u32], first: u32, second: u32) {
    let (a, b) = (find(parent, first), find(parent, second));
    if a != b {
        parent[a.max(b) as usize] = a.min(b);
    }
}

/// Number the components of `labels`; with `wrap_x` the first and last columns touch.
pub fn label_components(labels: &[i32], (height, width): (usize, usize), wrap_x: bool) -> Vec<i32> {
    if labels.is_empty() {
        return Vec::new();
    }
    let mut run_of = vec![0_i32; labels.len()];
    let mut runs: u32 = 0;
    for row in 0..height {
        for column in 0..width {
            let at = row * width + column;
            if column == 0 || labels[at] != labels[at - 1] {
                runs += 1;
            }
            run_of[at] = (runs - 1) as i32;
        }
    }
    let mut parent: Vec<u32> = (0..runs).collect();
    for row in 1..height {
        for column in 0..width {
            let at = row * width + column;
            if labels[at] == labels[at - width] {
                join(&mut parent, run_of[at - width] as u32, run_of[at] as u32);
            }
        }
    }
    if wrap_x && width > 1 {
        for row in 0..height {
            let (first, last) = (row * width, row * width + width - 1);
            if labels[first] == labels[last] {
                join(&mut parent, run_of[first] as u32, run_of[last] as u32);
            }
        }
    }
    let mut component = vec![0_i32; runs as usize];
    let mut next: i32 = 0;
    for run in 0..runs {
        let root = find(&mut parent, run);
        if root == run {
            component[run as usize] = next;
            next += 1;
        } else {
            component[run as usize] = component[root as usize];
        }
    }
    for slot in &mut run_of {
        *slot = component[*slot as usize];
    }
    run_of
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn components_are_numbered_by_their_first_pixel() {
        // 1 1 2
        // 3 1 2
        // 3 3 2   (label 1 is one component; label 2 one; label 3 one)
        let labels = [1, 1, 2, 3, 1, 2, 3, 3, 2];
        assert_eq!(
            label_components(&labels, (3, 3), false),
            vec![0, 0, 1, 2, 0, 1, 2, 2, 1]
        );
    }

    #[test]
    fn the_seam_joins_the_first_and_last_columns() {
        let labels = [5, 6, 5];
        assert_eq!(label_components(&labels, (1, 3), false), vec![0, 1, 2]);
        assert_eq!(label_components(&labels, (1, 3), true), vec![0, 1, 0]);
    }
}
