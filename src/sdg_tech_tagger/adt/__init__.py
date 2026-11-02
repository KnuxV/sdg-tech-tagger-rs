"""The technology queries: advanced digital technologies (ADT).

``wos_query`` reads a query file written for the Web of Science into its
terms, ``translate`` turns terms into patterns and applies them to text on
Polars, and ``wos_form`` writes a compiled gate back as Web of Science
queries.

Two versions of the queries ship as data:

- ``wos/``: the simplified query of the Nature Communications paper, six
  groups, as Web of Science files, with ``adt_patterns_v1.json`` compiled
  from them.
- ``gate_v2/``: gate v2, seven groups, the terms with their sources
  (``provenance.tsv``), the query files and ``gate_patterns_v2.json``;
  ``gate_v2_wos/`` writes it out as Web of Science queries.

Both are read-only; ``SHA256SUMS`` in each says what the files must be.
"""
