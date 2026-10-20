//! Integer-exact hot kernels of the Random New World generator ([ADR 0005]).
//!
//! Every function equals its Python reference in `tests/reference/` bit for bit.

pub mod distance;
pub mod hash;
pub mod lzav;
pub mod noise;

use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

pyo3::create_exception!(_native, LzavError, pyo3::exceptions::PyValueError);

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
