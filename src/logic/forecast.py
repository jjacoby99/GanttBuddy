from __future__ import annotations
from models.phase import Phase
from models.task import Task
from models.project import Project
from models.project_settings import ProjectSettings
from models.session import SessionModel
from logic.duration import DurationCalculator
import pandas as pd


import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# -----------------------------
# Utilities
# -----------------------------

DTFMT = "%Y-%m-%d %H:%M"

def _infer_as_of_from_actuals(df: pd.DataFrame) -> pd.Timestamp:
    """Use the last actual timestamp as the 'as_of'.
    Prefer latest actual_finish; if none, fall back to latest actual_start.
    If there are truly no actuals, fall back to latest planned_start."""
    candidates = []
    if "actual_finish" in df: candidates.append(df["actual_finish"])
    if "actual_start" in df:  candidates.append(df["actual_start"])
    series = pd.concat([c for c in candidates if c is not None], axis=0)
    latest = pd.to_datetime(series.max())
    if pd.isna(latest):
        latest = pd.to_datetime(df["planned_start"].max())
    return latest

def _to_dt(x):
    if pd.isna(x) or x is None or x == "":
        return pd.NaT
    return pd.to_datetime(x)


def _ensure_hours(row) -> float:
    """Return planned_hours with sensible fallback to planned duration.
    If planned_start/finish are NaT or equal, fall back to 0.
    """
    if not pd.isna(row.get("planned_hours", np.nan)):
        return float(row["planned_hours"]) or 0.0
    ps, pf = row["planned_start"], row["planned_finish"]
    if pd.isna(ps) or pd.isna(pf):
        return 0.0
    dur_h = max((pf - ps).total_seconds() / 3600.0, 0.0)
    return dur_h


def _planned_rate(row) -> float:
    ps, pf = row["planned_start"], row["planned_finish"]
    hours = _ensure_hours(row)
    if pd.isna(ps) or pd.isna(pf):
        return 0.0
    dur_h = (pf - ps).total_seconds() / 3600.0
    if dur_h <= 0:
        return 0.0
    return hours / dur_h


# -----------------------------
# Forecasting Engine
# -----------------------------

@dataclass
class ForecastResult:
    planned_curve: pd.Series  # hourly increments cum-summed
    actual_forecast_curve: pd.Series
    forecasted_tasks: pd.DataFrame  # with forecast_start/forecast_finish/completed_hours/remaining_hours
    planned_end: Optional[pd.Timestamp]
    forecast_end: Optional[pd.Timestamp]
    completed_hours_to_date: float
    total_planned_hours: float
    as_of: pd.Timestamp


def _spread_equal_over_time(start: pd.Timestamp, end: pd.Timestamp, total_hours: float, freq: str = "H") -> pd.Series:
    """Return a Series of increments, equally spread across [start, end) at given freq.
    If start==end or there are zero steps, place the entire amount at `end`.
    """
    if pd.isna(start) or pd.isna(end) or total_hours <= 0:
        return pd.Series(dtype=float)
    if end <= start:
        # place at end as a single spike
        return pd.Series([total_hours], index=[end])
    times = pd.date_range(start=start, end=end, inclusive="left", freq=freq)
    if len(times) == 0:
        return pd.Series([total_hours], index=[end])
    increment = total_hours / len(times)
    return pd.Series(np.full(len(times), increment, dtype=float), index=times)


def _build_cumulative(tasks: pd.DataFrame, start_col: str, end_col: str, hours_col: str, freq: str = "H") -> pd.Series:
    """Create a cumulative hours curve by uniformly distributing a task's hours between its start and end.
    Returns a Series indexed by timestamp with cumulative hours values.
    """
    per_step = pd.Series(dtype=float)
    for _, r in tasks.iterrows():
        inc = _spread_equal_over_time(r[start_col], r[end_col], float(r[hours_col] or 0.0), freq=freq)
        if not inc.empty:
            per_step = per_step.add(inc, fill_value=0.0)
    if per_step.empty:
        return per_step
    return per_step.sort_index().cumsum()


def forecast(tasks: pd.DataFrame,
            as_of: Optional[pd.Timestamp] = None,
            productivity: float = 1.0,
            freq: str = "H") -> ForecastResult:
    df = tasks.copy()
    for col in ["planned_start", "planned_finish", "actual_start", "actual_finish"]:
        df[col] = df[col].apply(_to_dt)

    # If no as_of provided, infer it from actuals
    if as_of is None or pd.isna(as_of):
        as_of = _infer_as_of_from_actuals(df)

    df["planned_hours"] = df.apply(_ensure_hours, axis=1)
    planned_curve = _build_cumulative(df, "planned_start", "planned_finish", "planned_hours", freq=freq)

    completed_hours, remaining_hours, fc_start, fc_finish = [], [], [], []
    for _, r in df.iterrows():
        plan_rate = _planned_rate(r)
        ph = float(r["planned_hours"]) or 0.0
        a_s, a_f = r["actual_start"], r["actual_finish"]

        # Completed to as_of
        comp = 0.0
        if not pd.isna(a_s):
            stop = min(a_f, as_of) if not pd.isna(a_f) else as_of
            if not pd.isna(stop) and stop > a_s and plan_rate > 0:
                elapsed_h = (stop - a_s).total_seconds() / 3600.0
                comp = min(ph, elapsed_h * plan_rate)
            if not pd.isna(a_f) and a_f <= as_of and not pd.isna(r.get("actual_hours", np.nan)):
                comp = min(ph, float(r["actual_hours"]))
        comp = max(0.0, min(ph, comp))
        rem = max(0.0, ph - comp)

        # Forecast window for remaining work
        if rem <= 1e-9:
            start_fc = pd.NaT
            finish_fc = r["actual_finish"] if not pd.isna(r["actual_finish"]) else r["planned_finish"]
        else:
            rate = plan_rate * max(productivity, 1e-6)
            dur_rem_h = rem / rate if rate > 0 else 0.0
            if not pd.isna(a_s):
                start_fc = max(as_of, a_s)
            else:
                ps = r["planned_start"]
                start_fc = ps if (not pd.isna(ps) and ps > as_of) else as_of
            finish_fc = start_fc + timedelta(hours=dur_rem_h)

        completed_hours.append(comp)
        remaining_hours.append(rem)
        fc_start.append(start_fc); fc_finish.append(finish_fc)

    df["completed_hours_to_date"] = completed_hours
    df["remaining_hours"] = remaining_hours
    df["forecast_start"] = fc_start
    df["forecast_finish"] = fc_finish

    # Build actual + forecast curve
    per_step = pd.Series(dtype=float)
    for _, r in df.iterrows():
        if r["completed_hours_to_date"] > 0 and not pd.isna(r["actual_start"]):
            actual_stop = min(r.get("actual_finish", pd.NaT), as_of)
            if pd.isna(actual_stop) or actual_stop <= r["actual_start"]:
                actual_stop = as_of
            seg = _spread_equal_over_time(r["actual_start"], actual_stop,
                                          r["completed_hours_to_date"], freq=freq)
            per_step = per_step.add(seg, fill_value=0.0)
        if r["remaining_hours"] > 0 and not pd.isna(r["forecast_start"]) and not pd.isna(r["forecast_finish"]):
            seg = _spread_equal_over_time(r["forecast_start"], r["forecast_finish"],
                                          r["remaining_hours"], freq=freq)
            per_step = per_step.add(seg, fill_value=0.0)

    actual_forecast_curve = per_step.sort_index().cumsum() if not per_step.empty else per_step
    planned_end = df["planned_finish"].max() if not df.empty else pd.NaT
    ends = []
    if (df["forecast_finish"].notna()).any(): ends.append(df["forecast_finish"].max())
    if (df["actual_finish"].notna()).any():  ends.append(df["actual_finish"].max())
    forecast_end = max(ends) if ends else pd.NaT

    return ForecastResult(
        planned_curve=planned_curve,
        actual_forecast_curve=actual_forecast_curve,
        forecasted_tasks=df,
        planned_end=planned_end,
        forecast_end=forecast_end,
        completed_hours_to_date=float(np.sum(completed_hours)),
        total_planned_hours=float(df["planned_hours"].sum() if not df.empty else 0.0),
        as_of=as_of,
    )


# -----------------------------
# Plotting
# -----------------------------

def _to_plot_df(planned: pd.Series, af: pd.Series) -> pd.DataFrame:
    # Align on a common time axis
    df = pd.DataFrame({"planned": planned, "actual_forecast": af})
    df = df.sort_index().ffill().reset_index()
    df = df.rename(columns={"index": "date"})
    # Melt for plotly express
    long = df.melt(id_vars=["date"], value_vars=["planned", "actual_forecast"],
                   var_name="series", value_name="cumulative_hours")
    long["series"] = long["series"].map({"planned": "Planned", "actual_forecast": "Actual / Forecast"})
    return long

def build_forecast_df_v2(project: Project) -> pd.DataFrame:
    if not project.phases:
        raise ValueError(f"Provided project {project.name} has no phases.")
    
    if not project.has_task:
        raise ValueError(f"Provided project {project.name} has no tasks")
    
    pd.set_option("display.float_format", "{:.2f}".format)

    duration_calc = DurationCalculator(settings=project.settings)

    data = {
        "id": [],
        "name": [],
        "phase": [],
        "planned_start": [],
        "planned_finish": [],
        "planned_hours": [],
        "actual_start": [],
        "actual_finish": [],
        "actual_hours": []
    }
    for pid in project.phase_order:
        phase = project.phases[pid]
        for tid in phase.task_order:
            task = phase.tasks[tid]
            data["id"].append(task.uuid)
            data["name"].append(task.name)
            data["phase"].append(phase.name)
            data["planned_start"].append(task.start_date)
            data["planned_finish"].append(task.end_date)
            data["planned_hours"].append(duration_calc.duration(task.start_date, task.end_date))
            data["actual_start"].append(task.actual_start) # Can be None
            data["actual_finish"].append(task.actual_end) # Can be None
            
            actual_duration = None
            if task.actual_end and task.actual_start:
                actual_duration = duration_calc.duration(task.actual_start, task.actual_end)
            
            data["actual_hours"].append(actual_duration)
    return pd.DataFrame(data)

from PIL import Image

def make_forecast_figure(result: ForecastResult,
                         as_of: Optional[pd.Timestamp] = None,
                         logo_path: Optional[str] = "assets/bta_logo.png") -> go.Figure:
    ORANGE = "#F97316"
    GREY   = "#BFBFBF"
    BAR_PAD_RATIO = 0.12

    if as_of is None or pd.isna(as_of):
        as_of = result.as_of

    df_p = result.planned_curve.sort_index().reset_index()
    df_p.columns = ["date", "planned"]
    df_af = result.actual_forecast_curve.sort_index().reset_index()
    df_af.columns = ["date", "af"]

    if len(df_p) >= 1:
        full_min = min(df_p["date"].min(), df_af["date"].min()) if len(df_af) else df_p["date"].min()
        full_max = max(df_p["date"].max(), df_af["date"].max()) if len(df_af) else df_p["date"].max()
        span_ms = max(int((pd.to_datetime(full_max) - pd.to_datetime(full_min)) / pd.Timedelta(milliseconds=1)), 1)
        n_bars = max(len(df_p), 1)
        slot_ms = span_ms / n_bars
        bar_width_ms = int(slot_ms * (1.0 - BAR_PAD_RATIO))
    else:
        bar_width_ms = int(pd.Timedelta(hours=8) / pd.Timedelta(milliseconds=1))


    fig = go.Figure()
    # Planned as grey columns (cumulative)
    fig.add_trace(go.Bar(
        x=df_p["date"], y=df_p["planned"], name="Planned",
        marker_color=GREY, opacity=0.55,
        width=[bar_width_ms] * len(df_p)
    ))
    # Actual/Forecast as orange line on top
    fig.add_trace(go.Scatter(
        x=df_af["date"], y=df_af["af"], name="Actual / Forecast",
        mode="lines", line=dict(color=ORANGE, width=3)
    ))
    fig.update_layout(barmode="overlay")

    # Red as-of line and blue shading to the left
    if not pd.isna(as_of):
        fig.add_vline(x=as_of, line_width=2, line_dash="solid", line_color="red")
        if len(df_af):
            fig.add_vrect(x0=min(df_af["date"].min(), df_p["date"].min()),
                          x1=as_of, fillcolor="LightBlue", opacity=0.15, line_width=0)

    # Annotation at the forecast start
    y_asof_series = result.actual_forecast_curve[result.actual_forecast_curve.index <= as_of]
    y_asof = float(y_asof_series.iloc[-1]) if len(y_asof_series) else 0.0
    fig.add_annotation(
        x=as_of, y=y_asof, text="Forecast Starts", showarrow=True, arrowhead=2,
        ax=60, ay=-60
    )

    # BTA logo in the top-right
    try:
        src = Image.open(logo_path)
    except Exception:
        src = None

    if src is not None:
        fig.add_layout_image(
            dict(source=src, xref="paper", yref="paper",
                 x=1.02, y=1.12, sizex=0.25, sizey=0.25,
                 xanchor="right", yanchor="top", layer="above"))
        # Give the logo some breathing room
        fig.update_layout(margin=dict(l=50, r=120, t=80, b=50))

    # Cosmetics to mirror your slide
    fig.update_layout(
        template="simple_white",
        legend=dict(orientation="v", y=0.95, x=1.01, xanchor="left", bgcolor="rgba(0,0,0,0)"),
        yaxis_title="Cumulative Hours", xaxis_title="Date",
    )

    fig.update_yaxes(rangemode="tozero")
    return fig