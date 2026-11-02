"""The command ``sdg-tech-tagger``: a parquet file in, the rows of ``detect`` out.

Contract: ``docs/contract.md``, "The command". Its output is compared with
``detect`` on the whole table with the same arguments, whole frames,
``features`` included: the command adds nothing to what ``detect`` returns,
whatever the batch size.
"""

import subprocess
import sys
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from sdg_tech_tagger import detect
from tests.unit.oracle_fixtures import COLUMNS, DTYPES, load_set

# pip installs the command beside the interpreter, with `.exe` on Windows.
COMMAND = Path(sys.executable).parent / (
    "sdg-tech-tagger.exe" if sys.platform == "win32" else "sdg-tech-tagger"
)


def run(*arguments: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run the command with ``arguments`` and return what it did."""
    assert COMMAND.exists(), f"the command is not installed at {COMMAND}"
    return subprocess.run(
        [str(COMMAND), *arguments],
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=600,
        check=False,
    )


def write(frame: pl.DataFrame, path: Path) -> Path:
    """Write ``frame`` to ``path`` as parquet and return the path."""
    frame.write_parquet(path)
    return path


def documents() -> pl.DataFrame:
    """The hand-written sentences."""
    return load_set("hand").sentences


def succeeded(result: subprocess.CompletedProcess) -> None:
    """Fail with the command's standard error unless it exited with 0."""
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("batch_size", ["7", "50", "1000"])
def test_batches_give_what_detect_gives(tmp_path, batch_size):
    """In batches of any size, the output is ``detect`` on the whole table."""
    source = write(documents(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    succeeded(
        run(
            "--documents",
            str(source),
            "--out",
            str(out),
            "--batch-size",
            batch_size,
            cwd=tmp_path,
        )
    )
    assert_frame_equal(pl.read_parquet(out), detect(documents()))


def test_arguments_are_those_of_detect(tmp_path):
    """Mode, systems and threads mean what they mean for ``detect``."""
    source = write(documents(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    result = run(
        "--documents",
        str(source),
        "--out",
        str(out),
        "--mode",
        "compatible",
        "--systems",
        "SIRIS,Aurora",
        "--batch-size",
        "11",
        "--threads",
        "1",
        cwd=tmp_path,
    )
    succeeded(result)
    expected = detect(documents(), systems=("SIRIS", "Aurora"), mode="compatible")
    assert_frame_equal(pl.read_parquet(out), expected)


def test_named_columns(tmp_path):
    """``--id-column`` and ``--text-column`` name the columns; extra columns are ignored."""
    table = (
        documents()
        .rename({"UT": "doc", "text": "body"})
        .with_columns(year=pl.lit(2024))
    )
    source = write(table, tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    result = run(
        "--documents",
        str(source),
        "--out",
        str(out),
        "--id-column",
        "doc",
        "--text-column",
        "body",
        "--batch-size",
        "13",
        cwd=tmp_path,
    )
    succeeded(result)
    got = pl.read_parquet(out)
    assert got.columns[0] == "doc"
    assert_frame_equal(got, detect(table, id_column="doc", text_column="body"))


def test_defaults(tmp_path):
    """Without the optional arguments: four systems, corrected mode, ``UT`` and ``text``."""
    source = write(documents(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    succeeded(run("--documents", str(source), "--out", str(out), cwd=tmp_path))
    got = pl.read_parquet(out)
    expected = detect(
        documents(),
        systems=("Aurora", "Elsevier", "SIRIS", "Auckland"),
        mode="corrected",
    )
    assert_frame_equal(got, expected)


def test_empty_file(tmp_path):
    """No document: an output with the five columns, their types, and no row."""
    empty = pl.DataFrame(schema={"UT": pl.String, "text": pl.String})
    source = write(empty, tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    succeeded(run("--documents", str(source), "--out", str(out), cwd=tmp_path))
    got = pl.read_parquet(out)
    assert got.columns == COLUMNS
    assert got.dtypes == DTYPES
    assert got.height == 0


def test_an_existing_output_is_replaced(tmp_path):
    """An output file that exists is overwritten by a run that ends."""
    source = write(documents(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    out.write_bytes(b"left by an earlier run")
    succeeded(
        run(
            "--documents",
            str(source),
            "--out",
            str(out),
            "--batch-size",
            "40",
            cwd=tmp_path,
        )
    )
    assert_frame_equal(pl.read_parquet(out), detect(documents()))


def duplicated_identifier() -> pl.DataFrame:
    """The hand-written sentences, the last one carrying the first one's identifier."""
    table = documents()
    first = table["UT"][0]
    return table.with_columns(
        UT=pl.when(pl.int_range(table.height) == table.height - 1)
        .then(pl.lit(first))
        .otherwise(pl.col("UT"))
    )


def missing_text_at_the_end() -> pl.DataFrame:
    """The hand-written sentences, the last one without a text."""
    table = documents()
    return table.with_columns(
        text=pl.when(pl.int_range(table.height) == table.height - 1)
        .then(None)
        .otherwise(pl.col("text"))
    )


@pytest.mark.parametrize(
    "make",
    [duplicated_identifier, missing_text_at_the_end],
    ids=["identifier twice", "null text"],
)
def test_input_that_does_not_fit_writes_nothing(tmp_path, make):
    """A status other than 0, a message on standard error, and no output file."""
    source = write(make(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    result = run(
        "--documents", str(source), "--out", str(out), "--batch-size", "2", cwd=tmp_path
    )
    assert result.returncode != 0
    assert result.stderr.strip()
    assert not out.exists()


def test_input_that_does_not_fit_leaves_an_existing_output_alone(tmp_path):
    """An output file that exists is overwritten only when a run ends."""
    source = write(duplicated_identifier(), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    out.write_bytes(b"left by an earlier run")
    result = run(
        "--documents", str(source), "--out", str(out), "--batch-size", "2", cwd=tmp_path
    )
    assert result.returncode != 0
    assert result.stderr.strip()
    assert out.read_bytes() == b"left by an earlier run"


def test_missing_column_is_reported(tmp_path):
    """A column that is not there: a status other than 0, a message, no output."""
    source = write(documents().rename({"text": "abstract"}), tmp_path / "in.parquet")
    out = tmp_path / "out.parquet"
    result = run("--documents", str(source), "--out", str(out), cwd=tmp_path)
    assert result.returncode != 0
    assert "text" in result.stderr
    assert not out.exists()
