//! corpustools' `search_features`, evaluated one document at a time.
//!
//! A port of `vendor/corpustools_0.5.2/R/search.r` (`lucene_like`, `lookup`,
//! `get_*_hit`, `remove_duplicate_hit_id`), `R/util.r` (`global_id`) and
//! `src/hit_ids_and.cpp`, `src/hit_ids_proximity.cpp`,
//! `src/hit_ids_sequence.cpp`, following the study's reimplementation of
//! them step by step. Where corpustools does something surprising, the code
//! does the same and says so.
//!
//! corpustools evaluates a search string over a whole corpus at once, and
//! numbers its matches across documents. Two of its steps can then let one
//! document's numbers reach another's: `global_id` offsets the numbers of an
//! `OR`'s members by the last number of the member before, not its largest,
//! so two matches in different documents can share a number, and
//! `remove_duplicate_hit_id` then weighs and removes matches by number
//! across documents. What a document gets would then depend on which other
//! documents share its batch. The port evaluates each document alone: it
//! returns what corpustools returns for a corpus made of that document, which
//! does not depend on the batch, the order of the input or the number of
//! threads (D007).
//!
//! The ghost flag, case sensitivity, directed proximity and sentence context
//! are not implemented; `query::parse` refuses the flags, and text2sdg
//! searches documents, not sentences.

use std::collections::{HashMap, HashSet};
use std::fmt;

use rayon::prelude::*;

use crate::index::{Batch, WordPostings};
use crate::query::{self, Node, Relation};
use crate::terms::{self, Pattern};

/// The two modes of `search_features` (D018).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Mode {
    /// `unique_hits`, the mode text2sdg searches in: whole matches, each
    /// token assigned once.
    UniqueHits,
    /// `features`: every token that satisfies the string.
    Features,
}

/// An error in a search string: corpustools' own, or a construction the
/// port refuses.
#[derive(Debug, Clone)]
pub struct SearchStringError {
    pub string: String,
    pub message: String,
}

impl fmt::Display for SearchStringError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "search string {:?}: {}", self.string, self.message)
    }
}

/// A node of a compiled search string: a term member refers to the string's
/// own numbering of its distinct terms.
#[derive(Debug, Clone)]
enum CNode {
    Term(Vec<usize>),
    Group {
        relation: Relation,
        window: f64,
        members: Vec<CNode>,
    },
}

/// A search string ready to be evaluated.
#[derive(Debug, Clone)]
struct Compiled {
    root: CNode,
    /// The global term of each of the string's own terms.
    terms: Vec<usize>,
}

/// A term of some search string, as it is looked up.
#[derive(Debug, Clone)]
struct TermSpec {
    words: Vec<String>,
    is_pattern: Vec<bool>,
}

/// The search strings of a run, parsed and compiled once.
pub struct Engine {
    strings: Vec<Compiled>,
    terms: Vec<TermSpec>,
    patterns: Vec<(String, Option<Pattern>)>,
}

fn compile(
    node: &Node,
    local: &mut HashMap<String, usize>,
    local_terms: &mut Vec<String>,
) -> Result<CNode, String> {
    match node {
        Node::Term(strings) => {
            // lookup(): a term given twice in one member is looked up once
            let mut ids: Vec<usize> = Vec::new();
            for s in strings {
                let id = *local.entry(s.clone()).or_insert_with(|| {
                    local_terms.push(s.clone());
                    local_terms.len() - 1
                });
                if !ids.contains(&id) {
                    ids.push(id);
                }
            }
            Ok(CNode::Term(ids))
        }
        Node::Group {
            relation,
            window,
            members,
        } => {
            if *relation == Relation::Proximity && members.len() > 1 {
                for m in members {
                    if let Node::Group {
                        relation: Relation::Proximity | Relation::And,
                        ..
                    } = m
                    {
                        // lucene_like stops on this when it evaluates it
                        return Err(
                            "Cannot nest proximity or AND search within a proximity search".into(),
                        );
                    }
                }
            }
            Ok(CNode::Group {
                relation: *relation,
                window: f64::from(*window),
                members: members
                    .iter()
                    .map(|m| compile(m, local, local_terms))
                    .collect::<Result<_, _>>()?,
            })
        }
    }
}

/// Where a term occurs in a document: its first token and its length in
/// tokens.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Occ {
    token_id: u32,
    ngram: u32,
}

/// The occurrences of every term in one batch.
pub struct Prepared<'a> {
    engine: &'a Engine,
    /// Per term: its occurrences, sorted by document then start.
    occ: Vec<Vec<Occ>>,
    /// Per term: (document, start, end) of the run of each document in
    /// `occ`.
    runs: Vec<Vec<(u32, u32, u32)>>,
}

impl Engine {
    /// Consumes search strings and produces them parsed and compiled, or the
    /// first error, naming its string.
    pub fn new(strings: &[String]) -> Result<Engine, SearchStringError> {
        let mut global: HashMap<String, usize> = HashMap::new();
        let mut terms: Vec<TermSpec> = Vec::new();
        let mut pattern_ids: HashMap<String, usize> = HashMap::new();
        let mut patterns = Vec::new();
        let mut compiled = Vec::with_capacity(strings.len());
        for s in strings {
            let fail = |message: String| SearchStringError {
                string: s.clone(),
                message,
            };
            let tree = query::parse(s).map_err(|e| fail(e.0))?;
            let mut local = HashMap::new();
            let mut local_terms = Vec::new();
            let root = compile(&tree, &mut local, &mut local_terms).map_err(fail)?;
            let ids = local_terms
                .into_iter()
                .map(|t| {
                    *global.entry(t.clone()).or_insert_with(|| {
                        let words = terms::words(&t);
                        let is_pattern: Vec<bool> =
                            words.iter().map(|w| terms::is_pattern(w)).collect();
                        for (w, &p) in words.iter().zip(&is_pattern) {
                            if p && !pattern_ids.contains_key(w) {
                                pattern_ids.insert(w.clone(), patterns.len());
                                patterns.push((w.clone(), terms::pattern(w)));
                            }
                        }
                        terms.push(TermSpec { words, is_pattern });
                        terms.len() - 1
                    })
                })
                .collect();
            compiled.push(Compiled { root, terms: ids });
        }
        Ok(Engine {
            strings: compiled,
            terms,
            patterns,
        })
    }

    /// The number of search strings.
    pub fn len(&self) -> usize {
        self.strings.len()
    }

    /// Whether there is no search string.
    pub fn is_empty(&self) -> bool {
        self.strings.is_empty()
    }

    /// Consumes the indices of the search strings given to `search_features`
    /// in one call and produces, for every term, how many times corpustools
    /// holds it in that call's dictionary: once for each string of the call
    /// that uses it (`R/query.r:4`, `parse_queries` stacks the distinct
    /// terms of each string, `query_terms` at `R/query.r:92-95`, without
    /// making them distinct across strings). Each copy gives every
    /// occurrence of the term once more (`R/search.r:5-31`,
    /// `get_dict_results`, and `R/search.r:164`, `lookup`).
    pub fn multiplicity(&self, call: &[usize]) -> Vec<u32> {
        let mut out = vec![0u32; self.terms.len()];
        for &s in call {
            for &t in &self.strings[s].terms {
                out[t] += 1;
            }
        }
        out
    }

    /// Consumes a batch and produces the occurrences of every term in it.
    pub fn prepare<'a>(&'a self, batch: &Batch) -> std::io::Result<Prepared<'a>> {
        // the words each pattern covers in this batch (expand_wildcards)
        let expansions: Vec<Vec<String>> = self
            .patterns
            .par_iter()
            .map(|(_, p)| match p {
                Some(p) => batch.expand(p),
                None => Ok(Vec::new()),
            })
            .collect::<Result<_, _>>()?;
        let pattern_of: HashMap<&str, usize> = self
            .patterns
            .iter()
            .enumerate()
            .map(|(i, (w, _))| (w.as_str(), i))
            .collect();

        // every word sequence of every term (collapse_dict)
        let sequences: Vec<Vec<Vec<&str>>> = self
            .terms
            .iter()
            .map(|t| sequences(t, &pattern_of, &expansions))
            .collect();

        // the postings of the first word of each sequence
        let firsts: HashSet<&str> = sequences
            .iter()
            .flatten()
            .filter_map(|s| s.first().copied())
            .collect();
        let firsts: Vec<&str> = firsts.into_iter().collect();
        let postings: Vec<WordPostings> = firsts
            .par_iter()
            .map(|w| batch.postings(w))
            .collect::<Result<_, _>>()?;
        let postings: HashMap<&str, WordPostings> = firsts.into_iter().zip(postings).collect();

        let (occ, runs): (Vec<_>, Vec<_>) = sequences
            .par_iter()
            .map(|seqs| occurrences(batch, seqs, &postings))
            .unzip();
        Ok(Prepared {
            engine: self,
            occ,
            runs,
        })
    }
}

/// `expand_wildcards` (`R/search_dictionary.r:442-503`, the merge at
/// 494-500): the word sequences a term
/// is looked up as. corpustools merges the expansions of a term's pattern
/// words on the term, not on the word: for each word an expansion of one
/// pattern covers, every pattern word of the term is replaced by that word,
/// and every word is repeated as often as that pattern occurs in the term.
/// So a term with two pattern words only matches one token repeated. A word
/// that is not in the batch leaves the sequence without a match
/// (`replace_string_with_factor`).
fn sequences<'a>(
    term: &'a TermSpec,
    pattern_of: &HashMap<&str, usize>,
    expansions: &'a [Vec<String>],
) -> Vec<Vec<&'a str>> {
    if !term.is_pattern.iter().any(|&p| p) {
        return vec![term.words.iter().map(String::as_str).collect()];
    }
    let mut order: Vec<&str> = Vec::new();
    let mut counts: HashMap<&str, usize> = HashMap::new();
    for (w, &p) in term.words.iter().zip(&term.is_pattern) {
        if p {
            if !counts.contains_key(w.as_str()) {
                order.push(w);
            }
            *counts.entry(w).or_insert(0) += 1;
        }
    }
    let mut out = Vec::new();
    for p in order {
        let n = counts[p];
        for e in &expansions[pattern_of[p]] {
            let mut seq = Vec::with_capacity(term.words.len() * n);
            for (w, &is_p) in term.words.iter().zip(&term.is_pattern) {
                let word = if is_p { e.as_str() } else { w.as_str() };
                seq.extend(std::iter::repeat_n(word, n));
            }
            out.push(seq);
        }
    }
    out
}

/// The occurrences of one term (`src/dictionary_lookup.cpp:40-79`): its words on
/// consecutive lookup rows of one document. Sorted by document and first
/// row; at one first row, in the order of the term's sequences. The first
/// token is the token of the first row and the length counts the tokens
/// from the first row's to the last row's (`get_dict_results`).
#[allow(clippy::type_complexity)]
fn occurrences(
    batch: &Batch,
    seqs: &[Vec<&str>],
    postings: &HashMap<&str, WordPostings>,
) -> (Vec<Occ>, Vec<(u32, u32, u32)>) {
    let mut found: Vec<(u32, u32, usize, Occ)> = Vec::new();
    for (k, seq) in seqs.iter().enumerate() {
        let Some(first) = seq.first() else { continue };
        let Some(list) = postings.get(first) else {
            continue;
        };
        for (row, positions) in list {
            let doc = &batch.docs[*row as usize];
            for &p in positions {
                let p = p as usize;
                let end = p + seq.len();
                if end > doc.row_count() {
                    continue;
                }
                if (1..seq.len()).all(|m| doc.row(p + m) == seq[m]) {
                    let first_token = doc.token_of_row(p);
                    let last_token = doc.token_of_row(end - 1);
                    found.push((
                        *row,
                        p as u32,
                        k,
                        Occ {
                            token_id: first_token + 1,
                            ngram: last_token - first_token + 1,
                        },
                    ));
                }
            }
        }
    }
    found.sort_unstable_by_key(|&(row, p, k, _)| (row, p, k));
    let mut runs: Vec<(u32, u32, u32)> = Vec::new();
    for (i, &(row, ..)) in found.iter().enumerate() {
        match runs.last_mut() {
            Some(run) if run.0 == row => run.2 = i as u32 + 1,
            _ => runs.push((row, i as u32, i as u32 + 1)),
        }
    }
    (found.into_iter().map(|(.., o)| o).collect(), runs)
}

/// The rows of one search string's result in one document: the token ids
/// of `search_features`' hit table, each match of n tokens spread over its n
/// tokens, in increasing order with repetition.
pub type DocHits = Vec<u32>;

impl Prepared<'_> {
    /// Consumes the index of a search string, a mode and the multiplicity of
    /// the terms in the call the string is searched in
    /// (`Engine::multiplicity`), and produces, for each document of the
    /// batch in which the string has a match, its batch index and its hit
    /// tokens, in increasing order of the index.
    pub fn evaluate(&self, string: usize, mode: Mode, multiplicity: &[u32]) -> Vec<(u32, DocHits)> {
        let compiled = &self.engine.strings[string];
        let mut entries: Vec<(u32, usize, u32, u32)> = Vec::new();
        for (local, &global) in compiled.terms.iter().enumerate() {
            for &(row, start, end) in &self.runs[global] {
                entries.push((row, local, start, end));
            }
        }
        entries.sort_unstable_by_key(|e| (e.0, e.1));
        let groups: Vec<&[(u32, usize, u32, u32)]> = entries.chunk_by(|a, b| a.0 == b.0).collect();
        let run = |group: &[(u32, usize, u32, u32)], ranges: &mut Vec<Option<(u32, u32)>>| {
            for &(_, local, s, e) in group {
                ranges[local] = Some((s, e));
            }
            let ctx = DocContext {
                prepared: self,
                compiled,
                ranges,
                multiplicity,
                features: mode == Mode::Features,
            };
            let out = ctx.search();
            for &(_, local, ..) in group {
                ranges[local] = None;
            }
            out.map(|hits| (group[0].0, hits))
        };
        let n_terms = compiled.terms.len();
        if groups.len() < 64 {
            let mut ranges = vec![None; n_terms];
            groups.iter().filter_map(|g| run(g, &mut ranges)).collect()
        } else {
            groups
                .par_iter()
                .map_init(|| vec![None; n_terms], |ranges, g| run(g, ranges))
                .flatten()
                .collect()
        }
    }
}

/// One search string in one document.
struct DocContext<'a> {
    prepared: &'a Prepared<'a>,
    compiled: &'a Compiled,
    /// Per term of the string: its run in the document, if it occurs.
    ranges: &'a [Option<(u32, u32)>],
    /// Per global term: how many copies the call's dictionary holds.
    multiplicity: &'a [u32],
    features: bool,
}

/// A row of corpustools' hit table at some level of `lucene_like`.
#[derive(Debug, Clone)]
struct Row {
    token_id: u32,
    ngram: u32,
    /// `.group_i`: the path of member numbers to the term, for `AND`.
    group: String,
    /// `.term_i`: the member of the current level the row belongs to.
    term_i: u32,
    /// `.seq_i`: the position in a nested sequence, NA as `None`.
    seq_i: Option<f64>,
    /// `hit_id`, NA as `None`.
    hit_id: Option<f64>,
}

/// A hit table: its rows, and which of the optional columns it has.
struct Table {
    rows: Vec<Row>,
    has_hit_id: bool,
    has_seq_i: bool,
}

impl DocContext<'_> {
    /// `search_features` for one string in one document: the hit tokens, or
    /// `None` without a match. A term match of n tokens gives its n tokens
    /// (`R/search_features.r:240-244`); text2sdg pastes them in token order
    /// (`R/search_features.r:247`), so their order is all that is kept.
    fn search(&self) -> Option<DocHits> {
        let CNode::Group {
            relation,
            window,
            members,
        } = &self.compiled.root
        else {
            unreachable!("the root of a parsed string is a group");
        };
        let table = self.lucene_like(*relation, *window, members, Relation::Empty, 1)?;
        let mut hits: Vec<u32> = table
            .rows
            .iter()
            .flat_map(|r| r.token_id..r.token_id + r.ngram)
            .collect();
        hits.sort_unstable();
        // remove_duplicate_hit_id can remove every match of a string: the
        // string then has no row, as if it had never matched (R/search.r:
        // 232-257, R/search_features.r:236-238)
        (!hits.is_empty()).then_some(hits)
    }

    /// `lookup` (`R/search.r:152-172`): the rows of a term member, term by term in the member's
    /// order, each term's rows in the order of its occurrences, each
    /// occurrence as many times as the call's dictionary holds the term.
    fn lookup(&self, terms: &[usize]) -> Option<Table> {
        let mut rows = Vec::new();
        for &local in terms {
            if let Some((s, e)) = self.ranges[local] {
                let global = self.compiled.terms[local];
                let copies = self.multiplicity[global].max(1);
                for o in &self.prepared.occ[global][s as usize..e as usize] {
                    for _ in 0..copies {
                        rows.push(Row {
                            token_id: o.token_id,
                            ngram: o.ngram,
                            group: String::new(),
                            term_i: 0,
                            seq_i: None,
                            hit_id: None,
                        });
                    }
                }
            }
        }
        (!rows.is_empty()).then_some(Table {
            rows,
            has_hit_id: false,
            has_seq_i: false,
        })
    }

    /// `lucene_like` (`R/search.r:86-150`), for one level of the tree. A
    /// level with one nested member is that member (100-104); a member under
    /// `AND`, a proximity or a sequence is evaluated in the features fashion
    /// (135-136); rows without a hit id are dropped (144); the top level in
    /// the `unique_hits` mode goes through `remove_duplicate_hit_id` (147).
    fn lucene_like(
        &self,
        relation: Relation,
        window: f64,
        members: &[CNode],
        parent: Relation,
        level: u32,
    ) -> Option<Table> {
        let unique = !self.features;
        let nterms = members.len();
        let multi = matches!(
            relation,
            Relation::Proximity | Relation::Sequence | Relation::And
        );
        let mut hit_list: Vec<Table> = Vec::new();
        for (j0, q) in members.iter().enumerate() {
            let j = j0 as u32 + 1;
            let jhits = match q {
                CNode::Group {
                    relation: q_relation,
                    window: q_window,
                    members: q_members,
                } => {
                    let jhits =
                        self.lucene_like(*q_relation, *q_window, q_members, relation, level + 1);
                    if nterms == 1 {
                        // a level with one nested member is that member
                        if level == 1 && unique {
                            return jhits.map(remove_duplicate_hit_id);
                        }
                        return jhits;
                    }
                    jhits.map(|mut t| {
                        if *q_relation == Relation::Sequence {
                            for r in &mut t.rows {
                                r.seq_i = Some(f64::from(r.term_i));
                            }
                            t.has_seq_i = true;
                        }
                        if multi {
                            for r in &mut t.rows {
                                r.group = format!("{j}_{}", r.group);
                            }
                        }
                        t
                    })
                }
                CNode::Term(terms) => self.lookup(terms).map(|mut t| {
                    if multi {
                        let g = format!("{j}_");
                        for r in &mut t.rows {
                            r.group.clone_from(&g);
                        }
                    }
                    t
                }),
            };
            match jhits {
                None => {
                    if multi || nterms == 1 {
                        return None;
                    }
                }
                Some(mut t) => {
                    for r in &mut t.rows {
                        r.term_i = j;
                    }
                    hit_list.push(t);
                }
            }
        }

        let has_hit_id = hit_list.iter().any(|t| t.has_hit_id);
        let has_seq_i = hit_list.iter().any(|t| t.has_seq_i);
        let rows: Vec<Row> = hit_list.into_iter().flat_map(|t| t.rows).collect();
        if rows.is_empty() {
            return None;
        }
        let mut table = Table {
            rows,
            has_hit_id,
            has_seq_i,
        };
        let feature_mode = self.features
            || matches!(
                parent,
                Relation::And | Relation::Proximity | Relation::Sequence
            );
        let n = nterms as u32;
        match relation {
            Relation::And => {
                sort_rows(&mut table.rows);
                let ids = and_hit_ids(&table.rows, n, feature_mode);
                assign(&mut table, ids);
            }
            Relation::Not => get_not_hit(&mut table, n),
            Relation::Proximity => {
                sort_rows(&mut table.rows);
                let ids = proximity_hit_ids(&table.rows, n, window, table.has_seq_i, feature_mode);
                assign(&mut table, ids);
            }
            Relation::Or | Relation::Empty => get_or_hit(&mut table),
            Relation::Sequence => {
                sort_rows(&mut table.rows);
                let ids = sequence_hit_ids(&table.rows, n);
                assign(&mut table, ids);
            }
        }
        table.rows.retain(|r| r.hit_id.is_some_and(|h| h > 0.0));
        if table.rows.is_empty() {
            return None;
        }
        if level == 1 && unique {
            table = remove_duplicate_hit_id(table);
        }
        Some(table)
    }
}

/// `setorderv(d, c('doc_id', 'token_id', '.term_i'))` (`R/search.r:176`,
/// 185, 195, 206), stable, in one document.
fn sort_rows(rows: &mut [Row]) {
    rows.sort_by_key(|r| (r.token_id, r.term_i));
}

fn assign(table: &mut Table, ids: Vec<f64>) {
    for (r, id) in table.rows.iter_mut().zip(ids) {
        r.hit_id = Some(id);
    }
    table.has_hit_id = true;
}

/// `proximity_hit_ids_cpp` (`src/hit_ids_proximity.cpp:23-82`), undirected
/// and without ghost terms. From each
/// row, the rows within `window` positions after it are scanned. In the
/// `unique_hits` mode the first unassigned row of each member not yet seen
/// is taken, and a full set gets a new number; in the `features` mode every
/// row in the window is taken, and a full set is numbered 1.
fn proximity_hit_ids(
    rows: &[Row],
    n_unique: u32,
    window: f64,
    use_seq: bool,
    feature_mode: bool,
) -> Vec<f64> {
    let n = rows.len();
    let mut out = vec![0.0f64; n];
    let mut hit_id = 1.0;
    let mut tracker: std::collections::BTreeMap<u32, std::collections::BTreeSet<usize>> =
        Default::default();
    for i in 0..n {
        for iw in i..n {
            if f64::from(rows[iw].token_id) - f64::from(rows[i].token_id) > window {
                break;
            }
            if !feature_mode {
                if out[iw] > 0.0 {
                    continue;
                }
                if tracker.contains_key(&rows[iw].term_i) {
                    continue;
                }
            }
            tracker.entry(rows[iw].term_i).or_default().insert(iw);
            if use_seq && rows[iw].seq_i.is_some() {
                let more = get_sequence(iw, rows);
                tracker.entry(rows[iw].term_i).or_default().extend(more);
            }
            if !feature_mode && tracker.len() as u32 == n_unique {
                break;
            }
        }
        if tracker.len() as u32 == n_unique {
            for positions in tracker.values() {
                for &p in positions {
                    out[p] = hit_id;
                }
            }
            if !feature_mode {
                hit_id += 1.0;
            }
        }
        tracker.clear();
    }
    out
}

/// `get_sequence` (`src/hit_ids_proximity.cpp:5-20`): the rows that follow `iw` in
/// the table and continue its nested sequence. An NA position compares
/// unequal, as NaN does in C++.
fn get_sequence(iw: usize, rows: &[Row]) -> Vec<usize> {
    let mut out = Vec::new();
    let v = rows[iw].term_i;
    let mut lag = iw;
    for si in iw + 1..rows.len() {
        let posdif = i64::from(rows[si].token_id) - i64::from(rows[lag].token_id);
        if !(0..=1).contains(&posdif) {
            break;
        }
        match (rows[si].seq_i, rows[lag].seq_i) {
            (Some(a), Some(b)) if a == b + 1.0 => {}
            _ => break,
        }
        if rows[si].term_i != v {
            continue;
        }
        out.push(si);
        lag = si;
    }
    out
}

/// `match_shortest` (`src/hit_ids_and.cpp:5-11`): whether `x` and one of the groups
/// agree on the length of the shorter.
fn match_shortest(x: &str, groups: &HashSet<String>) -> bool {
    groups.iter().any(|y| {
        let n = x.len().min(y.len());
        x.as_bytes()[..n] == y.as_bytes()[..n]
    })
}

/// `AND_hit_ids_cpp` (`src/hit_ids_and.cpp:15-67`), without ghost terms:
/// like the proximity, over the rest
/// of the document. In the `unique_hits` mode a member already seen is
/// skipped unless its group differs from those seen for it; a group is
/// always set under an `AND`, so the scan never stops early.
fn and_hit_ids(rows: &[Row], n_unique: u32, feature_mode: bool) -> Vec<f64> {
    let n = rows.len();
    let mut out = vec![0.0f64; n];
    let mut hit_id = 1.0;
    let mut tracker: std::collections::BTreeMap<u32, std::collections::BTreeSet<usize>> =
        Default::default();
    let mut group_tracker: HashMap<u32, HashSet<String>> = HashMap::new();
    for i in 0..n {
        for iw in i..n {
            let r = &rows[iw];
            if !feature_mode {
                if out[iw] > 0.0 {
                    continue;
                }
                if tracker.contains_key(&r.term_i) {
                    if r.group.is_empty() {
                        continue;
                    }
                    // std::map's operator[] creates the entry it reads
                    if match_shortest(&r.group, group_tracker.entry(r.term_i).or_default()) {
                        continue;
                    }
                }
            }
            tracker.entry(r.term_i).or_default().insert(iw);
            if !r.group.is_empty() {
                group_tracker
                    .entry(r.term_i)
                    .or_default()
                    .insert(r.group.clone());
            }
            if !feature_mode && group_tracker.is_empty() && tracker.len() as u32 == n_unique {
                break;
            }
        }
        if tracker.len() as u32 == n_unique {
            for positions in tracker.values() {
                for &p in positions {
                    out[p] = hit_id;
                }
            }
            if !feature_mode {
                hit_id += 1.0;
            }
        }
        tracker.clear();
        group_tracker.clear();
    }
    out
}

/// `sequence_hit_ids_cpp` (`src/hit_ids_sequence.cpp:6-35`): the members on
/// consecutive rows of the sorted
/// table, member k at most k positions after the first.
fn sequence_hit_ids(rows: &[Row], length: u32) -> Vec<f64> {
    let n = rows.len();
    let length = length as usize;
    let mut out = vec![0.0f64; n];
    let mut hit_id = 1.0;
    for i in 0..n {
        for s in 0..length {
            if i + s >= n {
                break;
            }
            if out[i + s] > 0.0 {
                continue;
            }
            if rows[i + s].term_i as usize != s + 1 {
                break;
            }
            if i64::from(rows[i + s].token_id) - i64::from(rows[i].token_id) > s as i64 {
                break;
            }
            if s == length - 1 {
                for f in 0..length {
                    out[i + f] = hit_id;
                }
                hit_id += 1.0;
                break;
            }
        }
    }
    out
}

/// `global_id` (`R/util.r:36-50`), as written: the numbers of each group after
/// the first are offset by the sum of the last number of each group before
/// it (not their largest), the groups being the runs that start where a
/// value first appears.
fn global_id(group: &[u32], ids: &[f64]) -> Vec<f64> {
    let first = group[0];
    if group.iter().all(|&g| g == first) {
        return ids.to_vec();
    }
    let mut seen = HashSet::new();
    let starts: Vec<usize> = group
        .iter()
        .enumerate()
        .filter(|(_, g)| seen.insert(**g))
        .map(|(k, _)| k)
        .collect();
    let mut out = ids.to_vec();
    let mut add = 0.0;
    for (k, &start) in starts.iter().enumerate() {
        if start > 0 {
            add += ids[start - 1];
        }
        let end = starts.get(k + 1).copied().unwrap_or(ids.len());
        for v in &mut out[start..end] {
            *v += add;
        }
    }
    out
}

/// `get_OR_hit` (`R/search.r:216-230`): each row keeps the number it had
/// from a nested member, a
/// row without one gets the next number after the largest, or its row
/// number when no row has one; then the members are made distinct with
/// `global_id`.
fn get_or_hit(table: &mut Table) {
    let mut h: Vec<Option<f64>> = if table.has_hit_id {
        table.rows.iter().map(|r| r.hit_id).collect()
    } else {
        (1..=table.rows.len()).map(|k| Some(k as f64)).collect()
    };
    if h.iter().any(Option::is_none) {
        let base = h.iter().flatten().copied().reduce(f64::max).unwrap_or(0.0);
        let mut next = base;
        for v in &mut h {
            if v.is_none() {
                next += 1.0;
                *v = Some(next);
            }
        }
    }
    let h: Vec<f64> = h.into_iter().map(|v| v.expect("filled")).collect();
    let group: Vec<u32> = table.rows.iter().map(|r| r.term_i).collect();
    let ids = global_id(&group, &h);
    assign(table, ids);
}

/// `get_NOT_hit` (`R/search.r:204-214`): the rows of the first member, in
/// a document where the
/// second has no row. A row keeps its number, or gets its row number in the
/// sorted table.
fn get_not_hit(table: &mut Table, n_unique: u32) {
    sort_rows(&mut table.rows);
    let and_ids = and_hit_ids(&table.rows, n_unique, true);
    if !table.has_hit_id {
        // d[, hit_id := integer()] makes a column of NA
        for r in &mut table.rows {
            r.hit_id = None;
        }
        table.has_hit_id = true;
    }
    for (k, r) in table.rows.iter_mut().enumerate() {
        if r.hit_id.is_none() {
            r.hit_id = Some((k + 1) as f64);
        }
    }
    for (r, a) in table.rows.iter_mut().zip(and_ids) {
        if !(r.term_i == 1 && a == 0.0) {
            r.hit_id = Some(0.0);
        }
    }
}

/// `remove_duplicate_hit_id` (`R/search.r:232-257`) with `keep_longest =
/// TRUE`, the default text2sdg never changes, at the top level in
/// the `unique_hits` mode: a token may start a term of one match only. The
/// matches are ranked by the total length of their terms, ties in table
/// order, and a match that starts a term on a token an earlier-ranked match
/// already used is removed whole, even if that earlier match is itself
/// removed. Only first tokens are compared.
fn remove_duplicate_hit_id(table: Table) -> Table {
    let mut seen = HashSet::new();
    let mut rows: Vec<Row> = table
        .rows
        .into_iter()
        .filter(|r| seen.insert((r.token_id, r.hit_id.map(f64::to_bits))))
        .collect();
    let mut tokens = HashSet::new();
    let any_dup = rows.iter().any(|r| !tokens.insert(r.token_id));
    if any_dup {
        let mut length: HashMap<u64, u64> = HashMap::new();
        for r in &rows {
            *length.entry(hit_key(r)).or_insert(0) += u64::from(r.ngram);
        }
        rows.sort_by_key(|r| std::cmp::Reverse(length[&hit_key(r)]));
        let mut tokens = HashSet::new();
        let mut dup_ids = HashSet::new();
        for r in &rows {
            if !tokens.insert(r.token_id) {
                dup_ids.insert(hit_key(r));
            }
        }
        rows.retain(|r| !dup_ids.contains(&hit_key(r)));
    }
    Table {
        rows,
        has_hit_id: table.has_hit_id,
        has_seq_i: table.has_seq_i,
    }
}

fn hit_key(r: &Row) -> u64 {
    r.hit_id.map(f64::to_bits).unwrap_or(u64::MAX)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(strings: &[&str], texts: &[&str], mode: Mode) -> Vec<Vec<(u32, DocHits)>> {
        let strings: Vec<String> = strings.iter().map(|s| s.to_string()).collect();
        let engine = Engine::new(&strings).unwrap();
        let batch = Batch::build(texts, 2).unwrap();
        let prepared = engine.prepare(&batch).unwrap();
        let call: Vec<usize> = (0..strings.len()).collect();
        let multiplicity = engine.multiplicity(&call);
        (0..strings.len())
            .map(|i| prepared.evaluate(i, mode, &multiplicity))
            .collect()
    }

    #[test]
    fn follows_the_rules_of_the_corpustools_probe() {
        // docs/corpustools-matching.md, rules 2 to 7
        let texts = [
            "tobacco , ( a ) ; : control",
            "tobacco a b c d e control",
            "control of tobacco",
            "Under-five mortality and under five",
            "reductions in tobacco",
        ];
        let r = run(
            &[
                "<(<tobacco>) (<control*>)>~6",
                "<under-five>",
                "<under five>",
                "*bacco",
                "reduction?",
            ],
            &texts,
            Mode::UniqueHits,
        );
        assert_eq!(r[0], vec![(1, vec![1, 7]), (2, vec![1, 3])]);
        assert_eq!(r[1], vec![(3, vec![1, 2, 3])]);
        assert_eq!(r[2], vec![(3, vec![6, 7])]);
        assert_eq!(
            r[3],
            vec![(0, vec![1]), (1, vec![1]), (2, vec![3]), (4, vec![3])]
        );
        assert_eq!(r[4], vec![(4, vec![1])]);
    }

    #[test]
    fn unique_hits_assigns_a_token_once_and_features_mode_does_not() {
        // the example of search_features' documentation: 'A A B'
        let texts = ["A A B"];
        let unique = run(&["A AND B"], &texts, Mode::UniqueHits);
        assert_eq!(unique[0], vec![(0, vec![1, 3])]);
        let features = run(&["A AND B"], &texts, Mode::Features);
        assert_eq!(features[0], vec![(0, vec![1, 2, 3])]);
    }

    #[test]
    fn not_keeps_the_first_member_where_the_second_is_absent() {
        let texts = ["poverty here", "poverty and wealth"];
        let r = run(&["poverty NOT wealth"], &texts, Mode::UniqueHits);
        assert_eq!(r[0], vec![(0, vec![1])]);
    }

    #[test]
    fn a_match_can_be_lost_in_the_unique_hits_mode() {
        // the study's case cascade_whole_match_lost: with the copies a shared
        // term gets in one call, remove_duplicate_hit_id removes every match
        let texts = ["Poverty and hunger near marine life and marine life."];
        let strings = [
            "(poverty OR hunger OR marine) AND (<marine life>)",
            "hunger OR <marine life>",
        ];
        assert!(run(&strings, &texts, Mode::UniqueHits)[0].is_empty());
        assert!(!run(&strings, &texts, Mode::Features)[0].is_empty());
        assert!(!run(&strings[..1], &texts, Mode::UniqueHits)[0].is_empty());
    }

    #[test]
    fn a_sequence_of_two_patterns_matches_only_a_repeated_token() {
        let texts = ["sustainable development", "develop develop"];
        let r = run(&["<sustainab* develop*>"], &texts, Mode::UniqueHits);
        assert_eq!(r[0], vec![(1, vec![1, 2])]);
    }

    #[test]
    fn global_id_offsets_by_the_last_value() {
        assert_eq!(
            global_id(&[1, 1, 2, 2], &[3.0, 1.0, 1.0, 2.0]),
            vec![3.0, 1.0, 2.0, 3.0]
        );
    }
}
