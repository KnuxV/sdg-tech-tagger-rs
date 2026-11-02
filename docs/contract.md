# The contract of the port

What goes in, what comes out, and what happens to an input that does not
fit. Tests are written from this file and from fixtures run through the
oracles, text2sdg 1.1.2 run in R in each mode; the implementation is
written against the tests. Where the behaviour is text2sdg's or
corpustools', this file names the file of their source (as published on
CRAN) where it is shown and does not restate it.

## The function

```python
from sdg_tech_tagger import detect

rows = detect(
    documents,                    # polars.DataFrame
    systems=("Aurora", "Elsevier", "SIRIS", "Auckland"),
    mode="corrected",             # or "compatible"
    id_column="UT",
    text_column="text",
    threads=None,                 # None: every core
)
```

### Input

- `documents` is a `polars.DataFrame` with a column named by `id_column`
  and one named by `text_column`, both of type `String`. Other columns are
  ignored.
- The text is matched as given: no trimming, no normalisation.
- `systems` is a sequence of distinct names out of `Aurora`, `Elsevier`,
  `SIRIS` and `Auckland`, in any order, at least one.
- `mode` is `"compatible"` or `"corrected"`.
- `threads` is `None` or a positive integer.

### Output

A `polars.DataFrame` with exactly these columns, in this order:

| column | type | |
|---|---|---|
| the identifier, named as `id_column` | `String` | the document |
| `system` | `String` | `Aurora`, `Elsevier`, `SIRIS` or `Auckland` |
| `sdg` | `String` | `SDG-01` to `SDG-17` |
| `query_id` | `Int32` | the query, as text2sdg numbers it |
| `features` | `String` | the matched tokens, as written in the document, joined with `", "` |

- One row per firing: a (document, system, `sdg`, `query_id`) that fired.
  The four columns are a key. A document on which nothing fires has no
  row. An Aurora query is identified by (`sdg`, `query_id`); the other
  systems number their queries 1 to n.
- Rows are sorted by the identifier, `system`, `sdg`, `query_id`, each in
  ascending order of its value (`String` in byte order), so
  `Auckland < Aurora < Elsevier < SIRIS`.
- An empty input table, or one on which nothing fires, gives a table with
  these columns and types and no row.
- The output is the same whatever `threads` is and whatever the order of
  the input rows.

### Input that does not fit

Each stops the call before any matching, with an exception whose message
names the problem. Nothing is dropped silently.

| input | exception |
|---|---|
| `documents` is not a `polars.DataFrame` | `TypeError` |
| a named column is missing | `ValueError` |
| a named column is not of type `String` | `TypeError` |
| a missing identifier (null) | `ValueError` |
| an identifier that appears twice | `ValueError` |
| a missing text (null) | `ValueError` |
| `systems` empty, a name not among the four, or a name given twice | `ValueError` |
| `mode` not one of the two | `ValueError` |
| `threads` not `None` and not a positive integer | `ValueError` |

An empty text, or a text of whitespace only, is valid: it has no token and
gives no row. The oracle refuses such a text, so this case is shown by
this contract and not by R.

## The command

```bash
uv run sdg-tech-tagger --documents IN.parquet --out OUT.parquet \
  [--systems Aurora,Elsevier,SIRIS,Auckland] [--mode corrected] \
  [--id-column UT] [--text-column text] [--batch-size 20000] [--threads N]
```

- It works through `IN.parquet` in batches of `--batch-size` rows, so that
  a file of millions of documents does not have to be held in memory, and
  writes `OUT.parquet`.
- `OUT.parquet` holds exactly the rows, columns, types and order that
  `detect` returns for the whole of `IN.parquet` with the same arguments.
  The batch size changes nothing in it.
- The identifiers of the whole file are checked first, as `detect` checks
  them: an input that does not fit stops the run before any matching and
  writes no `OUT.parquet`. A batch with a missing text stops the run in
  the same way, and `OUT.parquet` is not written.
- An `OUT.parquet` that exists is overwritten only when the run ends; the
  run does not resume.
- Exit status 0 on success; on an input that does not fit, a message on
  standard error that names the problem and a status other than 0.

## How a text is matched

By the engine rules, those of corpustools 0.5.2, in both modes.

- **Tokens.** ICU word boundaries, the pieces that are only whitespace
  dropped, every other piece a token with its position
  (corpustools 0.5.2, `R/tokenize.r`). The port cuts with ICU4X.
- **Case** is ignored when matching and kept in `features`.
- **The query language**, sequences, proximity, wildcards, braces, `AND`,
  `OR`, `NOT`: the source of corpustools 0.5.2 (`src/parse_query.cpp`, `R/query.r`,
  `R/search.r`, `src/hit_ids_*.cpp`).
- **Which tokens a search string reports**, in the modes `unique_hits` and
  `features` of corpustools: corpustools 0.5.2, `R/search.r`.

## What each system returns

The search strings are those of the query tables of text2sdg 1.1.2, as it
ships them (`query_tables/` of the package).

- **Elsevier, SIRIS, Auckland**: a query fires in a document when its
  search string matches there (text2sdg 1.1.2, `R/elsevier.R`,
  `siris.R`, `auckland.R`).
- **Aurora**: text2sdg 1.1.2, `R/aurora.R`: the three internal tables and
  the three queries written by hand, and the query text that sits under two
  goals, SDG-04 id 8 and SDG-12 id 15, returned under both. text2sdg 1.1.2
  cannot run Aurora over all goals in one call, nor search a goal that has
  no `aurora_w` query; the oracle works around both, by calling Aurora once
  per goal and by turning an empty query vector into a query that cannot
  match. Neither workaround changes a firing.

### Compatible mode

The firings are those of text2sdg 1.1.2 on the same texts, its defects
included: the outer proximity of the `aurora_w` queries is never applied,
and a query text under two goals is returned under both. This includes SDG-11 id 3
and SDG-03 id 8, which text2sdg filters by distance on the tokens the
`unique_hits` mode reports.

### Corrected mode

Compatible mode with six corrections, each of which restores what the
published query says. The firings are those of text2sdg 1.1.2 on the same
texts, run with the six corrections applied.

| | what changes |
|---|---|
| 1 | an `aurora_w` query fires only if a token satisfying its first search string lies within 3 positions of a token satisfying its second |
| 2 | SDG-02 id 5 searches its first clause with `~6` |
| 3 | a chain of `aurora_and`, and the chain inside SDG-03 id 3, fires only if some token satisfies both of its search strings |
| 4 | SDG-03 id 16 searches `<(<bronchitis>) (<chronic>)>~3` |
| 5 | SDG-15 id 15 searches `<( <prevent*> ) ( <extinction> )>~3` as its first search string |
| 6 | SDG-03 id 9 searches `<(<national>) (<strategy*> OR <program*>)>~3` |

The tokens the checks of corrections 1 and 3 look at are those the
`features` mode of corpustools reports. The exact search strings of
corrections 2, 4, 5 and 6 are in `rust/src/systems.rs`.

## What counts as agreeing

- The gate: the set of (identifier, `system`, `sdg`, `query_id`) is
  exactly the oracle's, the oracle of the mode, on the same texts.
- `features` is compared with the oracle's two ways, as the exact string
  and as the set of distinct tokens. Both rates are measured and
  recorded; neither gates. The port aims at text2sdg's string:
  the tokens corpustools reports in the mode text2sdg searches in, in the
  order and with the repetition text2sdg pastes them (`R/aurora.R` and
  `R/elsevier.R` repeat a token once per match, `R/siris.R` keeps each
  token once).
- The tests assert the key rows exactly. The `features` of a fixture are
  stored with it, as the oracle returned them, and are not asserted.

## Not in this contract

- A goal filter: all goals always run.
- text2sdg's `hit` column.
- Resuming an interrupted command.
- Any later version of a system than the one text2sdg 1.1.2 ships.
