"""The function ``detect``: its input, its output and the input that does not fit.

Contract: ``docs/contract.md``, "The function". Where a test needs the rows
a text gives, they are the oracle's rows stored in the fixture sets of
``tests/fixtures/``, never rows reasoned out here.
"""

import random

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from sdg_tech_tagger import detect
from tests.unit.oracle_fixtures import (
    COLUMNS,
    DTYPES,
    KEY,
    SYSTEMS,
    assert_same_firings,
    keys,
    load_set,
    run_detect,
)

EMPTY = pl.DataFrame(schema={"UT": pl.String, "text": pl.String})


def hand():
    """The hand-written set."""
    return load_set("hand")


def some_documents(count: int = 3000) -> pl.DataFrame:
    """The hand-written sentences and a fixed sample of the generated ones."""
    generated = load_set("generated").sentences
    sample = generated.sample(count, seed=20261003, shuffle=False)
    return pl.concat([hand().sentences, sample])


def with_identifiers(
    source_ut: str, identifiers: list[str]
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Documents that all hold the text of ``source_ut``, and their oracle rows.

    The rows are the corrected oracle's rows of ``source_ut``, repeated under
    each new identifier.
    """
    fixture = hand()
    text = fixture.texts()[source_ut]
    documents = pl.DataFrame({"UT": identifiers, "text": [text] * len(identifiers)})
    rows = fixture.rows["corrected"].filter(pl.col("UT") == source_ut)
    expected = pl.concat(
        [rows.with_columns(UT=pl.lit(identifier)) for identifier in identifiers]
    )
    return documents, expected


def silent_identifiers() -> list[str]:
    """Hand-written sentences on which neither oracle returned a row."""
    fixture = hand()
    fired = set(fixture.rows["compatible"]["UT"]) | set(fixture.rows["corrected"]["UT"])
    silent = [ut for ut in fixture.sentences["UT"] if ut not in fired]
    assert silent, "the hand-written set has no sentence on which nothing fires"
    return silent


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def test_output_columns_types_and_order():
    """Five columns, in order, with the types of the contract."""
    got = run_detect("hand", "corrected", SYSTEMS)
    assert got.columns == COLUMNS
    assert got.dtypes == DTYPES
    assert got.height > 0


def test_rows_are_sorted_by_the_key():
    """Rows are sorted by identifier, system, sdg and query_id."""
    got = run_detect("hand", "corrected", SYSTEMS)
    assert_frame_equal(got.select(KEY), got.select(KEY).sort(KEY))
    assert_frame_equal(got.select(KEY), hand().rows["corrected"].select(KEY))


def test_query_id_is_sorted_as_a_number():
    """Within a document, system and goal, query 2 comes before query 13."""
    fixture = load_set("generated")
    expected = fixture.rows["corrected"]
    groups = expected.group_by("UT", "system", "sdg").agg(
        as_number=pl.col("query_id").sort().cast(pl.String),
        as_text=pl.col("query_id").cast(pl.String).sort(),
    )
    differ = groups.filter(pl.col("as_number") != pl.col("as_text"))
    chosen = differ["UT"].unique().sort().head(20).to_list()
    assert chosen, "no document of the generated set tells the two orders apart"
    documents = fixture.sentences.filter(pl.col("UT").is_in(chosen))
    got = detect(documents)
    assert_frame_equal(
        got.select(KEY), expected.filter(pl.col("UT").is_in(chosen)).select(KEY)
    )


def test_identifiers_are_sorted_in_byte_order():
    """``B`` < ``Z`` < ``_`` < ``a`` < ``ä`` < ``é``, and ``10`` < ``9``."""
    identifiers = ["é", "a", "9", "Z", "ä", "_", "B", "10", "b b", "b"]
    documents, expected = with_identifiers("H-seq-03", identifiers)
    got = detect(documents)
    assert_frame_equal(got.select(KEY), expected.sort(KEY).select(KEY))
    assert got["UT"].unique(maintain_order=True).to_list() == sorted(identifiers)
    assert sorted(identifiers) == sorted(identifiers, key=lambda ut: ut.encode())


def test_systems_are_sorted_auckland_aurora_elsevier_siris():
    """``Auckland`` < ``Aurora`` < ``Elsevier`` < ``SIRIS`` within a document."""
    got = run_detect("hand", "corrected", SYSTEMS)
    order = ["Auckland", "Aurora", "Elsevier", "SIRIS"]
    for _, group in got.group_by("UT", maintain_order=True):
        systems = group["system"].unique(maintain_order=True).to_list()
        assert systems == [s for s in order if s in systems]


def test_empty_table_gives_no_row():
    """No document: the five columns, their types, no row."""
    got = detect(EMPTY)
    assert got.columns == COLUMNS
    assert got.dtypes == DTYPES
    assert got.height == 0


def test_nothing_fires_gives_no_row():
    """Texts on which the oracles return nothing give the five columns and no row."""
    fixture = hand()
    documents = fixture.sentences.filter(pl.col("UT").is_in(silent_identifiers()))
    for mode in ("compatible", "corrected"):
        got = detect(documents, mode=mode)
        assert got.columns == COLUMNS
        assert got.dtypes == DTYPES
        assert got.height == 0, got


@pytest.mark.parametrize("text", ["", " ", "   ", "\t", "\n", " \t\r\n  \n"])
def test_empty_or_blank_text_gives_no_row(text):
    """An empty text or one of whitespace only is valid and has no row."""
    fixture = hand()
    documents = pl.DataFrame(
        {"UT": ["blank", "H-seq-03"], "text": [text, fixture.texts()["H-seq-03"]]}
    )
    for mode in ("compatible", "corrected"):
        got = detect(documents, mode=mode)
        assert "blank" not in got["UT"].to_list()
        expected = fixture.rows[mode].filter(pl.col("UT") == "H-seq-03")
        assert_same_firings(got, expected, fixture.texts())


def test_only_blank_texts_give_no_row():
    """A table of blank texts only gives the five columns and no row."""
    documents = pl.DataFrame({"UT": ["a", "b", "c"], "text": ["", "  ", "\n"]})
    got = detect(documents)
    assert got.columns == COLUMNS
    assert got.dtypes == DTYPES
    assert got.height == 0


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


def test_identifier_column_keeps_its_name():
    """With other column names, the output's first column has the input's name."""
    fixture = hand()
    documents = fixture.sentences.rename({"UT": "doc_id", "text": "abstract"})
    got = detect(documents, id_column="doc_id", text_column="abstract")
    assert got.columns == ["doc_id", *COLUMNS[1:]]
    assert got.dtypes == DTYPES
    assert_same_firings(
        got, fixture.rows["corrected"], fixture.texts(), id_column="doc_id"
    )


def test_the_named_columns_are_used_and_the_default_names_ignored():
    """Columns called ``UT`` and ``text`` are ignored when others are named."""
    fixture = hand()
    documents = fixture.sentences.rename({"UT": "doc", "text": "body"}).with_columns(
        UT=pl.lit("decoy"), text=pl.lit("Extreme poverty persists.")
    )
    got = detect(documents, id_column="doc", text_column="body")
    assert got.columns[0] == "doc"
    assert_same_firings(
        got, fixture.rows["corrected"], fixture.texts(), id_column="doc"
    )


def test_other_columns_are_ignored():
    """Extra columns, of any type, nulls included, change nothing."""
    fixture = hand()
    plain = run_detect("hand", "corrected", SYSTEMS)
    count = fixture.sentences.height
    documents = fixture.sentences.with_columns(
        year=pl.int_range(count, dtype=pl.Int64),
        note=pl.when(pl.int_range(count) % 2 == 0).then(pl.lit("x")).otherwise(None),
        system=pl.lit("not a system"),
        features=pl.lit(1.5),
    ).select("note", "UT", "year", "system", "text", "features")
    assert_frame_equal(detect(documents), plain)


def test_systems_in_any_order_and_as_a_list():
    """The order of the names and the kind of sequence change nothing."""
    first = detect(hand().sentences, systems=("SIRIS", "Aurora"))
    second = detect(hand().sentences, systems=["Aurora", "SIRIS"])
    assert_frame_equal(first, second)
    expected = (
        hand().rows["corrected"].filter(pl.col("system").is_in(["Aurora", "SIRIS"]))
    )
    assert_same_firings(first, expected, hand().texts())


def test_default_mode_is_corrected():
    """Without ``mode``, the rows are those of the corrected mode."""
    fixture = hand()
    assert keys(fixture.rows["corrected"]) != keys(fixture.rows["compatible"])
    got = detect(fixture.sentences)
    assert_frame_equal(got, run_detect("hand", "corrected", SYSTEMS))
    assert_same_firings(got, fixture.rows["corrected"], fixture.texts())


def test_default_systems_are_the_four():
    """Without ``systems``, the four systems run."""
    fixture = hand()
    got = detect(fixture.sentences, mode="compatible")
    assert set(got["system"].unique()) == set(SYSTEMS)
    assert_same_firings(got, fixture.rows["compatible"], fixture.texts())


@pytest.mark.parametrize("threads", [1, 2, 7])
def test_threads_change_nothing(threads):
    """The output is the same frame whatever the number of threads (D007)."""
    documents = some_documents()
    assert_frame_equal(
        detect(documents, threads=threads), detect(documents, threads=None)
    )


def test_order_of_input_rows_changes_nothing():
    """Shuffled input rows give the same frame (D007)."""
    documents = some_documents()
    order = list(range(documents.height))
    random.Random(7).shuffle(order)
    shuffled = documents[order]
    assert_frame_equal(detect(shuffled), detect(documents))


def test_text_is_matched_as_given():
    """Leading and trailing whitespace, tabs and new lines are kept as they are."""
    fixture = hand()
    chosen = ["H-ws-01", "H-ws-02", "H-ws-03", "H-ws-04", "H-ws-05", "H-multi-02"]
    documents = fixture.sentences.filter(pl.col("UT").is_in(chosen))
    expected = fixture.rows["corrected"].filter(pl.col("UT").is_in(chosen))
    assert_same_firings(detect(documents), expected, fixture.texts())


# ---------------------------------------------------------------------------
# Input that does not fit
# ---------------------------------------------------------------------------


def base() -> pl.DataFrame:
    """A small valid table."""
    return hand().sentences.head(5)


NOT_A_FRAME = [
    pytest.param(lambda: None, id="None"),
    pytest.param(lambda: {"UT": ["a"], "text": ["b"]}, id="dict"),
    pytest.param(lambda: [("a", "b")], id="list"),
    pytest.param(lambda: base().lazy(), id="LazyFrame"),
    pytest.param(lambda: base()["text"], id="Series"),
]


@pytest.mark.parametrize("make", NOT_A_FRAME)
def test_documents_not_a_data_frame(make):
    """``documents`` that is not a ``polars.DataFrame`` raises ``TypeError``."""
    with pytest.raises(TypeError):
        detect(make())


@pytest.mark.parametrize(
    ("documents", "arguments", "column"),
    [
        pytest.param(lambda: base().drop("UT"), {}, "UT", id="no UT"),
        pytest.param(lambda: base().drop("text"), {}, "text", id="no text"),
        pytest.param(
            lambda: base(), {"id_column": "doc"}, "doc", id="no named identifier"
        ),
        pytest.param(
            lambda: base(), {"text_column": "body"}, "body", id="no named text"
        ),
    ],
)
def test_missing_column(documents, arguments, column):
    """A named column that is missing raises ``ValueError`` naming it."""
    with pytest.raises(ValueError, match=column):
        detect(documents(), **arguments)


@pytest.mark.parametrize(
    ("documents", "column"),
    [
        pytest.param(
            lambda: base().with_columns(UT=pl.int_range(5, dtype=pl.Int64)),
            "UT",
            id="UT Int64",
        ),
        pytest.param(
            lambda: base().with_columns(text=pl.lit(1)), "text", id="text Int32"
        ),
        pytest.param(
            lambda: base().with_columns(pl.col("text").cast(pl.Categorical)),
            "text",
            id="text Categorical",
        ),
        pytest.param(
            lambda: base().with_columns(pl.col("UT").cast(pl.Binary)),
            "UT",
            id="UT Binary",
        ),
        pytest.param(
            lambda: base().with_columns(text=pl.lit(None, dtype=pl.Null)),
            "text",
            id="text Null",
        ),
    ],
)
def test_column_of_another_type(documents, column):
    """A named column that is not of type ``String`` raises ``TypeError`` naming it."""
    with pytest.raises(TypeError, match=column):
        detect(documents())


@pytest.mark.parametrize(
    "documents",
    [
        pytest.param(
            lambda: base().with_columns(
                UT=pl.when(pl.int_range(5) == 3).then(None).otherwise(pl.col("UT"))
            ),
            id="null identifier",
        ),
        pytest.param(
            lambda: base().with_columns(
                UT=pl.when(pl.int_range(5) == 4)
                .then(pl.lit(base()["UT"][0]))
                .otherwise(pl.col("UT"))
            ),
            id="identifier twice",
        ),
        pytest.param(
            lambda: base().with_columns(
                text=pl.when(pl.int_range(5) == 2).then(None).otherwise(pl.col("text"))
            ),
            id="null text",
        ),
    ],
)
def test_missing_or_duplicate_identifier_or_missing_text(documents):
    """A null identifier, an identifier twice, a null text raise ``ValueError``."""
    with pytest.raises(ValueError) as raised:
        detect(documents())
    assert str(raised.value).strip()


@pytest.mark.parametrize(
    "systems",
    [
        pytest.param((), id="empty"),
        pytest.param([], id="empty list"),
        pytest.param(("Aurora", "SDSN"), id="unknown"),
        pytest.param(("aurora",), id="lowercase"),
        pytest.param(("Aurora", "Aurora"), id="twice"),
    ],
)
def test_systems_that_do_not_fit(systems):
    """No system, a name not among the four, or a name twice raise ``ValueError``."""
    with pytest.raises(ValueError):
        detect(base(), systems=systems)


@pytest.mark.parametrize("mode", ["", "Corrected", "COMPATIBLE", "fixed", "strict"])
def test_mode_that_does_not_fit(mode):
    """A mode other than ``compatible`` and ``corrected`` raises ``ValueError``."""
    with pytest.raises(ValueError):
        detect(base(), mode=mode)


@pytest.mark.parametrize("threads", [0, -1, 1.5, "2"])
def test_threads_that_do_not_fit(threads):
    """``threads`` not ``None`` and not a positive integer raises ``ValueError``."""
    with pytest.raises(ValueError):
        detect(base(), threads=threads)


def test_input_that_does_not_fit_is_reported_whatever_the_rest():
    """A bad argument is reported on an otherwise valid, larger table too."""
    with pytest.raises(ValueError):
        detect(some_documents(), mode="faithful")
