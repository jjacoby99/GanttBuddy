from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.constraint import Constraint, ConstraintRelation, earliest_start_from_constraint
from ui.utils.constraints import constraints_from_editor_df


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        (ConstraintRelation.FS, dt.datetime(2026, 2, 1, 11, 0)),
        (ConstraintRelation.SS, dt.datetime(2026, 2, 1, 7, 0)),
        (ConstraintRelation.FF, dt.datetime(2026, 2, 1, 9, 0)),
        (ConstraintRelation.SF, dt.datetime(2026, 2, 1, 5, 0)),
    ],
)
def test_earliest_start_from_constraint_supports_all_relations(
    relation: ConstraintRelation,
    expected: dt.datetime,
) -> None:
    predecessor_start = dt.datetime(2026, 2, 1, 7, 0)
    predecessor_end = dt.datetime(2026, 2, 1, 11, 0)
    successor_duration = dt.timedelta(hours=2)

    resolved = earliest_start_from_constraint(
        predecessor_start=predecessor_start,
        predecessor_end=predecessor_end,
        successor_duration=successor_duration,
        relation=relation,
    )

    assert resolved == expected


def test_earliest_start_from_constraint_applies_positive_and_negative_lag() -> None:
    predecessor_start = dt.datetime(2026, 2, 1, 7, 0)
    predecessor_end = dt.datetime(2026, 2, 1, 11, 0)
    successor_duration = dt.timedelta(hours=2)

    delayed = earliest_start_from_constraint(
        predecessor_start=predecessor_start,
        predecessor_end=predecessor_end,
        successor_duration=successor_duration,
        relation=ConstraintRelation.FS,
        lag=dt.timedelta(hours=3),
    )
    overlap = earliest_start_from_constraint(
        predecessor_start=predecessor_start,
        predecessor_end=predecessor_end,
        successor_duration=successor_duration,
        relation=ConstraintRelation.SS,
        lag=dt.timedelta(hours=-1),
    )

    assert delayed == dt.datetime(2026, 2, 1, 14, 0)
    assert overlap == dt.datetime(2026, 2, 1, 6, 0)


def test_constraint_editor_limits_ui_authored_relations_to_fs_and_ss() -> None:
    editor_df = pd.DataFrame(
        [
            {"relation_type": "FS", "predecessor": "Task A", "lag_hours": 0.0},
            {"relation_type": "FF", "predecessor": "Task B", "lag_hours": 0.0},
        ]
    )

    constraints, messages = constraints_from_editor_df(
        editor_df,
        predecessor_kind="task",
        id_by_label={"Task A": "task-a", "Task B": "task-b"},
    )

    assert constraints == [
        Constraint(
            predecessor_id="task-a",
            predecessor_kind="task",
            relation_type=ConstraintRelation.FS,
            lag=dt.timedelta(0),
        )
    ]
    assert any("FS" in message and "SS" in message for message in messages)
