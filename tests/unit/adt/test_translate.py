"""Tests of `sdg_tech_tagger.adt.translate`, written from the contract alone.

Source of every expected value: `docs/query-translation-contract.md`, section
"Module `translate`" of the contract. Expected strings are derived by hand
from the rules of the contract; the spaces at the ends of normalised texts and
of patterns are part of the values and are asserted exactly.

The `compile_queries` tests read the six query files of `query/wos_adt/`. They
assert exact terms and an exact pattern for the Blockchain file only, plus
fragments derived by hand for the other five; no term count is hard-coded.
"""

import json
import re
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from sdg_tech_tagger.adt import translate
from sdg_tech_tagger.adt.wos_query import QueryError, parse_terms

ROOT = Path(__file__).resolve().parents[3]
QUERY_DIR = ROOT / "src" / "sdg_tech_tagger" / "adt" / "wos"

# Code to file, in the order of the contract's mapping table.
QUERY_FILES = {
    "AI": QUERY_DIR / "AI.txt",
    "IOT": QUERY_DIR / "IOT.txt",
    "CI": QUERY_DIR / "Computing_infrastructure.txt",
    "BL": QUERY_DIR / "Blockchain.txt",
    "ROB": QUERY_DIR / "Robotics.txt",
    "AM": QUERY_DIR / "Additive_Manufacturing.txt",
}

# The value of the artefact's "normalisation" key, as the contract's JSON
# block writes it (there the backslashes are doubled by JSON escaping).
NORMALISATION = (
    r"lower-case; every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)

# The six terms of query/wos_adt/Blockchain.txt, read by hand from the file.
BLOCKCHAIN_TERMS = [
    "altcoin",
    "bitcoin",
    "blockchain*",
    "cryptocurrenc*",
    "private blockchain*",
    "public blockchain*",
]
BLOCKCHAIN_PATTERN = (
    " (?:altcoin |bitcoin |blockchain[^ ]*|cryptocurrenc[^ ]*"
    "|private blockchain[^ ]*|public blockchain[^ ]*)"
)

# The eight rows of the contract's normalisation table.
NORMALISATION_TABLE = [
    ("3D-Printing, IoT.", " 3d printing iot "),
    ("  Machine\nLearning (ML)  ", " machine learning ml "),
    ("Industry 4.0", " industry 4 0 "),
    ("Señal de k-means", " señal de k means "),
    ("data_mining", " data mining "),
    ("", "  "),
    (None, "  "),
    ("...", "  "),
]

# Further cases that follow from the five steps of the normalisation.
NORMALISATION_DERIVED = [
    ("IoT", " iot "),
    ("iot", " iot "),
    ("   ", "  "),
    (" \n\t ", "  "),
    ("a\t\tb\r\nc", " a b c "),
    ("a--b__c", " a b c "),
    ("H2O", " h2o "),
    ("word2vec", " word2vec "),
    ("(IoT)", " iot "),
    ("ÉCOLE", " école "),
    ("<i>IoT</i> networks", " i iot i networks "),
    # A combining mark is neither a letter nor a number: it is a separator.
    ("école", " e cole "),
]


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("text", "expected"), NORMALISATION_TABLE)
def test_normalise_contract_table(text, expected):
    """Each row of the normalisation table gives exactly the listed string."""
    assert translate.normalise(text) == expected


@pytest.mark.parametrize(("text", "expected"), NORMALISATION_DERIVED)
def test_normalise_derived_cases(text, expected):
    """Cases derived from the five steps give exactly the expected string."""
    assert translate.normalise(text) == expected


def test_normalise_returns_a_python_str():
    """`normalise` produces a `str`, for a text and for `None` alike."""
    assert type(translate.normalise("IoT")) is str
    assert type(translate.normalise(None)) is str


def test_normalise_of_nothing_is_exactly_two_spaces():
    """Empty, null and punctuation-only texts all normalise to two spaces."""
    assert [translate.normalise(text) for text in ["", None, "...", " ", "-_-"]] == ["  "] * 5
    assert len(translate.normalise(None)) == 2


def test_normalise_expr_contract_table():
    """`normalise_expr` over a column gives the table's outputs, row for row."""
    frame = pl.DataFrame(
        {"t": [text for text, _ in NORMALISATION_TABLE]},
        schema={"t": pl.String},
    )
    out = frame.select(translate.normalise_expr(pl.col("t"))).to_series()
    assert out.to_list() == [expected for _, expected in NORMALISATION_TABLE]


def test_normalise_expr_is_a_string_expression_and_never_null():
    """The expression yields a String column with no null, even from nulls."""
    frame = pl.DataFrame({"t": [None, "IoT", None]}, schema={"t": pl.String})
    out = frame.select(translate.normalise_expr(pl.col("t"))).to_series()
    assert out.dtype == pl.String
    assert out.null_count() == 0
    assert out.to_list() == ["  ", " iot ", "  "]


def test_normalise_expr_composes_with_other_expressions():
    """The result is an ordinary expression: it can be aliased and kept alongside."""
    frame = pl.DataFrame({"id": [1, 2], "t": ["Industry 4.0", None]})
    out = frame.with_columns(translate.normalise_expr(pl.col("t")).alias("n"))
    expected = pl.DataFrame(
        {"id": [1, 2], "t": ["Industry 4.0", None], "n": [" industry 4 0 ", "  "]}
    )
    assert_frame_equal(out, expected)


# --------------------------------------------------------------------------
# One term
# --------------------------------------------------------------------------


# The nine rows of the contract's term table that produce a pattern.
@pytest.mark.parametrize(
    ("term", "hyphen_closed_form", "expected"),
    [
        ("iot", False, "iot "),
        ("robot*", False, "robot[^ ]*"),
        ("machine learning", False, "machine learning "),
        ("3d print*", False, "3d print[^ ]*"),
        ("industry 4.0", False, "industry 4 0 "),
        ("k-means", False, "k means "),
        ("k-means", True, "k ?means "),
        ("computer-mediated realit*", True, "computer ?mediated realit[^ ]*"),
        ("water resource* management", False, "water resource[^ ]* management "),
    ],
)
def test_term_pattern_contract_table(term, hyphen_closed_form, expected):
    """Each pattern row of the term table gives exactly the listed regex."""
    assert translate.term_pattern(term, hyphen_closed_form=hyphen_closed_form) == expected


# The four rows of the contract's term table that raise.
@pytest.mark.parametrize("term", ["colo?r", "*bot", "ro*bot", "naïve bayes"])
def test_term_pattern_contract_table_errors(term):
    """Each error row of the term table raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.term_pattern(term, hyphen_closed_form=False)


def test_term_pattern_default_keeps_hyphen_as_a_plain_separator():
    """`hyphen_closed_form` defaults to False: a hyphen compiles to one space."""
    assert translate.term_pattern("k-means") == "k means "
    assert translate.term_pattern("iot") == "iot "


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("IoT", "iot "),
        ("Robot*", "robot[^ ]*"),
        ("  Machine Learning  ", "machine learning "),
        ("\t3D Print*\n", "3d print[^ ]*"),
    ],
)
def test_term_pattern_strips_and_lower_cases(term, expected):
    """The term is stripped and lower-cased before it is compiled."""
    assert translate.term_pattern(term) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("5g", "5g "),
        ("word2vec", "word2vec "),
        ("machine   learning", "machine learning "),
        ("a.b", "a b "),
        ("k_means", "k means "),
        ("o'neil", "o neil "),
        ("machine-to-machine", "machine to machine "),
        ("large-scale data*", "large scale data[^ ]*"),
        ("long short term memory", "long short term memory "),
        ("wireless* sensor* network*", "wireless[^ ]* sensor[^ ]* network[^ ]*"),
        ("unmanned underwater vehicles*", "unmanned underwater vehicles[^ ]*"),
    ],
)
def test_term_pattern_derived_cases(term, expected):
    """Words are joined by one space whatever the separator run between them."""
    assert translate.term_pattern(term) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("machine-to-machine", "machine ?to ?machine "),
        ("large-scale data*", "large ?scale data[^ ]*"),
        ("cyber-physical system*", "cyber ?physical system[^ ]*"),
        ("multi-cloud*", "multi ?cloud[^ ]*"),
        ("a - b", "a ?b "),
        # No hyphen in the separator: the switch changes nothing.
        ("industry 4.0", "industry 4 0 "),
        ("machine learning", "machine learning "),
        ("iot", "iot "),
    ],
)
def test_term_pattern_hyphen_closed_form(term, expected):
    """With the switch on, only a separator holding a hyphen compiles to ` ?`."""
    assert translate.term_pattern(term, hyphen_closed_form=True) == expected


@pytest.mark.parametrize(
    "term",
    [
        # The two other Web of Science wildcards.
        "colo?r",
        "robot?",
        "?",
        "colo$r",
        "robot$",
        # A star that is not the last character of its word.
        "*bot",
        "ro*bot",
        "ro**",
        "deep *learning",
        "a*b c",
        # A word that is only a star.
        "*",
        "machine *",
        "* learning",
        # No word at all.
        "",
        "   ",
        "-",
        "...",
        # A letter or a digit outside ASCII.
        "naïve bayes",
        "café",
        "NAÏVE",
        "٣d print*",
    ],
)
def test_term_pattern_rejects_what_it_cannot_compile(term):
    """Every kind of term the contract lists as not compilable raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.term_pattern(term)


def test_term_pattern_rejects_the_same_terms_with_the_switch_on():
    """The errors do not depend on `hyphen_closed_form`."""
    for term in ["colo?r", "*bot", "ro*bot", "naïve bayes", ""]:
        with pytest.raises(QueryError):
            translate.term_pattern(term, hyphen_closed_form=True)


# --------------------------------------------------------------------------
# One code
# --------------------------------------------------------------------------


def test_code_pattern_contract_example():
    """The contract's example, character for character."""
    assert translate.code_pattern(["bitcoin", "blockchain*"]) == " (?:bitcoin |blockchain[^ ]*)"


def test_code_pattern_of_one_term():
    """One term still gets the leading space and the group."""
    assert translate.code_pattern(["iot"]) == " (?:iot )"
    assert translate.code_pattern(["robot*"]) == " (?:robot[^ ]*)"


def test_code_pattern_keeps_the_order_given():
    """The alternation follows the order of the terms, not a sorted order."""
    terms = ["robot*", "iot", "3d print*", "machine learning"]
    assert translate.code_pattern(terms) == " (?:robot[^ ]*|iot |3d print[^ ]*|machine learning )"
    assert (
        translate.code_pattern(list(reversed(terms)))
        == " (?:machine learning |3d print[^ ]*|iot |robot[^ ]*)"
    )


def test_code_pattern_accepts_any_sequence():
    """A tuple of terms compiles like a list."""
    assert translate.code_pattern(("bitcoin", "blockchain*")) == " (?:bitcoin |blockchain[^ ]*)"


def test_code_pattern_passes_hyphen_closed_form_to_every_term():
    """The switch reaches each term pattern of the alternation."""
    terms = ["k-means", "iot", "computer-mediated realit*"]
    assert translate.code_pattern(terms) == " (?:k means |iot |computer mediated realit[^ ]*)"
    assert (
        translate.code_pattern(terms, hyphen_closed_form=True)
        == " (?:k ?means |iot |computer ?mediated realit[^ ]*)"
    )


def test_code_pattern_of_the_blockchain_terms():
    """The pattern of the six Blockchain terms, derived by hand."""
    assert translate.code_pattern(BLOCKCHAIN_TERMS) == BLOCKCHAIN_PATTERN


@pytest.mark.parametrize("terms", [[], ()])
def test_code_pattern_of_no_term_raises(terms):
    """An empty sequence of terms raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.code_pattern(terms)


def test_code_pattern_raises_when_one_term_cannot_be_compiled():
    """One term that cannot be compiled stops the whole code."""
    with pytest.raises(QueryError):
        translate.code_pattern(["iot", "colo?r", "robot*"])


@pytest.mark.parametrize("hyphen_closed_form", [False, True])
def test_code_pattern_has_no_quote_and_no_backslash(hyphen_closed_form):
    """Quotes and backslashes in a term are separators and never reach the pattern."""
    terms = ["o'neil", 'say "x" now', "back\\slash", "k-means", "industry 4.0", "3d print*"]
    pattern = translate.code_pattern(terms, hyphen_closed_form=hyphen_closed_form)
    assert "'" not in pattern
    assert '"' not in pattern
    assert "\\" not in pattern


def test_code_pattern_of_terms_with_quotes_and_backslash_exact():
    """The same odd terms compile to plain words joined by single spaces."""
    terms = ["o'neil", 'say "x" now', "back\\slash"]
    assert translate.code_pattern(terms) == " (?:o neil |say x now |back slash )"


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

MATCH_TERMS = ["3d print*", "iot", "machine learning", "robot*"]


def test_pattern_of_the_matching_example():
    """The pattern the matching table is built on, written out by hand."""
    assert (
        translate.code_pattern(MATCH_TERMS)
        == " (?:3d print[^ ]*|iot |machine learning |robot[^ ]*)"
    )


# The eleven rows of the contract's matching table.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A 3D-printing, approach", True),
        ("3-D printing", False),
        ("IoT-based sensing", True),
        ("The patriot act", False),
        ("IoT", True),
        ("Machine. Learning is hard", True),
        ("machine-learning", True),
        ("machinelearning", False),
        ("robotics", True),
        ("microrobot", False),
        (None, False),
    ],
)
def test_matches_contract_table(text, expected):
    """Each row of the matching table gives exactly the listed Boolean."""
    pattern = translate.code_pattern(MATCH_TERMS)
    assert translate.matches(pattern, text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", False),
        ("   ", False),
        ("...", False),
        ("robot", True),
        ("Robots.", True),
        ("3D printer", True),
        ("3D print", True),
        ("iots", False),
        ("iot2020", False),
        ("smart_iot_device", True),
        ("señal IoT", True),
        ("IoTñ", False),
        ("machine\nlearning", True),
        ("machine learnings", False),
        ("a machine, a learning", False),
    ],
)
def test_matches_derived_cases(text, expected):
    """Further texts, each derived by normalising by hand and searching the pattern."""
    pattern = translate.code_pattern(MATCH_TERMS)
    assert translate.matches(pattern, text) is expected


def test_matches_returns_a_python_bool():
    """`matches` produces `True` or `False`, never a null and never a Polars value."""
    pattern = translate.code_pattern(MATCH_TERMS)
    assert type(translate.matches(pattern, "IoT")) is bool
    assert type(translate.matches(pattern, "nothing here")) is bool
    assert type(translate.matches(pattern, None)) is bool


@pytest.mark.parametrize(
    ("text", "open_form", "closed_form"),
    [
        ("k-means", True, True),
        ("k means", True, True),
        ("K-Means clustering", True, True),
        ("kmeans", False, True),
        ("kxmeans", False, False),
        ("k  means", True, True),
    ],
)
def test_matches_with_and_without_hyphen_closed_form(text, open_form, closed_form):
    """The closed spelling matches only when the switch is on."""
    assert translate.matches(translate.code_pattern(["k-means"]), text) is open_form
    assert (
        translate.matches(translate.code_pattern(["k-means"], hyphen_closed_form=True), text)
        is closed_form
    )


# --------------------------------------------------------------------------
# Flagging a table
# --------------------------------------------------------------------------


def _example_patterns():
    """Return the two code patterns of the contract's `flag` example."""
    return {
        "AI": translate.code_pattern(["machine learning", "deep learning"]),
        "ROB": translate.code_pattern(["robot*"]),
    }


def _example_frame():
    """Return the three-row frame of the contract's `flag` example."""
    return pl.DataFrame(
        {
            "title": ["Deep learning for robots", "Blockchain", None],
            "abstract": [None, "We use machine", "learning"],
        },
        schema={"title": pl.String, "abstract": pl.String},
    )


def _wider_frame():
    """Return six hand-written rows, with two columns that are not searched."""
    return pl.DataFrame(
        {
            "id": [30, 10, 20, 40, 50, 60],
            "title": ["Robots at work", None, "Machine", None, "", "Deep Learning"],
            "abstract": [
                None,
                "A machine-learning study.",
                "learning robotics",
                None,
                "",
                "of microrobots",
            ],
            "venue": ["Journal of Robotics"] * 6,
        },
        schema={"id": pl.Int64, "title": pl.String, "abstract": pl.String, "venue": pl.String},
    )


def test_flag_contract_example():
    """The contract's example: exact columns, exact values, exact dtypes."""
    out = translate.flag(_example_frame(), _example_patterns(), ["title", "abstract"])
    expected = pl.DataFrame(
        {
            "title": ["Deep learning for robots", "Blockchain", None],
            "abstract": [None, "We use machine", "learning"],
            "AI": [True, False, False],
            "ROB": [True, False, False],
        },
        schema={"title": pl.String, "abstract": pl.String, "AI": pl.Boolean, "ROB": pl.Boolean},
    )
    assert out.columns == ["title", "abstract", "AI", "ROB"]
    assert out["AI"].to_list() == [True, False, False]
    assert out["ROB"].to_list() == [True, False, False]
    assert_frame_equal(out, expected)


def test_flag_columns_follow_the_order_of_the_mapping():
    """The flag columns are appended in the order of the mapping, not sorted."""
    patterns = _example_patterns()
    reordered = {"ROB": patterns["ROB"], "AI": patterns["AI"]}
    out = translate.flag(_example_frame(), reordered, ["title", "abstract"])
    assert out.columns == ["title", "abstract", "ROB", "AI"]
    assert out["ROB"].to_list() == [True, False, False]
    assert out["AI"].to_list() == [True, False, False]


def test_flag_keeps_rows_order_and_original_columns():
    """Same rows in the same order, every original column untouched, flags appended."""
    out = translate.flag(_wider_frame(), _example_patterns(), ["title", "abstract"])
    expected = _wider_frame().with_columns(
        pl.Series("AI", [False, True, False, False, False, True], dtype=pl.Boolean),
        pl.Series("ROB", [True, False, True, False, False, False], dtype=pl.Boolean),
    )
    assert out.columns == ["id", "title", "abstract", "venue", "AI", "ROB"]
    assert out["id"].to_list() == [30, 10, 20, 40, 50, 60]
    assert_frame_equal(out, expected)


def test_flag_searches_only_the_named_fields():
    """A column that is not named in `fields` is never searched."""
    patterns = _example_patterns()
    title_only = translate.flag(_wider_frame(), patterns, ["title"])
    assert title_only["AI"].to_list() == [False, False, False, False, False, True]
    assert title_only["ROB"].to_list() == [True, False, False, False, False, False]
    abstract_only = translate.flag(_wider_frame(), patterns, ["abstract"])
    assert abstract_only["AI"].to_list() == [False, True, False, False, False, False]
    assert abstract_only["ROB"].to_list() == [False, False, True, False, False, False]
    venue_only = translate.flag(_wider_frame(), patterns, ["venue"])
    assert venue_only["AI"].to_list() == [False] * 6
    assert venue_only["ROB"].to_list() == [True] * 6


def test_flag_does_not_depend_on_the_order_of_the_fields():
    """A flag is true when any field matches, whichever is named first."""
    patterns = _example_patterns()
    out = translate.flag(_wider_frame(), patterns, ["abstract", "title"])
    assert out["AI"].to_list() == [False, True, False, False, False, True]
    assert out["ROB"].to_list() == [True, False, True, False, False, False]


def test_flag_term_never_spans_two_fields():
    """`machine` ending one field and `learning` starting the other is not a hit."""
    frame = pl.DataFrame(
        {
            "title": ["A machine", "learning", "machine learning"],
            "abstract": ["learning to see", "A machine", None],
        },
        schema={"title": pl.String, "abstract": pl.String},
    )
    out = translate.flag(frame, _example_patterns(), ["title", "abstract"])
    assert out["AI"].to_list() == [False, False, True]
    assert out["ROB"].to_list() == [False, False, False]


def test_flag_is_never_null():
    """Null fields match nothing: the flags are False, not null."""
    frame = pl.DataFrame(
        {"title": [None, None, "Robots"], "abstract": [None, "", None]},
        schema={"title": pl.String, "abstract": pl.String},
    )
    out = translate.flag(frame, _example_patterns(), ["title", "abstract"])
    assert out["AI"].dtype == pl.Boolean
    assert out["ROB"].dtype == pl.Boolean
    assert out["AI"].null_count() == 0
    assert out["ROB"].null_count() == 0
    assert out["AI"].to_list() == [False, False, False]
    assert out["ROB"].to_list() == [False, False, True]


def test_flag_of_a_frame_with_no_row():
    """A frame with no row comes back with no row and the Boolean columns added."""
    frame = pl.DataFrame(schema={"title": pl.String, "abstract": pl.String})
    out = translate.flag(frame, _example_patterns(), ["title", "abstract"])
    assert out.height == 0
    assert out.schema == {
        "title": pl.String,
        "abstract": pl.String,
        "AI": pl.Boolean,
        "ROB": pl.Boolean,
    }


def test_flag_agrees_with_matches_field_by_field():
    """A flag equals `matches` on the title or `matches` on the abstract."""
    frame = _wider_frame()
    patterns = _example_patterns()
    out = translate.flag(frame, patterns, ["title", "abstract"])
    for code, pattern in patterns.items():
        by_hand = [
            translate.matches(pattern, title) or translate.matches(pattern, abstract)
            for title, abstract in zip(frame["title"], frame["abstract"], strict=True)
        ]
        assert out[code].to_list() == by_hand


def test_flag_raises_on_a_field_absent_from_the_frame():
    """A field name that is not a column of the frame raises `ValueError`."""
    with pytest.raises(ValueError):
        translate.flag(_example_frame(), _example_patterns(), ["title", "keywords"])
    with pytest.raises(ValueError):
        translate.flag(_example_frame(), _example_patterns(), ["fulltext"])


def test_flag_raises_when_a_code_is_already_a_column():
    """A code that is already a column of the frame raises `ValueError`."""
    frame = _example_frame().with_columns(pl.lit(False).alias("AI"))
    with pytest.raises(ValueError):
        translate.flag(frame, _example_patterns(), ["title", "abstract"])
    with pytest.raises(ValueError):
        translate.flag(
            _example_frame(), {"title": translate.code_pattern(["robot*"])}, ["title", "abstract"]
        )


# --------------------------------------------------------------------------
# Compiling the files
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artefact():
    """Compile the six real query files, in the order of the contract's mapping."""
    return translate.compile_queries(QUERY_FILES)


def _write(path, text):
    """Write a hand-made query file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_compile_queries_on_two_hand_written_files(tmp_path):
    """The whole artefact for two small files, asserted value for value."""
    one = _write(tmp_path / "one.txt", 'TS = (\n("Bitcoin") OR ("k-means") OR ("bitcoin")\n)')
    two = _write(tmp_path / "sub" / "two.txt", 'TS = ( ("Robot*") OR ("industry 4.0") )')
    out = translate.compile_queries({"ZZ": two, "AA": one})
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION,
        "hyphen_closed_form": False,
        "plural_tolerant": False,
        "definitions": [
            {
                "code": "ZZ",
                "source": "two.txt",
                "term_count": 2,
                "terms": ["robot*", "industry 4.0"],
                "pattern": " (?:robot[^ ]*|industry 4 0 )",
            },
            {
                "code": "AA",
                "source": "one.txt",
                "term_count": 2,
                "terms": ["bitcoin", "k-means"],
                "pattern": " (?:bitcoin |k means )",
            },
        ],
    }


def test_compile_queries_with_hyphen_closed_form(tmp_path):
    """The switch is recorded in the artefact and applied to every pattern."""
    one = _write(tmp_path / "one.txt", 'TS = ( ("Bitcoin") OR ("k-means") )')
    out = translate.compile_queries({"AA": one}, hyphen_closed_form=True)
    assert out["hyphen_closed_form"] is True
    assert out["definitions"] == [
        {
            "code": "AA",
            "source": "one.txt",
            "term_count": 2,
            "terms": ["bitcoin", "k-means"],
            "pattern": " (?:bitcoin |k ?means )",
        }
    ]


def test_compile_queries_stops_on_a_file_that_is_not_a_disjunction(tmp_path):
    """A query file with `AND` raises `QueryError`: nothing is repaired."""
    good = _write(tmp_path / "good.txt", 'TS = ( ("a") OR ("b") )')
    bad = _write(tmp_path / "bad.txt", 'TS = ( ("a") AND ("b") )')
    with pytest.raises(QueryError):
        translate.compile_queries({"GOOD": good, "BAD": bad})


def test_compile_queries_stops_on_a_term_that_cannot_be_compiled(tmp_path):
    """A term with another wildcard raises `QueryError`: nothing is repaired."""
    bad = _write(tmp_path / "bad.txt", 'TS = ( ("robot*") OR ("colo?r") )')
    with pytest.raises(QueryError):
        translate.compile_queries({"BAD": bad})


def test_real_artefact_top_level(artefact):
    """Version 1, the fixed normalisation text, the switch off, six definitions."""
    assert list(artefact) == [
        "version",
        "normalisation",
        "hyphen_closed_form",
        "plural_tolerant",
        "definitions",
    ]
    assert artefact["version"] == 1
    assert type(artefact["version"]) is int
    assert artefact["normalisation"] == NORMALISATION
    assert artefact["hyphen_closed_form"] is False
    assert type(artefact["definitions"]) is list
    assert len(artefact["definitions"]) == 6


def test_real_artefact_codes_are_in_the_order_of_the_mapping(artefact):
    """`definitions` follows the mapping: AI, IOT, CI, BL, ROB, AM."""
    codes = [definition["code"] for definition in artefact["definitions"]]
    assert codes == ["AI", "IOT", "CI", "BL", "ROB", "AM"]


def test_real_artefact_follows_a_different_mapping_order():
    """The order comes from the mapping given, not from a fixed or sorted order."""
    files = {"BL": QUERY_FILES["BL"], "AM": QUERY_FILES["AM"], "AI": QUERY_FILES["AI"]}
    out = translate.compile_queries(files)
    assert [definition["code"] for definition in out["definitions"]] == ["BL", "AM", "AI"]
    assert [definition["source"] for definition in out["definitions"]] == [
        "Blockchain.txt",
        "Additive_Manufacturing.txt",
        "AI.txt",
    ]


def test_real_artefact_source_is_the_bare_file_name(artefact):
    """`source` is the file name without its directory."""
    sources = [definition["source"] for definition in artefact["definitions"]]
    assert sources == [
        "AI.txt",
        "IOT.txt",
        "Computing_infrastructure.txt",
        "Blockchain.txt",
        "Robotics.txt",
        "Additive_Manufacturing.txt",
    ]


def test_real_artefact_definitions_have_exactly_the_contract_keys(artefact):
    """Each definition holds code, source, term_count, terms and pattern, nothing else."""
    for definition in artefact["definitions"]:
        assert set(definition) == {"code", "source", "term_count", "terms", "pattern"}


def test_real_artefact_term_count_is_the_length_of_terms(artefact):
    """`term_count` equals `len(terms)`, and no code is empty."""
    for definition in artefact["definitions"]:
        assert type(definition["terms"]) is list
        assert type(definition["term_count"]) is int
        assert definition["term_count"] == len(definition["terms"])
        assert definition["term_count"] > 0


def test_real_artefact_terms_are_what_parse_terms_returns(artefact):
    """`terms` is exactly `parse_terms` of the text of the file."""
    for definition in artefact["definitions"]:
        text = QUERY_FILES[definition["code"]].read_text(encoding="utf-8")
        assert definition["terms"] == parse_terms(text)


def test_real_artefact_terms_have_no_repeat(artefact):
    """Within one code no term is listed twice."""
    for definition in artefact["definitions"]:
        assert len(set(definition["terms"])) == len(definition["terms"])


def test_real_artefact_pattern_is_code_pattern_of_terms(artefact):
    """Each `pattern` equals `code_pattern(terms)` with the switch off."""
    for definition in artefact["definitions"]:
        assert definition["pattern"] == translate.code_pattern(definition["terms"])


def test_real_artefact_blockchain_exact(artefact):
    """The Blockchain definition, derived by hand from the file and the contract."""
    assert artefact["definitions"][3] == {
        "code": "BL",
        "source": "Blockchain.txt",
        "term_count": 6,
        "terms": BLOCKCHAIN_TERMS,
        "pattern": BLOCKCHAIN_PATTERN,
    }


# First and last term of each file, read by hand from the files.
@pytest.mark.parametrize(
    ("position", "code", "first", "last"),
    [
        (0, "AI", "artificial intellig*", "distributed file system*"),
        (1, "IOT", "connected device*", "wireless sensor network*"),
        (2, "CI", "data center*", "5g networks"),
        (3, "BL", "altcoin", "public blockchain*"),
        (4, "ROB", "autonomous car*", "unmanned vehicle*"),
        (5, "AM", "3d print*", "stereolithography"),
    ],
)
def test_real_artefact_first_and_last_term(artefact, position, code, first, last):
    """The terms of each file start and end where the file does."""
    definition = artefact["definitions"][position]
    assert definition["code"] == code
    assert definition["terms"][0] == first
    assert definition["terms"][-1] == last


# Fragments of the five other patterns, each derived by hand from consecutive
# terms of the file: (position, code, how the pattern starts, a fragment
# inside it, how it ends).
@pytest.mark.parametrize(
    ("position", "code", "start", "inside", "end"),
    [
        (
            0,
            "AI",
            " (?:artificial intellig[^ ]*|automated reasoning |backpropagation |",
            "|generative adversarial network |k means |language model |",
            "|apache hive |distributed file system[^ ]*)",
        ),
        (
            1,
            "IOT",
            " (?:connected device[^ ]*|connected home[^ ]*|cyber physical system[^ ]*|",
            "|internet of things |iot |machine to enterprise |machine to human |",
            "|wireless body area network[^ ]*|wireless sensor network[^ ]*)",
        ),
        (
            2,
            "CI",
            " (?:data center[^ ]*|data centre[^ ]*|cloud application[^ ]*|",
            "|inter cloud computing |multi cloud[^ ]*|on demand computing |",
            "|5g |5th generation mobile |fifth generation mobile |5g networks )",
        ),
        (
            4,
            "ROB",
            " (?:autonomous car[^ ]*|autonomous underwater vehicle[^ ]*|",
            "|robot[^ ]*|robotic[^ ]*|self driving car[^ ]*|",
            "|unmanned underwater vehicles[^ ]*|unmanned vehicle[^ ]*)",
        ),
        (
            5,
            "AM",
            " (?:3d print[^ ]*|3d prototyping |additive fabrication |",
            "|direct digital manufacturing |industry 4 0 |layered manufacturing |",
            "|selective laser sintering |stereolithography )",
        ),
    ],
)
def test_real_artefact_pattern_fragments(artefact, position, code, start, inside, end):
    """Each pattern starts, continues and ends as the file's terms compile by hand."""
    definition = artefact["definitions"][position]
    assert definition["code"] == code
    assert definition["pattern"].startswith(start)
    assert inside in definition["pattern"]
    assert definition["pattern"].endswith(end)


def test_real_artefact_patterns_use_only_the_contract_alphabet(artefact):
    """Lower-case ASCII words, single spaces, `[^ ]*`, `|` and one group, nothing else."""
    word = r"[a-z0-9]+"
    term = rf"(?:{word}(?:\[\^ \]\*)? )*{word}(?:\[\^ \]\*| )"
    shape = re.compile(rf" \(\?:{term}(?:\|{term})*\)")
    for definition in artefact["definitions"]:
        pattern = definition["pattern"]
        assert shape.fullmatch(pattern) is not None, definition["code"]
        assert "'" not in pattern
        assert '"' not in pattern
        assert "\\" not in pattern
        assert "  " not in pattern


def test_real_artefact_survives_json(artefact):
    """The artefact is plain data: `json.dumps` accepts it and it reads back equal."""
    text = json.dumps(artefact)
    assert json.loads(text) == artefact


def test_real_artefact_with_hyphen_closed_form():
    """With the switch on, the same terms compile with ` ?` at each hyphen."""
    out = translate.compile_queries(QUERY_FILES, hyphen_closed_form=True)
    assert out["hyphen_closed_form"] is True
    assert [definition["code"] for definition in out["definitions"]] == [
        "AI",
        "IOT",
        "CI",
        "BL",
        "ROB",
        "AM",
    ]
    for definition in out["definitions"]:
        assert definition["term_count"] == len(definition["terms"])
        assert definition["pattern"] == translate.code_pattern(
            definition["terms"], hyphen_closed_form=True
        )
    ai = out["definitions"][0]
    assert "|generative adversarial network |k ?means |language model |" in ai["pattern"]
    # No Blockchain term has a hyphen: its pattern is the same either way.
    assert out["definitions"][3]["pattern"] == BLOCKCHAIN_PATTERN


def test_real_artefact_terms_do_not_depend_on_the_switch(artefact):
    """`hyphen_closed_form` changes patterns only: the terms stay as parsed."""
    out = translate.compile_queries(QUERY_FILES, hyphen_closed_form=True)
    for closed, plain in zip(out["definitions"], artefact["definitions"], strict=True):
        assert closed["terms"] == plain["terms"]
