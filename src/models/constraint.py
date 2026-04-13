from dataclasses import dataclass, field
import datetime as dt
from typing import Literal
from enum import Enum

class ConstraintRelation(str, Enum):
    FS = "Finish-to-Start"
    FF = "Finish-to-Finish"
    SS = "Start-to-Start"
    SF = "Start-to-Finish"

@dataclass
class Constraint:
    predecessor_id: str # id of the other task or phase in the constraint relationship
    predecessor_kind: Literal["task", "phase"] # whether the predecessor is a task or a phase
    relation_type: ConstraintRelation # type of constraint relationship (FS, FF, SS, SF)
    lag: dt.timedelta = field(default_factory=lambda: dt.timedelta(0)) # optional lag time between the two tasks, default is 0 (no lag)


def earliest_start_from_constraint(
        *,
        predecessor_start: dt.datetime,
        predecessor_end: dt.datetime,
        successor_duration: dt.timedelta,
        relation: ConstraintRelation,
        lag: dt.timedelta = dt.timedelta(0)
) -> dt.datetime:
    if relation == ConstraintRelation.FS:
        return predecessor_end + lag
    elif relation == ConstraintRelation.SS:
        return predecessor_start + lag
    elif relation == ConstraintRelation.FF:
        return predecessor_end + lag - successor_duration
    elif relation == ConstraintRelation.SF:
        return predecessor_start + lag - successor_duration
    else:
        raise ValueError(f"Unsupported constraint relation: {relation}")
    