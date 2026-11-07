//! Integer-exact hot kernels of the Random New World generator ([ADR 0005]).
//!
//! Every function equals its Python reference in `tests/reference/` bit for bit.

pub mod cells;
pub mod components;
pub mod distance;
pub mod drainage;
pub mod hash;
pub mod lzav;
pub mod mountains;
pub mod noise;
pub mod objects;
pub mod raster;
pub mod slots;
pub mod terrain;
pub mod tiles;
pub mod voronoi;

use numpy::{
    IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3,
};
use pyo3::prelude::*;

pyo3::create_exception!(_native, LzavError, pyo3::exceptions::PyValueError);

fn object_fault(fault: objects::Fault) -> PyErr {
    let message = match fault {
        objects::Fault::Label => "a label has no class or a key is negative",
        objects::Fault::Shape => "the rasters do not fit together",
    };
    pyo3::exceptions::PyValueError::new_err(message)
}

/// A row-major vector as a two-dimensional array without copying.
fn shaped<T: numpy::Element>(
    py: Python<'_>,
    (height, width): (usize, usize),
    values: Vec<T>,
) -> PyResult<Bound<'_, PyArray2<T>>> {
    let array = numpy::ndarray::Array2::from_shape_vec((height, width), values)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    Ok(array.into_pyarray(py))
}

#[pymodule]
mod _native {
    use super::*;
    use pyo3::types::PyBytes;

    #[pymodule_export]
    use super::LzavError;

    /// Size the thread pool of the kernels; returns its size. Only the first call before a
    /// kernel has run can change it, later calls report the size in force.
    #[pyfunction]
    fn configure_threads(threads: usize) -> usize {
        let _ = rayon::ThreadPoolBuilder::new()
            .num_threads(threads.max(1))
            .build_global();
        rayon::current_num_threads()
    }

    /// Decode a format-3 LZAV stream that expands to exactly `size` bytes.
    #[pyfunction]
    fn lzav_decode<'py>(
        py: Python<'py>,
        data: &[u8],
        size: usize,
    ) -> PyResult<Bound<'py, PyBytes>> {
        let out = py
            .detach(|| lzav::decode(data, size))
            .map_err(|fault| LzavError::new_err(fault.to_string()))?;
        Ok(PyBytes::new(py, &out))
    }

    /// Fractal noise of a window of the world, row-major `height * width` values.
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn fractal_window<'py>(
        py: Python<'py>,
        key: u64,
        x0: i64,
        y0: i64,
        width: usize,
        height: usize,
        period: i64,
        octaves: u32,
        persistence_permille: i64,
    ) -> Bound<'py, PyArray1<i64>> {
        py.detach(|| {
            noise::fractal_window(
                key,
                (x0, y0),
                (width, height),
                period,
                octaves,
                persistence_permille,
            )
        })
        .into_pyarray(py)
    }

    /// One octave of value noise of a window of the world, row-major.
    #[pyfunction]
    fn value_window<'py>(
        py: Python<'py>,
        key: u64,
        x0: i64,
        y0: i64,
        width: usize,
        height: usize,
        period: i64,
    ) -> Bound<'py, PyArray1<i64>> {
        py.detach(|| noise::value_window(key, (x0, y0), (width, height), period))
            .into_pyarray(py)
    }

    /// Rotated-lattice fractal noise at sub-pixel coordinates (1/16 pixel).
    #[pyfunction]
    fn fractal_at<'py>(
        py: Python<'py>,
        key: u64,
        xs: PyReadonlyArray1<'py, i64>,
        ys: PyReadonlyArray1<'py, i64>,
        period: i64,
        octaves: u32,
        persistence_permille: i64,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let (xs, ys) = (xs.as_slice()?, ys.as_slice()?);
        Ok(py
            .detach(|| noise::fractal_at(key, xs, ys, period, octaves, persistence_permille))
            .into_pyarray(py))
    }

    /// Step distance to the nearest source pixel, capped at `limit`.
    #[pyfunction]
    #[pyo3(signature = (sources, limit, octagonal, wrap_x=false))]
    fn distance_from<'py>(
        py: Python<'py>,
        sources: PyReadonlyArray2<'py, bool>,
        limit: i32,
        octagonal: bool,
        wrap_x: bool,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = sources.as_array().dim();
        let flags = sources.as_slice()?;
        let out =
            py.detach(|| distance::distance_from_wrapped(flags, shape, limit, octagonal, wrap_x));
        shaped(py, shape, out)
    }

    /// Exact Euclidean distance in eighths of a pixel, capped at `limit` pixels.
    #[pyfunction]
    fn euclidean_distance<'py>(
        py: Python<'py>,
        sources: PyReadonlyArray2<'py, bool>,
        limit: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = sources.as_array().dim();
        let flags = sources.as_slice()?;
        let out = py
            .detach(|| distance::euclidean_distance(flags, shape, limit))
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("limit is too large"))?;
        shaped(py, shape, out)
    }

    /// Spread the labels of `sources` pixels outwards by up to `limit` 4-steps.
    #[pyfunction]
    fn nearest_label<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        sources: PyReadonlyArray2<'py, bool>,
        limit: usize,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = sources.as_array().dim();
        let (labels, flags) = (labels.as_slice()?, sources.as_slice()?);
        let out = py.detach(|| distance::nearest_label(labels, flags, shape, limit));
        shaped(py, shape, out)
    }

    /// Assign masked pixels to their closest seed in Euclidean distance.
    #[pyfunction]
    fn sea_voronoi<'py>(
        py: Python<'py>,
        mask: PyReadonlyArray2<'py, bool>,
        seeds: PyReadonlyArray2<'py, i32>,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = mask.as_array().dim();
        if seeds.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "raster shapes differ",
            ));
        }
        let (flags, sites) = (mask.as_slice()?, seeds.as_slice()?);
        let out = py.detach(|| voronoi::partition(flags, sites, shape.1));
        shaped(py, shape, out)
    }

    /// Bilinear upsampling of a grid sampled every `step` pixels.
    #[pyfunction]
    fn upsample<'py>(
        py: Python<'py>,
        coarse: PyReadonlyArray2<'py, i64>,
        step: usize,
        height: usize,
        width: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let (rows, columns) = coarse.as_array().dim();
        if step == 0
            || rows < height.saturating_sub(1) / step + 2
            || columns < width.saturating_sub(1) / step + 2
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the grid is too small",
            ));
        }
        let samples = coarse.as_slice()?;
        let out = py.detach(|| raster::upsample(samples, columns, step, (height, width)));
        shaped(py, (height, width), out)
    }

    /// Mean of each `step` x `step` block, edge blocks replicated.
    #[pyfunction]
    fn block_mean<'py>(
        py: Python<'py>,
        values: PyReadonlyArray2<'py, i64>,
        step: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = values.as_array().dim();
        if step == 0 || shape.0 == 0 || shape.1 == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "empty grid or step",
            ));
        }
        let samples = values.as_slice()?;
        let (rows, columns, out) = py.detach(|| raster::block_mean(samples, shape, step));
        shaped(py, (rows, columns), out)
    }

    /// Separable integer box blur with edge replication.
    #[pyfunction]
    fn box_blur<'py>(
        py: Python<'py>,
        values: PyReadonlyArray2<'py, i64>,
        radius: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = values.as_array().dim();
        if shape.0 == 0 || shape.1 == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err("empty grid"));
        }
        let samples = values.as_slice()?;
        let out = py.detach(|| raster::box_blur(samples, shape, radius));
        shaped(py, shape, out)
    }

    /// Row, column, fine key and coarse key of every canvas material pixel.
    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn canvas_pixels<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        materials: PyReadonlyArray2<'py, u8>,
        canvas: PyReadonlyArray2<'py, bool>,
        fine_classes: PyReadonlyArray1<'py, i64>,
        coarse_classes: PyReadonlyArray1<'py, i64>,
    ) -> PyResult<(
        Bound<'py, PyArray1<u32>>,
        Bound<'py, PyArray1<u32>>,
        Bound<'py, PyArray1<u32>>,
        Bound<'py, PyArray1<u32>>,
    )> {
        let shape = labels.as_array().dim();
        let raster = objects::Raster {
            labels: labels.as_slice()?,
            materials: materials.as_slice()?,
            shape,
        };
        let (flags, fine, coarse) = (
            canvas.as_slice()?,
            fine_classes.as_slice()?,
            coarse_classes.as_slice()?,
        );
        let pixels = py
            .detach(|| objects::canvas_pixels(&raster, flags, fine, coarse))
            .map_err(object_fault)?;
        Ok((
            pixels.rows.into_pyarray(py),
            pixels.columns.into_pyarray(py),
            pixels.fine.into_pyarray(py),
            pixels.coarse.into_pyarray(py),
        ))
    }

    /// Material pixels per key among the pixels whose label is in `mask`.
    #[pyfunction]
    fn pixel_counts<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        materials: PyReadonlyArray2<'py, u8>,
        table: PyReadonlyArray1<'py, i64>,
        mask: PyReadonlyArray1<'py, bool>,
        keys: usize,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let shape = labels.as_array().dim();
        let raster = objects::Raster {
            labels: labels.as_slice()?,
            materials: materials.as_slice()?,
            shape,
        };
        let (table, mask) = (table.as_slice()?, mask.as_slice()?);
        let counts = py
            .detach(|| objects::pixel_counts(&raster, table, mask, keys))
            .map_err(object_fault)?;
        Ok(counts.into_pyarray(py))
    }

    /// New instance records for canvas pixels; `(count, 10)` floats in pixel order.
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn sample_instances<'py>(
        py: Python<'py>,
        rows: PyReadonlyArray1<'py, u32>,
        columns: PyReadonlyArray1<'py, u32>,
        fine_keys: PyReadonlyArray1<'py, u32>,
        coarse_keys: PyReadonlyArray1<'py, u32>,
        use_fine: PyReadonlyArray1<'py, bool>,
        fine: PyReadonlyArray1<'py, i64>,
        coarse: PyReadonlyArray1<'py, i64>,
        donors: PyReadonlyArray2<'py, f32>,
        key: u64,
        map_rows: i64,
    ) -> PyResult<Bound<'py, PyArray2<f32>>> {
        let lengths = [
            rows.len()?,
            columns.len()?,
            fine_keys.len()?,
            coarse_keys.len()?,
        ];
        if lengths.iter().any(|&n| n != lengths[0]) || use_fine.len()? != fine.len()? {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "mismatched lengths",
            ));
        }
        if donors.as_array().dim().1 != 10 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "records have ten floats",
            ));
        }
        let pixels = objects::PixelView {
            rows: rows.as_slice()?,
            columns: columns.as_slice()?,
            fine: fine_keys.as_slice()?,
            coarse: coarse_keys.as_slice()?,
        };
        let density = objects::Densities {
            use_fine: use_fine.as_slice()?,
            fine: fine.as_slice()?,
            coarse: coarse.as_slice()?,
        };
        let donors = donors.as_slice()?;
        let out = py.detach(|| objects::sample_instances(pixels, &density, donors, key, map_rows));
        shaped(py, (out.len() / 10, 10), out)
    }

    /// `sample_instances` of several instance sets over the same pixels in one call: the
    /// records of each set in order, each the same as a call of its own.
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn sample_instance_sets<'py>(
        py: Python<'py>,
        rows: PyReadonlyArray1<'py, u32>,
        columns: PyReadonlyArray1<'py, u32>,
        fine_keys: PyReadonlyArray1<'py, u32>,
        coarse_keys: PyReadonlyArray1<'py, u32>,
        use_fine: PyReadonlyArray1<'py, bool>,
        fines: Vec<PyReadonlyArray1<'py, i64>>,
        coarses: Vec<PyReadonlyArray1<'py, i64>>,
        donors: Vec<PyReadonlyArray2<'py, f32>>,
        keys: Vec<u64>,
        map_rows: i64,
    ) -> PyResult<Vec<Bound<'py, PyArray2<f32>>>> {
        let lengths = [
            rows.len()?,
            columns.len()?,
            fine_keys.len()?,
            coarse_keys.len()?,
        ];
        let sets = keys.len();
        if lengths.iter().any(|&n| n != lengths[0])
            || fines.len() != sets
            || coarses.len() != sets
            || donors.len() != sets
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "mismatched lengths",
            ));
        }
        let use_fine_values = use_fine.as_slice()?;
        let mut tables: Vec<(&[i64], &[i64], &[f32])> = Vec::with_capacity(sets);
        for ((fine, coarse), records) in fines.iter().zip(&coarses).zip(&donors) {
            if fine.len()? != use_fine_values.len() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "mismatched lengths",
                ));
            }
            if records.as_array().dim().1 != 10 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "records have ten floats",
                ));
            }
            tables.push((fine.as_slice()?, coarse.as_slice()?, records.as_slice()?));
        }
        let (rows, columns) = (rows.as_slice()?, columns.as_slice()?);
        let (fine_keys, coarse_keys) = (fine_keys.as_slice()?, coarse_keys.as_slice()?);
        let found: Vec<Vec<f32>> = py.detach(|| {
            tables
                .iter()
                .zip(&keys)
                .map(|(&(fine, coarse, records), &key)| {
                    let pixels = objects::PixelView {
                        rows,
                        columns,
                        fine: fine_keys,
                        coarse: coarse_keys,
                    };
                    let density = objects::Densities {
                        use_fine: use_fine_values,
                        fine,
                        coarse,
                    };
                    objects::sample_instances(pixels, &density, records, key, map_rows)
                })
                .collect()
        });
        found
            .into_iter()
            .map(|out| shaped(py, (out.len() / 10, 10), out))
            .collect()
    }

    /// Sorted unique touching label pairs, packed as `low << 32 | high`.
    #[pyfunction]
    fn adjacency_pairs<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        wrap_x: bool,
        diagonal: bool,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let shape = labels.as_array().dim();
        let values = labels.as_slice()?;
        let out = py.detach(|| cells::adjacency_pairs(values, shape, wrap_x, diagonal));
        Ok(out.into_pyarray(py))
    }

    /// Sorted unique 4-neighbour label pairs and the number of contacts of each.
    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn adjacency_lengths<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray1<i64>>)> {
        let shape = labels.as_array().dim();
        let values = labels.as_slice()?;
        let (pairs, lengths) = py.detach(|| cells::adjacency_lengths(values, shape));
        Ok((pairs.into_pyarray(py), lengths.into_pyarray(py)))
    }

    /// Pixels, row, column, elevation and elevation square sums of each of `count` cells,
    /// as five rows of `count`.
    #[pyfunction]
    fn cell_sums<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        elevation: PyReadonlyArray2<'py, i32>,
        count: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = labels.as_array().dim();
        if elevation.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the labels and the elevation differ in shape",
            ));
        }
        let (values, heights) = (labels.as_slice()?, elevation.as_slice()?);
        let out = py
            .detach(|| cells::cell_sums(values, heights, shape, count))
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("a label is past the count"))?;
        shaped(py, (5, count), out)
    }

    /// Number the 4-connected equal-label components in raster order of first pixel.
    #[pyfunction]
    fn label_components<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        wrap_x: bool,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = labels.as_array().dim();
        let values = labels.as_slice()?;
        if i32::try_from(values.len()).is_err() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "more pixels than 32-bit component numbers",
            ));
        }
        let out = py.detach(|| components::label_components(values, shape, wrap_x));
        shaped(py, shape, out)
    }

    /// Priority-flood drainage tree of a coarse land grid: (downstream cell, catchment).
    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn drainage<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        height: PyReadonlyArray2<'py, i64>,
        rain: PyReadonlyArray2<'py, i64>,
        key: u64,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray1<i64>>)> {
        let shape = land.as_array().dim();
        if height.as_array().dim() != shape || rain.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err("mismatched grids"));
        }
        let (land, height, rain) = (land.as_slice()?, height.as_slice()?, rain.as_slice()?);
        let tree = py.detach(|| crate::drainage::drainage(land, height, rain, shape, key));
        Ok((tree.parent.into_pyarray(py), tree.flow.into_pyarray(py)))
    }

    /// Per cell, the interior point `(row, column)` (see `raster::interior_points`), as `(count, 2)`.
    #[pyfunction]
    fn interior_points<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        land: PyReadonlyArray1<'py, bool>,
        interior_limit: i32,
        shore_limit: i32,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = labels.as_array().dim();
        let (labels, land) = (labels.as_slice()?, land.as_slice()?);
        let count = land.len();
        if shape.0 == 0
            || shape.1 == 0
            || labels
                .iter()
                .any(|&label| usize::try_from(label).is_ok_and(|label| label >= count))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "an empty raster or a label that is not below the count",
            ));
        }
        let out = py
            .detach(|| raster::interior_points(labels, shape, land, (interior_limit, shore_limit)));
        shaped(py, (count, 2), out)
    }

    /// Terrain material slot per pixel of a decal window (`u8`, 255 = none).
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn synthesize_slots<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        land: PyReadonlyArray2<'py, bool>,
        rivers: PyReadonlyArray2<'py, bool>,
        tables: Vec<PyReadonlyArray1<'py, i64>>,
        water: PyReadonlyArray1<'py, bool>,
        keys: [u64; 5],
        periods: [i64; 3],
        quantiles: Vec<PyReadonlyArray1<'py, i64>>,
        x0: i64,
        y0: i64,
        remap: PyReadonlyArray1<'py, i64>,
        core: (usize, usize, usize, usize),
    ) -> PyResult<Bound<'py, PyArray2<u8>>> {
        let shape = labels.as_array().dim();
        let core = slots::Core {
            row0: core.0,
            rows: core.1,
            column0: core.2,
            columns: core.3,
        };
        if !core.fits(shape) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the core does not lie inside the window",
            ));
        }
        if land.as_array().dim() != shape || rivers.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "mismatched rasters",
            ));
        }
        if tables.len() != 7 || quantiles.len() != 3 || remap.len()? != 17 * 16 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "wrong table counts",
            ));
        }
        let columns: Vec<&[i64]> = tables
            .iter()
            .map(|array| array.as_slice())
            .collect::<Result<_, _>>()?;
        let quantile_slices: Vec<&[i64]> = quantiles
            .iter()
            .map(|array| array.as_slice())
            .collect::<Result<_, _>>()?;
        let labels = labels.as_slice()?;
        let labels_count = water.len()?;
        if columns.iter().any(|column| column.len() != labels_count)
            || labels
                .iter()
                .any(|&l| usize::try_from(l).map_or(true, |l| l >= labels_count))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "labels outside the tables",
            ));
        }
        let tables = slots::Tables {
            water: water.as_slice()?,
            coast_slot: columns[0],
            topography: columns[1],
            vegetation: columns[2],
            climate: columns[3],
            level_one: columns[4],
            level_two: columns[5],
            materials: columns[6],
        };
        let wobble = slots::Wobble {
            coast: keys[0],
            shelf: keys[1],
            border: keys[2],
            family: keys[3],
            level: keys[4],
            periods,
            quantiles: [quantile_slices[0], quantile_slices[1], quantile_slices[2]],
        };
        let (land, rivers, remap) = (land.as_slice()?, rivers.as_slice()?, remap.as_slice()?);
        let out = py.detach(|| {
            slots::synthesize(
                labels,
                land,
                rivers,
                shape,
                core,
                &tables,
                &wobble,
                (x0, y0),
                remap,
            )
        });
        shaped(py, core.shape(), out)
    }

    /// Encode bytes as an LZAV format-3 stream with offset-8 references for repeated runs.
    #[pyfunction]
    fn lzav_encode<'py>(py: Python<'py>, raw: &[u8]) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &py.detach(|| tiles::encode(raw)))
    }

    /// Compressed tiles of a layer image (north-up, 16-bit samples; an 8-bit layer keeps
    /// the low byte): the size of each and the joined bytes.
    #[pyfunction]
    fn pack_layer<'py>(
        py: Python<'py>,
        image: PyReadonlyArray2<'py, u16>,
        sample_bytes: usize,
    ) -> PyResult<(Vec<usize>, Bound<'py, PyBytes>)> {
        let shape = image.as_array().dim();
        if shape.0 == 0 || shape.1 == 0 || !(1..=2).contains(&sample_bytes) {
            return Err(pyo3::exceptions::PyValueError::new_err("unsupported layer"));
        }
        let samples = image.as_slice()?;
        let (sizes, bytes) = py.detach(|| tiles::pack_layer(samples, shape, sample_bytes));
        Ok((sizes, PyBytes::new(py, &bytes)))
    }

    /// Mip level 0 of a tiled layer, south-up as stored, as `height x width` samples of 16
    /// bits (`sample_bytes` 2) or 8 bits (1); tiles decode in parallel in one call.
    #[pyfunction]
    fn read_level0<'py>(
        py: Python<'py>,
        data: &[u8],
        spans: Vec<(usize, usize)>,
        shape: (usize, usize),
        sample_bytes: usize,
    ) -> PyResult<Bound<'py, PyAny>> {
        let tiles = shape.0.div_ceil(tiles::TILE) * shape.1.div_ceil(tiles::TILE);
        if !(1..=2).contains(&sample_bytes) || spans.len() < tiles {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the layer lists fewer tiles than its size needs, or an unknown sample size",
            ));
        }
        if sample_bytes == 1 {
            let out = py
                .detach(|| tiles::read_level0(data, &spans, shape, 1))
                .map_err(|fault| LzavError::new_err(fault.to_string()))?;
            return Ok(shaped(py, shape, out)?.into_any());
        }
        let out = py
            .detach(|| {
                tiles::read_level0(data, &spans, shape, 2).map(|bytes| {
                    bytes
                        .as_chunks::<2>()
                        .0
                        .iter()
                        .map(|&pair| u16::from_le_bytes(pair))
                        .collect::<Vec<u16>>()
                })
            })
            .map_err(|fault| LzavError::new_err(fault.to_string()))?;
        Ok(shaped(py, shape, out)?.into_any())
    }

    /// Additive height and laid slot of the mountain stamps over a decal window: `sources`
    /// and `materials` stack the stamps' images (no materials: zero images), `placements`
    /// has a row of seven numbers per stamp and `bounds` four.
    #[pyfunction]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn mountain_stamp<'py>(
        py: Python<'py>,
        sources: PyReadonlyArray3<'py, u16>,
        materials: PyReadonlyArray3<'py, u8>,
        placements: PyReadonlyArray2<'py, i64>,
        bounds: PyReadonlyArray2<'py, i64>,
        rotations: Vec<(i64, i64)>,
        origin: (i64, i64),
        shape: (usize, usize),
        unit: i64,
        no_material: u8,
    ) -> PyResult<(Bound<'py, PyArray2<i64>>, Bound<'py, PyArray2<u8>>)> {
        let (count, height, width) = sources.as_array().dim();
        let (material_count, slot_height, slot_width) = materials.as_array().dim();
        let images = mountains::Sources {
            heights: sources.as_slice()?,
            count,
            shape: (height, width),
            materials: materials.as_slice()?,
            material_count,
            material_shape: (slot_height, slot_width),
        };
        let (placements, bounds) = (placements.as_slice()?, bounds.as_slice()?);
        let (out, laid) = py
            .detach(|| {
                mountains::stamp(
                    &images,
                    placements,
                    bounds,
                    &rotations,
                    origin,
                    shape,
                    unit,
                    no_material,
                )
            })
            .map_err(|fault| {
                pyo3::exceptions::PyValueError::new_err(match fault {
                    mountains::Fault::Shape => "the stamps' sources or tables do not fit together",
                    mountains::Fault::Placement => "a stamp names no source or rotation it has",
                })
            })?;
        Ok((shaped(py, shape, out)?, shaped(py, shape, laid)?))
    }

    /// Land mask, canvas mask and heights of a decal window at decal resolution.
    #[pyfunction]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn decal_heights<'py>(
        py: Python<'py>,
        codes: PyReadonlyArray2<'py, i8>,
        vanilla_water: PyReadonlyArray2<'py, bool>,
        relief: PyReadonlyArray2<'py, i64>,
        keys: (u64, u64),
        origin: (i64, i64),
        table: Vec<(i64, i64)>,
        profile_end: i32,
        params: std::collections::HashMap<String, i64>,
        core: (usize, usize, usize, usize),
    ) -> PyResult<(
        Bound<'py, PyArray2<bool>>,
        Bound<'py, PyArray2<bool>>,
        Bound<'py, PyArray2<i64>>,
    )> {
        let shape = codes.as_array().dim();
        if vanilla_water.as_array().dim() != shape || relief.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "mismatched rasters",
            ));
        }
        if shape.0 == 0 || shape.1 == 0 || table.is_empty() {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "empty window or profile",
            ));
        }
        let (codes, water, relief) = (
            codes.as_slice()?,
            vanilla_water.as_slice()?,
            relief.as_slice()?,
        );
        let params = terrain::Params::new(params);
        let core = slots::Core {
            row0: core.0,
            rows: core.1,
            column0: core.2,
            columns: core.3,
        };
        if !core.fits((shape.0 * 2, shape.1 * 2)) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the core does not lie inside the window",
            ));
        }
        let (land, canvas, heights) = py
            .detach(|| {
                let fields =
                    terrain::land_and_distances(codes, water, shape, &params, profile_end)?;
                let heights =
                    terrain::heights(relief, shape, core, &fields, keys, origin, &table, &params)?;
                let canvas = slots::crop(&fields.canvas, shape.1 * 2, core);
                Ok::<_, String>((fields.land, canvas, heights))
            })
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        let doubled = (shape.0 * 2, shape.1 * 2);
        Ok((
            shaped(py, doubled, land)?,
            shaped(py, core.shape(), canvas)?,
            shaped(py, core.shape(), heights)?,
        ))
    }

    /// Value noise at arbitrary integer coordinates.
    #[pyfunction]
    fn value_noise_at<'py>(
        py: Python<'py>,
        key: u64,
        xs: PyReadonlyArray1<'py, i64>,
        ys: PyReadonlyArray1<'py, i64>,
        period: i64,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let (xs, ys) = (xs.as_slice()?, ys.as_slice()?);
        Ok(py
            .detach(|| noise::value_noise_at(key, xs, ys, period))
            .into_pyarray(py))
    }
}
