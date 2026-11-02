"""Web of Science terms to engine-portable patterns, and matching with them.

Contract: ``docs/query-translation-contract.md``. Matching is two steps.

1. The text is normalised the way Web of Science tokenises it: lower-cased,
   every run of punctuation or whitespace turned into one space, one space at
   each end. With ``decimal_whole`` a dot or comma between two digits first
   becomes the letter ``p``, so "0.5g" stays one word and is not the word
   "5g", and "4.0" is not "40".
2. A pattern made only of ASCII letters, digits, single spaces, ``[^ ]*``,
   `` ?``, ``|`` and one group is searched in that text.

Step 2 has nothing in it on which RE2 (BigQuery, DuckDB) and the Rust regex
crate (Polars) can disagree, which is why the same pattern can be validated
here and executed there. A pattern applied to text that has not been through
step 1 is wrong: use ``matches`` or ``flag``, never the pattern alone. A
pattern compiled with ``decimal_whole`` is matched only against text
normalised with it: read the value from the artefact.
"""

import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

import polars as pl

from sdg_tech_tagger.adt.wos_query import QueryError, parse_terms

ARTEFACT_VERSION = 1

# The one engine-dependent expression of the design: a run of characters that
# are neither a Unicode letter nor a Unicode number.
SEPARATOR_RUN = r"[^\p{L}\p{N}]+"

# A dot or comma between two ASCII digits. Replaced by a marker letter, twice
# over, because matches cannot overlap and one pass leaves every second
# separator of "1.2.3". A marker, not nothing: deleting made "4.0" the word
# "40", and "industry 4.0" matched "industry. 40 firms" (Amendment 4).
DECIMAL_SEPARATOR = r"([0-9])[.,]([0-9])"
DECIMAL_MARKER = "p"

NORMALISATION = (
    "lower-case; every run of characters outside \\p{L}\\p{N} becomes one space; "
    "trimmed; one space added at each end"
)
NORMALISATION_DECIMAL_WHOLE = NORMALISATION.replace(
    "lower-case; ", "lower-case; a dot or comma between two ASCII digits becomes the letter p; "
)

_WORD = re.compile(r"[a-z0-9*]+")
_VALID_WORD = re.compile(r"[a-z0-9]+\*?")
_TRUNCATION = "[^ ]*"
_VOWELS = "aeiou"


def normalise_expr(text: pl.Expr, decimal_whole: bool = False) -> pl.Expr:
    """A string expression to its normalised form, never null.

    Null becomes empty, the text is lower-cased, every run of characters that
    are neither letters nor numbers becomes one space, and the result is
    trimmed and wrapped in one space at each end. With ``decimal_whole`` a
    dot or comma between two ASCII digits becomes ``p`` after lower-casing.
    """
    lowered = text.fill_null("").str.to_lowercase()
    if decimal_whole:
        for _ in range(2):
            lowered = lowered.str.replace_all(DECIMAL_SEPARATOR, "${1}" + DECIMAL_MARKER + "${2}")
    core = lowered.str.replace_all(SEPARATOR_RUN, " ").str.strip_chars(" ")
    return pl.concat_str([pl.lit(" "), core, pl.lit(" ")])


def normalise(text: str | None, decimal_whole: bool = False) -> str:
    """One value to its normalised form, through ``normalise_expr``."""
    return pl.select(normalise_expr(pl.lit(text, dtype=pl.String), decimal_whole)).item()


def _comparable(term: str) -> str:
    """A term as two terms are compared: stripped, lower-cased, one space between words."""
    return " ".join(term.split()).lower()


def _plural(word: str) -> str:
    """The last word of a term with its regular English plural made optional."""
    if word.endswith("y") and len(word) > 1 and word[-2] not in _VOWELS:
        return word[:-1] + "(?:y|ies)"
    return word + "(?:s|es)?"


def term_pattern(
    term: str,
    hyphen_closed_form: bool = False,
    plural_tolerant: bool = False,
    decimal_whole: bool = False,
) -> str:
    """One Web of Science term to the regex searched right after a space.

    Consumes a term as ``parse_terms`` returns it. Produces its words joined
    by one space, a final ``*`` compiled to ``[^ ]*``, and a closing space
    unless the last word is truncated. With ``hyphen_closed_form`` a hyphen
    between two words is `` ?`` so the closed spelling matches too. With
    ``plural_tolerant`` a last word that ends with a letter and is not
    truncated also matches its regular plural. With ``decimal_whole`` a dot or
    comma between two digits of the term first becomes ``p``, as it does in
    the text. Raises ``QueryError`` for a
    wildcard other than a word-final ``*`` and for any non-ASCII letter or
    digit.
    """
    term = term.strip().lower()
    if "?" in term or "$" in term:
        raise QueryError(f"wildcards ? and $ are not supported: {term!r}")
    if any(character.isalnum() and not character.isascii() for character in term):
        raise QueryError(f"non-ASCII letter or digit in term {term!r}")
    if decimal_whole:
        for _ in range(2):
            term = re.sub(DECIMAL_SEPARATOR, rf"\g<1>{DECIMAL_MARKER}\g<2>", term)
    words = list(_WORD.finditer(term))
    if not words:
        raise QueryError(f"term {term!r} has no word")
    pattern = ""
    for index, word in enumerate(words):
        if not _VALID_WORD.fullmatch(word.group()):
            raise QueryError(f"* is only supported at the end of a word: {term!r}")
        if index:
            separator = term[words[index - 1].end() : word.start()]
            pattern += " ?" if hyphen_closed_form and "-" in separator else " "
        text = word.group()
        if text.endswith("*"):
            pattern += text[:-1] + _TRUNCATION
        elif plural_tolerant and index == len(words) - 1 and text[-1].isalpha():
            pattern += _plural(text)
        else:
            pattern += text
    return pattern if pattern.endswith(_TRUNCATION) else pattern + " "


def code_pattern(
    terms: Sequence[str],
    hyphen_closed_form: bool = False,
    plural_tolerant: bool = False,
    decimal_whole: bool = False,
    plural_exceptions: Collection[str] = (),
) -> str:
    """The terms of one ADT to one pattern: a space, then their alternation.

    A term listed in ``plural_exceptions`` is compiled without plural
    tolerance. An exception that is not among the terms is ignored, since the
    list is shared by all codes.
    """
    if not terms:
        raise QueryError("a code needs at least one term")
    exceptions = {_comparable(exception) for exception in plural_exceptions}
    branches = "|".join(
        term_pattern(
            term,
            hyphen_closed_form,
            plural_tolerant and _comparable(term) not in exceptions,
            decimal_whole,
        )
        for term in terms
    )
    return f" (?:{branches})"


def matches(pattern: str, text: str | None, decimal_whole: bool = False) -> bool:
    """True when ``pattern`` is found in the normalised form of ``text``.

    ``decimal_whole`` is the value the pattern was compiled with.
    """
    normalised = normalise_expr(pl.lit(text, dtype=pl.String), decimal_whole)
    return bool(pl.select(normalised.str.contains(pattern)).item())


def flag(
    frame: pl.DataFrame,
    patterns: Mapping[str, str],
    fields: Sequence[str],
    decimal_whole: bool = False,
) -> pl.DataFrame:
    """Add one Boolean column per code: does its pattern match in any field?

    Consumes a frame, the code patterns, and the names of the string columns
    to search. Produces the same rows in the same order with one column per
    code, in the order of ``patterns``, never null. Each field is normalised
    on its own, so no term spans two fields. ``decimal_whole`` is the value
    the patterns were compiled with.
    """
    missing = [name for name in fields if name not in frame.columns]
    if missing or not fields:
        raise ValueError(f"fields to search are missing from the frame: {missing or 'none given'}")
    clashes = [code for code in patterns if code in frame.columns]
    if clashes:
        raise ValueError(f"codes are already columns of the frame: {clashes}")
    # Normalise each field once, not once per code.
    normalised = {name: f"__normalised_{index}" for index, name in enumerate(fields)}
    return (
        frame.with_columns(
            normalise_expr(pl.col(name), decimal_whole).alias(alias)
            for name, alias in normalised.items()
        )
        .with_columns(
            pl.any_horizontal(
                [pl.col(alias).str.contains(pattern) for alias in normalised.values()]
            ).alias(code)
            for code, pattern in patterns.items()
        )
        .drop(list(normalised.values()))
    )


def compile_queries(
    files: Mapping[str, Path],
    hyphen_closed_form: bool = False,
    plural_tolerant: bool = False,
    decimal_whole: bool = False,
    plural_exceptions: Collection[str] = (),
) -> dict:
    """The query file of each code to the artefact holding terms and patterns.

    Consumes a mapping from code to query file. Produces plain data, one
    definition per code in the order of the mapping, with the terms as parsed
    and the compiled pattern, so the queries are inspectable outside Python.
    ``decimal_whole`` and ``plural_exceptions`` are written into it only when
    used. Raises ``QueryError`` for a plural exception that is a term of none
    of the files.
    """
    exceptions = list(dict.fromkeys(_comparable(exception) for exception in plural_exceptions))
    definitions = []
    seen: set[str] = set()
    for code, path in files.items():
        terms = parse_terms(Path(path).read_text(encoding="utf-8"))
        seen.update(terms)
        definitions.append(
            {
                "code": code,
                "source": Path(path).name,
                "term_count": len(terms),
                "terms": terms,
                "pattern": code_pattern(
                    terms, hyphen_closed_form, plural_tolerant, decimal_whole, exceptions
                ),
            }
        )
    unknown = [exception for exception in exceptions if exception not in seen]
    if unknown:
        raise QueryError(f"plural exceptions that are terms of no query file: {unknown}")
    artefact: dict = {
        "version": ARTEFACT_VERSION,
        "normalisation": NORMALISATION_DECIMAL_WHOLE if decimal_whole else NORMALISATION,
        "hyphen_closed_form": hyphen_closed_form,
        "plural_tolerant": plural_tolerant,
    }
    # Written only when used, so an artefact compiled with the defaults keeps its keys.
    if decimal_whole:
        artefact["decimal_whole"] = True
    if exceptions:
        artefact["plural_exceptions"] = exceptions
    artefact["definitions"] = definitions
    return artefact
