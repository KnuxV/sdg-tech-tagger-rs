"""Tests of `sdg_tech_tagger.adt.wos_query`, written from the contract alone.

Source of every expected value: `docs/query-translation-contract.md`, section
"Module `wos_query`" of the contract. Each test feeds `parse_terms` the text
of a query, written by hand, and asserts the exact list of terms it returns or
the `QueryError` it raises.
"""

import pytest

from sdg_tech_tagger.adt.wos_query import QueryError, parse_terms


def test_query_error_is_a_value_error():
    """`QueryError` is declared as a subclass of `ValueError`."""
    assert issubclass(QueryError, ValueError)


# The three rows of the contract's example table that produce terms.
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('TS = ( ("Bitcoin") OR ("blockchain*") )', ["bitcoin", "blockchain*"]),
        ('TS=("a b" OR "c")', ["a b", "c"]),
        ('("data mining ") or ("Data Mining") OR ("x")', ["data mining", "x"]),
    ],
)
def test_contract_examples_that_parse(text, expected):
    """Each parsing row of the example table gives exactly the listed terms."""
    assert parse_terms(text) == expected


# The four rows of the contract's example table that raise.
@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") AND ("b") )',
        'TS = ( ("a") ("b") )',
        'TI = ("a")',
        'TS = ( ("a") OR iot )',
    ],
)
def test_contract_examples_that_raise(text):
    """Each error row of the example table raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


def test_result_is_a_list_of_strings():
    """The terms come back as a plain list of `str`."""
    terms = parse_terms('TS = ( ("Bitcoin") OR ("blockchain*") )')
    assert type(terms) is list
    assert [type(term) for term in terms] == [str, str]


@pytest.mark.parametrize(
    "text",
    [
        'TS = ("a")',
        'TS=("a")',
        'TS =("a")',
        'TS= ("a")',
        'TS   =   ("a")',
        'ts = ("a")',
        'Ts = ("a")',
        'tS=("a")',
        '("a")',
    ],
)
def test_field_tag_ts_is_removed_in_any_case_and_spacing(text):
    """`TS =` in any case, with optional spaces around `=`, or absent, is accepted."""
    assert parse_terms(text) == ["a"]


@pytest.mark.parametrize(
    "text",
    [
        'TI = ("a")',
        'TI=("a")',
        'AB = ("a")',
        'AK=("a") OR ("b")',
        'ti = ("a")',
        'TS = ( TI = ("a") )',
    ],
)
def test_other_field_tag_raises(text):
    """A two-letter field tag other than `TS` raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") AND ("b") )',
        'TS = ( ("a") and ("b") )',
        'TS = ("a" AND "b")',
        'TS = ( ("a") OR ("b") AND ("c") )',
    ],
)
def test_and_raises(text):
    """`AND` between terms raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") NOT ("b") )',
        'TS = ( ("a") not ("b") )',
        'TS = ("a" NOT "b")',
        'TS = ( ("a") OR NOT ("b") )',
    ],
)
def test_not_raises(text):
    """`NOT` raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") NEAR ("b") )',
        'TS = ( ("a") near ("b") )',
        'TS = ("a" NEAR "b")',
    ],
)
def test_near_raises(text):
    """`NEAR` raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") NEAR/3 ("b") )',
        'TS = ( ("a") NEAR/15 ("b") )',
        'TS = ("a" near/3 "b")',
    ],
)
def test_near_with_distance_raises(text):
    """`NEAR/n` raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") OR iot )',
        'TS = ( iot OR ("a") )',
        "TS = ( iot )",
        "TS = iot",
        'TS = ( ("a") OR ("b") ) 2019',
        'TS = ( ("a") OR ("b") );',
        'TS = ( ("a"), ("b") )',
        'TS = ( ("a") | ("b") )',
        'TS = ( ("a") OR ("b") ) x',
        'TS = ( ("a") OR * )',
    ],
)
def test_text_outside_quotes_raises(text):
    """Text outside quotes that is not a parenthesis, `OR` or whitespace raises."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") OR ("b")',
        'TS = ( ("a") OR ("b") ) )',
        'TS = ( ("a" OR ("b") )',
        'TS = ("a"',
        'TS = "a")',
        'TS = ) ("a") (',
        '(("a") OR ("b")',
    ],
)
def test_unbalanced_parenthesis_raises(text):
    """A parenthesis that is never closed, or closed without being opened, raises."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") ("b") )',
        'TS = ( "a" "b" )',
        'TS = ( ("a") OR ("b") ("c") )',
        'TS = ( "a" ("b" OR "c") )',
        'TS = ( ("a" OR "b") "c" )',
        'TS = ("a")\n("b")',
    ],
)
def test_two_terms_with_no_or_between_them_raise(text):
    """Two terms, or a term and a group, with no `OR` between them raise."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ( ("a") OR )',
        'TS = ( OR ("a") )',
        'TS = ( ("a") OR ("b") OR )',
        'TS = ( ("a") OR ("b") ) OR',
        'TS = OR ("a")',
        'TS = ("a" OR)',
        'TS = ( ("a") OR OR ("b") )',
        "TS = ( OR )",
        "OR",
    ],
)
def test_dangling_or_raises(text):
    """An `OR` with no term or group on one of its sides raises."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        "TS = ()",
        "TS = ( )",
        'TS = ( ("a") OR () )',
        'TS = ( () OR ("a") )',
        'TS = ( ("a") OR ( ( ) ) )',
        "()",
    ],
)
def test_empty_group_raises(text):
    """An empty group `()` raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize("text", ["", " ", "\n", " \n\t ", "TS =", "TS = ", "ts=\n"])
def test_empty_query_raises(text):
    """A query with nothing in it, with or without the field tag, raises."""
    with pytest.raises(QueryError):
        parse_terms(text)


@pytest.mark.parametrize(
    "text",
    [
        'TS = ("")',
        'TS = (" ")',
        'TS = ("   ")',
        'TS = ("\t")',
        'TS = ( ("a") OR ("") )',
        'TS = ( ("") OR ("a") )',
        'TS = ( ("a") OR ("  ") OR ("b") )',
    ],
)
def test_empty_term_raises(text):
    """A term that is empty after stripping raises `QueryError`."""
    with pytest.raises(QueryError):
        parse_terms(text)


def test_terms_are_stripped_and_lower_cased():
    """Surrounding whitespace is removed and every term is lower-cased."""
    text = 'TS = ( ("  Machine Learning ") OR ("IoT") OR ("3D Print*") OR ("\tK-Means\n") )'
    assert parse_terms(text) == ["machine learning", "iot", "3d print*", "k-means"]


def test_term_characters_are_kept_as_written():
    """Hyphens, dots, digits and the wildcard inside a term are not touched."""
    text = 'TS = ( ("industry 4.0") OR ("semi-supervised learning") OR ("word2vec") OR ("5g") )'
    assert parse_terms(text) == ["industry 4.0", "semi-supervised learning", "word2vec", "5g"]


def test_order_of_first_writing_is_kept():
    """Terms come back in the order written, not sorted."""
    text = 'TS = ( ("zebra") OR ("apple") OR ("mango") OR ("3d print*") OR ("banana") )'
    assert parse_terms(text) == ["zebra", "apple", "mango", "3d print*", "banana"]


def test_repeats_are_dropped_and_first_position_is_kept():
    """A repeat is dropped; the term keeps the place where it was first written."""
    text = 'TS = ( ("b") OR ("a") OR ("b") OR ("c") OR ("a") OR ("b") )'
    assert parse_terms(text) == ["b", "a", "c"]


def test_repeats_are_compared_after_stripping_and_lower_casing():
    """Two spellings that differ only by case or outer whitespace are one term."""
    text = 'TS = ( ("Big Data") OR ("iot") OR (" big data ") OR ("IoT") OR ("BIG DATA") OR ("x") )'
    assert parse_terms(text) == ["big data", "iot", "x"]


def test_a_term_and_its_truncated_form_are_two_terms():
    """`neural network` and `neural net*` differ as strings, so both are kept."""
    text = 'TS = ( ("neural net*") OR ("neural network") OR ("neural net*") )'
    assert parse_terms(text) == ["neural net*", "neural network"]


def test_repeats_across_nested_groups_are_dropped():
    """Repeats are dropped wherever they sit in the nesting."""
    text = 'TS = ( ("a" OR "b") OR ( ("B") OR ("c") ) OR "a" )'
    assert parse_terms(text) == ["a", "b", "c"]


def test_newlines_between_terms_are_accepted():
    """The layout of the real files, one block over several lines, parses."""
    text = 'TS = (\n("altcoin") OR ("bitcoin") OR\n("blockchain*") OR ("cryptocurrenc*")\n)'
    assert parse_terms(text) == ["altcoin", "bitcoin", "blockchain*", "cryptocurrenc*"]


def test_any_whitespace_is_accepted():
    """Tabs, carriage returns, blank lines and no space at all are all whitespace."""
    text = '\n\tTS\t=\r\n(\n\n("a")\tOR\r\n("b")OR("c")\n\n)\n\n'
    assert parse_terms(text) == ["a", "b", "c"]


def test_or_is_accepted_in_any_case():
    """`OR`, `or`, `Or` and `oR` all join terms."""
    text = 'TS = ( ("a") OR ("b") or ("c") Or ("d") oR ("e") )'
    assert parse_terms(text) == ["a", "b", "c", "d", "e"]


def test_nesting_of_any_depth_is_accepted():
    """Groups may be nested to any depth; the terms come out in reading order."""
    text = 'TS = ( ("a") OR ( ("b") OR ( ("c") OR ((("d"))) ) ) OR (("e") OR "f") )'
    assert parse_terms(text) == ["a", "b", "c", "d", "e", "f"]


def test_terms_need_no_parentheses_of_their_own():
    """A quoted term is an operand with or without a group around it."""
    assert parse_terms('"a" OR "b"') == ["a", "b"]
    assert parse_terms('TS = "a" OR ("b" OR "c")') == ["a", "b", "c"]


def test_one_term_is_a_disjunction():
    """A query of one term gives a list of one term."""
    assert parse_terms('TS = ( ("Bitcoin") )') == ["bitcoin"]


def test_operator_words_and_parentheses_inside_quotes_are_term_text():
    """Only text outside quotes is syntax; inside quotes it belongs to the term."""
    text = 'TS = ( ("search and rescue") OR ("near field") OR ("or") OR ("a (b) c") )'
    assert parse_terms(text) == ["search and rescue", "near field", "or", "a (b) c"]


def test_operator_letters_inside_a_word_are_not_operators():
    """`random`, `vector` and `nearest` hold `and`, `or` and `near` and still parse."""
    text = 'TS = ( ("random forest") OR ("vector machine") OR ("nearest neighbour algorithm") )'
    assert parse_terms(text) == ["random forest", "vector machine", "nearest neighbour algorithm"]
