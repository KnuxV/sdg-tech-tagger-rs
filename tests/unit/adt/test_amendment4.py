"""Tests of Amendment 4 of the query translation contract, from the contract alone.

Source of every expected value: `docs/query-translation-contract.md`, section
"Amendment 4, 2026-10-08: a decimal separator becomes a marker, not nothing".
With `decimal_whole=True`, a `.` or `,` between two ASCII digits becomes the
lower-case letter `p`; it is no longer deleted. Every expected string was
derived by hand from that rule; the spaces at the ends of normalised texts and
of patterns are part of the values.

`test_amendment3.py` holds the tests of Amendment 3, with their expectations
of the decimal rule moved to the marker. This file holds what Amendment 4
states on its own:

- the three tables (normalisation, term patterns, matching), one test per row;
- the SQL strings in both dialects and the marker in `render_adt_flags`;
- the artefact's `normalisation` string;
- engine parity (Polars against DuckDB on RE2) on a fixture that holds the two
  kinds of text the amendment adds;
- the behaviours it lists as known and accepted, and the entry it withdraws.

The texts go into DuckDB through bound parameters, so a null stays a null.
"""

import json

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from sdg_tech_tagger.adt import translate

# The value of the artefact's "normalisation" key with `decimal_whole`, as
# Amendment 4 gives it (in the contract's JSON the backslashes are doubled),
# and the value Amendment 3 gave, which must no longer be written.
NORMALISATION_MARKER = (
    "lower-case; a dot or comma between two ASCII digits becomes the letter p; "
    r"every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)
NORMALISATION_AMENDMENT_3 = (
    "lower-case; a dot or comma between two ASCII digits is removed; "
    r"every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)

KEYS_DECIMAL = [
    "version",
    "normalisation",
    "hyphen_closed_form",
    "plural_tolerant",
    "decimal_whole",
    "definitions",
]

# The DuckDB form with `decimal_whole`, as the amendment's code block gives it.

# The BigQuery form: no `, 'g'`, the patterns and `\1p\2` as raw literals, the
# replacement `' '` a plain literal.


def _write(path, text):
    """Write a hand-made query file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ==========================================================================
# On text
# ==========================================================================

# (input, output with `decimal_whole=True`, output with the default). The
# first two columns are the amendment's table, row for row, fifteen rows. The
# third is derived from the five steps of the base normalisation.
MARKER_TABLE = [
    ("0.5g of salt", " 0p5g of salt ", " 0 5g of salt "),
    ("0,5g", " 0p5g ", " 0 5g "),
    ("5G networks", " 5g networks ", " 5g networks "),
    ("beyond-5G (5G)", " beyond 5g 5g ", " beyond 5g 5g "),
    ("Industry 4.0", " industry 4p0 ", " industry 4 0 "),
    ("Industry 4.0.", " industry 4p0 ", " industry 4 0 "),
    ("1,000 nodes", " 1p000 nodes ", " 1 000 nodes "),
    ("v1.2.3", " v1p2p3 ", " v1 2 3 "),
    ("1.2.3.4.5", " 1p2p3p4p5 ", " 1 2 3 4 5 "),
    ("in 2020. 5G", " in 2020 5g ", " in 2020 5g "),
    ("industry. 40 firms", " industry 40 firms ", " industry 40 firms "),
    ("3.5 g", " 3p5 g ", " 3 5 g "),
    ("a.5", " a 5 ", " a 5 "),
    ("GPT-3.5", " gpt 3p5 ", " gpt 3 5 "),
    (None, "  ", "  "),
]

# Further cases that follow from the rule: one `.` or `,` standing between two
# ASCII digits becomes `p`; everything else is as before.
MARKER_DERIVED = [
    # The dot and the comma give the same marker: the same word.
    ("4.0", " 4p0 ", " 4 0 "),
    ("4,0", " 4p0 ", " 4 0 "),
    # The marker is the lower-case letter, whatever the case of the text.
    ("INDUSTRY 4.0", " industry 4p0 ", " industry 4 0 "),
    # A text that already holds the letter, in either case, is the same word.
    ("industry 4p0", " industry 4p0 ", " industry 4p0 "),
    ("Industry 4P0", " industry 4p0 ", " industry 4p0 "),
    # Two passes: the second separator of a chain is reached, with a letter
    # already standing where the first one was.
    ("1.2.3", " 1p2p3 ", " 1 2 3 "),
    ("1,2,3,4", " 1p2p3p4 ", " 1 2 3 4 "),
    ("1p2.3", " 1p2p3 ", " 1p2 3 "),
    # The marker does not make a neighbour a digit: `p.5` has no digit on its left.
    ("1.5p.5", " 1p5p 5 ", " 1 5p 5 "),
    # The texts of the third check of the extended query: nothing stands between two digits.
    ("textile industry. 40 firms", " textile industry 40 firms ", " textile industry 40 firms "),
    ("in industry, 40% of plants", " in industry 40 of plants ", " in industry 40 of plants "),
    # A sentence end glued to the next number is a decimal to the rule.
    ("industry.40 firms", " industry 40 firms ", " industry 40 firms "),
    ("in 2020.5G", " in 2020p5g ", " in 2020 5g "),
    ("in 2020,5G", " in 2020p5g ", " in 2020 5g "),
    # A percentage and a mass.
    ("40.5% of plants", " 40p5 of plants ", " 40 5 of plants "),
    ("5g of soil", " 5g of soil ", " 5g of soil "),
    ("0.5 g", " 0p5 g ", " 0 5 g "),
    ("", "  ", "  "),
]

MARKER_ALL = MARKER_TABLE + MARKER_DERIVED


def test_marker_table_has_the_fifteen_rows_of_the_amendment():
    """A guard on this file: the table has as many rows as the amendment's."""
    assert len(MARKER_TABLE) == 15
    assert all(len(row) == 3 for row in MARKER_ALL)


@pytest.mark.parametrize(("text", "expected"), [(t, e) for t, e, _ in MARKER_TABLE])
def test_normalise_marker_contract_table(text, expected):
    """Each row of the amendment's normalisation table gives exactly the listed string."""
    assert translate.normalise(text, decimal_whole=True) == expected


@pytest.mark.parametrize(("text", "expected"), [(t, e) for t, e, _ in MARKER_DERIVED])
def test_normalise_marker_derived_cases(text, expected):
    """Cases derived from the marker rule give exactly the expected string."""
    assert translate.normalise(text, decimal_whole=True) == expected


@pytest.mark.parametrize(("text", "expected"), [(t, d) for t, _, d in MARKER_ALL])
def test_normalise_default_is_unchanged_on_the_same_inputs(text, expected):
    """With the default nothing changes at all: the five base steps and nothing else."""
    assert translate.normalise(text) == expected
    assert translate.normalise(text, decimal_whole=False) == expected


def test_normalise_expr_marker_contract_table():
    """`normalise_expr` over a column gives the table's outputs, row for row, never null."""
    frame = pl.DataFrame({"t": [text for text, _, _ in MARKER_ALL]}, schema={"t": pl.String})
    out = frame.select(translate.normalise_expr(pl.col("t"), decimal_whole=True)).to_series()
    assert out.dtype == pl.String
    assert out.null_count() == 0
    assert out.to_list() == [expected for _, expected, _ in MARKER_ALL]


@pytest.mark.parametrize(
    ("with_dot", "with_comma"),
    [
        ("Industry 4.0", "Industry 4,0"),
        ("0.5g", "0,5g"),
        ("v1.2.3", "v1,2,3"),
        ("v1.2.3", "v1,2.3"),
        ("1.000 nodes", "1,000 nodes"),
    ],
)
def test_normalise_dot_and_comma_give_the_same_word(with_dot, with_comma):
    """The dot and the comma give the same marker, so the two spellings are one text."""
    assert translate.normalise(with_dot, decimal_whole=True) == translate.normalise(
        with_comma, decimal_whole=True
    )
    assert "p" in translate.normalise(with_dot, decimal_whole=True)


@pytest.mark.parametrize(
    ("text", "amendment_3"),
    [
        ("0.5g of salt", " 05g of salt "),
        ("Industry 4.0", " industry 40 "),
        ("1,000 nodes", " 1000 nodes "),
        ("v1.2.3", " v123 "),
        ("GPT-3.5", " gpt 35 "),
    ],
)
def test_normalise_no_longer_deletes_the_separator(text, amendment_3):
    """What Amendment 3 gave for these texts is no longer the output."""
    assert translate.normalise(text, decimal_whole=True) != amendment_3


# ==========================================================================
# On terms
# ==========================================================================


# The eight rows of the amendment's term table.
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
        ("3.5*", {"decimal_whole": True}, "3p5[^ ]*"),
    ],
)
def test_term_pattern_marker_contract_table(term, options, expected):
    """Each row of the amendment's term table gives exactly the listed regex."""
    assert translate.term_pattern(term, **options) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        # A last word ending in a digit takes no plural, marker or not.
        ("society 5.0", "society 5p0 "),
        ("industry 4.0", "industry 4p0 "),
        ("4,0", "4p0 "),
        ("gpt-3", "gpt 3 "),
        ("3.5*", "3p5[^ ]*"),
        # The marker is not the last letter of the word, so it brings no plural.
        ("v1.2.3", "v1p2p3 "),
        # A last word ending in a letter still gets its group.
        ("5g", "5g(?:s|es)? "),
        ("web 2.0 app", "web 2p0 app(?:s|es)? "),
    ],
)
def test_term_pattern_marker_with_plural_tolerant(term, expected):
    """A term whose last word ends with a digit still takes no plural."""
    assert translate.term_pattern(term, decimal_whole=True, plural_tolerant=True) == expected


@pytest.mark.parametrize(
    ("with_dot", "with_comma"),
    [("industry 4.0", "industry 4,0"), ("gpt-3.5", "gpt-3,5"), ("v1.2.3", "v1,2,3")],
)
def test_term_pattern_dot_and_comma_give_the_same_pattern(with_dot, with_comma):
    """On terms too the dot and the comma give the same marker."""
    assert translate.term_pattern(with_dot, decimal_whole=True) == translate.term_pattern(
        with_comma, decimal_whole=True
    )


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        # The marker comes after lower-casing and is itself lower-case.
        ("INDUSTRY 4.0", "industry 4p0 "),
        # A term written with the marker is the term written with the decimal.
        ("industry 4p0", "industry 4p0 "),
        # No digit on both sides: a separator as before, no marker.
        ("a.5", "a 5 "),
        ("4. 0", "4 0 "),
        ("4..0", "4 0 "),
        ("industry 4.0.", "industry 4p0 "),
        # A chain needs the second pass.
        ("1.2.3.4.5", "1p2p3p4p5 "),
    ],
)
def test_term_pattern_marker_derived_cases(term, expected):
    """Further terms, each compiled by hand after marking the separators between digits."""
    assert translate.term_pattern(term, decimal_whole=True) == expected


@pytest.mark.parametrize(
    ("term", "amendment_3"),
    [
        ("industry 4.0", "industry 40 "),
        ("i4.0", "i40 "),
        ("gpt-3.5", "gpt 35 "),
        ("3.5*", "35[^ ]*"),
    ],
)
def test_term_pattern_no_longer_deletes_the_separator(term, amendment_3):
    """What Amendment 3 gave for these terms is no longer the pattern."""
    assert translate.term_pattern(term, decimal_whole=True) != amendment_3


def test_term_pattern_with_the_marker_stays_in_the_pattern_alphabet():
    """The marker is a plain letter: no quote, no backslash, no new construct."""
    pattern = translate.code_pattern(
        ["industry 4.0", "gpt-3.5", "3.5*", "v1,2.3"], decimal_whole=True
    )
    assert pattern == " (?:industry 4p0 |gpt 3p5 |3p5[^ ]*|v1p2p3 )"
    assert "'" not in pattern
    assert '"' not in pattern
    assert "\\" not in pattern
    assert "." not in pattern
    assert "," not in pattern


# ==========================================================================
# Matching
# ==========================================================================

MATCH_TERMS = ["5g", "industry 4.0", "gpt-3"]
MATCH_PATTERN = " (?:5g |industry 4p0 |gpt 3 )"


def test_code_pattern_of_the_matching_example():
    """The pattern the amendment's matching table is built on, written out by hand."""
    assert translate.code_pattern(MATCH_TERMS, decimal_whole=True) == MATCH_PATTERN


# The sixteen rows of the amendment's matching table.
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
        ("the rise of Industry 4.0.", True),
        ("industry 4,0", True),
        ("industry 4 0", False),
        ("the industry 40 years ago", False),
        ("in the textile industry. 40 firms were surveyed", False),
        ("in industry, 40% of plants", False),
        ("GPT-3 was prompted", True),
        ("GPT-3.5 was prompted", False),
        ("industry 4p0", True),
    ],
)
def test_matches_marker_contract_table(text, expected):
    """Each row of the amendment's matching table gives exactly the listed Boolean."""
    pattern = translate.code_pattern(MATCH_TERMS, decimal_whole=True)
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
        # The two texts of finding 4.1, as the amendment's "Why" quotes them.
        ("in the textile industry. 40 firms", False),
        ("in industry, 40% of plants", False),
        # The two texts of the parity paragraph.
        ("industry. 40 firms", False),
        ("in industry, 40% of", False),
        # Variants of the same accident: a full stop, a comma, a space.
        ("Industry. 40 firms", False),
        ("industry 40", False),
        ("industry, 40", False),
        ("industry 40.", False),
        ("industry 40%", False),
        # The term itself, with either separator, at a sentence end, in capitals.
        ("Industry 4.0.", True),
        ("INDUSTRY 4,0", True),
        ("industry 4.0, then", True),
        ("Industry 4P0", True),
        # One digit more or one separator more is another word.
        ("industry 4.01", False),
        ("industry 4.0.1", False),
        ("industry 14.0", False),
        ("industry 4. 0", False),
        ("industry 4p", False),
        ("", False),
        (None, False),
    ],
)
def test_matches_marker_derived_cases(text, expected):
    """Further texts, each derived by normalising by hand and searching the pattern."""
    assert translate.matches(MATCH_PATTERN, text, decimal_whole=True) is expected


def test_matches_marker_returns_a_python_bool():
    """With the option `matches` still produces a `bool`."""
    assert type(translate.matches(MATCH_PATTERN, "Industry 4.0", decimal_whole=True)) is bool
    assert type(translate.matches(MATCH_PATTERN, None, decimal_whole=True)) is bool


# --------------------------------------------------------------------------
# Known and accepted, and the withdrawn entry
# --------------------------------------------------------------------------


def test_accepted_term_followed_by_a_decimal_fraction_does_not_match():
    """`gpt-3` does not match "GPT-3.5"; the decimal form is listed as its own term."""
    bare = translate.code_pattern(["gpt-3"], decimal_whole=True)
    assert bare == " (?:gpt 3 )"
    assert translate.normalise("GPT-3.5", decimal_whole=True) == " gpt 3p5 "
    assert translate.matches(bare, "GPT-3.5", decimal_whole=True) is False
    assert translate.matches(bare, "GPT-3", decimal_whole=True) is True
    listed = translate.code_pattern(["gpt-3", "gpt-3.5"], decimal_whole=True)
    assert listed == " (?:gpt 3 |gpt 3p5 )"
    assert translate.matches(listed, "GPT-3.5", decimal_whole=True) is True
    assert translate.matches(listed, "GPT-3,5", decimal_whole=True) is True
    assert translate.matches(listed, "GPT-3", decimal_whole=True) is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # A mass written with a space never matched `5g`.
        ("0.5 g", False),
        ("0.5 g of soil", False),
        # A whole-number mass matches: the rule is about decimals only.
        ("5g of soil", True),
        ("add 5g of soil", True),
        ("5 g of soil", False),
        # A decimal mass is one word and does not match.
        ("0.5g of soil", False),
        ("0,5g of soil", False),
    ],
)
def test_accepted_masses(text, expected):
    """A mass with a space never matched; a whole-number mass matches `5g`."""
    pattern = translate.code_pattern(["5g"], decimal_whole=True)
    assert pattern == " (?:5g )"
    assert translate.matches(pattern, text, decimal_whole=True) is expected


def test_accepted_number_glued_to_a_term_by_a_comma():
    """ "in 2020,5G" becomes the one word `2020p5g` and the term is missed."""
    pattern = translate.code_pattern(["5g"], decimal_whole=True)
    assert translate.normalise("in 2020,5G", decimal_whole=True) == " in 2020p5g "
    assert translate.matches(pattern, "in 2020,5G", decimal_whole=True) is False
    assert translate.matches(pattern, "in 2020, 5G", decimal_whole=True) is True
    # Without the option the comma is a separator and the term is found.
    assert translate.matches(translate.code_pattern(["5g"]), "in 2020,5G") is True


def test_accepted_text_that_holds_the_marker_itself():
    """A text that holds the marker itself, "industry 4p0", matches."""
    pattern = translate.code_pattern(["industry 4.0"], decimal_whole=True)
    assert pattern == " (?:industry 4p0 )"
    assert translate.matches(pattern, "industry 4p0", decimal_whole=True) is True
    assert translate.matches(pattern, "the Industry 4P0 era", decimal_whole=True) is True
    # Only after the word, and only as that word.
    assert translate.matches(pattern, "industry 4p01", decimal_whole=True) is False
    assert translate.matches(pattern, "4p0 industry", decimal_whole=True) is False


@pytest.mark.parametrize(
    "text",
    [
        "the industry 40 years ago",
        "The industry 40 years ago",
        "the industry 40 years ago.",
        "industry 40",
    ],
)
def test_withdrawn_industry_40_no_longer_matches(text):
    """The entry of Amendment 3's list is withdrawn: `industry 4.0` does not match "40"."""
    pattern = translate.code_pattern(["industry 4.0"], decimal_whole=True)
    assert pattern == " (?:industry 4p0 )"
    assert translate.matches(pattern, text, decimal_whole=True) is False


def test_withdrawn_industry_40_did_not_match_by_default_either():
    """With the default the text never matched: the two settings now agree on it."""
    plain = translate.code_pattern(["industry 4.0"])
    assert plain == " (?:industry 4 0 )"
    assert translate.matches(plain, "the industry 40 years ago") is False


# --------------------------------------------------------------------------
# Flagging a table
# --------------------------------------------------------------------------


def _marker_frame():
    """Return six hand-written rows: the term, the texts of finding 4.1, a decimal, a null."""
    return pl.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "title": [
                "The rise of Industry 4.0.",
                "Textile firms",
                None,
                "GPT-3.5 was prompted",
                "5g of soil",
                None,
            ],
            "abstract": [
                None,
                "in the textile industry. 40 firms were surveyed",
                "in industry, 40% of plants",
                "we used GPT-3",
                "industry 4,0",
                "the industry 40 years ago",
            ],
        },
        schema={"id": pl.Int64, "title": pl.String, "abstract": pl.String},
    )


def test_flag_marker_exact_rows():
    """`flag` with the option on a hand-written frame: exact columns, values and dtypes.

    Rows 2 and 3 are the texts of finding 4.1, row 4 has the decimal form in
    one field and the bare term in the other, row 6 is the withdrawn entry.
    """
    patterns = {
        "G5": translate.code_pattern(["5g", "gpt-3"], decimal_whole=True),
        "I4": translate.code_pattern(["industry 4.0"], decimal_whole=True),
    }
    assert patterns == {"G5": " (?:5g |gpt 3 )", "I4": " (?:industry 4p0 )"}
    out = translate.flag(_marker_frame(), patterns, ["title", "abstract"], decimal_whole=True)
    expected = _marker_frame().with_columns(
        pl.Series("G5", [False, False, False, True, True, False], dtype=pl.Boolean),
        pl.Series("I4", [True, False, False, False, True, False], dtype=pl.Boolean),
    )
    assert out.columns == ["id", "title", "abstract", "G5", "I4"]
    assert out["G5"].to_list() == [False, False, False, True, True, False]
    assert out["I4"].to_list() == [True, False, False, False, True, False]
    assert_frame_equal(out, expected)


def test_flag_marker_title_only():
    """Only the named field is searched: row 4's bare term is in the abstract."""
    patterns = {"G5": " (?:5g |gpt 3 )", "I4": " (?:industry 4p0 )"}
    out = translate.flag(_marker_frame(), patterns, ["title"], decimal_whole=True)
    assert out["G5"].to_list() == [False, False, False, False, True, False]
    assert out["I4"].to_list() == [True, False, False, False, False, False]


# ==========================================================================
# In SQL
# ==========================================================================


# --------------------------------------------------------------------------
# render_adt_flags, as in Amendment 3 with the marker
# --------------------------------------------------------------------------


# ==========================================================================
# The artefact
# ==========================================================================

QUERY_TEXT = 'TS = ( ("5G") OR ("industry 4.0") OR ("gpt-3") OR ("gpt-3.5") OR ("3.5*") )'
QUERY_TERMS = ["5g", "industry 4.0", "gpt-3", "gpt-3.5", "3.5*"]


def test_compile_queries_marker_artefact(tmp_path):
    """The whole artefact with `decimal_whole`: Amendment 3's keys, Amendment 4's values."""
    one = _write(tmp_path / "sub" / "one.txt", QUERY_TEXT)
    out = translate.compile_queries({"AA": one}, decimal_whole=True)
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION_MARKER,
        "hyphen_closed_form": False,
        "plural_tolerant": False,
        "decimal_whole": True,
        "definitions": [
            {
                "code": "AA",
                "source": "one.txt",
                "term_count": 5,
                "terms": QUERY_TERMS,
                "pattern": " (?:5g |industry 4p0 |gpt 3 |gpt 3p5 |3p5[^ ]*)",
            }
        ],
    }
    assert list(out) == KEYS_DECIMAL


def test_compile_queries_marker_normalisation_string(tmp_path):
    """The exact `normalisation` value, and its JSON form with doubled backslashes."""
    one = _write(tmp_path / "one.txt", QUERY_TEXT)
    out = translate.compile_queries({"AA": one}, decimal_whole=True)
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
    assert out["normalisation"] != NORMALISATION_AMENDMENT_3
    assert "is removed" not in out["normalisation"]


def test_compile_queries_marker_keys_with_exceptions(tmp_path):
    """The keys and their order are those of Amendment 3, plural exceptions included."""
    one = _write(tmp_path / "one.txt", QUERY_TEXT)
    out = translate.compile_queries(
        {"AA": one}, plural_tolerant=True, decimal_whole=True, plural_exceptions=["5g"]
    )
    assert list(out) == [
        "version",
        "normalisation",
        "hyphen_closed_form",
        "plural_tolerant",
        "decimal_whole",
        "plural_exceptions",
        "definitions",
    ]
    assert out["normalisation"] == NORMALISATION_MARKER
    assert out["plural_exceptions"] == ["5g"]
    # No term of the file takes a plural: four end with a digit or `*`, one is excepted.
    assert out["definitions"][0]["pattern"] == " (?:5g |industry 4p0 |gpt 3 |gpt 3p5 |3p5[^ ]*)"


def test_compile_queries_default_normalisation_is_unchanged(tmp_path):
    """With the default nothing changes: five keys and the base `normalisation` string."""
    one = _write(tmp_path / "one.txt", QUERY_TEXT)
    for out in (
        translate.compile_queries({"AA": one}),
        translate.compile_queries({"AA": one}, decimal_whole=False),
    ):
        assert list(out) == [
            "version",
            "normalisation",
            "hyphen_closed_form",
            "plural_tolerant",
            "definitions",
        ]
        assert out["normalisation"] == (
            r"lower-case; every run of characters outside \p{L}\p{N} becomes one space; "
            "trimmed; one space added at each end"
        )
        assert out["definitions"][0]["pattern"] == " (?:5g |industry 4 0 |gpt 3 |gpt 3 5 |3 5[^ ]*)"


# ==========================================================================
# Engine parity
# ==========================================================================

# Small term lists written by hand: a bare term a mass can imitate and a term
# a decimal fraction can follow, terms holding a decimal, a chain and a
# truncated term after a decimal.
PARITY_TERMS = {
    "G5": ["5g", "gpt-3"],
    "I4": ["industry 4.0", "society 5.0"],
    "VW": ["v1.2.3", "web 2.0 technolog*"],
}

# What `code_pattern(..., decimal_whole=True)` must give for each list above.
PARITY_PATTERNS = {
    "G5": " (?:5g |gpt 3 )",
    "I4": " (?:industry 4p0 |society 5p0 )",
    "VW": " (?:v1p2p3 |web 2p0 technolog[^ ]*)",
}


def _hits(*codes):
    """Return the expected flags of one text: True for the codes named, False for the rest."""
    unknown = set(codes) - set(PARITY_TERMS)
    assert not unknown, unknown
    return {code: code in codes for code in PARITY_TERMS}


# (text, {code: expected flag}). Each expectation was derived by normalising
# the text by hand with `decimal_whole=True` and searching the three patterns.
PARITY_FIXTURE = [
    # The bare term.
    ("5G", _hits("G5")),
    ("a 5G network", _hits("G5")),
    ("señal 5G", _hits("G5")),
    # A decimal before a term: the mass is one word and the term is not hit.
    ("0.5g of salt", _hits()),
    ("2.5G networks", _hits()),
    # A comma decimal.
    ("0,5g per day", _hits()),
    ("industry 4,0", _hits("I4")),
    # A mass with a space, and a whole-number mass.
    ("0.5 g of salt", _hits()),
    ("5g of soil", _hits("G5")),
    # A chain.
    ("1.2.3 is a chain", _hits()),
    ("release v1.2.3 of the tool", _hits("VW")),
    ("v1,2.3", _hits("VW")),
    ("v123", _hits()),
    ("v1.2.3.4", _hits()),
    ("v1.2 3", _hits()),
    # A term holding a decimal.
    ("Industry 4.0 and beyond", _hits("I4")),
    ("the rise of Industry 4.0.", _hits("I4")),
    ("industry 4 0", _hits()),
    ("the industry 40 years ago", _hits()),
    ("industry 4p0", _hits("I4")),
    ("Industry 4.01", _hits()),
    ("Society 5.0 in Japan", _hits("I4")),
    ("Web 2.0 technologies", _hits("VW")),
    ("web 2 0 technology", _hits()),
    ("web 20 technologies", _hits()),
    # A thousands separator.
    ("1,000 nodes and 5G", _hits("G5")),
    ("1,000,000 devices", _hits()),
    # A sentence end after a number.
    ("in 2020. 5G arrives", _hits("G5")),
    ("Measured in 2020. Industry 4.0 followed.", _hits("I4")),
    ("It ended in 2020.", _hits()),
    # A number at a sentence end before a second number.
    ("industry. 40 firms", _hits()),
    ("in the textile industry. 40 firms were surveyed", _hits()),
    # A percentage after a comma.
    ("in industry, 40% of", _hits()),
    ("in industry, 40% of plants", _hits()),
    # A number glued to a term by a comma, and the same with a space.
    ("in 2020,5G", _hits()),
    ("in 2020, 5G", _hits("G5")),
    # A term followed by a decimal fraction.
    ("GPT-3 was prompted", _hits("G5")),
    ("GPT-3.5 was prompted", _hits()),
    ("GPT-3,5", _hits()),
    ("GPT-3. 5 runs", _hits("G5")),
    # Digits outside ASCII do not hold a decimal together.
    ("5G ٣.٥", _hits("G5")),
    # A null, an empty string, and texts with no letter.
    (None, _hits()),
    ("", _hits()),
    ("...", _hits()),
    ("1.5", _hits()),
    # Several codes in one text.
    ("5G, Industry 4.0 and v1.2.3", _hits("G5", "I4", "VW")),
    ("INDUSTRY 4.0, SOCIETY 5,0, GPT-3.", _hits("G5", "I4")),
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


def test_parity_fixture_has_the_kinds_of_text_the_amendment_lists():
    """The six kinds of Amendment 3 and the two Amendment 4 adds, a null, hits and misses."""
    for text in [
        "0.5g of salt",
        "0,5g per day",
        "1.2.3 is a chain",
        "Industry 4.0 and beyond",
        "1,000 nodes and 5G",
        "in 2020. 5G arrives",
        "industry. 40 firms",
        "in industry, 40% of",
    ]:
        assert text in PARITY_TEXTS, text
    assert PARITY_TEXTS.count(None) == 1
    assert PARITY_TEXTS.count("") == 1
    for code in PARITY_TERMS:
        flags = [expected[code] for _, expected in PARITY_FIXTURE]
        assert True in flags, code
        assert False in flags, code


@pytest.mark.parametrize("code", list(PARITY_TERMS))
def test_polars_marker_matches_the_fixture(parity_patterns, code):
    """`translate.matches` with the option gives the expected flag for every fixture text."""
    got = [
        translate.matches(parity_patterns[code], text, decimal_whole=True) for text in PARITY_TEXTS
    ]
    assert got == [expected[code] for _, expected in PARITY_FIXTURE]


def test_polars_flag_marker_matches_the_fixture(parity_patterns):
    """`translate.flag` over the fixture as a one-column frame equals the fixture."""
    frame = pl.DataFrame({"t": PARITY_TEXTS}, schema={"t": pl.String})
    out = translate.flag(frame, parity_patterns, ["t"], decimal_whole=True)
    for code in PARITY_TERMS:
        assert out[code].to_list() == [expected[code] for _, expected in PARITY_FIXTURE], code


