//! The Rust core of `sdg_tech_tagger`.
//!
//! It cuts texts into tokens as corpustools 0.5.2 does, indexes them in
//! tantivy, evaluates corpustools' query language on token positions and
//! applies the logic of text2sdg 1.1.2's four systems, in compatible and
//! corrected mode. Python reaches it through the `_native` module.

pub mod engine;
pub mod index;
pub mod query;
pub mod systems;
pub mod terms;
pub mod tokens;

use pyo3::prelude::*;
use rayon::prelude::*;

/// Consumes a text and produces its tokens as written, as corpustools cuts
/// them. For checking the tokenizer against R.
#[pyfunction]
fn tokenize(text: &str) -> Vec<String> {
    tokens::token_spans(text)
        .into_iter()
        .map(|(s, e)| text[s..e].to_string())
        .collect()
}

/// Consumes a search string and produces its parsed tree in the compact form
/// of `query::Node`'s `Display`. Raises `ValueError` where corpustools stops.
/// For checking the parser against R.
#[pyfunction]
fn parse_tree(query: &str) -> PyResult<String> {
    query::parse(query)
        .map(|node| node.to_string())
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.0))
}

/// Consumes a term and produces the string corpustools looks up for it
/// (`standardize_dict_term_spacing`). For checking against R.
#[pyfunction]
fn standardize_term(term: &str) -> String {
    terms::standardize(term)
}

/// Consumes search strings, texts, a mode (`"unique_hits"` or `"features"`)
/// and a number of threads, and produces the hit table `search_features`
/// would return, all strings given in one call, for each string evaluated
/// on each text alone: three equal
/// length lists, the index of the string, the index of the text and the
/// token id, sorted by string, text and token. For checking the engine
/// against R.
#[pyfunction]
fn search_hits(
    py: Python<'_>,
    strings: Vec<String>,
    texts: Vec<String>,
    mode: &str,
    threads: usize,
) -> PyResult<(Vec<u32>, Vec<u32>, Vec<u32>)> {
    let mode = match mode {
        "unique_hits" => engine::Mode::UniqueHits,
        "features" => engine::Mode::Features,
        _ => return Err(pyo3::exceptions::PyValueError::new_err("unknown mode")),
    };
    let engine = engine::Engine::new(&strings)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    py.detach(|| {
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build()
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        pool.install(|| {
            let refs: Vec<&str> = texts.iter().map(String::as_str).collect();
            let batch = index::Batch::build(&refs, threads)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            let prepared = engine
                .prepare(&batch)
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            let call: Vec<usize> = (0..engine.len()).collect();
            let multiplicity = engine.multiplicity(&call);
            let per_string: Vec<Vec<(u32, Vec<u32>)>> = (0..engine.len())
                .into_par_iter()
                .map(|i| prepared.evaluate(i, mode, &multiplicity))
                .collect();
            let (mut a, mut b, mut c) = (Vec::new(), Vec::new(), Vec::new());
            for (i, docs) in per_string.into_iter().enumerate() {
                for (row, hits) in docs {
                    for t in hits {
                        a.push(i as u32);
                        b.push(row);
                        c.push(t);
                    }
                }
            }
            Ok((a, b, c))
        })
    })
}

/// A row of a query table as Python hands it over: `sdg`, `query_id`,
/// `query`.
type QueryTuple = (String, i32, String);
/// A row of an internal Aurora table: `orig`, `correct`, `correct 2`.
type InternalTuple = (String, String, Option<String>);
/// The columns of the firings of a batch: the index of the document in the
/// batch, `system`, `sdg`, `query_id`, `features`.
type FiringColumns = (Vec<u32>, Vec<String>, Vec<String>, Vec<i32>, Vec<String>);

fn query_rows(rows: Vec<QueryTuple>) -> Vec<systems::QueryRow> {
    rows.into_iter()
        .map(|(sdg, query_id, query)| systems::QueryRow {
            sdg,
            query_id,
            query,
        })
        .collect()
}

fn internal_rows(rows: Vec<InternalTuple>) -> Vec<systems::InternalRow> {
    rows.into_iter()
        .map(|(orig, correct, correct2)| systems::InternalRow {
            orig,
            correct,
            correct2,
        })
        .collect()
}

/// The port, built once from text2sdg's query tables: the search strings of
/// both modes compiled, ready to run on batches of texts.
#[pyclass(frozen, name = "Port")]
struct NativePort {
    port: systems::Port,
}

#[pymethods]
impl NativePort {
    /// Consumes the rows of the seven query tables of `queries/`, in table
    /// order, and produces the port. Raises `ValueError` if a search string
    /// does not parse or a correction does not find the string it corrects.
    #[new]
    #[allow(clippy::too_many_arguments)]
    fn new(
        elsevier: Vec<QueryTuple>,
        siris: Vec<QueryTuple>,
        auckland: Vec<QueryTuple>,
        aurora: Vec<QueryTuple>,
        aurora_simple: Vec<InternalTuple>,
        aurora_and: Vec<InternalTuple>,
        aurora_w: Vec<InternalTuple>,
    ) -> PyResult<Self> {
        let tables = systems::Tables {
            elsevier: query_rows(elsevier),
            siris: query_rows(siris),
            auckland: query_rows(auckland),
            aurora: query_rows(aurora),
            aurora_simple: internal_rows(aurora_simple),
            aurora_and: internal_rows(aurora_and),
            aurora_w: internal_rows(aurora_w),
        };
        let port = systems::Port::new(&tables)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.0))?;
        Ok(NativePort { port })
    }

    /// Consumes the texts of a batch, the names of the systems, the mode
    /// (`"compatible"` or `"corrected"`) and a number of threads, and
    /// produces the firings as columns, in no particular order. The arguments
    /// are checked by the Python side; a name or mode that does not fit
    /// raises `ValueError` here too.
    fn detect(
        &self,
        py: Python<'_>,
        texts: Vec<String>,
        systems: Vec<String>,
        mode: &str,
        threads: usize,
    ) -> PyResult<FiringColumns> {
        let systems: Vec<systems::System> = systems
            .iter()
            .map(|s| {
                systems::System::from_name(s).ok_or_else(|| {
                    pyo3::exceptions::PyValueError::new_err(format!("unknown system: {s}"))
                })
            })
            .collect::<PyResult<_>>()?;
        let mode = match mode {
            "compatible" => systems::PortMode::Compatible,
            "corrected" => systems::PortMode::Corrected,
            _ => {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "unknown mode: {mode}"
                )))
            }
        };
        let threads = threads.max(1);
        let firings = py.detach(|| {
            let pool = rayon::ThreadPoolBuilder::new()
                .num_threads(threads)
                .build()
                .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
            pool.install(|| {
                let refs: Vec<&str> = texts.iter().map(String::as_str).collect();
                self.port
                    .detect(&refs, &systems, mode, threads)
                    .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
            })
        })?;
        let mut out: FiringColumns = Default::default();
        for f in firings {
            out.0.push(f.row);
            out.1.push(f.system.name().to_string());
            out.2.push(f.sdg);
            out.3.push(f.query_id);
            out.4.push(f.features);
        }
        Ok(out)
    }
}

/// The module `sdg_tech_tagger._native`.
#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(tokenize, m)?)?;
    m.add_function(wrap_pyfunction!(parse_tree, m)?)?;
    m.add_function(wrap_pyfunction!(standardize_term, m)?)?;
    m.add_function(wrap_pyfunction!(search_hits, m)?)?;
    m.add_class::<NativePort>()?;
    Ok(())
}
