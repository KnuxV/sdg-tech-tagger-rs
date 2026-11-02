# Contract: the extended technology query written as Web of Science queries

Module: `sdg_tech_tagger.adt.wos_form`. Shipped files:
`src/sdg_tech_tagger/adt/extended_wos/`.

## What this is for

The extended query is a list of terms and three rules that live in its compiled
patterns only: a term also matches its regular plural, a term written with
a hyphen also matches its closed spelling, and a decimal is kept whole
(the options stored in `adt/extended/patterns.json`). The query
files of `adt/extended/` hold the terms in Web of Science syntax without
those rules, so run as they are they are not the extended query.

This stage writes the extended query as Web of Science queries that carry the first
two rules, by writing out every spelling the pattern of a term accepts as
a term of its own. A term with no rule applied is called a **plain term**
here: it is searched as the Web of Science query of `adt/simplified/` is, with
every option of `translate` off.

It is the other direction of `adt.wos_query` and `adt.translate`, which
go from a query file to patterns. Neither is changed by this stage.

## What is proven and what is not

Proven here, by the tests: the plain terms of a term, compiled by
`translate` with every option off, match exactly the texts the term
matches when compiled with `hyphen_closed_form` and `plural_tolerant` as
given and `decimal_whole` off. That is an equality inside this package's
own matcher.

Not proven here: what the Web of Science returns for these queries. The
package's matcher with every option off flagged again 163,723 of 163,739
records the Web of Science had returned for the query of `adt/simplified/`.
When this contract was written no query of this stage had been run on the
Web of Science; the eight files were run there afterwards and accepted
(`adt/extended_wos/README.md`).

## Inputs

- A term, as `wos_query.parse_terms` returns it: lower-case, stripped, one
  space where it had whitespace.
- The options of the artefact (`patterns.json`):
  `hyphen_closed_form`, `plural_tolerant`, `plural_exceptions`.
  `decimal_whole` is read and not used (see "What cannot be written").

## `plain_terms(term, hyphen_closed_form=False, plural_tolerant=False) -> list[str]`

Consumes one term. Produces the plain terms that together say what the
term says under the two options, in a fixed order, without repeats.

A **word** of a term is a run of the characters `a` to `z`, `0` to `9`
and `*`, as in `translate.term_pattern`. A **separator** is what stands
between two words. What stands before the first word or after the last is
dropped. A term is its words and the separators between them.

**Spellings of the separators.** With `hyphen_closed_form`, a separator
that holds a hyphen has two spellings: as written, and nothing, the two
words glued. Any other separator, and every separator without the option,
has one spelling: as written. A term with k hyphenated separators has
2^k spellings. They are ordered as binary numbers of k digits, the first
separator the highest digit, "as written" before "nothing".

**Endings of the last word.** With `plural_tolerant`, when the last word
does not end with `*` and its last character is a letter:

- if the last word has more than one character, ends with `y`, and the
  character before the `y` is not one of `a e i o u`: two endings, the
  word as written and the word with its `y` replaced by `ies`;
- otherwise three endings: the word as written, the word plus `s`, the
  word plus `es`.

In every other case the last word has one ending, as written. These are
the plurals of Amendment 1 of the translation contract.

**Order.** For each spelling of the separators in order, each ending in
order.

**A term that does not fit.** Raises `QueryError` (the class of
`wos_query`) in every case where
`translate.term_pattern(term, hyphen_closed_form, plural_tolerant)` raises
it. Also raises `QueryError` when `hyphen_closed_form` is on and a word
that ends with `*` stands right before a hyphenated separator: gluing
would put the `*` inside a word, which a plain term cannot hold.

Examples:

| term | closed | plural | plain terms |
|---|---|---|---|
| `random forest` | any | off | `random forest` |
| `random forest` | any | on | `random forest`, `random forests`, `random forestes` |
| `digital economy` | off | on | `digital economy`, `digital economies` |
| `relay` | off | on | `relay`, `relays`, `relayes` |
| `robot*` | on | on | `robot*` |
| `gpt-4` | on | on | `gpt-4`, `gpt4` |
| `meta-learning` | off | off | `meta-learning` |
| `meta-learning` | on | off | `meta-learning`, `metalearning` |
| `meta-learning` | on | on | `meta-learning`, `meta-learnings`, `meta-learninges`, `metalearning`, `metalearnings`, `metalearninges` |
| `data-center*` | on | on | `data-center*`, `datacenter*` |
| `system-on-a-chip` | on | off | `system-on-a-chip`, `system-on-achip`, `system-ona-chip`, `system-onachip`, `systemon-a-chip`, `systemon-achip`, `systemona-chip`, `systemonachip` |
| `web 3.0` | on | on | `web 3.0` |
| ` -big data- ` | on | on | `big data`, `big datas`, `big dataes` |
| `multi*-class` | on | any | `QueryError` |
| `ro*bot` | any | any | `QueryError` |

**The equality.** For every term that does not raise, every pair of
options and every text:

```
translate.matches(translate.code_pattern(plain_terms(term, h, p)), text)
  == translate.matches(" " + translate.term_pattern(term, h, p), text)
```

both sides with `decimal_whole` off.

## `plain_code_terms(terms, hyphen_closed_form=False, plural_tolerant=False, plural_exceptions=()) -> list[str]`

Consumes the terms of one group in order. Produces the plain terms of each
in order, one list, a repeat dropped where it comes second. A term listed
in `plural_exceptions` is expanded with `plural_tolerant` off; terms and
exceptions are compared as `translate.code_pattern` compares them
(stripped, lower-cased, one space between words). An exception that is no
term of the list is ignored. Raises `QueryError` for an empty list.

`plain_code_terms(["ai", "ann"], False, True, ["ai"])` is
`["ai", "ann", "anns", "annes"]`.

## `query_text(terms) -> str`

Consumes plain terms. Produces one Web of Science query in the layout of
the files of `adt/extended/`: the line `TS = (`, then one line per term,
`("term") OR`, the last without ` OR`, then the line `)`, each line ended
by a newline. Raises `QueryError` for an empty list and for a term that
holds a double quote.

`query_text(["a b", "c*"])` is `'TS = (\n("a b") OR\n("c*")\n)\n'`.

`wos_query.parse_terms(query_text(terms))` is `terms`, for terms without
repeats in the form `parse_terms` returns.

## `render_gate(artefact) -> dict[str, str]`

Consumes an artefact as `translate.compile_queries` produces it. Produces
the text of each file, by name, in this order:

- `<code>.txt` for each definition in order: `query_text` of
  `plain_code_terms` of its terms, with the options of the artefact
  (`plural_exceptions` absent means none);
- `ALL.txt`: `query_text` of the plain terms of every definition in
  order, a repeat dropped where it comes second. One query for the whole
  query set, the umbrella terms included.

`decimal_whole` changes nothing in what is produced. Raises `QueryError`
for an artefact without definitions, and `KeyError` for a missing key
among `hyphen_closed_form`, `plural_tolerant`, `definitions`, and `code`
and `terms` of a definition.

## The shipped files

`src/sdg_tech_tagger/adt/extended_wos/` holds, byte for byte, what
`render_gate` produces from `adt/extended/patterns.json`: `AI.txt`,
`IOT.txt`, `CI.txt`, `BL.txt`, `ROB.txt`, `AM.txt`, `UMBRELLA.txt` and
`ALL.txt`. Beside them `SHA256SUMS`, in the format of `sha256sum`, lists
those eight files, and `README.md` says what they are and are not. The
directory is read-only once written; a new query set is a new directory.

Each of the eight files is read back by `wos_query.parse_terms`.

## What cannot be written

- **Decimals.** The extended query reads "0.5g" as one word, so `5g` does not match
  it, and "Industry 4.0" as `industry 4p0`. A Web of Science term cannot
  say that. The files are the extended query with `decimal_whole` off: they match
  "0.5g per day" for `5g`, and `industry 4.0` matches "industry 4 0". The
  extended query matches neither. In the other direction, it matches the text
  "industry 4p0" and the files do not.
- **Fields.** The package searches the text it is given, usually title and abstract. The files are written
  with `TS =`, as the queries of `adt/simplified/` and `adt/extended/` are, and on
  the Web of Science `TS` also searches the author keywords and Keywords
  Plus.
- **The engine.** See "What is proven and what is not".
