"""The technology queries: advanced digital technologies (ADT).

``wos_query`` reads a query file written for the Web of Science into its
terms, ``translate`` turns terms into patterns and applies them to text on
Polars, and ``wos_form`` writes a compiled query back as Web of Science
queries.

Two versions of the queries ship as data:

- ``simplified/``: the simplified query, six groups, as Web of Science
  files, with ``patterns.json`` compiled from them. Terms are matched as
  written.
- ``extended/``: the extended query, seven groups, more terms per group,
  the terms with their sources (``provenance.tsv``), the query files and
  ``patterns.json``, which also accepts plurals, the closed spelling of
  hyphenated terms and decimals as one word; ``extended_wos/`` writes it out
  as Web of Science queries.

Every term of both is listed in ``docs/technology-queries.md``. Both are
read-only; ``SHA256SUMS`` in each says what the files must be.
"""
