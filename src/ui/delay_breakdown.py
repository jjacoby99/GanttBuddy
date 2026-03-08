from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

import pandas as pd
import plotly.express as px
import streamlit as st


def _delay_type_label(x: Any) -> str:
    # Works for Enum, string, etc.
    if x is None:
        return "Unknown"
    name = getattr(x, "name", None)
    if name:
        return name.replace("_", " ").title()
    s = str(x)
    return s.replace("_", " ").title()


def _safe_minutes(row: dict) -> float:
    dm = row.get("duration_minutes")
    if dm is None or dm == "":
        return 0.0
    try:
        return max(0.0, float(dm))
    except Exception:
        return 0.0


#@st.cache_data(show_spinner=False)
def _build_delay_breakdown_df(items_dump: list[dict]) -> pd.DataFrame:
    if not items_dump:
        return pd.DataFrame(columns=["delay_type", "delay_type_label", "minutes", "hours"])

    df = pd.DataFrame(items_dump)

    if "delay_type" not in df.columns:
        df["delay_type"] = None

    df["delay_type_label"] = df["delay_type"].apply(_delay_type_label)

    # Compute minutes robustly
    rows = df.to_dict(orient="records")
    df["minutes"] = [_safe_minutes(r) for r in rows]
    df["hours"] = df["minutes"] / 60.0

    return df


def build_delay_count_bar_chart(group_count, color_map: dict):
    fig_count = px.bar(
            group_count,
            x="count",
            y="delay_type_label",
            orientation="h",
            text="count",
            color="delay_type_label",
            color_discrete_map=color_map,
            title="Count by delay type",
        )
    fig_count.update_traces(textposition="outside")
    fig_count.update_layout(
        template="plotly_white",
        yaxis_title="",
        xaxis_title="Count",
        showlegend=False,  # labels already on the axis
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig_count

def build_delay_hours_bar_chart(group_hours, color_map: dict):
    fig_hours = px.bar(
        group_hours,
        x="hours",
        y="delay_type_label",
        orientation="h",
        text="hours",
        color="delay_type_label",
        color_discrete_map=color_map,
        title="Total hours by delay type",
    )
    fig_hours.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_hours.update_layout(
        template="plotly_white",
        yaxis_title="",
        xaxis_title="Hours",
        showlegend=False,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig_hours

def build_delay_count_pie_chart(group_count):
    fig_count = px.pie(
        group_count,
        names="delay_type_label",
        values="count",
        hole=0.55,
        title="Count share by type",
    )
    fig_count.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
    return fig_count

def build_delay_hours_pie_chart(group_hours):
    fig_hours = px.pie(
        group_hours,
        names="delay_type_label",
        values="hours",
        hole=0.55,
        title="Hours share by type",
    )
    fig_hours.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=50, b=10))
    return fig_hours

def render_delay_breakdown_charts(
    delays: Iterable[Any],
    *,
    title: str = "Delay breakdown",
) -> None:
    delays = list(delays)
    if not delays:
        st.info("No delays found for this project.")
        return

    # Dump pydantic models (Delay or DelayEditorRow) to plain dict
    items_dump: list[dict] = []
    for d in delays:
        if hasattr(d, "model_dump"):
            items_dump.append(d.model_dump())
        elif hasattr(d, "dict"):
            items_dump.append(d.dict())
        else:
            # Fallback: best-effort
            items_dump.append(getattr(d, "__dict__", {}))

    df = _build_delay_breakdown_df(items_dump)
    if df.empty:
        st.info("No delay data to chart.")
        return

    with st.container(horizontal=True):
        st.subheader(title)

        st.space("stretch")

        with st.popover(":material/settings: Display Preferences"):
            c1, c2 = st.columns(2)
            # Filters
            all_types = sorted(df["delay_type_label"].unique().tolist())
            selected = c1.multiselect(
                "Filter delay types", 
                options=all_types, 
                default=all_types
            )

            # Chart style toggle
            chart_style = c2.radio(
                "Chart style",
                options=["Bars", "Donut"],
                horizontal=True,
                index=0,
            )

    st.divider()

    fdf = df[df["delay_type_label"].isin(selected)].copy()
    if fdf.empty:
        st.info("No delays match the selected filters.")
        return

    # Summary metrics
    total_count = int(len(fdf))
    total_hours = float(fdf["hours"].sum())
    avg_mins = float(fdf["minutes"].mean()) if total_count else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Delays Tracked", f"{total_count}")
    c2.metric("Total delay (hours)", f"{total_hours:.2f}")
    c3.metric("Avg duration (mins)", f"{avg_mins:.1f}")

    st.divider() 

    # Group
    g = (
        fdf.groupby("delay_type_label", as_index=False)
        .agg(count=("delay_type_label", "size"), hours=("hours", "sum"))
    )

    left, right = st.columns(2)

    if chart_style.startswith("Bars"):
        types = sorted(g["delay_type_label"].unique().tolist())
        palette = px.colors.qualitative.Safe  # good default palette
        color_map = {t: palette[i % len(palette)] for i, t in enumerate(types)}


        # Count chart
        g_count = g.sort_values("count", ascending=True)
        fig_count = build_delay_count_bar_chart(group_count=g_count, color_map=color_map)

        # Hours chart
        g_hours = g.sort_values("hours", ascending=True)
        fig_hours = build_delay_hours_bar_chart(group_hours=g_hours, color_map=color_map)

        with left:
            st.plotly_chart(fig_count, width="stretch")
        with right:
            st.plotly_chart(fig_hours, width="stretch")

    else:
        # Donut charts (still useful as an optional view)
        g_count = g.sort_values("count", ascending=False)
        fig_count = build_delay_count_pie_chart(group_count=g_count)

        g_hours = g.sort_values("hours", ascending=False)
        fig_hours = build_delay_hours_pie_chart(group_hours=g_hours)

        with left:
            st.plotly_chart(fig_count, width="stretch")
        with right:
            st.plotly_chart(fig_hours, width="stretch")

    with st.expander("Show breakdown table"):
        st.dataframe(
            g.sort_values("hours", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "delay_type_label": st.column_config.TextColumn(
                    label="Delay Type"
                ),
                "count": st.column_config.TextColumn(
                    label="Count"
                ),
                "hours": st.column_config.TextColumn(
                    label="Delay Tracked (hours)"
                )
            }
        )