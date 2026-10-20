//! Integer-exact hot kernels of the Random New World generator ([ADR 0005]).
//!
//! Every function equals its Python reference in `tests/reference/` bit for bit.

pub mod hash;
pub mod lzav;

use pyo3::prelude::*;

pyo3::create_exception!(_native, LzavError, pyo3::exceptions::PyValueError);

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
}
