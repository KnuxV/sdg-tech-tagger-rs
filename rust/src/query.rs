//! corpustools' query language, parsed into the tree its evaluator walks.
//!
//! A port of corpustools 0.5.2 `src/parse_query.cpp` (with
//! `src/QueryIter.cpp`), followed by `R/query.r`, `parse_query`:
//! `simplify_query`, then `collapse_or_queries` and
//! `collapse_sequence_queries` applied by `optimize_query`. The parser reads
//! the string byte by byte, as the C++ does; a character outside ASCII is
//! never one of its special characters, so its bytes go into a term whole.
//!
//! The flags `~s` (case sensitive), `~g` (ghost), `~d` (directed), token and
//! meta expressions, and a feature column (`name:`) are refused: no search
//! string of the four systems uses them, and
//! the evaluator does not implement them.

use std::fmt;

/// How the members of a group combine (`relation` in corpustools).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Relation {
    /// No operator: a group with a single member, or terms side by side
    /// that `get_bool_operator` reads as one.
    Empty,
    Or,
    And,
    Not,
    /// Members adjacent and in order: `<a b>` or `"a b"` without a window.
    Sequence,
    /// Members within a window: `<a b>~n`.
    Proximity,
}

impl Relation {
    fn name(self) -> &'static str {
        match self {
            Relation::Empty => "",
            Relation::Or => "OR",
            Relation::And => "AND",
            Relation::Not => "NOT",
            Relation::Sequence => "sequence",
            Relation::Proximity => "proximity",
        }
    }
}

/// A node of a parsed search string.
#[derive(Debug, Clone, PartialEq)]
pub enum Node {
    /// A term: one string, or after `collapse_or_queries` several strings
    /// looked up together as one member. A string may hold several words
    /// (a collapsed sequence, a braced phrase).
    Term(Vec<String>),
    /// A group of members.
    Group {
        relation: Relation,
        /// The window of a proximity; 0 otherwise.
        window: u32,
        members: Vec<Node>,
    },
}

impl fmt::Display for Node {
    /// A compact form of the tree, used to compare it with the tree
    /// corpustools builds: `T[a|b]` for a term, `REL~w(member,member)` for a
    /// group.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Node::Term(terms) => write!(f, "T[{}]", terms.join("|")),
            Node::Group {
                relation,
                window,
                members,
            } => {
                write!(f, "{}", relation.name())?;
                if *relation == Relation::Proximity {
                    write!(f, "~{window}")?;
                }
                write!(f, "(")?;
                for (i, m) in members.iter().enumerate() {
                    if i > 0 {
                        write!(f, ",")?;
                    }
                    write!(f, "{m}")?;
                }
                write!(f, ")")
            }
        }
    }
}

/// `src/QueryIter.cpp`: the query padded with a space at each end and a
/// cursor. Reading past the end gives the byte 0, as `std::string` does.
struct QueryIter {
    query: Vec<u8>,
    position: usize,
}

impl QueryIter {
    fn new(x: &str) -> Self {
        let mut query = Vec::with_capacity(x.len() + 2);
        query.push(b' ');
        query.extend_from_slice(x.as_bytes());
        query.push(b' ');
        QueryIter { query, position: 0 }
    }

    fn at(&self, i: usize) -> u8 {
        self.query.get(i).copied().unwrap_or(0)
    }

    fn next(&mut self) {
        if self.position < self.query.len() {
            self.position += 1;
        }
    }

    fn pop(&mut self) -> u8 {
        let c = self.at(self.position);
        self.next();
        c
    }

    fn done(&self) -> bool {
        self.position >= self.query.len()
    }

    fn is(&self, c: u8) -> bool {
        if self.position + 1 == self.query.len() {
            return false;
        }
        self.at(self.position) == c
    }

    fn is_break(&self) -> bool {
        b"() \"<>".contains(&self.at(self.position))
    }

    fn pop_till_break(&mut self) -> Vec<u8> {
        let mut out = Vec::new();
        let mut escaped1 = false;
        let mut escaped2 = false;
        while !self.done() {
            if self.is(b'{') {
                escaped1 = true;
            }
            if self.is(b'[') {
                escaped2 = true;
            }
            if self.is_break() && !escaped1 && !escaped2 {
                break;
            }
            if self.is(b'}') {
                escaped1 = false;
            }
            if self.is(b']') {
                escaped2 = false;
            }
            out.push(self.pop());
        }
        out
    }

    fn pop_flag(&mut self) -> Vec<u8> {
        if self.is(b'~') {
            self.next();
            return self.pop_till_break();
        }
        Vec::new()
    }
}

/// An error of parsing, or a construction the port does not implement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueryError(pub String);

impl fmt::Display for QueryError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

fn err<T>(message: &str) -> Result<T, QueryError> {
    Err(QueryError(message.to_string()))
}

/// `char_in_flag`: whether `c` occurs in the flag outside `{...}`.
fn char_in_flag(flag: &[u8], c: u8) -> bool {
    let mut opened = false;
    for &f in flag {
        if f == b'{' {
            opened = true;
        }
        if f == b'}' {
            opened = false;
        }
        if !opened && f == c {
            return true;
        }
    }
    false
}

/// `get_number`: the digits of the flag read as one number; -1 without any.
fn get_number(flag: &[u8]) -> i64 {
    let digits: String = flag
        .iter()
        .filter(|b| b.is_ascii_digit())
        .map(|&b| b as char)
        .collect();
    if digits.is_empty() {
        -1
    } else {
        digits.parse().unwrap_or(i64::MAX)
    }
}

/// Refuses a flag that holds anything but a window.
fn plain_flag(flag: &[u8]) -> Result<(), QueryError> {
    for c in *b"sgd" {
        if char_in_flag(flag, c) {
            return err("the flags ~s, ~g and ~d are not supported");
        }
    }
    if flag.contains(&b'{') || flag.contains(&b'[') {
        return err("token and meta expressions are not supported");
    }
    Ok(())
}

/// An item of a level before `parse_terms`: a string (a term or an
/// operator) or a nested level.
enum Raw {
    Str(Vec<u8>),
    Nested(Node),
}

/// `get_bool_operator`: the one boolean operator of a level, a space read as
/// `OR`.
fn get_bool_operator(terms: &[Raw]) -> Result<Relation, QueryError> {
    let mut out: Option<Relation> = None;
    let mut lag_bool = true;
    let n = terms.len();
    for (i, t) in terms.iter().enumerate() {
        let b: &[u8] = match t {
            Raw::Str(s) => s,
            Raw::Nested(_) => b" ",
        };
        let op = match b {
            b"AND" => Some(Relation::And),
            b"OR" => Some(Relation::Or),
            b"NOT" => Some(Relation::Not),
            _ => None,
        };
        let b = if let Some(op) = op {
            if i == 0 {
                return err("cannot start with boolean operators (AND, OR, NOT)");
            }
            if i == n - 1 {
                return err("cannot end with boolean operators (AND, OR, NOT)");
            }
            if lag_bool {
                return err("cannot have adjacent boolean operators (AND, OR, NOT)");
            }
            lag_bool = true;
            op
        } else if !lag_bool {
            Relation::Or
        } else {
            lag_bool = false;
            continue;
        };
        match out {
            Some(o) if o != b => {
                return err("Cannot have more than one type of boolean operator at the same level");
            }
            _ => out = Some(b),
        }
    }
    Ok(out.unwrap_or(Relation::Empty))
}

/// The state of one level while it is read (`get_nested_terms`).
struct Level {
    terms: Vec<Raw>,
    flags: Vec<Vec<u8>>,
    term: Vec<u8>,
}

impl Level {
    /// `add_term`: a term that is complete goes in, with the flag after it.
    fn add_term(&mut self, q: &mut QueryIter) -> Result<(), QueryError> {
        if !self.term.is_empty() {
            let term = std::mem::take(&mut self.term);
            self.terms.push(Raw::Str(term));
            self.flags.push(q.pop_flag());
        }
        Ok(())
    }
}

/// `get_nested_terms`, line by line: reads one level of the query from the
/// cursor and produces its node.
fn get_nested_terms(
    q: &mut QueryIter,
    nested_i: usize,
    in_quote: u32,
    in_quotemark: bool,
) -> Result<Node, QueryError> {
    let mut level = Level {
        terms: Vec::new(),
        flags: Vec::new(),
        term: Vec::new(),
    };
    let mut relation: Option<Relation> = None;
    let mut window: u32 = 0;
    let mut lag_space = true;
    loop {
        if q.done() {
            if matches!(q.at(nested_i), b'"' | b'(' | b'<') {
                return err("incorrect nesting");
            }
            break;
        }
        let mut x = q.pop();

        // skip double spaces
        if x == b' ' {
            if lag_space {
                continue;
            }
            lag_space = true;
        } else {
            lag_space = false;
        }

        // escape next char
        if x == b'\\' {
            x = q.pop();
            match x {
                b'*' => level.term.extend_from_slice(b"\\*"),
                b'?' => level.term.extend_from_slice(b"\\?"),
                _ => level.term.push(x),
            }
            continue;
        }

        // add verbatim term: everything up to the closing brace, the
        // wildcards escaped
        if x == b'{' {
            x = q.pop();
            let mut escape_close = false;
            while x != b'}' && !escape_close {
                if x == b'{' {
                    return err("Trying to open a verbatim term within a verbatim term");
                }
                match x {
                    b'*' => level.term.extend_from_slice(b"\\*"),
                    b'?' => level.term.extend_from_slice(b"\\?"),
                    _ => level.term.push(x),
                }
                x = q.pop();
                if x == b'\\' {
                    escape_close = true;
                    x = q.pop();
                } else {
                    escape_close = false;
                }
                if q.done() {
                    return err("Did not close a verbatim term");
                }
            }
            continue;
        }

        // nesting within parentheses
        if x == b'(' {
            level.add_term(q)?;
            let nested = get_nested_terms(q, q.position - 1, in_quote, in_quotemark)?;
            level.terms.push(Raw::Nested(nested));
            level.flags.push(Vec::new());
            continue;
        }
        // ending part between parentheses
        if x == b')' {
            if q.at(nested_i) != b'(' {
                return err("incorrect nesting: trying to close with ')'");
            }
            let flag = q.pop_flag();
            plain_flag(&flag)?;
            break;
        }

        // nesting within quotes
        if (x == b'"' && q.at(nested_i) != b'"') || x == b'<' {
            level.add_term(q)?;
            let quotemark = x == b'"';
            let nested = get_nested_terms(q, q.position - 1, in_quote + 1, quotemark)?;
            level.terms.push(Raw::Nested(nested));
            level.flags.push(Vec::new());
            continue;
        }
        // ending part between quotes
        if (x == b'"' && in_quotemark) || x == b'>' {
            if x == b'"' && q.at(nested_i) != b'"' {
                return err("incorrect nesting: trying to close with '\"'");
            }
            if x == b'>' && q.at(nested_i) != b'<' {
                return err("incorrect nesting: trying to close with '>'");
            }
            let flag = q.pop_flag();
            plain_flag(&flag)?;
            let w = get_number(&flag);
            if w < 0 {
                relation = Some(Relation::Sequence);
            } else {
                relation = Some(Relation::Proximity);
                window = u32::try_from(w).map_err(|_| QueryError("window too large".into()))?;
            }
            break;
        }

        if x == b':' {
            return err("a feature column (name:) is not supported");
        }

        // a space at this point ends a term
        if x == b' ' {
            level.add_term(q)?;
        } else {
            level.term.push(x);
        }

        // a flag next in line ends the term it belongs to
        if q.is(b'~') {
            level.add_term(q)?;
        }
    }
    level.add_term(q)?;

    // parse_terms: operators and empty strings are not members
    let mut members = Vec::new();
    for (raw, flag) in level.terms.iter().zip(&level.flags) {
        match raw {
            Raw::Str(s) => {
                if s.as_slice() == b"AND" || s.as_slice() == b"OR" || s.as_slice() == b"NOT" {
                    continue;
                }
                if s.is_empty() {
                    continue;
                }
                plain_flag(flag)?;
                let term = String::from_utf8(s.clone())
                    .map_err(|_| QueryError("a term is not valid UTF-8".into()))?;
                members.push(Node::Term(vec![term]));
            }
            Raw::Nested(node) => members.push(node.clone()),
        }
    }
    let relation = match relation {
        Some(r) => r,
        None => get_bool_operator(&level.terms)?,
    };
    if in_quote > 0 && matches!(relation, Relation::And | Relation::Not) {
        return err("Cannot use AND or NOT inside of quotes");
    }
    if in_quote > 1 && relation == Relation::Proximity {
        return err("Cannot nest a proximity search inside of quotes");
    }
    if relation == Relation::Not && members.len() != 2 {
        return err("NOT operator can only be used with one term before and one term after");
    }
    Ok(Node::Group {
        relation,
        window,
        members,
    })
}

/// `simplify_query`: every term lowercased, as `stringi::stri_trans_tolower`
/// does (full Unicode lowercasing).
fn simplify(node: &mut Node) {
    match node {
        Node::Term(terms) => {
            for t in terms.iter_mut() {
                *t = t.to_lowercase();
            }
        }
        Node::Group { members, .. } => members.iter_mut().for_each(simplify),
    }
}

/// `collapse_or_queries`: at an `OR`, two or more plain terms become one
/// member holding all their strings, in their order, placed first; the
/// nested members follow in their order.
fn collapse_or(node: Node) -> Node {
    match node {
        Node::Group {
            relation: Relation::Or,
            window,
            members,
        } => {
            let plain = members
                .iter()
                .filter(|m| matches!(m, Node::Term(_)))
                .count();
            if plain > 1 {
                let mut strings = Vec::new();
                let mut nested = Vec::new();
                for m in members {
                    match m {
                        Node::Term(t) => strings.extend(t),
                        group => nested.push(group),
                    }
                }
                let mut out = vec![Node::Term(strings)];
                out.extend(nested);
                Node::Group {
                    relation: Relation::Or,
                    window,
                    members: out,
                }
            } else {
                Node::Group {
                    relation: Relation::Or,
                    window,
                    members,
                }
            }
        }
        other => other,
    }
}

/// `collapse_sequence_queries`: a sequence of plain terms becomes one term,
/// the words joined by a space, looked up as a phrase.
fn collapse_sequence(node: Node) -> Node {
    match node {
        Node::Group {
            relation: Relation::Sequence,
            window,
            members,
        } => {
            if members.iter().any(|m| matches!(m, Node::Group { .. })) {
                return Node::Group {
                    relation: Relation::Sequence,
                    window,
                    members,
                };
            }
            let words: Vec<String> = members
                .into_iter()
                .flat_map(|m| match m {
                    Node::Term(t) => t,
                    Node::Group { .. } => unreachable!("checked above"),
                })
                .collect();
            Node::Term(vec![words.join(" ")])
        }
        other => other,
    }
}

/// `optimize_query`: `fun` at this node, then at each nested member.
fn optimize(node: Node, fun: fn(Node) -> Node) -> Node {
    match fun(node) {
        Node::Group {
            relation,
            window,
            members,
        } => Node::Group {
            relation,
            window,
            members: members
                .into_iter()
                .map(|m| match m {
                    group @ Node::Group { .. } => optimize(group, fun),
                    term => term,
                })
                .collect(),
        },
        term => term,
    }
}

/// Consumes a search string and produces the tree corpustools evaluates for
/// it (`R/query.r`, `parse_query`), or the error corpustools would stop
/// with, or a refusal of a construction the port does not implement.
pub fn parse(query: &str) -> Result<Node, QueryError> {
    let mut q = QueryIter::new(query);
    let mut node = get_nested_terms(&mut q, 0, 0, false)?;
    simplify(&mut node);
    let node = optimize(node, collapse_or);
    Ok(optimize(node, collapse_sequence))
}

/// Every term string of a tree, in order, repeated as often as it occurs.
pub fn terms(node: &Node) -> Vec<&str> {
    let mut out = Vec::new();
    fn walk<'a>(node: &'a Node, out: &mut Vec<&'a str>) {
        match node {
            Node::Term(t) => out.extend(t.iter().map(String::as_str)),
            Node::Group { members, .. } => members.iter().for_each(|m| walk(m, out)),
        }
    }
    walk(node, &mut out);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tree(q: &str) -> String {
        parse(q).unwrap().to_string()
    }

    #[test]
    fn reads_the_handwritten_aurora_strings() {
        // text2sdg 1.1.2 R/aurora.R, special 2
        assert_eq!(
            tree("(<neonatal> OR <under-five> OR ( <(<under>) (<5> OR <five>)>~2 ) OR <before fifth>)"),
            "(OR(T[neonatal],T[under-five],(proximity~2((T[under]),OR(T[5],T[five]))),T[before fifth]))"
        );
        assert_eq!(
            tree("<(<physical> OR <sexual>) (<harass*>)>~3"),
            "(proximity~3(OR(T[physical],T[sexual]),(T[harass*])))"
        );
    }

    #[test]
    fn collapses_plain_terms_of_an_or_first() {
        assert_eq!(tree("a OR (b AND c) OR d"), "OR(T[a|d],AND(T[b],T[c]))");
        assert_eq!(tree("Poverty poor"), "OR(T[poverty|poor])");
    }

    #[test]
    fn reads_a_braced_phrase_verbatim() {
        assert_eq!(
            tree("{urban poverty} OR {micro-financ*}"),
            "OR(T[urban poverty|micro-financ\\*])"
        );
        assert_eq!(
            tree("{water, sanitation and hygiene}"),
            "(T[water, sanitation and hygiene])"
        );
    }

    #[test]
    fn reads_quotes_as_a_sequence() {
        assert_eq!(
            tree("(\"anti-poverty\") AND (\"poverty\" OR \"vulnerability\")"),
            "AND((T[anti-poverty]),OR(T[poverty],T[vulnerability]))"
        );
    }

    #[test]
    fn refuses_what_corpustools_refuses() {
        assert!(parse("a AND b OR c").is_err());
        assert!(parse("a NOT b NOT c").is_err());
        // inside quotes the operator is dropped and the level is a sequence
        assert_eq!(tree("<a AND b>"), "(T[a b])");
        assert!(parse("(a b").is_err());
        assert!(parse("a~s").is_err());
    }
}
