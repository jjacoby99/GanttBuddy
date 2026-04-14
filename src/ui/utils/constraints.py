from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Iterable

import pandas as pd
import streamlit as st

from models.constraint import Constraint, ConstraintRelation


CONSTRAINT_RELATION_OPTIONS = [relation.value for relation in ConstraintRelation]


def build_constraint_target_labels(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    pairs = [(str(item_id), name.strip() or str(item_id)) for item_id, name in items]
    label_counts = Counter(name for _, name in pairs)

    return {
        item_id: f"{name} ({item_id[:8]})" if label_counts[name] > 1 else name
        for item_id, name in pairs
    }


def constraints_to_editor_df(
    constraints: list[Constraint],
    *,
    predecessor_kind: str,
    labels_by_id: dict[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for constraint in constraints:
        if constraint.predecessor_kind != predecessor_kind:
            continue
        rows.append(
            {
                "relation_type": constraint.relation_type.value,
                "predecessor": labels_by_id.get(constraint.predecessor_id, constraint.predecessor_id),
                "lag_hours": constraint.lag.total_seconds() / 3600,
            }
        )

    if not rows:
        return pd.DataFrame(
            {
                "relation_type": pd.Series(dtype="object"),
                "predecessor": pd.Series(dtype="object"),
                "lag_hours": pd.Series(dtype="float64"),
            }
        )

    return pd.DataFrame(rows)


def constraints_from_editor_df(
    df: pd.DataFrame,
    *,
    predecessor_kind: str,
    id_by_label: dict[str, str],
) -> list[Constraint]:
    constraints: list[Constraint] = []
    seen: set[tuple[str, str, str, int]] = set()

    for record in df.to_dict(orient="records"):
        predecessor_label = record.get("predecessor")
        relation_value = record.get("relation_type") or ConstraintRelation.FS.value
        lag_hours = record.get("lag_hours")

        if predecessor_label is None or pd.isna(predecessor_label):
            continue

        predecessor_id = id_by_label.get(str(predecessor_label))
        if predecessor_id is None:
            continue

        lag_hours_value = 0.0 if lag_hours is None or pd.isna(lag_hours) else float(lag_hours)
        lag_seconds = int(dt.timedelta(hours=lag_hours_value).total_seconds())
        dedupe_key = (predecessor_id, predecessor_kind, str(relation_value), lag_seconds)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        constraints.append(
            Constraint(
                predecessor_id=predecessor_id,
                predecessor_kind=predecessor_kind,
                relation_type=ConstraintRelation(str(relation_value)),
                lag=dt.timedelta(seconds=lag_seconds),
            )
        )

    return constraints


def render_constraints_editor(
    *,
    key: str,
    title: str,
    help_text: str,
    constraints: list[Constraint],
    predecessor_kind: str,
    labels_by_id: dict[str, str],
) -> list[Constraint]:
    if not labels_by_id:
        st.caption(help_text)
        st.info(f"No available {predecessor_kind} predecessors yet.")
        return []

    editor_df = constraints_to_editor_df(
        constraints,
        predecessor_kind=predecessor_kind,
        labels_by_id=labels_by_id,
    )
    id_by_label = {label: item_id for item_id, label in labels_by_id.items()}

    edited_df = st.data_editor(
        editor_df,
        key=key,
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        column_order=["relation_type", "predecessor", "lag_hours"],
        column_config={
            "relation_type": st.column_config.SelectboxColumn(
                label="Constraint Type",
                options=CONSTRAINT_RELATION_OPTIONS,
                help="How this item depends on its predecessor.",
                required=True,
            ),
            "predecessor": st.column_config.SelectboxColumn(
                label="Predecessor",
                options=list(id_by_label.keys()),
                help=help_text,
                required=True,
            ),
            "lag_hours": st.column_config.NumberColumn(
                label="Lag (hrs)",
                help="Positive values delay the successor; negative values overlap it.",
                default=0.0,
                step=0.25,
                format="%.2f",
            ),
        },
    )

    st.caption(title)
    return constraints_from_editor_df(
        edited_df,
        predecessor_kind=predecessor_kind,
        id_by_label=id_by_label,
    )
