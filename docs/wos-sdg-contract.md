# Contract: the four systems written as Web of Science queries

Decision: D033. Module: `sdg_tech_tagger.wos_sdg`. Shipped files:
`src/sdg_tech_tagger/wos_queries/`.

## What this is for

The published queries of Aurora, Elsevier and Auckland are in Scopus
syntax, and the vocabulary of SIRIS is a table of keywords. This stage
writes each as a Web of Science query, one per system and goal, so that a
goal can be run there once and combined with other searches.

It proves one thing: the Web of Science text says what the published
query says, operator for operator, under the documented reading of each
syntax. It does not prove what the Web of Science returns, and nothing
here is run there. It is not the port: the port follows the engine rules
of corpustools and reports firings.

## The two syntaxes

**Scopus, as read here** (D022; Scopus search tips). Operators, in any
case: `OR` binds first, then `W/n`, then `AND`, then `AND NOT`.
Parentheses group. A term is a text in double quotes, a text in braces,
or a bare word: a run of characters other than white space, parentheses,
braces and double quotes that is not an operator. `TITLE-ABS-KEY` before a
parenthesis is a field and is dropped. A no-break space is a space, and
the quotes `“` and `”` are `"`.

**Web of Science, as written here.** `NEAR/n`, `NOT`, `AND`, `OR`, terms
in double quotes, parentheses, and the tag `TS=`. The Web of Science
binds `NEAR/n` first, then `NOT`, then `AND`, then `OR`.

## Trees

Both readers produce the same kind of tree, a nested tuple:

- `("term", text)`: the text as written, white space collapsed to single
  spaces and stripped, case kept;
- `("or", (a, b, ...))` and `("and", (a, b, ...))`: two or more operands,
  in the order written;
- `("not", a, b)`: `a` and not `b`;
- `("near", n, a, b)`: `a` within `n` words of `b`, `n` an integer.

Operands joined by one operator at one level are one node: `a OR b OR c`
is one `or` of three. Parentheses that are written are kept as nesting:
`(a OR b) OR c` is an `or` of an `or` and a term. Parentheses around a
single operand add nothing: `((a))` is `a`. `a AND NOT b AND NOT c` is
`("not", ("not", a, b), c)`.

## `read_scopus(query) -> tree`

Consumes one published query. Produces its tree, with two rewritings:

- **A chain.** Three or more operands joined by `W/n` at one level,
  `a W/x b W/y c`, become `("and", (("near", x, a, b), ("near", y, b, c)))`,
  one `near` per neighbouring pair, as its own node.
- **Braces and bare words** become plain terms.

Raises `QueryError` (a `ValueError` defined in this module) for:

- `PRE/n`;
- an operand of `W/n` that holds an `and` or a `not`, at any depth, the
  `and` of a chain included: the Web of Science takes no `AND` inside a
  `NEAR`;
- a field other than `TITLE-ABS-KEY`: an upper-case word with hyphens
  right before a parenthesis;
- a term with a double quote inside braces, or a word that holds two
  wildcards side by side (`**`, `*?`, `?*`, `??`);
- a parenthesis, a quote or a brace that is not closed, an operator with
  no operand, two operands with no operator, an empty query.

Examples:

| query | tree |
|---|---|
| `"a b"` | `("term", "a b")` |
| `{a  b}` | `("term", "a b")` |
| `poverty` | `("term", "poverty")` |
| `TITLE-ABS-KEY ( {a} OR b )` | `("or", (("term", "a"), ("term", "b")))` |
| `"a" OR "b" W/3 "c" OR "d"` | `("near", 3, ("or", (a, b)), ("or", (c, d)))` |
| `"a" AND "b" OR "c"` | `("and", (a, ("or", (b, c))))` |
| `"a" AND "b" AND NOT "c"` | `("not", ("and", (a, b)), c)` |
| `"a" w/3 "b" and not "c"` | `("not", ("near", 3, a, b), c)` |
| `("a") W/3 ("b") W/6 ("c")` | `("and", (("near", 3, a, b), ("near", 6, b, c)))` |
| `"p" AND "a" W/3 "b" W/3 "c"` | `("and", (p, ("and", (("near", 3, a, b), ("near", 3, b, c)))))` |
| `("a" W/3 "b") W/3 "c"` | `("near", 3, ("near", 3, a, b), c)` |
| `"a" PRE/3 "b"` | `QueryError` |
| `"a" W/3 ("b" AND "c")` | `QueryError` |
| `("a" W/3 "b" W/3 "c") W/3 "d"` | `QueryError` |
| `TITLE ( "a" )` | `QueryError` |

(In the table `a` stands for `("term", "a")`.)

## `write_wos(tree) -> str`

Consumes a tree. Produces Web of Science text:

- a term: `"text"`;
- `or`: `(A OR B OR C)`; `and`: `(A AND B)`; `not`: `(A NOT B)`;
  `near`: `(A NEAR/n B)`, where `A`, `B` are the operands written by the
  same rules.

Every node that is not a term is in parentheses, the outermost included.
Raises `QueryError` for a term that holds a double quote.

`write_wos(read_scopus('"p" AND "a" W/3 "b" W/3 "c"'))` is
`("p" AND (("a" NEAR/3 "b") AND ("b" NEAR/3 "c")))`.

## `read_wos(text) -> tree`

Consumes Web of Science text of the kind above, with or without a leading
`TS=` or `TS =`. Produces its tree, by the Web of Science's binding order.
Operators are read in any case. A `NEAR/n` joins exactly two operands at
one level; three raise `QueryError`, as do the unclosed and the empty
cases of `read_scopus`. Unquoted words that are not operators raise
`QueryError`.

**The round trip.** For every query `q` that `read_scopus` reads:
`read_wos(write_wos(read_scopus(q))) == read_scopus(q)`.

## `notes(tree) -> list[tuple[str, str]]`

Consumes a tree. Produces what in it may not run on the Web of Science or
may not mean there what it meant in Scopus, as `(code, piece)` pairs, in
the order of the written text; a node comes before its operands.

| code | when | piece |
|---|---|---|
| `nested-proximity` | a `near` with a `near` anywhere inside an operand | `write_wos` of the outer `near` |
| `left-truncation` | a word of a term starts with `*` or `?` | the term text |
| `short-stem` | a word of a term has its first wildcard after one or two characters | the term text |
| `non-ascii` | a term holds a character outside ASCII | the term text |
| `parenthesis` | a term holds `(` or `)` | the term text |

A term gives at most one pair per code, in the order of the table.

`read_scopus` cannot keep two things a note needs, so:

## `translate(query) -> Translation`

`Translation` is a named tuple `(text, notes)`. Consumes one published
query. Produces `write_wos(read_scopus(query))` and `notes` of that tree,
to which two codes are added, each where its piece is written:

| code | when | piece |
|---|---|---|
| `chain` | a chain was rewritten | `write_wos` of the `and` it became |
| `braces-wildcard` | a term in braces holds `*` or `?` | the term text |

`chain` comes before the notes of the node; `braces-wildcard` is the
first note of its term.

`translate('{a*} W/3 "b" W/3 "c"')` is the text
`(("a*" NEAR/3 "b") AND ("b" NEAR/3 "c"))` and the notes
`[("chain", '(("a*" NEAR/3 "b") AND ("b" NEAR/3 "c"))'), ("braces-wildcard", "a*"), ("short-stem", "a*")]`.

## `siris_expression(keyword, extra) -> Translation`

Consumes one row of the SIRIS vocabulary: the keyword and its extra
terms, a text with `|` between terms, or `None` or empty. Each is
stripped, inner white space collapsed; an empty extra term is dropped.
Produces:

- no extra term: `"keyword"`;
- one: `("keyword" AND "e1")`;
- several: `("keyword" AND ("e1" OR "e2"))`.

This is the vocabulary's rule, the extra terms "should co-appear with the
key-term", as `probes/published_audit_probe.py` reads it. Notes as
`notes` gives them. Raises `QueryError` for an empty keyword and for a
double quote.

## `goal_query(expressions) -> str`

Consumes the Web of Science texts of one goal, in order. Produces one
line: `TS=(` , the texts joined by ` OR `, a repeat dropped where it comes
second, `)`, and a newline. Raises `QueryError` for an empty list.

`goal_query(['"a"', '("b" AND "c")', '"a"'])` is
`'TS=("a" OR ("b" AND "c"))\n'`.

## `build(published) -> dict[str, str]`

Consumes the path of `published/`. Produces the text of every shipped
file by its name relative to `wos_queries/`. It needs `openpyxl`, a
development dependency, and imports it when called.

Sources and order:

- **Aurora**, `aurora/sdg-queries-v5.0.3.zip`: in each `query_SDG<n>.xml`,
  every `query-line` element in document order, its text translated by
  `translate`. File `aurora/SDG-<nn>.txt`, 17 goals.
- **Elsevier**, `elsevier/2019_v1/SDG_queries_collated_20191010.xlsx`,
  the active sheet, columns SDG and Query after the header; a row with no
  query is skipped. `elsevier/SDG-<nn>.txt`, 16 goals.
- **Auckland**, `auckland/uoa_sdg_queries_v_2.0.xlsx`, sheet
  `uoa_sdg_queries`, columns SDG (`SDG<n>`) and Search Query.
  `auckland/SDG-<nn>.txt`, 16 goals.
- **SIRIS**, `siris/sdg_vocabulary_V.1.3 [zenodo].xlsx`, every sheet but
  `README`, rows after the header in workbook order: column 1 the goal
  (`SDG <n>`), column 3 the keyword, column 4 the extra terms. The goal
  is the row's column, not the sheet. `siris/SDG-<nn>.txt`, 16 goals.

Each goal file is `goal_query` of its expressions. `<nn>` has two digits.

`NOTES.tsv` comes last: a header `system`, `sdg`, `line`, `code`, `piece`,
tab-separated, then one row per note, systems in the order aurora,
elsevier, auckland, siris, goals in order, `line` the position of the
expression in its goal counted from 1 before repeats are dropped, a
repeated expression giving no row. `sdg` is written `SDG-<nn>`. A tab or
a newline never occurs in a piece.

## The shipped files

`src/sdg_tech_tagger/wos_queries/` holds, byte for byte, what
`build("published")` produces: 65 goal files and `NOTES.tsv`. Beside them
`SHA256SUMS`, in the format of `sha256sum`, lists those 66 files by their
relative names, and `README.md` says what they are and are not. Each goal
file is read back by `read_wos`.

## What cannot be said, known and accepted

- **Stemming.** Scopus also finds the plural and spelling variants of a
  term in double quotes or bare. A quoted Web of Science term is searched
  as written. The files are narrower than Scopus there, and as the port's
  engine rules are.
- **Braces.** In Scopus a `*` in braces is a character. Here it is a
  wildcard (`braces-wildcard`).
- **Chains.** Scopus does not document how `A W/3 B W/3 C` is read; it is
  written as two pairs (`chain`).
- **Keywords.** `TITLE-ABS-KEY` and `TS` both read title, abstract and
  keywords, and the keyword fields of the two databases are not the same.
- **The engine.** Whether the Web of Science accepts a proximity inside a
  proximity, a wildcard at the start of a word, and a query of this
  length is not known here.
