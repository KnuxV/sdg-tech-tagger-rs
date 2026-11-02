//! Tokens as corpustools 0.5.2 cuts a text, and the form in which it looks
//! them up.
//!
//! `vendor/corpustools_0.5.2/R/tokenize.r`, `split_tokens`: the text is cut at
//! ICU word boundaries (`stringi::stri_split_boundaries(type = "word")`) and
//! the pieces that match the ICU regex `^\s+$` are dropped. Every other piece
//! is a token, and its index plus one is corpustools' `token_id`. The port
//! cuts with ICU4X (D013; `probes/segmenter_probe/`).
//!
//! For the lookup of query terms, corpustools prepares the tokens once more
//! (`R/search_dictionary.r`, `dictionary_lookup_tokens`): a token that holds
//! an underscore or a space is cut again into parts (`R/multitokens.r`,
//! `is_splittable`, `flatten_terms`), and every token is lowercased with base
//! R's `tolower` and trimmed (`normalize_string`). The parts of a token keep
//! its `token_id`.

use icu_segmenter::options::WordBreakInvariantOptions;
use icu_segmenter::{WordSegmenter, WordSegmenterBorrowed};

/// The segmenter of the port: ICU4X in auto mode, its data compiled into the
/// crate (D013).
pub fn segmenter() -> WordSegmenterBorrowed<'static> {
    WordSegmenter::new_auto(WordBreakInvariantOptions::default())
}

/// Whether a character is matched by ICU's `\s`, which is
/// `[\t\n\f\r\p{Z}]`. It is not Rust's White_Space: U+000B and U+0085 are not
/// in it.
pub fn is_icu_space(c: char) -> bool {
    matches!(
        c,
        '\t' | '\n' | '\u{000C}' | '\r'
            // Zs
            | '\u{0020}' | '\u{00A0}' | '\u{1680}' | '\u{2000}'
            ..='\u{200A}'
            | '\u{202F}' | '\u{205F}' | '\u{3000}'
            // Zl, Zp
            | '\u{2028}' | '\u{2029}'
    )
}

/// Whether a piece matches `^\s+$`, the test by which `split_tokens` drops it.
pub fn is_space_piece(piece: &str) -> bool {
    !piece.is_empty() && piece.chars().all(is_icu_space)
}

/// Consumes a string and produces the byte range of every piece between two
/// ICU word boundaries, whitespace pieces included, in order.
pub fn pieces(text: &str) -> Vec<(usize, usize)> {
    let mut out = Vec::new();
    let mut start = 0usize;
    for end in segmenter().segment_str(text) {
        if end > start {
            out.push((start, end));
            start = end;
        }
    }
    out
}

/// Consumes a text and produces the byte range of each of its tokens, in
/// order: `split_tokens` with `remember_spaces = FALSE`.
pub fn token_spans(text: &str) -> Vec<(usize, usize)> {
    pieces(text)
        .into_iter()
        .filter(|&(s, e)| !is_space_piece(&text[s..e]))
        .collect()
}

/// Consumes a string and produces it lowercased character by character, as
/// base R's `tolower` does through the C library's `towlower`: a simple, one
/// to one mapping, so a final sigma stays `σ`. The one character whose
/// Unicode lowercase is two characters, U+0130, maps to `i`, as `towlower`
/// maps it.
pub fn r_tolower(s: &str) -> String {
    s.chars()
        .map(|c| {
            let mut lower = c.to_lowercase();
            match (lower.next(), lower.next()) {
                (Some(l), None) => l,
                _ if c == '\u{0130}' => 'i',
                _ => c,
            }
        })
        .collect()
}

/// Consumes a string and produces it without the White_Space characters at
/// either end, as `stringi::stri_trim` does.
pub fn r_trim(s: &str) -> &str {
    s.trim_matches(char::is_whitespace)
}

/// `normalize_string(lowercase = TRUE, ascii = FALSE, trim = TRUE)` of
/// `R/search_dictionary.r`: the form in which a token is looked up.
pub fn normalize(s: &str) -> String {
    r_trim(&r_tolower(s)).to_string()
}

/// The tokens of one document.
#[derive(Debug, Clone, Default)]
pub struct DocTokens {
    /// The byte range of each token in the text; the index is `token_id - 1`.
    pub spans: Vec<(u32, u32)>,
    /// The rows the lookup runs on, each token normalised and a splittable
    /// token replaced by its parts, written one after the other.
    rows_text: String,
    /// The end of each row in `rows_text`.
    row_ends: Vec<u32>,
    /// For each row, the index of the token it comes from. Empty when no
    /// token was split, in which case row and token coincide.
    row_token: Vec<u32>,
}

impl DocTokens {
    /// The number of lookup rows.
    pub fn row_count(&self) -> usize {
        self.row_ends.len()
    }

    /// The lookup row `i`.
    pub fn row(&self, i: usize) -> &str {
        let start = if i == 0 {
            0
        } else {
            self.row_ends[i - 1] as usize
        };
        &self.rows_text[start..self.row_ends[i] as usize]
    }

    /// The index of the token a lookup row comes from.
    pub fn token_of_row(&self, row: usize) -> u32 {
        if self.row_token.is_empty() {
            row as u32
        } else {
            self.row_token[row]
        }
    }

    fn push_row(&mut self, token: &str) {
        self.rows_text.push_str(&normalize(token));
        self.row_ends.push(self.rows_text.len() as u32);
    }
}

/// Consumes a token and produces its parts when `is_splittable` holds for it:
/// the token with `_` replaced by a space, cut by `split_tokens`, gives more
/// than one piece. `None` when it does not. Only a token that holds an
/// underscore or whitespace is cut again: any other token is one ICU piece,
/// and cut alone it stays one.
fn split_parts(token: &str) -> Option<Vec<String>> {
    if !token.contains('_') && !token.chars().any(char::is_whitespace) {
        return None;
    }
    let spaced = token.replace('_', " ");
    let parts: Vec<String> = token_spans(&spaced)
        .into_iter()
        .map(|(s, e)| spaced[s..e].to_string())
        .collect();
    (parts.len() > 1).then_some(parts)
}

/// Consumes a text and produces its tokens and lookup rows.
pub fn cut(text: &str) -> DocTokens {
    let spans = token_spans(text);
    let mut doc = DocTokens {
        spans: spans.iter().map(|&(s, e)| (s as u32, e as u32)).collect(),
        rows_text: String::with_capacity(text.len()),
        row_ends: Vec::with_capacity(spans.len()),
        row_token: Vec::new(),
    };
    for (index, &(s, e)) in spans.iter().enumerate() {
        let token = &text[s..e];
        match split_parts(token) {
            None => {
                doc.push_row(token);
                if !doc.row_token.is_empty() {
                    doc.row_token.push(index as u32);
                }
            }
            Some(parts) => {
                if doc.row_token.is_empty() {
                    doc.row_token = (0..doc.row_count() as u32).collect();
                }
                for part in parts {
                    doc.push_row(&part);
                    doc.row_token.push(index as u32);
                }
            }
        }
    }
    doc
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tokens(text: &str) -> Vec<&str> {
        token_spans(text)
            .into_iter()
            .map(|(s, e)| &text[s..e])
            .collect()
    }

    #[test]
    fn cuts_as_the_corpustools_probe_shows() {
        // docs/corpustools-matching.md, "Tokens"
        let text =
            "Under-five mortality: we reduce neonatal deaths. Women's rights, e.g. CO2 (US$1.90).";
        assert_eq!(
            tokens(text),
            vec![
                "Under",
                "-",
                "five",
                "mortality",
                ":",
                "we",
                "reduce",
                "neonatal",
                "deaths",
                ".",
                "Women's",
                "rights",
                ",",
                "e.g",
                ".",
                "CO2",
                "(",
                "US",
                "$",
                "1.90",
                ")",
                "."
            ]
        );
    }

    #[test]
    fn lowercases_one_character_at_a_time() {
        assert_eq!(r_tolower("ΣΟΦΟΣ"), "σοφοσ");
        assert_eq!(r_tolower("İstanbul"), "istanbul");
        assert_eq!(normalize(" Poverty\u{00A0}"), "poverty");
    }

    #[test]
    fn splits_a_token_with_an_underscore() {
        let doc = cut("the CO_2 level");
        assert_eq!(doc.spans.len(), 3);
        let rows: Vec<&str> = (0..doc.row_count()).map(|i| doc.row(i)).collect();
        assert_eq!(rows, vec!["the", "co", "2", "level"]);
        assert_eq!(
            (0..4).map(|r| doc.token_of_row(r)).collect::<Vec<_>>(),
            vec![0, 1, 1, 2]
        );
        let plain = cut("no split here");
        assert!(plain.row_token.is_empty());
        assert_eq!(plain.token_of_row(2), 2);
    }
}
