//! The original integer wind scans, on independent rows or columns.
//! Python retains latitude weights, relief smoothing and bounded strip checkpoints.

use rayon::prelude::*;

const PERMILLE: i64 = 1000;
const SATURATED: i64 = 1 << 16;

/// NumPy's signed int64 floor division, including its zero and MIN/-1 values.
#[inline]
fn floor(n: i64, d: i64) -> i64 {
    if d == 0 {
        return 0;
    }
    let q = n.wrapping_div(d);
    let r = n.wrapping_rem(d);
    if r != 0 && (r < 0) != (d < 0) {
        q.wrapping_sub(1)
    } else {
        q
    }
}

#[derive(Clone, Copy)]
pub struct Rates(pub i64, pub i64, pub i64);

impl Rates {
    #[inline]
    fn loss(self, moisture: i64, here: i64, previous: i64) -> i64 {
        let rise = here.wrapping_sub(previous).max(0);
        floor(moisture, self.0)
            .wrapping_add(floor(moisture.wrapping_mul(rise), self.2))
            .min(moisture)
    }

    #[inline]
    fn next(self, moisture: i64, target: i64, loss: i64, ocean: bool) -> i64 {
        if ocean {
            moisture.wrapping_add(floor(target.wrapping_sub(moisture), self.1))
        } else {
            moisture.wrapping_sub(loss)
        }
    }
}

pub fn sea_run(sea: &[bool], width: usize, limit: i64, laps: usize) -> Vec<i64> {
    let mut out = vec![0; sea.len()];
    out.par_chunks_mut(width)
        .zip(sea.par_chunks(width))
        .for_each(|(line, flags)| {
            let mut run = limit;
            for lap in 0..laps {
                for (x, &ocean) in flags.iter().enumerate() {
                    run = if ocean {
                        run.wrapping_add(1).min(limit)
                    } else {
                        0
                    };
                    if lap + 1 == laps {
                        line[x] = run;
                    }
                }
            }
        });
    out
}

pub fn scan(sea: &[bool], height: &[i64], width: usize, rates: Rates, laps: usize) -> Vec<i64> {
    let mut out = vec![0; sea.len()];
    out.par_chunks_mut(width)
        .zip(sea.par_chunks(width))
        .zip(height.par_chunks(width))
        .for_each(|((line, flags), relief)| {
            let mut moisture = SATURATED;
            let mut previous = relief[width - 1];
            for lap in 0..laps {
                for x in 0..width {
                    let loss = rates.loss(moisture, relief[x], previous);
                    moisture = rates.next(moisture, SATURATED, loss, flags[x]);
                    if lap + 1 == laps && !flags[x] {
                        line[x] = loss;
                    }
                    previous = relief[x];
                }
            }
        });
    out
}

pub struct Sources<'a> {
    pub shape: (usize, usize),
    pub sea: &'a [bool],
    pub off_west: &'a [bool],
    pub off_east: &'a [bool],
    pub capacity: &'a [i64],
    pub cold: &'a [i64],
    pub warm: &'a [i64],
}

impl Sources<'_> {
    #[inline]
    fn at(&self, season: usize, row: usize, column: usize) -> i64 {
        let at = row * self.shape.1 + column;
        let band = season * self.shape.0 + row;
        if self.off_east[at] {
            self.warm[band]
        } else if self.off_west[at] {
            self.cold[band]
        } else {
            self.capacity[band]
        }
    }
}

pub fn zonal(
    sources: &Sources<'_>,
    height: &[i64],
    weights: (&[i64], &[i64], &[i64]),
    rates: Rates,
    laps: usize,
) -> Vec<i64> {
    let (rows, columns) = sources.shape;
    let (efficiency, west, east) = weights;
    let mut out = vec![0_i64; 2 * rows * columns];
    out.par_chunks_mut(columns)
        .enumerate()
        .for_each(|(band, line)| {
            let (season, row) = (band / rows, band % rows);
            for direction in 0..2 {
                let last = if direction == 0 { columns - 1 } else { 0 };
                let mut moisture = sources.at(season, row, last);
                let mut previous = height[row * columns + last];
                let weight = if direction == 0 {
                    west[band]
                } else {
                    east[band]
                };
                for lap in 0..laps {
                    for step in 0..columns {
                        let column = if direction == 0 {
                            step
                        } else {
                            columns - 1 - step
                        };
                        let at = row * columns + column;
                        let loss = rates.loss(moisture, height[at], previous);
                        moisture = rates.next(
                            moisture,
                            sources.at(season, row, column),
                            loss,
                            sources.sea[at],
                        );
                        if lap + 1 == laps && !sources.sea[at] {
                            let fallen = floor(loss.wrapping_mul(efficiency[band]), PERMILLE)
                                .wrapping_mul(weight);
                            line[column] = line[column].wrapping_add(fallen);
                        }
                        previous = height[at];
                    }
                }
            }
        });
    out
}

/// Column-major output within each season; Python transposes before the original addition.
pub fn inflow(
    sources: &Sources<'_>,
    height: &[i64],
    weights: (&[i64], &[i64]),
    rates: Rates,
    equator: i64,
) -> Vec<i64> {
    let (rows, columns) = sources.shape;
    let (efficiency, weight) = weights;
    let start = equator.clamp(0, rows as i64 - 1) as usize;
    let mut out = vec![0_i64; 2 * rows * columns];
    out.par_chunks_mut(rows)
        .enumerate()
        .for_each(|(band, line)| {
            let (season, column) = (band / columns, band % columns);
            for direction in 0..2 {
                let mut moisture = sources.at(season, start, column);
                let mut previous = height[start * columns + column];
                let count = if direction == 0 {
                    start + 1
                } else {
                    rows - start
                };
                for step in 0..count {
                    let row = if direction == 0 {
                        start - step
                    } else {
                        start + step
                    };
                    let at = row * columns + column;
                    let climate = season * rows + row;
                    let loss = rates.loss(moisture, height[at], previous);
                    moisture = rates.next(
                        moisture,
                        sources.at(season, row, column),
                        loss,
                        sources.sea[at],
                    );
                    if !sources.sea[at] {
                        let fallen = floor(loss.wrapping_mul(efficiency[climate]), PERMILLE)
                            .wrapping_mul(weight[climate]);
                        line[row] = line[row].wrapping_add(fallen);
                    }
                    previous = height[at];
                }
            }
        });
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn floor_matches_signed_numpy_integer_cases() {
        for (n, d, answer) in [
            (-7, 3, -3),
            (7, -3, -3),
            (-7, -3, 2),
            (i64::MIN, -1, i64::MIN),
            (1, 0, 0),
        ] {
            assert_eq!(floor(n, d), answer);
        }
    }

    #[test]
    fn cylindrical_sea_runs_keep_the_second_lap() {
        assert_eq!(
            sea_run(&[true, true, false, true], 4, 5, 2),
            vec![2, 3, 0, 1]
        );
        assert_eq!(sea_run(&[true; 4], 4, 5, 2), vec![5; 4]);
    }

    #[test]
    fn wind_outputs_do_not_depend_on_worker_count() {
        let (rows, columns) = (17, 29);
        let sea: Vec<bool> = (0..rows * columns).map(|at| at % 11 < 4).collect();
        let height: Vec<i64> = (0..sea.len()).map(|at| (at * 301 % 60000) as i64).collect();
        let off_west: Vec<bool> = (0..sea.len()).map(|at| at % 7 == 1).collect();
        let off_east: Vec<bool> = (0..sea.len()).map(|at| at % 7 == 6).collect();
        let capacity = vec![60000; 2 * rows];
        let cold = vec![30000; 2 * rows];
        let warm = vec![65000; 2 * rows];
        let efficiency = vec![750; 2 * rows];
        let west = vec![350; 2 * rows];
        let east = vec![650; 2 * rows];
        let rates = Rates(23, 7, 40000);
        let source = Sources {
            shape: (rows, columns),
            sea: &sea,
            off_west: &off_west,
            off_east: &off_east,
            capacity: &capacity,
            cold: &cold,
            warm: &warm,
        };
        let run = || {
            (
                sea_run(&sea, columns, 12, 2),
                scan(&sea, &height, columns, rates, 2),
                zonal(&source, &height, (&efficiency, &west, &east), rates, 2),
                inflow(&source, &height, (&efficiency, &west), rates, 5),
            )
        };
        let single = rayon::ThreadPoolBuilder::new()
            .num_threads(1)
            .build()
            .unwrap()
            .install(run);
        let many = rayon::ThreadPoolBuilder::new()
            .num_threads(4)
            .build()
            .unwrap()
            .install(run);
        assert_eq!(single, many);
    }
}
