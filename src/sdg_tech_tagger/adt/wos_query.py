"""Reading a Web of Science ADT query file into its list of terms.

Contract: ``docs/query-translation-contract.md``. The ADT query files are one
``TS = ( ("term") OR ("term") ... )`` block each, a plain disjunction of quoted
terms, and this module accepts nothing else: a query that needs ``AND``,
``NOT`` or ``NEAR`` is not a list of terms and raises rather than being
flattened into one.
"""

import re


class QueryError(ValueError):
    """A query could not be read as a disjunction of terms, or a term cannot be compiled."""


_TOKEN = re.compile(
    r'"(?P<phrase>[^"]*)"'
    r"|(?P<paren>[()])"
    r"|(?P<tag>[A-Za-z]{2})\s*="
    r"|(?P<word>[A-Za-z]+(?:/\d+)?)"
    r"|(?P<space>\s+)"
)

_SET_OPERATORS = ("AND", "NOT", "NEAR")


def _tokenise(text: str) -> list[tuple[str, str]]:
    """Query text to ``(kind, value)`` tokens, the ``TS =`` tags dropped.

    Kinds are ``phrase``, ``paren`` and ``or``. Anything that is not one of
    them, a ``TS =`` tag or whitespace raises ``QueryError``.
    """
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise QueryError(f"cannot read query at {text[position : position + 40]!r}")
        position = match.end()
        if match.group("space") is not None:
            continue
        if match.group("phrase") is not None:
            tokens.append(("phrase", match.group("phrase")))
        elif match.group("paren") is not None:
            tokens.append(("paren", match.group("paren")))
        elif match.group("tag") is not None:
            if match.group("tag").upper() != "TS":
                raise QueryError(f"unsupported field tag {match.group(0)!r}")
        else:
            word = match.group("word").upper()
            if word == "OR":
                tokens.append(("or", word))
            elif word.split("/")[0] in _SET_OPERATORS:
                raise QueryError(f"{word} is not supported: the query must be a disjunction")
            else:
                raise QueryError(f"unquoted text {match.group('word')!r} in the query")
    return tokens


def _read_disjunction(tokens: list[tuple[str, str]], position: int, terms: list[str]) -> int:
    """Read ``atom (OR atom)*`` from ``position``, appending terms; return the next position."""
    position = _read_atom(tokens, position, terms)
    while position < len(tokens) and tokens[position][0] == "or":
        position = _read_atom(tokens, position + 1, terms)
    return position


def _read_atom(tokens: list[tuple[str, str]], position: int, terms: list[str]) -> int:
    """Read one quoted term or one parenthesised disjunction."""
    if position >= len(tokens):
        raise QueryError("query ends where a term was expected")
    kind, value = tokens[position]
    if kind == "phrase":
        # Inner whitespace is collapsed so that "big  data" repeats "big data".
        term = " ".join(value.split()).lower()
        if not term:
            raise QueryError("empty term")
        terms.append(term)
        return position + 1
    if (kind, value) == ("paren", "("):
        position = _read_disjunction(tokens, position + 1, terms)
        if position >= len(tokens) or tokens[position] != ("paren", ")"):
            raise QueryError("unbalanced parenthesis, or two terms with no OR between them")
        return position + 1
    raise QueryError(f"expected a term, found {value!r}")


def parse_terms(text: str) -> list[str]:
    """The text of one query file to its terms.

    Consumes a disjunction of double-quoted terms, with any nesting in
    parentheses and an optional ``TS =`` tag. Produces the terms stripped,
    lower-cased and with inner whitespace collapsed to one space, in the order
    they are first written, repeats dropped. Raises
    ``QueryError`` for anything that is not such a disjunction.
    """
    tokens = _tokenise(text)
    if not tokens:
        raise QueryError("empty query")
    terms: list[str] = []
    position = _read_disjunction(tokens, 0, terms)
    if position != len(tokens):
        raise QueryError(f"unexpected {tokens[position][1]!r} after a complete query")
    return list(dict.fromkeys(terms))
