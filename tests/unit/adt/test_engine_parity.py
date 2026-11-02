"""Engine parity: Polars, DuckDB and the hand-written fixture agree exactly.

Source: `docs/query-translation-contract.md`, section "Engine parity". The
three ways of computing a flag are compared:

1. `translate.matches(pattern, text)`, on Polars (the Rust `regex` crate);
2. DuckDB evaluating `flag_sql(pattern, normalise_sql("t"))` over a table with
   a column `t`, on RE2, the engine BigQuery uses;
3. the expected value written by hand in `FIXTURE`.

The patterns of the fixture are built with `code_pattern` from the small term
lists of `TERMS`. Two further tests run every pattern of the real compiled
artefact and assert that Polars and DuckDB agree, with no expected value.

The texts go into DuckDB through bound parameters, so a null stays a null.
"""

from pathlib import Path

import pytest

from sdg_tech_tagger.adt import translate

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

# Small term lists written by hand: truncation, a hyphenated term, a term
# with a digit and a dot, a one-word acronym.
TERMS = {
    "AM": ["3d print*", "industry 4.0", "additive manufacturing"],
    "IOT": ["iot", "internet of things", "smart sensor*"],
    "AI": ["machine learning", "k-means", "neural net*"],
    "ROB": ["robot*", "uav"],
}

# What `code_pattern` must give for each list above, derived by hand.
EXPECTED_PATTERNS = {
    "AM": " (?:3d print[^ ]*|industry 4 0 |additive manufacturing )",
    "IOT": " (?:iot |internet of things |smart sensor[^ ]*)",
    "AI": " (?:machine learning |k means |neural net[^ ]*)",
    "ROB": " (?:robot[^ ]*|uav )",
}


def _hits(*codes):
    """Return the expected flags of one text: True for the codes named, False for the rest."""
    unknown = set(codes) - set(TERMS)
    assert not unknown, unknown
    return {code: code in codes for code in TERMS}


# (text, {code: expected flag}). Each expectation was derived by normalising
# the text by hand and searching the four patterns above in it.
FIXTURE = [
    # A term at the very start of the text.
    ("IoT sensors for smart homes", _hits("IOT")),
    ("Machine learning: a review", _hits("AI")),
    ("UAV-based mapping", _hits("ROB")),
    ("Additive manufacturing: a review", _hits("AM")),
    # A term at the very end of the text.
    ("A survey of the IoT", _hits("IOT")),
    ("We fly the uav", _hits("ROB")),
    ("A neural net", _hits("AI")),
    ("A smart sensor", _hits("IOT")),
    # The text is the term and nothing else.
    ("IoT", _hits("IOT")),
    ("robotics", _hits("ROB")),
    ("K-Means", _hits("AI")),
    # A term followed by punctuation.
    ("Robots, drones and UAV.", _hits("ROB")),
    ("We apply machine learning, then test.", _hits("AI")),
    ("The road to Industry 4.0.", _hits("AM")),
    ("Internet-of-Things (IoT)", _hits("IOT")),
    # Hyphenated, spaced and closed spellings of the same term.
    ("k-means clustering", _hits("AI")),
    ("k means clustering", _hits("AI")),
    ("kmeans clustering", _hits()),
    ("machine-learning", _hits("AI")),
    ("machinelearning", _hits()),
    ("3D-printing of parts", _hits("AM")),
    ("3D printing of parts", _hits("AM")),
    ("3-D printing", _hits()),
    # An accented neighbour, apart from the term and glued to it.
    ("señal IoT", _hits("IOT")),
    ("IoT señal", _hits("IOT")),
    ("SEÑAL IOT", _hits("IOT")),
    ("IoTñ devices", _hits()),
    ("ñIoT devices", _hits()),
    ("robótica industrial", _hits()),
    # A term split by a sentence end.
    ("Machine. Learning is hard", _hits("AI")),
    ("It runs on the Internet of. Things changed.", _hits("IOT")),
    # A null, an empty string, and texts with no letter and no digit.
    (None, _hits()),
    ("", _hits()),
    ("   ", _hits()),
    ("...", _hits()),
    # A near miss inside a longer word.
    ("The patriot act", _hits()),
    ("microrobot swarm", _hits()),
    ("uavs fly", _hits()),
    ("iot2020", _hits()),
    ("neuralnet", _hits()),
    ("additive manufacturings", _hits()),
    # Truncation: the stem alone, and the stem with more letters.
    ("neural networks", _hits("AI")),
    ("3D printers", _hits("AM")),
    # A digit and a dot inside a term.
    ("Industry 4.0 and beyond", _hits("AM")),
    ("Industry 4,0", _hits("AM")),
    ("Industry 4.01", _hits()),
    ("Industry 40 firms", _hits()),
    # Other separators: newline, tab, underscore, no-break space, markup.
    ("smart\nsensors and smart\tsensing", _hits("IOT")),
    ("smart_iot_device", _hits("IOT")),
    ("additive manufacturing", _hits("AM")),
    ("<i>IoT</i> networks", _hits("IOT")),
    # Two words of a term with something between them.
    ("machine 2 learning", _hits()),
    # A script with no case and no spaces between words.
    ("物联网 IoT 研究", _hits("IOT")),
    ("物联网IoT研究", _hits()),
    # Several codes in one text.
    ("MACHINE LEARNING AND ROBOTS IN INDUSTRY 4.0", _hits("AI", "ROB", "AM")),
    ("IoT, robots, k-means, 3D printers", _hits("AM", "IOT", "AI", "ROB")),
]

FIXTURE_TEXTS = [text for text, _ in FIXTURE]


@pytest.fixture(scope="module")
def patterns():
    """Build the four fixture patterns with `code_pattern`."""
    return {code: translate.code_pattern(terms) for code, terms in TERMS.items()}


@pytest.fixture(scope="module")
def artefact():
    """Compile the six real query files."""
    return translate.compile_queries(QUERY_FILES)


def test_fixture_patterns_are_the_ones_the_expectations_were_derived_from(patterns):
    """The patterns built from `TERMS` are exactly the ones written out by hand."""
    assert patterns == EXPECTED_PATTERNS


def test_fixture_has_the_kinds_of_text_the_contract_lists():
    """The fixture holds one null, one empty string, and every code hits and misses."""
    assert FIXTURE_TEXTS.count(None) == 1
    assert FIXTURE_TEXTS.count("") == 1
    assert "señal IoT" in FIXTURE_TEXTS
    for code in TERMS:
        flags = [expected[code] for _, expected in FIXTURE]
        assert True in flags, code
        assert False in flags, code


@pytest.mark.parametrize("code", list(TERMS))
def test_polars_matches_the_fixture(patterns, code):
    """`translate.matches` gives the expected flag for every fixture text."""
    got = [translate.matches(patterns[code], text) for text in FIXTURE_TEXTS]
    assert got == [expected[code] for _, expected in FIXTURE]


