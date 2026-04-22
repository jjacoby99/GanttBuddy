from dataclasses import dataclass, field
import datetime as dt
from typing import Any, Literal
from enum import Enum


class ConstraintRelation(str, Enum):
    FS = "FS"
    FF = "FF"
    SS = "SS"
    SF = "SF"

    @property
    def label(self) -> str:
        return {
            ConstraintRelation.FS: "Finish-to-Start",
            ConstraintRelation.FF: "Finish-to-Finish",
            ConstraintRelation.SS: "Start-to-Start",
            ConstraintRelation.SF: "Start-to-Finish",
        }[self]


@dataclass
class Constraint:
    predecessor_id: str
    predecessor_kind: Literal["task", "phase"]
    relation_type: ConstraintRelation = ConstraintRelation.FS
    lag: dt.timedelta = field(default_factory=dt.timedelta)

    def to_dict(self) -> dict[str, Any]:
        return {
            "predecessor_id": self.predecessor_id,
            "predecessor_kind": self.predecessor_kind,
            "relation_type": self.relation_type.value,
            "lag_seconds": int(self.lag.total_seconds()),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Constraint":
        relation_value = data.get("relation_type", ConstraintRelation.FS.value)
        lag_value = data.get("lag")
        if lag_value is None:
            lag_seconds = data.get("lag_seconds", 0)
            lag = dt.timedelta(seconds=float(lag_seconds))
        elif isinstance(lag_value, dt.timedelta):
            lag = lag_value
        else:
            lag = dt.timedelta(seconds=float(lag_value))

        return Constraint(
            predecessor_id=data["predecessor_id"],
            predecessor_kind=data.get("predecessor_kind", "task"),
            relation_type=ConstraintRelation(relation_value),
            lag=lag,
        )


def earliest_start_from_constraint(
    *,
    predecessor_start: dt.datetime,
    predecessor_end: dt.datetime,
    successor_duration: dt.timedelta,
    relation: ConstraintRelation,
    lag: dt.timedelta = dt.timedelta(0),
) -> dt.datetime:
    if relation == ConstraintRelation.FS:
        return predecessor_end + lag
    if relation == ConstraintRelation.SS:
        return predecessor_start + lag
    if relation == ConstraintRelation.FF:
        return predecessor_end + lag - successor_duration
    if relation == ConstraintRelation.SF:
        return predecessor_start + lag - successor_duration
    raise ValueError(f"Unsupported constraint relation: {relation}")

def earliest_start_from_constraints(
    *,
    successor_duration: dt.timedelta,
    constraints: list[Constraint],
) -> dt.datetime:
    if not constraints:
        return None

    earliest_starts = [
        earliest_start_from_constraint(
            predecessor_start=constraint.predecessor_start,
            predecessor_end=constraint.predecessor_end,
            successor_duration=successor_duration,
            relation=constraint.relation_type,
            lag=constraint.lag,
        )
        for constraint in constraints
    ]
    return max(earliest_starts)
    
