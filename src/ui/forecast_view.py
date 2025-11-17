import streamlit as st
import pandas as pd
from models.session import SessionModel
from models.phase import Phase
from models.task import Task
from models.project import Project
from logic.forecast import build_forecast_df_v2, forecast, make_forecast_figure

DTFMT = "%Y-%m-%d %H:%M"


def render_forecast(session: SessionModel):
    raw = build_forecast_df_v2(session.project)

    # No manual As Of. Forecast will infer it from the last actual.
    st.caption("The red line marks where actuals end and the forecast begins (last actual timestamp).")

    productivity = st.slider("Productivity factor (relative to plan)", 0.25, 2.0, 1.0, 0.05)
    freq = st.selectbox("Time step", options=["H", "30min", "15min", "D"], index=0,
                        help="Resolution for building cumulative curves.")

    # Let the engine infer as_of=None
    res = forecast(raw, as_of=None, productivity=float(productivity), freq=freq)

    # KPIs
    DTFMT = "%Y-%m-%d %H:%M"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Planned End", res.planned_end.strftime(DTFMT) if not pd.isna(res.planned_end) else "—")
    k2.metric("Forecast End", res.forecast_end.strftime(DTFMT) if not pd.isna(res.forecast_end) else "—",
              delta=("+" if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end) and res.forecast_end > res.planned_end) else "")
                    + (str((res.forecast_end - res.planned_end)) if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end)) else ""))
    k3.metric("Completed (to date)", f"{res.completed_hours_to_date:,.1f} h")
    k4.metric("Total Planned", f"{res.total_planned_hours:,.1f} h")

    # Chart (logo will be pulled from assets/bta_logo.png or /mnt/data/bta_logo.png)
    fig = make_forecast_figure(res, as_of=res.as_of, logo_path="assets/bta_logo.png")
    st.plotly_chart(fig, use_container_width=True)

    # Details
    show_table = st.checkbox("Show forecasted task details", value=True)
    if show_table:
        view = res.forecasted_tasks[[
            "name",
            "phase" if "phase" in res.forecasted_tasks.columns else None,
            "planned_start", "planned_finish", "planned_hours",
            "actual_start", "actual_finish",
            "completed_hours_to_date", "remaining_hours",
            "forecast_start", "forecast_finish",
        ]].dropna(axis=1, how='all')
        view.rename({old: str.capitalize(old) for old in view.columns})
        st.dataframe(view, use_container_width=True)
 