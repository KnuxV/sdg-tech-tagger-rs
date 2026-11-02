# Licences of the data files

The code of this package (Python under `src/`, Rust under `rust/`, the
tests) is under the GNU General Public License, version 3 (`LICENSE`). It is
a port of the R packages text2sdg and corpustools, which are GPL-3.

The data files shipped in the package keep the licence their sources impose.
Every source, with its version and DOI, is in `CREDITS.md`.

| files | derived from | licence |
|---|---|---|
| `src/sdg_tech_tagger/query_tables/` (the seven query tables and `SHA256SUMS`) | the query tables of text2sdg 1.1.2, exported unchanged; they hold the queries of Aurora, Elsevier, SIRIS and Auckland as text2sdg translated them | GPL-3, as text2sdg (`LICENSE`); the SIRIS rows also under the terms of CC BY-SA 4.0, see below |
| `src/sdg_tech_tagger/wos_queries/aurora/` | Aurora SDG queries v5.0.3 | CC BY 4.0 (`LICENSES/CC-BY-4.0.txt`) |
| `src/sdg_tech_tagger/wos_queries/elsevier/` | Elsevier SDG queries 2019, version 1 | CC BY 4.0 |
| `src/sdg_tech_tagger/wos_queries/auckland/` | University of Auckland SDG queries v2.0 | CC BY 4.0 for this adaptation; see the note on Auckland below |
| `src/sdg_tech_tagger/wos_queries/siris/` | SIRIS Academic SDG vocabulary v1.3 | CC BY-SA 4.0 (`LICENSES/CC-BY-SA-4.0.txt`) |
| `src/sdg_tech_tagger/wos_queries/NOTES.tsv`, `README.md`, `SHA256SUMS` | written for this package | CC BY 4.0 |
| `src/sdg_tech_tagger/adt/simplified/` | the simplified technology query, Kevin Michoud | CC BY 4.0 |
| `src/sdg_tech_tagger/adt/extended/`, `src/sdg_tech_tagger/adt/extended_wos/` | the extended technology query, Kevin Michoud; terms drawn from the sources listed in `provenance.tsv` and `CREDITS.md` | CC BY 4.0 |

## Changes made to the sources

- **text2sdg's query tables** are exported from the installed R package to
  parquet without renaming, filtering or reordering. The port applies its
  corrections at run time, in `corrected` mode; the tables are unchanged.
- **The Web of Science files** are translations of the published queries
  from Scopus syntax to Web of Science syntax: `W/n` becomes `NEAR/n`,
  `AND NOT` becomes `NOT`, `TITLE-ABS-KEY` becomes `TS`, every term is
  quoted and every group parenthesised, and a chain `A W/n B W/n C` is
  written as `(A NEAR/n B) AND (B NEAR/n C)`. What may not run or may not
  mean the same on the Web of Science is listed query by query in
  `wos_queries/NOTES.tsv`. No term is added, dropped or reworded.

## SIRIS, ShareAlike

The SIRIS vocabulary is published under CC BY-SA 4.0. Its rows in the
query tables and the files of `wos_queries/siris/` are adaptations, so they
are shared under CC BY-SA 4.0. Creative Commons lists GPL-3 as a compatible
licence for BY-SA 4.0 adaptations, in that direction only, which is why the
SIRIS rows can sit in the GPL-3 query tables.

## Auckland

The University of Auckland publishes its SDG queries and keyword list
without stating a licence. This package carries them, in text2sdg's table
and as Web of Science queries, adapted to another syntax and not changed in
what they search, and cites them as the University asks (`CREDITS.md`).
The CC BY 4.0 above covers the adaptation written for this package; it
cannot grant rights in the University's own work.
