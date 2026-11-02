"""The function ``detect``: a table of documents in, a table of firings out.

The contract is ``docs/contract.md``, "The function". Python checks the
input and builds the output table; the Rust extension (``_native``) does
the cutting, the indexing and the matching.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from functools import cache
from pathlib import Path

import polars as pl

from sdg_tech_tagger import _native

SYSTEMS = ("Aurora", "Elsevier", "SIRIS", "Auckland")
MODES = ("compatible", "corrected")
OUTPUT_TYPES = {
    "system": pl.String,
    "sdg": pl.String,
    "query_id": pl.Int32,
    "features": pl.String,
}
# The documents given to the extension at once. Each batch is indexed on its
# own; the firings of a document do not depend on the batch it is in.
BATCH_SIZE = 20_000

TABLES = Path(__file__).resolve().parent / "query_tables"
TABLE_FILES = (
    "elsevier_queries.parquet",
    "siris_queries.parquet",
    "auckland_queries.parquet",
    "aurora_queries.parquet",
    "aurora_simple.parquet",
    "aurora_and.parquet",
    "aurora_w.parquet",
)


def check_tables(directory: Path = TABLES) -> None:
    """Consume the directory of the shipped query tables and raise
    ``RuntimeError`` unless each file has the checksum its ``SHA256SUMS``
    lists. The files and ``SHA256SUMS`` are copies of ``queries/``.
    """
    sums = {}
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        sums[name] = digest
    for name in TABLE_FILES:
        digest = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        if sums.get(name) != digest:
            raise RuntimeError(f"the query table {name} is not the one of queries/")


@cache
def native_port() -> _native.Port:
    """Produce the extension's port, built once per process from the query
    tables shipped with the package, after checking them."""
    check_tables()

    def read(name: str) -> pl.DataFrame:
        return pl.read_parquet(TABLES / name)

    def query_rows(name: str) -> list[tuple[str, int, str]]:
        table = read(name)
        return list(zip(table["sdg"], table["query_id"], table["query"], strict=True))

    def internal_rows(name: str) -> list[tuple[str, str, str | None]]:
        table = read(name)
        second = table["correct 2"] if "correct 2" in table.columns else None
        return [
            (orig, correct, None if second is None else second[i])
            for i, (orig, correct) in enumerate(
                zip(table["orig"], table["correct"], strict=True)
            )
        ]

    return _native.Port(
        query_rows("elsevier_queries.parquet"),
        query_rows("siris_queries.parquet"),
        query_rows("auckland_queries.parquet"),
        query_rows("aurora_queries.parquet"),
        internal_rows("aurora_simple.parquet"),
        internal_rows("aurora_and.parquet"),
        internal_rows("aurora_w.parquet"),
    )


def check_arguments(
    systems: Sequence[str], mode: str, threads: int | None
) -> tuple[list[str], int]:
    """Consume the arguments of ``detect`` other than the table and produce
    the systems as a list and the number of threads; raise ``ValueError``
    where one does not fit (``docs/contract.md``)."""
    try:
        names = list(systems)
    except TypeError:
        raise ValueError(
            f"systems must be a sequence of names out of {SYSTEMS}"
        ) from None
    if not names:
        raise ValueError("systems is empty: name at least one system")
    for name in names:
        if name not in SYSTEMS:
            raise ValueError(f"unknown system {name!r}: the systems are {SYSTEMS}")
    if len(set(names)) != len(names):
        raise ValueError(f"a system is named twice in {names}")
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    if threads is None:
        count = os.cpu_count() or 1
    elif isinstance(threads, int) and not isinstance(threads, bool) and threads > 0:
        count = threads
    else:
        raise ValueError(f"threads must be None or a positive integer, not {threads!r}")
    return names, count


def check_column(documents: pl.DataFrame, column: str) -> None:
    """Raise ``ValueError`` if the column is missing, ``TypeError`` if it is
    not of type ``String``."""
    if column not in documents.columns:
        raise ValueError(f"the column {column!r} is not in the table")
    dtype = documents.schema[column]
    if dtype != pl.String:
        raise TypeError(f"the column {column!r} is of type {dtype}, not String")


def check_identifiers(identifiers: pl.Series) -> None:
    """Raise ``ValueError`` if an identifier is missing or appears twice."""
    missing = identifiers.null_count()
    if missing:
        raise ValueError(
            f"{missing} documents have no identifier in the column {identifiers.name!r}"
        )
    duplicated = identifiers.filter(identifiers.is_duplicated()).unique().sort()
    if duplicated.len():
        raise ValueError(
            f"{duplicated.len()} identifiers appear more than once in the column "
            f"{identifiers.name!r}, first: {duplicated[0]!r}"
        )


def check_texts(texts: pl.Series, identifiers: pl.Series) -> None:
    """Raise ``ValueError`` if a text is missing, naming the first document."""
    missing = texts.is_null()
    count = int(missing.sum())
    if count:
        first = identifiers.filter(missing)[0]
        raise ValueError(
            f"{count} documents have no text in the column {texts.name!r}, "
            f"first: {first!r}"
        )


def empty_output(id_column: str) -> pl.DataFrame:
    """The output table with no row."""
    return pl.DataFrame(schema={id_column: pl.String, **OUTPUT_TYPES})


def detect(
    documents: pl.DataFrame,
    systems: Sequence[str] = SYSTEMS,
    mode: str = "corrected",
    id_column: str = "UT",
    text_column: str = "text",
    threads: int | None = None,
) -> pl.DataFrame:
    """Say which queries of which systems fire on each document.

    Consumes a ``polars.DataFrame`` with an identifier column and a text
    column, both ``String`` (other columns are ignored), the systems to run
    (out of Aurora, Elsevier, SIRIS and Auckland), the mode (``"corrected"``,
    the default, or ``"compatible"``) and the number of threads (``None``:
    every core). Produces one row per firing, with the columns
    (identifier named as ``id_column``, ``system``, ``sdg``, ``query_id``
    ``Int32``, ``features``), sorted by those four, the strings in byte
    order. The texts are matched as given. The output does not depend on
    ``threads`` or on the order of the input rows.

    Raises ``TypeError`` when ``documents`` is not a ``polars.DataFrame`` or
    a named column is not ``String``, and ``ValueError`` for a missing
    column, a missing or repeated identifier, a missing text, or an argument
    that does not fit; nothing is matched then (``docs/contract.md``).
    """
    if not isinstance(documents, pl.DataFrame):
        raise TypeError(
            f"documents must be a polars.DataFrame, not {type(documents).__name__}"
        )
    names, count = check_arguments(systems, mode, threads)
    check_column(documents, id_column)
    check_column(documents, text_column)
    identifiers = documents[id_column]
    texts = documents[text_column]
    check_identifiers(identifiers)
    check_texts(texts, identifiers)

    port = native_port()
    parts = []
    for start in range(0, documents.height, BATCH_SIZE):
        batch = texts.slice(start, BATCH_SIZE).to_list()
        rows, system, sdg, query_id, features = port.detect(batch, names, mode, count)
        if not rows:
            continue
        index = pl.Series("row", rows, dtype=pl.UInt32) + start
        parts.append(
            pl.DataFrame(
                {
                    id_column: identifiers.gather(index),
                    "system": pl.Series(system, dtype=pl.String),
                    "sdg": pl.Series(sdg, dtype=pl.String),
                    "query_id": pl.Series(query_id, dtype=pl.Int32),
                    "features": pl.Series(features, dtype=pl.String),
                }
            )
        )
    if not parts:
        return empty_output(id_column)
    out = pl.concat(parts)
    return out.sort([id_column, "system", "sdg", "query_id"])
