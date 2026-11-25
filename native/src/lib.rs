//! Integer-exact hot kernels of the Random New World generator ([ADR 0005]).
//!
//! Every function equals its Python reference in `tests/reference/` bit for bit.

pub mod cells;
pub mod climate;
pub mod components;
pub mod distance;
pub mod drainage;
pub mod growth;
pub mod hash;
pub mod knn;
pub mod lzav;
pub mod mountains;
pub mod noise;
pub mod objects;
pub mod pdx;
pub mod raster;
pub mod relief;
pub mod seacells;
pub mod slots;
pub mod spacing;
pub mod splnet;
pub mod terrain;
pub mod tiles;
pub mod voronoi;
pub mod water;

use numpy::{
    IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3,
    PyReadonlyArrayDyn,
};
use pyo3::prelude::*;

pyo3::create_exception!(_native, LzavError, pyo3::exceptions::PyValueError);
pyo3::create_exception!(_native, TerrainRangeError, pyo3::exceptions::PyValueError);
pyo3::create_exception!(_native, PdxSyntaxError, pyo3::exceptions::PyValueError);
pyo3::create_exception!(_native, SplineReadError, pyo3::exceptions::PyValueError);

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

type ClimateMasks<'py> = (
    PyReadonlyArray2<'py, bool>,
    PyReadonlyArray2<'py, bool>,
    PyReadonlyArray2<'py, bool>,
);
type ClimateWater<'py> = (
    PyReadonlyArray2<'py, i64>,
    PyReadonlyArray2<'py, i64>,
    PyReadonlyArray2<'py, i64>,
);

fn climate_sources<'a>(
    shape: (usize, usize),
    masks: &'a ClimateMasks<'_>,
    water: &'a ClimateWater<'_>,
) -> PyResult<climate::Sources<'a>> {
    if shape.0 == 0
        || shape.1 == 0
        || masks.0.as_array().dim() != shape
        || masks.1.as_array().dim() != shape
        || masks.2.as_array().dim() != shape
        || water.0.as_array().dim() != (2, shape.0)
        || water.1.as_array().dim() != (2, shape.0)
        || water.2.as_array().dim() != (2, shape.0)
    {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "climate rasters do not fit together",
        ));
    }
    Ok(climate::Sources {
        shape,
        sea: masks.0.as_slice()?,
        off_west: masks.1.as_slice()?,
        off_east: masks.2.as_slice()?,
        capacity: water.0.as_slice()?,
        cold: water.1.as_slice()?,
        warm: water.2.as_slice()?,
    })
}

#[pymodule]
mod _native {
    use super::*;
    use pyo3::types::PyBytes;

    #[pymodule_export]
    use super::LzavError;
    #[pymodule_export]
    use super::PdxSyntaxError;
    #[pymodule_export]
    use super::SplineReadError;
    #[pymodule_export]
    use super::TerrainRangeError;

    #[pyfunction]
    fn climate_sea_run<'py>(
        py: Python<'py>,
        sea: PyReadonlyArray2<'py, bool>,
        limit: i64,
        laps: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = sea.as_array().dim();
        let flags = sea.as_slice()?;
        if shape.1 == 0 {
            return shaped(py, shape, vec![]);
        }
        let out = py.detach(|| climate::sea_run(flags, shape.1, limit, laps));
        shaped(py, shape, out)
    }

    #[pyfunction]
    fn climate_scan<'py>(
        py: Python<'py>,
        sea: PyReadonlyArray2<'py, bool>,
        height: PyReadonlyArray2<'py, i64>,
        rates: (i64, i64, i64),
        laps: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = sea.as_array().dim();
        if shape != height.as_array().dim() || shape.1 == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "climate rasters do not fit together",
            ));
        }
        let (flags, heights) = (sea.as_slice()?, height.as_slice()?);
        let rates = climate::Rates(rates.0, rates.1, rates.2);
        let out = py.detach(|| climate::scan(flags, heights, shape.1, rates, laps));
        shaped(py, shape, out)
    }

    #[pyfunction]
    fn climate_zonal<'py>(
        py: Python<'py>,
        masks: ClimateMasks<'py>,
        water: ClimateWater<'py>,
        height: PyReadonlyArray2<'py, i64>,
        weights: ClimateWater<'py>,
        rates: (i64, i64, i64),
        laps: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = height.as_array().dim();
        let sources = climate_sources(shape, &masks, &water)?;
        if weights.0.as_array().dim() != (2, shape.0)
            || weights.1.as_array().dim() != (2, shape.0)
            || weights.2.as_array().dim() != (2, shape.0)
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "climate weights do not fit the rows",
            ));
        }
        let heights = height.as_slice()?;
        let weights = (
            weights.0.as_slice()?,
            weights.1.as_slice()?,
            weights.2.as_slice()?,
        );
        let rates = climate::Rates(rates.0, rates.1, rates.2);
        let out = py.detach(|| climate::zonal(&sources, heights, weights, rates, laps));
        shaped(py, (2 * shape.0, shape.1), out)
    }

    #[pyfunction]
    fn climate_inflow<'py>(
        py: Python<'py>,
        masks: ClimateMasks<'py>,
        water: ClimateWater<'py>,
        height: PyReadonlyArray2<'py, i64>,
        weights: (PyReadonlyArray2<'py, i64>, PyReadonlyArray2<'py, i64>),
        rates: (i64, i64, i64),
        equator: i64,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = height.as_array().dim();
        let sources = climate_sources(shape, &masks, &water)?;
        if weights.0.as_array().dim() != (2, shape.0) || weights.1.as_array().dim() != (2, shape.0)
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "climate weights do not fit the rows",
            ));
        }
        let heights = height.as_slice()?;
        let weights = (weights.0.as_slice()?, weights.1.as_slice()?);
        let rates = climate::Rates(rates.0, rates.1, rates.2);
        let out = py.detach(|| climate::inflow(&sources, heights, weights, rates, equator));
        shaped(py, (2 * shape.1, shape.0), out)
    }

    #[pyfunction]
    fn spline_lists(
        py: Python<'_>,
        data: &[u8],
        offset: usize,
        segments: i32,
        strips: i32,
    ) -> PyResult<splnet::Lists> {
        py.detach(|| splnet::parse(data, offset, segments, strips))
            .map_err(SplineReadError::new_err)
    }

    #[pyclass]
    struct PdxParser {
        state: Option<pdx::Parser>,
    }

    #[pymethods]
    impl PdxParser {
        #[new]
        fn new(text: String) -> Self {
            Self {
                state: Some(pdx::Parser::new(text)),
            }
        }

        fn advance(&mut self, py: Python<'_>) -> PyResult<bool> {
            let state = self.state.as_mut().ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("script parser is finished")
            })?;
            py.detach(|| state.advance(std::time::Duration::from_millis(20)))
                .map_err(|fault| {
                    let (reason, offset) = match fault {
                        pdx::Fault::Bad(offset, value) => (
                            format!(
                                "unexpected character {}",
                                pyo3::types::PyString::new(py, &value.to_string())
                                    .repr()
                                    .expect("string repr")
                            ),
                            offset,
                        ),
                        pdx::Fault::Value(offset, at) => (
                            format!(
                                "expected a value, found {}",
                                pyo3::types::PyString::new(py, state.value(at))
                                    .repr()
                                    .expect("string repr")
                            ),
                            offset,
                        ),
                        pdx::Fault::Message(message, offset) => (message.to_owned(), offset),
                        pdx::Fault::Deep => {
                            return pyo3::exceptions::PyRecursionError::new_err(
                                "script uses the recursive reference parser",
                            );
                        }
                    };
                    PdxSyntaxError::new_err((reason, offset))
                })
        }

        fn finish<'py>(
            &mut self,
            py: Python<'py>,
            block: &Bound<'py, PyAny>,
            entry: &Bound<'py, PyAny>,
            checkpoint: &Bound<'py, PyAny>,
        ) -> PyResult<Bound<'py, PyAny>> {
            use pyo3::types::PyList;

            let state = self.state.take().ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("script parser is finished")
            })?;
            if !state.finished() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "script parser has unfinished work",
                ));
            }
            // Keep the existing Python records and their mutable lists. All blocks
            // exist before wiring children; no Python/C recursion or shared cache.
            let mut blocks = Vec::with_capacity(state.blocks.len());
            let mut lists = Vec::with_capacity(state.blocks.len());
            for (at, node) in state.blocks.iter().enumerate() {
                if at % 1024 == 0 {
                    checkpoint.call0()?;
                }
                let entries = PyList::empty(py);
                blocks.push(block.call1((
                    &entries,
                    node.open.map_or(-1, |n| n as i64),
                    node.close,
                ))?);
                lists.push(entries);
            }
            let mut count = 0;
            for (at, node) in state.blocks.iter().enumerate() {
                for item in &node.entries {
                    if count % 1024 == 0 {
                        checkpoint.call0()?;
                    }
                    count += 1;
                    let value = match item.value {
                        pdx::Value::Scalar(token) => {
                            pyo3::types::PyString::new(py, state.value(token)).into_any()
                        }
                        pdx::Value::Block(child) => blocks[child].clone(),
                    };
                    lists[at].append(entry.call1((
                        item.key.map(|key| state.value(key)),
                        item.op.map(|op| state.value(op)),
                        value,
                        item.start,
                        item.end,
                    ))?)?;
                }
            }
            Ok(blocks.swap_remove(0))
        }
    }

    #[pyclass]
    struct RidgeAccumulator {
        state: relief::Ridges,
        shape: (usize, usize),
        finished: bool,
    }

    #[pymethods]
    impl RidgeAccumulator {
        #[new]
        fn new(height: usize, width: usize, scale: i64, gain: i64) -> PyResult<Self> {
            let size = height.checked_mul(width).ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("ridge shape is too large")
            })?;
            if scale <= 0 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "ridge scale must be positive",
                ));
            }
            Ok(Self {
                state: relief::Ridges::new(size, scale, gain),
                shape: (height, width),
                finished: false,
            })
        }

        fn add(
            &mut self,
            py: Python<'_>,
            noise: PyReadonlyArray2<'_, i64>,
            share: i64,
        ) -> PyResult<()> {
            if self.finished || noise.as_array().dim() != self.shape {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "ridge state is finished or noise shape differs",
                ));
            }
            let noise = noise.as_slice()?;
            py.detach(|| self.state.add(noise, share));
            Ok(())
        }

        fn finish<'py>(
            &mut self,
            py: Python<'py>,
            shares: i64,
        ) -> PyResult<Bound<'py, PyArray2<i64>>> {
            if self.finished || shares <= 0 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "ridge state is finished or shares are not positive",
                ));
            }
            self.finished = true;
            let values = py.detach(|| self.state.finish(shares));
            shaped(py, self.shape, values)
        }
    }

    #[pyfunction]
    fn relief_chain<'py>(
        py: Python<'py>,
        axis: PyReadonlyArray2<'py, i64>,
        wander: PyReadonlyArray2<'py, i64>,
        width: PyReadonlyArray2<'py, i64>,
        params: [i64; 9],
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = axis.as_array().dim();
        if shape.0 == 0
            || shape.1 == 0
            || wander.as_array().dim() != shape
            || width.as_array().dim() != shape
            || params[0] <= 0
            || params[1] < 0
            || params[2] <= 0
            || params[5] <= 0
            || params[6] <= 0
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid relief chain window or parameters",
            ));
        }
        let (axis, wander, width) = (axis.as_slice()?, wander.as_slice()?, width.as_slice()?);
        let out = py.detach(|| relief::chain(axis, wander, width, shape, params));
        shaped(py, shape, out)
    }

    #[pyfunction]
    fn parse_instances<'py>(py: Python<'py>, text: &str) -> PyResult<Bound<'py, PyArray1<f32>>> {
        let values = py
            .detach(|| {
                text.split(|c: char| c.is_ascii_whitespace() || c == '\u{b}')
                    .filter(|word| !word.is_empty())
                    .map(|word| word.parse::<f64>().map(|value| value as f32))
                    .collect::<Result<Vec<_>, _>>()
            })
            .map_err(|_| {
                pyo3::exceptions::PyValueError::new_err("invalid instance transform number")
            })?;
        Ok(values.into_pyarray(py))
    }

    #[pyfunction]
    fn murmur3(data: &[u8], seed: u32) -> u32 {
        hash::murmur3(data, seed)
    }

    #[pyfunction]
    fn key_hashes(py: Python<'_>, keys: Vec<String>) -> Vec<u32> {
        py.detach(|| {
            keys.iter()
                .map(|key| hash::murmur3(key.as_bytes(), 0))
                .collect()
        })
    }

    /// Size the thread pool of the kernels; returns its size. Only the first call before a
    /// kernel has run can change it, later calls report the size in force.
    #[pyfunction]
    fn configure_threads(threads: usize) -> usize {
        let _ = rayon::ThreadPoolBuilder::new()
            .num_threads(threads.max(1))
            .build_global();
        rayon::current_num_threads()
    }

    #[pyfunction]
    fn first_pixels32<'py>(
        py: Python<'py>,
        labels: PyReadonlyArrayDyn<'py, i32>,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let labels = labels.as_slice()?;
        Ok(py.detach(|| cells::first_pixels(labels)).into_pyarray(py))
    }
    #[pyfunction]
    fn first_pixels64<'py>(
        py: Python<'py>,
        labels: PyReadonlyArrayDyn<'py, i64>,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let labels = labels.as_slice()?;
        Ok(py.detach(|| cells::first_pixels(labels)).into_pyarray(py))
    }
    #[pyfunction]
    fn first_pixels_u64<'py>(
        py: Python<'py>,
        labels: PyReadonlyArrayDyn<'py, u64>,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let labels = labels.as_slice()?;
        Ok(py.detach(|| cells::first_pixels(labels)).into_pyarray(py))
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn blend_mountains<'py>(
        py: Python<'py>,
        heights: PyReadonlyArray2<'py, i64>,
        inside: PyReadonlyArray2<'py, bool>,
        detail: PyReadonlyArray2<'py, i64>,
        laid: PyReadonlyArray2<'py, u8>,
        reach: PyReadonlyArray2<'py, i32>,
        limits: (i64, i64, i64),
        no_material: u8,
    ) -> PyResult<(Bound<'py, PyArray2<i64>>, Bound<'py, PyArray2<u8>>)> {
        let shape = heights.as_array().dim();
        if inside.as_array().dim() != shape
            || detail.as_array().dim() != shape
            || laid.as_array().dim() != shape
            || reach.as_array().dim() != shape
            || limits.1 <= limits.0
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid mountain blend arrays",
            ));
        }
        let (h, i, d, l, r) = (
            heights.as_slice()?,
            inside.as_slice()?,
            detail.as_slice()?,
            laid.as_slice()?,
            reach.as_slice()?,
        );
        let (out, stamps) = py
            .detach(|| terrain::blend_mountains(h, i, d, l, r, limits, no_material))
            .map_err(TerrainRangeError::new_err)?;
        Ok((shaped(py, shape, out)?, shaped(py, shape, stamps)?))
    }

    #[pyfunction]
    fn stamp_slots<'py>(
        py: Python<'py>,
        slots: PyReadonlyArray2<'py, u8>,
        stamped: PyReadonlyArray2<'py, u8>,
        labels: PyReadonlyArray2<'py, i32>,
        materials: PyReadonlyArray1<'py, i64>,
        remap: PyReadonlyArray1<'py, i64>,
    ) -> PyResult<Bound<'py, PyArray2<u8>>> {
        let shape = slots.as_array().dim();
        if stamped.as_array().dim() != shape
            || labels.as_array().dim() != shape
            || remap.len()? != 17 * 16
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid stamp slot arrays",
            ));
        }
        let (s, t, l, m, r) = (
            slots.as_slice()?,
            stamped.as_slice()?,
            labels.as_slice()?,
            materials.as_slice()?,
            remap.as_slice()?,
        );
        let out = py
            .detach(|| slots::stamp_slots(s, t, l, m, r))
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        shaped(py, shape, out)
    }

    #[pyfunction]
    fn coastal_pixels<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        land: PyReadonlyArray1<'py, bool>,
        sea: PyReadonlyArray1<'py, bool>,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = labels.as_array().dim();
        let (labels, land, sea) = (labels.as_slice()?, land.as_slice()?, sea.as_slice()?);
        if land.len() != sea.len() || labels.iter().any(|&l| l >= 0 && l as usize >= land.len()) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "coast label out of range",
            ));
        }
        let out = py.detach(|| cells::coastal_pixels(labels, shape, land, sea));
        shaped(py, (out.len() / 3, 3), out)
    }

    #[pyfunction]
    fn format_instances(py: Python<'_>, values: PyReadonlyArray2<'_, f32>) -> PyResult<String> {
        let shape = values.as_array().dim();
        let values = values.as_slice()?;
        Ok(py.detach(|| objects::format_inline(values, shape)))
    }

    #[pyfunction]
    fn renumber<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = labels.as_array().dim();
        let labels = labels.as_slice()?;
        let out = py.detach(|| cells::renumber(labels));
        shaped(py, shape, out)
    }

    #[pyfunction]
    fn land_blur<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        values: PyReadonlyArray2<'py, i64>,
        radius: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = land.as_array().dim();
        if values.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "raster shapes differ",
            ));
        }
        let (land, values) = (land.as_slice()?, values.as_slice()?);
        let out = py.detach(|| raster::land_blur(land, values, shape, radius));
        shaped(py, shape, out)
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn block_relief<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        values: PyReadonlyArray2<'py, i64>,
        bend: Option<PyReadonlyArray2<'py, i64>>,
        blocks: usize,
        step: usize,
        first: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = land.as_array().dim();
        if values.as_array().dim() != shape
            || bend.as_ref().is_some_and(|b| b.as_array().dim() != shape)
            || step == 0
            || (shape.0 > 0 && blocks < (first + shape.0).div_ceil(step) * shape.1.div_ceil(step))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid relief block strip",
            ));
        }
        let bend = bend.as_ref().map(|b| b.as_slice()).transpose()?;
        let (land, values) = (land.as_slice()?, values.as_slice()?);
        let out =
            py.detach(|| cells::block_relief(land, values, bend, shape.1, blocks, step, first));
        shaped(py, (5, blocks), out)
    }

    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn block_labels<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        step: usize,
    ) -> PyResult<(Bound<'py, PyArray2<i32>>, Bound<'py, PyArray1<i64>>)> {
        if step == 0 {
            return Err(pyo3::exceptions::PyValueError::new_err("empty block step"));
        }
        let shape = land.as_array().dim();
        let land = land.as_slice()?;
        let (labels, counts) = py.detach(|| cells::block_labels(land, shape, step));
        Ok((shaped(py, shape, labels)?, counts.into_pyarray(py)))
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn strip_bend<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        values: PyReadonlyArray2<'py, i64>,
        start: usize,
        stop: usize,
        rows: usize,
        step: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = land.as_array().dim();
        if values.as_array().dim() != shape
            || start > stop
            || stop > rows
            || shape.0 != (stop.saturating_add(step).min(rows) - start.saturating_sub(step))
            || step == 0
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid bend strip or halo",
            ));
        }
        let (land, values) = (land.as_slice()?, values.as_slice()?);
        let out =
            py.detach(|| raster::strip_bend(land, values, shape.1, (start, stop, rows, step)));
        shaped(py, (stop - start, shape.1), out)
    }

    #[pyfunction]
    fn water_open_cells<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        distance: PyReadonlyArray2<'py, u8>,
        reach: u8,
        first: usize,
        last: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = distance.as_array().dim();
        if image.as_array().dim() != (shape.0, shape.1, 4)
            || first > last
            || last > shape.0
            || !first.is_multiple_of(32)
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid water strip",
            ));
        }
        let (image, distance) = (image.as_slice()?, distance.as_slice()?);
        let out = py.detach(|| water::open_cells(image, distance, shape.1, reach, first, last));
        shaped(py, (out.len() / 5, 5), out)
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn water_profile_sums<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        distance: PyReadonlyArray2<'py, u8>,
        grid: PyReadonlyArray3<'py, i64>,
        reach: usize,
        first: usize,
        last: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = distance.as_array().dim();
        let (gr, gc, channels) = grid.as_array().dim();
        if image.as_array().dim() != (shape.0, shape.1, 4)
            || shape.0 < 64
            || gr == 0
            || gc == 0
            || channels != 4
            || reach > 255
            || first > last
            || last > shape.0
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid water calibration strip",
            ));
        }
        let (image, distance, grid) = (image.as_slice()?, distance.as_slice()?, grid.as_slice()?);
        let out = py.detach(|| {
            water::profile_sums(image, distance, shape, grid, (gr, gc), reach, first, last)
        });
        shaped(py, (out.len() / 5, 5), out)
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn water_render<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        old: PyReadonlyArray2<'py, u8>,
        new: PyReadonlyArray2<'py, u8>,
        touched: PyReadonlyArray2<'py, bool>,
        table: PyReadonlyArray3<'py, i64>,
        grid: PyReadonlyArray3<'py, i64>,
        first: usize,
        last: usize,
        reach: usize,
        key: u64,
    ) -> PyResult<Bound<'py, PyArray1<u8>>> {
        let shape = old.as_array().dim();
        let (bands, distances, channels) = table.as_array().dim();
        let (gr, gc, gchannels) = grid.as_array().dim();
        if image.as_array().dim() != (shape.0, shape.1, 4)
            || new.as_array().dim() != shape
            || touched.as_array().dim() != shape
            || bands == 0
            || reach > 255
            || distances != reach + 1
            || channels != 4
            || gr == 0
            || gc == 0
            || gchannels != 4
            || first >= last
            || last > shape.0
            || shape.1 == 0
            || reach > 255
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid water render strip",
            ));
        }
        let params = water::Render {
            image: image.as_slice()?,
            old: old.as_slice()?,
            new: new.as_slice()?,
            touched: touched.as_slice()?,
            shape,
            table: table.as_slice()?,
            bands,
            grid: grid.as_slice()?,
            grid_shape: (gr, gc),
            first,
            last,
            reach,
            key,
        };
        let out = py.detach(|| water::render(&params));
        Ok(out.into_pyarray(py))
    }

    #[pyfunction]
    fn label_moments<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        values: Option<PyReadonlyArray2<'py, i64>>,
        count: usize,
        first: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = labels.as_array().dim();
        if values.as_ref().is_some_and(|v| v.as_array().dim() != shape) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "raster shapes differ",
            ));
        }
        let values = values.as_ref().map(|v| v.as_slice()).transpose()?;
        let labels = labels.as_slice()?;
        let out = py.detach(|| cells::moments(labels, values, shape.1, count, first));
        shaped(py, (4, count), out)
    }

    #[pyfunction]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn location_sums<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        table: PyReadonlyArray2<'py, i64>,
        count: usize,
        step: usize,
        block_columns: usize,
        first: usize,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray2<i64>>)> {
        let (rows, width) = labels.as_array().dim();
        let (blocks, features) = table.as_array().dim();
        if step == 0
            || block_columns < width.div_ceil(step)
            || (rows > 0
                && width > 0
                && blocks < ((first + rows - 1) / step) * block_columns + width.div_ceil(step))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "block table does not fit the raster",
            ));
        }
        let (labels, table) = (labels.as_slice()?, table.as_slice()?);
        let (pixels, sums) = py
            .detach(|| {
                cells::location_sums(
                    labels,
                    width,
                    table,
                    features,
                    count,
                    step,
                    block_columns,
                    first,
                )
            })
            .map_err(|_| pyo3::exceptions::PyValueError::new_err("label out of range"))?;
        Ok((
            pixels.into_pyarray(py),
            shaped(py, (count, features), sums)?,
        ))
    }

    #[pyfunction]
    fn centre_pixels<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        flat: PyReadonlyArray1<'py, i64>,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let width = labels.as_array().dim().1;
        let (labels, flat) = (labels.as_slice()?, flat.as_slice()?);
        let out = py.detach(|| cells::centre_pixels(labels, width, flat));
        Ok(out.into_pyarray(py))
    }

    #[pyfunction]
    fn merge_small<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        minimum: i64,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = labels.as_array().dim();
        let labels = labels.as_slice()?;
        let out = py.detach(|| cells::merge_small(labels, shape, minimum));
        shaped(py, shape, out)
    }

    /// Frontier growth; call Python cancellation only between Rust-owned batches.
    #[pyfunction]
    fn grow_labels<'py>(
        py: Python<'py>,
        mask: PyReadonlyArray2<'py, bool>,
        seeds: PyReadonlyArray2<'py, i32>,
        speed: Option<PyReadonlyArray1<'py, i64>>,
        checkpoint: Py<PyAny>,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = mask.as_array().dim();
        if seeds.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "raster shapes differ",
            ));
        }
        let speeds = speed.as_ref().map(|s| s.as_slice()).transpose()?;
        let (mask, seeds) = (mask.as_slice()?, seeds.as_slice()?);
        let mut state = py
            .detach(|| growth::Growth::new(mask, seeds, shape.1, speeds))
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        loop {
            checkpoint.call0(py)?;
            if py.detach(|| state.advance(std::time::Duration::from_millis(100))) {
                break;
            }
        }
        shaped(py, shape, state.finish())
    }

    /// Synchronous eight-neighbour spacing relaxation, with unchanged convergence.
    #[pyfunction]
    fn grade_spacing<'py>(
        py: Python<'py>,
        spacing: PyReadonlyArray2<'py, i64>,
        land: PyReadonlyArray2<'py, bool>,
        step: i64,
        checkpoint: Py<PyAny>,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let shape = spacing.as_array().dim();
        if land.as_array().dim() != shape || step < 0 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid spacing grid or step",
            ));
        }
        let (spacing, land) = (spacing.as_slice()?, land.as_slice()?);
        let mut state = py.detach(|| spacing::Grading::new(spacing, land, shape.1, step));
        loop {
            checkpoint.call0(py)?;
            if py.detach(|| state.advance(std::time::Duration::from_millis(100))) {
                break;
            }
        }
        shaped(py, shape, state.finish())
    }

    /// Sequential seed acceptance in hashed buckets, preserving candidate order.
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn throw_seeds<'py>(
        py: Python<'py>,
        xs: PyReadonlyArray1<'py, i64>,
        ys: PyReadonlyArray1<'py, i64>,
        radius: PyReadonlyArray1<'py, i64>,
        smallest: i64,
        widest: i64,
        columns: i64,
        gap: i64,
        checkpoint: Py<PyAny>,
    ) -> PyResult<Bound<'py, PyArray1<i64>>> {
        let (xs, ys, radius) = (xs.as_slice()?, ys.as_slice()?, radius.as_slice()?);
        if xs.len() != ys.len()
            || xs.len() != radius.len()
            || smallest <= 0
            || widest <= 0
            || gap <= 0
            || radius.iter().any(|&r| r <= 0 || r > widest)
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "invalid seed candidates or spacing",
            ));
        }
        let mut state = spacing::Scatter::new(xs, ys, radius, smallest, widest, gap);
        loop {
            checkpoint.call0(py)?;
            if py.detach(|| state.advance(std::time::Duration::from_millis(100))) {
                break;
            }
        }
        Ok(state.finish(columns).into_pyarray(py))
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

    /// The distance through water from the nearest site, and the site, on a coarse raster.
    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn sea_geodesic<'py>(
        py: Python<'py>,
        mask: PyReadonlyArray2<'py, bool>,
        region: PyReadonlyArray2<'py, i32>,
        sites: PyReadonlyArray2<'py, i64>,
        start: PyReadonlyArray1<'py, u32>,
    ) -> PyResult<(Bound<'py, PyArray2<i32>>, Bound<'py, PyArray2<u32>>)> {
        let shape = mask.as_array().dim();
        let flags = mask.as_slice()?;
        let regions = region.as_slice()?;
        if region.as_array().dim() != shape {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the rasters do not fit together",
            ));
        }
        let at = sites.as_array();
        let (count, columns) = at.dim();
        let begin = start.as_slice()?;
        if columns != 2 || begin.len() != count {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the sites do not fit together",
            ));
        }
        let mut points = Vec::with_capacity(count);
        for row in 0..count {
            let (r, c) = (at[[row, 0]], at[[row, 1]]);
            if r < 0 || c < 0 || r as usize >= shape.0 || c as usize >= shape.1 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "a site lies outside the raster",
                ));
            }
            points.push((r as usize, c as usize));
        }
        let found =
            py.detach(|| seacells::geodesic(flags, regions, shape.0, shape.1, &points, begin));
        Ok((
            shaped(py, shape, found.label)?,
            shaped(py, shape, found.cost)?,
        ))
    }

    /// Per label of a geodesic partition: the pixel nearest the label's centre of mass and the
    /// pixel farthest from its site, as flat indices (-1 where the label has no pixel).
    #[pyfunction]
    #[allow(clippy::type_complexity)]
    fn sea_extremes<'py>(
        py: Python<'py>,
        label: PyReadonlyArray2<'py, i32>,
        cost: PyReadonlyArray2<'py, u32>,
        centres: PyReadonlyArray2<'py, f64>,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray1<i64>>)> {
        let shape = label.as_array().dim();
        let (labels, costs) = (label.as_slice()?, cost.as_slice()?);
        let at = centres.as_array();
        if cost.as_array().dim() != shape || at.dim().1 != 2 {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the rasters do not fit together",
            ));
        }
        let middles: Vec<(f64, f64)> = (0..at.dim().0)
            .map(|row| (at[[row, 0]], at[[row, 1]]))
            .collect();
        let (near, far) = py.detach(|| seacells::extremes(labels, costs, shape.1, &middles));
        Ok((near.into_pyarray(py), far.into_pyarray(py)))
    }

    /// The full raster's partition that follows a coarse one with exact borders.
    #[pyfunction]
    #[allow(clippy::too_many_arguments)]
    fn sea_refine<'py>(
        py: Python<'py>,
        mask: PyReadonlyArray2<'py, bool>,
        coarse: PyReadonlyArray2<'py, i32>,
        step: usize,
        reach: usize,
        sites: PyReadonlyArray2<'py, i64>,
        depth: PyReadonlyArray2<'py, i32>,
        band_width: i64,
        last_band: i64,
        site_band: PyReadonlyArray1<'py, i32>,
        site_claim: PyReadonlyArray2<'py, i64>,
    ) -> PyResult<Bound<'py, PyArray2<i32>>> {
        let shape = mask.as_array().dim();
        let (flags, grid) = (mask.as_slice()?, coarse.as_slice()?);
        let cells = coarse.as_array().dim();
        let at = sites.as_array();
        let bands_of = site_band.as_slice()?;
        let claim = site_claim.as_array();
        if step == 0
            || reach == 0
            || cells.0 == 0
            || cells.1 == 0
            || cells.0 != shape.0.div_ceil(step)
            || cells.1 != shape.1.div_ceil(step)
            || depth.as_array().dim() != cells
            || at.dim().1 != 2
            || bands_of.len() != at.dim().0
            || claim.dim() != (at.dim().0, 2)
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the rasters do not fit together",
            ));
        }
        let points: Vec<(i64, i64)> = (0..at.dim().0)
            .map(|row| (at[[row, 0]], at[[row, 1]]))
            .collect();
        let claims: Vec<(i64, i64)> = (0..at.dim().0)
            .map(|row| (claim[[row, 0]], claim[[row, 1]]))
            .collect();
        if grid
            .iter()
            .any(|&label| label >= 0 && label as usize >= points.len())
        {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "a label has no site",
            ));
        }
        let bands = seacells::Bands {
            depth: depth.as_slice()?,
            width: band_width,
            last: last_band,
            site: bands_of,
            claim: &claims,
        };
        let out = py.detach(|| {
            seacells::refine(flags, shape.1, grid, cells.1, step, reach, &points, &bands)
        });
        shaped(py, shape, out)
    }

    /// The `k` nearest `train` rows to each `query` row, nearest first, ties by index.
    #[pyfunction]
    fn nearest_rows<'py>(
        py: Python<'py>,
        train: PyReadonlyArray2<'py, i64>,
        query: PyReadonlyArray2<'py, i64>,
        k: usize,
    ) -> PyResult<Bound<'py, PyArray2<i64>>> {
        let (rows, width) = train.as_array().dim();
        let (queries, columns) = query.as_array().dim();
        if columns != width || k > rows {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "the rows do not fit together",
            ));
        }
        let (train, query) = (train.as_slice()?, query.as_slice()?);
        let out = py.detach(|| knn::nearest(train, query, width, k));
        shaped(py, (queries, k), out)
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

    #[pyfunction]
    #[allow(clippy::too_many_arguments, clippy::type_complexity)]
    fn canvas_counts<'py>(
        py: Python<'py>,
        labels: PyReadonlyArray2<'py, i32>,
        materials: PyReadonlyArray2<'py, u8>,
        canvas: PyReadonlyArray2<'py, bool>,
        fine: PyReadonlyArray1<'py, i64>,
        coarse: PyReadonlyArray1<'py, i64>,
        use_fine: PyReadonlyArray1<'py, bool>,
        coarse_keys: usize,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray1<i64>>)> {
        let shape = labels.as_array().dim();
        if canvas.as_array().dim() != shape {
            return Err(object_fault(objects::Fault::Shape));
        }
        let raster = objects::Raster {
            labels: labels.as_slice()?,
            materials: materials.as_slice()?,
            shape,
        };
        let (canvas, fine, coarse, use_fine) = (
            canvas.as_slice()?,
            fine.as_slice()?,
            coarse.as_slice()?,
            use_fine.as_slice()?,
        );
        let (fine, coarse) = py
            .detach(|| objects::canvas_counts(&raster, canvas, fine, coarse, use_fine, coarse_keys))
            .map_err(object_fault)?;
        Ok((fine.into_pyarray(py), coarse.into_pyarray(py)))
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
    #[pyo3(signature = (land, height, rain, key, blocked=None))]
    #[allow(clippy::type_complexity)]
    fn drainage<'py>(
        py: Python<'py>,
        land: PyReadonlyArray2<'py, bool>,
        height: PyReadonlyArray2<'py, i64>,
        rain: PyReadonlyArray2<'py, i64>,
        key: u64,
        blocked: Option<PyReadonlyArray2<'py, bool>>,
    ) -> PyResult<(Bound<'py, PyArray1<i64>>, Bound<'py, PyArray1<i64>>)> {
        let shape = land.as_array().dim();
        if height.as_array().dim() != shape
            || rain.as_array().dim() != shape
            || blocked
                .as_ref()
                .is_some_and(|array| array.as_array().dim() != shape)
        {
            return Err(pyo3::exceptions::PyValueError::new_err("mismatched grids"));
        }
        let (land, height, rain) = (land.as_slice()?, height.as_slice()?, rain.as_slice()?);
        let blocked = blocked.as_ref().map(|array| array.as_slice()).transpose()?;
        let tree = py.detach(|| crate::drainage::drainage(land, height, rain, shape, key, blocked));
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
    #[pyo3(signature = (codes, vanilla_water, relief, keys, origin, table, profile_end, params, core, sampled=false))]
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
        sampled: bool,
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
        let step = if sampled { 2 } else { 1 };
        let core = if sampled {
            slots::Core {
                row0: core.row0 + 1,
                rows: core.rows.saturating_sub(1),
                column0: core.column0 + 1,
                columns: core.columns.saturating_sub(1),
            }
        } else {
            core
        };
        let (land, canvas, heights) = py
            .detach(|| {
                let fields =
                    terrain::land_and_distances(codes, water, shape, &params, profile_end)?;
                let heights = terrain::heights(
                    relief, shape, core, &fields, keys, origin, &table, &params, step,
                )?;
                let canvas = slots::crop_strided(&fields.canvas, shape.1 * 2, core, step);
                Ok::<_, String>((fields.land, canvas, heights))
            })
            .map_err(pyo3::exceptions::PyValueError::new_err)?;
        let doubled = (shape.0 * 2, shape.1 * 2);
        let output = (core.rows.div_ceil(step), core.columns.div_ceil(step));
        Ok((
            shaped(py, doubled, land)?,
            shaped(py, output, canvas)?,
            shaped(py, output, heights)?,
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
