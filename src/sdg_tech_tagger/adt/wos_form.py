"""The technology gate written as Web of Science queries.

Contract: ``docs/adt-wos-form-contract.md``. The other direction of
``translate``: from the terms of a gate and the options its patterns were
compiled with, to query files in which every spelling a pattern accepts is
a term of its own, so that the files say what the patterns say with every
option off. The decimal rule cannot be written and is left out.
"""

import re
from collections.abc import Collection, Mapping, Sequence
from itertools import pairwise, product

from sdg_tech_tagger.adt import translate
from sdg_tech_tagger.adt.wos_query import QueryError

_WORD = re.compile(r"[a-z0-9*]+")
_VOWELS = "aeiou"


def _endings(word: str) -> list[str]:
    """The last word of a term and its regular plurals, as Amendment 1 forms them."""
    if len(word) > 1 and word.endswith("y") and word[-2] not in _VOWELS:
        return [word, word[:-1] + "ies"]
    return [word, word + "s", word + "es"]


def plain_terms(
    term: str, hyphen_closed_form: bool = False, plural_tolerant: bool = False
) -> list[str]:
    """One term to the plain terms that together say what it says under the options.

    Consumes a term as ``parse_terms`` returns it. Produces its spellings in
    a fixed order, without repeats: for each hyphenated separator, as written
    then glued, the first separator varying slowest; for each of those, the
    last word as written then its regular plurals. What stands before the
    first word or after the last is dropped. Raises ``QueryError`` where
    ``translate.term_pattern`` does, and when gluing would put a ``*`` inside
    a word.
    """
    # Refuses what the pattern builder refuses, with its messages.
    translate.term_pattern(term, hyphen_closed_form, plural_tolerant)
    term = term.strip().lower()
    found = list(_WORD.finditer(term))
    words = [match.group() for match in found]
    separators = [term[before.end() : after.start()] for before, after in pairwise(found)]
    spellings = []
    for word, separator in zip(words, separators, strict=False):
        if hyphen_closed_form and "-" in separator:
            if word.endswith("*"):
                raise QueryError(f"the closed spelling would put * inside a word: {term!r}")
            spellings.append([separator, ""])
        else:
            spellings.append([separator])
    last = words[-1]
    plural = plural_tolerant and not last.endswith("*") and last[-1].isalpha()
    endings = _endings(last) if plural else [last]
    plain = []
    for chosen in product(*spellings):
        head = "".join(word + separator for word, separator in zip(words, chosen, strict=False))
        plain.extend(head + ending for ending in endings)
    return list(dict.fromkeys(plain))


def _comparable(term: str) -> str:
    """A term as two terms are compared: stripped, lower-cased, one space between words."""
    return " ".join(term.split()).lower()


def plain_code_terms(
    terms: Sequence[str],
    hyphen_closed_form: bool = False,
    plural_tolerant: bool = False,
    plural_exceptions: Collection[str] = (),
) -> list[str]:
    """The terms of one group to its plain terms, in order, a repeat dropped.

    A term listed in ``plural_exceptions`` is expanded without plurals; an
    exception that is no term of the list is ignored. Raises ``QueryError``
    for an empty list.
    """
    if not terms:
        raise QueryError("a code needs at least one term")
    exceptions = {_comparable(exception) for exception in plural_exceptions}
    plain: list[str] = []
    for term in terms:
        plain.extend(
            plain_terms(
                term, hyphen_closed_form, plural_tolerant and _comparable(term) not in exceptions
            )
        )
    return list(dict.fromkeys(plain))


def query_text(terms: Sequence[str]) -> str:
    """Plain terms to one Web of Science query, in the layout of the gate's query files.

    Produces ``TS = (``, one ``("term") OR`` line per term, the last without
    `` OR``, then ``)``, each line ended by a newline. Raises ``QueryError``
    for an empty list and for a term that holds a double quote.
    """
    if not terms:
        raise QueryError("a query needs at least one term")
    for term in terms:
        if '"' in term:
            raise QueryError(f"a term cannot hold a double quote: {term!r}")
    lines = " OR\n".join(f'("{term}")' for term in terms)
    return f"TS = (\n{lines}\n)\n"


def render_gate(artefact: Mapping) -> dict[str, str]:
    """A compiled gate to the text of its Web of Science query files, by name.

    Consumes an artefact as ``translate.compile_queries`` produces it.
    Produces ``<code>.txt`` for each definition in order, then ``ALL.txt``,
    one query for every plain term of the gate, a repeat dropped where it
    comes second. ``decimal_whole`` changes nothing. Raises ``QueryError``
    for an artefact without definitions and ``KeyError`` for a missing key.
    """
    hyphen_closed_form = artefact["hyphen_closed_form"]
    plural_tolerant = artefact["plural_tolerant"]
    definitions = artefact["definitions"]
    exceptions = artefact.get("plural_exceptions", ())
    if not definitions:
        raise QueryError("the artefact has no definition")
    files: dict[str, str] = {}
    every: list[str] = []
    for definition in definitions:
        plain = plain_code_terms(
            definition["terms"], hyphen_closed_form, plural_tolerant, exceptions
        )
        files[f"{definition['code']}.txt"] = query_text(plain)
        every.extend(plain)
    files["ALL.txt"] = query_text(list(dict.fromkeys(every)))
    return files
