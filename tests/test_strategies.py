import pytest

from atlasweave.models import AtlasWeaveError, Dataset
from atlasweave.strategies import StrategyConfig, profile, suggest


def test_normalization_is_explicit_and_preserves_zeros():
    left = Dataset("left", ("cust_id",), ((" 001 ",), ("ABC",), (None,), ("  ",)), True)
    right = Dataset("right", ("Customer ID",), (("001",), ("abc",), (None,)), True)
    *_, exact = suggest(left, right, StrategyConfig())
    assert exact[0]["evidence"]["shared_distinct"] == 0
    config = StrategyConfig(trim=True, casefold=True)
    *_, normalized = suggest(left, right, config)
    assert normalized[0]["evidence"]["shared_distinct"] == 2
    assert normalized[0]["evidence"]["left_nulls"] == 2
    assert normalized[0]["evidence"]["inner_join_rows"] == 2
    assert config.normalize("001") != config.normalize("1")


def test_empty_columns_are_not_unique_join_keys():
    data = Dataset("empty", ("id",), ((None,), (None,)), True)
    profiles, _ = profile(data, StrategyConfig())
    assert profiles[0].kind == "empty"
    *_, candidates = suggest(data, data, StrategyConfig(min_score=0))
    assert candidates[0]["scores"]["uniqueness"] == 0
    assert candidates[0]["evidence"]["inner_join_rows"] == 0


@pytest.mark.parametrize(
    "config",
    [
        {"weights": {"name": 1}},
        {"weights": dict.fromkeys(["name", "type", "overlap", "uniqueness"], 0)},
        {"weights": {"name": float("inf"), "type": 1, "overlap": 1, "uniqueness": 1}},
        {"trim": "false"},
        {"min_score": -1},
        {"min_score": float("nan")},
        {"aliases": {"a": "b", "b": "a"}},
        {"aliases": {"ID": "x", "id": "y"}},
        {"aliases": {"": "id"}},
    ],
)
def test_invalid_config(config):
    with pytest.raises(AtlasWeaveError):
        StrategyConfig(**config)


def test_deterministic_ranking_and_mixed_profile():
    data = Dataset("mixed", ("id", "other"), (("1", "a"), ("001", "b")), True)
    first = suggest(data, data, StrategyConfig())
    assert first == suggest(data, data, StrategyConfig())
    assert first[0][0]["kind"] == "mixed"
    assert first[0][0]["distinct_count"] == 2
