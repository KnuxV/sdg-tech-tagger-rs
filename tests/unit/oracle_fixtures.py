"""The fixture sets of tests/fixtures/, loaded once, and how a difference is shown.

A fixture set is a table of sentences (``UT``, ``text``) and, per mode, the
rows the oracle of that mode returned for them (``UT``, ``system``, ``sdg``,
``query_id``, ``features``), written by ``tests/fixtures/make_fixtures.py``.
The tests compare the port with them on the key (``UT``, ``system``,
``sdg``, ``query_id``); ``features`` is stored and not asserted (D028).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import polars as pl
import pytest

from sdg_tech_tagger import detect

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SET_NAMES = ("hand", "generated")
MODES = ("compatible", "corrected")
SYSTEMS = ("Aurora", "Elsevier", "SIRIS", "Auckland")
KEY = ["UT", "system", "sdg", "query_id"]
COLUMNS = ["UT", "system", "sdg", "query_id", "features"]
DTYPES = [pl.String, pl.String, pl.String, pl.Int32, pl.String]


@dataclass(frozen=True)
class FixtureSet:
    """One set: its sentences and, by mode, the oracle's rows."""

    name: str
    sentences: pl.DataFrame
    rows: dict[str, pl.DataFrame]

    def texts(self) -> dict[str, str]:
        """Map each identifier to its text."""
        return dict(zip(self.sentences["UT"], self.sentences["text"], strict=True))


@cache
def load_set(name: str) -> FixtureSet:
    """Read the sentences and both modes' rows of the set ``name``."""
    sentences = pl.read_parquet(FIXTURES / f"{name}_sentences.parquet")
    rows = {
        mode: pl.read_parquet(FIXTURES / f"{name}_{mode}.parquet") for mode in MODES
    }
    return FixtureSet(name, sentences, rows)


@cache
def run_detect(name: str, mode: str, systems: tuple[str, ...]) -> pl.DataFrame:
    """``detect`` on the sentences of the set ``name``, computed once per arguments."""
    return detect(load_set(name).sentences, systems=systems, mode=mode)


def keys(frame: pl.DataFrame, id_column: str = "UT") -> set[tuple]:
    """The set of (identifier, system, sdg, query_id) of a table of firings."""
    return set(frame.select(id_column, "system", "sdg", "query_id").iter_rows())


def describe_difference(
    got: set[tuple], expected: set[tuple], texts: dict[str, str], limit: int = 8
) -> str:
    """A short report of the firings in one set of keys and not the other.

    Counts first, then the queries most often concerned, then the first
    ``limit`` missing and extra firings with the start of their sentence.
    """
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    counts = f"{len(missing)} missing, {len(extra)} extra"
    lines = [f"expected {len(expected)} firings, got {len(got)}: {counts}"]
    for label, items in (("missing", missing), ("extra", extra)):
        if not items:
            continue
        queries = Counter(key[1:] for key in items).most_common(5)
        summary = ", ".join(f"{s} {g} {q} ({n})" for (s, g, q), n in queries)
        lines.append(f"{label}, by query: {summary}")
        for key in items[:limit]:
            text = texts.get(key[0], "<identifier not in the input>")
            short = text if len(text) <= 100 else text[:97] + "..."
            lines.append(f"  {label} {key}: {short!r}")
    return "\n".join(lines)


def assert_same_firings(
    got: pl.DataFrame,
    expected: pl.DataFrame,
    texts: dict[str, str],
    id_column: str = "UT",
) -> None:
    """Fail unless ``got`` has exactly the key rows of ``expected``, each once."""
    got_keys = keys(got, id_column)
    duplicated = got.height - len(got_keys)
    if duplicated:
        pytest.fail(f"{duplicated} firings are returned more than once", pytrace=False)
    expected_keys = keys(expected)
    if got_keys != expected_keys:
        pytest.fail(describe_difference(got_keys, expected_keys, texts), pytrace=False)
