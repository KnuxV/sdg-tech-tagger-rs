# sdg-tech-tagger-rs

Tag scientific texts with the UN Sustainable Development Goals (SDGs) and
with advanced digital technologies, by published Boolean queries.

- **SDGs.** The four query systems of the R package
  [text2sdg](https://github.com/dwulff/text2sdg): Aurora, Elsevier, SIRIS
  and Auckland. The matching is a port of text2sdg to Rust, on the
  [tantivy](https://github.com/quickwit-oss/tantivy) search engine, with a
  Python interface. It returns, for each text, which query of which system
  fired and on which words.
- **Technologies.** Two versions of a set of queries on advanced digital
  technologies: the simplified query of the Nature Communications paper
  (citation: TODO (Kevin), to be added once the paper is published), and
  gate v2, the version of the PhD thesis.

Each comes in three forms: a Python program (text in, tags out), queries
for the Web of Science, and a recipe for OpenAlex.

These are queries, not a trained model: a tag means a published query
matched the text.

## Install

From source for now (a PyPI release will follow), from a clone of the
repository or from the source archive of the Zenodo record. It needs Python
3.13 or later and a Rust toolchain.

```bash
git clone https://github.com/OWNER/sdg-tech-tagger-rs   # TODO (Kevin): OWNER
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

`rows` has one row per firing, a (document, system, goal, query) that
matched, with the columns `UT`, `system`, `sdg` (`SDG-01` to `SDG-17`),
`query_id` and `features` (the matched words, as written in the text). A
document on which nothing fires has no row. The identifier and text columns
can be renamed with `id_column` and `text_column`. The full contract is in
`docs/contract.md`.

For large files, the command reads and writes parquet in batches:

```bash
sdg-tech-tagger --documents IN.parquet --out OUT.parquet \
  [--systems Aurora,Elsevier,SIRIS,Auckland] [--mode corrected] \
  [--id-column UT] [--text-column text] [--batch-size 20000] [--threads N]
```

### The two modes

- **`compatible`** returns exactly what text2sdg 1.1.2 returns, its defects
  included. Use it to reproduce earlier work done with text2sdg.
- **`corrected`**, the default, applies a short list of corrections, each of
  which restores what a published Aurora query says and can be checked in R:

  | correction | what it restores |
  |---|---|
  | 1 | the outer `W/3` of the 21 Aurora queries that join two searches by proximity is applied (text2sdg computes it and discards the result) |
  | 2 | Aurora SDG-02 query 5 is searched with its published distance of 6 |
  | 3 | a chain `A W/n B W/n C` fires only when its two pairs share the middle word (also inside SDG-03 query 3) |
  | 4 | Aurora SDG-03 query 16 searches "bronchitis" within 3 words of "chronic" |
  | 5 | Aurora SDG-15 query 15 gets back its first pair |
  | 6 | a published query is read with Scopus's operator precedence (Aurora SDG-03 query 9) |

  Elsevier, SIRIS and Auckland return the same in both modes.

### Agreement with text2sdg

On 2,000 OpenAlex works drawn at random from a sample of 300,001 works
(articles and reviews, 2019 to 2024), texts never used to develop the port,
the R package text2sdg 1.1.2 and this package return the same firings with
the same matched words:

| mode | firings, R | firings, this package | on one side only | same matched words |
|---|---|---|---|---|
| compatible | 2,746 | 2,746 | 0 | 2,746 |
| corrected (R with the corrections applied) | 2,729 | 2,729 | 0 | 2,729 |

The port labelled all 300,001 works in about 20 seconds on 8 threads; text2sdg,
at its speed on the 2,000, would take an estimated 5 hours on one core.

## Technologies in Python

Two versions ship, as compiled patterns. Neither is the default.

| version | file | groups | terms |
|---|---|---|---|
| Nature Communications paper, simplified | `adt/wos/adt_patterns_v1.json` | AI (with big data), IOT, CI, BL, ROB, AM | 285 |
| gate v2, PhD thesis | `adt/gate_v2/gate_patterns_v2.json` | the six above and UMBRELLA | 868 |

Gate v2 also accepts plurals, the closed spelling of hyphenated terms
(`3d-printing` and `3dprinting`), and reads a decimal number as one word.

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

for name in ["adt/wos/adt_patterns_v1.json", "adt/gate_v2/gate_patterns_v2.json"]:
    gate = json.loads((files("sdg_tech_tagger") / name).read_text())
    patterns = {entry["code"]: entry["pattern"] for entry in gate["definitions"]}
    flags = translate.flag(
        documents, patterns, ["title", "abstract"],
        decimal_whole=gate.get("decimal_whole", False),
    )
    print(name, flags.row(0, named=True))
```

`flags` has the input columns and one Boolean column per group. Here `AM`
(additive manufacturing) is true in both versions.

## Web of Science

Ready to paste in the advanced search of the Web of Science, one line per
file.

- `src/sdg_tech_tagger/wos_queries/<system>/SDG-<nn>.txt`: the four SDG
  systems, one query per system and goal, translated from the published
  queries. `NOTES.tsv` lists, query by query, what may not run or may not
  mean the same on the Web of Science; the `README.md` beside them says
  what they are not. All 65 queries were accepted by the Web of Science.
- `src/sdg_tech_tagger/adt/wos/`: the technology query of the Nature
  Communications paper, as it was run.
- `src/sdg_tech_tagger/adt/gate_v2_wos/`: gate v2 with every plural and
  closed spelling written out, one file per group and `ALL.txt` for the
  whole gate. Its `README.md` says where it differs from the Python gate
  (the decimal rule cannot be written).

The Web of Science returns records, not which query fired on which words,
and has its own matching: these files approximate the Python program, they
do not reproduce it. To combine a technology with a goal, run each once and
combine the numbers of the search history, for example
`#1 AND (#2 OR #3 OR #4 OR #5)`.

## OpenAlex

The OpenAlex API cannot express the SDG queries (Aurora's proximity
operators with `OR` lists and wildcards inside them have no equivalent), so
the OpenAlex form is a recipe: fetch title and abstract, then run the
package on them.

1. Fetch the works, from the API with
   `select=id,title,abstract_inverted_index` (cursor paging, `per_page=100`,
   a free API key recommended), or from the OpenAlex snapshot.
2. Rebuild each abstract from its inverted index.
3. Build the text as `title + ". " + abstract` and run `detect` and
   `translate.flag` on it.

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

## Also in the package

`src/sdg_tech_tagger/protocol_v1/`: the frozen prompts of the four LLM
passes of the thesis (SDG and technology, passes 1 and 2), as files with
their checksums.

## Credits and licences

The queries are the work of others; please cite them along with this
package. `CREDITS.md` lists every source with its version, DOI and licence,
and `CITATION.cff` gives them in machine-readable form.

- Code: GNU GPL version 3 only (GPL-3.0-only, `LICENSE`), as text2sdg and
  corpustools.
- Data files: CC BY 4.0, except what derives from SIRIS (CC BY-SA 4.0) and
  text2sdg's own query tables (GPL-3.0-only). Details in `LICENSE-DATA.md`.
- Auckland's queries are used with citation, adapted to another syntax and
  not changed in what they search; their source states no licence, and the
  licences above cannot grant rights in the University of Auckland's own
  work.
- Rust crates compiled into the extension: `THIRD_PARTY_LICENSES.md`.

## How AI was used

TODO (Kevin): how AI was used in building this package.
