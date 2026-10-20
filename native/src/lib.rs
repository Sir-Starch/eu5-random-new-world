//! Integer-exact hot kernels of the Random New World generator ([ADR 0005]).
//!
//! Every function equals its Python reference in `tests/reference/` bit for bit.

pub mod components;
pub mod distance;
pub mod drainage;
pub mod hash;
pub mod lzav;
pub mod noise;
pub mod objects;
pub mod raster;

use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
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
    fn distance_from<'py>(
        py: Python<'py>,
        sources: PyReadonlyArray2<'py, bool>,
        limit: i32,
        octagonal: bool,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = sources.as_array().dim();
        let flags = sources.as_slice()?;
        let out = py.detach(|| distance::distance_from(flags, shape, limit, octagonal));
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

    /// Number the 4-connected equal-label components in raster order of first pixel.
    #[pyfunction]
    fn label_components<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        wrap_x: bool,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = labels.as_array().dim();
        let values = labels.as_slice()?;
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

    /// Per label, the first raster pixel with the best score (ties by `tie`), as `(count, 2)`.
    #[pyfunction]
    fn best_points<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        score: PyReadonlyArray2<'py, i64>,
        tie: PyReadonlyArray2<'py, i64>,
        count: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let (height, width) = labels.as_array().dim();
        if score.as_array().dim() != (height, width) || tie.as_array().dim() != (height, width) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "mismatched rasters",
            ));
        }
        let (labels, score, tie) = (labels.as_slice()?, score.as_slice()?, tie.as_slice()?);
        if labels
            .iter()
            .any(|&label| usize::try_from(label).is_ok_and(|label| label >= count))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "a label is not below the count",
            ));
        }
        let out = py.detach(|| raster::best_points(labels, score, tie, width, count));
        shaped(py, (count, 2), out)
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
