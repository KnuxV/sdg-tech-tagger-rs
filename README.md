# sdg-tech-tagger-rs

Tag scientific texts with the UN Sustainable Development Goals (SDGs) and with advanced digital technologies, by published Boolean queries.

- **SDGs.** To tag texts with SDGs, the package ports the R package [text2sdg](https://github.com/dwulff/text2sdg) to Rust, for speed, with a Python interface. It has text2sdg's four query systems: Aurora, Elsevier, SIRIS and Auckland. The texts are indexed with [tantivy](https://github.com/quickwit-oss/tantivy), a full-text search library written in Rust and inspired by Apache Lucene. The queries are evaluated by the package itself on the tantivy index. It returns, for each text, which query of which system fired and on which words.
- **Technologies.** There are two variations of queries to annotate advanced digital technologies: a simplified version and an extended version. The extended version contains more keywords related to advanced digital technologies and is designed to have a better recall at the potential expense of precision.

Each comes in three forms: a Python program (text in, tags out), queries for the Web of Science, and a recipe for OpenAlex.

## Install

From PyPI, with Python 3.13 or later. Wheels are built for Linux (x86_64 and aarch64), macOS (Intel and Apple silicon) and Windows (x64).

```bash
pip install sdg-tech-tagger-rs     # or: uv add sdg-tech-tagger-rs
```

The package imports as `sdg_tech_tagger`. On another platform, pip builds it from the source distribution, which needs a Rust toolchain. From a clone of the repository:

```bash
git clone https://github.com/KnuxV/sdg-tech-tagger-rs
cd sdg-tech-tagger-rs
uv sync            # or: pip install .
```

## SDGs in Python

```python
import polars as pl
from sdg_tech_tagger import detect

documents = pl.DataFrame({
    "UT": ["a", "b"],
    "text": [
        "Extreme poverty persists in rural households.",
        "Access to clean drinking water and sanitation in schools.",
    ],
})
rows = detect(documents)                     # corrected mode, four systems
rows = detect(documents, mode="compatible")  # what text2sdg 1.1.2 returns
rows = detect(documents, systems=["Aurora"])
```

`rows` has one row per firing, a (document, system, goal, query) that matched, with the columns `UT`, `system`, `sdg` (`SDG-01` to `SDG-17`), `query_id` and `features` (the matched words, as written in the text). A document on which nothing fires has no row. The identifier and text columns can be renamed with `id_column` and `text_column`. The full contract is in `docs/contract.md`.

For large files, the command reads and writes parquet in batches:

```bash
sdg-tech-tagger --documents IN.parquet --out OUT.parquet \
  [--systems Aurora,Elsevier,SIRIS,Auckland] [--mode corrected] \
  [--id-column UT] [--text-column text] [--batch-size 20000] [--threads N]
```

### The two modes

- **`compatible`** returns exactly what text2sdg 1.1.2 returns, its defects included. Use it to reproduce earlier work done with text2sdg.
- **`corrected`**, the default, applies a short list of corrections, each of which restores what a published Aurora query says and can be checked in R:

  | correction | what it restores                                                                                                                       |
  | ---------- | -------------------------------------------------------------------------------------------------------------------------------------- |
  | 1          | the outer `W/3` of the 21 Aurora queries that join two searches by proximity is applied (text2sdg computes it and discards the result) |
  | 2          | Aurora SDG-02 query 5 is searched with its published distance of 6                                                                     |
  | 3          | a chain `A W/n B W/n C` fires only when its two pairs share the middle word (also inside SDG-03 query 3)                               |
  | 4          | Aurora SDG-03 query 16 searches "bronchitis" within 3 words of "chronic"                                                               |
  | 5          | Aurora SDG-15 query 15 gets back its first pair                                                                                        |
  | 6          | a published query is read with Scopus's operator precedence (Aurora SDG-03 query 9)                                                    |

  Elsevier, SIRIS and Auckland return the same in both modes.

### Agreement with text2sdg

On a random sample of 300,001 OpenAlex works (articles and reviews, 2019 to 2024), texts never used to develop the port, the R package text2sdg 1.1.2 and this package return the same firings with the same matched words, but for ten Auckland firings:

| mode                                       | firings, R | firings, this package | R only | this package only | same matched words |
| ------------------------------------------ | ---------- | --------------------- | ------ | ----------------- | ------------------ |
| compatible                                 | 389,935    | 389,932               | 3      | 0                 | 389,925            |
| corrected (R with the corrections applied) | 387,795    | 387,792               | 3      | 0                 | 387,785            |

The ten differ on Korean text in which Latin letters or digits are glued to Hangul (`COVID-19로`): the two packages cut such text into words differently, so text2sdg sometimes matches a word this package does not. Seven works of the sample were left out: text2sdg stops with an error on a text holding the character U+FFFE, which this package reads. Every firing, from both, is in the data record [sdg-tech-tagger-rs-data](https://github.com/KnuxV/sdg-tech-tagger-rs-data).

This package labelled all 300,001 works in about 20 seconds on 8 threads; text2sdg took about 2 hours 25 minutes in compatible mode, split over five processes.

## Technologies in Python (ADTs)

Two versions ship, as compiled patterns. Neither is the default. Every term of both, group by group, is listed in `docs/technology-queries.md`.

| version    | file                           | groups                                   | terms |
| ---------- | ------------------------------ | ---------------------------------------- | ----- |
| simplified | `adt/simplified/patterns.json` | AI (with big data), IOT, CI, BL, ROB, AM | 285   |
| extended   | `adt/extended/patterns.json`   | the six above and UMBRELLA               | 868   |

The extended version has more terms per group, for a higher recall at some cost of precision. It also accepts plurals, the closed spelling of hyphenated terms (`3d-printing` and `3dprinting`), and reads a decimal number as one word.

```python
import json
from importlib.resources import files

import polars as pl
from sdg_tech_tagger.adt import translate

documents = pl.DataFrame({
    "id": ["a"],
    "title": ["A 3D-printing approach"],
    "abstract": ["With no other technology."],
})

for name in ["adt/simplified/patterns.json", "adt/extended/patterns.json"]:
    query = json.loads((files("sdg_tech_tagger") / name).read_text())
    patterns = {entry["code"]: entry["pattern"] for entry in query["definitions"]}
    flags = translate.flag(
        documents, patterns, ["title", "abstract"],
        decimal_whole=query.get("decimal_whole", False),
    )
    print(name, flags.row(0, named=True))
```

`flags` has the input columns and one Boolean column per group. Here `AM` (additive manufacturing) is true in both versions.

## Web of Science

Ready to paste in the advanced search of the Web of Science, one line per file.

- `src/sdg_tech_tagger/wos_queries/<system>/SDG-<nn>.txt`: the four SDG systems, one query per system and goal, translated from the published queries. `NOTES.tsv` lists, query by query, what may not run or may not mean the same on the Web of Science; the `README.md` beside them says what they are not. All 65 queries were accepted by the Web of Science.
- `src/sdg_tech_tagger/adt/simplified/`: the simplified technology query, as it was run on the Web of Science.
- `src/sdg_tech_tagger/adt/extended_wos/`: the extended technology query with every plural and closed spelling written out, one file per group and `ALL.txt` for all groups. Its `README.md` says where it differs from the Python program (the decimal rule cannot be written).

The Web of Science returns records, not which query fired on which words, and has its own matching: these files approximate the Python program, they do not reproduce it. To combine a technology with a goal, run each once and combine the numbers of the search history, for example `#1 AND (#2 OR #3 OR #4 OR #5)`.

## OpenAlex

The OpenAlex API cannot express the SDG queries (Aurora's proximity operators with `OR` lists and wildcards inside them have no equivalent), so the OpenAlex form is a recipe: fetch title and abstract, then run the package on them.

1. Fetch the works, from the API with `select=id,title,abstract_inverted_index` (cursor paging, `per_page=100`, a free API key recommended), or from the OpenAlex snapshot.
2. Rebuild each abstract from its inverted index.
3. Build the text as `title + ". " + abstract` and run `detect` and `translate.flag` on it.

```python
def rebuild_abstract(inverted_index):
    """Rebuild an OpenAlex abstract from its inverted index.

    Consumes the ``abstract_inverted_index`` of a work (a mapping from each
    word to the positions where it occurs, or None) and produces the abstract
    as one string, words joined by single spaces in position order ("" when
    there is no index).
    """
    if not inverted_index:
        return ""
    positions = {
        position: word
        for word, places in inverted_index.items()
        for position in places
    }
    return " ".join(positions[position] for position in sorted(positions))


assert rebuild_abstract({"Clean": [0], "water": [1, 4], "and": [2], "more": [3]}) == (
    "Clean water and more water"
)
assert rebuild_abstract(None) == ""
```

Some works have no abstract in OpenAlex; their title alone is then tagged.

## Credits and licences

The queries are the work of others; please cite them along with this package. `CREDITS.md` lists every source with its version, DOI and licence, and `CITATION.cff` gives them in machine-readable form.

- Code: GNU GPL version 3 only (GPL-3.0-only, `LICENSE`), as text2sdg and corpustools.
- Data files: CC BY 4.0, except what derives from SIRIS (CC BY-SA 4.0) and text2sdg's own query tables (GPL-3.0-only). Details in `LICENSE-DATA.md`.
- Auckland's queries are used with citation, adapted to another syntax and not changed in what they search; their source states no licence, and the licences above cannot grant rights in the University of Auckland's own work.
- Rust crates compiled into the extension: `THIRD_PARTY_LICENSES.md`.

## How AI was used

The port of text2sdg from R to Rust done using Claude Code 5.5. I have only supervised it and made sure the results were consistent on a 300,000 scientific publications dataset retrieved on OpenAlex. The port was necessary given the slowness of R and the need to classify millions of publications.
The query systems are not original works by me. This package only compiles them for simplicity and speed.
The extended ADT query system is an aggregate of queries found in the literature using Claude Code. The goal was to be more comprehensive that the simplified version.
Claude Opus was used for research and development.
