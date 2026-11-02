"""Tests of `sdg_tech_tagger.wos_sdg`, written from the contract alone.

Source of every expected value: `docs/wos-sdg-contract.md` (D033). An expected
tree, string or list of notes is either a row or an example of the contract,
or a rule of the contract applied by hand to a short query written for this
file. No published query is copied here.

What is covered:

- `read_scopus`: every row of the contract's table, the four that raise
  included, and cases derived by hand: the binding order of the operators in
  every pairing, operators in any case, parentheses, chains, the field
  `TITLE-ABS-KEY`, no-break spaces, curly quotes, the text of a term, and
  every error the contract lists;
- `write_wos`: the exact text of each kind of node and of nestings;
- `read_wos`: exact trees of hand-written Web of Science text, the binding
  order where parentheses are absent, and the errors the contract lists;
- the round trip of the contract over hand-written Scopus queries;
- `notes` and `translate`: each code with its exact piece, and the order;
- `siris_expression` and `goal_query`;
- `build` and the shipped files of `wos_queries/`: the names, the bytes, what
  `read_wos` reads back, `SHA256SUMS`, `README.md` and `NOTES.tsv`, and two
  sources read a second time inside the test, with openpyxl, to check `build`
  against the functions above.

Readings taken where the contract leaves room, each the most literal one:

- "a word that holds two wildcards side by side" is a word of any term, bare,
  in double quotes or in braces;
- a term that stands twice in a tree gives its notes twice, so the middle
  operand of a chain gives them twice, `braces-wildcard` included;
- `a AND NOT b AND c` is `a AND NOT (b AND c)`, since `AND` binds before
  `AND NOT`;
- `"a" NOT "b" NOT "c"` in Web of Science text is nested to the left, as the
  section on trees says of `AND NOT`;
- `build` is given the path as a `str`, as in the contract's `build("published")`;
- the shipped files are compared with the text of `build` encoded as UTF-8.

`wos_sdg` is imported inside a fixture, so a missing module or function fails
a test and not the collection. openpyxl is a development dependency that
`build` needs; the tests that read a workbook import it in their body, so its
absence fails them.
"""

import hashlib
import importlib
import re
from importlib.resources import files
from pathlib import Path

import pytest

# tests/unit/test_wos_sdg.py: the repository root is three parents up.
ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = ROOT / "published"
ELSEVIER_BOOK = (
    PUBLISHED / "elsevier" / "2019_v1" / "SDG_queries_collated_20191010.xlsx"
)
SIRIS_BOOK = PUBLISHED / "siris" / "sdg_vocabulary_V.1.3 [zenodo].xlsx"

SHIPPED_DIR = Path(str(files("sdg_tech_tagger") / "wos_queries"))

# The 65 goal files the contract names: 17 goals for Aurora, 16 for each of
# the three others.
GOAL_FILES = (
    [f"aurora/SDG-{n:02d}.txt" for n in range(1, 18)]
    + [f"elsevier/SDG-{n:02d}.txt" for n in range(1, 17)]
    + [f"auckland/SDG-{n:02d}.txt" for n in range(1, 17)]
    + [f"siris/SDG-{n:02d}.txt" for n in range(1, 17)]
)
BUILT_FILES = [*GOAL_FILES, "NOTES.tsv"]

SYSTEMS = ["aurora", "elsevier", "auckland", "siris"]

# The five codes of `notes` and the two `translate` adds.
CODES = {
    "nested-proximity",
    "left-truncation",
    "short-stem",
    "non-ascii",
    "parenthesis",
    "chain",
    "braces-wildcard",
}


@pytest.fixture(scope="module")
def wos_sdg():
    """The module under test, imported here so its absence fails each test."""
    return importlib.import_module("sdg_tech_tagger.wos_sdg")


@pytest.fixture(scope="module")
def built(wos_sdg):
    """What `build` produces from `published/`, computed once.

    The published originals are not in this repository; CREDITS.md names
    where to download each. Put them in `published/` to run the tests that
    rebuild the shipped files from them; without them those tests are skipped.
    """
    if not PUBLISHED.is_dir():
        pytest.skip("published/ is not present: the published originals are not shipped")
    return wos_sdg.build(str(PUBLISHED))


# --------------------------------------------------------------------------
# Trees, written short
# --------------------------------------------------------------------------


def term(text):
    """Return the tree of one term."""
    return ("term", text)


def any_of(*operands):
    """Return an `or` node over the operands, in the order given."""
    return ("or", operands)


def all_of(*operands):
    """Return an `and` node over the operands, in the order given."""
    return ("and", operands)


def but(kept, excluded):
    """Return a `not` node: `kept` and not `excluded`."""
    return ("not", kept, excluded)


def near(distance, left, right):
    """Return a `near` node: `left` within `distance` words of `right`."""
    return ("near", distance, left, right)


A, B, C, D, E, P = (term(letter) for letter in "abcdep")


# --------------------------------------------------------------------------
# read_scopus: the contract's table
# --------------------------------------------------------------------------

SCOPUS_TABLE = [
    ('"a b"', term("a b")),
    ("{a  b}", term("a b")),
    ("poverty", term("poverty")),
    ("TITLE-ABS-KEY ( {a} OR b )", any_of(A, B)),
    ('"a" OR "b" W/3 "c" OR "d"', near(3, any_of(A, B), any_of(C, D))),
    ('"a" AND "b" OR "c"', all_of(A, any_of(B, C))),
    ('"a" AND "b" AND NOT "c"', but(all_of(A, B), C)),
    ('"a" w/3 "b" and not "c"', but(near(3, A, B), C)),
    ('("a") W/3 ("b") W/6 ("c")', all_of(near(3, A, B), near(6, B, C))),
    (
        '"p" AND "a" W/3 "b" W/3 "c"',
        all_of(P, all_of(near(3, A, B), near(3, B, C))),
    ),
    ('("a" W/3 "b") W/3 "c"', near(3, near(3, A, B), C)),
]

SCOPUS_TABLE_ERRORS = [
    '"a" PRE/3 "b"',
    '"a" W/3 ("b" AND "c")',
    '("a" W/3 "b" W/3 "c") W/3 "d"',
    'TITLE ( "a" )',
]


@pytest.mark.parametrize(("query", "expected"), SCOPUS_TABLE)
def test_read_scopus_gives_the_tree_of_the_contract_table(wos_sdg, query, expected):
    assert wos_sdg.read_scopus(query) == expected


@pytest.mark.parametrize("query", SCOPUS_TABLE_ERRORS)
def test_read_scopus_raises_on_the_rows_of_the_table_that_raise(wos_sdg, query):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.read_scopus(query)


def test_query_error_is_a_value_error(wos_sdg):
    assert issubclass(wos_sdg.QueryError, ValueError)


# --------------------------------------------------------------------------
# read_scopus: the rules applied by hand
# --------------------------------------------------------------------------

# OR binds first, then W/n, then AND, then AND NOT. Each pair of operators is
# written in both orders.
SCOPUS_BINDING = [
    # OR and W/n
    ('"a" OR "b" W/3 "c"', near(3, any_of(A, B), C)),
    ('"a" W/3 "b" OR "c"', near(3, A, any_of(B, C))),
    # OR and AND
    ('"a" OR "b" AND "c"', all_of(any_of(A, B), C)),
    ('"a" AND "b" OR "c"', all_of(A, any_of(B, C))),
    # OR and AND NOT
    ('"a" OR "b" AND NOT "c"', but(any_of(A, B), C)),
    ('"a" AND NOT "b" OR "c"', but(A, any_of(B, C))),
    # W/n and AND
    ('"a" W/3 "b" AND "c"', all_of(near(3, A, B), C)),
    ('"a" AND "b" W/3 "c"', all_of(A, near(3, B, C))),
    # W/n and AND NOT
    ('"a" W/3 "b" AND NOT "c"', but(near(3, A, B), C)),
    ('"a" AND NOT "b" W/3 "c"', but(A, near(3, B, C))),
    # AND and AND NOT
    ('"a" AND "b" AND NOT "c"', but(all_of(A, B), C)),
    ('"a" AND NOT "b" AND "c"', but(A, all_of(B, C))),
    # The four at once.
    (
        '"a" OR "b" W/2 "c" AND "d" AND NOT "e"',
        but(all_of(near(2, any_of(A, B), C), D), E),
    ),
    (
        '"a" AND NOT "b" AND "c" W/2 "d" OR "e"',
        but(A, all_of(B, near(2, C, any_of(D, E)))),
    ),
    # OR inside AND on both sides.
    ('"a" OR "b" AND "c" OR "d"', all_of(any_of(A, B), any_of(C, D))),
]

# Operands joined by one operator at one level are one node.
SCOPUS_ONE_NODE = [
    ("a OR b OR c", any_of(A, B, C)),
    ('"a" OR "b" OR "c" OR "d"', any_of(A, B, C, D)),
    ('"a" AND "b" AND "c"', all_of(A, B, C)),
    ('"a" AND "b" AND "c" AND "d"', all_of(A, B, C, D)),
    ('"a" W/5 "b"', near(5, A, B)),
    ('"a" W/15 "b"', near(15, A, B)),
    ('"a" W/0 "b"', near(0, A, B)),
    ('"a" AND NOT "b"', but(A, B)),
]

# Operators are read in any case.
SCOPUS_CASE = [
    ('"a" or "b"', any_of(A, B)),
    ('"a" Or "b"', any_of(A, B)),
    ('"a" oR "b" OR "c"', any_of(A, B, C)),
    ('"a" and "b"', all_of(A, B)),
    ('"a" And "b" aNd "c"', all_of(A, B, C)),
    ('"a" and not "b"', but(A, B)),
    ('"a" And Not "b"', but(A, B)),
    ('"a" AND not "b"', but(A, B)),
    ('"a" w/3 "b"', near(3, A, B)),
    (
        '"a" or "b" w/4 "c" and "d" and not "e"',
        but(all_of(near(4, any_of(A, B), C), D), E),
    ),
    # A word that only holds the letters of an operator is a term.
    ("sand OR band", any_of(term("sand"), term("band"))),
    ("ORGANIC AND Andes", all_of(term("ORGANIC"), term("Andes"))),
    ("nothing OR notion", any_of(term("nothing"), term("notion"))),
]

# Parentheses that are written are kept as nesting; around one operand they
# add nothing.
SCOPUS_PARENTHESES = [
    ("(a OR b) OR c", any_of(any_of(A, B), C)),
    ("a OR (b OR c)", any_of(A, any_of(B, C))),
    ('("a" OR "b") OR ("c" OR "d")', any_of(any_of(A, B), any_of(C, D))),
    ('("a" AND "b") AND "c"', all_of(all_of(A, B), C)),
    ('"a" AND ("b" AND "c")', all_of(A, all_of(B, C))),
    ('("a" AND "b") OR "c"', any_of(all_of(A, B), C)),
    ('"a" OR ("b" AND "c")', any_of(A, all_of(B, C))),
    ('("a" AND NOT "b") OR "c"', any_of(but(A, B), C)),
    ('"a" AND NOT ("b" AND NOT "c")', but(A, but(B, C))),
    ('("a" AND NOT "b") AND "c"', all_of(but(A, B), C)),
    ('("a" W/3 "b") OR "c"', any_of(near(3, A, B), C)),
    ('"a" W/3 ("b" W/2 "c")', near(3, A, near(2, B, C))),
    ('("a" W/1 "b") W/2 ("c" W/3 "d")', near(2, near(1, A, B), near(3, C, D))),
    ('"a" W/3 ("b" OR ("c" W/2 "d"))', near(3, A, any_of(B, near(2, C, D)))),
    ('("a" OR "b") W/3 ("c" OR "d")', near(3, any_of(A, B), any_of(C, D))),
    ("((a))", A),
    ('("a")', A),
    ('((("a b")))', term("a b")),
    ("({a})", A),
    ("(a OR b)", any_of(A, B)),
    ("((a OR b))", any_of(A, B)),
    ('(("a")) OR ((("b")))', any_of(A, B)),
    ('(("a" AND "b"))', all_of(A, B)),
    ('(("a" W/3 "b"))', near(3, A, B)),
    # No space is needed around a parenthesis or a quote.
    ('("a")OR("b")', any_of(A, B)),
    ('("a"OR"b")AND"c"', all_of(any_of(A, B), C)),
    # An operator right before a parenthesis is not a field.
    ('"a" OR ("b" AND "c") OR ("d" AND "e")', any_of(A, all_of(B, C), all_of(D, E))),
    (
        '"a" AND ("b" OR "c") AND NOT ("d" OR "e")',
        but(all_of(A, any_of(B, C)), any_of(D, E)),
    ),
]

# `a AND NOT b AND NOT c` is nested to the left.
SCOPUS_AND_NOT = [
    ("a AND NOT b AND NOT c", but(but(A, B), C)),
    ('"a" AND NOT "b" AND NOT "c" AND NOT "d"', but(but(but(A, B), C), D)),
    ('"a" AND "b" AND NOT "c" AND NOT "d"', but(but(all_of(A, B), C), D)),
    ('"a" and not "b" And Not "c"', but(but(A, B), C)),
    (
        '("a" OR "b") AND NOT "c" AND NOT ("d" OR "e")',
        but(but(any_of(A, B), C), any_of(D, E)),
    ),
    # White space of any length between the two words of the operator.
    ('"a" AND   NOT "b"', but(A, B)),
    ('"a" AND\n NOT "b"', but(A, B)),
    ('"a" AND\xa0NOT "b"', but(A, B)),
]

# A chain: three or more operands joined by W/n at one level become an `and`
# of one `near` per neighbouring pair, as its own node.
SCOPUS_CHAINS = [
    ('"a" W/3 "b" W/3 "c"', all_of(near(3, A, B), near(3, B, C))),
    ('"a" W/2 "b" W/7 "c"', all_of(near(2, A, B), near(7, B, C))),
    (
        '"a" W/1 "b" W/2 "c" W/3 "d"',
        all_of(near(1, A, B), near(2, B, C), near(3, C, D)),
    ),
    (
        '"a" W/4 "b" W/4 "c" W/9 "d"',
        all_of(near(4, A, B), near(4, B, C), near(9, C, D)),
    ),
    (
        '"a" w/5 "b" W/6 "c" w/7 "d" W/8 "e"',
        all_of(near(5, A, B), near(6, B, C), near(7, C, D), near(8, D, E)),
    ),
    # OR binds first, so an operand of a chain may be an `or`.
    (
        '"a" OR "p" W/3 "b" W/5 "c" OR "d"',
        all_of(near(3, any_of(A, P), B), near(5, B, any_of(C, D))),
    ),
    (
        '"a" W/3 ("b" OR "c") W/5 "d"',
        all_of(near(3, A, any_of(B, C)), near(5, any_of(B, C), D)),
    ),
    # An operand of a chain may be a `near` in parentheses.
    (
        '("a" W/2 "b") W/3 "c" W/4 "d"',
        all_of(near(3, near(2, A, B), C), near(4, C, D)),
    ),
    (
        '"a" W/3 ("b" W/2 "c") W/4 "d"',
        all_of(near(3, A, near(2, B, C)), near(4, near(2, B, C), D)),
    ),
    # The chain is its own node, not merged into an `and` around it.
    (
        '"a" W/3 "b" W/3 "c" AND "p"',
        all_of(all_of(near(3, A, B), near(3, B, C)), P),
    ),
    (
        '("a" W/3 "b" W/3 "c") AND "p"',
        all_of(all_of(near(3, A, B), near(3, B, C)), P),
    ),
    (
        '"p" AND "a" W/3 "b" W/3 "c" AND "d"',
        all_of(P, all_of(near(3, A, B), near(3, B, C)), D),
    ),
    ('("a" W/3 "b" W/3 "c")', all_of(near(3, A, B), near(3, B, C))),
    (
        '"a" W/3 "b" W/3 "c" OR "d"',
        all_of(near(3, A, B), near(3, B, any_of(C, D))),
    ),
    (
        '("a" W/3 "b" W/3 "c") OR "d"',
        any_of(all_of(near(3, A, B), near(3, B, C)), D),
    ),
    (
        '"a" W/3 "b" W/3 "c" AND NOT "d"',
        but(all_of(near(3, A, B), near(3, B, C)), D),
    ),
    (
        '"p" AND NOT "a" W/3 "b" W/3 "c"',
        but(P, all_of(near(3, A, B), near(3, B, C))),
    ),
    # Two W/n at two levels are not a chain.
    ('("a" W/3 "b") W/6 "c"', near(6, near(3, A, B), C)),
    ('"a" W/3 ("b" W/6 "c")', near(3, A, near(6, B, C))),
]

# TITLE-ABS-KEY before a parenthesis is dropped.
SCOPUS_FIELD = [
    ('TITLE-ABS-KEY("a")', A),
    ('TITLE-ABS-KEY ("a")', A),
    ('TITLE-ABS-KEY ( "a" )', A),
    ('TITLE-ABS-KEY\xa0(\xa0"a"\xa0)', A),
    ('TITLE-ABS-KEY("a" OR "b")', any_of(A, B)),
    ('TITLE-ABS-KEY ( ( "a" OR "b" ) AND "c" )', all_of(any_of(A, B), C)),
    ('TITLE-ABS-KEY(("a"))', A),
    ("TITLE-ABS-KEY ( {a} AND NOT {b} )", but(A, B)),
    ('TITLE-ABS-KEY("a") AND TITLE-ABS-KEY ("b")', all_of(A, B)),
    ('TITLE-ABS-KEY("a" OR "b") AND NOT TITLE-ABS-KEY("c")', but(any_of(A, B), C)),
    ('(TITLE-ABS-KEY("a" W/3 "b"))', near(3, A, B)),
    # Its parentheses are written, so they are kept as nesting.
    ('TITLE-ABS-KEY("a" OR "b") OR "c"', any_of(any_of(A, B), C)),
    ('"p" AND TITLE-ABS-KEY ( "a" AND "b" )', all_of(P, all_of(A, B))),
]

# A no-break space is a space; the quotes “ and ” are ".
SCOPUS_CHARACTERS = [
    ('"a"\xa0OR\xa0"b"', any_of(A, B)),
    ("\xa0(\xa0{a}\xa0 OR\xa0 {b}\xa0)\xa0", any_of(A, B)),
    ('"a"\xa0W/3\xa0"b"', near(3, A, B)),
    ('"a\xa0b"', term("a b")),
    ("{a\xa0\xa0b}", term("a b")),
    ('"\xa0a b\xa0"', term("a b")),
    ("a\xa0OR\xa0b", any_of(A, B)),
    ("“a b”", term("a b")),
    ("“a” OR “b”", any_of(A, B)),
    ('“a” AND "b"', all_of(A, B)),
    ("“a” W/3 “b” W/3 “c”", all_of(near(3, A, B), near(3, B, C))),
    ("TITLE-ABS-KEY ( “a” OR “b c” )", any_of(A, term("b c"))),
    # Other white space between the pieces.
    ('"a"\n\tOR\n"b"', any_of(A, B)),
    ('  "a"   AND   "b"  ', all_of(A, B)),
]

# The text of a term: white space collapsed and stripped, case kept.
SCOPUS_TERMS = [
    ('"climate change"', term("climate change")),
    ('"  Climate   Change "', term("Climate Change")),
    ('"a\tb\n c"', term("a b c")),
    ("{ Extreme\tPoverty }", term("Extreme Poverty")),
    ("{a b c}", term("a b c")),
    ('"HIV"', term("HIV")),
    ("Poverty", term("Poverty")),
    ("{North-South Divide}", term("North-South Divide")),
    # A term in quotes or braces may hold the words of operators.
    ('"research and development"', term("research and development")),
    ('"black or white"', term("black or white")),
    ("{trade and not aid}", term("trade and not aid")),
    ('"a W/3 b"', term("a W/3 b")),
    # ... and parentheses.
    ('"gross domestic product (gdp)"', term("gross domestic product (gdp)")),
    # Wildcards stay in the text.
    ('"child* labo?r"', term("child* labo?r")),
    ("{child*}", term("child*")),
    ('"*ism"', term("*ism")),
    ('"a*b?c"', term("a*b?c")),
]

# A bare word: a run of characters other than white space, parentheses,
# braces and double quotes, that is not an operator.
SCOPUS_BARE = [
    ("socio-economic", term("socio-economic")),
    ("covid-19", term("covid-19")),
    ("women's", term("women's")),
    ("l'eau", term("l'eau")),
    ("women’s", term("women’s")),
    ("child*", term("child*")),
    ("wom?n", term("wom?n")),
    ("*ism", term("*ism")),
    ("labo?r*", term("labo?r*")),
    ("3.5", term("3.5")),
    ("Niño", term("Niño")),
    ("low-income AND child*", all_of(term("low-income"), term("child*"))),
    (
        "women's OR socio-economic OR wom?n",
        any_of(term("women's"), term("socio-economic"), term("wom?n")),
    ),
    ("(poverty)", term("poverty")),
    ("poverty W/3 child*", near(3, term("poverty"), term("child*"))),
    ('{a} OR b OR "c"', any_of(A, B, C)),
    ("poverty AND NOT mice", but(term("poverty"), term("mice"))),
]

SCOPUS_DERIVED = (
    SCOPUS_BINDING
    + SCOPUS_ONE_NODE
    + SCOPUS_CASE
    + SCOPUS_PARENTHESES
    + SCOPUS_AND_NOT
    + SCOPUS_CHAINS
    + SCOPUS_FIELD
    + SCOPUS_CHARACTERS
    + SCOPUS_TERMS
    + SCOPUS_BARE
)


@pytest.mark.parametrize(("query", "expected"), SCOPUS_DERIVED)
def test_read_scopus_gives_the_tree_the_rules_give(wos_sdg, query, expected):
    assert wos_sdg.read_scopus(query) == expected


# Every error the contract lists, by its line of the list.
SCOPUS_ERRORS = {
    "PRE/n": [
        '"a" PRE/3 "b"',
        '"a" pre/3 "b"',
        '"a" Pre/10 "b"',
        '"a" OR "b" PRE/2 "c"',
        '("a" PRE/3 "b") AND "c"',
        '"a" W/3 "b" PRE/3 "c"',
    ],
    "an and or a not inside an operand of W/n": [
        '"a" W/3 ("b" AND "c")',
        '("a" AND "b") W/3 "c"',
        '"a" W/3 ("b" AND NOT "c")',
        '("a" AND NOT "b") W/3 "c"',
        '"a" W/3 ("b" OR ("c" AND "d"))',
        '"a" W/3 ("b" OR ("c" AND NOT "d"))',
        '("p" OR ("a" AND "b")) W/3 "c"',
        '"a" W/3 ("b" W/2 ("c" AND "d"))',
        '"a" W/3 ("b" OR ("c" W/2 ("d" AND NOT "e")))',
        '"a" w/3 ("b" and "c")',
        # ... of a chain as well.
        '"a" W/3 ("b" AND "c") W/3 "d"',
        '"a" W/3 "b" W/3 ("c" AND NOT "d")',
    ],
    "a chain inside an operand of W/n": [
        '("a" W/3 "b" W/3 "c") W/3 "d"',
        '"d" W/3 ("a" W/3 "b" W/3 "c")',
        '"d" W/3 ("p" OR ("a" W/3 "b" W/3 "c"))',
        '"d" W/3 ("p" W/2 ("a" W/3 "b" W/3 "c"))',
        '("a" W/1 "b" W/2 "c") W/3 "d" W/4 "e"',
    ],
    "a field other than TITLE-ABS-KEY": [
        'TITLE ( "a" )',
        'TITLE("a")',
        'TITLE-ABS("a")',
        'TITLE-ABS ( "a" OR "b" )',
        'AUTHKEY("a")',
        'ABS ("a")',
        'KEY("a")',
        'TITLE-ABS-KEY-AUTH("a")',
        '"a" AND TITLE-ABS("b")',
        'TITLE-ABS-KEY("a") OR AUTHKEY("b")',
    ],
    "a double quote inside braces": [
        '{a "b" c}',
        '{"a"}',
        '{a"b}',
        "{“a”}",
        '"p" OR {a "b"}',
    ],
    "two wildcards side by side in a word": [
        "a**",
        "a*?",
        "a?*b",
        "a??b",
        "**a",
        '"a" OR b??',
        '"a b**"',
        '"wom??n rights"',
        "{a*?}",
        "{child ?*}",
    ],
    "a parenthesis that is not closed": [
        '("a" OR "b"',
        '(("a")',
        '"a" AND ("b" OR ("c")',
        'TITLE-ABS-KEY("a"',
        "(a",
    ],
    "a quote that is not closed": [
        '"a',
        '"a" OR "b',
        '("a" OR "b)',
        "“a",
    ],
    "a brace that is not closed": [
        "{a",
        '"a" OR {b',
        "({a)",
    ],
    "an operator with no operand": [
        'OR "a"',
        '"a" OR',
        '"a" OR OR "b"',
        'AND "a"',
        '"a" AND',
        '"a" AND AND "b"',
        '"a" W/3',
        'W/3 "a"',
        '"a" W/3 W/3 "b"',
        '"a" AND NOT',
        'AND NOT "a"',
        '("a" OR) AND "b"',
        '"a" AND (OR "b")',
        '"a" OR AND "b"',
        "OR",
        "and",
    ],
    "two operands with no operator": [
        '"a" "b"',
        "a b",
        "{a} {b}",
        '"a" {b}',
        '"a" ("b")',
        '("a") ("b")',
        '"a" OR "b" "c"',
        '("a" OR "b") "c"',
        "climate change",
    ],
    "an empty query": [
        "",
        "   ",
        "\xa0",
        "\n\t ",
    ],
}


@pytest.mark.parametrize(
    "query",
    [query for queries in SCOPUS_ERRORS.values() for query in queries],
)
def test_read_scopus_raises_on_every_listed_error(wos_sdg, query):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.read_scopus(query)


def test_a_double_wildcard_apart_is_read(wos_sdg):
    """Two wildcards in one word that are not side by side are no error."""
    assert wos_sdg.read_scopus("a*b?") == term("a*b?")
    assert wos_sdg.read_scopus('"a* b?"') == term("a* b?")


# --------------------------------------------------------------------------
# write_wos
# --------------------------------------------------------------------------

WRITTEN = [
    # A term.
    (A, '"a"'),
    (term("a b"), '"a b"'),
    (term("Climate Change"), '"Climate Change"'),
    (term("child* labo?r"), '"child* labo?r"'),
    (term("gross domestic product (gdp)"), '"gross domestic product (gdp)"'),
    (term("El Niño"), '"El Niño"'),
    # One node of each kind.
    (any_of(A, B), '("a" OR "b")'),
    (any_of(A, B, C), '("a" OR "b" OR "c")'),
    (any_of(A, B, C, D), '("a" OR "b" OR "c" OR "d")'),
    (all_of(A, B), '("a" AND "b")'),
    (all_of(A, B, C), '("a" AND "b" AND "c")'),
    (but(A, B), '("a" NOT "b")'),
    (near(3, A, B), '("a" NEAR/3 "b")'),
    (near(15, A, B), '("a" NEAR/15 "b")'),
    (near(0, A, B), '("a" NEAR/0 "b")'),
    # The order written is the order of the operands.
    (any_of(C, A, B), '("c" OR "a" OR "b")'),
    (near(3, B, A), '("b" NEAR/3 "a")'),
    (but(B, A), '("b" NOT "a")'),
    # Nestings: every node that is not a term is in parentheses.
    (any_of(any_of(A, B), C), '(("a" OR "b") OR "c")'),
    (any_of(A, all_of(B, C)), '("a" OR ("b" AND "c"))'),
    (all_of(any_of(A, B), any_of(C, D)), '(("a" OR "b") AND ("c" OR "d"))'),
    (all_of(all_of(A, B), C), '(("a" AND "b") AND "c")'),
    (but(but(A, B), C), '(("a" NOT "b") NOT "c")'),
    (but(A, but(B, C)), '("a" NOT ("b" NOT "c"))'),
    (but(all_of(A, B), any_of(C, D)), '(("a" AND "b") NOT ("c" OR "d"))'),
    (near(3, any_of(A, B), any_of(C, D)), '(("a" OR "b") NEAR/3 ("c" OR "d"))'),
    (near(3, near(2, A, B), C), '(("a" NEAR/2 "b") NEAR/3 "c")'),
    (near(3, A, near(2, B, C)), '("a" NEAR/3 ("b" NEAR/2 "c"))'),
    (all_of(near(3, A, B), near(6, B, C)), '(("a" NEAR/3 "b") AND ("b" NEAR/6 "c"))'),
    (
        all_of(P, all_of(near(3, A, B), near(3, B, C))),
        '("p" AND (("a" NEAR/3 "b") AND ("b" NEAR/3 "c")))',
    ),
    (
        any_of(A, but(all_of(B, near(4, C, any_of(D, E))), P)),
        '("a" OR (("b" AND ("c" NEAR/4 ("d" OR "e"))) NOT "p"))',
    ),
]


@pytest.mark.parametrize(("tree", "expected"), WRITTEN)
def test_write_wos_gives_the_exact_text(wos_sdg, tree, expected):
    assert wos_sdg.write_wos(tree) == expected


def test_write_wos_of_the_contract_example(wos_sdg):
    tree = wos_sdg.read_scopus('"p" AND "a" W/3 "b" W/3 "c"')
    assert (
        wos_sdg.write_wos(tree) == '("p" AND (("a" NEAR/3 "b") AND ("b" NEAR/3 "c")))'
    )


@pytest.mark.parametrize(
    "tree",
    [
        term('a "b"'),
        term('"'),
        any_of(A, term('b"c')),
        all_of(A, any_of(B, term('say "no"'))),
        but(A, term('"b')),
        near(3, term('a"'), B),
    ],
)
def test_write_wos_raises_on_a_term_that_holds_a_double_quote(wos_sdg, tree):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.write_wos(tree)


# --------------------------------------------------------------------------
# read_wos
# --------------------------------------------------------------------------

WOS_READ = [
    # A term, with and without the tag.
    ('"a"', A),
    ('"a b"', term("a b")),
    ('TS="a"', A),
    ('TS=("a")', A),
    ('TS = ("a")', A),
    ('TS =("a b")', term("a b")),
    ('TS=("a" OR "b")', any_of(A, B)),
    ('TS = ("a" OR "b")', any_of(A, B)),
    (
        'TS=(("a" NEAR/3 "b") AND ("b" NEAR/3 "c"))',
        all_of(near(3, A, B), near(3, B, C)),
    ),
    ('TS=("a" OR ("b" AND "c"))', any_of(A, all_of(B, C))),
    ('TS=("a" OR ("b" AND "c"))\n', any_of(A, all_of(B, C))),
    # One node of each kind, as `write_wos` writes it and without parentheses.
    ('("a" OR "b" OR "c")', any_of(A, B, C)),
    ('"a" OR "b" OR "c"', any_of(A, B, C)),
    ('("a" AND "b" AND "c")', all_of(A, B, C)),
    ('"a" AND "b"', all_of(A, B)),
    ('("a" NOT "b")', but(A, B)),
    ('"a" NOT "b"', but(A, B)),
    ('("a" NEAR/3 "b")', near(3, A, B)),
    ('"a" NEAR/15 "b"', near(15, A, B)),
    ('"a" NEAR/0 "b"', near(0, A, B)),
    # Parentheses that are written are kept; around one operand they add
    # nothing.
    ('(("a" OR "b") OR "c")', any_of(any_of(A, B), C)),
    ('("a" OR "b") OR "c"', any_of(any_of(A, B), C)),
    ('"a" OR ("b" OR "c")', any_of(A, any_of(B, C))),
    ('("a" OR "b") AND "c"', all_of(any_of(A, B), C)),
    ('("a" AND "b") AND "c"', all_of(all_of(A, B), C)),
    ('"a" NOT ("b" NOT "c")', but(A, but(B, C))),
    ('(("a" NOT "b") NOT "c")', but(but(A, B), C)),
    ('("a" NEAR/2 "b") NEAR/3 "c"', near(3, near(2, A, B), C)),
    ('"a" NEAR/3 ("b" NEAR/2 "c")', near(3, A, near(2, B, C))),
    ('("a" OR "b") NEAR/3 ("c" OR "d")', near(3, any_of(A, B), any_of(C, D))),
    ('(("a"))', A),
    ('(("a" OR "b"))', any_of(A, B)),
    ('TS=((("a" AND "b")))', all_of(A, B)),
    ('(("a")) OR ("b")', any_of(A, B)),
    # The text of a term.
    ('"Climate Change"', term("Climate Change")),
    ('"a  b"', term("a b")),
    ('"child* labo?r"', term("child* labo?r")),
    ('"El Niño"', term("El Niño")),
    ('"gross domestic product (gdp)"', term("gross domestic product (gdp)")),
    ('"research and development"', term("research and development")),
    ('("a near/3 b" OR "not")', any_of(term("a near/3 b"), term("not"))),
]

# The Web of Science binds NEAR/n first, then NOT, then AND, then OR.
WOS_BINDING = [
    # OR and AND
    ('"a" OR "b" AND "c"', any_of(A, all_of(B, C))),
    ('"a" AND "b" OR "c"', any_of(all_of(A, B), C)),
    # OR and NOT
    ('"a" OR "b" NOT "c"', any_of(A, but(B, C))),
    ('"a" NOT "b" OR "c"', any_of(but(A, B), C)),
    # OR and NEAR
    ('"a" OR "b" NEAR/3 "c"', any_of(A, near(3, B, C))),
    ('"a" NEAR/3 "b" OR "c"', any_of(near(3, A, B), C)),
    # AND and NOT
    ('"a" AND "b" NOT "c"', all_of(A, but(B, C))),
    ('"a" NOT "b" AND "c"', all_of(but(A, B), C)),
    # AND and NEAR
    ('"a" AND "b" NEAR/3 "c"', all_of(A, near(3, B, C))),
    ('"a" NEAR/3 "b" AND "c"', all_of(near(3, A, B), C)),
    # NOT and NEAR
    ('"a" NOT "b" NEAR/3 "c"', but(A, near(3, B, C))),
    ('"a" NEAR/3 "b" NOT "c"', but(near(3, A, B), C)),
    # The four at once, in both orders.
    (
        '"a" OR "b" AND "c" NOT "d" NEAR/2 "e"',
        any_of(A, all_of(B, but(C, near(2, D, E)))),
    ),
    (
        '"a" NEAR/2 "b" NOT "c" AND "d" OR "e"',
        any_of(all_of(but(near(2, A, B), C), D), E),
    ),
    ('"a" OR "b" AND "c" OR "d"', any_of(A, all_of(B, C), D)),
    ('"a" AND "b" OR "c" AND "d"', any_of(all_of(A, B), all_of(C, D))),
    (
        '"a" NEAR/1 "b" AND "c" NEAR/2 "d"',
        all_of(near(1, A, B), near(2, C, D)),
    ),
    ('TS=("a" OR "b" AND "c")', any_of(A, all_of(B, C))),
    # NOT twice at one level is nested to the left, as the trees say.
    ('"a" NOT "b" NOT "c"', but(but(A, B), C)),
]

# Operators are read in any case.
WOS_CASE = [
    ('"a" or "b"', any_of(A, B)),
    ('"a" Or "b" oR "c"', any_of(A, B, C)),
    ('"a" and "b"', all_of(A, B)),
    ('"a" And "b"', all_of(A, B)),
    ('"a" not "b"', but(A, B)),
    ('"a" Not "b"', but(A, B)),
    ('"a" near/3 "b"', near(3, A, B)),
    ('"a" Near/12 "b"', near(12, A, B)),
    (
        '"a" or "b" and "c" not "d" near/2 "e"',
        any_of(A, all_of(B, but(C, near(2, D, E)))),
    ),
]


@pytest.mark.parametrize(("text", "expected"), WOS_READ + WOS_BINDING + WOS_CASE)
def test_read_wos_gives_the_exact_tree(wos_sdg, text, expected):
    assert wos_sdg.read_wos(text) == expected


WOS_ERRORS = {
    "a NEAR/n that joins three operands at one level": [
        '"a" NEAR/3 "b" NEAR/3 "c"',
        '"a" NEAR/3 "b" NEAR/5 "c"',
        '("a" NEAR/3 "b" NEAR/3 "c")',
        'TS=("a" NEAR/3 "b" NEAR/3 "c")',
        '"p" AND "a" NEAR/3 "b" NEAR/3 "c"',
        '"a" NEAR/1 "b" NEAR/2 "c" NEAR/3 "d"',
    ],
    "an unquoted word that is not an operator": [
        "poverty",
        '"a" OR poverty',
        'TS=(poverty AND "a")',
        'climate "change"',
        '"a" W/3 "b"',
        '"a" PRE/3 "b"',
        '"a" NEAR "b"',
    ],
    "a parenthesis that is not closed": [
        '("a" OR "b"',
        'TS=("a"',
        '(("a")',
        '"a" AND ("b" OR ("c")',
    ],
    "a quote that is not closed": [
        '"a',
        '"a" OR "b',
        'TS=("a" OR "b)',
    ],
    "an empty text": [
        "",
        "   ",
        "\n",
    ],
}


@pytest.mark.parametrize(
    "text",
    [text for texts in WOS_ERRORS.values() for text in texts],
)
def test_read_wos_raises_on_every_listed_error(wos_sdg, text):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.read_wos(text)


# --------------------------------------------------------------------------
# The round trip
# --------------------------------------------------------------------------

# Hand-written Scopus queries of varied shape, every one read by
# `read_scopus`.
ROUND_TRIP = [
    "poverty",
    '"extreme poverty"',
    "{poverty line}",
    "child*",
    '"Climate   Change"',
    "“food security”",
    '"gross domestic product (gdp)"',
    '"El Niño"',
    "poverty OR hunger",
    '"a" OR "b" OR "c" OR "d"',
    '"poverty" AND "income"',
    '"a" AND "b" AND "c"',
    '"poverty" AND NOT "mice"',
    '"a" AND NOT "b" AND NOT "c"',
    '"a" AND NOT "b" AND "c"',
    '"poverty" W/3 "alleviation"',
    '"a" W/3 "b" W/3 "c"',
    '"a" W/1 "b" W/2 "c" W/3 "d"',
    '"a" w/5 "b" W/6 "c" w/7 "d" W/8 "e"',
    '"a" OR "b" W/3 "c" OR "d"',
    '"a" AND "b" OR "c"',
    '"a" OR "b" AND "c" OR "d"',
    '"a" AND "b" AND NOT "c"',
    '"a" w/3 "b" and not "c"',
    '("a") W/3 ("b") W/6 ("c")',
    '"p" AND "a" W/3 "b" W/3 "c"',
    '("a" W/3 "b") W/3 "c"',
    '"a" W/3 ("b" W/2 "c")',
    '("a" W/1 "b") W/2 ("c" W/3 "d")',
    '("a" W/2 "b") W/3 "c" W/4 "d"',
    '"a" W/3 ("b" OR ("c" W/2 "d"))',
    "(a OR b) OR c",
    "a OR (b OR c)",
    '("a" AND "b") AND "c"',
    '("a" AND "b") OR ("c" AND "d")',
    '("a" AND NOT "b") OR "c"',
    '"a" AND NOT ("b" AND NOT "c")',
    '("a" AND NOT "b") AND "c"',
    "((a))",
    "((a OR b))",
    "TITLE-ABS-KEY ( {a} OR b )",
    'TITLE-ABS-KEY("a" OR "b") OR "c"',
    'TITLE-ABS-KEY("a" OR "b") AND NOT TITLE-ABS-KEY("c")',
    "TITLE-ABS-KEY\xa0(\xa0(\xa0{extreme poverty}\xa0 OR\xa0 {poor}\xa0)\xa0 AND\xa0 {aid}\xa0)",
    "( {financial aid} AND {poverty} ) OR ( {financial aid} AND {poor} )",
    '("poverty" OR "poor") W/3 ("alleviat*" OR "reduc*" OR eradicat*)',
    '(("land" OR "soil") W/3 "degradation") AND ("restor*" OR "rehabilitat*")',
    '"a" W/3 "b" W/3 "c" AND NOT "d"',
    '"p" AND NOT "a" W/3 "b" W/3 "c"',
    '("a" W/3 "b" W/3 "c") OR ("d" W/2 "e" W/2 "p")',
    '"x" OR ("a" W/3 "b" W/3 "c") OR ("d" AND NOT "e")',
    "women's AND socio-economic AND wom?n",
    '{*ism} OR "ab*" OR a?b',
    '"research and development" AND {trade and not aid}',
    '(("a" OR "b") AND ("c" OR "d")) AND NOT (("e" W/2 "p") OR "x")',
    '"a" OR "b" W/2 "c" AND "d" AND NOT "e"',
    '"a" AND NOT "b" AND "c" W/2 "d" OR "e"',
    '("a")OR("b")',
]


def test_the_round_trip_list_holds_at_least_forty_distinct_queries():
    assert len(set(ROUND_TRIP)) == len(ROUND_TRIP)
    assert len(ROUND_TRIP) >= 40


@pytest.mark.parametrize("query", ROUND_TRIP)
def test_the_round_trip_gives_the_tree_back(wos_sdg, query):
    tree = wos_sdg.read_scopus(query)
    assert wos_sdg.read_wos(wos_sdg.write_wos(tree)) == tree


@pytest.mark.parametrize("query", ROUND_TRIP)
def test_the_round_trip_holds_under_the_tag(wos_sdg, query):
    """A goal file of one expression is read back as the tree of that query."""
    tree = wos_sdg.read_scopus(query)
    line = wos_sdg.goal_query([wos_sdg.write_wos(tree)])
    assert wos_sdg.read_wos(line) == tree


# --------------------------------------------------------------------------
# notes
# --------------------------------------------------------------------------

NOTED = [
    # Nothing to say.
    (A, []),
    (term("climate change"), []),
    (any_of(A, B, C), []),
    (all_of(A, but(B, C)), []),
    (near(3, A, B), []),
    (near(3, any_of(A, B), any_of(C, D)), []),
    # Two `near` side by side are not one inside the other.
    (all_of(near(3, A, B), near(3, B, C)), []),
    (any_of(near(3, A, B), near(2, C, D)), []),
    # nested-proximity: a `near` with a `near` anywhere inside an operand.
    (
        near(3, near(2, A, B), C),
        [("nested-proximity", '(("a" NEAR/2 "b") NEAR/3 "c")')],
    ),
    (
        near(3, A, near(2, B, C)),
        [("nested-proximity", '("a" NEAR/3 ("b" NEAR/2 "c"))')],
    ),
    (
        near(3, any_of(A, near(2, B, C)), D),
        [("nested-proximity", '(("a" OR ("b" NEAR/2 "c")) NEAR/3 "d")')],
    ),
    (
        near(2, near(1, A, B), near(3, C, D)),
        [("nested-proximity", '(("a" NEAR/1 "b") NEAR/2 ("c" NEAR/3 "d"))')],
    ),
    # The piece is the outer `near`, not the tree around it.
    (
        any_of(P, near(3, near(2, A, B), C)),
        [("nested-proximity", '(("a" NEAR/2 "b") NEAR/3 "c")')],
    ),
    # Three deep: the outer one, then the one inside it, which holds one too.
    (
        near(5, near(4, near(3, A, B), C), D),
        [
            ("nested-proximity", '((("a" NEAR/3 "b") NEAR/4 "c") NEAR/5 "d")'),
            ("nested-proximity", '(("a" NEAR/3 "b") NEAR/4 "c")'),
        ],
    ),
    # left-truncation: a word of the term starts with * or ?.
    (term("*ism"), [("left-truncation", "*ism")]),
    (term("?ism"), [("left-truncation", "?ism")]),
    (term("social *ism"), [("left-truncation", "social *ism")]),
    (term("*ab*"), [("left-truncation", "*ab*")]),
    # short-stem: the first wildcard of a word after one or two characters.
    (term("a*"), [("short-stem", "a*")]),
    (term("ab*"), [("short-stem", "ab*")]),
    (term("a?b"), [("short-stem", "a?b")]),
    (term("ab?c"), [("short-stem", "ab?c")]),
    (term("ab*c*"), [("short-stem", "ab*c*")]),
    (term("big a*"), [("short-stem", "big a*")]),
    (term("abc*"), []),
    (term("abc?"), []),
    (term("abc*d*"), []),
    (term("child* labo?r"), []),
    # non-ascii and parenthesis.
    (term("El Niño"), [("non-ascii", "El Niño")]),
    (term("café"), [("non-ascii", "café")]),
    (term("naïve*"), [("non-ascii", "naïve*")]),
    (term("women’s"), [("non-ascii", "women’s")]),
    (
        term("gross domestic product (gdp)"),
        [("parenthesis", "gross domestic product (gdp)")],
    ),
    (term("a) b"), [("parenthesis", "a) b")]),
    (term("x (y"), [("parenthesis", "x (y")]),
    # The codes of one term come in the order of the table.
    (
        term("*x ab* café (y)"),
        [
            ("left-truncation", "*x ab* café (y)"),
            ("short-stem", "*x ab* café (y)"),
            ("non-ascii", "*x ab* café (y)"),
            ("parenthesis", "*x ab* café (y)"),
        ],
    ),
    (
        term("(y) café ab* *x"),
        [
            ("left-truncation", "(y) café ab* *x"),
            ("short-stem", "(y) café ab* *x"),
            ("non-ascii", "(y) café ab* *x"),
            ("parenthesis", "(y) café ab* *x"),
        ],
    ),
    (term("*x a*"), [("left-truncation", "*x a*"), ("short-stem", "*x a*")]),
    # A term gives at most one pair per code.
    (term("*a ?b"), [("left-truncation", "*a ?b")]),
    (term("a* b* cd?"), [("short-stem", "a* b* cd?")]),
    (term("é ñ ü"), [("non-ascii", "é ñ ü")]),
    (term("(a) (b)"), [("parenthesis", "(a) (b)")]),
    (
        term("*a *b c* d* é ñ (x) (y)"),
        [
            ("left-truncation", "*a *b c* d* é ñ (x) (y)"),
            ("short-stem", "*a *b c* d* é ñ (x) (y)"),
            ("non-ascii", "*a *b c* d* é ñ (x) (y)"),
            ("parenthesis", "*a *b c* d* é ñ (x) (y)"),
        ],
    ),
    # The order of the written text, under each kind of node.
    (
        any_of(term("a*"), term("*b"), term("é")),
        [("short-stem", "a*"), ("left-truncation", "*b"), ("non-ascii", "é")],
    ),
    (
        all_of(term("é"), term("a*")),
        [("non-ascii", "é"), ("short-stem", "a*")],
    ),
    (
        but(term("*b"), term("a*")),
        [("left-truncation", "*b"), ("short-stem", "a*")],
    ),
    (
        near(3, term("(x)"), term("é")),
        [("parenthesis", "(x)"), ("non-ascii", "é")],
    ),
    # A node comes before its operands, and after what is written before it.
    (
        any_of(term("a*"), near(3, near(2, term("*b"), C), term("é"))),
        [
            ("short-stem", "a*"),
            ("nested-proximity", '(("*b" NEAR/2 "c") NEAR/3 "é")'),
            ("left-truncation", "*b"),
            ("non-ascii", "é"),
        ],
    ),
    (
        near(3, term("a*"), near(2, term("*b"), term("é"))),
        [
            ("nested-proximity", '("a*" NEAR/3 ("*b" NEAR/2 "é"))'),
            ("short-stem", "a*"),
            ("left-truncation", "*b"),
            ("non-ascii", "é"),
        ],
    ),
    # A term that stands twice in the tree gives its notes twice.
    (
        any_of(term("a*"), term("a*")),
        [("short-stem", "a*"), ("short-stem", "a*")],
    ),
    (
        all_of(near(3, A, term("ab*")), near(3, term("ab*"), C)),
        [("short-stem", "ab*"), ("short-stem", "ab*")],
    ),
]


@pytest.mark.parametrize(("tree", "expected"), NOTED)
def test_notes_gives_the_exact_pairs_in_order(wos_sdg, tree, expected):
    found = wos_sdg.notes(tree)
    assert isinstance(found, list)
    assert found == expected


# --------------------------------------------------------------------------
# translate
# --------------------------------------------------------------------------

CHAIN_ABC = '(("a" NEAR/3 "b") AND ("b" NEAR/3 "c"))'

TRANSLATED = [
    # Nothing to say.
    ("poverty", '"poverty"', []),
    ('"a" OR "b"', '("a" OR "b")', []),
    (
        "TITLE-ABS-KEY ( ( {extreme poverty} OR {poor} ) AND NOT {mice} )",
        '(("extreme poverty" OR "poor") NOT "mice")',
        [],
    ),
    ('"a" W/3 "b"', '("a" NEAR/3 "b")', []),
    # chain: its piece is the `and` it became, not the tree around it.
    ('"a" W/3 "b" W/3 "c"', CHAIN_ABC, [("chain", CHAIN_ABC)]),
    ('("a") W/3 ("b") W/3 ("c")', CHAIN_ABC, [("chain", CHAIN_ABC)]),
    (
        '"p" AND "a" W/3 "b" W/3 "c"',
        '("p" AND ' + CHAIN_ABC + ")",
        [("chain", CHAIN_ABC)],
    ),
    (
        '"a" W/1 "b" W/2 "c" W/3 "d"',
        '(("a" NEAR/1 "b") AND ("b" NEAR/2 "c") AND ("c" NEAR/3 "d"))',
        [("chain", '(("a" NEAR/1 "b") AND ("b" NEAR/2 "c") AND ("c" NEAR/3 "d"))')],
    ),
    # An `and` of two `near` that was written so is not a chain.
    ('("a" W/3 "b") AND ("b" W/3 "c")', CHAIN_ABC, []),
    # Two chains, in the order written.
    (
        '("a" W/3 "b" W/3 "c") OR ("d" W/2 "e" W/2 "p")',
        "(" + CHAIN_ABC + ' OR (("d" NEAR/2 "e") AND ("e" NEAR/2 "p")))',
        [
            ("chain", CHAIN_ABC),
            ("chain", '(("d" NEAR/2 "e") AND ("e" NEAR/2 "p"))'),
        ],
    ),
    # A chain comes where it is written: after the notes of what precedes it,
    # before the notes of its own operands.
    (
        '"x*" OR ("a" W/3 "b" W/3 "c")',
        '("x*" OR ' + CHAIN_ABC + ")",
        [("short-stem", "x*"), ("chain", CHAIN_ABC)],
    ),
    (
        '("a" W/2 "b") W/3 "c" W/3 "d"',
        '((("a" NEAR/2 "b") NEAR/3 "c") AND ("c" NEAR/3 "d"))',
        [
            ("chain", '((("a" NEAR/2 "b") NEAR/3 "c") AND ("c" NEAR/3 "d"))'),
            ("nested-proximity", '(("a" NEAR/2 "b") NEAR/3 "c")'),
        ],
    ),
    (
        '"a" W/3 "*b" W/3 "é"',
        '(("a" NEAR/3 "*b") AND ("*b" NEAR/3 "é"))',
        [
            ("chain", '(("a" NEAR/3 "*b") AND ("*b" NEAR/3 "é"))'),
            ("left-truncation", "*b"),
            ("left-truncation", "*b"),
            ("non-ascii", "é"),
        ],
    ),
    # braces-wildcard: a term in braces that holds * or ?.
    ("{child*}", '"child*"', [("braces-wildcard", "child*")]),
    ("{wom?n}", '"wom?n"', [("braces-wildcard", "wom?n")]),
    (
        "{social   protection*}",
        '"social protection*"',
        [("braces-wildcard", "social protection*")],
    ),
    ('"child*"', '"child*"', []),
    ("child*", '"child*"', []),
    ("{child}", '"child"', []),
    # It is the first note of its term.
    ("{a*}", '"a*"', [("braces-wildcard", "a*"), ("short-stem", "a*")]),
    ("{*ism}", '"*ism"', [("braces-wildcard", "*ism"), ("left-truncation", "*ism")]),
    (
        "{*x ab* café (y)}",
        '"*x ab* café (y)"',
        [
            ("braces-wildcard", "*x ab* café (y)"),
            ("left-truncation", "*x ab* café (y)"),
            ("short-stem", "*x ab* café (y)"),
            ("non-ascii", "*x ab* café (y)"),
            ("parenthesis", "*x ab* café (y)"),
        ],
    ),
    # Only the term in braces is marked.
    (
        '"child*" OR {pollutant*} OR {poor} OR "a*"',
        '("child*" OR "pollutant*" OR "poor" OR "a*")',
        [("braces-wildcard", "pollutant*"), ("short-stem", "a*")],
    ),
    (
        '{law*} AND NOT ("é" W/3 {marginali?ation})',
        '("law*" NOT ("é" NEAR/3 "marginali?ation"))',
        [
            ("braces-wildcard", "law*"),
            ("non-ascii", "é"),
            ("braces-wildcard", "marginali?ation"),
        ],
    ),
    # The middle operand of a chain is written twice, and noted twice.
    (
        '"a" W/3 {child*} W/3 "c"',
        '(("a" NEAR/3 "child*") AND ("child*" NEAR/3 "c"))',
        [
            ("chain", '(("a" NEAR/3 "child*") AND ("child*" NEAR/3 "c"))'),
            ("braces-wildcard", "child*"),
            ("braces-wildcard", "child*"),
        ],
    ),
]


def test_translate_gives_the_contract_example(wos_sdg):
    found = wos_sdg.translate('{a*} W/3 "b" W/3 "c"')
    assert found.text == '(("a*" NEAR/3 "b") AND ("b" NEAR/3 "c"))'
    assert found.notes == [
        ("chain", '(("a*" NEAR/3 "b") AND ("b" NEAR/3 "c"))'),
        ("braces-wildcard", "a*"),
        ("short-stem", "a*"),
    ]


@pytest.mark.parametrize(("query", "text", "expected"), TRANSLATED)
def test_translate_gives_the_exact_text_and_notes(wos_sdg, query, text, expected):
    found = wos_sdg.translate(query)
    assert found.text == text
    assert isinstance(found.notes, list)
    assert found.notes == expected


def test_translation_is_a_named_tuple_of_text_and_notes(wos_sdg):
    assert issubclass(wos_sdg.Translation, tuple)
    assert wos_sdg.Translation._fields == ("text", "notes")
    found = wos_sdg.translate('"a" OR "b"')
    assert isinstance(found, wos_sdg.Translation)
    text, notes = found
    assert text == '("a" OR "b")'
    assert notes == []
    assert found == ('("a" OR "b")', [])
    assert found == wos_sdg.Translation(text='("a" OR "b")', notes=[])


@pytest.mark.parametrize("query", ROUND_TRIP)
def test_translate_text_is_write_wos_of_read_scopus(wos_sdg, query):
    assert wos_sdg.translate(query).text == wos_sdg.write_wos(
        wos_sdg.read_scopus(query)
    )


@pytest.mark.parametrize("query", ROUND_TRIP)
def test_translate_adds_only_its_two_codes_to_the_notes_of_the_tree(wos_sdg, query):
    found = wos_sdg.translate(query).notes
    kept = [pair for pair in found if pair[0] not in ("chain", "braces-wildcard")]
    assert kept == wos_sdg.notes(wos_sdg.read_scopus(query))


@pytest.mark.parametrize(
    "query",
    [
        '"a" PRE/3 "b"',
        '"a" W/3 ("b" AND "c")',
        'TITLE ( "a" )',
        '{a "b"}',
        "",
        '"a" "b"',
    ],
)
def test_translate_raises_where_read_scopus_raises(wos_sdg, query):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.translate(query)


# --------------------------------------------------------------------------
# siris_expression
# --------------------------------------------------------------------------

SIRIS = [
    # No extra term.
    ("climate change", None, '"climate change"', []),
    ("climate change", "", '"climate change"', []),
    ("climate change", "   ", '"climate change"', []),
    ("Poverty", None, '"Poverty"', []),
    # One.
    ("acidification", "ocean", '("acidification" AND "ocean")', []),
    (
        "clean water",
        "developing countries",
        '("clean water" AND "developing countries")',
        [],
    ),
    # Several.
    ("acidification", "ocean|sea", '("acidification" AND ("ocean" OR "sea"))', []),
    (
        "ableism",
        "law|policy|state|public sector",
        '("ableism" AND ("law" OR "policy" OR "state" OR "public sector"))',
        [],
    ),
    # Each is stripped, inner white space collapsed.
    ("  climate   change ", None, '"climate change"', []),
    ("\tclimate\nchange", "", '"climate change"', []),
    (" acid  rain ", "  ocean ", '("acid rain" AND "ocean")', []),
    (
        "acid rain",
        " open  sea | coast |\tlake",
        '("acid rain" AND ("open sea" OR "coast" OR "lake"))',
        [],
    ),
    # An empty extra term is dropped.
    ("acidification", "ocean|", '("acidification" AND "ocean")', []),
    ("acidification", "|ocean", '("acidification" AND "ocean")', []),
    ("acidification", "ocean| |sea", '("acidification" AND ("ocean" OR "sea"))', []),
    ("acidification", "ocean||sea|", '("acidification" AND ("ocean" OR "sea"))', []),
    ("acidification", "|", '"acidification"', []),
    ("acidification", " | | ", '"acidification"', []),
    # Notes, as `notes` gives them for the tree.
    ("El Niño", None, '"El Niño"', [("non-ascii", "El Niño")]),
    (
        "gross domestic product (gdp)",
        "",
        '"gross domestic product (gdp)"',
        [("parenthesis", "gross domestic product (gdp)")],
    ),
    (
        "El Niño",
        "climate",
        '("El Niño" AND "climate")',
        [("non-ascii", "El Niño")],
    ),
    (
        "oscillation",
        "El Niño|la niña (enso)|ocean",
        '("oscillation" AND ("El Niño" OR "la niña (enso)" OR "ocean"))',
        [
            ("non-ascii", "El Niño"),
            ("non-ascii", "la niña (enso)"),
            ("parenthesis", "la niña (enso)"),
        ],
    ),
    (
        "product (gdp)",
        "café",
        '("product (gdp)" AND "café")',
        [("parenthesis", "product (gdp)"), ("non-ascii", "café")],
    ),
]


@pytest.mark.parametrize(("keyword", "extra", "text", "expected"), SIRIS)
def test_siris_expression_gives_the_exact_text_and_notes(
    wos_sdg, keyword, extra, text, expected
):
    found = wos_sdg.siris_expression(keyword, extra)
    assert isinstance(found, wos_sdg.Translation)
    assert found.text == text
    assert found.notes == expected


@pytest.mark.parametrize(
    ("keyword", "extra"),
    [
        # An empty keyword.
        ("", None),
        ("", "ocean"),
        ("   ", None),
        ("\t\n", "ocean|sea"),
        # A double quote, in the keyword or in an extra term.
        ('say "no"', None),
        ('"', ""),
        ('climate "change"', "ocean"),
        ("climate change", 'the "ocean"'),
        ("climate change", 'ocean|"sea"'),
    ],
)
def test_siris_expression_raises_on_an_empty_keyword_and_on_a_double_quote(
    wos_sdg, keyword, extra
):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.siris_expression(keyword, extra)


@pytest.mark.parametrize(
    ("keyword", "extra", "expected"),
    [
        ("climate change", None, term("climate change")),
        ("acidification", "ocean", all_of(term("acidification"), term("ocean"))),
        (
            "acidification",
            "ocean|open sea",
            all_of(term("acidification"), any_of(term("ocean"), term("open sea"))),
        ),
    ],
)
def test_siris_expression_is_read_back_by_read_wos(wos_sdg, keyword, extra, expected):
    assert wos_sdg.read_wos(wos_sdg.siris_expression(keyword, extra).text) == expected


# --------------------------------------------------------------------------
# goal_query
# --------------------------------------------------------------------------

GOALS = [
    # The contract's example.
    (['"a"', '("b" AND "c")', '"a"'], 'TS=("a" OR ("b" AND "c"))\n'),
    # One expression.
    (['"a"'], 'TS=("a")\n'),
    (['("a" OR "b")'], 'TS=(("a" OR "b"))\n'),
    # Several, in the order given.
    (['"b"', '"a"'], 'TS=("b" OR "a")\n'),
    (
        ['("a" NEAR/3 "b")', '"c"', '("d" NOT "e")'],
        'TS=(("a" NEAR/3 "b") OR "c" OR ("d" NOT "e"))\n',
    ),
    # A repeat is dropped where it comes second.
    (['"a"', '"a"'], 'TS=("a")\n'),
    (['"a"', '"a"', '"a"'], 'TS=("a")\n'),
    (['"b"', '"a"', '"b"', '"c"', '"a"'], 'TS=("b" OR "a" OR "c")\n'),
    (
        ['("a" AND "b")', '"c"', '("a" AND "b")', '("b" AND "a")'],
        'TS=(("a" AND "b") OR "c" OR ("b" AND "a"))\n',
    ),
]


@pytest.mark.parametrize(("expressions", "expected"), GOALS)
def test_goal_query_gives_the_exact_line(wos_sdg, expressions, expected):
    assert wos_sdg.goal_query(expressions) == expected


def test_goal_query_raises_on_an_empty_list(wos_sdg):
    with pytest.raises(wos_sdg.QueryError):
        wos_sdg.goal_query([])


def test_goal_query_is_read_back_as_an_or_of_its_expressions(wos_sdg):
    line = wos_sdg.goal_query(['"a"', '("b" AND "c")', '"a"', '("d" OR "e")'])
    assert wos_sdg.read_wos(line) == any_of(A, all_of(B, C), any_of(D, E))


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------


def notes_rows(text):
    """Return the rows of a `NOTES.tsv` text after its header, each a list of
    its columns. The header is checked by its own test."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.split("\t") for line in lines[1:]]


def test_build_gives_the_65_goal_files_and_the_notes(built):
    assert isinstance(built, dict)
    assert len(GOAL_FILES) == 65
    assert set(built) == set(BUILT_FILES)
    assert len(built) == 66


def test_build_gives_the_notes_last(built):
    assert list(built)[-1] == "NOTES.tsv"


def test_build_gives_text(built):
    assert [name for name, text in built.items() if not isinstance(text, str)] == []


@pytest.mark.parametrize("name", GOAL_FILES)
def test_a_built_goal_file_is_one_line_under_the_tag(wos_sdg, built, name):
    text = built[name]
    assert text.startswith("TS=(")
    assert text.endswith(")\n")
    assert text.count("\n") == 1
    wos_sdg.read_wos(text)


def test_build_gives_the_elsevier_goal_of_a_second_reading(wos_sdg, built):
    """The first goal of Elsevier, read here from the workbook: one query,
    translated and put under the tag."""
    import openpyxl

    book = openpyxl.load_workbook(ELSEVIER_BOOK)
    rows = list(book.active.iter_rows(values_only=True))[1:]
    queries = [row[1] for row in rows if int(row[0]) == 1 and row[1]]
    assert len(queries) == 1
    expected = wos_sdg.goal_query([wos_sdg.translate(queries[0]).text])
    assert built["elsevier/SDG-01.txt"] == expected


def test_build_gives_the_elsevier_notes_of_a_second_reading(wos_sdg, built):
    """The rows of `NOTES.tsv` for Elsevier are the notes of `translate` for
    each row of the workbook that has a query, goals in order, one expression
    per goal and so `line` 1."""
    import openpyxl

    book = openpyxl.load_workbook(ELSEVIER_BOOK)
    rows = list(book.active.iter_rows(values_only=True))[1:]
    queries = {int(row[0]): row[1] for row in rows if row[1]}
    assert len(queries) == len([row for row in rows if row[1]])
    expected = [
        ["elsevier", f"SDG-{goal:02d}", "1", code, piece]
        for goal in sorted(queries)
        for code, piece in wos_sdg.translate(queries[goal]).notes
    ]
    found = [row for row in notes_rows(built["NOTES.tsv"]) if row[0] == "elsevier"]
    assert found == expected


def test_build_gives_the_siris_goal_as_many_expressions_as_a_second_reading(
    wos_sdg, built
):
    """The first goal of SIRIS holds one expression per distinct row of the
    vocabulary whose goal column is `SDG 1`, whatever its sheet."""
    import openpyxl

    book = openpyxl.load_workbook(SIRIS_BOOK)
    distinct = set()
    for sheet in book.worksheets:
        if sheet.title == "README":
            continue
        for row in list(sheet.iter_rows(values_only=True))[1:]:
            if row[0] != "SDG 1":
                continue
            keyword = " ".join(row[2].split())
            extra = [" ".join(part.split()) for part in (row[3] or "").split("|")]
            distinct.add((keyword, tuple(part for part in extra if part)))
    assert len(distinct) > 1

    tree = wos_sdg.read_wos(built["siris/SDG-01.txt"])
    operands = len(tree[1]) if tree[0] == "or" else 1
    assert operands == len(distinct)


# --------------------------------------------------------------------------
# NOTES.tsv, as built
# --------------------------------------------------------------------------


def test_the_notes_file_has_the_stated_header(built):
    assert built["NOTES.tsv"].split("\n")[0] == "system\tsdg\tline\tcode\tpiece"


def test_the_notes_file_has_five_columns_in_every_row(built):
    rows = notes_rows(built["NOTES.tsv"])
    assert [row for row in rows if len(row) != 5] == []


def test_the_notes_file_holds_only_the_seven_codes(built):
    rows = notes_rows(built["NOTES.tsv"])
    assert {row[3] for row in rows} <= CODES


def test_the_notes_file_names_systems_goals_and_lines_as_stated(built):
    rows = notes_rows(built["NOTES.tsv"])
    assert {row[0] for row in rows} <= set(SYSTEMS)
    assert [row[1] for row in rows if not re.fullmatch(r"SDG-\d\d", row[1])] == []
    assert [row[2] for row in rows if not re.fullmatch(r"[1-9]\d*", row[2])] == []
    assert [row for row in rows if f"{row[0]}/{row[1]}.txt" not in GOAL_FILES] == []
    assert [row for row in rows if row[4] == ""] == []


def test_the_notes_file_is_in_the_order_of_systems_then_goals(built):
    rows = notes_rows(built["NOTES.tsv"])
    keys = [(SYSTEMS.index(row[0]), row[1]) for row in rows]
    assert keys == sorted(keys)


# --------------------------------------------------------------------------
# The shipped files
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", BUILT_FILES)
def test_a_shipped_file_is_what_build_gives_byte_for_byte(built, name):
    assert (SHIPPED_DIR / name).read_bytes() == built[name].encode("utf-8")


@pytest.mark.parametrize("name", GOAL_FILES)
def test_a_shipped_goal_file_is_one_line_read_back_by_read_wos(wos_sdg, name):
    text = (SHIPPED_DIR / name).read_bytes().decode("utf-8")
    assert text.startswith("TS=(")
    assert text.endswith("\n")
    assert text.count("\n") == 1
    wos_sdg.read_wos(text)


def test_the_shipped_notes_file_is_as_the_contract_states():
    text = (SHIPPED_DIR / "NOTES.tsv").read_bytes().decode("utf-8")
    assert text.split("\n")[0] == "system\tsdg\tline\tcode\tpiece"
    rows = notes_rows(text)
    assert [row for row in rows if len(row) != 5] == []
    assert {row[3] for row in rows} <= CODES
    assert {row[0] for row in rows} <= set(SYSTEMS)
    keys = [(SYSTEMS.index(row[0]), row[1]) for row in rows]
    assert keys == sorted(keys)


def test_sha256sums_lists_exactly_the_66_files_with_their_hashes():
    lines = (SHIPPED_DIR / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    listed = {}
    for line in lines:
        # The format of sha256sum: the hash, a space, a space or a star, the name.
        found = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        assert found is not None, line
        assert found.group(2) not in listed
        listed[found.group(2)] = found.group(1)
    assert len(listed) == 66
    assert set(listed) == set(BUILT_FILES)
    expected = {
        name: hashlib.sha256((SHIPPED_DIR / name).read_bytes()).hexdigest()
        for name in BUILT_FILES
    }
    assert listed == expected


def test_the_readme_is_shipped_and_not_empty():
    assert (SHIPPED_DIR / "README.md").read_text(encoding="utf-8").strip() != ""
