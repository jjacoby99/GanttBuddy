from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from logic.backend.api_client import fetch_project_forecast
from logic.forecast import ForecastResult, make_forecast_figure
from models.forecast import ForecastResponse
from models.session import SessionModel
from ui.utils.format import format_timedelta

DTFMT = "%Y-%m-%d %H:%M"


def _to_figure_result(payload: ForecastResponse) -> ForecastResult:
    series = payload.series_to_frame()
    return ForecastResult(
        time=series["time"],
        planned_curve=series["planned_cum_hours"],
        actual_forecast_curve=series["actual_forecast_cum_hours"],
        planned_end=payload._to_local(payload.planned_end),
        forecast_end=payload._to_local(payload.forecast_end),
        forecast_start=payload._to_local(payload.forecast_start),
    )


def render_forecast(session: SessionModel):
    headers = st.session_state.get("auth_headers", {})
    project = session.project

    try:
        payload = fetch_project_forecast(headers=headers, project_id=project.uuid)
    except ValueError as exc:
        st.error(f"No Forecast available. Save your project first.")
        return

    if not payload.has_actuals:
        st.info("Enter actual start / end dates for at least one task to view forecast.")
        return

    st.subheader("Forecast")

    result = _to_figure_result(payload)

    with st.container(horizontal=True):
        st.metric(
            "Planned End",
            result.planned_end.strftime(DTFMT) if result.planned_end is not None and not pd.isna(result.planned_end) else "-",
        )

        st.space("stretch")

        delay = None
        if result.planned_end is not None and result.forecast_end is not None:
            delay = result.forecast_end - result.planned_end

        st.metric(
            "Forecast End",
            result.forecast_end.strftime(DTFMT) if result.forecast_end is not None and not pd.isna(result.forecast_end) else "-",
            delta=(
                (
                    "+"
                    if (
                        result.planned_end is not None
                        and result.forecast_end is not None
                        and result.forecast_end > result.planned_end
                    )
                    else ""
                )
                + (str(format_timedelta(delay)) if delay is not None else "")
            ),
            delta_color="inverse",
        )

        st.space("stretch")

        earned_delta = timedelta(hours=payload.earned_actual_hours - payload.earned_planned_hours)
        st.metric(
            label="Earned (to date)",
            value=f"{payload.earned_actual_hours:.1f} h",
            delta=f"{format_timedelta(earned_delta)}",
            delta_color="inverse",
            help="Total *actual* hours completed across all **planned** tasks vs the *planned* hours for those tasks.",
        )

        st.space("stretch")

        st.metric("Unplanned (to date)", f"{payload.unplanned_hours:.1f} h")

        st.space("stretch")

        st.metric("Total Planned", f"{payload.total_planned_hours:,.1f} h")

    fig = make_forecast_figure(result, project_name=project.name)
    st.plotly_chart(fig, width="stretch")

    if result.forecast_start is not None:
        st.info(f"Last Update: {result.forecast_start.strftime('%b %d %H:%M')}", width=220)

    show_table = st.checkbox("Show forecasted task details", value=False)
    if show_table:
        view = payload.tasks_to_frame()
        if not view.empty:
            view = view[
                [
                    "name",
                    "phase",
                    "planned_start",
                    "planned_finish",
                    "planned_duration",
                    "actual_start",
                    "actual_finish",
                    "actual_duration",
                ]
            ].dropna(axis=1, how="all")
        st.dataframe(view, width="stretch")
