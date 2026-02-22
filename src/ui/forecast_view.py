from datetime import timedelta
import streamlit as st
import pandas as pd
from models.session import SessionModel
from models.phase import Phase
from models.task import Task
from models.project import Project
from logic.forecast import build_forecast_df_v2, build_forecast_result, make_forecast_figure

from ui.utils.format import format_timedelta

DTFMT = "%Y-%m-%d %H:%M"


def render_forecast(session: SessionModel):

    if not session.project.has_actuals:
        st.info("Enter actual start / end dates for at least one task to view forecast.")
        return
    
    st.subheader("Forecast")

    raw = build_forecast_df_v2(session.project)

    # Build curves + KPIs using the (phase_order, task_order) traversal.
    res, forecast_df = build_forecast_result(raw, freq="H")

    # KPIs
    DTFMT = "%Y-%m-%d %H:%M"
    with st.container(horizontal=True):
        st.metric("Planned End", res.planned_end.strftime(DTFMT) if not pd.isna(res.planned_end) else "—")
        
        st.space(f"stretch")
        proj = session.project
        variance = 0.0
        for pid in proj.phase_order:
            phase = proj.phases[pid]
            for tid in phase.task_order:
                task = phase.tasks[tid]
                if task.completed:
                    variance += task.variance.total_seconds() / 3600
        last_task_completed = None
        last_task = None
        for pid in proj.phase_order:
            phase = proj.phases[pid]
            for tid in phase.task_order:
                task = phase.tasks[tid]
                if not task.completed:
                    last_task_completed = last_task
                    break
                last_task = task
        if last_task_completed is not None:
            delay = last_task_completed.actual_end - last_task_completed.end_date
        else: delay = proj.actual_end - proj.end_date
        # st.metric(
        #     "Forecast End",
        #     res.forecast_end.strftime(DTFMT) if not pd.isna(res.forecast_end) else "—",
        #     delta=(
        #         ("+" if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end) and res.forecast_end > res.planned_end) else "")
        #         + (str(format_timedelta(res.forecast_end - res.planned_end)) if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end)) else "")
        #     ),
        #     delta_color="inverse"
        # )
        forecast_end = proj.end_date + delay #- timedelta(hours=1.5)
        st.metric(
            "Forecast End",
            forecast_end.strftime(DTFMT),
            delta=(
                ("+" if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end) and res.forecast_end > res.planned_end) else "")
                + (str(format_timedelta(delay)) if delay is not None else "")
            ),
            delta_color="inverse"
        )
        st.space(f"stretch")

        actual, planned = session.project.completed_hours()
        # actual += timedelta(hours=1.5).total_seconds() / 3600
        # planned += timedelta(hours=1.5).total_seconds() / 3600
        st.metric(
            label="Earned (to date)", 
            value=f"{actual:.1f} h",
            delta=f"{format_timedelta(timedelta(hours=actual - planned))}",
            delta_color="inverse",
            help="Total *actual* hours completed across all **planned** tasks vs the *planned* hours for those tasks."
        )
        
        st.space(f"stretch")

        st.metric("Unplanned (to date)", f"{session.project.unplanned_hours():.1f} h")

        st.space(f"stretch")
        
        st.metric("Total Planned", f"{res.planned_curve.iloc[-1]:,.1f} h")

    # Chart (logo will be pulled from assets/bta_logo.png or /mnt/data/bta_logo.png)
    fig = make_forecast_figure(res, project_name=session.project.name)
    st.plotly_chart(fig, width='stretch')
    
    if res.forecast_start is not None:
        st.info(f"Last Update: {res.forecast_start.strftime("%b %d %H:%M")}", width=220)

    # Details
    show_table = st.checkbox("Show forecasted task details", value=False)
    if show_table:
        view = raw[[
            "name",
            "phase" if "phase" in raw.columns else None,
            "planned_start", "planned_finish", "planned_duration",
            "actual_start", "actual_finish", "actual_duration",
        ]].dropna(axis=1, how='all')
        view.rename({old: str.capitalize(old) for old in view.columns})
        st.dataframe(view, width='stretch')