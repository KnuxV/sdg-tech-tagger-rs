"""Tests of Amendments 2 and 3 of the query translation contract, from the contract alone.

Source of every expected value: `docs/query-translation-contract.md`, sections
"Amendment 2, 2026-10-07: four edge cases of the query files" and
"Amendment 3, 2026-10-07: decimals kept whole, and plural exceptions". Every
expected string was derived by hand from the rules stated there; the spaces at
the ends of normalised texts and of patterns are part of the values.

Updated on 2026-10-08 for "Amendment 4, 2026-10-08: a decimal separator becomes
a marker, not nothing": wherever a test of `decimal_whole=True` expected the
separator between two ASCII digits to be deleted, it now expects the letter
`p` in its place, and the artefact's `normalisation` string is Amendment 4's.
Names that still say "deletion" (`DELETION_CALL_TAIL`, some test names) are
kept from Amendment 3 and designate the marker replacement. What Amendment 4
adds (its new table rows, its fixture texts) is in `test_amendment4.py`.

What is covered:

- Amendment 2: the optional `TS =` tag, the unclosed quote, separators at the
  ends of a term, repeats compared after collapsing inner whitespace;
- `decimal_whole` on text (`normalise`, `normalise_expr`, `matches`, `flag`),
  on terms (`term_pattern`, `code_pattern`), in SQL (`normalise_sql`,
  `render_adt_flags`) and across engines (Polars against DuckDB on RE2);
- `plural_exceptions` in `code_pattern` and `compile_queries`;
- the two optional keys of the artefact, their place and their values;
- that every default is what it was.

The texts go into DuckDB through bound parameters, so a null stays a null.
"""

import json
from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from sdg_tech_tagger.adt import translate
from sdg_tech_tagger.adt.wos_query import QueryError, parse_terms

ROOT = Path(__file__).resolve().parents[3]
QUERY_DIR = ROOT / "src" / "sdg_tech_tagger" / "adt" / "simplified"

# Code to file, in the order of the contract's mapping table.
QUERY_FILES = {
    "AI": QUERY_DIR / "AI.txt",
    "IOT": QUERY_DIR / "IOT.txt",
    "CI": QUERY_DIR / "Computing_infrastructure.txt",
    "BL": QUERY_DIR / "Blockchain.txt",
    "ROB": QUERY_DIR / "Robotics.txt",
    "AM": QUERY_DIR / "Additive_Manufacturing.txt",
}

# The value of the artefact's "normalisation" key without the option, and with
# `decimal_whole` (in the contract's JSON the backslashes are doubled).
NORMALISATION = (
    r"lower-case; every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)
NORMALISATION_DECIMAL = (
    "lower-case; a dot or comma between two ASCII digits becomes the letter p; "
    r"every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)

# The top-level keys of the artefact in each of the four combinations.
KEYS_DEFAULT = ["version", "normalisation", "hyphen_closed_form", "plural_tolerant", "definitions"]
KEYS_DECIMAL = [
    "version",
    "normalisation",
    "hyphen_closed_form",
    "plural_tolerant",
    "decimal_whole",
    "definitions",
]
KEYS_EXCEPTIONS = [
    "version",
    "normalisation",
    "hyphen_closed_form",
    "plural_tolerant",
    "plural_exceptions",
    "definitions",
]
KEYS_BOTH = [
    "version",
    "normalisation",
    "hyphen_closed_form",
    "plural_tolerant",
    "decimal_whole",
    "plural_exceptions",
    "definitions",
]


def _write(path, text):
    """Write a hand-made query file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ==========================================================================
# Amendment 2: four edge cases of the query files
# ==========================================================================

# --------------------------------------------------------------------------
# Point 1: the `TS =` tag is optional
# --------------------------------------------------------------------------


def test_a2_table_no_field_tag():
    """First row of the amendment's table: a file with no tag is the same disjunction."""
    assert parse_terms('("a") OR ("b")') == ["a", "b"]


@pytest.mark.parametrize(
    ("untagged", "tagged", "expected"),
    [
        ('("a") OR ("b")', 'TS = ("a") OR ("b")', ["a", "b"]),
        (
            '( ("Bitcoin") OR ("blockchain*") )',
            'TS = ( ("Bitcoin") OR ("blockchain*") )',
            ["bitcoin", "blockchain*"],
        ),
        ('"a b" OR "c"', 'TS="a b" OR "c"', ["a b", "c"]),
        ('\n(\n("x")\nOR ("y")\n)\n', '\nts =(\n("x")\nOR ("y")\n)\n', ["x", "y"]),
        ('("only")', 'TS = ("only")', ["only"]),
    ],
)
def test_a2_untagged_file_parses_as_the_tagged_one(untagged, tagged, expected):
    """With and without the tag, the same terms come back in the same order."""
    assert parse_terms(untagged) == expected
    assert parse_terms(tagged) == expected


@pytest.mark.parametrize(
    "text",
    ['TI = ("a") OR ("b")', 'AB=("a")', 'ti = ("a")', 'AK = ( ("a") OR ("b") )'],
)
def test_a2_another_field_tag_still_raises(text):
    """Any other two-letter field tag still raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


# --------------------------------------------------------------------------
# Point 2: a quote that is never closed
# --------------------------------------------------------------------------


def test_a2_table_unclosed_quote():
    """Second row of the amendment's table: three double quotes raise `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms('TS = ( ("a) OR ("b") )')


@pytest.mark.parametrize(
    "text",
    [
        # One quote, never closed.
        '("a',
        '"a',
        '"',
        'TS = ("a)',
        'TS = ( ("a )',
        # An odd number of quotes: the last one opens a term that never ends.
        '("a") OR ("b',
        'TS = ( ("a") OR ("b) )',
        'TS = ( ("a") OR ("b") OR (" )',
        '"a" OR "b" OR "',
        '("a") OR ("b") "',
        # Five quotes, without a field tag.
        '("a") OR ("b") OR ("c)',
    ],
)
def test_a2_odd_number_of_quotes_raises(text):
    """A file with an odd number of double quotes raises `QueryError`."""
    assert text.count('"') % 2 == 1
    with pytest.raises(QueryError):
        parse_terms(text)


# --------------------------------------------------------------------------
# Point 3: a separator at the start or at the end of a term
# --------------------------------------------------------------------------


# The two rows of the amendment's term table, and `-iot` from its text.
@pytest.mark.parametrize("term", ["(iot)", "iot.", "-iot"])
def test_a2_table_separator_at_an_end_of_a_term(term):
    """Each spelling compiles to the pattern of `iot`, which is `iot `."""
    assert translate.term_pattern(term) == "iot "
    assert translate.term_pattern(term) == translate.term_pattern("iot")


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("...iot...", "iot "),
        ("iot-", "iot "),
        ("[iot]", "iot "),
        ("'iot'", "iot "),
        (" (IoT) ", "iot "),
        ("(robot*)", "robot[^ ]*"),
        ("robot*.", "robot[^ ]*"),
        ("-k-means-", "k means "),
        ("(machine learning)", "machine learning "),
        (".3d print*", "3d print[^ ]*"),
        ("industry 4.0.", "industry 4 0 "),
    ],
)
def test_a2_separators_at_the_ends_are_ignored(term, expected):
    """Whatever the run of separators at either end, only the words are compiled."""
    assert translate.term_pattern(term) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        # A hyphen at an end joins nothing, so it gives no ` ?`.
        ("-iot", "iot "),
        ("iot-", "iot "),
        ("-k-means-", "k ?means "),
        ("--machine-to-machine--", "machine ?to ?machine "),
        ("(robot*)-", "robot[^ ]*"),
    ],
)
def test_a2_separators_at_the_ends_with_hyphen_closed_form(term, expected):
    """With `hyphen_closed_form`, a hyphen at an end of the term is ignored too."""
    assert translate.term_pattern(term, hyphen_closed_form=True) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("iot.", "iot(?:s|es)? "),
        ("(iot)", "iot(?:s|es)? "),
        ("(smart city)", "smart cit(?:y|ies) "),
        ("robot*.", "robot[^ ]*"),
        ("industry 4.0.", "industry 4 0 "),
    ],
)
def test_a2_separators_at_the_ends_with_plural_tolerant(term, expected):
    """The last word is the last word, whatever separator follows it."""
    assert translate.term_pattern(term, plural_tolerant=True) == expected


@pytest.mark.parametrize("term", ["()", "-", "...", " . ", "(-)", "_", "'"])
def test_a2_term_made_only_of_separators_raises(term):
    """A term made only of separators has no word and raises `QueryError`, as before."""
    with pytest.raises(QueryError):
        translate.term_pattern(term)


# --------------------------------------------------------------------------
# Point 4: repeats compared after collapsing inner whitespace
# --------------------------------------------------------------------------


def test_a2_table_repeats_after_collapsing_whitespace():
    """Third row of the amendment's table: `big  data` and `big data` are one term."""
    assert parse_terms('("big  data") OR ("big data") OR ("x")') == ["big data", "x"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # The term is returned collapsed, even when it has no repeat.
        ('("deep   learning")', ["deep learning"]),
        ('TS = ("a  b   c")', ["a b c"]),
        ('TS = ("big \t\n data")', ["big data"]),
        ('TS = ("  big \n data  ")', ["big data"]),
        ('TS = ("Big\tData")', ["big data"]),
        # The collapsed spelling written first, or second: one term either way.
        ('("big data") OR ("big  data") OR ("x")', ["big data", "x"]),
        ('TS = ( ("Machine   Learning") OR ("machine learning") )', ["machine learning"]),
        ('TS = ( ("a  b") OR ("a\tb") OR ("a\nb") OR (" A   B ") )', ["a b"]),
        # The place of the first writing is kept.
        ('("x") OR ("big data") OR ("y") OR ("big    data")', ["x", "big data", "y"]),
        ('("big    data") OR ("y") OR ("big data")', ["big data", "y"]),
        # Words with no whitespace between them are another term.
        ('("big data") OR ("bigdata")', ["big data", "bigdata"]),
        ('("big data") OR ("big-data")', ["big data", "big-data"]),
    ],
)
def test_a2_inner_whitespace_is_collapsed(text, expected):
    """Every run of whitespace inside a term becomes one space, then repeats are dropped."""
    assert parse_terms(text) == expected


def test_a2_collapsed_terms_reach_the_artefact(tmp_path):
    """`compile_queries` keeps what `parse_terms` returned: one collapsed term."""
    one = _write(tmp_path / "one.txt", '("big  data") OR ("big data") OR ("x")')
    out = translate.compile_queries({"AA": one})
    assert out["definitions"] == [
        {
            "code": "AA",
            "source": "one.txt",
            "term_count": 2,
            "terms": ["big data", "x"],
            "pattern": " (?:big data |x )",
        }
    ]


# ==========================================================================
# Amendment 3: decimals kept whole
# ==========================================================================

# --------------------------------------------------------------------------
# On text
# --------------------------------------------------------------------------

# (input, output with `decimal_whole=True`, output with the default). The
# inputs are those of Amendment 3's table, row for row; the second column is
# what Amendment 4's table gives for them. The third is derived from the five
# steps of the base normalisation.
DECIMAL_TABLE = [
    ("0.5g of salt", " 0p5g of salt ", " 0 5g of salt "),
    ("0,5g", " 0p5g ", " 0 5g "),
    ("5G networks", " 5g networks ", " 5g networks "),
    ("beyond-5G (5G)", " beyond 5g 5g ", " beyond 5g 5g "),
    ("Industry 4.0", " industry 4p0 ", " industry 4 0 "),
    ("1,000 nodes", " 1p000 nodes ", " 1 000 nodes "),
    ("v1.2.3", " v1p2p3 ", " v1 2 3 "),
    ("1.2.3.4.5", " 1p2p3p4p5 ", " 1 2 3 4 5 "),
    ("in 2020. 5G", " in 2020 5g ", " in 2020 5g "),
    ("3.5 g", " 3p5 g ", " 3 5 g "),
    ("a.5", " a 5 ", " a 5 "),
    ("GPT-3.5", " gpt 3p5 ", " gpt 3 5 "),
    (None, "  ", "  "),
]

# Further cases that follow from the rule: only one `.` or `,` standing
# between two ASCII digits becomes `p`; everything else is as before.
DECIMAL_DERIVED = [
    ("", "  ", "  "),
    ("...", "  ", "  "),
    ("1.5", " 1p5 ", " 1 5 "),
    ("1,5", " 1p5 ", " 1 5 "),
    # No digit on one side: a separator as before.
    (".5", " 5 ", " 5 "),
    ("5.", " 5 ", " 5 "),
    ("5.a", " 5 a ", " 5 a "),
    ("1.5.", " 1p5 ", " 1 5 "),
    ("x2.0y", " x2p0y ", " x2 0y "),
    # Two marks in a row, or a space next to the mark: not between two digits.
    ("1..2", " 1 2 ", " 1 2 "),
    ("1.,2", " 1 2 ", " 1 2 "),
    ("1 . 2", " 1 2 ", " 1 2 "),
    ("1. 2", " 1 2 ", " 1 2 "),
    ("1.\n2", " 1 2 ", " 1 2 "),
    # Only the dot and the comma become the marker.
    ("1:2", " 1 2 ", " 1 2 "),
    ("1/2", " 1 2 ", " 1 2 "),
    ("1-2", " 1 2 ", " 1 2 "),
    ("1;2", " 1 2 ", " 1 2 "),
    ("1_2", " 1 2 ", " 1 2 "),
    # Chains: two passes mark every separator, dots and commas mixed.
    ("1.2,3", " 1p2p3 ", " 1 2 3 "),
    ("3,14,15", " 3p14p15 ", " 3 14 15 "),
    ("1.2.3.4.5.6.7", " 1p2p3p4p5p6p7 ", " 1 2 3 4 5 6 7 "),
    ("10.20.30", " 10p20p30 ", " 10 20 30 "),
    ("1,000,000.50", " 1p000p000p50 ", " 1 000 000 50 "),
    # Only the ASCII digits count: Arabic-Indic digits are numbers, not `0-9`.
    ("٣.٥", " ٣ ٥ ", " ٣ ٥ "),
    ("3.٥", " 3 ٥ ", " 3 ٥ "),
    # The step sits after lower-casing and before the separator replacement.
    ("INDUSTRY 4.0, SOCIETY 5.0.", " industry 4p0 society 5p0 ", " industry 4 0 society 5 0 "),
    ("In 2020,5G", " in 2020p5g ", " in 2020 5g "),
    ("0.5 g", " 0p5 g ", " 0 5 g "),
]

DECIMAL_ALL = DECIMAL_TABLE + DECIMAL_DERIVED


@pytest.mark.parametrize(("text", "expected"), [(t, e) for t, e, _ in DECIMAL_TABLE])
def test_normalise_decimal_whole_contract_table(text, expected):
    """Each row of the amendment's normalisation table gives exactly the listed string."""
    assert translate.normalise(text, decimal_whole=True) == expected


@pytest.mark.parametrize(("text", "expected"), [(t, e) for t, e, _ in DECIMAL_DERIVED])
def test_normalise_decimal_whole_derived_cases(text, expected):
    """Cases derived from the deletion rule give exactly the expected string."""
    assert translate.normalise(text, decimal_whole=True) == expected


@pytest.mark.parametrize(("text", "expected"), [(t, d) for t, _, d in DECIMAL_ALL])
def test_normalise_default_is_unchanged_on_the_same_inputs(text, expected):
    """Without the keyword, and with it False, the five base steps apply and nothing else."""
    assert translate.normalise(text) == expected
    assert translate.normalise(text, decimal_whole=False) == expected


def test_normalise_decimal_whole_returns_a_python_str():
    """`normalise` produces a `str` with the option, for a text and for `None` alike."""
    assert type(translate.normalise("0.5g", decimal_whole=True)) is str
    assert type(translate.normalise(None, decimal_whole=True)) is str
    assert len(translate.normalise(None, decimal_whole=True)) == 2


def test_normalise_expr_decimal_whole_contract_table():
    """`normalise_expr` over a column gives the table's outputs, row for row."""
    frame = pl.DataFrame({"t": [text for text, _, _ in DECIMAL_TABLE]}, schema={"t": pl.String})
    out = frame.select(translate.normalise_expr(pl.col("t"), decimal_whole=True)).to_series()
    assert out.to_list() == [expected for _, expected, _ in DECIMAL_TABLE]


def test_normalise_expr_decimal_whole_derived_cases():
    """The derived cases, through the expression."""
    frame = pl.DataFrame({"t": [text for text, _, _ in DECIMAL_DERIVED]}, schema={"t": pl.String})
    out = frame.select(translate.normalise_expr(pl.col("t"), decimal_whole=True)).to_series()
    assert out.to_list() == [expected for _, expected, _ in DECIMAL_DERIVED]


def test_normalise_expr_default_is_unchanged_on_the_same_inputs():
    """Without the keyword, and with it False, the expression gives the base outputs."""
    frame = pl.DataFrame({"t": [text for text, _, _ in DECIMAL_ALL]}, schema={"t": pl.String})
    expected = [default for _, _, default in DECIMAL_ALL]
    plain = frame.select(translate.normalise_expr(pl.col("t"))).to_series()
    explicit = frame.select(translate.normalise_expr(pl.col("t"), decimal_whole=False)).to_series()
    assert plain.to_list() == expected
    assert explicit.to_list() == expected


def test_normalise_expr_decimal_whole_is_a_string_expression_and_never_null():
    """With the option the expression still yields a String column with no null."""
    frame = pl.DataFrame({"t": [None, "0.5g", None, "Industry 4.0"]}, schema={"t": pl.String})
    out = frame.select(translate.normalise_expr(pl.col("t"), decimal_whole=True)).to_series()
    assert out.dtype == pl.String
    assert out.null_count() == 0
    assert out.to_list() == ["  ", " 0p5g ", "  ", " industry 4p0 "]


def test_normalise_expr_decimal_whole_side_by_side_with_the_default():
    """Both forms of the expression can sit in one frame, each with its own output."""
    frame = pl.DataFrame({"id": [1, 2, 3], "t": ["v1.2.3", None, "GPT-3.5"]})
    out = frame.with_columns(
        translate.normalise_expr(pl.col("t")).alias("plain"),
        translate.normalise_expr(pl.col("t"), decimal_whole=True).alias("whole"),
    )
    expected = pl.DataFrame(
        {
            "id": [1, 2, 3],
            "t": ["v1.2.3", None, "GPT-3.5"],
            "plain": [" v1 2 3 ", "  ", " gpt 3 5 "],
            "whole": [" v1p2p3 ", "  ", " gpt 3p5 "],
        }
    )
    assert_frame_equal(out, expected)


# --------------------------------------------------------------------------
# On terms
# --------------------------------------------------------------------------


# The seven rows of the amendment's term table.
@pytest.mark.parametrize(
    ("term", "options", "expected"),
    [
        ("5g", {"decimal_whole": True}, "5g "),
        ("industry 4.0", {"decimal_whole": True}, "industry 4p0 "),
        ("industry 4.0", {}, "industry 4 0 "),
        ("i4.0", {"decimal_whole": True}, "i4p0 "),
        ("gpt-3.5", {"decimal_whole": True}, "gpt 3p5 "),
        ("gpt-3.5", {"decimal_whole": True, "hyphen_closed_form": True}, "gpt ?3p5 "),
        ("society 5.0", {"decimal_whole": True, "plural_tolerant": True}, "society 5p0 "),
    ],
)
def test_term_pattern_decimal_whole_contract_table(term, options, expected):
    """Each row of the amendment's term table gives exactly the listed regex."""
    assert translate.term_pattern(term, **options) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("4.0", "4p0 "),
        ("4,0", "4p0 "),
        ("industry 4,0", "industry 4p0 "),
        ("v1.2.3", "v1p2p3 "),
        ("1.2.3.4.5", "1p2p3p4p5 "),
        ("1,000 nodes", "1p000 nodes "),
        ("web 2.0 technolog*", "web 2p0 technolog[^ ]*"),
        ("3.5*", "3p5[^ ]*"),
        # No digit on both sides: a separator as before.
        ("a.5", "a 5 "),
        ("a.b", "a b "),
        ("5.a", "5 a "),
        ("4. 0", "4 0 "),
        ("4..0", "4 0 "),
        ("4-0", "4 0 "),
        # Nothing to mark: the pattern is the default one.
        ("iot", "iot "),
        ("robot*", "robot[^ ]*"),
        ("k-means", "k means "),
        ("3d print*", "3d print[^ ]*"),
        ("machine learning", "machine learning "),
        # Stripping and lower-casing still come first.
        ("  Industry 4.0 ", "industry 4p0 "),
        ("GPT-3.5", "gpt 3p5 "),
        # A separator at an end of the term is still ignored (Amendment 2).
        ("(industry 4.0)", "industry 4p0 "),
        ("industry 4.0.", "industry 4p0 "),
    ],
)
def test_term_pattern_decimal_whole_derived_cases(term, expected):
    """Further terms, each compiled by hand after marking the separators between digits."""
    assert translate.term_pattern(term, decimal_whole=True) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("gpt-3.5", "gpt ?3p5 "),
        ("industry-4.0", "industry ?4p0 "),
        ("gpt-3.5-turbo", "gpt ?3p5 ?turbo "),
        ("i4.0", "i4p0 "),
        ("k-means", "k ?means "),
        # The dot becomes `p`, not a joint: no ` ?` comes from it.
        ("web 2.0", "web 2p0 "),
    ],
)
def test_term_pattern_decimal_whole_with_hyphen_closed_form(term, expected):
    """The hyphen still gives ` ?`; the decimal mark is a letter before the split."""
    assert translate.term_pattern(term, decimal_whole=True, hyphen_closed_form=True) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        # A last word ending in a digit is left as it is.
        ("society 5.0", "society 5p0 "),
        ("industry 4.0", "industry 4p0 "),
        ("gpt-3.5", "gpt 3p5 "),
        # A last word ending in a letter gets its group.
        ("5g", "5g(?:s|es)? "),
        ("1,000 node", "1p000 node(?:s|es)? "),
        ("industry 4.0 technology", "industry 4p0 technolog(?:y|ies) "),
        ("web 2.0 app*", "web 2p0 app[^ ]*"),
    ],
)
def test_term_pattern_decimal_whole_with_plural_tolerant(term, expected):
    """The plural rules apply to the last word of the term after the marking."""
    assert translate.term_pattern(term, decimal_whole=True, plural_tolerant=True) == expected


def test_term_pattern_decimal_whole_with_both_other_switches():
    """All three options on one term, character for character."""
    assert (
        translate.term_pattern(
            "gpt-3.5 model", decimal_whole=True, hyphen_closed_form=True, plural_tolerant=True
        )
        == "gpt ?3p5 model(?:s|es)? "
    )
    assert (
        translate.term_pattern(
            "industry-4.0", decimal_whole=True, hyphen_closed_form=True, plural_tolerant=True
        )
        == "industry ?4p0 "
    )


@pytest.mark.parametrize("term", ["colo?r", "*bot", "ro*bot", "naïve bayes", "", "robot$", "..."])
def test_term_pattern_decimal_whole_still_rejects_what_it_cannot_compile(term):
    """The errors of the term rules do not depend on `decimal_whole`."""
    with pytest.raises(QueryError):
        translate.term_pattern(term, decimal_whole=True)


# (term, hyphen_closed_form, plural_tolerant, pattern before this amendment).
DEFAULT_TERM_ROWS = [
    ("iot", False, False, "iot "),
    ("5g", False, False, "5g "),
    ("robot*", False, False, "robot[^ ]*"),
    ("industry 4.0", False, False, "industry 4 0 "),
    ("i4.0", False, False, "i4 0 "),
    ("gpt-3.5", False, False, "gpt 3 5 "),
    ("gpt-3.5", True, False, "gpt ?3 5 "),
    ("society 5.0", False, True, "society 5 0 "),
    ("v1.2.3", False, False, "v1 2 3 "),
    ("1,000 nodes", False, True, "1 000 nodes(?:s|es)? "),
    ("k-means", True, True, "k ?means(?:s|es)? "),
    ("smart city", False, True, "smart cit(?:y|ies) "),
]


@pytest.mark.parametrize(
    ("term", "hyphen_closed_form", "plural_tolerant", "expected"), DEFAULT_TERM_ROWS
)
def test_term_pattern_default_is_unchanged(term, hyphen_closed_form, plural_tolerant, expected):
    """Without the keyword, and with it False, every term pattern is what it was."""
    options = {"hyphen_closed_form": hyphen_closed_form, "plural_tolerant": plural_tolerant}
    assert translate.term_pattern(term, **options) == expected
    assert translate.term_pattern(term, decimal_whole=False, **options) == expected


# --------------------------------------------------------------------------
# One code
# --------------------------------------------------------------------------

DECIMAL_MATCH_TERMS = ["5g", "industry 4.0"]


def test_code_pattern_decimal_whole_of_the_matching_example():
    """The pattern the amendment's matching table is built on, written out by hand."""
    assert (
        translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True) == " (?:5g |industry 4p0 )"
    )


def test_code_pattern_decimal_whole_reaches_every_term():
    """The option reaches each term of the alternation, in the order given."""
    terms = ["industry 4.0", "gpt-3.5", "iot", "v1.2.3", "web 2.0 technolog*"]
    assert (
        translate.code_pattern(terms, decimal_whole=True)
        == " (?:industry 4p0 |gpt 3p5 |iot |v1p2p3 |web 2p0 technolog[^ ]*)"
    )


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({}, " (?:gpt 3 5 |society 5 0 |smart city |5g )"),
        ({"decimal_whole": True}, " (?:gpt 3p5 |society 5p0 |smart city |5g )"),
        (
            {"decimal_whole": True, "hyphen_closed_form": True},
            " (?:gpt ?3p5 |society 5p0 |smart city |5g )",
        ),
        (
            {"decimal_whole": True, "plural_tolerant": True},
            " (?:gpt 3p5 |society 5p0 |smart cit(?:y|ies) |5g(?:s|es)? )",
        ),
        (
            {"decimal_whole": True, "hyphen_closed_form": True, "plural_tolerant": True},
            " (?:gpt ?3p5 |society 5p0 |smart cit(?:y|ies) |5g(?:s|es)? )",
        ),
        (
            {"hyphen_closed_form": True, "plural_tolerant": True},
            " (?:gpt ?3 5 |society 5 0 |smart cit(?:y|ies) |5g(?:s|es)? )",
        ),
    ],
)
def test_code_pattern_decimal_whole_combinations(options, expected):
    """`decimal_whole` combines with `hyphen_closed_form` and `plural_tolerant`."""
    terms = ["gpt-3.5", "society 5.0", "smart city", "5g"]
    assert translate.code_pattern(terms, **options) == expected


def test_code_pattern_decimal_whole_of_no_term_raises():
    """An empty sequence of terms still raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.code_pattern([], decimal_whole=True)


def test_code_pattern_decimal_whole_has_no_quote_and_no_backslash():
    """The option brings no quote and no backslash: SQL raw literals stay safe."""
    pattern = translate.code_pattern(
        ["o'neil 4.0", 'say "2,5" now', "back\\slash 1.2.3"], decimal_whole=True
    )
    assert pattern == " (?:o neil 4p0 |say 2p5 now |back slash 1p2p3 )"
    assert "'" not in pattern
    assert '"' not in pattern
    assert "\\" not in pattern


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


# The ten rows of the amendment's matching table.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a 5G network", True),
        ("beyond-5G systems", True),
        ("(5G)", True),
        ("0.5g per day", False),
        ("0,5g per day", False),
        ("2.5G networks", False),
        ("Industry 4.0 and beyond", True),
        ("industry 4,0", True),
        ("industry 4 0", False),
        ("the industry 40 years ago", False),
    ],
)
def test_matches_decimal_whole_contract_table(text, expected):
    """Each row of the amendment's matching table gives exactly the listed Boolean."""
    pattern = translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True)
    assert translate.matches(pattern, text, decimal_whole=True) is expected


def test_matches_default_still_matches_a_mass():
    """The default row: `5g` compiled and matched without the option hits "0.5g per day"."""
    q = translate.code_pattern(["5g"])
    assert q == " (?:5g )"
    assert translate.matches(q, "0.5g per day") is True
    assert translate.matches(q, "0.5g per day", decimal_whole=False) is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5G", True),
        ("5g.", True),
        ("In 2020. 5G arrived", True),
        ("in 2020, 5G", True),
        # A number glued to the term by a comma becomes one word: known and accepted.
        ("in 2020,5G", False),
        # A mass written with a space never matched and still does not.
        ("0.5 g", False),
        ("1,000 nodes on 5G", True),
        ("1,5g", False),
        ("5.5G", False),
        ("Industry 4.0.", True),
        ("INDUSTRY 4.0", True),
        ("industry 4.01", False),
        ("industry 4.0.1", False),
        ("industry 4. 0", False),
        ("industry 4..0", False),
        ("industry 40", False),
        ("industry 4-0", False),
        ("", False),
        ("...", False),
        (None, False),
    ],
)
def test_matches_decimal_whole_derived_cases(text, expected):
    """Further texts, each derived by normalising by hand and searching the pattern."""
    pattern = translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True)
    assert translate.matches(pattern, text, decimal_whole=True) is expected


@pytest.mark.parametrize(
    ("text", "plain", "whole"),
    [
        ("a 5G network", True, True),
        ("0.5g per day", True, False),
        ("0,5g per day", True, False),
        ("2.5G networks", True, False),
        ("in 2020,5G", True, False),
        ("Industry 4.0 and beyond", True, True),
        ("industry 4,0", True, True),
        ("industry 4 0", True, False),
        ("the industry 40 years ago", False, False),
        ("0.5 g", False, False),
        (None, False, False),
    ],
)
def test_matches_with_and_without_decimal_whole(text, plain, whole):
    """Each side consistent with itself: default pattern on default text, option on option."""
    default_pattern = translate.code_pattern(DECIMAL_MATCH_TERMS)
    whole_pattern = translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True)
    assert default_pattern == " (?:5g |industry 4 0 )"
    assert translate.matches(default_pattern, text) is plain
    assert translate.matches(default_pattern, text, decimal_whole=False) is plain
    assert translate.matches(whole_pattern, text, decimal_whole=True) is whole


def test_matches_term_followed_by_a_decimal_fraction():
    """Known and accepted: `gpt-3` no longer matches "GPT-3.5" with the option on."""
    whole = translate.code_pattern(["gpt-3"], decimal_whole=True)
    plain = translate.code_pattern(["gpt-3"])
    assert whole == " (?:gpt 3 )"
    assert plain == " (?:gpt 3 )"
    assert translate.matches(whole, "GPT-3.5", decimal_whole=True) is False
    assert translate.matches(whole, "GPT-3 and GPT-4", decimal_whole=True) is True
    assert translate.matches(plain, "GPT-3.5") is True
    listed = translate.code_pattern(["gpt-3", "gpt-3.5"], decimal_whole=True)
    assert listed == " (?:gpt 3 |gpt 3p5 )"
    assert translate.matches(listed, "GPT-3.5", decimal_whole=True) is True


def test_matches_takes_the_option_for_the_text_only():
    """`matches` normalises the text as told and does not look at how the pattern was made.

    A pattern compiled with the option, matched without it, is searched in
    text normalised without it: "Industry 4.0" is then ` industry 4 0 ` and
    the pattern ` (?:5g |industry 4p0 )` is not found. The contract calls this
    mix wrong; the test only pins that nothing at this level corrects it.
    """
    whole_pattern = translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True)
    assert translate.matches(whole_pattern, "Industry 4.0") is False
    assert translate.matches(whole_pattern, "Industry 4.0", decimal_whole=True) is True


def test_matches_decimal_whole_returns_a_python_bool():
    """With the option `matches` still produces a `bool`."""
    pattern = translate.code_pattern(DECIMAL_MATCH_TERMS, decimal_whole=True)
    assert type(translate.matches(pattern, "5G", decimal_whole=True)) is bool
    assert type(translate.matches(pattern, None, decimal_whole=True)) is bool


# --------------------------------------------------------------------------
# Flagging a table
# --------------------------------------------------------------------------


def _decimal_frame():
    """Return seven hand-written rows: masses, decimals, nulls and a term cut by a field."""
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "title": [
                "5G networks",
                "Salt intake",
                "Industry 4.0",
                None,
                "industry 4",
                None,
                "",
            ],
            "abstract": [
                None,
                "0.5g per day",
                "beyond-5G systems",
                "industry 4,0 at 2.5G",
                "0 and 5g",
                None,
                "the industry 40 years ago",
            ],
        },
        schema={"id": pl.Int64, "title": pl.String, "abstract": pl.String},
    )


def test_flag_decimal_whole_exact_rows():
    """`flag` with the option on a hand-written frame: exact columns, values and dtypes.

    Row 2 is a mass, row 4 holds "2.5G" and a comma decimal, row 5 has the
    term cut between two fields, row 7 is "industry 40", which Amendment 4 no longer accepts.
    """
    patterns = {
        "G5": translate.code_pattern(["5g"], decimal_whole=True),
        "I4": translate.code_pattern(["industry 4.0"], decimal_whole=True),
    }
    assert patterns == {"G5": " (?:5g )", "I4": " (?:industry 4p0 )"}
    out = translate.flag(_decimal_frame(), patterns, ["title", "abstract"], decimal_whole=True)
    expected = _decimal_frame().with_columns(
        pl.Series("G5", [True, False, True, False, True, False, False], dtype=pl.Boolean),
        pl.Series("I4", [False, False, True, True, False, False, False], dtype=pl.Boolean),
    )
    assert out.columns == ["id", "title", "abstract", "G5", "I4"]
    assert out["G5"].to_list() == [True, False, True, False, True, False, False]
    assert out["I4"].to_list() == [False, False, True, True, False, False, False]
    assert_frame_equal(out, expected)


def test_flag_default_on_the_same_frame_is_unchanged():
    """Without the keyword, and with it False, the default patterns flag as before."""
    patterns = {
        "G5": translate.code_pattern(["5g"]),
        "I4": translate.code_pattern(["industry 4.0"]),
    }
    assert patterns == {"G5": " (?:5g )", "I4": " (?:industry 4 0 )"}
    expected = _decimal_frame().with_columns(
        pl.Series("G5", [True, True, True, True, True, False, False], dtype=pl.Boolean),
        pl.Series("I4", [False, False, True, True, False, False, False], dtype=pl.Boolean),
    )
    plain = translate.flag(_decimal_frame(), patterns, ["title", "abstract"])
    explicit = translate.flag(
        _decimal_frame(), patterns, ["title", "abstract"], decimal_whole=False
    )
    assert_frame_equal(plain, expected)
    assert_frame_equal(explicit, expected)


def test_flag_decimal_whole_searches_only_the_named_fields():
    """With the option, a column not named in `fields` is still never searched."""
    patterns = {"G5": " (?:5g )", "I4": " (?:industry 4p0 )"}
    out = translate.flag(_decimal_frame(), patterns, ["title"], decimal_whole=True)
    assert out.columns == ["id", "title", "abstract", "G5", "I4"]
    assert out["G5"].to_list() == [True, False, False, False, False, False, False]
    assert out["I4"].to_list() == [False, False, True, False, False, False, False]


def test_flag_decimal_whole_is_never_null_and_keeps_the_mapping_order():
    """Flags are Boolean with no null, in the order of the mapping, nulls included."""
    patterns = {"I4": " (?:industry 4p0 )", "G5": " (?:5g )"}
    out = translate.flag(_decimal_frame(), patterns, ["abstract", "title"], decimal_whole=True)
    assert out.columns == ["id", "title", "abstract", "I4", "G5"]
    for code in patterns:
        assert out[code].dtype == pl.Boolean
        assert out[code].null_count() == 0
    assert out["G5"].to_list() == [True, False, True, False, True, False, False]
    assert out["I4"].to_list() == [False, False, True, True, False, False, False]


def test_flag_decimal_whole_agrees_with_matches_field_by_field():
    """A flag is the "or" of `matches` over the fields, with the option on each side."""
    patterns = {"G5": " (?:5g )", "I4": " (?:industry 4p0 )"}
    frame = _decimal_frame()
    out = translate.flag(frame, patterns, ["title", "abstract"], decimal_whole=True)
    for code, pattern in patterns.items():
        by_hand = [
            translate.matches(pattern, title, decimal_whole=True)
            or translate.matches(pattern, abstract, decimal_whole=True)
            for title, abstract in zip(frame["title"], frame["abstract"], strict=True)
        ]
        assert out[code].to_list() == by_hand, code


def test_flag_decimal_whole_still_raises_on_a_bad_field_or_code():
    """The two `ValueError` cases of `flag` do not depend on the option."""
    patterns = {"G5": " (?:5g )"}
    with pytest.raises(ValueError):
        translate.flag(_decimal_frame(), patterns, ["title", "keywords"], decimal_whole=True)
    with pytest.raises(ValueError):
        translate.flag(_decimal_frame(), {"id": " (?:5g )"}, ["title"], decimal_whole=True)


# --------------------------------------------------------------------------
# In SQL: normalise_sql
# --------------------------------------------------------------------------

# The two default forms, as they were before this amendment.

# The DuckDB form with `decimal_whole`, as the amendment's code block gives it.

# The BigQuery form: no `, 'g'`, the three patterns and `\1p\2` as raw
# literals, the replacement `' '` a plain literal.


# --------------------------------------------------------------------------
# In SQL: render_adt_flags
# --------------------------------------------------------------------------


# The pieces of the BigQuery normalisation, as raw literals.
DELETION_CALL_TAIL = r", r'([0-9])[.,]([0-9])', r'\1p\2')"


# --------------------------------------------------------------------------
# Engine parity with decimal_whole
# --------------------------------------------------------------------------

# Small term lists written by hand: a bare term a mass can imitate, terms
# holding a decimal, a chain, a truncated term.
PARITY_TERMS = {
    "G5": ["5g", "gpt-3.5"],
    "I4": ["industry 4.0", "society 5.0"],
    "AM": ["3d print*", "v1.2.3"],
}

# What `code_pattern(..., decimal_whole=True)` must give for each list above.
PARITY_PATTERNS = {
    "G5": " (?:5g |gpt 3p5 )",
    "I4": " (?:industry 4p0 |society 5p0 )",
    "AM": " (?:3d print[^ ]*|v1p2p3 )",
}


def _hits(*codes):
    """Return the expected flags of one text: True for the codes named, False for the rest."""
    unknown = set(codes) - set(PARITY_TERMS)
    assert not unknown, unknown
    return {code: code in codes for code in PARITY_TERMS}


# (text, {code: expected flag}). Each expectation was derived by normalising
# the text by hand with `decimal_whole=True` and searching the three patterns.
PARITY_FIXTURE = [
    # The bare term, on its own and inside a sentence.
    ("5G", _hits("G5")),
    ("a 5G network", _hits("G5")),
    ("beyond-5G (5G)", _hits("G5")),
    ("señal 5G", _hits("G5")),
    # A decimal before a term: the mass is one word and the term is not hit.
    ("0.5g of salt", _hits()),
    ("0.5g", _hits()),
    ("2.5G networks", _hits()),
    # A comma decimal.
    ("0,5g per day", _hits()),
    ("industry 4,0", _hits("I4")),
    ("GPT-3,5", _hits("G5")),
    # A mass written with a space: never a hit.
    ("0.5 g of salt", _hits()),
    # A chain.
    ("1.2.3 is a chain", _hits()),
    ("release v1.2.3 of the tool", _hits("AM")),
    ("v1.2.3", _hits("AM")),
    ("v1,2.3", _hits("AM")),
    ("v123", _hits()),
    ("v1.2.3.4", _hits()),
    ("v1.2 3", _hits()),
    ("1.2.3.4.5G", _hits()),
    # A term holding a decimal.
    ("Industry 4.0 and beyond", _hits("I4")),
    ("INDUSTRY 4.0", _hits("I4")),
    ("Industry 4.0.", _hits("I4")),
    ("industry 4 0", _hits()),
    ("the industry 40 years ago", _hits()),
    ("Industry 4.01", _hits()),
    ("Industry 4.0.1", _hits()),
    ("Society 5.0 in Japan", _hits("I4")),
    ("GPT-3.5 answers", _hits("G5")),
    ("GPT 35", _hits()),
    ("GPT-3 answers", _hits()),
    # A thousands separator.
    ("1,000 nodes and 5G", _hits("G5")),
    ("1,000 3D printers", _hits("AM")),
    ("1,000,000 devices", _hits()),
    ("1,3D printing", _hits()),
    # A sentence end after a number.
    ("in 2020. 5G arrives", _hits("G5")),
    ("Measured in 2020. Industry 4.0 followed.", _hits("I4")),
    ("It ended in 2020.", _hits()),
    # A number glued to a term by a comma, and the same with a space.
    ("in 2020,5G", _hits()),
    ("in 2020, 5G", _hits("G5")),
    # A dot that is not between two digits is a separator as before.
    ("3.D printing", _hits()),
    ("3D.printing", _hits("AM")),
    ("5.G", _hits()),
    # Digits outside ASCII do not hold a decimal together.
    ("5G ٣.٥", _hits("G5")),
    # A null, an empty string, and texts with no letter.
    (None, _hits()),
    ("", _hits()),
    ("...", _hits()),
    ("1.5", _hits()),
    # Several codes in one text.
    ("3D-printing at 0.5g", _hits("AM")),
    ("5G, Industry 4.0 and 3D printers", _hits("G5", "I4", "AM")),
    ("GPT-3.5, society 5,0, v1.2.3.", _hits("G5", "I4", "AM")),
]

PARITY_TEXTS = [text for text, _ in PARITY_FIXTURE]


@pytest.fixture(scope="module")
def parity_patterns():
    """Build the three fixture patterns with `code_pattern` and `decimal_whole=True`."""
    return {
        code: translate.code_pattern(terms, decimal_whole=True)
        for code, terms in PARITY_TERMS.items()
    }


def test_parity_patterns_are_the_ones_the_expectations_were_derived_from(parity_patterns):
    """The patterns built from `PARITY_TERMS` are exactly the ones written out by hand."""
    assert parity_patterns == PARITY_PATTERNS


def test_parity_fixture_has_the_kinds_of_text_the_contract_lists():
    """One text of each kind the amendment names, a null, an empty string, hits and misses."""
    for text in [
        "0.5g of salt",
        "0,5g per day",
        "1.2.3 is a chain",
        "Industry 4.0 and beyond",
        "1,000 nodes and 5G",
        "in 2020. 5G arrives",
    ]:
        assert text in PARITY_TEXTS, text
    assert PARITY_TEXTS.count(None) == 1
    assert PARITY_TEXTS.count("") == 1
    for code in PARITY_TERMS:
        flags = [expected[code] for _, expected in PARITY_FIXTURE]
        assert True in flags, code
        assert False in flags, code


@pytest.mark.parametrize("code", list(PARITY_TERMS))
def test_polars_decimal_whole_matches_the_fixture(parity_patterns, code):
    """`translate.matches` with the option gives the expected flag for every fixture text."""
    got = [
        translate.matches(parity_patterns[code], text, decimal_whole=True) for text in PARITY_TEXTS
    ]
    assert got == [expected[code] for _, expected in PARITY_FIXTURE]


def test_polars_flag_decimal_whole_matches_the_fixture(parity_patterns):
    """`translate.flag` over the fixture as a one-column frame equals the fixture."""
    frame = pl.DataFrame({"t": PARITY_TEXTS}, schema={"t": pl.String})
    out = translate.flag(frame, parity_patterns, ["t"], decimal_whole=True)
    for code in PARITY_TERMS:
        assert out[code].to_list() == [expected[code] for _, expected in PARITY_FIXTURE], code


# ==========================================================================
# Amendment 3: plural exceptions
# ==========================================================================

# --------------------------------------------------------------------------
# code_pattern
# --------------------------------------------------------------------------


# The four rows of the amendment's table (its `\|` is a plain `|`).
@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"plural_tolerant": True, "plural_exceptions": ["ai"]}, " (?:ai |iot(?:s|es)? )"),
        ({"plural_tolerant": True, "plural_exceptions": [" AI "]}, " (?:ai |iot(?:s|es)? )"),
        (
            {"plural_tolerant": True, "plural_exceptions": ["bert"]},
            " (?:ai(?:s|es)? |iot(?:s|es)? )",
        ),
        ({"plural_exceptions": ["ai"]}, " (?:ai |iot )"),
    ],
)
def test_code_pattern_plural_exceptions_contract_table(options, expected):
    """Each row of the amendment's table gives exactly the listed code pattern."""
    assert translate.code_pattern(["ai", "iot"], **options) == expected


# The three rows of the amendment's matching table.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AI systems", True),
        ("patients with AIS", False),
        ("IoTs at scale", True),
    ],
)
def test_matches_plural_exceptions_contract_table(text, expected):
    """Each row of the matching table gives exactly the listed Boolean."""
    pattern = translate.code_pattern(["ai", "iot"], plural_tolerant=True, plural_exceptions=["ai"])
    assert translate.matches(pattern, text) is expected


@pytest.mark.parametrize(
    ("text", "with_exception", "without_exception"),
    [
        ("AI systems", True, True),
        ("patients with AIS", False, True),
        ("AIes", False, True),
        ("IoTs at scale", True, True),
        ("the IoT", True, True),
        ("aisle", False, False),
        (None, False, False),
    ],
)
def test_matches_with_and_without_the_exception(text, with_exception, without_exception):
    """The exception removes the plural of `ai` and nothing else."""
    excepted = translate.code_pattern(["ai", "iot"], plural_tolerant=True, plural_exceptions=["ai"])
    tolerant = translate.code_pattern(["ai", "iot"], plural_tolerant=True)
    assert tolerant == " (?:ai(?:s|es)? |iot(?:s|es)? )"
    assert translate.matches(excepted, text) is with_exception
    assert translate.matches(tolerant, text) is without_exception


@pytest.mark.parametrize(
    "exception",
    ["ai", " AI ", "Ai", "AI", "\tai\n", "aI  "],
)
def test_code_pattern_exception_is_stripped_and_lower_cased(exception):
    """An exception is compared after stripping and lower-casing."""
    assert (
        translate.code_pattern(["ai", "iot"], plural_tolerant=True, plural_exceptions=[exception])
        == " (?:ai |iot(?:s|es)? )"
    )


@pytest.mark.parametrize(
    "exception",
    ["random forest", "Random   Forest", " random\tforest ", "RANDOM \n FOREST", "random  forest"],
)
def test_code_pattern_exception_has_its_inner_whitespace_collapsed(exception):
    """An exception is compared after collapsing its inner whitespace."""
    assert (
        translate.code_pattern(
            ["random forest", "smart city"], plural_tolerant=True, plural_exceptions=[exception]
        )
        == " (?:random forest |smart cit(?:y|ies) )"
    )


@pytest.mark.parametrize("term", ["ai", " AI ", "Ai", "AI"])
def test_code_pattern_term_is_stripped_and_lower_cased_for_the_comparison(term):
    """The term too is stripped and lower-cased before it is compared with an exception."""
    assert (
        translate.code_pattern([term, "iot"], plural_tolerant=True, plural_exceptions=["ai"])
        == " (?:ai |iot(?:s|es)? )"
    )


def test_code_pattern_term_has_its_inner_whitespace_collapsed_for_the_comparison():
    """A term written with two spaces is the exception written with one."""
    assert (
        translate.code_pattern(
            ["Random  Forest", "smart city"],
            plural_tolerant=True,
            plural_exceptions=["random forest"],
        )
        == " (?:random forest |smart cit(?:y|ies) )"
    )


def test_code_pattern_exception_on_a_y_term():
    """An excepted term ending in a consonant and `y` keeps its plain `y`."""
    assert (
        translate.code_pattern(
            ["smart city", "random forest"],
            plural_tolerant=True,
            plural_exceptions=["smart city"],
        )
        == " (?:smart city |random forest(?:s|es)? )"
    )


def test_code_pattern_several_exceptions():
    """Every term that is an exception is compiled without the plural group."""
    terms = ["ai", "iot", "smart city", "robot*", "5g"]
    assert (
        translate.code_pattern(terms, plural_tolerant=True, plural_exceptions=["5g", "ai"])
        == " (?:ai |iot(?:s|es)? |smart cit(?:y|ies) |robot[^ ]*|5g )"
    )
    assert (
        translate.code_pattern(
            terms, plural_tolerant=True, plural_exceptions=["ai", "iot", "smart city", "5g"]
        )
        == " (?:ai |iot |smart city |robot[^ ]*|5g )"
    )


def test_code_pattern_all_terms_excepted_equals_the_intolerant_pattern():
    """With every term an exception, the pattern is the one of `plural_tolerant=False`."""
    terms = ["ai", "iot", "smart city"]
    assert translate.code_pattern(
        terms, plural_tolerant=True, plural_exceptions=terms
    ) == translate.code_pattern(terms)
    assert translate.code_pattern(terms) == " (?:ai |iot |smart city )"


def test_code_pattern_exception_absent_from_the_terms_is_ignored():
    """An exception that is not among the terms given changes nothing and raises nothing."""
    tolerant = " (?:ai(?:s|es)? |iot(?:s|es)? )"
    for exceptions in (["bert"], ["bert", "gpt", "a i"], ["ais"], ["io"], ["ai*"]):
        assert (
            translate.code_pattern(
                ["ai", "iot"], plural_tolerant=True, plural_exceptions=exceptions
            )
            == tolerant
        ), exceptions
    assert (
        translate.code_pattern(
            ["ai", "iot"], plural_tolerant=True, plural_exceptions=["bert", "iot", "gpt"]
        )
        == " (?:ai(?:s|es)? |iot )"
    )


def test_code_pattern_exception_is_compared_as_a_string_not_as_a_pattern():
    """Only stripping, lower-casing and whitespace collapsing come before the comparison.

    `k means` and `k-means` compile to the same pattern but are two strings:
    the exception `k means` is not the term `k-means`, and is ignored.
    """
    assert (
        translate.code_pattern(["k-means"], plural_tolerant=True, plural_exceptions=["k means"])
        == " (?:k means(?:s|es)? )"
    )
    assert (
        translate.code_pattern(["k-means"], plural_tolerant=True, plural_exceptions=["K-Means"])
        == " (?:k means )"
    )


def test_code_pattern_exception_on_a_term_the_plural_rule_leaves_alone():
    """An exception that names a truncated term or one ending in a digit changes nothing."""
    terms = ["robot*", "industry 4.0", "iot"]
    assert (
        translate.code_pattern(
            terms, plural_tolerant=True, plural_exceptions=["robot*", "industry 4.0"]
        )
        == " (?:robot[^ ]*|industry 4 0 |iot(?:s|es)? )"
    )


@pytest.mark.parametrize(
    "exceptions",
    [["ai"], ("ai",), {"ai"}, frozenset({"ai"}), ["ai", "ai"], ["ai", " AI ", "bert"]],
)
def test_code_pattern_accepts_any_collection_of_exceptions(exceptions):
    """A list, a tuple, a set or a frozenset, with or without repeats, all work alike."""
    assert (
        translate.code_pattern(["ai", "iot"], plural_tolerant=True, plural_exceptions=exceptions)
        == " (?:ai |iot(?:s|es)? )"
    )


@pytest.mark.parametrize(
    "exceptions", [["ai"], [" AI "], ["bert"], ["ai", "iot"], ["smart city"], ()]
)
def test_code_pattern_exceptions_change_nothing_without_plural_tolerant(exceptions):
    """With `plural_tolerant` False, by default or given, the exceptions change nothing."""
    terms = ["ai", "iot", "smart city", "robot*"]
    expected = " (?:ai |iot |smart city |robot[^ ]*)"
    assert translate.code_pattern(terms, plural_exceptions=exceptions) == expected
    assert (
        translate.code_pattern(terms, plural_tolerant=False, plural_exceptions=exceptions)
        == expected
    )


def test_code_pattern_exceptions_combine_with_the_other_options():
    """Exceptions with `hyphen_closed_form` and `decimal_whole`: only the plural is withheld."""
    terms = ["society 5.0", "gpt-3.5 model", "5g", "k-means"]
    assert (
        translate.code_pattern(
            terms,
            hyphen_closed_form=True,
            plural_tolerant=True,
            decimal_whole=True,
            plural_exceptions=["5g", "k-means"],
        )
        == " (?:society 5p0 |gpt ?3p5 model(?:s|es)? |5g |k ?means )"
    )
    assert (
        translate.code_pattern(
            terms, hyphen_closed_form=True, plural_tolerant=True, decimal_whole=True
        )
        == " (?:society 5p0 |gpt ?3p5 model(?:s|es)? |5g(?:s|es)? |k ?means(?:s|es)? )"
    )


def test_code_pattern_of_no_term_with_exceptions_raises():
    """An empty sequence of terms still raises `QueryError`, whatever the exceptions."""
    with pytest.raises(QueryError):
        translate.code_pattern([], plural_tolerant=True, plural_exceptions=["ai"])


# --------------------------------------------------------------------------
# compile_queries
# --------------------------------------------------------------------------

ONE_TEXT = 'TS = ( ("AI") OR ("IoT") OR ("smart city") )'
TWO_TEXT = '( ("Robot*") OR ("big  data") OR ("5G") OR ("industry 4.0") OR ("gpt-3.5") )'

ONE_TERMS = ["ai", "iot", "smart city"]
TWO_TERMS = ["robot*", "big data", "5g", "industry 4.0", "gpt-3.5"]


@pytest.fixture
def two_files(tmp_path):
    """Write two hand-made query files and return the mapping from code to file."""
    one = _write(tmp_path / "one.txt", ONE_TEXT)
    two = _write(tmp_path / "sub" / "two.txt", TWO_TEXT)
    return {"AA": one, "ZZ": two}


def _definitions(pattern_one, pattern_two):
    """Return the two definitions of the hand-made files with the patterns given."""
    return [
        {
            "code": "AA",
            "source": "one.txt",
            "term_count": 3,
            "terms": ONE_TERMS,
            "pattern": pattern_one,
        },
        {
            "code": "ZZ",
            "source": "two.txt",
            "term_count": 5,
            "terms": TWO_TERMS,
            "pattern": pattern_two,
        },
    ]


def test_compile_queries_neither_option(two_files):
    """Combination 1 of 4: the defaults give the five keys and the patterns as before."""
    out = translate.compile_queries(two_files)
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION,
        "hyphen_closed_form": False,
        "plural_tolerant": False,
        "definitions": _definitions(
            " (?:ai |iot |smart city )",
            " (?:robot[^ ]*|big data |5g |industry 4 0 |gpt 3 5 )",
        ),
    }
    assert list(out) == KEYS_DEFAULT
    assert "decimal_whole" not in out
    assert "plural_exceptions" not in out


def test_compile_queries_decimal_whole_only(two_files):
    """Combination 2 of 4: `decimal_whole` after `plural_tolerant`, and its normalisation."""
    out = translate.compile_queries(two_files, decimal_whole=True)
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION_DECIMAL,
        "hyphen_closed_form": False,
        "plural_tolerant": False,
        "decimal_whole": True,
        "definitions": _definitions(
            " (?:ai |iot |smart city )",
            " (?:robot[^ ]*|big data |5g |industry 4p0 |gpt 3p5 )",
        ),
    }
    assert list(out) == KEYS_DECIMAL
    assert out["decimal_whole"] is True
    assert "plural_exceptions" not in out


def test_compile_queries_plural_exceptions_only(two_files):
    """Combination 3 of 4: `plural_exceptions` after `plural_tolerant`, base normalisation."""
    out = translate.compile_queries(two_files, plural_tolerant=True, plural_exceptions=["ai"])
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION,
        "hyphen_closed_form": False,
        "plural_tolerant": True,
        "plural_exceptions": ["ai"],
        "definitions": _definitions(
            " (?:ai |iot(?:s|es)? |smart cit(?:y|ies) )",
            " (?:robot[^ ]*|big data(?:s|es)? |5g(?:s|es)? |industry 4 0 |gpt 3 5 )",
        ),
    }
    assert list(out) == KEYS_EXCEPTIONS
    assert "decimal_whole" not in out


def test_compile_queries_both_options(two_files):
    """Combination 4 of 4: `decimal_whole` then `plural_exceptions`, `definitions` last."""
    out = translate.compile_queries(
        two_files,
        hyphen_closed_form=True,
        plural_tolerant=True,
        decimal_whole=True,
        plural_exceptions=["ai", "5g"],
    )
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION_DECIMAL,
        "hyphen_closed_form": True,
        "plural_tolerant": True,
        "decimal_whole": True,
        "plural_exceptions": ["ai", "5g"],
        "definitions": _definitions(
            " (?:ai |iot(?:s|es)? |smart cit(?:y|ies) )",
            " (?:robot[^ ]*|big data(?:s|es)? |5g |industry 4p0 |gpt ?3p5 )",
        ),
    }
    assert list(out) == KEYS_BOTH
    assert list(out)[-1] == "definitions"
    assert out["version"] == 1


def test_compile_queries_normalisation_string_with_decimal_whole(two_files):
    """The exact `normalisation` value, and its JSON form with doubled backslashes."""
    out = translate.compile_queries(two_files, decimal_whole=True)
    assert out["normalisation"] == (
        "lower-case; a dot or comma between two ASCII digits becomes the letter p; "
        "every run of characters outside \\p{L}\\p{N} becomes one space; "
        "trimmed; one space added at each end"
    )
    assert json.dumps(out["normalisation"]) == (
        '"lower-case; a dot or comma between two ASCII digits becomes the letter p; '
        "every run of characters outside \\\\p{L}\\\\p{N} becomes one space; "
        'trimmed; one space added at each end"'
    )


def test_compile_queries_decimal_whole_false_writes_no_key(two_files):
    """`decimal_whole=False` given explicitly writes no key and the base normalisation."""
    out = translate.compile_queries(two_files, decimal_whole=False)
    assert list(out) == KEYS_DEFAULT
    assert out["normalisation"] == NORMALISATION


@pytest.mark.parametrize("empty", [(), [], set(), frozenset()])
def test_compile_queries_empty_exceptions_write_no_key(two_files, empty):
    """An empty collection of exceptions writes no key, tolerant or not."""
    assert list(translate.compile_queries(two_files, plural_exceptions=empty)) == KEYS_DEFAULT
    out = translate.compile_queries(two_files, plural_tolerant=True, plural_exceptions=empty)
    assert list(out) == KEYS_DEFAULT
    assert out == translate.compile_queries(two_files, plural_tolerant=True)


def test_compile_queries_defaults_given_explicitly_change_nothing(two_files):
    """An artefact compiled with the defaults equals one with every option at its default."""
    implicit = translate.compile_queries(two_files)
    explicit = translate.compile_queries(
        two_files,
        hyphen_closed_form=False,
        plural_tolerant=False,
        decimal_whole=False,
        plural_exceptions=(),
    )
    assert explicit == implicit
    assert list(explicit) == list(implicit) == KEYS_DEFAULT
    assert json.dumps(explicit) == json.dumps(implicit)


def test_compile_queries_exceptions_are_written_as_compared(two_files):
    """The key holds the exceptions stripped, lower-cased and with whitespace collapsed."""
    out = translate.compile_queries(
        two_files, plural_tolerant=True, plural_exceptions=[" AI ", "Big   Data", "SMART\tCITY"]
    )
    assert out["plural_exceptions"] == ["ai", "big data", "smart city"]
    assert out["definitions"] == _definitions(
        " (?:ai |iot(?:s|es)? |smart city )",
        " (?:robot[^ ]*|big data |5g(?:s|es)? |industry 4 0 |gpt 3 5 )",
    )


def test_compile_queries_exceptions_keep_the_order_given_and_drop_repeats(two_files):
    """The order given is kept, not sorted; a repeat keeps its first place."""
    out = translate.compile_queries(
        two_files,
        plural_tolerant=True,
        plural_exceptions=[" Big  Data", "AI", "big data", "ai ", "5G", "Ai", "5g"],
    )
    assert out["plural_exceptions"] == ["big data", "ai", "5g"]
    assert type(out["plural_exceptions"]) is list
    assert list(out) == KEYS_EXCEPTIONS


def test_compile_queries_exceptions_given_as_a_tuple_are_written_as_a_list(two_files):
    """Whatever the collection, the artefact is plain data: a list of `str`."""
    out = translate.compile_queries(
        two_files, plural_tolerant=True, plural_exceptions=("smart city", "ai")
    )
    assert out["plural_exceptions"] == ["smart city", "ai"]
    assert type(out["plural_exceptions"]) is list
    assert [type(item) for item in out["plural_exceptions"]] == [str, str]


def test_compile_queries_an_exception_may_be_a_term_of_any_file(two_files):
    """The list is shared by all codes: each exception acts in the file that has the term."""
    out = translate.compile_queries(
        two_files, plural_tolerant=True, plural_exceptions=["5g", "iot"]
    )
    assert out["plural_exceptions"] == ["5g", "iot"]
    assert out["definitions"] == _definitions(
        " (?:ai(?:s|es)? |iot |smart cit(?:y|ies) )",
        " (?:robot[^ ]*|big data(?:s|es)? |5g |industry 4 0 |gpt 3 5 )",
    )


@pytest.mark.parametrize("plural_tolerant", [True, False])
@pytest.mark.parametrize(
    "exceptions",
    [
        ["bert"],
        ["ai", "bert"],
        ["bert", "ai"],
        # Misspellings of terms of the files.
        ["a i"],
        ["iots"],
        ["robot"],
        ["bigdata"],
        ["smart cities"],
        ["industry 4 0"],
    ],
)
def test_compile_queries_exception_of_no_file_raises(two_files, plural_tolerant, exceptions):
    """An exception that is a term of none of the files raises, tolerant or not."""
    with pytest.raises(QueryError):
        translate.compile_queries(
            two_files, plural_tolerant=plural_tolerant, plural_exceptions=exceptions
        )


@pytest.mark.parametrize("plural_tolerant", [True, False])
def test_compile_queries_exception_of_no_file_raises_with_decimal_whole(two_files, plural_tolerant):
    """The check does not depend on the other options."""
    with pytest.raises(QueryError):
        translate.compile_queries(
            two_files,
            hyphen_closed_form=True,
            plural_tolerant=plural_tolerant,
            decimal_whole=True,
            plural_exceptions=["bert"],
        )


def test_compile_queries_exceptions_without_plural_tolerant_change_no_pattern(two_files):
    """With `plural_tolerant` False the patterns are the default ones; the key is written.

    The amendment writes the key "when the collection is not empty", with no
    condition on `plural_tolerant`.
    """
    out = translate.compile_queries(two_files, plural_exceptions=["ai", "5g"])
    default = translate.compile_queries(two_files)
    assert out["definitions"] == default["definitions"]
    assert out["plural_tolerant"] is False
    assert out["plural_exceptions"] == ["ai", "5g"]
    assert list(out) == KEYS_EXCEPTIONS


def test_compile_queries_artefacts_with_the_options_survive_json(two_files):
    """The artefact is plain data: JSON gives it back, keys in the same order."""
    out = translate.compile_queries(
        two_files, plural_tolerant=True, decimal_whole=True, plural_exceptions=["ai"]
    )
    back = json.loads(json.dumps(out))
    assert back == out
    assert list(back) == KEYS_BOTH


def test_compile_queries_still_stops_on_a_bad_term_with_the_options(tmp_path):
    """A term that cannot be compiled raises `QueryError` with the options on too."""
    bad = _write(tmp_path / "bad.txt", 'TS = ( ("robot*") OR ("colo?r") )')
    with pytest.raises(QueryError):
        translate.compile_queries({"BAD": bad}, decimal_whole=True)
    with pytest.raises(QueryError):
        translate.compile_queries({"BAD": bad}, plural_tolerant=True, plural_exceptions=["robot*"])


# --------------------------------------------------------------------------
# The real query files
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_default():
    """Compile the six real query files with the defaults."""
    return translate.compile_queries(QUERY_FILES)


def test_real_default_artefact_equals_the_defaults_given_explicitly(real_default):
    """On the real files too, the explicit defaults give the same artefact, key for key."""
    explicit = translate.compile_queries(
        QUERY_FILES,
        hyphen_closed_form=False,
        plural_tolerant=False,
        decimal_whole=False,
        plural_exceptions=(),
    )
    assert explicit == real_default
    assert list(explicit) == list(real_default) == KEYS_DEFAULT
    assert json.dumps(explicit) == json.dumps(real_default)
    assert real_default["normalisation"] == NORMALISATION
    assert real_default["version"] == 1


def test_real_decimal_artefact_top_level_and_patterns(real_default):
    """With the option: six keys, the decimal normalisation, same terms, recompiled patterns."""
    out = translate.compile_queries(QUERY_FILES, decimal_whole=True)
    assert list(out) == KEYS_DECIMAL
    assert out["version"] == 1
    assert out["normalisation"] == NORMALISATION_DECIMAL
    assert out["hyphen_closed_form"] is False
    assert out["plural_tolerant"] is False
    assert out["decimal_whole"] is True
    assert [d["code"] for d in out["definitions"]] == ["AI", "IOT", "CI", "BL", "ROB", "AM"]
    for whole, default in zip(out["definitions"], real_default["definitions"], strict=True):
        assert whole["terms"] == default["terms"], whole["code"]
        assert whole["term_count"] == default["term_count"], whole["code"]
        assert whole["source"] == default["source"], whole["code"]
        assert whole["pattern"] == translate.code_pattern(whole["terms"], decimal_whole=True)


@pytest.mark.parametrize("plural_tolerant", [True, False])
def test_real_files_exception_of_no_file_raises(plural_tolerant):
    """A string that is a term of none of the six real files raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.compile_queries(
            QUERY_FILES,
            plural_tolerant=plural_tolerant,
            plural_exceptions=["no such term in any file 12345"],
        )


# ==========================================================================
# Defaults are unchanged
# ==========================================================================

DEFAULT_CODE_ROWS = [
    (["bitcoin", "blockchain*"], {}, " (?:bitcoin |blockchain[^ ]*)"),
    (["5g", "industry 4.0"], {}, " (?:5g |industry 4 0 )"),
    (["ai", "iot"], {}, " (?:ai |iot )"),
    (["ai", "iot"], {"plural_tolerant": True}, " (?:ai(?:s|es)? |iot(?:s|es)? )"),
    (["k-means", "gpt-3.5"], {"hyphen_closed_form": True}, " (?:k ?means |gpt ?3 5 )"),
    (
        ["random forest", "smart city"],
        {"plural_tolerant": True},
        " (?:random forest(?:s|es)? |smart cit(?:y|ies) )",
    ),
]


@pytest.mark.parametrize(("terms", "options", "expected"), DEFAULT_CODE_ROWS)
def test_code_pattern_default_is_unchanged(terms, options, expected):
    """Without the new keywords, and with them at their defaults, the pattern is what it was."""
    assert translate.code_pattern(terms, **options) == expected
    assert translate.code_pattern(terms, decimal_whole=False, **options) == expected
    assert translate.code_pattern(terms, plural_exceptions=(), **options) == expected
    assert (
        translate.code_pattern(terms, decimal_whole=False, plural_exceptions=[], **options)
        == expected
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.5g per day", True),
        ("a 5G network", True),
        ("Industry 4.0 and beyond", True),
        ("industry 4 0", True),
        ("the industry 40 years ago", False),
        ("patients with AIS", False),
        ("AI systems", False),
        (None, False),
        ("", False),
    ],
)
def test_matches_default_is_unchanged(text, expected):
    """Default pattern on default text, with the arguments absent and at their defaults."""
    plain = translate.code_pattern(["5g", "industry 4.0"])
    explicit = translate.code_pattern(
        ["5g", "industry 4.0"], decimal_whole=False, plural_exceptions=()
    )
    assert plain == explicit == " (?:5g |industry 4 0 )"
    assert translate.matches(plain, text) is expected
    assert translate.matches(explicit, text, decimal_whole=False) is expected


def test_flag_default_contract_example_is_unchanged():
    """The base contract's `flag` example, with the keyword absent and with it False."""
    frame = pl.DataFrame(
        {
            "title": ["Deep learning for robots", "Blockchain", None],
            "abstract": [None, "We use machine", "learning"],
        },
        schema={"title": pl.String, "abstract": pl.String},
    )
    patterns = {
        "AI": translate.code_pattern(["machine learning", "deep learning"]),
        "ROB": translate.code_pattern(["robot*"]),
    }
    expected = frame.with_columns(
        pl.Series("AI", [True, False, False], dtype=pl.Boolean),
        pl.Series("ROB", [True, False, False], dtype=pl.Boolean),
    )
    assert_frame_equal(translate.flag(frame, patterns, ["title", "abstract"]), expected)
    assert_frame_equal(
        translate.flag(frame, patterns, ["title", "abstract"], decimal_whole=False), expected
    )
