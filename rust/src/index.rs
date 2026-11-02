//! tantivy as the word index of a batch of documents (D013).
//!
//! Each document's lookup rows (`tokens::DocTokens`) are indexed as a
//! pre-tokenised text whose positions are the row numbers, so the postings
//! of a word give, per document, the rows where it stands. A `u64` fast field
//! holds the document's index in the batch, which is the only identifier
//! that survives tantivy's segments (`docs/tantivy-notes.md`). The term
//! dictionary of each segment gives the words a wildcard pattern covers.
//! Nothing of tantivy's own querying is used.

use std::collections::BTreeSet;
use std::sync::Arc;

use rayon::prelude::*;
use tantivy::merge_policy::NoMergePolicy;
use tantivy::postings::Postings;
use tantivy::schema::{Field, IndexRecordOption, Schema, TextFieldIndexing, TextOptions, FAST};
use tantivy::tokenizer::{PreTokenizedString, Token};
use tantivy::{
    DocSet, Index, IndexWriter, InvertedIndexReader, ReloadPolicy, TantivyDocument, TERMINATED,
};

use crate::terms::Pattern;
use crate::tokens::{self, DocTokens};

/// The most indexing threads tantivy uses.
const MAX_INDEX_THREADS: usize = 8;
/// The memory tantivy may use per indexing thread before it writes a segment.
const MEMORY_PER_THREAD: usize = 64 * 1024 * 1024;

/// One segment of the index, with what it takes to read it.
struct Segment {
    inverted: Arc<InvertedIndexReader>,
    /// The batch index of each of the segment's documents.
    row_of_doc: Vec<u32>,
}

/// A batch of documents, cut and indexed.
pub struct Batch {
    /// The tokens of each document of the batch, in input order.
    pub docs: Vec<DocTokens>,
    segments: Vec<Segment>,
}

/// The postings of one word: the batch index of each document that holds it,
/// with the rows where it stands, both in increasing order.
pub type WordPostings = Vec<(u32, Vec<u32>)>;

impl Batch {
    /// Consumes the texts of a batch and produces them cut and indexed. The
    /// cutting runs on rayon's threads, the indexing on up to `threads` of
    /// tantivy's.
    pub fn build(texts: &[&str], threads: usize) -> tantivy::Result<Batch> {
        let docs: Vec<DocTokens> = texts.par_iter().map(|t| tokens::cut(t)).collect();

        let mut builder = Schema::builder();
        let row_field = builder.add_u64_field("row", FAST);
        let indexing = TextFieldIndexing::default()
            .set_index_option(IndexRecordOption::WithFreqsAndPositions)
            .set_fieldnorms(false);
        let body = builder.add_text_field(
            "body",
            TextOptions::default().set_indexing_options(indexing),
        );
        let index = Index::create_in_ram(builder.build());
        let writer_threads = threads.clamp(1, MAX_INDEX_THREADS);
        let mut writer: IndexWriter =
            index.writer_with_num_threads(writer_threads, writer_threads * MEMORY_PER_THREAD)?;
        writer.set_merge_policy(Box::new(NoMergePolicy));
        for (row, doc) in docs.iter().enumerate() {
            writer.add_document(tantivy_doc(row_field, body, row as u64, doc))?;
        }
        writer.commit()?;
        drop(writer);

        let reader = index
            .reader_builder()
            .reload_policy(ReloadPolicy::Manual)
            .try_into()?;
        let searcher = reader.searcher();
        let mut segments = Vec::new();
        for segment in searcher.segment_readers() {
            let column = segment.fast_fields().u64("row")?;
            let row_of_doc = (0..segment.max_doc())
                .map(|d| column.first(d).expect("every document has a row") as u32)
                .collect();
            segments.push(Segment {
                inverted: segment.inverted_index(body)?,
                row_of_doc,
            });
        }
        Ok(Batch { docs, segments })
    }

    /// Consumes a word and produces its postings in the batch.
    pub fn postings(&self, word: &str) -> std::io::Result<WordPostings> {
        let mut out = Vec::new();
        let mut positions = Vec::new();
        for segment in &self.segments {
            let Some(info) = segment.inverted.terms().get(word.as_bytes())? else {
                continue;
            };
            let mut postings = segment
                .inverted
                .read_postings_from_terminfo(&info, IndexRecordOption::WithFreqsAndPositions)?;
            while postings.doc() != TERMINATED {
                postings.positions(&mut positions);
                out.push((
                    segment.row_of_doc[postings.doc() as usize],
                    positions.clone(),
                ));
                postings.advance();
            }
        }
        out.sort_unstable_by_key(|&(row, _)| row);
        Ok(out)
    }

    /// Consumes a pattern and produces the words of the batch it covers,
    /// sorted and distinct, read from the term dictionaries: from the
    /// pattern's fixed prefix on, or the whole dictionary when the pattern
    /// starts with a wildcard.
    pub fn expand(&self, pattern: &Pattern) -> std::io::Result<Vec<String>> {
        let mut words = BTreeSet::new();
        let prefix = pattern.prefix.as_bytes();
        for segment in &self.segments {
            let dictionary = segment.inverted.terms();
            let mut stream = dictionary.range().ge(prefix).into_stream()?;
            while stream.advance() {
                let key = stream.key();
                if !key.starts_with(prefix) {
                    break;
                }
                if let Ok(word) = std::str::from_utf8(key) {
                    if pattern.matches(word) {
                        words.insert(word.to_string());
                    }
                }
            }
        }
        Ok(words.into_iter().collect())
    }
}

/// The tantivy document of one of ours: its batch index and its lookup rows,
/// each at its own position.
fn tantivy_doc(row_field: Field, body: Field, row: u64, doc: &DocTokens) -> TantivyDocument {
    let tokens = (0..doc.row_count())
        .map(|i| Token {
            offset_from: 0,
            offset_to: 0,
            position: i,
            text: doc.row(i).to_string(),
            position_length: 1,
        })
        .collect();
    let mut out = TantivyDocument::default();
    out.add_u64(row_field, row);
    out.add_pre_tokenized_text(
        body,
        PreTokenizedString {
            text: String::new(),
            tokens,
        },
    );
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::terms::pattern;

    #[test]
    fn gives_rows_of_documents_and_words_of_patterns() {
        let texts = ["Tobacco control, tobacco.", "No smoking here", "TOBACCOS"];
        let batch = Batch::build(&texts, 2).unwrap();
        assert_eq!(batch.postings("tobacco").unwrap(), vec![(0, vec![0, 3])]);
        assert_eq!(batch.postings("smoking").unwrap(), vec![(1, vec![1])]);
        assert!(batch.postings("absent").unwrap().is_empty());
        let words = batch.expand(&pattern("tobacco*").unwrap()).unwrap();
        assert_eq!(words, vec!["tobacco", "tobaccos"]);
        let words = batch.expand(&pattern("*ing").unwrap()).unwrap();
        assert_eq!(words, vec!["smoking"]);
    }
}
