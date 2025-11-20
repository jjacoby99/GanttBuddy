from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from PIL import Image

from logic.duration import DurationCalculator
from models.project import Project

DTFMT = "%Y-%m-%d %H:%M"

import pandas as pd
import numpy as np
from datetime import timedelta

def forecast(df: pd.DataFrame, freq: str = "H") -> pd.DataFrame:
    """
    Given a DataFrame with columns:
        id, name, phase,
        planned_start, planned_finish, planned_duration,
        actual_start, actual_finish, actual_duration

    returns a time-indexed DataFrame with columns:
        time
        planned_cum_hours
        actual_forecast_cum_hours

    The algorithm:
      - Builds a continuous-time cumulative planned-hours curve from planned intervals.
      - Derives an effective schedule for each task that incorporates actuals and a
        global delay for unstarted tasks, then builds the actual+forecast cumulative curve.
      - Evaluates both curves on a regular time grid with step `freq` (default 1 hour).
    """

    # ---- Safety checks / normalization --------------------------------------
    required_cols = [
        "planned_start", "planned_finish", "planned_duration",
        "actual_start", "actual_finish", "actual_duration"
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    # Ensure datetime types
    for col in ["planned_start", "planned_finish", "actual_start", "actual_finish"]:
        if not pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col])

    # Ensure floats for durations
    for col in ["planned_duration", "actual_duration"]:
        if not pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].astype(float)

    # ---- Helper to build curve on a time grid from (start, finish, duration) ----
    def _build_curve_on_grid(starts: pd.Series,
                             finishes: pd.Series,
                             durations: pd.Series,
                             grid: pd.DatetimeIndex) -> np.ndarray:
        """
        Construct cumulative hours curve evaluated on `grid` times.

        Each task contributes durations[i] hours between starts[i] and finishes[i],
        at constant rate = durations[i] / (finish - start in hours).

        The integration is done via an event-based sweep, then integrated to the grid.
        """
        # Build events: (time, delta_rate)
        events = []
        for s, f, d in zip(starts, finishes, durations):
            if pd.isna(s) or pd.isna(f) or pd.isna(d):
                continue
            dt_hours = (f - s).total_seconds() / 3600.0
            if dt_hours <= 0 or d <= 0:
                # Degenerate or zero-duration tasks are ignored
                continue
            rate = d / dt_hours
            events.append((s, rate))
            events.append((f, -rate))

        if not events:
            # No valid tasks → just zeros
            return np.zeros(len(grid), dtype=float)

        events.sort(key=lambda x: x[0])

        # Sweep simultaneously over events and grid
        values = np.zeros(len(grid), dtype=float)
        current_rate = 0.0
        cum = 0.0

        e_idx = 0
        last_t = grid[0]

        # If first event is before grid start, fast-forward to grid[0]
        # updating the rate but not integrating before grid start
        while e_idx < len(events) and events[e_idx][0] < last_t:
            _, delta_rate = events[e_idx]
            current_rate += delta_rate
            e_idx += 1

        for i, t in enumerate(grid):
            # Process all events up to this grid time
            while e_idx < len(events) and events[e_idx][0] <= t:
                ev_t, delta_rate = events[e_idx]
                dt = (ev_t - last_t).total_seconds() / 3600.0
                if dt > 0:
                    cum += current_rate * dt
                    last_t = ev_t
                current_rate += delta_rate
                e_idx += 1

            # Integrate from last_t to t at current_rate
            dt = (t - last_t).total_seconds() / 3600.0
            if dt > 0:
                cum += current_rate * dt
                last_t = t

            values[i] = cum

        return values

    # ---- 1. Define the time grid --------------------------------------------
    # Planned start/end bounds
    planned_starts = df["planned_start"]
    planned_finishes = df["planned_finish"]

    # We'll later compute effective (actual/forecast) intervals as well
    actual_starts = df["actual_start"]
    actual_finishes = df["actual_finish"]

    # Compute overall min/max over planned and actual/forecast side
    t_min_candidates = pd.concat([planned_starts.dropna(), actual_starts.dropna()])
    t_max_candidates = pd.concat([planned_finishes.dropna(), actual_finishes.dropna()])

    if t_min_candidates.empty or t_max_candidates.empty:
        raise ValueError("Cannot determine project time bounds from provided DataFrame.")

    t_min = t_min_candidates.min()
    t_max = t_max_candidates.max()

    # Just in case everything is same timestamp, extend by 1 hour so date_range works
    if t_min == t_max:
        t_max = t_max + timedelta(hours=1)

    grid = pd.date_range(t_min, t_max, freq=freq)

    # ---- 2. Planned curve ----------------------------------------------------
    planned_durations = df["planned_duration"].copy()

    planned_cum = _build_curve_on_grid(
        starts=planned_starts,
        finishes=planned_finishes,
        durations=planned_durations,
        grid=grid,
    )

    # ---- 3. Build effective actual/forecast schedule for each task ----------
    n = len(df)
    eff_start = pd.Series(index=df.index, dtype="datetime64[ns]")
    eff_finish = pd.Series(index=df.index, dtype="datetime64[ns]")
    eff_duration = pd.Series(index=df.index, dtype=float)

    # Masks
    completed_mask = df["actual_start"].notna() & df["actual_finish"].notna()
    in_progress_mask = df["actual_start"].notna() & df["actual_finish"].isna()
    not_started_mask = df["actual_start"].isna() & df["actual_finish"].isna()

    # 3.1 Completed tasks: use actuals
    if completed_mask.any():
        # Use actual_duration if present; fall back to actual_end - actual_start
        actual_dur = df.loc[completed_mask, "actual_duration"].copy()

        # Fill missing or zero/negative with difference between timestamps
        bad = actual_dur.isna() | (actual_dur <= 0)
        if bad.any():
            dt_hours = (
                df.loc[completed_mask & bad, "actual_finish"]
                - df.loc[completed_mask & bad, "actual_start"]
            ).dt.total_seconds() / 3600.0
            actual_dur.loc[bad] = dt_hours

        eff_start.loc[completed_mask] = df.loc[completed_mask, "actual_start"]
        eff_finish.loc[completed_mask] = df.loc[completed_mask, "actual_finish"]
        eff_duration.loc[completed_mask] = actual_dur

    # 3.2 In-progress tasks: started, not finished → actual_start + planned_duration
    if in_progress_mask.any():
        eff_start.loc[in_progress_mask] = df.loc[in_progress_mask, "actual_start"]
        eff_duration.loc[in_progress_mask] = df.loc[in_progress_mask, "planned_duration"]
        eff_finish.loc[in_progress_mask] = eff_start.loc[in_progress_mask] + df.loc[
            in_progress_mask, "planned_duration"
        ].apply(lambda h: timedelta(hours=h))

    # 3.3 Not-started tasks: shift plan by global delay Δ
    delay = timedelta(0)
    if completed_mask.any():
        # Start delay per completed task
        start_delays = (
            df.loc[completed_mask, "actual_start"]
            - df.loc[completed_mask, "planned_start"]
        )
        # Robust aggregate: median
        delay = start_delays.median()
        if pd.isna(delay):
            delay = timedelta(0)

    if not_started_mask.any():
        eff_start.loc[not_started_mask] = df.loc[not_started_mask, "planned_start"] + delay
        eff_duration.loc[not_started_mask] = df.loc[not_started_mask, "planned_duration"]
        eff_finish.loc[not_started_mask] = eff_start.loc[not_started_mask] + df.loc[
            not_started_mask, "planned_duration"
        ].apply(lambda h: timedelta(hours=h))

    # ---- 4. Actual + forecast curve -----------------------------------------
    actual_forecast_cum = _build_curve_on_grid(
        starts=eff_start,
        finishes=eff_finish,
        durations=eff_duration,
        grid=grid,
    )

    # ---- 5. Assemble result --------------------------------------------------

    result = pd.DataFrame({
        "time": grid,
        "planned_cum_hours": planned_cum,
        "actual_forecast_cum_hours": actual_forecast_cum,
    })

    return result

@dataclass
class ForecastResult:
    time: pd.Series
    planned_curve: pd.Series
    actual_forecast_curve: pd.Series
    planned_end: Optional[pd.Timestamp]
    forecast_end: Optional[pd.Timestamp]
    forecast_start: Optional[pd.Timestamp] = None

    def write_to_csv(self, path: str):
        df = pd.DataFrame({
            "time": self.time,
            "planned_cum_hours": self.planned_curve,
            "actual_forecast_cum_hours": self.actual_forecast_curve,
        })
        df.to_csv(path, index=False)


def make_forecast_figure(
        result: pd.DataFrame,
        project_name: str,
        logo_path: Optional[str] = "assets/bta_logo.png",
    ) -> go.Figure:
    ORANGE = "#F97316"
    GREY   = "#CFCFCF"
    BAR_PAD_RATIO = 0.12  # constant gap between columns

    df_p = result.planned_curve.sort_index().reset_index()
    df_p.columns = ["date", "planned"]
    df_p["date"] = result.time
    
    df_af = result.actual_forecast_curve.sort_index().reset_index()
    df_af.columns = ["date", "af"]
    df_af["date"] = result.time

    # --- Constant-width bars based on total plot span / number of bars
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
        width=[bar_width_ms] * len(df_p),
    ))
    # Actual/Forecast as orange line on top
    fig.add_trace(go.Scatter(
        x=df_af["date"], y=df_af["af"], name="Actual / Forecast",
        mode="lines", line=dict(color=ORANGE, width=3)
    ))
    fig.update_layout(barmode="overlay", bargap=0.0, bargroupgap=0.0)

    # Red as-of line and blue shading to the left
    if not result.forecast_start is None:
        fig.add_vline(x=result.forecast_start, line_width=2, line_dash="solid", line_color="red")
        if len(df_af) and len(df_p):
            fig.add_vrect(x0=min(df_af["date"].min(), df_p["date"].min()),
                          x1=result.forecast_start, fillcolor="LightBlue", opacity=0.15, line_width=0)

    # Annotation at the forecast start
    y_asof_series = result.actual_forecast_curve[result.time <= result.forecast_start]
    y_asof = float(y_asof_series.iloc[-1]) if len(y_asof_series) else 0.0
    fig.add_annotation(
        x=result.forecast_start, y=y_asof, text="Forecast", showarrow=True, arrowhead=2,
        ax=60, ay=-60
    )

    # BTA logo in the top-right
    try:
        from pathlib import Path
        src = Image.open(Path(__file__).parent.parent / logo_path)
    except Exception as e:
        print(f"Exception caught trying to open logo at {logo_path}: {e}")
        src = None
    if src is not None:
        fig.add_layout_image(
            dict(source=src, xref="paper", yref="paper",
                 x=1.0, y=1.0, sizex=0.15, sizey=0.15,
                 xanchor="right", yanchor="top", layer="above"))
        fig.update_layout(margin=dict(l=50, r=120, t=80, b=50))

    # Cosmetics to mirror your slide
    fig.update_layout(
        template="simple_white",
        legend=dict(orientation="v", y=0.95, x=1.01, xanchor="left", bgcolor="rgba(0,0,0,0)"),
        yaxis_title="Cumulative Hours", xaxis_title="Date",
        yaxis=dict(range=[0, max(result.planned_curve.max(), result.actual_forecast_curve.max()) * 1.2]),
        title=f"{project_name} Forecast"
    )
    fig.update_yaxes(rangemode="tozero")
    return fig


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
        "planned_duration": [],
        "actual_start": [],
        "actual_finish": [],
        "actual_duration": []
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
            data["planned_duration"].append(task.planned_duration.total_seconds() / 3600.0)
            data["actual_start"].append(task.actual_start) # Can be None
            data["actual_finish"].append(task.actual_end) # Can be None
            
            actual_duration = None
            if task.actual_end and task.actual_start:
                actual_duration = task.actual_duration.total_seconds() / 3600.0
            
            data["actual_duration"].append(actual_duration)
    return pd.DataFrame(data)