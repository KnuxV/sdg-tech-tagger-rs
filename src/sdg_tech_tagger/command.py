"""The command ``sdg-tech-tagger``: a parquet file of documents in, one of firings out.

The contract is ``docs/contract.md``, "The command". The file is read and
matched in batches, and the output is exactly what ``detect`` returns on the
whole file with the same arguments. Every check of the input is made before
the output is written; the output is written to a temporary file next to it
and renamed only when the run ends, so a run that stops leaves an existing
output as it was.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import polars as pl

from sdg_tech_tagger.port import (
    MODES,
    SYSTEMS,
    check_arguments,
    check_column,
    check_identifiers,
    check_texts,
    detect,
    empty_output,
)


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    """Consume the command line and produce its arguments."""
    parser = argparse.ArgumentParser(
        prog="sdg-tech-tagger",
        description="Run the port of text2sdg over a parquet file of documents.",
    )
    parser.add_argument("--documents", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    parser.add_argument("--mode", default="corrected", help=f"one of {MODES}")
    parser.add_argument("--id-column", default="UT")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--batch-size", type=int, default=20_000)
    parser.add_argument("--threads", type=int, default=None)
    return parser.parse_args(argv)


def run(arguments: argparse.Namespace) -> None:
    """Consume the arguments, check the whole input, match it in batches and
    write the output. Raise ``ValueError`` or ``TypeError`` on an input that
    does not fit, before anything is written."""
    systems = [s for s in arguments.systems.split(",") if s != ""]
    check_arguments(systems, arguments.mode, arguments.threads)
    if arguments.batch_size < 1:
        raise ValueError(f"--batch-size must be positive, not {arguments.batch_size}")
    id_column, text_column = arguments.id_column, arguments.text_column

    source = pl.scan_parquet(arguments.documents)
    schema = source.collect_schema()
    frame = pl.DataFrame(schema={name: dtype for name, dtype in schema.items()})
    check_column(frame, id_column)
    check_column(frame, text_column)
    identifiers = source.select(id_column).collect()[id_column]
    check_identifiers(identifiers)

    parts = []
    for start in range(0, identifiers.len(), arguments.batch_size):
        batch = (
            source.select(id_column, text_column)
            .slice(start, arguments.batch_size)
            .collect()
        )
        check_texts(batch[text_column], batch[id_column])
        parts.append(
            detect(
                batch,
                systems=systems,
                mode=arguments.mode,
                id_column=id_column,
                text_column=text_column,
                threads=arguments.threads,
            )
        )
    out = (
        pl.concat(parts).sort([id_column, "system", "sdg", "query_id"])
        if parts
        else empty_output(id_column)
    )

    target = arguments.out
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        out.write_parquet(temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    """The entry point: run, and on an input that does not fit print the
    problem on standard error and return a status other than 0."""
    arguments = parse_arguments(argv)
    try:
        run(arguments)
    except (ValueError, TypeError, OSError, pl.exceptions.PolarsError) as error:
        print(f"sdg-tech-tagger: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
