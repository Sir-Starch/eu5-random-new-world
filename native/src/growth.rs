//! Frontier growth with the reference's directional claims and weighted round clock.
//! Buffers survive rounds; callbacks see only Rust-owned state, between bounded batches.

use std::time::{Duration, Instant};

pub struct Growth {
    allowed: Vec<bool>,
    labels: Vec<i32>,
    frontier: Vec<usize>,
    pending: Vec<usize>,
    claimed: Vec<usize>,
    width: usize,
    speed: Option<Vec<i64>>,
    fastest: i64,
    round: i64,
}

impl Growth {
    pub fn new(
        allowed: &[bool],
        seeds: &[i32],
        width: usize,
        speed: Option<&[i64]>,
    ) -> Result<Self, &'static str> {
        let labels: Vec<i32> = allowed
            .iter()
            .zip(seeds)
            .map(|(&allowed, &label)| if allowed { label } else { -1 })
            .collect();
        if let Some(speed) = speed
            && (speed.iter().any(|&s| s <= 0)
                || labels.iter().any(|&s| s >= 0 && s as usize >= speed.len()))
        {
            return Err("growth needs a positive speed for every seed label");
        }
        let frontier = labels
            .iter()
            .enumerate()
            .filter_map(|(at, &label)| (label >= 0).then_some(at))
            .collect();
        Ok(Self {
            allowed: allowed.to_vec(),
            labels,
            frontier,
            pending: Vec::new(),
            claimed: Vec::new(),
            width,
            speed: speed.map(<[i64]>::to_vec),
            fastest: speed.and_then(|s| s.iter().max().copied()).unwrap_or(1),
            round: 0,
        })
    }

    fn step(&mut self) {
        self.round = self.round.wrapping_add(1);
        self.pending.clear();
        self.claimed.clear();
        if let Some(speed) = &self.speed {
            self.frontier.retain(|&at| {
                let pace = speed[self.labels[at] as usize];
                let advance = self.round.wrapping_mul(pace).div_euclid(self.fastest)
                    > (self.round - 1).wrapping_mul(pace).div_euclid(self.fastest);
                if !advance {
                    self.pending.push(at);
                }
                advance
            });
        }
        // The source code claims south, east, west, north, irrespective of its old docstring.
        // In one direction each target is unique, so assignments equal NumPy's vector write.
        let width = self.width;
        for direction in 0..4 {
            for &source in &self.frontier {
                let target = match direction {
                    0 if source + width < self.labels.len() => source + width,
                    1 if source % width + 1 < width => source + 1,
                    2 if source % width > 0 => source - 1,
                    3 if source >= width => source - width,
                    _ => continue,
                };
                if self.allowed[target] && self.labels[target] < 0 {
                    self.labels[target] = self.labels[source];
                    self.claimed.push(target);
                }
            }
        }
        self.claimed.sort_unstable();
        self.frontier.clear();
        self.frontier.append(&mut self.pending);
        self.frontier.append(&mut self.claimed);
    }

    /// Return true when done; release the GIL for at most this batch (plus one round).
    pub fn advance(&mut self, budget: Duration) -> bool {
        let start = Instant::now();
        while !self.frontier.is_empty() {
            self.step();
            if start.elapsed() >= budget {
                return self.frontier.is_empty();
            }
        }
        true
    }

    pub fn finish(self) -> Vec<i32> {
        self.labels
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn direction_priority_and_barriers() {
        let mut growth = Growth::new(&[true; 3], &[0, -1, 1], 3, None).unwrap();
        assert!(growth.advance(Duration::from_secs(1)));
        assert_eq!(growth.finish(), vec![0, 0, 1]);
        let mut growth = Growth::new(&[true, false, true], &[0, -1, -1], 3, None).unwrap();
        assert!(growth.advance(Duration::from_secs(1)));
        assert_eq!(growth.finish(), vec![0, -1, -1]);
    }
}
