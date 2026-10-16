"""Explainable, deterministic ranking. Scores are not probabilities."""

import math
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Protocol

from atlasweave.models import AtlasWeaveError, Dataset


def name_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


@dataclass(frozen=True)
class StrategyConfig:
    aliases: dict[str, str] = field(default_factory=lambda: {"custid": "customerid"})
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "name": 0.4,
            "type": 0.1,
            "overlap": 0.4,
            "uniqueness": 0.1,
        }
    )
    trim: bool = False
    casefold: bool = False
    min_score: float = 0.55

    def __post_init__(self):
        if not isinstance(self.aliases, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and name_key(k) and name_key(v)
            for k, v in self.aliases.items()
        ):
            raise AtlasWeaveError("Aliases must map nonempty column names to canonical names.")
        normalized = {name_key(k): name_key(v) for k, v in self.aliases.items()}
        if len(normalized) != len(self.aliases):
            raise AtlasWeaveError("Alias names collide after normalization.")
        if any(v in normalized and normalized[v] != v for v in normalized.values()):
            raise AtlasWeaveError("Aliases must point directly to canonical names, without chains.")
        object.__setattr__(self, "aliases", normalized)
        if not isinstance(self.weights, dict) or set(self.weights) != {
            "name",
            "type",
            "overlap",
            "uniqueness",
        }:
            raise AtlasWeaveError("Weights must specify name, type, overlap and uniqueness.")
        if (
            any(
                type(v) not in (int, float) or not math.isfinite(v) or v < 0
                for v in self.weights.values()
            )
            or sum(self.weights.values()) <= 0
            or not math.isfinite(sum(self.weights.values()))
        ):
            raise AtlasWeaveError("Weights must be finite, nonnegative, with a positive total.")
        if type(self.trim) is not bool or type(self.casefold) is not bool:
            raise AtlasWeaveError("trim and casefold must be booleans.")
        if type(self.min_score) not in (int, float) or not 0 <= self.min_score <= 1:
            raise AtlasWeaveError("min_score must be between 0 and 1.")

    def normalize(self, value: str | None) -> str | None:
        if value is None:
            return None
        if self.trim:
            value = value.strip()
        if self.casefold:
            value = value.casefold()
        return value or None


@dataclass(frozen=True)
class ColumnProfile:
    id: str
    name: str
    kind: str
    row_count: int
    null_count: int
    distinct_count: int
    duplicate_count: int


def infer_kind(values: Counter) -> str:
    if not values:
        return "empty"
    kinds = set()
    for value in values:
        if re.fullmatch(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
            kinds.add("number")
        elif value in ("true", "false"):
            kinds.add("boolean")
        else:
            kinds.add("text")
    return kinds.pop() if len(kinds) == 1 else "mixed"


def profile(dataset: Dataset, config: StrategyConfig):
    profiles, counts = [], []
    for index, name in enumerate(dataset.fields):
        values = [config.normalize(v) for v in dataset.column(index)]
        counter = Counter(v for v in values if v is not None)
        non_null = sum(counter.values())
        profiles.append(
            ColumnProfile(
                f"f{index + 1}",
                name,
                infer_kind(counter),
                len(values),
                len(values) - non_null,
                len(counter),
                non_null - len(counter),
            )
        )
        counts.append(counter)
    return profiles, counts


class MatchStrategy(Protocol):
    """A strategy scores one profiled field pair from zero to one."""

    def __call__(
        self,
        left: ColumnProfile,
        right: ColumnProfile,
        left_values: Counter,
        right_values: Counter,
        config: StrategyConfig,
    ) -> float: ...


def name_score(left, right, _lv, _rv, config):
    a, b = name_key(left.name), name_key(right.name)
    a, b = config.aliases.get(a, a), config.aliases.get(b, b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def type_score(left, right, _lv, _rv, _config):
    return float(left.kind == right.kind and left.kind not in ("empty", "mixed"))


def overlap_score(_left, _right, lv, rv, _config):
    return len(lv.keys() & rv.keys()) / len(lv) if lv else 0.0


def uniqueness_score(_left, _right, _lv, rv, _config):
    return len(rv) / sum(rv.values()) if rv else 0.0


STRATEGIES: dict[str, MatchStrategy] = {
    "name": name_score,
    "type": type_score,
    "overlap": overlap_score,
    "uniqueness": uniqueness_score,
}


def join_evidence(left: ColumnProfile, right: ColumnProfile, lv: Counter, rv: Counter):
    shared = lv.keys() & rv.keys()
    unmatched_left = sum(count for value, count in lv.items() if value not in rv) + left.null_count
    unmatched_right = (
        sum(count for value, count in rv.items() if value not in lv) + right.null_count
    )
    inner_rows = sum(lv[value] * rv[value] for value in shared)
    cardinality = (
        (
            ("many" if left.duplicate_count else "one")
            + "-to-"
            + ("many" if right.duplicate_count else "one")
        )
        if shared
        else "no-overlap"
    )
    return {
        "shared_distinct": len(shared),
        "unmatched_left_rows": unmatched_left,
        "unmatched_right_rows": unmatched_right,
        "inner_join_rows": inner_rows,
        "left_join_rows": inner_rows + unmatched_left,
        "cardinality": cardinality,
        "left_nulls": left.null_count,
        "right_nulls": right.null_count,
        "left_duplicates": left.duplicate_count,
        "right_duplicates": right.duplicate_count,
    }


def suggest(left: Dataset, right: Dataset, config: StrategyConfig):
    lp, lc = profile(left, config)
    rp, rc = profile(right, config)
    candidates = []
    for i, a in enumerate(lp):
        for j, b in enumerate(rp):
            scores = {
                name: strategy(a, b, lc[i], rc[j], config) for name, strategy in STRATEGIES.items()
            }
            score = sum(scores[k] * w for k, w in config.weights.items()) / sum(
                config.weights.values()
            )
            if score < config.min_score or not (scores["name"] or scores["overlap"]):
                continue
            candidates.append(
                {
                    "id": f"left.{a.id}--right.{b.id}",
                    "left_field": a.id,
                    "right_field": b.id,
                    "score": round(score, 6),
                    "scores": {key: round(value, 6) for key, value in scores.items()},
                    "evidence": join_evidence(a, b, lc[i], rc[j]),
                    "scope": "full" if left.complete and right.complete else "sample",
                    "status": "pending",
                    "rules": None,
                }
            )
    candidates.sort(key=lambda c: (-c["score"], c["id"]))
    return [asdict(p) for p in lp], [asdict(p) for p in rp], candidates
