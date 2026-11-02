//! text2sdg 1.1.2's four systems, in compatible and corrected mode.
//!
//! Elsevier, SIRIS and Auckland (`vendor/text2sdg_1.1.2/R/elsevier.R`,
//! `siris.R`, `auckland.R`): a query fires in a document when its search
//! string has a match there; all of a system's strings are searched in one
//! call of `search_features`, as `r/detect_text2sdg.R` calls them.
//!
//! Aurora (`R/aurora.R`) searches three internal tables (lines 19 to 61)
//! and three queries written out by hand (63 to 127), binds their rows in
//! that order (129 to 141) and joins them back to its query table on the
//! query text, pasting the features per document and query (149 to 163). `r/detect_text2sdg.R` calls it once per goal (defect 1 of
//! `docs/text2sdg-behaviour.md`), so each internal table is searched per
//! goal, in one call per table and column. Corrected mode is
//! `r/detect_text2sdg_corrected.R`: the six corrections of
//! `docs/contract.md`, each marked where it applies.

use std::collections::HashMap;
use std::fmt;

use rayon::prelude::*;

use crate::engine::{DocHits, Engine, Mode, Prepared};
use crate::index::Batch;

/// One of the four systems.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum System {
    Aurora,
    Elsevier,
    Siris,
    Auckland,
}

impl System {
    /// The name text2sdg gives the system in its output.
    pub fn name(self) -> &'static str {
        match self {
            System::Aurora => "Aurora",
            System::Elsevier => "Elsevier",
            System::Siris => "SIRIS",
            System::Auckland => "Auckland",
        }
    }

    /// The system of a name, as text2sdg writes it.
    pub fn from_name(name: &str) -> Option<System> {
        [
            System::Aurora,
            System::Elsevier,
            System::Siris,
            System::Auckland,
        ]
        .into_iter()
        .find(|s| s.name() == name)
    }
}

/// The two modes of the port (D008).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PortMode {
    Compatible,
    Corrected,
}

/// A row of a query table: Elsevier's, SIRIS's, Auckland's, or Aurora's
/// `aurora_queries`.
#[derive(Debug, Clone)]
pub struct QueryRow {
    pub sdg: String,
    pub query_id: i32,
    pub query: String,
}

/// A row of one of Aurora's internal tables: the query text it joins on and
/// its search strings (`correct`, and `correct 2` for `aurora_and` and
/// `aurora_w`).
#[derive(Debug, Clone)]
pub struct InternalRow {
    pub orig: String,
    pub correct: String,
    pub correct2: Option<String>,
}

/// The query tables text2sdg 1.1.2 ships (`queries/`).
#[derive(Debug, Clone)]
pub struct Tables {
    pub elsevier: Vec<QueryRow>,
    pub siris: Vec<QueryRow>,
    pub auckland: Vec<QueryRow>,
    pub aurora: Vec<QueryRow>,
    pub aurora_simple: Vec<InternalRow>,
    pub aurora_and: Vec<InternalRow>,
    pub aurora_w: Vec<InternalRow>,
}

/// An error in the query tables, found when the port is built.
#[derive(Debug, Clone)]
pub struct TablesError(pub String);

impl fmt::Display for TablesError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// One firing: a document of the batch, a query, the features.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Firing {
    pub row: u32,
    pub system: System,
    pub sdg: String,
    pub query_id: i32,
    pub features: String,
}

// The three queries `detect_aurora` writes out by hand
// (vendor/text2sdg_1.1.2/R/aurora.R, "handle special 1", "handle special 2"
// and "handle special 3"): their search strings, and the query text the
// hits are joined back on.

const SPECIAL_1: [&str; 3] = [
    "<(<physical> OR <sexual>) (<harass*>)>~3",
    "<victim*>",
    "(<city> OR <cities> OR <urban> OR <municipalit*>)",
];
const SPECIAL_1_QUERY: &str = "( \"city\"  OR  \"cities\"  OR  \"urban\"  OR  \"municipalit*\" )  W/3  ( ( \"victim*\" )  W/3  ( ( \"physical\"  OR  \"sexual\" )  W/3  ( \"harass*\" ) ) )";
const SPECIAL_1_GOAL: &str = "SDG-11";

const SPECIAL_2: [&str; 3] = [
    "(<neonatal> OR <under-five> OR ( <(<under>) (<5> OR <five>)>~2 ) OR <before fifth>)",
    "(<mortality> OR <death*>)",
    "(<reduce> OR <end> OR <ending> OR <prevent*> OR <ratio*>)",
];
const SPECIAL_2_QUERY: &str = "( (\"reduce\" OR \"end\" OR \"ending\" OR \"prevent*\" OR \"ratio*\") W/3 ((\"neonatal\" OR \"under-five\" OR ( \"under\" W/2 (\"5\" OR \"five\") ) OR \"before fifth\") W/3 (\"mortality\" OR \"death*\") ) )";

const SPECIAL_3: [&str; 3] = [
    "( <(<tobacco>) (<control*>)>~6 ) OR ( <(<health>) (<smoking>)>~3 )",
    "<(<smoking>) (<cessation> OR <quit*>)>~3",
    "<(<cessation> OR <quit*>) (<health> OR <benefit*>)>~3",
];
const SPECIAL_3_QUERY: &str = "( \"tobacco\" W/6 \"control*\" ) OR ( \"health\" W/3 \"smoking\" ) OR ((\"smoking\") W/3 (\"cessation\" OR \"quit*\") W/3 ( \"health\"  OR  \"benefit*\" ))";
const SPECIALS_2_3_GOAL: &str = "SDG-03";

/// Which internal table and column a string correction applies to.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Column {
    SimpleCorrect,
    AndCorrect,
}

/// Corrections 2, 4, 5 and 6: the piece of a search string text2sdg ships
/// and the piece that replaces it, as `STRING_CORRECTIONS` of
/// `r/detect_text2sdg_corrected.R` writes them. The shipped piece must be
/// found exactly once in its column, or the port is not built.
const STRING_CORRECTIONS: [(Column, &str, &str); 4] = [
    // correction 2 (D016): `"agricultur*" W/6 ( "sustainab*" OR "resilien*" )`
    (
        Column::SimpleCorrect,
        "( <(<agricultur*>) ( <sustainab*> OR <resilien*> )>~3)",
        "( <(<agricultur*>) ( <sustainab*> OR <resilien*> )>~6)",
    ),
    // correction 4 (D020): `("bronchitis" W/3 "chronic")`
    (
        Column::SimpleCorrect,
        "<(<bronchitis>  <chronic>)>~3",
        "<(<bronchitis>) (<chronic>)>~3",
    ),
    // correction 6 (D022): `("national" W/3 "strategy*" OR "program*")`, OR
    // bound first as Scopus reads it
    (
        Column::SimpleCorrect,
        "(<<national>  <strategy*>>~3 OR <program*>)",
        "(<(<national>) (<strategy*> OR <program*>)>~3)",
    ),
    // correction 5 (D021): the first pair of SDG-15 id 15, `prevent*` near
    // `extinction`
    (
        Column::AndCorrect,
        "<( <extinction> ) ( <species> )>~3",
        "<( <prevent*> ) ( <extinction> )>~3",
    ),
];

/// Applies the string corrections to the internal tables.
fn correct_strings(simple: &mut [InternalRow], and: &mut [InternalRow]) -> Result<(), TablesError> {
    for (column, shipped, corrected) in STRING_CORRECTIONS {
        let rows: &mut [InternalRow] = match column {
            Column::SimpleCorrect => simple,
            Column::AndCorrect => and,
        };
        let found: Vec<usize> = rows
            .iter()
            .enumerate()
            .filter(|(_, r)| r.correct.contains(shipped))
            .map(|(i, _)| i)
            .collect();
        if found.len() != 1 || rows[found[0]].correct.matches(shipped).count() != 1 {
            return Err(TablesError(format!(
                "not found exactly once in the internal tables: {shipped}"
            )));
        }
        let row = &mut rows[found[0]];
        row.correct = row.correct.replacen(shipped, corrected, 1);
    }
    Ok(())
}

/// A call of `search_features`: the strings given together, and the
/// multiplicity of their terms in it.
struct Call {
    multiplicity: Vec<u32>,
}

/// A string searched in a call, in a mode: the unit of evaluation.
type Task = (usize, usize, Mode);

/// One query of the port, with what decides whether it fires and what it
/// reports.
#[derive(Debug, Clone)]
enum Unit {
    /// Elsevier, SIRIS, Auckland, and `aurora_simple`: the string matches.
    Plain { task: Task },
    /// `aurora_and` and `aurora_w`: both strings match. In corrected mode,
    /// `check` holds the two strings in the `features` mode and whether
    /// they must share a token (correction 3) or lie within 3 (correction
    /// 1).
    Pair {
        first: Task,
        second: Task,
        check: Option<(Task, Task, PairCheck)>,
    },
    /// Special 1 and 2: the three strings match, the first within 3 of the
    /// second and the third within 3 of either.
    Distance { tasks: [Task; 3] },
    /// Special 3: the first string matches, or the second and the third;
    /// in corrected mode the second and third must share a token in the
    /// `features` mode (correction 3, D023).
    Smoking {
        tasks: [Task; 3],
        chain: Option<(Task, Task)>,
    },
}

#[derive(Debug, Clone, Copy)]
enum PairCheck {
    /// Correction 3 (D017, D018): some token satisfies both strings.
    SharedToken,
    /// Correction 1 (D010, D018): a token of the first within 3 of one of
    /// the second.
    Within3,
}

/// A query of the port and the targets its firings are reported under.
#[derive(Debug, Clone)]
struct Query {
    system: System,
    targets: Vec<(String, i32)>,
    unit: Unit,
}

/// The plan of one mode: its queries and the calls they are searched in.
struct Plan {
    queries: Vec<Query>,
    calls: Vec<Call>,
}

/// The port: the search strings compiled once, and a plan per mode.
pub struct Port {
    engine: Engine,
    compatible: Plan,
    corrected: Plan,
}

/// Collects the strings of the plans and the calls they are given in.
struct Builder {
    strings: Vec<String>,
    index: HashMap<String, usize>,
    calls: Vec<Vec<usize>>,
}

impl Builder {
    fn string(&mut self, s: &str) -> usize {
        if let Some(&i) = self.index.get(s) {
            return i;
        }
        self.strings.push(s.to_string());
        self.index.insert(s.to_string(), self.strings.len() - 1);
        self.strings.len() - 1
    }

    /// A call of the given strings; produces its number and the string
    /// indices, in order.
    fn call(&mut self, strings: &[&str]) -> (usize, Vec<usize>) {
        let ids: Vec<usize> = strings.iter().map(|s| self.string(s)).collect();
        self.calls.push(ids.clone());
        (self.calls.len() - 1, ids)
    }
}

fn goal_of(sdg: &str) -> String {
    sdg.to_string()
}

/// The plan of one mode, its calls given as string lists in `builder`.
fn plan(tables: &Tables, mode: PortMode, builder: &mut Builder) -> Result<Vec<Query>, TablesError> {
    let mut queries = Vec::new();
    let corrected = mode == PortMode::Corrected;

    // Elsevier, SIRIS, Auckland: one call each, all goals
    for (system, rows) in [
        (System::Elsevier, &tables.elsevier),
        (System::Siris, &tables.siris),
        (System::Auckland, &tables.auckland),
    ] {
        let strings: Vec<&str> = rows.iter().map(|r| r.query.as_str()).collect();
        let (call, ids) = builder.call(&strings);
        for (row, id) in rows.iter().zip(ids) {
            queries.push(Query {
                system,
                targets: vec![(row.sdg.clone(), row.query_id)],
                unit: Unit::Plain {
                    task: (id, call, Mode::UniqueHits),
                },
            });
        }
    }

    // Aurora
    let mut simple = tables.aurora_simple.clone();
    let mut and = tables.aurora_and.clone();
    if corrected {
        correct_strings(&mut simple, &mut and)?;
    }
    let mut by_text: HashMap<&str, Vec<(String, i32)>> = HashMap::new();
    for r in &tables.aurora {
        by_text
            .entry(r.query.as_str())
            .or_default()
            .push((r.sdg.clone(), r.query_id));
    }
    let mut goals: Vec<String> = tables.aurora.iter().map(|r| goal_of(&r.sdg)).collect();
    goals.sort();
    goals.dedup();

    for goal in &goals {
        // the rows of each internal table whose query text sits under this
        // goal, in table order, and the targets reported for them from this
        // goal's call: those under this goal
        let select = |rows: &[InternalRow]| -> Vec<(usize, Vec<(String, i32)>)> {
            rows.iter()
                .enumerate()
                .filter_map(|(i, r)| {
                    let targets: Vec<(String, i32)> = by_text
                        .get(r.orig.as_str())
                        .map(|t| t.iter().filter(|(s, _)| s == goal).cloned().collect())
                        .unwrap_or_default();
                    (!targets.is_empty()).then_some((i, targets))
                })
                .collect()
        };

        let rows = select(&simple);
        let strings: Vec<&str> = rows
            .iter()
            .map(|(i, _)| simple[*i].correct.as_str())
            .collect();
        let (call, ids) = builder.call(&strings);
        for ((_, targets), id) in rows.into_iter().zip(ids) {
            queries.push(Query {
                system: System::Aurora,
                targets,
                unit: Unit::Plain {
                    task: (id, call, Mode::UniqueHits),
                },
            });
        }

        for (table, check) in [
            (&and, PairCheck::SharedToken),
            (&tables.aurora_w, PairCheck::Within3),
        ] {
            let rows = select(table);
            let first: Vec<&str> = rows
                .iter()
                .map(|(i, _)| table[*i].correct.as_str())
                .collect();
            let second: Vec<&str> = rows
                .iter()
                .map(|(i, _)| table[*i].correct2.as_deref().unwrap_or(""))
                .collect();
            let (call1, ids1) = builder.call(&first);
            let (call2, ids2) = builder.call(&second);
            for (k, (_, targets)) in rows.into_iter().enumerate() {
                let t1 = (ids1[k], call1, Mode::UniqueHits);
                let t2 = (ids2[k], call2, Mode::UniqueHits);
                // corrections 1 and 3 look at the tokens of the features
                // mode, searched with the same strings in the same calls
                let check = corrected.then_some((
                    (ids1[k], call1, Mode::Features),
                    (ids2[k], call2, Mode::Features),
                    check,
                ));
                queries.push(Query {
                    system: System::Aurora,
                    targets,
                    unit: Unit::Pair {
                        first: t1,
                        second: t2,
                        check,
                    },
                });
            }
        }

        let special_targets = |text: &str| -> Result<Vec<(String, i32)>, TablesError> {
            by_text
                .get(text)
                .cloned()
                .ok_or_else(|| TablesError(format!("query not in aurora_queries: {text}")))
        };
        if goal == SPECIAL_1_GOAL {
            let (call, ids) = builder.call(&SPECIAL_1);
            queries.push(Query {
                system: System::Aurora,
                targets: special_targets(SPECIAL_1_QUERY)?,
                unit: Unit::Distance {
                    tasks: [0, 1, 2].map(|k| (ids[k], call, Mode::UniqueHits)),
                },
            });
        }
        if goal == SPECIALS_2_3_GOAL {
            let (call, ids) = builder.call(&SPECIAL_2);
            queries.push(Query {
                system: System::Aurora,
                targets: special_targets(SPECIAL_2_QUERY)?,
                unit: Unit::Distance {
                    tasks: [0, 1, 2].map(|k| (ids[k], call, Mode::UniqueHits)),
                },
            });
            let (call, ids) = builder.call(&SPECIAL_3);
            // correction 3 for the chain of special 3 (D023): each string
            // searched alone in the features mode
            let chain = if corrected {
                let (c2, i2) = builder.call(&SPECIAL_3[1..2]);
                let (c3, i3) = builder.call(&SPECIAL_3[2..3]);
                Some(((i2[0], c2, Mode::Features), (i3[0], c3, Mode::Features)))
            } else {
                None
            };
            queries.push(Query {
                system: System::Aurora,
                targets: special_targets(SPECIAL_3_QUERY)?,
                unit: Unit::Smoking {
                    tasks: [0, 1, 2].map(|k| (ids[k], call, Mode::UniqueHits)),
                    chain,
                },
            });
        }
    }
    Ok(queries)
}

impl Port {
    /// Consumes the query tables and produces the port, its search strings
    /// compiled, or an error naming what does not fit.
    pub fn new(tables: &Tables) -> Result<Port, TablesError> {
        let mut builder = Builder {
            strings: Vec::new(),
            index: HashMap::new(),
            calls: Vec::new(),
        };
        let compatible = plan(tables, PortMode::Compatible, &mut builder)?;
        let compatible_calls = builder.calls.len();
        let corrected = plan(tables, PortMode::Corrected, &mut builder)?;
        let engine = Engine::new(&builder.strings).map_err(|e| TablesError(e.to_string()))?;
        let calls: Vec<Call> = builder
            .calls
            .iter()
            .map(|c| Call {
                multiplicity: engine.multiplicity(c),
            })
            .collect();
        let mut calls = calls.into_iter();
        let compatible_calls: Vec<Call> = calls.by_ref().take(compatible_calls).collect();
        let corrected_calls: Vec<Call> = calls.collect();
        // the corrected plan numbers its calls after the compatible plan's
        let offset = compatible_calls.len();
        let corrected = corrected
            .into_iter()
            .map(|q| shift_calls(q, offset))
            .collect();
        Ok(Port {
            engine,
            compatible: Plan {
                queries: compatible,
                calls: compatible_calls,
            },
            corrected: Plan {
                queries: corrected,
                calls: corrected_calls,
            },
        })
    }

    /// Consumes the texts of a batch, the systems and the mode, and produces
    /// the firings, in no particular order. Must run inside the rayon pool
    /// that sets the number of threads; `index_threads` is the number of
    /// tantivy's indexing threads.
    pub fn detect(
        &self,
        texts: &[&str],
        systems: &[System],
        mode: PortMode,
        index_threads: usize,
    ) -> std::io::Result<Vec<Firing>> {
        let plan = match mode {
            PortMode::Compatible => &self.compatible,
            PortMode::Corrected => &self.corrected,
        };
        let batch = Batch::build(texts, index_threads).map_err(std::io::Error::other)?;
        let prepared = self.engine.prepare(&batch)?;
        let queries: Vec<&Query> = plan
            .queries
            .iter()
            .filter(|q| systems.contains(&q.system))
            .collect();
        let mut tasks: Vec<Task> = queries.iter().flat_map(|q| q.unit.tasks()).collect();
        tasks.sort_unstable_by_key(|&(s, c, m)| (s, c, m == Mode::Features));
        tasks.dedup();
        let results: HashMap<Task, Vec<(u32, DocHits)>> = tasks
            .par_iter()
            .map(|&t| (t, evaluate(&prepared, plan, t)))
            .collect();
        let firings = queries
            .par_iter()
            .flat_map_iter(|q| fire(q, &results, &batch, texts))
            .collect();
        Ok(firings)
    }
}

fn shift_calls(mut q: Query, offset: usize) -> Query {
    let shift = |t: &mut Task| t.1 -= offset;
    match &mut q.unit {
        Unit::Plain { task } => shift(task),
        Unit::Pair {
            first,
            second,
            check,
        } => {
            shift(first);
            shift(second);
            if let Some((a, b, _)) = check {
                shift(a);
                shift(b);
            }
        }
        Unit::Distance { tasks } => tasks.iter_mut().for_each(shift),
        Unit::Smoking { tasks, chain } => {
            tasks.iter_mut().for_each(shift);
            if let Some((a, b)) = chain {
                shift(a);
                shift(b);
            }
        }
    }
    q
}

impl Unit {
    fn tasks(&self) -> Vec<Task> {
        match self {
            Unit::Plain { task } => vec![*task],
            Unit::Pair {
                first,
                second,
                check,
            } => {
                let mut v = vec![*first, *second];
                if let Some((a, b, _)) = check {
                    v.extend([*a, *b]);
                }
                v
            }
            Unit::Distance { tasks } => tasks.to_vec(),
            Unit::Smoking { tasks, chain } => {
                let mut v = tasks.to_vec();
                if let Some((a, b)) = chain {
                    v.extend([*a, *b]);
                }
                v
            }
        }
    }
}

fn evaluate(
    prepared: &Prepared<'_>,
    plan: &Plan,
    (string, call, mode): Task,
) -> Vec<(u32, DocHits)> {
    prepared.evaluate(string, mode, &plan.calls[call].multiplicity)
}

/// The hits of a task in each document, as a map.
fn by_doc(results: &HashMap<Task, Vec<(u32, DocHits)>>, task: Task) -> HashMap<u32, &DocHits> {
    results[&task].iter().map(|(r, h)| (*r, h)).collect()
}

/// `w_n` (`vendor/text2sdg_1.1.2/R/helper.R:44-47`): whether some token of `x`
/// lies within 3 positions of some token of `y`.
fn w_n(x: &[u32], y: &[u32]) -> bool {
    x.iter().any(|&a| y.iter().any(|&b| a.abs_diff(b) <= 3))
}

/// Whether two sorted token lists share a token.
fn share(x: &[u32], y: &[u32]) -> bool {
    let (mut i, mut j) = (0, 0);
    while i < x.len() && j < y.len() {
        match x[i].cmp(&y[j]) {
            std::cmp::Ordering::Less => i += 1,
            std::cmp::Ordering::Greater => j += 1,
            std::cmp::Ordering::Equal => return true,
        }
    }
    false
}

/// The firings of one query, one per document and target.
fn fire(
    q: &Query,
    results: &HashMap<Task, Vec<(u32, DocHits)>>,
    batch: &Batch,
    texts: &[&str],
) -> Vec<Firing> {
    // per document, the hit tokens to report, in the order text2sdg pastes
    // them
    let mut fired: Vec<(u32, Vec<u32>)> = Vec::new();
    match &q.unit {
        Unit::Plain { task } => {
            for (row, hits) in &results[task] {
                fired.push((*row, hits.clone()));
            }
        }
        Unit::Pair {
            first,
            second,
            check,
        } => {
            // R/aurora.R: the rows of the first string, then those of the
            // second, where both match
            let second = by_doc(results, *second);
            let checks = check.map(|(a, b, kind)| (by_doc(results, a), by_doc(results, b), kind));
            for (row, hits1) in &results[first] {
                let Some(hits2) = second.get(row) else {
                    continue;
                };
                if let Some((a, b, kind)) = &checks {
                    let (Some(fa), Some(fb)) = (a.get(row), b.get(row)) else {
                        continue;
                    };
                    let keep = match kind {
                        PairCheck::SharedToken => share(fa, fb),
                        PairCheck::Within3 => w_n(fa, fb),
                    };
                    if !keep {
                        continue;
                    }
                }
                let mut tokens = hits1.clone();
                tokens.extend_from_slice(hits2);
                fired.push((*row, tokens));
            }
        }
        Unit::Distance { tasks } => {
            // R/aurora.R, special 1 and 2: all three strings, then w_n on the
            // tokens of the unique_hits mode
            let maps: Vec<_> = tasks.iter().map(|t| by_doc(results, *t)).collect();
            for (row, h1) in &results[&tasks[0]] {
                let (Some(h2), Some(h3)) = (maps[1].get(row), maps[2].get(row)) else {
                    continue;
                };
                let mut h12: Vec<u32> = h1.iter().chain(h2.iter()).copied().collect();
                h12.sort_unstable();
                if w_n(h1, h2) && w_n(h3, &h12) {
                    fired.push((*row, merge_by_token(&[h1, h2, h3])));
                }
            }
        }
        Unit::Smoking { tasks, chain } => {
            let maps: Vec<_> = tasks.iter().map(|t| by_doc(results, *t)).collect();
            let chains = chain.map(|(a, b)| (by_doc(results, a), by_doc(results, b)));
            let mut rows: Vec<u32> = maps.iter().flat_map(|m| m.keys().copied()).collect();
            rows.sort_unstable();
            rows.dedup();
            for row in rows {
                let h: Vec<Option<&&DocHits>> = maps.iter().map(|m| m.get(&row)).collect();
                let chained = match &chains {
                    None => true,
                    Some((a, b)) => match (a.get(&row), b.get(&row)) {
                        (Some(x), Some(y)) => share(x, y),
                        _ => false,
                    },
                };
                let fires = h[0].is_some() || (h[1].is_some() && h[2].is_some() && chained);
                if fires {
                    let present: Vec<&DocHits> = h.iter().flatten().map(|x| **x).collect();
                    fired.push((row, merge_by_token(&present)));
                }
            }
        }
    }
    let mut out = Vec::with_capacity(fired.len() * q.targets.len());
    for (row, tokens) in fired {
        let features = features(
            q.system,
            &batch.docs[row as usize],
            texts[row as usize],
            &tokens,
        );
        for (sdg, query_id) in &q.targets {
            out.push(Firing {
                row,
                system: q.system,
                sdg: sdg.clone(),
                query_id: *query_id,
                features: features.clone(),
            });
        }
    }
    out
}

/// The tokens of several strings of one call in one document, as
/// `search_features` returns them: by token, the strings in call order at
/// one token.
fn merge_by_token(lists: &[&DocHits]) -> Vec<u32> {
    let mut all: Vec<(u32, usize)> = lists
        .iter()
        .enumerate()
        .flat_map(|(k, l)| l.iter().map(move |&t| (t, k)))
        .collect();
    all.sort_unstable();
    all.into_iter().map(|(t, _)| t).collect()
}

/// The `features` string: the tokens as written in the document, joined
/// with ", " (`toString`, `R/elsevier.R:30`, `R/auckland.R:30`,
/// `R/aurora.R:157`); SIRIS keeps each distinct token once, in the order of
/// first appearance (`toString(unique(feature))`, `R/siris.R:31`).
fn features(system: System, doc: &crate::tokens::DocTokens, text: &str, tokens: &[u32]) -> String {
    let mut words: Vec<&str> = tokens
        .iter()
        .map(|&t| {
            let (s, e) = doc.spans[t as usize - 1];
            &text[s as usize..e as usize]
        })
        .collect();
    if system == System::Siris {
        let mut seen = std::collections::HashSet::new();
        words.retain(|w| seen.insert(*w));
    }
    words.join(", ")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn w_n_is_a_distance_of_at_most_three() {
        assert!(w_n(&[1, 20], &[23]));
        assert!(!w_n(&[1, 19], &[23]));
        assert!(!w_n(&[], &[1]));
    }

    #[test]
    fn share_finds_a_common_token() {
        assert!(share(&[1, 4, 9], &[2, 9]));
        assert!(!share(&[1, 4], &[2, 3, 5]));
    }

    #[test]
    fn merge_keeps_call_order_at_one_token() {
        let a = vec![3, 7];
        let b = vec![3, 5];
        assert_eq!(merge_by_token(&[&a, &b]), vec![3, 3, 5, 7]);
    }

    #[test]
    fn a_correction_that_does_not_find_its_string_stops_the_build() {
        let row = |s: &str| InternalRow {
            orig: "q".into(),
            correct: s.into(),
            correct2: None,
        };
        let mut simple = vec![row("<a>")];
        let mut and = vec![row("<b>")];
        assert!(correct_strings(&mut simple, &mut and).is_err());
    }
}
