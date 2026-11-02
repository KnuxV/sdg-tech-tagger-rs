# The contract of the port

What goes in, what comes out, and what happens to an input that does not
fit. Tests are written from this file and from fixtures run through the
oracles; the implementation is written against the tests. Where the
behaviour is text2sdg's or corpustools', this file names where it is shown
and does not restate it. Decisions behind it: D007, D008, D010 to D014,
D016 to D018, D020 to D023 and D028.

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
- The text is matched as given: no trimming, no normalisation
  (`docs/reference-set.md`).
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
  the input rows (D007).

### Input that does not fit

Each stops the call before any matching, with an exception whose message
names the problem (D012). Nothing is dropped silently.

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
  run does not resume (D012, D007).
- Exit status 0 on success; on an input that does not fit, a message on
  standard error that names the problem and a status other than 0.

## How a text is matched

By the engine rules (D008), those of corpustools 0.5.2, in both modes.

- **Tokens.** ICU word boundaries, the pieces that are only whitespace
  dropped, every other piece a token with its position
  (`docs/corpustools-matching.md`, "Tokens"). The port cuts with ICU4X
  (D013).
- **Case** is ignored when matching and kept in `features`.
- **The query language**, sequences, proximity, wildcards, braces, `AND`,
  `OR`, `NOT`: `docs/corpustools-matching.md`, with the source in
  `vendor/corpustools_0.5.2/` (`src/parse_query.cpp`, `R/query.r`,
  `R/search.r`, `src/hit_ids_*.cpp`).
- **Which tokens a search string reports**, in the modes `unique_hits` and
  `features` of corpustools: `vendor/corpustools_0.5.2/R/search.r` and the
  note on it in `docs/` once D025's study is in.

## What each system returns

The search strings are those of `queries/`, as text2sdg ships them.

- **Elsevier, SIRIS, Auckland**: a query fires in a document when its
  search string matches there (`vendor/text2sdg_1.1.2/R/elsevier.R`,
  `siris.R`, `auckland.R`).
- **Aurora**: `vendor/text2sdg_1.1.2/R/aurora.R`, with the two workarounds
  of `r/detect_text2sdg.R` (`docs/text2sdg-behaviour.md`, defects 1 and 2):
  the three internal tables, the three queries written by hand, and the
  query text that sits under two goals, SDG-04 id 8 and SDG-12 id 15,
  returned under both.

### Compatible mode

The firings are those of `r/detect_text2sdg.R` on the same texts, defects 3
and 4 of `docs/text2sdg-behaviour.md` included. This includes SDG-11 id 3
and SDG-03 id 8, which text2sdg filters by distance on the tokens the
`unique_hits` mode reports.

### Corrected mode

Compatible mode with the six accepted corrections. The firings are those of
`r/detect_text2sdg_corrected.R` on the same texts.

| | entry | what changes |
|---|---|---|
| 1 | D010, D018 | an `aurora_w` query fires only if a token satisfying its first search string lies within 3 positions of a token satisfying its second |
| 2 | D016 | SDG-02 id 5 searches its first clause with `~6` |
| 3 | D017, D018, D023 | a chain of `aurora_and`, and the chain inside SDG-03 id 3, fires only if some token satisfies both of its search strings |
| 4 | D020 | SDG-03 id 16 searches `<(<bronchitis>) (<chronic>)>~3` |
| 5 | D021 | SDG-15 id 15 searches `<( <prevent*> ) ( <extinction> )>~3` as its first search string |
| 6 | D022 | SDG-03 id 9 searches `<(<national>) (<strategy*> OR <program*>)>~3` |

The tokens the checks of corrections 1 and 3 look at are those the
`features` mode of corpustools reports (D018). The exact search strings of
corrections 2, 4, 5 and 6 are in `STRING_CORRECTIONS` of
`r/detect_text2sdg_corrected.R`.

## What counts as agreeing

- The gate (D011): the set of (identifier, `system`, `sdg`, `query_id`) is
  exactly the oracle's, the oracle of the mode, on the same texts.
- `features` is compared with the oracle's two ways, as the exact string
  and as the set of distinct tokens. Both rates are measured and
  journalled; neither gates until Kevin decides how exact the reported
  tokens must be (D011, D025). The port aims at text2sdg's string:
  the tokens corpustools reports in the mode text2sdg searches in, in the
  order and with the repetition text2sdg pastes them (`R/aurora.R` and
  `R/elsevier.R` repeat a token once per match, `R/siris.R` keeps each
  token once).
- The tests assert the key rows exactly. The `features` of a fixture are
  stored with it, as the oracle returned them, so that they can be
  asserted once D025 is decided.

## Not in this contract

- A goal filter: all goals always run (D012).
- text2sdg's `hit` column (D012).
- Resuming an interrupted command (D007).
- Any later version of a system than the one text2sdg 1.1.2 ships (D027).
