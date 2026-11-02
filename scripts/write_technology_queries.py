"""Write docs/technology-queries.md from the shipped technology query files.

Consumes the two compiled query sets of the package,
``src/sdg_tech_tagger/adt/simplified/patterns.json`` and
``src/sdg_tech_tagger/adt/extended/patterns.json``, and the sources of the
extended terms, ``src/sdg_tech_tagger/adt/extended/provenance.tsv``.
Produces ``docs/technology-queries.md``: every term of both versions, group
by group, with the source of each extended term. The document is generated,
never edited by hand; run this script again after any change to the files.

Raises ``ValueError`` if the terms of ``provenance.tsv`` marked ``in`` are not
exactly the terms of the extended query, or if a term count stored in a
pattern file disagrees with its list of terms.

Usage, from the root of the repository:
    python scripts/write_technology_queries.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADT = ROOT / "src" / "sdg_tech_tagger" / "adt"
OUT = ROOT / "docs" / "technology-queries.md"

# Display name and a plain description of each group, in the order of the
# extended query. The descriptions paraphrase the definitions the package's
# LLM prompts give for the six technologies.
GROUPS = {
    "AI": (
        "Artificial intelligence and big data analytics",
        (
            "Systems that infer from their input how to produce outputs such as "
            "predictions, content, recommendations or decisions: machine learning and "
            "deep learning of every kind, and logic- and knowledge-based approaches "
            "such as expert systems. Big data analytics and data mining are counted "
            "here when they are the method of analysis."
        ),
    ),
    "IOT": (
        "Internet of Things",
        (
            "Physical devices and objects that sense or act and are connected to a "
            "network, with the services that collect, exchange and process their data."
        ),
    ),
    "CI": (
        "Computing infrastructure",
        (
            "Shared or specialised computing and network resources: cloud, edge and "
            "fog computing, data centres, high-performance and quantum computing, "
            "accelerator hardware, big data platforms, and mobile networks such as 5G. "
            "Ordinary computers and generic software are not meant."
        ),
    ),
    "BL": (
        "Blockchain",
        (
            "A ledger shared across a network of computers, in which records are "
            "grouped into blocks linked by cryptographic hashes and validated by a "
            "consensus mechanism, and the applications built on it, cryptocurrencies "
            "included."
        ),
    ),
    "ROB": (
        "Robotics",
        (
            "Programmed physical machines that sense and act on their environment with "
            "a degree of autonomy, to move, manipulate or position: industrial, "
            "service, medical and mobile robots, drones and other unmanned or "
            "self-driving vehicles."
        ),
    ),
    "AM": (
        "Additive manufacturing",
        (
            "Computer-controlled production that creates three-dimensional objects by "
            "joining materials layer by layer, 3D printing included."
        ),
    ),
    "UMBRELLA": (
        "Umbrella terms",
        (
            "General terms for digital technologies as a whole or for their "
            "combination, such as digital transformation, Industry 4.0 or smart "
            "cities, that name no single group. Extended query only."
        ),
    ),
}

INTRO = """\
# The technology queries

This document is written by `scripts/write_technology_queries.py` from the
files the package ships. Do not edit it by hand.

The technology queries tag a text with advanced digital technologies. A
query is a list of terms per group; a text is tagged with a group when one of
the group's terms occurs in it. They are keyword queries, not a trained
model. Two versions ship:

- **Simplified** (`src/sdg_tech_tagger/adt/simplified/`): {s_terms} terms in
  six groups. Terms are matched as they are written.
- **Extended** (`src/sdg_tech_tagger/adt/extended/`): {e_terms} terms in seven
  groups, the six of the simplified query and a group of umbrella terms. It
  has more terms per group, for a higher recall at some cost of precision.
  It also accepts the regular plural of a term, the closed spelling of a
  term written with a hyphen, and reads a decimal number as one word. The
  source of each of its terms is given below; the keys resolve in
  [`CREDITS.md`](../CREDITS.md).

{both} terms are in both versions, written the same way.

## How a term is matched

The text and the terms are put in the same form: lower case, and every run
of characters that are not letters or digits becomes one space. A term then
matches a run of whole words of the text.

- A term of several words matches those words in that order, side by side:
  `computer vision` matches "Computer-Vision" and "computer vision", not
  "vision of the computer".
- `*` at the end of a word stands for any ending of that word, the empty
  one included: `robot*` matches "robot", "robots" and "robotics". It never
  reaches into the next word.
- In the extended query only:
  - a term also matches its regular plural (`s`, `es`, or `ies` for a `y`
    after a consonant), except `ai`; a term ending in `*` or in a digit
    takes no plural;
  - a term written with a hyphen also matches its closed spelling:
    `back-propagation` matches "backpropagation";
  - a dot or comma between two digits keeps the number whole: `5g` does not
    match "0.5g", and `industry 4.0` does not match "industry 4 0".

In Python, `sdg_tech_tagger.adt.translate.flag` applies a version to a table
of texts; see `README.md`.

## The Web of Science files

- `adt/simplified/*.txt`: the simplified query in Web of Science syntax, one
  file per group. These are the queries as run on the Web of Science.
- `adt/extended/*.txt`: the terms of the extended query in Web of Science
  syntax, without the plural, hyphen and decimal rules, so they do not give
  the extended query when run as they are.
- `adt/extended_wos/`: the extended query with every plural and closed
  spelling written out as a term of its own, one file per group and
  `ALL.txt` for all groups. The decimal rule cannot be written in Web of
  Science syntax, and the `TS` field also reads keywords; its `README.md`
  says where the files and the package differ.

## Terms per group

| group | simplified | extended | in both |
|---|---:|---:|---:|
"""

SOURCE_TYPES = {
    "own, added for recall": "own, added for recall",
    "own, original WoS query": "own, from the simplified query",
}


def _load(path: Path) -> dict[str, list[str]]:
    """Return the terms of each group of a compiled query set, checked against its counts."""
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = {}
    for definition in data["definitions"]:
        terms = list(definition["terms"])
        if definition["term_count"] != len(terms):
            raise ValueError(f"{path}: term_count of {definition['code']} disagrees")
        groups[definition["code"]] = terms
    return groups


def _provenance(path: Path) -> dict[tuple[str, str], str]:
    """Return, for each (group, term) of the extended query, its sources as shown."""
    out = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["decision"] != "in":
                continue
            keys = row["sources"].strip()
            kind = row["source_type"].strip()
            if kind in SOURCE_TYPES and keys in ("", "OWN"):
                shown = SOURCE_TYPES[kind]
            elif kind in SOURCE_TYPES:
                shown = f"{keys} ({SOURCE_TYPES[kind]})"
            else:
                shown = keys or kind
            out[(row["group"], row["term"])] = shown
    return out


def render() -> str:
    """Return the text of docs/technology-queries.md."""
    simplified = _load(ADT / "simplified" / "patterns.json")
    extended = _load(ADT / "extended" / "patterns.json")
    sources = _provenance(ADT / "extended" / "provenance.tsv")
    pairs = {(g, t) for g, terms in extended.items() for t in terms}
    if pairs != set(sources):
        raise ValueError(
            "provenance.tsv and the extended patterns hold different terms"
        )

    s_all = {t for terms in simplified.values() for t in terms}
    e_all = {t for terms in extended.values() for t in terms}
    s_count = sum(len(t) for t in simplified.values())
    e_count = sum(len(t) for t in extended.values())
    text = INTRO.format(s_terms=s_count, e_terms=e_count, both=len(s_all & e_all))

    both_total = 0
    for code in GROUPS:
        s_terms, e_terms = simplified.get(code, []), extended.get(code, [])
        both = len(set(s_terms) & set(e_terms))
        both_total += both
        text += f"| {code}, {GROUPS[code][0]} | {len(s_terms)} | {len(e_terms)} | {both} |\n"
    text += f"| all groups | {s_count} | {e_count} | {both_total} |\n"
    text += (
        '\n"In both" counts the terms a group has in both versions. A term can '
        "sit in two groups: in the simplified query `data center*` and "
        "`data centre*` are in AI and CI, and in the extended query `tinyml` is in "
        "two groups. The last row counts terms per group, so a term in two groups "
        "counts twice there; the count of distinct terms is "
        f"{len(s_all)} simplified and {len(e_all)} extended, {len(s_all & e_all)} "
        "of them in both, whatever their group.\n"
    )

    for code, (name, description) in GROUPS.items():
        s_terms, e_terms = simplified.get(code, []), extended.get(code, [])
        text += f"\n## {code}: {name}\n\n{description}\n"
        if s_terms:
            text += f"\n### Simplified, {len(s_terms)} terms\n\n"
            text += "Terms not in the extended query are marked with a dagger (†).\n\n"
            shown = [f"`{t}`" + ("" if t in e_all else " †") for t in sorted(s_terms)]
            text += ", ".join(shown) + "\n"
        text += f"\n### Extended, {len(e_terms)} terms\n\n"
        text += "| term | source | also in simplified |\n|---|---|---|\n"
        for term in sorted(e_terms):
            mark = "yes" if term in s_all else ""
            text += f"| `{term}` | {sources[(code, term)]} | {mark} |\n"
    return text


def main() -> None:
    """Write the document and print its term counts."""
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
