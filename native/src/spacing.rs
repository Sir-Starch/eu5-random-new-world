//! Exact synchronous spacing relaxation and sequential bucketed seed acceptance.

use std::collections::HashMap;
use std::time::{Duration, Instant};

const BIG: i64 = 1 << 40;

pub struct Grading {
    original: Vec<i64>,
    land: Vec<bool>,
    values: Vec<i64>,
    next: Vec<i64>,
    width: usize,
    straight: i64,
    diagonal: i64,
}

impl Grading {
    pub fn new(spacing: &[i64], land: &[bool], width: usize, step: i64) -> Self {
        let values = spacing
            .iter()
            .zip(land)
            .map(|(&s, &l)| if l { s } else { BIG })
            .collect();
        Self {
            original: spacing.to_vec(),
            land: land.to_vec(),
            values,
            next: vec![BIG; spacing.len()],
            width,
            straight: step,
            diagonal: step.wrapping_mul(1414).div_euclid(1000),
        }
    }

    fn step(&mut self) -> bool {
        let mut changed = false;
        let rows = self.values.len() / self.width.max(1);
        for (at, &on_land) in self.land.iter().enumerate() {
            if !on_land {
                continue;
            }
            let row = at / self.width;
            let col = at % self.width;
            let mut value = self.values[at];
            for dy in -1_isize..=1 {
                for dx in -1_isize..=1 {
                    if dx == 0 && dy == 0 {
                        continue;
                    }
                    let y = row.checked_add_signed(dy);
                    let x = col.checked_add_signed(dx);
                    let neighbour = match (y, x) {
                        (Some(y), Some(x)) if y < rows && x < self.width => {
                            self.values[y * self.width + x]
                        }
                        _ => BIG,
                    };
                    let cost = if dx == 0 || dy == 0 {
                        self.straight
                    } else {
                        self.diagonal
                    };
                    value = value.min(neighbour.wrapping_add(cost));
                }
            }
            self.next[at] = value;
            changed |= value != self.values[at];
        }
        std::mem::swap(&mut self.values, &mut self.next);
        !changed
    }

    pub fn advance(&mut self, budget: Duration) -> bool {
        let start = Instant::now();
        loop {
            if self.step() {
                return true;
            }
            if start.elapsed() >= budget {
                return false;
            }
        }
    }

    pub fn finish(mut self) -> Vec<i64> {
        for (at, &land) in self.land.iter().enumerate() {
            if !land {
                self.values[at] = self.original[at];
            }
        }
        self.values
    }
}

pub struct Scatter {
    xs: Vec<i64>,
    ys: Vec<i64>,
    radius: Vec<i64>,
    buckets: HashMap<(i64, i64), Vec<usize>>,
    kept: Vec<usize>,
    at: usize,
    smallest: i64,
    widest: i64,
    gap: i64,
}

impl Scatter {
    pub fn new(
        xs: &[i64],
        ys: &[i64],
        radius: &[i64],
        smallest: i64,
        widest: i64,
        gap: i64,
    ) -> Self {
        Self {
            xs: xs.to_vec(),
            ys: ys.to_vec(),
            radius: radius.to_vec(),
            smallest,
            widest,
            gap,
            at: 0,
            buckets: HashMap::new(),
            kept: Vec::new(),
        }
    }

    pub fn advance(&mut self, budget: Duration) -> bool {
        let start = Instant::now();
        while self.at < self.xs.len() {
            let i = self.at;
            let (x, y, r) = (self.xs[i], self.ys[i], self.radius[i]);
            let numerator = i128::from(self.gap) * (i128::from(r) + i128::from(self.widest));
            let reach = -((-numerator).div_euclid(2000 * i128::from(self.smallest))) as i64;
            let (bx, by) = (x.div_euclid(self.smallest), y.div_euclid(self.smallest));
            let mut clear = true;
            'search: for cy in by - reach..=by + reach {
                for cx in bx - reach..=bx + reach {
                    if let Some(bucket) = self.buckets.get(&(cx, cy)) {
                        for &j in bucket {
                            let dx = i128::from(x) - i128::from(self.xs[j]);
                            let dy = i128::from(y) - i128::from(self.ys[j]);
                            let both = i128::from(r) + i128::from(self.radius[j]);
                            if 4_000_000 * (dx * dx + dy * dy)
                                < i128::from(self.gap).pow(2) * both * both
                            {
                                clear = false;
                                break 'search;
                            }
                        }
                    }
                }
            }
            if clear {
                self.buckets.entry((bx, by)).or_default().push(i);
                self.kept.push(i);
            }
            self.at += 1;
            if self.at.is_multiple_of(256) && start.elapsed() >= budget {
                return self.at == self.xs.len();
            }
        }
        true
    }

    pub fn finish(self, columns: i64) -> Vec<i64> {
        self.kept
            .iter()
            .map(|&j| self.ys[j].wrapping_mul(columns).wrapping_add(self.xs[j]))
            .collect()
    }
}
