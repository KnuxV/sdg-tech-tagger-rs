"""Write the fixture sets of the tests and run them through the two oracles.

Regenerating the fixtures needs R with text2sdg 1.1.2 installed (on the
library path R finds, or on ``R_LIBS_USER``) and the two R scripts that run
it in each mode, ``r/detect_text2sdg.R`` and ``r/detect_text2sdg_corrected.R``.
Those scripts belong to the development record and are not shipped with the
package; this file is kept to show how the stored fixtures were made, and
``--dry-run`` runs without them.

Usage, from the root of the repository:

    uv run python tests/fixtures/make_fixtures.py
    uv run python tests/fixtures/make_fixtures.py --sets hand --jobs 4
    uv run python tests/fixtures/make_fixtures.py --sets generated --dry-run

For each set it writes, into ``tests/fixtures/``:

- ``<set>_sentences.parquet``: ``UT`` and ``text``, both ``String``.
- ``<set>_compatible.parquet``: the rows of text2sdg 1.1.2.
- ``<set>_corrected.parquet``: the rows of text2sdg 1.1.2 with the six
  corrections of ``docs/contract.md`` applied.

The rows have the columns ``UT``, ``system``, ``sdg``, ``query_id`` (``Int32``)
and ``features``, sorted by the first four. Both oracles run with the four
systems and ``--keep-features true``, each on a fresh output directory in a
temporary work directory outside the repository. The sentences of a set are
split into shards run side by side (``--jobs``) and the rows concatenated:
text2sdg treats every document on its own, so this is the same as running
the set in one chunk. ``--dry-run`` writes the sentences only.

There are two sets.

- ``hand``: sentences written one by one in ``HAND_SENTENCES`` below, a few
  per kind of rule, and fifteen sentences written for the corrections of
  the corrected mode, a pair per correction.
- ``generated``: sentences built from the query strings of the four systems
  For every query, one sentence that should fire and one or more
  near misses; for Elsevier and Auckland, whose queries are long
  disjunctions, a sentence per branch of the outer disjunction. The
  generator does not decide what fires. The oracle does, and its rows are
  what is stored.

Everything is deterministic: a fixed seed per query, sorted output. The
words between the query terms are ours. No sentence here is taken from a
document.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent
QUERIES = ROOT / "queries"
SYSTEMS = "Aurora,Elsevier,SIRIS,Auckland"
ORACLES = {
    "compatible": ROOT / "r" / "detect_text2sdg.R",
    "corrected": ROOT / "r" / "detect_text2sdg_corrected.R",
}
KEY = ["UT", "system", "sdg", "query_id"]

# Words put between query terms. Short common words that no query of the
# four systems is made of on its own.
FILLER = [
    "the", "was", "then", "also", "very", "often", "here", "with", "this",
    "they", "were", "quite", "its", "such", "only", "some", "later", "those",
]

# How a wildcard is filled in when a term is turned into a word.
STAR_START = ["re", "bio", "agro", "un"]
STAR_MIDDLE = ["", "e", "o"]
STAR_END = ["", "s", "ing", "al", "ed", "ation"]
QUESTION_MARK = ["", "z", "s"]


# ---------------------------------------------------------------------------
# The hand-written set
# ---------------------------------------------------------------------------

# Fifteen sentences written for the corrections of the corrected mode, a pair
# per correction.
PROBE_SENTENCES = [
    "Income inequality hurts the poorest households.",
    (
        "Income inequality is rising in many countries of the region, and this report "
        "describes the poorest households."
    ),
    "Agriculture becomes sustainable.",
    "Agriculture can in time become sustainable.",
    "Poverty and development programs matter.",
    (
        "Poverty slows development in the region. Years later, developing new programs "
        "became possible."
    ),
    "Poverty reduces development and development programs.",
    "Chronic bronchitis leads to premature death.",
    "Chronic pain leads to premature death.",
    "We must prevent the extinction of species.",
    "The extinction of species continues.",
    "A national program improved reproductive healthcare.",
    "The program improved reproductive healthcare.",
    "Smoking cessation benefits everyone.",
    "Smoking cessation is hard. Later, quitting brought large benefits.",
]

# (identifier, text). The comment above each group says what the group is
# about and which query it aims at; what fires is the oracle's to say.
HAND_SENTENCES = [
    # Wildcards: a trailing star, a leading star (Elsevier and Auckland
    # *forest*), a question mark (fertili?er, urbani?ation, democrati?ation,
    # Auckland's fertili?wer), and the star inside Auckland's braces, which is
    # a character, as Scopus reads it.
    ("H-wild-01", "Microfinance helps rural households."),
    ("H-wild-02", "Micro-financing schemes reached the villages."),
    ("H-wild-03", "The search string literally says micro-financ* at this point."),
    ("H-wild-04", "Microfinanc* appears in a quoted search string."),
    ("H-wild-05", "Deforestation and reforestation changed the valley."),
    ("H-wild-06", "The forest was quiet."),
    ("H-wild-07", "Fertilizer and fertiliser prices rose."),
    ("H-wild-08", "Fertilier is a misspelling, and fertilisser has two letters too many."),
    ("H-wild-09", "Urbanisation and urbanization reshaped the coast."),
    ("H-wild-10", "Democratisation followed the elections."),
    ("H-wild-11", "Fertiliwer is an odd word, and fertilizwer is odder."),
    ("H-wild-12", "Agricultural reform made farms resilient."),
    # Sequences: adjacent and in order, broken by a word, by a comma, by
    # order. Elsevier <extreme poverty>, SIRIS "carbon monoxide poisoning".
    ("H-seq-01", "Carbon monoxide poisoning was reported."),
    ("H-seq-02", "Carbon monoxide caused poisoning."),
    ("H-seq-03", "Extreme poverty persists."),
    ("H-seq-04", "Extreme, poverty persists."),
    ("H-seq-05", "Poverty extreme persists."),
    ("H-seq-06", "Disaster risk reductions were planned in strategies."),
    ("H-seq-07", "Women’s participation grew, and women's participation grew."),
    ("H-seq-08", "The lithium–air battery and the lithium-air battery were compared."),
    # Proximity: Aurora SDG-03 id 3 asks tobacco within 6 of control*, or
    # health within 3 of smoking. Punctuation takes a position; order is
    # ignored; at most N positions apart.
    ("H-prox-01", "Tobacco use is hard to control."),
    ("H-prox-02", "Tobacco use, sadly, is hard to control."),
    ("H-prox-03", "Control of tobacco is a priority."),
    ("H-prox-04", "Tobacco: (a; b) control."),
    ("H-prox-05", "Tobacco one two three four five control."),
    ("H-prox-06", "Tobacco one two three four five six control."),
    ("H-prox-07", "Health and smoking were discussed."),
    ("H-prox-08", "Smoking was discussed at length, and health was not."),
    ("H-prox-09", "Agricultural land can, in time, become sustainable."),
    # NOT: Elsevier SDG-02 is (...) NOT <disease>, Elsevier SDG-04 ends in
    # NOT <health literacy>, Auckland SDG-02 in NOT biofuel.
    ("H-not-01", "The food supply chain was mapped."),
    ("H-not-02", "The food supply chain was mapped to fight disease."),
    ("H-not-03", "Smallholder farm incomes rose."),
    ("H-not-04", "Smallholder farm incomes rose thanks to biofuel."),
    ("H-not-05", "Teacher attrition is high."),
    ("H-not-06", "Teacher attrition is high and health literacy is low."),
    # AND: SIRIS ("dye wastewater") AND ("treatment"), anywhere in the text;
    # Elsevier ( <financial aid> AND <poverty> ).
    ("H-and-01", "Dye wastewater needs treatment."),
    ("H-and-02", "Dye wastewater was collected."),
    ("H-and-03", "Treatment came first. Many pages later, the dye wastewater was sampled."),
    ("H-and-04", "Financial aid reduced poverty."),
    ("H-and-05", "Financial aid was reduced."),
    # Hyphens: a hyphen is a token. SIRIS "anti-poverty" AND (...),
    # "micro-credit", "under-nutrition"; Aurora SDG-03 id 8 under-five.
    ("H-hyph-01", "Anti-poverty measures reduce vulnerability."),
    ("H-hyph-02", "Anti poverty measures reduce vulnerability."),
    ("H-hyph-03", "Micro-credit and microcredit and micro credit were offered."),
    ("H-hyph-04", "Under-nutrition is common; under nutrition is a spelling we also see."),
    ("H-hyph-05", "Low-income households and low income families."),
    # Braces of Auckland: a verbatim sequence, its comma and its apostrophe
    # are tokens to be matched.
    ("H-brace-01", "Water, sanitation and hygiene matter."),
    ("H-brace-02", "Water sanitation and hygiene matter."),
    ("H-brace-03", "Parkinson's disease is common."),
    ("H-brace-04", "Parkinson’s disease is common."),
    ("H-brace-05", "R&D spending rose."),
    ("H-brace-06", "URBAN POVERTY rose."),
    ("H-brace-07", "Urban and poverty are two words."),
    ("H-brace-08", "Heating, ventilation and air conditioning use energy."),
    # Case is ignored when matching.
    ("H-case-01", "EXTREME POVERTY PERSISTS."),
    ("H-case-02", "eXtReMe PoVeRtY persists."),
    ("H-case-03", "CARBON MONOXIDE POISONING."),
    # Aurora SDG-11 id 3, written by hand in detect_aurora: city near victim*
    # near physical or sexual harass*, with text2sdg's distance filter.
    ("H-aur-s1-01", "Victims of sexual harassment in cities."),
    ("H-aur-s1-02", "Victims of sexual harassment were interviewed over many months in the city."),
    ("H-aur-s1-03", "Urban victims were many; physical harassment, however, was rare."),
    ("H-aur-s1-04", "Physical harassment of urban victims."),
    ("H-aur-s1-05", "Sexual harassment in cities."),
    # Aurora SDG-03 id 8: reduce or end near neonatal or under-five near
    # mortality or death*.
    ("H-aur-s2-01", "We reduce neonatal mortality."),
    ("H-aur-s2-02", "Neonatal mortality is a burden that policy makers want to reduce."),
    ("H-aur-s2-03", "Ratios of under 5 deaths fell."),
    ("H-aur-s2-04", "Neonatal units were full and many deaths were recorded; we must prevent them."),
    ("H-aur-s2-05", "End mortality before fifth birthdays."),
    ("H-aur-s2-06", "Under-five mortality must end."),
    ("H-aur-s2-07", "Under five mortality must end."),
    ("H-aur-s2-08", "Underfive mortality must end."),
    ("H-aur-s2-09", "We reduced neonatal mortality."),
    # Aurora SDG-03 id 3 through its chain only, and broken.
    ("H-aur-s3-01", "Quitting smoking has health benefits."),
    ("H-aur-s3-02", "Smoking cessation clinics opened; years later, other clinics quit and health fell."),
    # The query text under two goals, Aurora SDG-04 id 8 and SDG-12 id 15, an
    # aurora_and chain.
    ("H-aur-dup-01", "Sustainable education programs are expanding."),
    ("H-aur-dup-02", "Global citizenship education curricula were revised."),
    (
        "H-aur-dup-03",
        (
            "Sustainable education matters; years later new policy was written for "
            "schools elsewhere and education policies changed."
        ),
    ),
    ("H-aur-dup-04", "Sustainable development and education."),
    # aurora_w: two halves, near and far apart.
    ("H-aur-w-01", "Safe green spaces for all."),
    (
        "H-aur-w-02",
        (
            "Safe streets matter, and much later in the plan, after many other "
            "chapters, the town opened public spaces."
        ),
    ),
    ("H-aur-w-03", "Disasters caused human losses."),
    ("H-aur-w-04", "Disasters were studied for decades by many teams before the number of deaths was known."),
    # aurora_and: disaster* near risk reduction* near strateg*.
    ("H-aur-and-01", "Disaster risk reduction strategies were adopted."),
    (
        "H-aur-and-02",
        (
            "Disaster risk reduction was discussed. Much later, in another chapter, "
            "risk reduction strategies were adopted."
        ),
    ),
    # Sequences of two wildcard terms, as Aurora writes <develop* countr*>,
    # beside the same words under a sequence of one wildcard term.
    ("H-wseq-01", "Child marriage persists."),
    ("H-wseq-02", "Scholarships for developing countries."),
    ("H-wseq-03", "Scholarships for least developed countries."),
    ("H-wseq-04", "Safe work environments."),
    # Parentheses inside SIRIS's quotes ("sole (fish)"), and the SIRIS
    # queries whose text holds backslashes ("el ni\\u00f1o").
    ("H-quote-01", "Sole (fish) is served."),
    ("H-quote-02", "Sole fish is served."),
    ("H-quote-03", "El niño changed the climate."),
    ("H-quote-04", 'The text \\"el ni\\u00f1o\\" and \\"climate\\" was found.'),
    # Text that is not ASCII: accents, a wildcard over an accented word,
    # Greek with a final sigma, Han, emoji, combining marks, a dotted capital I.
    ("H-utf-01", "La pauvreté extrême touche des millions; extreme poverty persists."),
    ("H-utf-02", "Sustainabilité education programmes."),
    ("H-utf-03", "Tobacco της πόλης control."),
    ("H-utf-04", "Tobacco ΤΗΣ ΠΟΛΗΣ ΚΑΙ ΤΗΣ ΧΩΡΑΣ ΜΑΣ control."),
    ("H-utf-05", "Η φτώχεια της πόλης: urban poverty in Greek towns."),
    ("H-utf-06", "Tobacco 控制吸烟很重要 control."),
    ("H-utf-07", "Tobacco 控制吸烟非常重要的 control."),
    ("H-utf-08", "极端贫困 extreme poverty 极端贫困."),
    ("H-utf-09", "Extreme 🙂 poverty persists."),
    ("H-utf-10", "Extreme poverty🙂 persists, 🌍 microfinance🌍 too."),
    ("H-utf-11", "Tobacco 🚭 🚭 🚭 🚭 🚭 🚭 control."),
    ("H-utf-12", "Tobacco 🚭 🚭 control."),
    ("H-utf-13", "Pauvrete\u0301 and extreme poverty, cafe\u0301 and microfinance."),
    ("H-utf-14", "MİCROFİNANCE and İNCOME İNEQUALİTY hurt the POOREST."),
    ("H-utf-15", "Ἀρχὴ ΟΔΥΣΣΕΥΣ and extreme poverty."),
    # Whitespace: tabs, new lines, a no-break space, space at both ends.
    ("H-ws-01", "  Extreme\tpoverty\n\npersists.  "),
    ("H-ws-02", "Tobacco\n\n\n\n\n\n\n\ncontrol."),
    ("H-ws-03", "Extreme\u00a0poverty persists."),
    ("H-ws-04", "Tobacco\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0control."),
    ("H-ws-05", "Extreme\u2003poverty and tobacco\u200bcontrol."),
    # Several sentences in one document, firing several systems and goals.
    (
        "H-multi-01",
        (
            "Extreme poverty persists in rural areas. Dye wastewater needs treatment. "
            "Tobacco use is hard to control. Sustainable education programs are expanding. "
            "Urban poverty rose while carbon monoxide poisoning fell."
        ),
    ),
    (
        "H-multi-02",
        (
            "Income inequality grew.\nThe poorest households lost most.\n\n"
            "Microfinance helped, and safe green spaces were opened."
        ),
    ),
]


def long_documents() -> list[tuple[str, str]]:
    """Return two long documents built from our own words.

    The first is some 3,000 tokens of filler with query terms at the start,
    in the middle and at the end, a proximity pair split across a sentence
    boundary, and a sequence that only appears once near the end. The second
    repeats one matching phrase many times, so that a firing has many
    matches.
    """
    rng = random.Random(20261003)
    words = [
        "river", "valley", "morning", "table", "window", "garden", "stone",
        "letter", "music", "paper", "travel", "orange", "simple", "quiet",
        "number", "method", "sample", "result", "figure", "model",
    ]

    def sentence(length: int) -> str:
        chosen = [rng.choice(words) for _ in range(length)]
        return " ".join(chosen).capitalize() + "."

    body = [sentence(rng.randint(8, 16)) for _ in range(250)]
    body[0] = "Extreme poverty opens this long text. " + body[0]
    body[120] = body[120] + " Tobacco use is hard to control."
    body[121] = "Tobacco is common. " + body[121] + " Control"
    body[200] = body[200] + " Dye wastewater was studied here."
    body[-1] = body[-1] + " Treatment of it, and income inequality hurts the poorest."
    first = " ".join(body)
    second = " ".join(["Extreme poverty persists, and microfinance helps."] * 60)
    return [("H-long-01", first), ("H-long-02", second)]


def hand_sentences() -> pl.DataFrame:
    """Return the hand-written set as a table of ``UT`` and ``text``."""
    rows = list(HAND_SENTENCES)
    rows += [(f"P{number:02d}", text) for number, text in enumerate(PROBE_SENTENCES, 1)]
    rows += long_documents()
    return _as_table(rows)


# ---------------------------------------------------------------------------
# A reader of corpustools query strings, as the four systems write them
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    """A bare or quoted word; may hold ``*`` and ``?``."""

    text: str


@dataclass(frozen=True)
class Verbatim:
    """A term in braces: matched as written, a star is a character."""

    text: str


@dataclass(frozen=True)
class Seq:
    """Members in order and adjacent, or within ``window`` positions."""

    members: tuple
    window: int | None


@dataclass(frozen=True)
class Bool:
    """``AND``, ``OR`` or ``NOT`` over its children (``NOT`` has two)."""

    op: str
    children: tuple


TOKEN = re.compile(r'\{[^}]*\}|"[^"]*"(?:~\d+)?|>~\d+|[()<>]|[^\s(){}<>"]+')


def parse(query: str):
    """Read a corpustools query string into a tree of the classes above.

    Only what the query tables use is read: parentheses, angle brackets with
    an optional ``~N``, quotes, braces, ``AND``, ``OR``, ``NOT`` and a space
    meaning ``OR``. A string this reader does not understand raises
    ``ValueError``.
    """
    tokens = TOKEN.findall(query)
    node, position = _parse_bool(tokens, 0, None)
    if position != len(tokens):
        raise ValueError(f"trailing tokens in {query!r}")
    return node


def _parse_bool(tokens, position, closer):
    operands, operators = [], []
    expect_operand = True
    while position < len(tokens) and tokens[position] != closer:
        token = tokens[position]
        if token in ("AND", "OR", "NOT"):
            operators.append(token)
            position += 1
            expect_operand = True
            continue
        if not expect_operand:
            operators.append("OR")
        operand, position = _parse_operand(tokens, position)
        operands.append(operand)
        expect_operand = False
    if closer is not None:
        if position >= len(tokens):
            raise ValueError(f"unclosed {closer!r}")
        position += 1
    if not operands:
        raise ValueError("empty group")
    if len(operands) == 1:
        return operands[0], position
    kinds = set(operators)
    if len(kinds) != 1:
        raise ValueError(f"mixed operators {kinds}")
    return Bool(kinds.pop(), tuple(operands)), position


def _parse_operand(tokens, position):
    token = tokens[position]
    if token == "(":
        return _parse_bool(tokens, position + 1, ")")
    if token == "<":
        return _parse_seq(tokens, position + 1)
    if token.startswith("{"):
        return Verbatim(token[1:-1].strip()), position + 1
    if token.startswith('"'):
        match = re.fullmatch(r'"([^"]*)"(?:~(\d+))?', token)
        # corpustools reads parentheses inside quotes as grouping, so a
        # sentence for "sole (fish)" carries the words without them.
        inner = match.group(1).replace("(", " ").replace(")", " ")
        words = tuple(Term(word) for word in inner.split())
        window = int(match.group(2)) if match.group(2) else None
        if len(words) == 1 and window is None:
            return words[0], position + 1
        return Seq(words, window), position + 1
    if token in (")", ">") or token.startswith(">~"):
        raise ValueError(f"unexpected {token!r}")
    return Term(token), position + 1


def _parse_seq(tokens, position):
    members = []
    while True:
        if position >= len(tokens):
            raise ValueError("unclosed <")
        token = tokens[position]
        if token == ">" or token.startswith(">~"):
            window = int(token[2:]) if token.startswith(">~") else None
            position += 1
            break
        if token in ("AND", "OR", "NOT"):
            # <a OR b>, and Elsevier's <women AND violence>: an operator
            # between members, kept as one member.
            previous = members.pop()
            following, position = _parse_operand(tokens, position + 1)
            members.append(Bool(token, (previous, following)))
            continue
        member, position = _parse_operand(tokens, position)
        members.append(member)
    if len(members) == 1 and window is None:
        return members[0], position
    return Seq(tuple(members), window), position


# ---------------------------------------------------------------------------
# Turning a tree into words
# ---------------------------------------------------------------------------


class Realiser:
    """Turns a query tree into a list of words, one variant at a time.

    ``variant`` names what is done to the tree on the way:

    - ``fire``: the members of every proximity side by side, every sequence
      adjacent, one branch of every ``OR``, the left side of every ``NOT``.
    - ``edge``: every proximity at its largest distance, ``N``.
    - ``far``: the first proximity one position too far, ``N + 1``.
    - ``punct``: the first proximity at ``N + 1``, one of the words between
      replaced by a comma.
    - ``swap``: the members of every proximity in reverse order.
    - ``drop``: the last child of the first ``AND`` left out.
    - ``not``: the right side of the first ``NOT`` written too.
    - ``seqbreak``: a word put inside the first sequence of two words or
      more.
    - ``hyphen``: every hyphen inside a term replaced by a space.
    - ``inflect``: an ``s`` added to the first term without a wildcard.
    - ``upper``: every word in capitals.
    """

    def __init__(self, variant: str, seed: str):
        self.variant = variant
        self.rng = random.Random(seed)
        self.done = False

    def filler(self, count: int) -> list[str]:
        """Return ``count`` filler words."""
        return [self.rng.choice(FILLER) for _ in range(count)]

    def once(self, name: str) -> bool:
        """True the first time the variant ``name`` is met, if it is ours."""
        if self.variant == name and not self.done:
            self.done = True
            return True
        return False

    def words(self, node) -> list[str]:
        """Return the words of ``node`` under this variant."""
        if isinstance(node, Term):
            return self.term(node.text)
        if isinstance(node, Verbatim):
            text = node.text
            if self.variant == "hyphen":
                text = text.replace("-", " ")
            if " " in text and self.once("seqbreak"):
                first, rest = text.split(" ", 1)
                text = " ".join([first, *self.filler(1), rest])
            if self.variant == "upper":
                text = text.upper()
            return [text]
        if isinstance(node, Seq):
            return self.seq(node)
        if node.op == "OR":
            return self.words(self.rng.choice(node.children))
        if node.op == "AND":
            children = list(node.children)
            if self.once("drop"):
                children = children[:-1]
            out: list[str] = []
            for index, child in enumerate(children):
                if index:
                    out += self.filler(2)
                out += self.words(child)
            return out
        # NOT
        out = self.words(node.children[0])
        if self.once("not"):
            out += self.filler(2) + self.words(node.children[1])
        return out

    def seq(self, node: Seq) -> list[str]:
        """Return the words of a sequence or a proximity."""
        parts = [self.words(member) for member in node.members]
        if node.window is None:
            if len(parts) > 1 and self.once("seqbreak"):
                return parts[0] + self.filler(1) + [w for part in parts[1:] for w in part]
            return [w for part in parts for w in part]
        window = node.window
        if self.variant == "swap":
            parts.reverse()
        # Members side by side: a hyphenated member is three tokens, and a
        # word between would put its far end out of a window of 3.
        gaps = [0] * (len(parts) - 1)
        punct = False
        if self.variant == "edge":
            gaps = [max(window - 1, 0)] * len(gaps)
        elif self.once("far"):
            gaps[0] = window
        elif self.once("punct"):
            gaps[0] = window
            punct = True
        out = list(parts[0])
        for index, part in enumerate(parts[1:]):
            between = self.filler(gaps[index])
            if punct and index == 0 and between:
                between[len(between) // 2] = ","
            out += between + part
        return out

    def term(self, text: str) -> list[str]:
        """Return a word that the term ``text`` should match."""
        if self.variant == "hyphen":
            text = text.replace("-", " ")
        if "*" not in text and "?" not in text and self.once("inflect"):
            text = text + ("es" if text.endswith("s") else "s")
        pieces = []
        for index, char in enumerate(text):
            if char == "*":
                if index == 0:
                    pieces.append(self.rng.choice(STAR_START))
                elif index == len(text) - 1:
                    pieces.append(self.rng.choice(STAR_END))
                else:
                    pieces.append(self.rng.choice(STAR_MIDDLE))
            elif char == "?":
                pieces.append(self.rng.choice(QUESTION_MARK))
            else:
                pieces.append(char)
        word = "".join(pieces)
        if self.variant == "upper":
            word = word.upper()
        return [word]


def has(node, kind: str) -> bool:
    """True if the tree holds something a variant of that name changes."""
    if isinstance(node, Term):
        if kind == "hyphen":
            return "-" in node.text
        if kind == "inflect":
            return "*" not in node.text and "?" not in node.text
        return False
    if isinstance(node, Verbatim):
        if kind == "hyphen":
            return "-" in node.text
        if kind == "seqbreak":
            return " " in node.text
        return False
    if isinstance(node, Seq):
        if kind in ("edge", "far", "punct", "swap") and node.window is not None:
            return True
        if kind == "seqbreak" and node.window is None and len(node.members) > 1:
            return True
        return any(has(member, kind) for member in node.members)
    if kind == "drop" and node.op == "AND":
        return True
    if kind == "not" and node.op == "NOT":
        return True
    return any(has(child, kind) for child in node.children)


def has_or(node) -> bool:
    """True if the tree holds an ``OR``."""
    if isinstance(node, (Term, Verbatim)):
        return False
    children = node.members if isinstance(node, Seq) else node.children
    return (isinstance(node, Bool) and node.op == "OR") or any(has_or(c) for c in children)


def as_sentence(words: list[str]) -> str:
    """Join words into a sentence with a capital and a full stop."""
    text = " ".join(word for word in words if word)
    return text[:1].upper() + text[1:] + "."


def realise(node, variant: str, seed: str) -> str:
    """Return the sentence of ``node`` under ``variant``."""
    return as_sentence(Realiser(variant, seed).words(node))


# ---------------------------------------------------------------------------
# The generated set
# ---------------------------------------------------------------------------

# Aurora's three queries written in the body of detect_aurora
# (vendor/text2sdg_1.1.2/R/aurora.R), as (sdg, query_id, search strings).
AURORA_BY_HAND = [
    (
        "SDG-11", 3,
        [
            "<(<physical> OR <sexual>) (<harass*>)>~3",
            "<victim*>",
            "(<city> OR <cities> OR <urban> OR <municipalit*>)",
        ],
    ),
    (
        "SDG-03", 8,
        [
            "(<neonatal> OR <under-five> OR ( <(<under>) (<5> OR <five>)>~2 ) OR <before fifth>)",
            "(<mortality> OR <death*>)",
            "(<reduce> OR <end> OR <ending> OR <prevent*> OR <ratio*>)",
        ],
    ),
    (
        "SDG-03", 3,
        [
            "( <(<tobacco>) (<control*>)>~6 ) OR ( <(<health>) (<smoking>)>~3 )",
            "<(<smoking>) (<cessation> OR <quit*>)>~3",
            "<(<cessation> OR <quit*>) (<health> OR <benefit*>)>~3",
        ],
    ),
]

SIMPLE_VARIANTS = ["far", "edge", "drop", "not", "hyphen", "punct", "swap", "seqbreak"]
BRANCH_VARIANTS = ["not", "drop", "hyphen", "seqbreak", "far", "inflect"]
BRANCH_CAP = 150


def _ident(system: str, sdg: str, query_id: int, tag: str) -> str:
    return f"G-{system}-{sdg[4:]}-{query_id:04d}-{tag}"


def simple_sentences(system, sdg, query_id, node, limit=6):
    """One sentence that should fire and up to ``limit - 1`` near misses."""
    seed = f"{system}/{sdg}/{query_id}"
    rows = [(_ident(system, sdg, query_id, "fire"), realise(node, "fire", seed))]
    if has_or(node):
        # another branch of its OR, chosen with another seed
        rows.append((_ident(system, sdg, query_id, "alt"), realise(node, "fire", seed + "/alt")))
    for variant in [v for v in SIMPLE_VARIANTS if has(node, v)][: limit - 1]:
        rows.append((_ident(system, sdg, query_id, variant), realise(node, variant, seed)))
    return rows


def pair_members(node):
    """The two members of a proximity of two, or None."""
    if isinstance(node, Seq) and node.window is not None and len(node.members) == 2:
        return node.members
    return None


def chain_sentences(system, sdg, query_id, first, second):
    """Sentences for a chain searched as two pairs, A near B and B near C."""
    seed = f"{system}/{sdg}/{query_id}"
    a_b, b_c = pair_members(first), pair_members(second)
    if a_b is None or b_c is None:
        return simple_sentences(system, sdg, query_id, Bool("AND", (first, second)))
    a, b = a_b
    b2, c = b_c
    w1, w2 = first.window, second.window

    def build(variant: str) -> list[str]:
        r = Realiser("fire", seed)
        middle = r.words(b) if b == b2 else r.words(b) + r.filler(1) + r.words(b2)
        if variant == "fire":
            return r.words(a) + r.filler(1) + middle + r.filler(1) + r.words(c)
        if variant == "edge":
            return r.words(a) + r.filler(w1 - 1) + middle + r.filler(w2 - 1) + r.words(c)
        if variant == "split":
            return (
                r.words(a) + r.filler(1) + r.words(b) + r.filler(8)
                + r.words(b2) + r.filler(1) + r.words(c)
            )
        if variant == "far":
            return r.words(a) + r.filler(w1) + middle + r.filler(1) + r.words(c)
        # one pair only
        return r.words(a) + r.filler(1) + r.words(b)

    return [
        (_ident(system, sdg, query_id, variant), as_sentence(build(variant)))
        for variant in ["fire", "edge", "split", "far", "pair"]
    ]


def halves_sentences(system, sdg, query_id, first, second):
    """Sentences for an aurora_w query: two halves, near and far apart."""
    seed = f"{system}/{sdg}/{query_id}"

    def build(variant: str) -> list[str]:
        r = Realiser("fire", seed)
        if variant == "fire":
            return r.words(first) + r.filler(1) + r.words(second)
        if variant == "edge":
            return r.words(first) + r.filler(2) + r.words(second)
        if variant == "apart":
            return r.words(first) + r.filler(9) + r.words(second)
        if variant == "half":
            return r.words(first)
        # the inner proximity of the first half, or else the second, too far
        inner = Realiser("far", seed)
        left = inner.words(first)
        return left + inner.filler(1) + inner.words(second)

    variants = ["fire", "edge", "apart", "half"]
    if has(first, "far") or has(second, "far"):
        variants.append("inner")
    return [
        (_ident(system, sdg, query_id, variant), as_sentence(build(variant)))
        for variant in variants
    ]


def by_hand_sentences(sdg, query_id, strings):
    """Sentences for the three Aurora queries written in detect_aurora."""
    system = "Aurora"
    nodes = [parse(string) for string in strings]
    seed = f"{system}/{sdg}/{query_id}"
    if (sdg, query_id) == ("SDG-03", 3):
        rows = simple_sentences(system, sdg, query_id, nodes[0])
        rows = [(ut.replace("-0003-", "-0003-one-"), text) for ut, text in rows]
        return rows + chain_sentences(system, sdg, query_id, nodes[1], nodes[2])
    # Three strings, each near the next: q3 q2 q1 for SDG-11 id 3,
    # q3 q1 q2 for SDG-03 id 8, as the published query orders them.
    order = [2, 1, 0] if sdg == "SDG-11" else [2, 0, 1]

    def build(variant: str) -> list[str]:
        r = Realiser("fire", seed)
        parts = [r.words(nodes[index]) for index in order]
        gaps = {"fire": [0, 0], "edge": [1, 0], "far": [6, 0], "far2": [0, 6]}
        if variant == "missing":
            return parts[1] + parts[2]
        first_gap, second_gap = gaps[variant]
        return parts[0] + r.filler(first_gap) + parts[1] + r.filler(second_gap) + parts[2]

    return [
        (_ident(system, sdg, query_id, variant), as_sentence(build(variant)))
        for variant in ["fire", "edge", "far", "far2", "missing"]
    ]


def branches(node):
    """Split a long query into the branches of its outer ``OR``.

    Returns (branch, the right sides of the ``NOT`` it sits under).
    """
    nots = []
    while isinstance(node, Bool) and node.op == "NOT":
        nots.append(node.children[1])
        node = node.children[0]
    if not (isinstance(node, Bool) and node.op == "OR"):
        return [(node, nots)]
    out = []
    for child in node.children:
        out += [(branch, nots + inner) for branch, inner in branches(child)]
    return out


def disjunction_sentences(system, sdg, query_id, node):
    """A sentence per branch of the outer ``OR``, and a near miss per branch."""
    found = branches(node)
    picked = list(range(len(found)))
    if len(picked) > BRANCH_CAP:
        picked = sorted(random.Random(f"{system}/{sdg}").sample(picked, BRANCH_CAP))
    rows = []
    for index in picked:
        branch, nots = found[index]
        seed = f"{system}/{sdg}/{query_id}/{index}"
        tag = f"b{index:03d}"
        rows.append((_ident(system, sdg, query_id, f"{tag}-fire"), realise(branch, "fire", seed)))
        if nots:
            r = Realiser("fire", seed)
            words = r.words(branch) + r.filler(2) + r.words(nots[0])
            rows.append((_ident(system, sdg, query_id, f"{tag}-outernot"), as_sentence(words)))
            if index % 3:
                continue
        variant = next((v for v in BRANCH_VARIANTS if has(branch, v)), None)
        if variant is not None:
            rows.append(
                (_ident(system, sdg, query_id, f"{tag}-{variant}"), realise(branch, variant, seed))
            )
    return rows


def siris_sentences(query_id, sdg, node):
    """The sentence that should fire, a near miss, and for a quarter a third."""
    system = "SIRIS"
    seed = f"{system}/{sdg}/{query_id}"
    rows = [(_ident(system, sdg, query_id, "fire"), realise(node, "fire", seed))]
    if has_or(node):
        rows.append((_ident(system, sdg, query_id, "alt"), realise(node, "fire", seed + "/alt")))
    misses = [v for v in ("drop", "hyphen", "seqbreak", "inflect") if has(node, v)]
    if misses:
        rows.append((_ident(system, sdg, query_id, misses[0]), realise(node, misses[0], seed)))
    if query_id % 4 == 0:
        extra = "upper" if query_id % 8 == 0 else "inflect"
        if extra != (misses[0] if misses else None):
            rows.append((_ident(system, sdg, query_id, extra), realise(node, extra, seed)))
    return rows


def aurora_keys() -> dict[str, list[tuple[str, int]]]:
    """Map an Aurora query text to its (sdg, query_id) pairs."""
    table = pl.read_parquet(QUERIES / "aurora_queries.parquet")
    keys: dict[str, list[tuple[str, int]]] = {}
    for row in table.iter_rows(named=True):
        keys.setdefault(row["query"], []).append((row["sdg"], row["query_id"]))
    return keys


def generated_sentences() -> pl.DataFrame:
    """Return the generated set as a table of ``UT`` and ``text``."""
    rows: list[tuple[str, str]] = []
    keys = aurora_keys()
    for table in ("aurora_simple", "aurora_and", "aurora_w"):
        frame = pl.read_parquet(QUERIES / f"{table}.parquet")
        for row in frame.iter_rows(named=True):
            sdg, query_id = keys[row["orig"]][0]
            first = parse(row["correct"])
            if table == "aurora_simple":
                rows += simple_sentences("Aurora", sdg, query_id, first)
            elif table == "aurora_and":
                rows += chain_sentences("Aurora", sdg, query_id, first, parse(row["correct 2"]))
            else:
                rows += halves_sentences("Aurora", sdg, query_id, first, parse(row["correct 2"]))
    for sdg, query_id, strings in AURORA_BY_HAND:
        rows += by_hand_sentences(sdg, query_id, strings)
    for system in ("Elsevier", "Auckland"):
        frame = pl.read_parquet(QUERIES / f"{system.lower()}_queries.parquet")
        for row in frame.iter_rows(named=True):
            rows += disjunction_sentences(system, row["sdg"], row["query_id"], parse(row["query"]))
    frame = pl.read_parquet(QUERIES / "siris_queries.parquet")
    for row in frame.iter_rows(named=True):
        rows += siris_sentences(row["query_id"], row["sdg"], parse(row["query"]))
    return _as_table(rows)


def _as_table(rows: list[tuple[str, str]]) -> pl.DataFrame:
    table = pl.DataFrame(rows, schema={"UT": pl.String, "text": pl.String}, orient="row")
    duplicated = table.filter(pl.col("UT").is_duplicated())
    if duplicated.height:
        raise ValueError(f"duplicate identifiers: {duplicated['UT'].head(5).to_list()}")
    blank = table.filter(pl.col("text").str.strip_chars() == "")
    if blank.height:
        raise ValueError(f"blank texts: {blank['UT'].head(5).to_list()}")
    return table.sort("UT")


# ---------------------------------------------------------------------------
# Running the oracles
# ---------------------------------------------------------------------------


def run_oracle(script: Path, documents: Path, out_dir: Path) -> None:
    """Run one oracle script on one parquet into a fresh directory."""
    environment = dict(os.environ)
    command = [
        "Rscript", str(script), "--documents", str(documents), "--out-dir", str(out_dir),
        "--systems", SYSTEMS, "--keep-features", "true", "--chunk-size", "1000000",
    ]
    result = subprocess.run(
        command, env=environment, capture_output=True, text=True, cwd=ROOT, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script.name} failed on {documents}:\n{result.stderr[-3000:]}")


def oracle_rows(sentences: pl.DataFrame, mode: str, work: Path, jobs: int) -> pl.DataFrame:
    """Return the rows of the oracle of ``mode`` for ``sentences``."""
    shards = max(1, min(jobs, sentences.height))
    size = -(-sentences.height // shards)
    tasks = []
    for number in range(shards):
        shard = sentences.slice(number * size, size)
        if shard.height == 0:
            continue
        documents = work / f"{mode}_shard_{number:02d}.parquet"
        shard.write_parquet(documents)
        tasks.append((documents, work / f"{mode}_out_{number:02d}"))
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        list(pool.map(lambda task: run_oracle(ORACLES[mode], *task), tasks))
    chunks = sorted(path for _, out in tasks for path in (out / "chunks").glob("chunk_*.parquet"))
    expected_chunks = len(tasks)
    if len(chunks) != expected_chunks:
        raise RuntimeError(f"expected {expected_chunks} chunk files, found {len(chunks)}")
    frames = [pl.read_parquet(path) for path in chunks]
    frames = [frame for frame in frames if frame.height]
    schema = {
        "UT": pl.String, "system": pl.String, "sdg": pl.String,
        "query_id": pl.Int32, "features": pl.String,
    }
    if not frames:
        return pl.DataFrame(schema=schema)
    rows = (
        pl.concat(frames, how="vertical_relaxed")
        .rename({"document": "UT"})
        .select(
            pl.col("UT").cast(pl.String),
            pl.col("system").cast(pl.String),
            pl.col("sdg").cast(pl.String),
            pl.col("query_id").cast(pl.Int32),
            pl.col("features").cast(pl.String),
        )
        .unique()
        .sort(KEY)
    )
    duplicated = rows.filter(pl.struct(KEY).is_duplicated())
    if duplicated.height:
        raise RuntimeError(f"the oracle returned a key twice:\n{duplicated.head()}")
    unknown = rows.join(sentences, on="UT", how="anti")
    if unknown.height:
        raise RuntimeError("the oracle returned an identifier that is not in the set")
    return rows


def build(name: str, sentences: pl.DataFrame, jobs: int, dry_run: bool) -> None:
    """Write one set: its sentences and, unless ``dry_run``, both oracles' rows."""
    sentences.write_parquet(FIXTURES / f"{name}_sentences.parquet")
    print(f"{name}: {sentences.height} sentences", flush=True)
    if dry_run:
        return
    with tempfile.TemporaryDirectory(prefix=f"fixtures_{name}_") as directory:
        work = Path(directory)
        for mode in ORACLES:
            started = time.monotonic()
            rows = oracle_rows(sentences, mode, work, jobs)
            elapsed = time.monotonic() - started
            rows.write_parquet(FIXTURES / f"{name}_{mode}.parquet")
            print(f"{name} {mode}: {rows.height} rows in {elapsed:.0f} s", flush=True)


SETS = {"hand": hand_sentences, "generated": generated_sentences}


def main() -> None:
    """Parse the arguments and write the sets asked for."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sets", default="hand,generated")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    missing = [str(script) for script in ORACLES.values() if not script.exists()]
    if missing and not arguments.dry_run:
        sys.exit("the R scripts of the oracles are missing: " + ", ".join(missing))
    for name in arguments.sets.split(","):
        build(name, SETS[name](), arguments.jobs, arguments.dry_run)


if __name__ == "__main__":
    main()
