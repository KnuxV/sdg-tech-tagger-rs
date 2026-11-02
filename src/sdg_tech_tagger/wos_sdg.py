"""The four systems written as Web of Science queries, one per system and goal.

Contract: ``docs/wos-sdg-contract.md``. The published queries of
Aurora, Elsevier and Auckland are read as Scopus documents its syntax and
written again in the syntax of the Web of Science, operator for operator;
the vocabulary of SIRIS is written from its rows. What may not run there,
or may not mean the same, is returned beside each text as notes. Nothing
here says what the Web of Science returns.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import NamedTuple


class QueryError(ValueError):
    """A query that cannot be read, or cannot be written for the Web of Science."""


class Translation(NamedTuple):
    """The Web of Science text of one query, and what in it may not hold there."""

    text: str
    notes: list[tuple[str, str]]


_WILDCARDS = "*?"
_SCOPUS_PIECE = re.compile(
    r"\{(?P<braces>[^}]*)\}"
    r'|"(?P<quotes>[^"]*)"'
    r"|(?P<paren>[()])"
    r'|(?P<word>[^\s(){}"]+)'
    r"|(?P<space>\s+)"
)
_WOS_PIECE = re.compile(
    r'"(?P<quotes>[^"]*)"|(?P<paren>[()])|(?P<word>[^\s()"]+)|(?P<space>\s+)'
)
_FIELD = re.compile(r"[A-Z]+(?:-[A-Z]+)*")
_AURORA = "{http://aurora-network.global/queries/namespace/}"

# Inside this module a term carries whether it was in braces, and the `and`
# of a chain carries a mark, so that `translate` can note both. `_public`
# removes them; every public tree is the plain one of the contract.
_CHAIN = "chain"


def _collapse(text: str) -> str:
    """A text stripped, with inner white space collapsed to single spaces."""
    return " ".join(text.split())


def _term(text: str, braced: bool = False) -> tuple:
    """A term node, refusing what no Web of Science term can hold."""
    text = _collapse(text)
    if not text:
        raise QueryError("empty term")
    if '"' in text:
        raise QueryError(f"a term cannot hold a double quote: {text!r}")
    for word in text.split():
        if re.search(r"[*?]{2}", word):
            raise QueryError(f"two wildcards side by side in {text!r}")
    return ("term", text, braced)


def _holds(tree: tuple, kinds: tuple[str, ...]) -> bool:
    """Whether a node of one of the kinds is in the tree, itself included."""
    if tree[0] in kinds:
        return True
    return any(_holds(operand, kinds) for operand in _operands(tree))


def _operands(tree: tuple) -> tuple:
    """The operands of a node, none for a term."""
    kind = tree[0]
    if kind == "term":
        return ()
    if kind in ("or", "and"):
        return tree[1]
    if kind == "not":
        return (tree[1], tree[2])
    return (tree[2], tree[3])


def _public(tree: tuple) -> tuple:
    """A tree of this module as the contract defines it, marks removed."""
    kind = tree[0]
    if kind == "term":
        return ("term", tree[1])
    if kind in ("or", "and"):
        return (kind, tuple(_public(operand) for operand in tree[1]))
    if kind == "not":
        return ("not", _public(tree[1]), _public(tree[2]))
    return ("near", tree[1], _public(tree[2]), _public(tree[3]))


class _Reader:
    """The pieces of a query and a position in them."""

    def __init__(self, pieces: list[tuple[str, str]]) -> None:
        self.pieces = pieces
        self.at = 0

    def peek(self) -> tuple[str, str] | None:
        """The next piece, not consumed."""
        return self.pieces[self.at] if self.at < len(self.pieces) else None

    def take(self) -> tuple[str, str]:
        """The next piece, consumed."""
        piece = self.pieces[self.at]
        self.at += 1
        return piece

    def operator(self, name: str) -> bool:
        """Consume the operator ``name`` if it is next."""
        if self.peek() == ("operator", name):
            self.at += 1
            return True
        return False

    def distance(self, name: str) -> int | None:
        """Consume a proximity operator ``name/n`` if it is next, and return n."""
        piece = self.peek()
        if piece is not None and piece[0] == name:
            self.at += 1
            return int(piece[1])
        return None

    def close(self) -> None:
        """Consume a closing parenthesis, or refuse the query."""
        if self.peek() != ("paren", ")"):
            found = self.peek()
            if found is None or found[0] == "operator":
                raise QueryError("a parenthesis is not closed")
            raise QueryError("two operands with no operator between them")
        self.at += 1

    def end(self) -> None:
        """Refuse whatever follows a complete query."""
        piece = self.peek()
        if piece is None:
            return
        if piece == ("paren", ")"):
            raise QueryError("a closing parenthesis with none open")
        if piece[0] in ("operator", "W", "PRE", "NEAR"):
            raise QueryError(f"operator {piece[1]!r} with no operand")
        raise QueryError("two operands with no operator between them")


def _pieces(text: str, pattern: re.Pattern) -> list[re.Match]:
    """The matches of ``pattern`` that cover ``text``, white space dropped."""
    found = []
    position = 0
    while position < len(text):
        match = pattern.match(text, position)
        if match is None:
            raise QueryError(f"a quote or a brace is not closed at {text[position : position + 40]!r}")
        position = match.end()
        if match.group("space") is None:
            found.append(match)
    return found


def _scopus_pieces(query: str) -> list[tuple[str, str]]:
    """A published query to its pieces: terms, parentheses and operators."""
    text = query.replace("\xa0", " ").replace("“", '"').replace("”", '"')
    matches = _pieces(text, _SCOPUS_PIECE)
    pieces: list[tuple[str, str]] = []
    index = 0
    while index < len(matches):
        match = matches[index]
        following = matches[index + 1] if index + 1 < len(matches) else None
        index += 1
        if match.group("braces") is not None:
            if '"' in match.group("braces"):
                raise QueryError(f"a double quote inside braces: {match.group(0)!r}")
            pieces.append(("braces", match.group("braces")))
        elif match.group("quotes") is not None:
            pieces.append(("quotes", match.group("quotes")))
        elif match.group("paren") is not None:
            pieces.append(("paren", match.group("paren")))
        else:
            word = match.group("word")
            upper = word.upper()
            opens = following is not None and following.group("paren") == "("
            if _FIELD.fullmatch(word) and upper not in ("AND", "OR", "NOT") and opens:
                if word != "TITLE-ABS-KEY":
                    raise QueryError(f"field {word} is not supported")
                continue
            proximity = re.fullmatch(r"(W|PRE)/(\d+)", upper)
            if proximity:
                pieces.append((proximity.group(1), proximity.group(2)))
            elif upper == "AND" and following is not None and (following.group("word") or "").upper() == "NOT":
                pieces.append(("operator", "AND NOT"))
                index += 1
            elif upper in ("AND", "OR"):
                pieces.append(("operator", upper))
            else:
                pieces.append(("word", word))
    return pieces


def _scopus_and_not(reader: _Reader) -> tuple:
    """Operands joined by ``AND NOT``, which binds last."""
    tree = _scopus_and(reader)
    while reader.operator("AND NOT"):
        tree = ("not", tree, _scopus_and(reader))
    return tree


def _scopus_and(reader: _Reader) -> tuple:
    """Operands joined by ``AND``."""
    operands = [_scopus_proximity(reader)]
    while reader.operator("AND"):
        operands.append(_scopus_proximity(reader))
    return operands[0] if len(operands) == 1 else ("and", tuple(operands))


def _scopus_proximity(reader: _Reader) -> tuple:
    """Operands joined by ``W/n``: one pair, or a chain written as its pairs."""
    operands = [_scopus_or(reader)]
    distances = []
    while True:
        if reader.peek() is not None and reader.peek()[0] == "PRE":
            raise QueryError("PRE/n has no form on the Web of Science")
        distance = reader.distance("W")
        if distance is None:
            break
        distances.append(distance)
        operands.append(_scopus_or(reader))
    if not distances:
        return operands[0]
    for operand in operands:
        if _holds(operand, ("and", "not")):
            raise QueryError("an AND or an AND NOT inside a W/n has no form on the Web of Science")
    pairs = tuple(
        ("near", distance, left, right)
        for distance, left, right in zip(distances, operands, operands[1:], strict=False)
    )
    return pairs[0] if len(pairs) == 1 else ("and", pairs, _CHAIN)


def _scopus_or(reader: _Reader) -> tuple:
    """Operands joined by ``OR``, which binds first."""
    operands = [_scopus_atom(reader)]
    while reader.operator("OR"):
        operands.append(_scopus_atom(reader))
    return operands[0] if len(operands) == 1 else ("or", tuple(operands))


def _scopus_atom(reader: _Reader) -> tuple:
    """A parenthesised query or a term."""
    piece = reader.peek()
    if piece is None:
        raise QueryError("the query ends where an operand is expected")
    kind, value = reader.take()
    if (kind, value) == ("paren", "("):
        tree = _scopus_and_not(reader)
        reader.close()
        return tree
    if kind in ("braces", "quotes", "word"):
        return _term(value, braced=kind == "braces")
    raise QueryError(f"{value!r} where an operand is expected")


def _read_scopus(query: str) -> tuple:
    """A published query to the tree of this module, marks kept."""
    reader = _Reader(_scopus_pieces(query))
    if not reader.pieces:
        raise QueryError("empty query")
    tree = _scopus_and_not(reader)
    reader.end()
    return tree


def read_scopus(query: str) -> tuple:
    """One published query in Scopus syntax to its tree.

    Consumes a query in which ``OR`` binds first, then ``W/n``, ``AND`` and
    ``AND NOT``. Produces the tree of the contract: terms, ``or``, ``and``,
    ``not`` and ``near`` nodes, a chain of ``W/n`` written as the ``and`` of
    its neighbouring pairs, ``TITLE-ABS-KEY`` dropped. Raises ``QueryError``
    for what has no Web of Science form (``PRE/n``, an ``AND`` inside a
    ``W/n``, another field) and for a query that cannot be read.
    """
    return _public(_read_scopus(query))


def write_wos(tree: tuple) -> str:
    """A tree to Web of Science text, every node but a term in parentheses.

    Raises ``QueryError`` for a term that holds a double quote.
    """
    kind = tree[0]
    if kind == "term":
        if '"' in tree[1]:
            raise QueryError(f"a term cannot hold a double quote: {tree[1]!r}")
        return f'"{tree[1]}"'
    if kind in ("or", "and"):
        return "(" + f" {kind.upper()} ".join(write_wos(operand) for operand in tree[1]) + ")"
    if kind == "not":
        return f"({write_wos(tree[1])} NOT {write_wos(tree[2])})"
    return f"({write_wos(tree[2])} NEAR/{tree[1]} {write_wos(tree[3])})"


def _wos_pieces(text: str) -> list[tuple[str, str]]:
    """Web of Science text to its pieces, a leading ``TS=`` dropped."""
    text = re.sub(r"^\s*TS\s*=", "", text)
    pieces: list[tuple[str, str]] = []
    for match in _pieces(text, _WOS_PIECE):
        if match.group("quotes") is not None:
            pieces.append(("quotes", match.group("quotes")))
        elif match.group("paren") is not None:
            pieces.append(("paren", match.group("paren")))
        else:
            upper = match.group("word").upper()
            near = re.fullmatch(r"NEAR/(\d+)", upper)
            if near:
                pieces.append(("NEAR", near.group(1)))
            elif upper in ("AND", "OR", "NOT"):
                pieces.append(("operator", upper))
            else:
                raise QueryError(f"unquoted text {match.group('word')!r} in the query")
    return pieces


def _wos_or(reader: _Reader) -> tuple:
    """Operands joined by ``OR``, which the Web of Science binds last."""
    operands = [_wos_and(reader)]
    while reader.operator("OR"):
        operands.append(_wos_and(reader))
    return operands[0] if len(operands) == 1 else ("or", tuple(operands))


def _wos_and(reader: _Reader) -> tuple:
    """Operands joined by ``AND``."""
    operands = [_wos_not(reader)]
    while reader.operator("AND"):
        operands.append(_wos_not(reader))
    return operands[0] if len(operands) == 1 else ("and", tuple(operands))


def _wos_not(reader: _Reader) -> tuple:
    """Operands joined by ``NOT``."""
    tree = _wos_near(reader)
    while reader.operator("NOT"):
        tree = ("not", tree, _wos_near(reader))
    return tree


def _wos_near(reader: _Reader) -> tuple:
    """Two operands joined by ``NEAR/n``, which binds first, or one operand."""
    left = _wos_atom(reader)
    distance = reader.distance("NEAR")
    if distance is None:
        return left
    tree = ("near", distance, left, _wos_atom(reader))
    if reader.peek() is not None and reader.peek()[0] == "NEAR":
        raise QueryError("a NEAR/n joins two operands, not three")
    return tree


def _wos_atom(reader: _Reader) -> tuple:
    """A parenthesised query or a quoted term."""
    piece = reader.peek()
    if piece is None:
        raise QueryError("the query ends where an operand is expected")
    kind, value = reader.take()
    if (kind, value) == ("paren", "("):
        tree = _wos_or(reader)
        reader.close()
        return tree
    if kind == "quotes":
        return _term(value)
    raise QueryError(f"{value!r} where an operand is expected")


def read_wos(text: str) -> tuple:
    """Web of Science text, with or without ``TS=``, to its tree.

    Consumes text of the kind ``write_wos`` produces. Produces its tree by
    the binding order of the Web of Science: ``NEAR/n``, then ``NOT``,
    ``AND`` and ``OR``. Raises ``QueryError`` for a ``NEAR/n`` with three
    operands, an unquoted word, and a text that cannot be read.
    """
    reader = _Reader(_wos_pieces(text))
    if not reader.pieces:
        raise QueryError("empty query")
    tree = _wos_or(reader)
    reader.end()
    return _public(tree)


def _term_notes(text: str, braced: bool) -> list[tuple[str, str]]:
    """The notes of one term, at most one per code, in the order of the contract."""
    words = text.split()
    first = [min((word.find(w) for w in _WILDCARDS if w in word), default=-1) for word in words]
    found = []
    if braced and any(position >= 0 for position in first):
        found.append("braces-wildcard")
    if 0 in first:
        found.append("left-truncation")
    if 1 in first or 2 in first:
        found.append("short-stem")
    if not text.isascii():
        found.append("non-ascii")
    if "(" in text or ")" in text:
        found.append("parenthesis")
    return [(code, text) for code in found]


def _notes(tree: tuple) -> list[tuple[str, str]]:
    """The notes of a tree of this module, a node before its operands."""
    kind = tree[0]
    if kind == "term":
        return _term_notes(tree[1], len(tree) > 2 and tree[2])
    found = []
    if kind == "and" and len(tree) > 2:
        found.append(("chain", write_wos(tree)))
    if kind == "near" and (_holds(tree[2], ("near",)) or _holds(tree[3], ("near",))):
        found.append(("nested-proximity", write_wos(tree)))
    for operand in _operands(tree):
        found.extend(_notes(operand))
    return found


def notes(tree: tuple) -> list[tuple[str, str]]:
    """What in a tree may not run, or not mean the same, on the Web of Science.

    Consumes a tree. Produces ``(code, piece)`` pairs in the order of the
    written text, a node before its operands: ``nested-proximity`` with the
    text of the outer ``near``, and for a term ``left-truncation``,
    ``short-stem``, ``non-ascii`` and ``parenthesis`` with its text.
    """
    return _notes(_public(tree))


def translate(query: str) -> Translation:
    """One published query to its Web of Science text and its notes.

    The text is ``write_wos(read_scopus(query))``. The notes are those of
    ``notes``, with ``chain`` where a chain was rewritten and
    ``braces-wildcard`` where a term in braces holds a wildcard.
    """
    tree = _read_scopus(query)
    return Translation(write_wos(tree), _notes(tree))


def siris_expression(keyword: str, extra: str | None) -> Translation:
    """One row of the SIRIS vocabulary to its Web of Science text and notes.

    Consumes the keyword and its extra terms, separated by ``|``, or none.
    Produces the keyword alone, or the keyword ``AND`` its extra terms
    joined by ``OR``. Raises ``QueryError`` for an empty keyword and for a
    double quote.
    """
    key = _term(keyword)
    extras = [_term(term) for term in (extra or "").split("|") if term.strip()]
    if not extras:
        tree = key
    elif len(extras) == 1:
        tree = ("and", (key, extras[0]))
    else:
        tree = ("and", (key, ("or", tuple(extras))))
    return Translation(write_wos(tree), _notes(tree))


def goal_query(expressions: list[str]) -> str:
    """The Web of Science texts of one goal to one ``TS=`` line.

    Joins them by ``OR``, a repeat dropped where it comes second. Raises
    ``QueryError`` for an empty list.
    """
    if not expressions:
        raise QueryError("a goal needs at least one expression")
    return "TS=(" + " OR ".join(dict.fromkeys(expressions)) + ")\n"


def _aurora(published: Path) -> dict[int, list[Translation]]:
    """The query lines of Aurora v5.0.3, translated, by goal."""
    goals: dict[int, list[Translation]] = {}
    with zipfile.ZipFile(published / "aurora/sdg-queries-v5.0.3.zip") as archive:
        for name in archive.namelist():
            found = re.search(r"/query_SDG(\d+)\.xml$", name)
            if not found:
                continue
            root = ET.parse(io.BytesIO(archive.read(name))).getroot()
            goals[int(found.group(1))] = [
                translate(line.text) for line in root.iter(_AURORA + "query-line")
            ]
    return goals


def _workbook_rows(path: Path, sheet: str | None) -> list[tuple]:
    """The rows of one sheet of a workbook after its header."""
    import openpyxl

    book = openpyxl.load_workbook(path)
    return list((book[sheet] if sheet else book.active).iter_rows(values_only=True))[1:]


def _elsevier(published: Path) -> dict[int, list[Translation]]:
    """The queries of Elsevier 2019, translated, by goal."""
    rows = _workbook_rows(published / "elsevier/2019_v1/SDG_queries_collated_20191010.xlsx", None)
    return {int(goal): [translate(query)] for goal, query in rows if query}


def _auckland(published: Path) -> dict[int, list[Translation]]:
    """The queries of Auckland v2.0, translated, by goal."""
    rows = _workbook_rows(published / "auckland/uoa_sdg_queries_v_2.0.xlsx", "uoa_sdg_queries")
    return {int(str(goal)[3:]): [translate(query)] for goal, query in rows if query}


def _siris(published: Path) -> dict[int, list[Translation]]:
    """The rows of the SIRIS vocabulary v1.3, written, by the goal of their column."""
    import openpyxl

    goals: dict[int, list[Translation]] = {}
    book = openpyxl.load_workbook(published / "siris/sdg_vocabulary_V.1.3 [zenodo].xlsx")
    for sheet in book.worksheets:
        if sheet.title == "README":
            continue
        for row in list(sheet.iter_rows(values_only=True))[1:]:
            goal = int(str(row[0]).split()[1])
            goals.setdefault(goal, []).append(siris_expression(row[2], row[3]))
    return goals


def build(published: str | Path) -> dict[str, str]:
    """The published files of the four systems to every shipped query file.

    Consumes the path of ``published/``. Produces, by name relative to
    ``wos_queries/``, one ``TS=`` line per system and goal, then
    ``NOTES.tsv``, one row per note with its system, goal, line, code and
    piece. Needs ``openpyxl``.
    """
    published = Path(published)
    systems = {
        "aurora": _aurora(published),
        "elsevier": _elsevier(published),
        "auckland": _auckland(published),
        "siris": _siris(published),
    }
    files: dict[str, str] = {}
    rows = ["system\tsdg\tline\tcode\tpiece"]
    for system, goals in systems.items():
        for goal in sorted(goals):
            label = f"SDG-{goal:02d}"
            files[f"{system}/{label}.txt"] = goal_query([t.text for t in goals[goal]])
            seen: set[str] = set()
            for line, translation in enumerate(goals[goal], 1):
                if translation.text in seen:
                    continue
                seen.add(translation.text)
                rows.extend(
                    f"{system}\t{label}\t{line}\t{code}\t{piece}"
                    for code, piece in translation.notes
                )
    files["NOTES.tsv"] = "\n".join(rows) + "\n"
    return files
