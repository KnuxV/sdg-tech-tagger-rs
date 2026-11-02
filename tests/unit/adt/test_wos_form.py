"""Tests of `sdg_tech_tagger.adt.wos_form`, written from the contract alone.

Source of every expected value: `docs/adt-wos-form-contract.md`. An
expected list or string is either a row of the contract, or a rule of the
contract applied by hand. For the equality of the contract the expected side
is `translate.term_pattern` and `translate.code_pattern`, which exist and are
trusted.

What is covered:

- `plain_terms`: every row of the contract's table, the two rows that raise
  included, and cases derived by hand from the rules of the separators, of
  the endings of the last word and of the order;
- the equality of the contract, for hand-written terms under the four pairs
  of options and for every term of `gate_patterns_v2.json` under the options
  of the artefact, over hand-written texts and over texts built from each
  term;
- `plain_code_terms`, `query_text` and `render_gate` on hand-written input;
- the shipped files of `adt/gate_v2_wos/`: their bytes, what `parse_terms`
  reads back from them, the number of terms each holds, `SHA256SUMS` and
  `README.md`.

No count of terms is hard-coded for a shipped file. `_by_the_rules` writes the
rules of `plain_terms` a second time, in the test, and the counts come from
it. It is used for the counts only, never for an expected list.

The gate-wide equality does not call `translate.matches` once per text: the
texts are normalised once with `translate.normalise_expr` and searched with
`str.contains`, which is what `translate.matches` and `translate.flag` do.

`wos_form` is imported inside a fixture, so a missing module or function
fails a test and not the collection.
"""

import hashlib
import importlib
import itertools
import json
import re
from importlib.resources import files
from pathlib import Path

import polars as pl
import pytest

from sdg_tech_tagger.adt import translate
from sdg_tech_tagger.adt.wos_query import QueryError, parse_terms

ADT_DIR = Path(str(files("sdg_tech_tagger") / "adt"))
GATE_PATH = ADT_DIR / "gate_v2" / "gate_patterns_v2.json"
SHIPPED_DIR = ADT_DIR / "gate_v2_wos"

# The eight files the contract names, in the order `render_gate` gives them.
SHIPPED_FILES = [
    "AI.txt",
    "IOT.txt",
    "CI.txt",
    "BL.txt",
    "ROB.txt",
    "AM.txt",
    "UMBRELLA.txt",
    "ALL.txt",
]

OPTION_PAIRS = [(False, False), (False, True), (True, False), (True, True)]


@pytest.fixture(scope="module")
def wos_form():
    """The module under test, imported here so its absence fails each test."""
    return importlib.import_module("sdg_tech_tagger.adt.wos_form")


@pytest.fixture(scope="module")
def gate():
    """The artefact of gate v2, as it is shipped."""
    return json.loads(GATE_PATH.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# plain_terms
# --------------------------------------------------------------------------

# The rows of the contract's table that do not raise. A row that says "any"
# for an option is written once for each value of it.
TABLE = [
    ("random forest", False, False, ["random forest"]),
    ("random forest", True, False, ["random forest"]),
    (
        "random forest",
        False,
        True,
        ["random forest", "random forests", "random forestes"],
    ),
    (
        "random forest",
        True,
        True,
        ["random forest", "random forests", "random forestes"],
    ),
    ("digital economy", False, True, ["digital economy", "digital economies"]),
    ("relay", False, True, ["relay", "relays", "relayes"]),
    ("robot*", True, True, ["robot*"]),
    ("gpt-4", True, True, ["gpt-4", "gpt4"]),
    ("meta-learning", False, False, ["meta-learning"]),
    ("meta-learning", True, False, ["meta-learning", "metalearning"]),
    (
        "meta-learning",
        True,
        True,
        [
            "meta-learning",
            "meta-learnings",
            "meta-learninges",
            "metalearning",
            "metalearnings",
            "metalearninges",
        ],
    ),
    ("data-center*", True, True, ["data-center*", "datacenter*"]),
    (
        "system-on-a-chip",
        True,
        False,
        [
            "system-on-a-chip",
            "system-on-achip",
            "system-ona-chip",
            "system-onachip",
            "systemon-a-chip",
            "systemon-achip",
            "systemona-chip",
            "systemonachip",
        ],
    ),
    ("web 3.0", True, True, ["web 3.0"]),
    (" -big data- ", True, True, ["big data", "big datas", "big dataes"]),
]

# Cases the rules give when applied by hand.
DERIVED = [
    # y after a consonant: two endings. y after a vowel: three.
    ("economy", False, True, ["economy", "economies"]),
    ("survey", False, True, ["survey", "surveys", "surveyes"]),
    ("toy", False, True, ["toy", "toys", "toyes"]),
    ("guy", False, True, ["guy", "guys", "guyes"]),
    ("3d sky", False, True, ["3d sky", "3d skies"]),
    # The one-letter word y has no character before its y: three endings.
    ("y", False, True, ["y", "ys", "yes"]),
    ("x y", False, True, ["x y", "x ys", "x yes"]),
    # A word of two letters ending with y after a consonant.
    ("my", False, True, ["my", "mies"]),
    # Only the last word takes an ending.
    (
        "economy class",
        False,
        True,
        ["economy class", "economy classs", "economy classes"],
    ),
    # A last word that ends with a digit has one ending.
    ("web3", False, True, ["web3"]),
    ("5g", False, True, ["5g", "5gs", "5ges"]),
    ("g5", True, True, ["g5"]),
    ("imt-2020", True, True, ["imt-2020", "imt2020"]),
    # A truncated last word has one ending.
    ("cryptocurrenc*", False, True, ["cryptocurrenc*"]),
    ("private blockchain*", True, True, ["private blockchain*"]),
    ("robot*", False, False, ["robot*"]),
    # A truncated word that is not the last, before a separator with no hyphen.
    ("multi* class", True, False, ["multi* class"]),
    # The row of the table that raises with the closed form does not raise without.
    ("multi*-class", False, False, ["multi*-class"]),
    (
        "multi*-class",
        False,
        True,
        ["multi*-class", "multi*-classs", "multi*-classes"],
    ),
    # Two hyphens: four spellings, the first separator the highest digit.
    ("a-b-c", True, False, ["a-b-c", "a-bc", "ab-c", "abc"]),
    ("a-b-c", False, False, ["a-b-c"]),
    (
        "car-to-car",
        True,
        True,
        [
            "car-to-car",
            "car-to-cars",
            "car-to-cares",
            "car-tocar",
            "car-tocars",
            "car-tocares",
            "carto-car",
            "carto-cars",
            "carto-cares",
            "cartocar",
            "cartocars",
            "cartocares",
        ],
    ),
    # One hyphenated separator and one that is a space: two spellings.
    ("k-nearest neighbo*", True, True, ["k-nearest neighbo*", "knearest neighbo*"]),
    ("deep q-learning", True, False, ["deep q-learning", "deep qlearning"]),
    # A separator that holds a hyphen and spaces is kept as written, or dropped.
    ("big - data", True, False, ["big - data", "bigdata"]),
    ("big - data", False, False, ["big - data"]),
    (
        "big - data",
        True,
        True,
        [
            "big - data",
            "big - datas",
            "big - dataes",
            "bigdata",
            "bigdatas",
            "bigdataes",
        ],
    ),
    ("big -data", True, False, ["big -data", "bigdata"]),
    # A dot is a separator with no hyphen: never glued.
    ("a.b", True, False, ["a.b"]),
    ("industry 4.0", True, True, ["industry 4.0"]),
    ("gpt-3.5", True, True, ["gpt-3.5", "gpt3.5"]),
    ("i4.0", True, True, ["i4.0"]),
    # What stands before the first word and after the last is dropped.
    ("  relay  ", False, False, ["relay"]),
    ("-meta-learning-", True, False, ["meta-learning", "metalearning"]),
    ("(k-means)", True, False, ["k-means", "kmeans"]),
]


@pytest.mark.parametrize(("term", "closed", "plural", "expected"), TABLE)
def test_plain_terms_rows_of_the_contract(wos_form, term, closed, plural, expected):
    """Each row of the contract's table gives exactly its list, in its order."""
    assert wos_form.plain_terms(term, closed, plural) == expected


@pytest.mark.parametrize(("term", "closed", "plural", "expected"), DERIVED)
def test_plain_terms_rules_applied_by_hand(wos_form, term, closed, plural, expected):
    """Each rule of the contract, applied by hand, gives exactly this list."""
    assert wos_form.plain_terms(term, closed, plural) == expected


@pytest.mark.parametrize(
    ("term", "expected"),
    [
        ("meta-learning", ["meta-learning"]),
        ("digital economy", ["digital economy"]),
        ("relay", ["relay"]),
        ("system-on-a-chip", ["system-on-a-chip"]),
        (" -big data- ", ["big data"]),
    ],
)
def test_plain_terms_defaults_are_both_options_off(wos_form, term, expected):
    """With no option given, a term has one plain term: itself, its ends dropped."""
    assert wos_form.plain_terms(term) == expected


def test_plain_terms_options_by_keyword(wos_form):
    """The two options have the names the contract gives them."""
    assert wos_form.plain_terms("gpt-4o", hyphen_closed_form=True) == [
        "gpt-4o",
        "gpt4o",
    ]
    assert wos_form.plain_terms("gpt-4o", plural_tolerant=True) == [
        "gpt-4o",
        "gpt-4os",
        "gpt-4oes",
    ]
    assert wos_form.plain_terms(
        "gpt-4o", hyphen_closed_form=True, plural_tolerant=True
    ) == [
        "gpt-4o",
        "gpt-4os",
        "gpt-4oes",
        "gpt4o",
        "gpt4os",
        "gpt4oes",
    ]


def test_plain_terms_returns_a_list_without_repeats(wos_form):
    """The result is a list, and no plain term comes twice."""
    result = wos_form.plain_terms("system-on-a-chip", True, True)
    assert isinstance(result, list)
    assert len(result) == 24
    assert len(set(result)) == 24
    assert result[:4] == [
        "system-on-a-chip",
        "system-on-a-chips",
        "system-on-a-chipes",
        "system-on-achip",
    ]
    assert result[-3:] == ["systemonachip", "systemonachips", "systemonachipes"]


@pytest.mark.parametrize("plural", [False, True])
def test_plain_terms_truncation_before_a_hyphen_raises_with_closed_form(
    wos_form, plural
):
    """Row `multi*-class` of the table: gluing would put the star inside a word."""
    with pytest.raises(QueryError):
        wos_form.plain_terms("multi*-class", True, plural)


@pytest.mark.parametrize("term", ["multi* - class", "a-b*-c", "data*-center*"])
def test_plain_terms_truncation_before_a_hyphenated_separator_raises(wos_form, term):
    """The same rule, for a separator with spaces and for a word that is not the first."""
    with pytest.raises(QueryError):
        wos_form.plain_terms(term, True, False)


@pytest.mark.parametrize(("closed", "plural"), OPTION_PAIRS)
def test_plain_terms_star_inside_a_word_raises(wos_form, closed, plural):
    """Row `ro*bot` of the table, under every pair of options."""
    with pytest.raises(QueryError):
        wos_form.plain_terms("ro*bot", closed, plural)


# Terms on which `translate.term_pattern` raises, whatever the options.
REFUSED_BY_TERM_PATTERN = [
    "wom?n",
    "colo$r",
    "señal",
    "naïve bayes",
    "",
    "   ",
    "-",
    " - . ",
    "*robot",
    "ro**bot",
    "robot**",
    "*",
]


@pytest.mark.parametrize("term", REFUSED_BY_TERM_PATTERN)
@pytest.mark.parametrize(("closed", "plural"), OPTION_PAIRS)
def test_plain_terms_raises_where_term_pattern_raises(wos_form, term, closed, plural):
    """A term `translate.term_pattern` refuses is refused here too."""
    with pytest.raises(QueryError):
        translate.term_pattern(term, closed, plural)
    with pytest.raises(QueryError):
        wos_form.plain_terms(term, closed, plural)


# --------------------------------------------------------------------------
# The equality of the contract
# --------------------------------------------------------------------------

# Hand-written terms, none of which raises under any pair of options.
EQUALITY_TERMS = [
    "random forest",
    "digital economy",
    "relay",
    "robot*",
    "gpt-4",
    "gpt-4o",
    "meta-learning",
    "data-center*",
    "system-on-a-chip",
    "web 3.0",
    " -big data- ",
    "big - data",
    "y",
    "ai",
    "k-means",
    "3-d print*",
    "class",
    "box",
    "5g",
    "industry 4.0",
    "multi* class",
    "a.b",
]

# Hand-written texts, made to hit and to miss the terms above: plurals, closed
# and spaced and hyphenated spellings, a term inside a longer word, and
# punctuation between two words.
EQUALITY_TEXTS = [
    "",
    "   ",
    "...",
    "Nothing in this sentence is about technology.",
    "A random forest was trained on the survey.",
    "Random forests beat the baseline.",
    "random forestes",
    "randomforest",
    "random-forest models",
    "random, forest",
    "The split was random. Forest fires spread.",
    "random forestry",
    "pseudorandom forest",
    "The digital economy grew.",
    "the digital economies of the region",
    "digital economys",
    "digital economyes",
    "digital economie",
    "digitaleconomy",
    "One relay failed.",
    "relays and relayes",
    "relaies",
    "relayed",
    "A robot.",
    "robots",
    "The robotics lab",
    "microrobot",
    "GPT-4 answered the question.",
    "gpt4",
    "gpt 4",
    "gpt-4s",
    "gpt-40",
    "chatgpt-4",
    "GPT-4o, then GPT-4os and gpt4oes",
    "gpt 4 o",
    "Meta-learning helps.",
    "Meta learning helps.",
    "metalearning",
    "metalearnings",
    "meta-learninges",
    "meta  -  learning",
    "meta, learning",
    "metalearningx",
    "nometa-learning",
    "meta learn ing",
    "meta-learner",
    "Two data centers were built.",
    "datacenter",
    "data-centres",
    "datacentering",
    "bigdata centers",
    "system on a chip",
    "A System-on-a-Chip design",
    "system-on-achip",
    "system-ona-chip",
    "systemon-a-chip",
    "systemonachip",
    "systemona chip",
    "system ona chip",
    "system on chip",
    "systems on a chip",
    "system on a chips",
    "Web 3.0 is discussed.",
    "web 3 0",
    "web3.0",
    "web 30",
    "web 3,0",
    "web 3.0s",
    "big data",
    "Big Data, again",
    "bigdata",
    "big datas",
    "big dataes",
    "big-data-",
    "big - data",
    "big database",
    "y",
    "ys",
    "yes",
    "ies",
    "the y axis",
    "why",
    "AI is everywhere.",
    "AIs",
    "aies",
    "said",
    "A.I.",
    "k-means",
    "kmeans",
    "k means clustering",
    "k-meanses",
    "k-meanss",
    "ok-means",
    "3-D printing of parts",
    "3d printed",
    "3 d print",
    "23-d print",
    "3-dprint",
    "A class of models",
    "classes",
    "classs",
    "subclass",
    "classy",
    "boxes",
    "boxs",
    "box",
    "5G networks",
    "5gs",
    "0.5g per day",
    "15g",
    "Industry 4.0 arrives.",
    "industry 4 0",
    "industry 4p0",
    "industry. 40 firms",
    "industry 4.0s",
    "multi class",
    "multiple class",
    "multi-label class",
    "a.b",
    "a b",
    "ab",
    "a, b and c",
]


def _normalised(texts):
    """Hand-written texts to their normalised form, `decimal_whole` off, in one frame."""
    frame = pl.DataFrame({"text": texts}, schema={"text": pl.String})
    return frame.select(translate.normalise_expr(pl.col("text"))).to_series()


def _disagreements(wos_form, term, closed, plural, texts, normalised):
    """The texts on which the two sides of the equality differ, with both verdicts.

    The left side is the plain terms compiled with every option off, the right
    side is the term compiled with the two options, both searched in texts
    normalised with `decimal_whole` off.
    """
    left = translate.code_pattern(wos_form.plain_terms(term, closed, plural))
    right = " " + translate.term_pattern(term, closed, plural)
    by_plain_terms = normalised.str.contains(left).to_list()
    by_term = normalised.str.contains(right).to_list()
    return [
        (term, text, plain, whole)
        for text, plain, whole in zip(texts, by_plain_terms, by_term, strict=True)
        if plain != whole
    ]


@pytest.mark.parametrize(
    ("term", "text"),
    [
        ("meta-learning", "Meta-learning helps."),
        ("meta-learning", "metalearnings"),
        ("meta-learning", "meta learn ing"),
        ("digital economy", "the digital economies of the region"),
        ("digital economy", "digital economys"),
        ("robot*", "The robotics lab"),
        ("robot*", "microrobot"),
        ("system-on-a-chip", "systemona chip"),
        ("system-on-a-chip", "system on chip"),
        ("web 3.0", "web 3,0"),
        ("web 3.0", "web 30"),
        (" -big data- ", "big dataes"),
        ("y", "yes"),
        ("y", "why"),
        ("ai", None),
    ],
)
@pytest.mark.parametrize(("closed", "plural"), OPTION_PAIRS)
def test_equality_as_the_contract_writes_it(wos_form, term, text, closed, plural):
    """The equality, word for word, through `translate.matches`."""
    plain = wos_form.plain_terms(term, closed, plural)
    left = translate.matches(translate.code_pattern(plain), text)
    right = translate.matches(" " + translate.term_pattern(term, closed, plural), text)
    assert left == right


@pytest.mark.parametrize("term", EQUALITY_TERMS)
@pytest.mark.parametrize(("closed", "plural"), OPTION_PAIRS)
def test_equality_on_hand_written_terms(wos_form, term, closed, plural):
    """The plain terms of a term match exactly the texts the term matches."""
    normalised = _normalised(EQUALITY_TEXTS)
    assert (
        _disagreements(wos_form, term, closed, plural, EQUALITY_TEXTS, normalised) == []
    )


@pytest.mark.parametrize("term", EQUALITY_TERMS)
def test_hand_written_texts_hit_and_miss_every_hand_written_term(wos_form, term):
    """The texts are not idle: each term, both options on, is hit and is missed.

    This guards the test above against a list of texts on which both sides
    are always false.
    """
    plain = wos_form.plain_terms(term, True, True)
    verdicts = set(
        _normalised(EQUALITY_TEXTS).str.contains(translate.code_pattern(plain))
    )
    assert verdicts == {True, False}


@pytest.mark.parametrize("plural", [False, True])
def test_equality_on_a_term_that_raises_only_with_closed_form(wos_form, plural):
    """`multi*-class` has plain terms when the closed form is off, and they agree."""
    texts = [
        "multi-class",
        "multiple classes",
        "multi classs",
        "multiclass",
        "multi label class",
    ]
    assert (
        _disagreements(
            wos_form, "multi*-class", False, plural, texts, _normalised(texts)
        )
        == []
    )


def _texts_from(term):
    """Texts built from one term of the gate, made to hit it and to miss it.

    The term is written with its hyphens kept, turned into spaces and dropped,
    with its spaces dropped, turned into hyphens and into a comma, with its
    dots turned into spaces and dropped, with a plural ending, with its
    truncation star turned into "ing", and one letter short. Each of these is
    then taken alone, inside a sentence, and glued to a letter before it and
    after it.
    """
    bare = term.replace("*", "")
    spellings = [
        bare,
        bare.replace("-", " "),
        bare.replace("-", ""),
        bare.replace("-", "", 1),
        "".join(bare.rsplit("-", 1)),
        bare.replace(" ", ""),
        bare.replace(" ", "-"),
        bare.replace(" ", ", "),
        bare.replace("-", " - "),
        bare.replace(".", " "),
        bare.replace(".", ""),
        bare + "s",
        bare + "es",
        bare.replace("-", "") + "s",
        bare.replace("-", " ") + "es",
        bare[:-1] + "ies",
        bare[:-1],
        term.replace("*", "ing"),
        term.replace("*", "ing").replace("-", ""),
        bare.upper(),
    ]
    texts = []
    for spelling in dict.fromkeys(spellings):
        texts += [
            spelling,
            f"We study {spelling} in firms.",
            f"x{spelling}",
            f"{spelling}x",
        ]
    return texts


@pytest.fixture(scope="module")
def gate_texts(gate):
    """For each term of the gate its own texts, and a pool shared by all terms.

    Both are given as written and normalised. Everything is normalised in one
    frame, so the gate-wide checks cost one Polars call per pattern.
    """
    terms = list(
        dict.fromkeys(
            term for definition in gate["definitions"] for term in definition["terms"]
        )
    )
    own = {term: _texts_from(term) for term in terms}
    flat = [text for term in terms for text in own[term]]
    flat_normalised = _normalised(flat).to_list()
    own_normalised = {}
    position = 0
    for term in terms:
        own_normalised[term] = flat_normalised[position : position + len(own[term])]
        position += len(own[term])
    # Every 29th text built from the gate, so each term also meets the
    # spellings of other terms, and the hand-written texts.
    pool = EQUALITY_TEXTS + flat[::29]
    pool_normalised = _normalised(EQUALITY_TEXTS).to_list() + flat_normalised[::29]
    return {
        "own": own,
        "own_normalised": own_normalised,
        "pool": pool,
        "pool_normalised": pool_normalised,
    }


GATE_CODES = ["AI", "IOT", "CI", "BL", "ROB", "AM", "UMBRELLA"]


def test_gate_codes_are_the_seven_of_the_contract(gate):
    """The parametrised tests below cover every definition of the artefact."""
    assert [definition["code"] for definition in gate["definitions"]] == GATE_CODES


@pytest.mark.parametrize("code", GATE_CODES)
def test_equality_on_every_term_of_the_gate(wos_form, gate, gate_texts, code):
    """Every term of a group, with the options of the artefact, keeps the equality.

    A term listed in `plural_exceptions` is taken with `plural_tolerant` off,
    as `translate.code_pattern` takes it. Each term is searched in the texts
    built from itself and in the shared pool.
    """
    closed = gate["hyphen_closed_form"]
    exceptions = set(gate.get("plural_exceptions", []))
    (definition,) = [d for d in gate["definitions"] if d["code"] == code]
    assert definition["terms"]
    found = []
    for term in definition["terms"]:
        plural = gate["plural_tolerant"] and term not in exceptions
        texts = gate_texts["own"][term] + gate_texts["pool"]
        normalised = pl.Series(
            gate_texts["own_normalised"][term] + gate_texts["pool_normalised"],
            dtype=pl.String,
        )
        found += _disagreements(wos_form, term, closed, plural, texts, normalised)
    assert found[:20] == []


@pytest.mark.parametrize("code", GATE_CODES)
def test_every_term_of_the_gate_is_hit_and_missed_by_its_own_texts(
    wos_form, gate, gate_texts, code
):
    """The texts built from a term hit its plain terms and miss them."""
    closed = gate["hyphen_closed_form"]
    exceptions = set(gate.get("plural_exceptions", []))
    (definition,) = [d for d in gate["definitions"] if d["code"] == code]
    idle = []
    for term in definition["terms"]:
        plural = gate["plural_tolerant"] and term not in exceptions
        pattern = translate.code_pattern(wos_form.plain_terms(term, closed, plural))
        normalised = pl.Series(gate_texts["own_normalised"][term], dtype=pl.String)
        if set(normalised.str.contains(pattern)) != {True, False}:
            idle.append(term)
    assert idle == []


@pytest.mark.parametrize("code", GATE_CODES)
def test_equality_of_a_whole_group_of_the_gate(wos_form, gate, gate_texts, code):
    """The plain terms of a group match what the pattern of the group matches.

    This is the equality taken over the terms of a group: the pattern of a
    group is the alternation of the patterns of its terms. Both sides are
    compiled with `decimal_whole` off, so the right side is not the pattern
    stored in the artefact.
    """
    closed = gate["hyphen_closed_form"]
    plural = gate["plural_tolerant"]
    exceptions = gate.get("plural_exceptions", [])
    (definition,) = [d for d in gate["definitions"] if d["code"] == code]
    terms = definition["terms"]
    plain = wos_form.plain_code_terms(terms, closed, plural, exceptions)
    left = translate.code_pattern(plain)
    right = translate.code_pattern(terms, closed, plural, False, exceptions)
    texts = gate_texts["pool"] + [
        text for term in terms for text in gate_texts["own"][term]
    ]
    normalised = pl.Series(
        gate_texts["pool_normalised"]
        + [text for term in terms for text in gate_texts["own_normalised"][term]],
        dtype=pl.String,
    )
    by_plain_terms = normalised.str.contains(left).to_list()
    by_terms = normalised.str.contains(right).to_list()
    found = [
        (text, a, b)
        for text, a, b in zip(texts, by_plain_terms, by_terms, strict=True)
        if a != b
    ]
    assert found[:20] == []
    assert set(by_terms) == {True, False}


# --------------------------------------------------------------------------
# plain_code_terms
# --------------------------------------------------------------------------


def test_plain_code_terms_example_of_the_contract(wos_form):
    """The example of the contract, exactly."""
    assert wos_form.plain_code_terms(["ai", "ann"], False, True, ["ai"]) == [
        "ai",
        "ann",
        "anns",
        "annes",
    ]


def test_plain_code_terms_defaults(wos_form):
    """With no option given, each term gives itself."""
    assert wos_form.plain_code_terms(["meta-learning", "relay", "robot*"]) == [
        "meta-learning",
        "relay",
        "robot*",
    ]


def test_plain_code_terms_keeps_the_order_of_the_terms(wos_form):
    """The plain terms of each term, in the order of the terms."""
    assert wos_form.plain_code_terms(
        ["relay", "gpt-4", "digital economy"], True, True
    ) == [
        "relay",
        "relays",
        "relayes",
        "gpt-4",
        "gpt4",
        "digital economy",
        "digital economies",
    ]
    assert wos_form.plain_code_terms(
        ["digital economy", "gpt-4", "relay"], True, True
    ) == [
        "digital economy",
        "digital economies",
        "gpt-4",
        "gpt4",
        "relay",
        "relays",
        "relayes",
    ]


def test_plain_code_terms_drops_a_repeat_where_it_comes_second(wos_form):
    """`anns` is a plain term of `ann` first, so the term `anns` does not add it again."""
    assert wos_form.plain_code_terms(["ann", "anns"], False, True) == [
        "ann",
        "anns",
        "annes",
        "annss",
        "annses",
    ]
    assert wos_form.plain_code_terms(["anns", "ann"], False, True) == [
        "anns",
        "annss",
        "annses",
        "ann",
        "annes",
    ]


def test_plain_code_terms_drops_a_repeat_made_by_the_closed_form(wos_form):
    """`metalearning` comes from `meta-learning` first, and from itself second."""
    assert wos_form.plain_code_terms(
        ["meta-learning", "metalearning", "relay"], True, False
    ) == [
        "meta-learning",
        "metalearning",
        "relay",
    ]
    assert wos_form.plain_code_terms(
        ["metalearning", "meta-learning"], True, False
    ) == [
        "metalearning",
        "meta-learning",
    ]


def test_plain_code_terms_drops_a_term_given_twice(wos_form):
    """A term that comes twice is expanded once."""
    assert wos_form.plain_code_terms(["ai", "relay", "ai"], False, True) == [
        "ai",
        "ais",
        "aies",
        "relay",
        "relays",
        "relayes",
    ]


def test_plain_code_terms_exception_is_expanded_without_plural(wos_form):
    """A term listed as an exception keeps the closed form and loses the plural."""
    assert wos_form.plain_code_terms(
        ["meta-learning", "k-means"], True, True, ["meta-learning"]
    ) == [
        "meta-learning",
        "metalearning",
        "k-means",
        "k-meanss",
        "k-meanses",
        "kmeans",
        "kmeanss",
        "kmeanses",
    ]


@pytest.mark.parametrize(
    "exception",
    [
        "big data",
        "  big data  ",
        "Big Data",
        "BIG   DATA",
        "big\tdata",
        " Big \n DATA ",
    ],
)
def test_plain_code_terms_exception_is_compared_as_code_pattern_compares(
    wos_form, exception
):
    """An exception is stripped, lower-cased and its spaces collapsed before comparing."""
    assert wos_form.plain_code_terms(["big data", "ai"], False, True, [exception]) == [
        "big data",
        "ai",
        "ais",
        "aies",
    ]


def test_plain_code_terms_unknown_exception_is_ignored(wos_form):
    """An exception that is no term of the list changes nothing and does not raise."""
    assert wos_form.plain_code_terms(["ann"], False, True, ["ai", "bigdata"]) == [
        "ann",
        "anns",
        "annes",
    ]


def test_plain_code_terms_exception_without_plural_option(wos_form):
    """With `plural_tolerant` off an exception has nothing to switch off."""
    assert wos_form.plain_code_terms(["ai", "gpt-4"], True, False, ["ai"]) == [
        "ai",
        "gpt-4",
        "gpt4",
    ]


def test_plain_code_terms_exceptions_by_keyword_and_as_a_tuple(wos_form):
    """The fourth argument is named `plural_exceptions` and any collection will do."""
    assert wos_form.plain_code_terms(
        ["ai", "ann"], plural_tolerant=True, plural_exceptions=("ai",)
    ) == ["ai", "ann", "anns", "annes"]


@pytest.mark.parametrize("terms", [[], ()])
def test_plain_code_terms_empty_list_raises(wos_form, terms):
    """A group with no term is refused."""
    with pytest.raises(QueryError):
        wos_form.plain_code_terms(terms)
    with pytest.raises(QueryError):
        wos_form.plain_code_terms(terms, True, True, ["ai"])


def test_plain_code_terms_raises_for_a_term_that_does_not_fit(wos_form):
    """A term `plain_terms` refuses is refused inside a list too."""
    with pytest.raises(QueryError):
        wos_form.plain_code_terms(["relay", "ro*bot"])
    with pytest.raises(QueryError):
        wos_form.plain_code_terms(["relay", "multi*-class"], True, False)


# --------------------------------------------------------------------------
# query_text
# --------------------------------------------------------------------------


def test_query_text_example_of_the_contract(wos_form):
    """The example of the contract, exactly."""
    assert wos_form.query_text(["a b", "c*"]) == 'TS = (\n("a b") OR\n("c*")\n)\n'


def test_query_text_one_term(wos_form):
    """One term: its line is the last, so it has no ` OR`."""
    assert wos_form.query_text(["meta-learning"]) == 'TS = (\n("meta-learning")\n)\n'


def test_query_text_three_terms(wos_form):
    """Every line but the last term's ends with ` OR`, and every line with a newline."""
    assert wos_form.query_text(["gpt-4", "gpt4", "web 3.0"]) == (
        'TS = (\n("gpt-4") OR\n("gpt4") OR\n("web 3.0")\n)\n'
    )


@pytest.mark.parametrize("terms", [[], ()])
def test_query_text_empty_list_raises(wos_form, terms):
    """A query with no term is refused."""
    with pytest.raises(QueryError):
        wos_form.query_text(terms)


@pytest.mark.parametrize(
    "terms",
    [['a "b"'], ['"'], ["relay", 'rel"ay'], ['say "ai"', "relay"]],
)
def test_query_text_double_quote_raises(wos_form, terms):
    """A term that holds a double quote cannot be written between double quotes."""
    with pytest.raises(QueryError):
        wos_form.query_text(terms)


@pytest.mark.parametrize(
    "terms",
    [
        ["a b", "c*"],
        ["relay"],
        [
            "meta-learning",
            "metalearning",
            "gpt-3.5",
            "gpt3.5",
            "web 3.0",
            "5g",
            "robot*",
        ],
        ["big - data", "bigdata", "system-on-achip", "i4.0"],
    ],
)
def test_query_text_is_read_back_by_parse_terms(wos_form, terms):
    """`parse_terms` gives back the terms `query_text` was given."""
    assert parse_terms(wos_form.query_text(terms)) == terms


# --------------------------------------------------------------------------
# render_gate
# --------------------------------------------------------------------------


def _small_artefact(**changes):
    """A hand-written artefact: two definitions that share the plain term `sensors`.

    Both options are on and `ai` is a plural exception. `changes` replaces
    keys of the artefact; the value `...` removes the key.
    """
    artefact = {
        "version": 1,
        "hyphen_closed_form": True,
        "plural_tolerant": True,
        "plural_exceptions": ["ai"],
        "definitions": [
            {"code": "AA", "terms": ["ai", "sensor"]},
            {"code": "BB", "terms": ["robot*", "sensors", "gpt-4"]},
        ],
    }
    for key, value in changes.items():
        if value is ...:
            del artefact[key]
        else:
            artefact[key] = value
    return artefact


SMALL_AA = 'TS = (\n("ai") OR\n("sensor") OR\n("sensors") OR\n("sensores")\n)\n'
SMALL_BB = (
    'TS = (\n("robot*") OR\n("sensors") OR\n("sensorss") OR\n("sensorses") OR\n'
    '("gpt-4") OR\n("gpt4")\n)\n'
)
# `sensors` comes from AA first, so BB does not add it again.
SMALL_ALL = (
    'TS = (\n("ai") OR\n("sensor") OR\n("sensors") OR\n("sensores") OR\n("robot*") OR\n'
    '("sensorss") OR\n("sensorses") OR\n("gpt-4") OR\n("gpt4")\n)\n'
)
SMALL_RENDERED = {"AA.txt": SMALL_AA, "BB.txt": SMALL_BB, "ALL.txt": SMALL_ALL}


def test_render_gate_small_artefact(wos_form):
    """One file per definition in order, then `ALL.txt` with the repeat dropped."""
    rendered = wos_form.render_gate(_small_artefact())
    assert rendered == SMALL_RENDERED
    assert list(rendered) == ["AA.txt", "BB.txt", "ALL.txt"]


@pytest.mark.parametrize("decimal_whole", [True, False])
def test_render_gate_decimal_whole_changes_nothing(wos_form, decimal_whole):
    """`decimal_whole` present, true or false, gives what its absence gives."""
    rendered = wos_form.render_gate(_small_artefact(decimal_whole=decimal_whole))
    assert rendered == SMALL_RENDERED
    assert list(rendered) == ["AA.txt", "BB.txt", "ALL.txt"]


def test_render_gate_decimal_whole_on_a_term_with_a_decimal(wos_form):
    """A decimal in a term is written as it is, with `decimal_whole` true or absent."""
    definitions = [{"code": "UU", "terms": ["industry 4.0", "gpt-3.5"]}]
    expected = {
        "UU.txt": 'TS = (\n("industry 4.0") OR\n("gpt-3.5") OR\n("gpt3.5")\n)\n',
        "ALL.txt": 'TS = (\n("industry 4.0") OR\n("gpt-3.5") OR\n("gpt3.5")\n)\n',
    }
    with_it = _small_artefact(definitions=definitions, decimal_whole=True)
    without_it = _small_artefact(definitions=definitions)
    assert wos_form.render_gate(with_it) == expected
    assert wos_form.render_gate(without_it) == expected


def test_render_gate_without_plural_exceptions(wos_form):
    """`plural_exceptions` absent means none: `ai` takes its plural endings."""
    rendered = wos_form.render_gate(_small_artefact(plural_exceptions=...))
    assert rendered == {
        "AA.txt": (
            'TS = (\n("ai") OR\n("ais") OR\n("aies") OR\n("sensor") OR\n("sensors") OR\n'
            '("sensores")\n)\n'
        ),
        "BB.txt": SMALL_BB,
        "ALL.txt": (
            'TS = (\n("ai") OR\n("ais") OR\n("aies") OR\n("sensor") OR\n("sensors") OR\n'
            '("sensores") OR\n("robot*") OR\n("sensorss") OR\n("sensorses") OR\n("gpt-4") OR\n'
            '("gpt4")\n)\n'
        ),
    }
    assert list(rendered) == ["AA.txt", "BB.txt", "ALL.txt"]


def test_render_gate_with_both_options_off(wos_form):
    """With the options off each file holds the terms as they are."""
    rendered = wos_form.render_gate(
        _small_artefact(hyphen_closed_form=False, plural_tolerant=False)
    )
    assert rendered == {
        "AA.txt": 'TS = (\n("ai") OR\n("sensor")\n)\n',
        "BB.txt": 'TS = (\n("robot*") OR\n("sensors") OR\n("gpt-4")\n)\n',
        "ALL.txt": (
            'TS = (\n("ai") OR\n("sensor") OR\n("robot*") OR\n("sensors") OR\n("gpt-4")\n)\n'
        ),
    }
    assert list(rendered) == ["AA.txt", "BB.txt", "ALL.txt"]


def test_render_gate_follows_the_order_of_the_definitions(wos_form):
    """The definitions swapped: the files swap, and `ALL.txt` drops the other repeat."""
    swapped = list(reversed(_small_artefact()["definitions"]))
    rendered = wos_form.render_gate(_small_artefact(definitions=swapped))
    assert rendered == {
        "BB.txt": SMALL_BB,
        "AA.txt": SMALL_AA,
        "ALL.txt": (
            'TS = (\n("robot*") OR\n("sensors") OR\n("sensorss") OR\n("sensorses") OR\n'
            '("gpt-4") OR\n("gpt4") OR\n("ai") OR\n("sensor") OR\n("sensores")\n)\n'
        ),
    }
    assert list(rendered) == ["BB.txt", "AA.txt", "ALL.txt"]


def test_render_gate_reads_an_artefact_of_compile_queries(wos_form, tmp_path):
    """An artefact made by `translate.compile_queries` is rendered as the hand-written one."""
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text('TS = (\n("ai") OR\n("sensor")\n)\n', encoding="utf-8")
    second.write_text(
        'TS = (\n("robot*") OR\n("sensors") OR\n("gpt-4")\n)\n', encoding="utf-8"
    )
    artefact = translate.compile_queries(
        {"AA": first, "BB": second},
        hyphen_closed_form=True,
        plural_tolerant=True,
        decimal_whole=True,
        plural_exceptions=["ai"],
    )
    assert wos_form.render_gate(artefact) == SMALL_RENDERED


@pytest.mark.parametrize(
    "key", ["hyphen_closed_form", "plural_tolerant", "definitions"]
)
def test_render_gate_missing_key_of_the_artefact_raises(wos_form, key):
    """An artefact without one of its three required keys raises `KeyError`."""
    with pytest.raises(KeyError):
        wos_form.render_gate(_small_artefact(**{key: ...}))


@pytest.mark.parametrize("key", ["code", "terms"])
@pytest.mark.parametrize("position", [0, 1])
def test_render_gate_missing_key_of_a_definition_raises(wos_form, key, position):
    """A definition without its code or its terms raises `KeyError`."""
    artefact = _small_artefact()
    del artefact["definitions"][position][key]
    with pytest.raises(KeyError):
        wos_form.render_gate(artefact)


def test_render_gate_no_definitions_raises(wos_form):
    """An artefact whose list of definitions is empty raises `QueryError`."""
    with pytest.raises(QueryError):
        wos_form.render_gate(_small_artefact(definitions=[]))


# --------------------------------------------------------------------------
# The shipped files
# --------------------------------------------------------------------------


def _by_the_rules(term, closed, plural):
    """The rules of `plain_terms` written a second time, for counting only.

    Words and separators are cut with the word of the contract. A separator
    that holds a hyphen has two spellings with the closed form, any other has
    one; the last word has one, two or three endings. `itertools.product`
    varies its last factor fastest, which is the order of the contract.
    """
    word = r"[a-z0-9*]+"
    words = re.findall(word, term)
    separators = re.split(word, term)[1:-1]
    last = words[-1]
    if not plural or last.endswith("*") or not last[-1].isalpha():
        endings = [last]
    elif len(last) > 1 and last.endswith("y") and last[-2] not in "aeiou":
        endings = [last, last[:-1] + "ies"]
    else:
        endings = [last, last + "s", last + "es"]
    choices = [
        [separator, ""] if closed and "-" in separator else [separator]
        for separator in separators
    ]
    spelled = []
    for chosen in itertools.product(*choices):
        head = "".join(w + s for w, s in zip(words[:-1], chosen, strict=True))
        spelled += [head + ending for ending in endings]
    return spelled


def _group_by_the_rules(gate, terms):
    """The distinct plain terms of a list of terms of the gate, by `_by_the_rules`."""
    exceptions = set(gate.get("plural_exceptions", []))
    spelled = []
    for term in terms:
        plural = gate["plural_tolerant"] and term not in exceptions
        spelled += _by_the_rules(term, gate["hyphen_closed_form"], plural)
    return list(dict.fromkeys(spelled))


def _terms_of(gate, name):
    """The terms of the gate a shipped file is made from: one group, or all in order."""
    if name == "ALL.txt":
        return [
            term for definition in gate["definitions"] for term in definition["terms"]
        ]
    (definition,) = [d for d in gate["definitions"] if d["code"] + ".txt" == name]
    return definition["terms"]


def _shipped(name):
    """The bytes of one shipped file; a missing file fails the test that asks."""
    path = SHIPPED_DIR / name
    assert path.is_file(), f"{path} is missing"
    return path.read_bytes()


def test_by_the_rules_gives_the_rows_of_the_contract():
    """The second writing of the rules agrees with the contract's table."""
    for term, closed, plural, expected in TABLE:
        assert _by_the_rules(term, closed, plural) == expected


def test_shipped_directory_holds_the_eight_query_files(wos_form):
    """The `.txt` files of the directory are the eight the contract names."""
    assert SHIPPED_DIR.is_dir(), f"{SHIPPED_DIR} is missing"
    assert sorted(path.name for path in SHIPPED_DIR.glob("*.txt")) == sorted(
        SHIPPED_FILES
    )


def test_render_gate_of_the_gate_names_the_eight_files_in_order(wos_form, gate):
    """`render_gate` of the shipped artefact gives the eight files, `ALL.txt` last."""
    assert list(wos_form.render_gate(gate)) == SHIPPED_FILES


@pytest.mark.parametrize("name", SHIPPED_FILES)
def test_shipped_file_is_render_gate_byte_for_byte(wos_form, gate, name):
    """A shipped file holds exactly what `render_gate` produces for it."""
    rendered = wos_form.render_gate(gate)
    assert _shipped(name) == rendered[name].encode("utf-8")


@pytest.mark.parametrize("name", SHIPPED_FILES)
def test_shipped_file_is_read_back_into_its_plain_terms(wos_form, gate, name):
    """`parse_terms` reads a shipped file into the plain terms of its group.

    For `ALL.txt` these are the plain terms of every group in order, a repeat
    dropped where it comes second.
    """
    closed = gate["hyphen_closed_form"]
    plural = gate["plural_tolerant"]
    exceptions = gate.get("plural_exceptions", [])
    if name == "ALL.txt":
        expected = list(
            dict.fromkeys(
                plain
                for definition in gate["definitions"]
                for plain in wos_form.plain_code_terms(
                    definition["terms"], closed, plural, exceptions
                )
            )
        )
    else:
        expected = wos_form.plain_code_terms(
            _terms_of(gate, name), closed, plural, exceptions
        )
    assert parse_terms(_shipped(name).decode("utf-8")) == expected


@pytest.mark.parametrize("name", SHIPPED_FILES)
def test_shipped_file_holds_the_number_of_terms_the_rules_give(wos_form, gate, name):
    """The number of terms of a shipped file is the one computed here from the rules.

    The file is counted twice: by `parse_terms`, and by its lines, since the
    layout has one term per line between the first line and the last.
    """
    expected = len(_group_by_the_rules(gate, _terms_of(gate, name)))
    text = _shipped(name).decode("utf-8")
    assert len(parse_terms(text)) == expected
    lines = text.split("\n")
    assert lines[0] == "TS = ("
    assert lines[-2:] == [")", ""]
    assert len(lines) - 3 == expected


def test_shipped_all_file_holds_every_plain_term_of_the_seven_others(wos_form):
    """`ALL.txt` holds the terms of the seven group files in order, repeats dropped."""
    together = []
    for name in SHIPPED_FILES[:-1]:
        together += parse_terms(_shipped(name).decode("utf-8"))
    assert parse_terms(_shipped("ALL.txt").decode("utf-8")) == list(
        dict.fromkeys(together)
    )


def test_shipped_sha256sums_lists_the_eight_files(wos_form):
    """`SHA256SUMS` has one `sha256sum` line for each of the eight files, and no other."""
    text = _shipped("SHA256SUMS").decode("utf-8")
    assert text.endswith("\n")
    lines = text.splitlines()
    assert len(lines) == 8
    listed = {}
    for line in lines:
        found = re.fullmatch(r"([0-9a-f]{64})  ([^ ]+)", line)
        assert found is not None, f"not a sha256sum line: {line!r}"
        listed[found.group(2)] = found.group(1)
    assert sorted(listed) == sorted(SHIPPED_FILES)
    assert listed == {
        name: hashlib.sha256(_shipped(name)).hexdigest() for name in SHIPPED_FILES
    }


def test_shipped_readme_exists_and_is_not_empty(wos_form):
    """`README.md` stands beside the query files and says something."""
    assert _shipped("README.md").decode("utf-8").strip() != ""
