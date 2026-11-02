"""Tests of Amendment 1 of the query translation contract, from the contract alone.

Source of every expected value: `docs/query-translation-contract.md`, section
"Amendment 1, 2026-10-03: plural tolerance and carried columns". Expected
patterns are derived by hand from the two plural rules; the spaces at the ends
of patterns and the exact group syntax `(?:s|es)?` and `(?:y|ies)` are part of
the values and are asserted exactly.

What is covered:

- `term_pattern`, `code_pattern` and `compile_queries` with the new keyword
  `plural_tolerant`, its combination with `hyphen_closed_form`, and that the
  default leaves every output as it was;
- `translate.matches` on plural-tolerant patterns;
- the artefact's fifth key, `plural_tolerant`, after `hyphen_closed_form`;
- engine parity of plural-tolerant patterns, Polars against DuckDB on RE2;
- `render_adt_flags` with `bigquery["carry_columns"]`, and its new header.

The texts go into DuckDB through bound parameters, so a null stays a null.
"""

import json
import re
from pathlib import Path

import pytest

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

# The value of the artefact's "normalisation" key, as the contract's JSON
# block writes it (there the backslashes are doubled by JSON escaping).
NORMALISATION = (
    r"lower-case; every run of characters outside \p{L}\p{N} becomes one space; "
    "trimmed; one space added at each end"
)

# The five top-level keys of the amended artefact, in the contract's order.
ARTEFACT_KEYS = ["version", "normalisation", "hyphen_closed_form", "plural_tolerant", "definitions"]

# The two groups the amendment adds to the pattern alphabet, written once.
S_ES = "(?:s|es)?"
Y_IES = "(?:y|ies)"


def _code(term_patterns):
    """Join hand-written term patterns the way the contract builds a code pattern."""
    return " (?:" + "|".join(term_patterns) + ")"


# --------------------------------------------------------------------------
# One term
# --------------------------------------------------------------------------


# The eight rows of the amendment's plural table.
@pytest.mark.parametrize(
    ("term", "plural_tolerant", "expected"),
    [
        ("random forest", True, "random forest(?:s|es)? "),
        ("smart city", True, "smart cit(?:y|ies) "),
        ("smart key", True, "smart key(?:s|es)? "),
        ("robot*", True, "robot[^ ]*"),
        ("iot", True, "iot(?:s|es)? "),
        ("industry 4.0", True, "industry 4 0 "),
        ("k-means", True, "k means(?:s|es)? "),
        ("k-means", False, "k means "),
    ],
)
def test_term_pattern_plural_table(term, plural_tolerant, expected):
    """Each row of the plural table gives exactly the listed regex."""
    assert translate.term_pattern(term, plural_tolerant=plural_tolerant) == expected


def test_term_pattern_plural_and_hyphen_closed_form_combine():
    """The amendment's combination example, character for character."""
    assert (
        translate.term_pattern("machine-to-machine", hyphen_closed_form=True, plural_tolerant=True)
        == "machine ?to ?machine(?:s|es)? "
    )


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        # A consonant before the final y: the y becomes the group.
        ("ontology", "ontolog(?:y|ies) "),
        ("privacy", "privac(?:y|ies) "),
        ("stereolithography", "stereolithograph(?:y|ies) "),
        ("hyper connectivity", "hyper connectivit(?:y|ies) "),
        ("long short term memory", "long short term memor(?:y|ies) "),
        # A vowel before the final y: the group for s or es is appended.
        ("relay", "relay(?:s|es)? "),
        ("convoy", "convoy(?:s|es)? "),
        ("guy", "guy(?:s|es)? "),
        ("smart key", "smart key(?:s|es)? "),
        # A last word already ending in s, x or another letter still gets it.
        ("internet of things", "internet of things(?:s|es)? "),
        ("cybernetics", "cybernetics(?:s|es)? "),
        ("bounding box", "bounding box(?:s|es)? "),
        ("5g", "5g(?:s|es)? "),
        ("word2vec", "word2vec(?:s|es)? "),
        # Only the last word changes, whatever the earlier words end with.
        ("city planning", "city planning(?:s|es)? "),
        ("smart cities network", "smart cities network(?:s|es)? "),
        ("water resource* management", "water resource[^ ]* management(?:s|es)? "),
        # A last word ending in a digit is left as it is.
        ("industry 4.0", "industry 4 0 "),
        ("web 2", "web 2 "),
        ("h2o2", "h2o2 "),
        # A truncated last word is left as it is.
        ("robot*", "robot[^ ]*"),
        ("3d print*", "3d print[^ ]*"),
        ("data center*", "data center[^ ]*"),
        ("wireless* sensor* network*", "wireless[^ ]* sensor[^ ]* network[^ ]*"),
        ("smart factor*", "smart factor[^ ]*"),
        # Stripping and lower-casing still come first.
        ("  Smart City ", "smart cit(?:y|ies) "),
        ("IoT", "iot(?:s|es)? "),
        # Separators are unchanged: one space, whatever the run was.
        ("machine-to-machine", "machine to machine(?:s|es)? "),
        ("a.b", "a b(?:s|es)? "),
    ],
)
def test_term_pattern_plural_derived_cases(term, expected):
    """Further terms, each compiled by hand with the two plural rules."""
    assert translate.term_pattern(term, plural_tolerant=True) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("machine-to-machine", "machine ?to ?machine(?:s|es)? "),
        ("cyber-physical system", "cyber ?physical system(?:s|es)? "),
        ("hyper-connectivity", "hyper ?connectivit(?:y|ies) "),
        ("multi-cloud*", "multi ?cloud[^ ]*"),
        ("industry-4.0", "industry ?4 0 "),
        ("k-means", "k ?means(?:s|es)? "),
        ("smart city", "smart cit(?:y|ies) "),
    ],
)
def test_term_pattern_plural_with_hyphen_closed_form(term, expected):
    """With both switches on, hyphens give ` ?` and the last word gets its group."""
    assert translate.term_pattern(term, hyphen_closed_form=True, plural_tolerant=True) == expected


@pytest.mark.parametrize(
    "term",
    ["colo?r", "*bot", "ro*bot", "naïve bayes", "", "robot$", "*", "-", "café"],
)
def test_term_pattern_plural_still_rejects_what_it_cannot_compile(term):
    """The errors of the term rules do not depend on `plural_tolerant`."""
    with pytest.raises(QueryError):
        translate.term_pattern(term, plural_tolerant=True)
    with pytest.raises(QueryError):
        translate.term_pattern(term, hyphen_closed_form=True, plural_tolerant=True)


# The pattern rows of the original term table, which the default must keep.
ORIGINAL_TERM_TABLE = [
    ("iot", False, "iot "),
    ("robot*", False, "robot[^ ]*"),
    ("machine learning", False, "machine learning "),
    ("3d print*", False, "3d print[^ ]*"),
    ("industry 4.0", False, "industry 4 0 "),
    ("k-means", False, "k means "),
    ("k-means", True, "k ?means "),
    ("computer-mediated realit*", True, "computer ?mediated realit[^ ]*"),
    ("water resource* management", False, "water resource[^ ]* management "),
    ("smart city", False, "smart city "),
    ("smart key", False, "smart key "),
    ("random forest", False, "random forest "),
    ("machine-to-machine", True, "machine ?to ?machine "),
]


@pytest.mark.parametrize(("term", "hyphen_closed_form", "expected"), ORIGINAL_TERM_TABLE)
def test_term_pattern_default_is_unchanged(term, hyphen_closed_form, expected):
    """Without the keyword, and with it False, every pattern is what it was."""
    assert translate.term_pattern(term, hyphen_closed_form=hyphen_closed_form) == expected
    assert (
        translate.term_pattern(term, hyphen_closed_form=hyphen_closed_form, plural_tolerant=False)
        == expected
    )


# --------------------------------------------------------------------------
# One code
# --------------------------------------------------------------------------


def test_code_pattern_plural_of_the_matching_example():
    """The pattern the amendment's matching table is built on, written out by hand."""
    assert (
        translate.code_pattern(["random forest", "smart city"], plural_tolerant=True)
        == " (?:random forest(?:s|es)? |smart cit(?:y|ies) )"
    )


def test_code_pattern_plural_combination_example():
    """The combination example, as a code of one term."""
    assert (
        translate.code_pattern(
            ["machine-to-machine"], hyphen_closed_form=True, plural_tolerant=True
        )
        == " (?:machine ?to ?machine(?:s|es)? )"
    )


def test_code_pattern_passes_plural_tolerant_to_every_term():
    """The switch reaches each term of the alternation, in the order given."""
    terms = ["k-means", "smart city", "robot*", "industry 4.0", "relay"]
    assert (
        translate.code_pattern(terms, plural_tolerant=True)
        == " (?:k means(?:s|es)? |smart cit(?:y|ies) |robot[^ ]*|industry 4 0 |relay(?:s|es)? )"
    )
    assert (
        translate.code_pattern(terms, hyphen_closed_form=True, plural_tolerant=True)
        == " (?:k ?means(?:s|es)? |smart cit(?:y|ies) |robot[^ ]*|industry 4 0 |relay(?:s|es)? )"
    )


def test_code_pattern_plural_of_no_term_raises():
    """An empty sequence of terms still raises `QueryError`."""
    with pytest.raises(QueryError):
        translate.code_pattern([], plural_tolerant=True)


def test_code_pattern_plural_has_no_quote_and_no_backslash():
    """The new groups bring no quote and no backslash: SQL raw literals stay safe."""
    terms = ["o'neil", 'say "x" now', "back\\slash", "smart city", "industry 4.0", "3d print*"]
    pattern = translate.code_pattern(terms, plural_tolerant=True)
    assert pattern == (
        " (?:o neil(?:s|es)? |say x now(?:s|es)? |back slash(?:s|es)? "
        "|smart cit(?:y|ies) |industry 4 0 |3d print[^ ]*)"
    )
    assert "'" not in pattern
    assert '"' not in pattern
    assert "\\" not in pattern


@pytest.mark.parametrize(
    ("terms", "expected"),
    [
        (
            ["3d print*", "iot", "machine learning", "robot*"],
            " (?:3d print[^ ]*|iot |machine learning |robot[^ ]*)",
        ),
        (["bitcoin", "blockchain*"], " (?:bitcoin |blockchain[^ ]*)"),
        (["random forest", "smart city"], " (?:random forest |smart city )"),
        (
            ["k-means", "iot", "computer-mediated realit*"],
            " (?:k means |iot |computer mediated realit[^ ]*)",
        ),
    ],
)
def test_code_pattern_default_is_unchanged(terms, expected):
    """Without the keyword, and with it False, every code pattern is what it was."""
    assert translate.code_pattern(terms) == expected
    assert translate.code_pattern(terms, plural_tolerant=False) == expected


def test_code_pattern_default_with_hyphen_closed_form_is_unchanged():
    """`hyphen_closed_form` alone gives what it gave before the amendment."""
    terms = ["k-means", "iot", "computer-mediated realit*"]
    expected = " (?:k ?means |iot |computer ?mediated realit[^ ]*)"
    assert translate.code_pattern(terms, hyphen_closed_form=True) == expected
    assert translate.code_pattern(terms, hyphen_closed_form=True, plural_tolerant=False) == expected


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------

PLURAL_MATCH_TERMS = ["random forest", "smart city"]


# The six rows of the amendment's matching table.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Random forests were trained", True),
        ("a random forest", True),
        ("Smart cities in Europe", True),
        ("the smart city", True),
        ("random forestry", False),
        ("smart citys", False),
    ],
)
def test_matches_plural_table(text, expected):
    """Each row of the amendment's matching table gives exactly the listed Boolean."""
    pattern = translate.code_pattern(PLURAL_MATCH_TERMS, plural_tolerant=True)
    assert translate.matches(pattern, text) is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("random forestes", True),
        ("Random-Forests.", True),
        ("RANDOM FOREST", True),
        ("random forestss", False),
        ("random forests2", False),
        ("random forestsñ", False),
        ("smart cityies", False),
        ("smart cit", False),
        ("smart cities, smart people", True),
        ("smart_cities", True),
        ("Smart\ncity", True),
        ("smartcities", False),
        ("", False),
        (None, False),
    ],
)
def test_matches_plural_derived_cases(text, expected):
    """Further texts, each derived by normalising by hand and searching the pattern."""
    pattern = translate.code_pattern(PLURAL_MATCH_TERMS, plural_tolerant=True)
    assert translate.matches(pattern, text) is expected


@pytest.mark.parametrize(
    ("text", "plain", "plural"),
    [
        ("Random forests were trained", False, True),
        ("a random forest", True, True),
        ("Smart cities in Europe", False, True),
        ("the smart city", True, True),
        ("random forestry", False, False),
        ("smart citys", False, False),
    ],
)
def test_matches_with_and_without_plural_tolerant(text, plain, plural):
    """Plural forms match only when the switch is on; the default is as before."""
    assert translate.matches(translate.code_pattern(PLURAL_MATCH_TERMS), text) is plain
    assert (
        translate.matches(translate.code_pattern(PLURAL_MATCH_TERMS, plural_tolerant=False), text)
        is plain
    )
    assert (
        translate.matches(translate.code_pattern(PLURAL_MATCH_TERMS, plural_tolerant=True), text)
        is plural
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("machine-to-machine", True),
        ("machine to machines", True),
        ("machinetomachines", True),
        ("Machine-to-Machinees", True),
        ("machine to machinery", False),
        ("machinetomachine", True),
    ],
)
def test_matches_plural_with_hyphen_closed_form(text, expected):
    """The combined pattern matches open, closed, singular and plural spellings."""
    pattern = translate.code_pattern(
        ["machine-to-machine"], hyphen_closed_form=True, plural_tolerant=True
    )
    assert translate.matches(pattern, text) is expected


# --------------------------------------------------------------------------
# Compiling the files
# --------------------------------------------------------------------------


def _write(path, text):
    """Write a hand-made query file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_compile_queries_plural_on_two_hand_written_files(tmp_path):
    """The whole amended artefact for two small files, value for value and key order."""
    one = _write(tmp_path / "one.txt", 'TS = (\n("Bitcoin") OR ("k-means") OR ("smart city")\n)')
    two = _write(
        tmp_path / "sub" / "two.txt", 'TS = ( ("Robot*") OR ("industry 4.0") OR ("Smart Key") )'
    )
    out = translate.compile_queries({"ZZ": two, "AA": one}, plural_tolerant=True)
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION,
        "hyphen_closed_form": False,
        "plural_tolerant": True,
        "definitions": [
            {
                "code": "ZZ",
                "source": "two.txt",
                "term_count": 3,
                "terms": ["robot*", "industry 4.0", "smart key"],
                "pattern": " (?:robot[^ ]*|industry 4 0 |smart key(?:s|es)? )",
            },
            {
                "code": "AA",
                "source": "one.txt",
                "term_count": 3,
                "terms": ["bitcoin", "k-means", "smart city"],
                "pattern": " (?:bitcoin(?:s|es)? |k means(?:s|es)? |smart cit(?:y|ies) )",
            },
        ],
    }
    assert list(out) == ARTEFACT_KEYS


def test_compile_queries_with_both_switches(tmp_path):
    """Both switches are recorded and both apply to every pattern."""
    one = _write(tmp_path / "one.txt", 'TS = ( ("Bitcoin") OR ("k-means") OR ("smart city") )')
    out = translate.compile_queries({"AA": one}, hyphen_closed_form=True, plural_tolerant=True)
    assert list(out) == ARTEFACT_KEYS
    assert out["hyphen_closed_form"] is True
    assert out["plural_tolerant"] is True
    assert out["definitions"] == [
        {
            "code": "AA",
            "source": "one.txt",
            "term_count": 3,
            "terms": ["bitcoin", "k-means", "smart city"],
            "pattern": " (?:bitcoin(?:s|es)? |k ?means(?:s|es)? |smart cit(?:y|ies) )",
        }
    ]


def test_compile_queries_default_writes_plural_tolerant_false(tmp_path):
    """Without the keyword the artefact says False and the patterns are as before."""
    one = _write(tmp_path / "one.txt", 'TS = ( ("Bitcoin") OR ("k-means") OR ("smart city") )')
    out = translate.compile_queries({"AA": one})
    assert out == {
        "version": 1,
        "normalisation": NORMALISATION,
        "hyphen_closed_form": False,
        "plural_tolerant": False,
        "definitions": [
            {
                "code": "AA",
                "source": "one.txt",
                "term_count": 3,
                "terms": ["bitcoin", "k-means", "smart city"],
                "pattern": " (?:bitcoin |k means |smart city )",
            }
        ],
    }
    assert list(out) == ARTEFACT_KEYS


def test_compile_queries_plural_still_stops_on_a_bad_term(tmp_path):
    """A term with another wildcard raises `QueryError` with the switch on too."""
    bad = _write(tmp_path / "bad.txt", 'TS = ( ("robot*") OR ("colo?r") )')
    with pytest.raises(QueryError):
        translate.compile_queries({"BAD": bad}, plural_tolerant=True)


@pytest.fixture(scope="module")
def default_artefact():
    """Compile the six real query files without the new keyword."""
    return translate.compile_queries(QUERY_FILES)


@pytest.fixture(scope="module")
def plural_artefact():
    """Compile the six real query files with `plural_tolerant=True`."""
    return translate.compile_queries(QUERY_FILES, plural_tolerant=True)


def test_real_default_artefact_has_five_keys_in_order(default_artefact):
    """The default artefact has the five keys, `plural_tolerant` after `hyphen_closed_form`."""
    assert list(default_artefact) == ARTEFACT_KEYS
    assert default_artefact["version"] == 1
    assert default_artefact["hyphen_closed_form"] is False
    assert default_artefact["plural_tolerant"] is False


def test_real_default_artefact_equals_an_explicit_false(default_artefact):
    """Passing `plural_tolerant=False` gives the same artefact as passing nothing."""
    out = translate.compile_queries(QUERY_FILES, plural_tolerant=False)
    assert out == default_artefact
    assert list(out) == ARTEFACT_KEYS


def test_real_default_artefact_patterns_are_unchanged(default_artefact):
    """With the default, each pattern is `code_pattern(terms)` as before."""
    for definition in default_artefact["definitions"]:
        assert definition["pattern"] == translate.code_pattern(definition["terms"])


def test_real_plural_artefact_top_level(plural_artefact):
    """Five keys in order, version still 1, the switch recorded as a real bool."""
    assert list(plural_artefact) == ARTEFACT_KEYS
    assert plural_artefact["version"] == 1
    assert type(plural_artefact["version"]) is int
    assert plural_artefact["normalisation"] == NORMALISATION
    assert plural_artefact["hyphen_closed_form"] is False
    assert plural_artefact["plural_tolerant"] is True
    assert [d["code"] for d in plural_artefact["definitions"]] == [
        "AI",
        "IOT",
        "CI",
        "BL",
        "ROB",
        "AM",
    ]


def test_real_plural_artefact_pattern_is_code_pattern_of_terms(plural_artefact):
    """Each pattern equals `code_pattern(terms, plural_tolerant=True)`."""
    for definition in plural_artefact["definitions"]:
        assert definition["pattern"] == translate.code_pattern(
            definition["terms"], plural_tolerant=True
        ), definition["code"]


def test_real_plural_artefact_terms_do_not_depend_on_the_switch(plural_artefact, default_artefact):
    """The switch changes patterns only: terms, counts and sources stay as parsed."""
    for plural, plain in zip(
        plural_artefact["definitions"], default_artefact["definitions"], strict=True
    ):
        assert plural["code"] == plain["code"]
        assert plural["source"] == plain["source"]
        assert plural["terms"] == plain["terms"]
        assert plural["term_count"] == plain["term_count"]
        text = QUERY_FILES[plural["code"]].read_text(encoding="utf-8")
        assert plural["terms"] == parse_terms(text)


def test_real_artefact_with_both_switches():
    """Both switches on: every pattern is `code_pattern` with both, both recorded."""
    out = translate.compile_queries(QUERY_FILES, hyphen_closed_form=True, plural_tolerant=True)
    assert list(out) == ARTEFACT_KEYS
    assert out["hyphen_closed_form"] is True
    assert out["plural_tolerant"] is True
    for definition in out["definitions"]:
        assert definition["pattern"] == translate.code_pattern(
            definition["terms"], hyphen_closed_form=True, plural_tolerant=True
        ), definition["code"]
    ai = out["definitions"][0]
    assert "|generative adversarial network(?:s|es)? |k ?means(?:s|es)? |" in ai["pattern"]


def test_real_plural_artefact_survives_json(plural_artefact):
    """The amended artefact is plain data and keeps its key order through JSON."""
    text = json.dumps(plural_artefact)
    back = json.loads(text)
    assert back == plural_artefact
    assert list(back) == ARTEFACT_KEYS
    assert '"hyphen_closed_form": false, "plural_tolerant": true, "definitions": ' in text


# The Blockchain, Robotics, IoT and additive manufacturing patterns with the
# switch on, each term compiled by hand from the file.
BLOCKCHAIN_PLURAL = _code(
    [
        "altcoin(?:s|es)? ",
        "bitcoin(?:s|es)? ",
        "blockchain[^ ]*",
        "cryptocurrenc[^ ]*",
        "private blockchain[^ ]*",
        "public blockchain[^ ]*",
    ]
)
ROBOTICS_PLURAL = _code(
    [
        "autonomous car[^ ]*",
        "autonomous underwater vehicle[^ ]*",
        "autonomous vehicle[^ ]*",
        "auv(?:s|es)? ",
        "chatbot[^ ]*",
        "cybernetics(?:s|es)? ",
        "drone[^ ]*",
        "humanoid robot[^ ]*",
        "manipulator[^ ]*",
        "mobile manipulator[^ ]*",
        "mobile robot[^ ]*",
        "robot[^ ]*",
        "robotic[^ ]*",
        "self driving car[^ ]*",
        "self driving vehicle[^ ]*",
        "uav(?:s|es)? ",
        "ugv(?:s|es)? ",
        "uncrewed vehicle[^ ]*",
        "unmanned aerial vehicle[^ ]*",
        "unmanned air vehicle[^ ]*",
        "unmanned aircraft system[^ ]*",
        "unmanned ground vehicle[^ ]*",
        "unmanned spacecraft(?:s|es)? ",
        "unmanned underwater vehicles[^ ]*",
        "unmanned vehicle[^ ]*",
    ]
)
IOT_PLURAL = _code(
    [
        "connected device[^ ]*",
        "connected home[^ ]*",
        "cyber physical system[^ ]*",
        "human machine interface[^ ]*",
        "hyper connectivit(?:y|ies) ",
        "industrial internet of things(?:s|es)? ",
        "intelligent factor[^ ]*",
        "internet of everything(?:s|es)? ",
        "internet of things(?:s|es)? ",
        "iot(?:s|es)? ",
        "machine to enterprise(?:s|es)? ",
        "machine to human(?:s|es)? ",
        "machine to machine(?:s|es)? ",
        "pervasive sensing(?:s|es)? ",
        "sensor network[^ ]*",
        "smart device[^ ]*",
        "smart factor[^ ]*",
        "smart home[^ ]*",
        "smart sensor[^ ]*",
        "wearable[^ ]*",
        "wireless body area network[^ ]*",
        "wireless sensor network[^ ]*",
    ]
)
AM_PLURAL = _code(
    [
        "3d print[^ ]*",
        "3d prototyping(?:s|es)? ",
        "additive fabrication(?:s|es)? ",
        "additive layer manufacturing(?:s|es)? ",
        "additive manufacturing(?:s|es)? ",
        "direct digital manufacturing(?:s|es)? ",
        "industry 4 0 ",
        "layered manufacturing(?:s|es)? ",
        "rapid prototyping(?:s|es)? ",
        "vat photopolymerization(?:s|es)? ",
        "material jetting(?:s|es)? ",
        "binder jetting(?:s|es)? ",
        "powder bed fusion(?:s|es)? ",
        "material extrusion(?:s|es)? ",
        "directed energy deposition(?:s|es)? ",
        "sheet lamination(?:s|es)? ",
        "composite filament fabrication(?:s|es)? ",
        "continuous liquid interface production(?:s|es)? ",
        "direct ink writing(?:s|es)? ",
        "direct metal laser sintering(?:s|es)? ",
        "electron beam freeform fabrication(?:s|es)? ",
        "electron beam melting(?:s|es)? ",
        "fused deposition modeling(?:s|es)? ",
        "fused filament fabrication(?:s|es)? ",
        "laminated object manufacturing(?:s|es)? ",
        "robocasting(?:s|es)? ",
        "selective laser melting(?:s|es)? ",
        "selective laser sintering(?:s|es)? ",
        "stereolithograph(?:y|ies) ",
    ]
)


@pytest.mark.parametrize(
    ("code", "pattern"),
    [("BL", BLOCKCHAIN_PLURAL), ("ROB", ROBOTICS_PLURAL), ("IOT", IOT_PLURAL), ("AM", AM_PLURAL)],
)
def test_hand_written_plural_patterns_have_one_entry_per_term(code, pattern):
    """Each hand-written list holds as many alternatives as the file has terms."""
    # The two groups each hold one `|` of their own, which is not a separator.
    separators = pattern.count("|") - pattern.count(S_ES) - pattern.count(Y_IES)
    terms = parse_terms(QUERY_FILES[code].read_text(encoding="utf-8"))
    assert separators + 1 == len(terms)


@pytest.mark.parametrize(
    ("position", "code", "expected"),
    [
        (1, "IOT", IOT_PLURAL),
        (3, "BL", BLOCKCHAIN_PLURAL),
        (4, "ROB", ROBOTICS_PLURAL),
        (5, "AM", AM_PLURAL),
    ],
)
def test_real_plural_artefact_exact_patterns(plural_artefact, position, code, expected):
    """Four whole patterns, derived by hand from the files and the two rules."""
    definition = plural_artefact["definitions"][position]
    assert definition["code"] == code
    assert definition["pattern"] == expected


# Fragments of the two other patterns, each derived by hand from consecutive
# terms of the file: (position, code, how the pattern starts, fragments
# inside it, how it ends).
@pytest.mark.parametrize(
    ("position", "code", "start", "inside", "end"),
    [
        (
            0,
            "AI",
            (
                " (?:artificial intellig[^ ]*|automated reasoning(?:s|es)? "
                "|backpropagation(?:s|es)? |"
            ),
            [
                (
                    "|generative adversarial network(?:s|es)? |k means(?:s|es)? "
                    "|language model(?:s|es)? |"
                ),
                (
                    "|long short term memor(?:y|ies) |vision transformer(?:s|es)? "
                    "|image model(?:s|es)? |"
                ),
                "|swarm optimisation(?:s|es)? |particle swarm optimisation(?:s|es)? |",
                "|latent dirichlet allocation(?:s|es)? |word2vec(?:s|es)? |",
                "|mixed realit[^ ]*|virtual realit[^ ]*|neural network(?:s|es)? |",
            ],
            "|apache hive(?:s|es)? |distributed file system[^ ]*)",
        ),
        (
            2,
            "CI",
            (
                " (?:data center[^ ]*|data centre[^ ]*|cloud application[^ ]*"
                "|cloud architecture[^ ]*|cloud broker(?:s|es)? |cloud client(?:s|es)? |"
            ),
            [
                (
                    "|infrastructure as a service(?:s|es)? |inter cloud computing(?:s|es)? "
                    "|multi cloud[^ ]*|on demand computing(?:s|es)? |"
                ),
                "|cloud optimizer(?:s|es)? |cloud portfolio(?:s|es)? |",
            ],
            (
                "|5g(?:s|es)? |5th generation mobile(?:s|es)? |fifth generation mobile(?:s|es)? "
                "|5g networks(?:s|es)? )"
            ),
        ),
    ],
)
def test_real_plural_artefact_pattern_fragments(
    plural_artefact, position, code, start, inside, end
):
    """The AI and CI patterns start, continue and end as their terms compile by hand."""
    definition = plural_artefact["definitions"][position]
    assert definition["code"] == code
    assert definition["pattern"].startswith(start)
    for fragment in inside:
        assert fragment in definition["pattern"], fragment
    assert definition["pattern"].endswith(end)


def _plural_by_hand(default_term_pattern):
    """Apply the amendment's two rules to a default term pattern, as written in the contract.

    Consumes a pattern from `term_pattern(term)` with both switches off.
    Produces what `plural_tolerant=True` must give: a truncated last word, or
    one ending in a digit, is left alone; a last word ending in a consonant
    then `y` has the `y` replaced by `(?:y|ies)`; any other last word ending
    in a letter gets `(?:s|es)?`. A last word of one letter `y`, or with a
    digit before the final `y`, is outside what the contract spells out and
    is refused here.
    """
    if default_term_pattern.endswith("[^ ]*"):
        return default_term_pattern
    assert default_term_pattern.endswith(" ")
    body = default_term_pattern[:-1]
    last = body.rsplit(" ", 1)[-1]
    if not last[-1].isalpha():
        return default_term_pattern
    if last.endswith("y"):
        assert len(last) >= 2 and last[-2].isalpha(), last
        if last[-2] not in "aeiou":
            return body[:-1] + Y_IES + " "
    return body + S_ES + " "


def test_real_plural_artefact_every_term_follows_the_rules(plural_artefact):
    """Every real term's plural pattern, rebuilt from its default pattern by the rules."""
    for definition in plural_artefact["definitions"]:
        expected = [_plural_by_hand(translate.term_pattern(term)) for term in definition["terms"]]
        for term, by_hand in zip(definition["terms"], expected, strict=True):
            assert translate.term_pattern(term, plural_tolerant=True) == by_hand, term
        assert definition["pattern"] == _code(expected), definition["code"]


def test_real_plural_artefact_patterns_use_the_amended_alphabet(plural_artefact):
    """Lower-case ASCII words, single spaces, `[^ ]*`, `|`, the two new groups, nothing else."""
    word = r"[a-z0-9]+"
    middle = rf"{word}(?:\[\^ \]\*)? "
    last = (
        rf"(?:{word}\[\^ \]\*"
        r"|[a-z0-9]*[0-9] "
        r"|[a-z0-9]*[a-z]\(\?:s\|es\)\? "
        r"|[a-z0-9]*\(\?:y\|ies\) )"
    )
    term = rf"(?:{middle})*{last}"
    shape = re.compile(rf" \(\?:{term}(?:\|{term})*\)")
    for definition in plural_artefact["definitions"]:
        pattern = definition["pattern"]
        assert shape.fullmatch(pattern) is not None, definition["code"]
        assert "'" not in pattern
        assert '"' not in pattern
        assert "\\" not in pattern
        assert "  " not in pattern


# --------------------------------------------------------------------------
# Engine parity
# --------------------------------------------------------------------------

# Small term lists written by hand: plain plurals, consonant-y and vowel-y
# words, a word in x, a truncated term, a hyphenated term, a last word that
# is a digit.
PARITY_TERMS = {
    "AI": ["random forest", "neural net*", "k-means"],
    "SC": ["smart city", "ontology"],
    "KEY": ["smart key", "relay", "bounding box"],
    "IOT": ["iot", "internet of things", "industry 4.0"],
}

# What `code_pattern(..., plural_tolerant=True)` must give for each list.
PARITY_PATTERNS = {
    "AI": " (?:random forest(?:s|es)? |neural net[^ ]*|k means(?:s|es)? )",
    "SC": " (?:smart cit(?:y|ies) |ontolog(?:y|ies) )",
    "KEY": " (?:smart key(?:s|es)? |relay(?:s|es)? |bounding box(?:s|es)? )",
    "IOT": " (?:iot(?:s|es)? |internet of things(?:s|es)? |industry 4 0 )",
}


def _hits(*codes):
    """Return the expected flags of one text: True for the codes named, False for the rest."""
    unknown = set(codes) - set(PARITY_TERMS)
    assert not unknown, unknown
    return {code: code in codes for code in PARITY_TERMS}


# (text, {code: expected flag}). Each expectation was derived by normalising
# the text by hand and searching the four patterns above in it.
PARITY_FIXTURE = [
    # Singular and plural forms with s and es.
    ("a random forest", _hits("AI")),
    ("Random forests were trained", _hits("AI")),
    ("random forestes", _hits("AI")),
    ("Random-Forest models", _hits("AI")),
    ("IoT", _hits("IOT")),
    ("IoTs and sensors", _hits("IOT")),
    ("many IoTes", _hits("IOT")),
    ("Internet of Things", _hits("IOT")),
    ("internet of thingses", _hits("IOT")),
    ("k-means", _hits("AI")),
    ("k-meanses", _hits("AI")),
    ("bounding box", _hits("KEY")),
    ("Bounding boxes.", _hits("KEY")),
    ("bounding boxs", _hits("KEY")),
    # A vowel before the y: s or es, never ies.
    ("smart key", _hits("KEY")),
    ("smart keys", _hits("KEY")),
    ("smart keyes", _hits("KEY")),
    ("smart kies", _hits()),
    ("Relays.", _hits("KEY")),
    ("a relay race", _hits("KEY")),
    ("relaies", _hits()),
    # A consonant before the y: y or ies, never ys.
    ("the smart city", _hits("SC")),
    ("Smart cities in Europe", _hits("SC")),
    ("SMART CITIES", _hits("SC")),
    ("smart citys", _hits()),
    ("smart cityies", _hits()),
    ("Ontologies and an ontology", _hits("SC")),
    ("ontologys", _hits()),
    ("paleontologies", _hits()),
    # Near misses after the stem.
    ("random forestry", _hits()),
    ("random forestss", _hits()),
    ("internet of thing", _hits()),
    ("iotss", _hits()),
    ("iot2020", _hits()),
    ("kmeans", _hits()),
    # A last word that is a digit takes no plural.
    ("Industry 4.0", _hits("IOT")),
    ("Industry 4.0s", _hits()),
    # Truncation is unchanged.
    ("neural networks", _hits("AI")),
    # An accented neighbour, apart from the term and glued to it.
    ("señal IoTs", _hits("IOT")),
    ("IoTsñ devices", _hits()),
    ("ciudades smart cities", _hits("SC")),
    # Terms at the very start and the very end, and followed by punctuation.
    ("Smart cities: a review", _hits("SC")),
    ("We study smart cities.", _hits("SC")),
    ("smart_keys", _hits("KEY")),
    ("smart  city", _hits("SC")),
    # A term split by a sentence end.
    ("Random. Forests grow", _hits("AI")),
    # A null, an empty string, and a text with no letter and no digit.
    (None, _hits()),
    ("", _hits()),
    ("...", _hits()),
    # Several codes in one text.
    ("IoTs in smart cities with random forests", _hits("IOT", "SC", "AI")),
    ("relays, boxes and ontologies", _hits("KEY", "SC")),
]

PARITY_TEXTS = [text for text, _ in PARITY_FIXTURE]


@pytest.fixture(scope="module")
def parity_patterns():
    """Build the four plural-tolerant fixture patterns with `code_pattern`."""
    return {
        code: translate.code_pattern(terms, plural_tolerant=True)
        for code, terms in PARITY_TERMS.items()
    }


def test_parity_patterns_are_the_ones_the_expectations_were_derived_from(parity_patterns):
    """The patterns built from `PARITY_TERMS` are exactly the ones written out by hand."""
    assert parity_patterns == PARITY_PATTERNS


def test_parity_fixture_has_the_kinds_of_text_needed():
    """Plural, singular and ies forms, a null, an empty string, hits and misses per code."""
    assert PARITY_TEXTS.count(None) == 1
    assert PARITY_TEXTS.count("") == 1
    assert "Smart cities in Europe" in PARITY_TEXTS
    assert "the smart city" in PARITY_TEXTS
    assert "Random forests were trained" in PARITY_TEXTS
    assert "a random forest" in PARITY_TEXTS
    for code in PARITY_TERMS:
        flags = [expected[code] for _, expected in PARITY_FIXTURE]
        assert True in flags, code
        assert False in flags, code


@pytest.mark.parametrize("code", list(PARITY_TERMS))
def test_polars_plural_matches_the_fixture(parity_patterns, code):
    """`translate.matches` gives the expected flag for every fixture text."""
    got = [translate.matches(parity_patterns[code], text) for text in PARITY_TEXTS]
    assert got == [expected[code] for _, expected in PARITY_FIXTURE]


# --------------------------------------------------------------------------
# render_adt_flags: carried columns and header
# --------------------------------------------------------------------------


# The two examples of the amendment, and a third plain column.


