//! What a term of a search string is looked up as: a sequence of words, some
//! of which may be wildcard patterns.
//!
//! corpustools 0.5.2 `R/search_dictionary.r`: `dictionary_lookup`
//! trims the term, `standardize_dict_term_spacing` (`R/multitokens.r`) cuts
//! it as a text is cut and joins the pieces with spaces, gluing `*` and `?`
//! back to their word, and `collapse_dict` lowercases it and splits it on
//! the spaces. A word with `*` or `?` is a pattern, turned into a regular
//! expression over whole tokens by `expand_wildcards`.

use std::sync::LazyLock;

use regex::Regex;

use crate::tokens::{is_space_piece, normalize, pieces, r_trim};

static AROUND_WILDCARD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r" ?([?*]) ?").expect("valid regex"));
static SPACES: LazyLock<Regex> = LazyLock::new(|| Regex::new(r" +").expect("valid regex"));

/// `split_tokens(remember_spaces = TRUE)` pasted with spaces: the pieces of
/// the string, each whitespace piece glued to the piece before it
/// (`src/collapse_terms.cpp`, `collapse_terms_cpp` with `sep = " "` and
/// `sep2 = ""`).
fn spaced_pieces(s: &str) -> String {
    let mut out: Vec<String> = Vec::new();
    let mut use_sep2 = false;
    for (i, (a, b)) in pieces(s).into_iter().enumerate() {
        let piece = &s[a..b];
        if !is_space_piece(piece) || i == 0 {
            out.push(piece.to_string());
            use_sep2 = false;
        } else {
            let last = out.last_mut().expect("a piece before");
            if !use_sep2 {
                last.push(' ');
            }
            last.push_str(piece);
            use_sep2 = true;
        }
    }
    out.join(" ")
}

/// Consumes a term and produces the string corpustools looks up for it:
/// `stri_trim`, then `standardize_dict_term_spacing(wildcards = TRUE)`.
pub fn standardize(term: &str) -> String {
    let s = r_trim(term).replace('_', " ");
    let s = spaced_pieces(r_trim(&s));
    let s = AROUND_WILDCARD.replace_all(&s, "$1");
    SPACES.replace_all(&s, " ").into_owned()
}

/// Consumes a term and produces its words, as `collapse_dict` splits the
/// standardised string: lowercased, trimmed, cut on single spaces.
pub fn words(term: &str) -> Vec<String> {
    let s = normalize(&standardize(term));
    let s = s.strip_prefix(' ').unwrap_or(&s);
    let s = s.strip_suffix(' ').unwrap_or(s);
    s.split(' ').map(str::to_string).collect()
}

/// Whether a word is a pattern (`grepl('[?*]', ...)`).
pub fn is_pattern(word: &str) -> bool {
    word.contains(['*', '?'])
}

/// A pattern word, ready to be matched against the vocabulary.
#[derive(Debug, Clone)]
pub struct Pattern {
    /// The characters every match starts with: the part before the first
    /// wildcard, with escapes resolved.
    pub prefix: String,
    regex: Regex,
}

impl Pattern {
    /// Whether a vocabulary word matches the whole pattern.
    pub fn matches(&self, word: &str) -> bool {
        self.regex.is_match(word)
    }
}

/// One element of a pattern after `expand_wildcards` has rewritten it.
#[derive(Debug, Clone, Copy, PartialEq)]
enum Piece {
    Char(char),
    Star,
    Question,
}

/// ICU's `.` without flags: any character but a line terminator.
const ICU_DOT: &str = r"[^\n\x0B\x0C\r\x{85}\x{2028}\x{2029}]";

/// Consumes a pattern word and produces its matcher, as `expand_wildcards`
/// (`R/search_dictionary.r`) builds the regular expression: an escaped `\*`
/// or `\?` (from braces, `src/parse_query.cpp`) is the character itself, a
/// run of `*` is one `*` and means any characters, a run of `?` is one `?`
/// and means one character or none, every other character is itself, and
/// the expression must match the whole token. A pattern that is only `*` is
/// ignored by corpustools and gives `None`: it matches nothing.
pub fn pattern(word: &str) -> Option<Pattern> {
    let chars: Vec<char> = word.chars().collect();
    let mut seq: Vec<Piece> = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '\\' && i + 1 < chars.len() && matches!(chars[i + 1], '*' | '?') {
            seq.push(Piece::Char(chars[i + 1]));
            i += 2;
            continue;
        }
        let piece = match c {
            '*' => Piece::Star,
            '?' => Piece::Question,
            _ => Piece::Char(c),
        };
        // gsub('\\?+', '?') and gsub('\\*+', '*')
        if matches!(piece, Piece::Star | Piece::Question) && seq.last() == Some(&piece) {
            i += 1;
            continue;
        }
        seq.push(piece);
        i += 1;
    }
    if seq == [Piece::Star] {
        return None;
    }
    let mut regex = String::from("^");
    let mut prefix = String::new();
    let mut in_prefix = true;
    for piece in &seq {
        match piece {
            Piece::Char(c) => {
                regex.push_str(&regex::escape(&c.to_string()));
                if in_prefix {
                    prefix.push(*c);
                }
            }
            Piece::Star => {
                regex.push_str(ICU_DOT);
                regex.push('*');
                in_prefix = false;
            }
            Piece::Question => {
                regex.push_str(ICU_DOT);
                regex.push_str("{0,1}");
                in_prefix = false;
            }
        }
    }
    regex.push('$');
    Some(Pattern {
        prefix,
        regex: Regex::new(&regex).expect("a pattern always gives a valid regex"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn standardizes_as_corpustools() {
        assert_eq!(standardize("micro-financ*"), "micro - financ*");
        assert_eq!(standardize("micro-financ\\*"), "micro - financ \\*");
        assert_eq!(standardize(" fertili?er "), "fertili?er");
        assert_eq!(standardize("*bacco"), "*bacco");
        assert_eq!(standardize("water, sanitation"), "water , sanitation");
        assert_eq!(standardize("el niño/southern"), "el niño / southern");
        assert_eq!(words("Under-Five"), vec!["under", "-", "five"]);
    }

    #[test]
    fn matches_whole_tokens() {
        let p = pattern("*bacco").unwrap();
        assert!(p.matches("tobacco") && !p.matches("tobaccos"));
        assert_eq!(p.prefix, "");
        let p = pattern("reduction?").unwrap();
        assert!(p.matches("reduction") && p.matches("reductions") && !p.matches("reductionss"));
        assert_eq!(p.prefix, "reduction");
        let p = pattern("fertili??er").unwrap();
        assert!(p.matches("fertilizer") && !p.matches("fertiliser2"));
        // a star escaped by braces is the character itself
        let p = pattern("\\*").unwrap();
        assert!(p.matches("*") && !p.matches("x"));
        assert_eq!(p.prefix, "*");
        assert!(pattern("**").is_none());
        let p = pattern("e.g*").unwrap();
        assert!(p.matches("e.g") && !p.matches("exg"));
    }
}
