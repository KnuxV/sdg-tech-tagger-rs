"""The port returns the oracle's firings on the fixture sets, in both modes.

Contract: ``docs/contract.md``, "What each system returns" and "What counts
as agreeing". The expected rows are those of ``r/detect_text2sdg.R``
(compatible mode) and ``r/detect_text2sdg_corrected.R`` (corrected mode),
run with the four systems by ``tests/fixtures/make_fixtures.py``. The gate
is the set of (``UT``, ``system``, ``sdg``, ``query_id``) (D011); the
oracle's ``features`` are kept in the fixtures and not asserted (D028).
"""

import polars as pl
import pytest

from tests.unit.oracle_fixtures import (
    MODES,
    SET_NAMES,
    SYSTEMS,
    assert_same_firings,
    load_set,
    run_detect,
)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("set_name", SET_NAMES)
def test_the_four_systems_give_the_oracle_firings(set_name, mode):
    """With the four systems, the firings are exactly the oracle's."""
    fixture = load_set(set_name)
    got = run_detect(set_name, mode, SYSTEMS)
    assert_same_firings(got, fixture.rows[mode], fixture.texts())


@pytest.mark.parametrize("system", SYSTEMS)
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("set_name", SET_NAMES)
def test_one_system_gives_its_own_oracle_firings(set_name, mode, system):
    """With one system, the firings are the oracle's rows of that system."""
    fixture = load_set(set_name)
    expected = fixture.rows[mode].filter(pl.col("system") == system)
    got = run_detect(set_name, mode, (system,))
    assert set(got["system"].unique()) <= {system}
    assert_same_firings(got, expected, fixture.texts())


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("set_name", SET_NAMES)
def test_every_identifier_returned_is_an_input_identifier(set_name, mode):
    """A row names a document of the input, by its identifier as given."""
    fixture = load_set(set_name)
    got = run_detect(set_name, mode, SYSTEMS)
    unknown = set(got["UT"]) - set(fixture.sentences["UT"])
    assert not unknown, f"identifiers not in the input: {sorted(unknown)[:5]}"
