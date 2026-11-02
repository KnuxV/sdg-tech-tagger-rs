"""A Python port of the R package text2sdg, built on the tantivy search engine.

``detect`` takes a table of documents and returns, for each document, the
queries of the labelling systems Aurora, Elsevier, SIRIS and Auckland that
fire on it (``docs/contract.md``).
"""

from sdg_tech_tagger.port import detect

__all__ = ["detect"]
