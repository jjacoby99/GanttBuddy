import streamlit as st
import pandas as pd
from models.session import SessionModel
from models.phase import Phase
from models.task import Task
from models.project import Project
from logic.forecast import build_forecast_df_v2, forecast, make_forecast_figure, ForecastResult

DTFMT = "%Y-%m-%d %H:%M"


def render_forecast(session: SessionModel):

    if not session.project.has_actuals:
        st.info("Enter actual start / end dates for at least one task to view forecast.")
        return

    raw = build_forecast_df_v2(session.project)

    # No manual As Of. Forecast will infer it from the last actual.
    st.caption("The red line marks where actuals end and the forecast begins (last actual timestamp).")

    freq = st.selectbox("Time step", options=["H", "30min", "15min", "D"], index=0,
                        help="Resolution for building cumulative curves.")

    # Let the engine infer as_of=None
    forecast_df = forecast(raw, freq=freq)
    res = ForecastResult(
        time=forecast_df["time"],
        planned_curve=forecast_df["planned_cum_hours"],
        actual_forecast_curve=forecast_df["actual_forecast_cum_hours"],
        planned_end=raw["planned_finish"].max(),
        forecast_end=raw["planned_finish"].max(), # Placeholder; could compute actual forecast end
        forecast_start=session.project.actual_end
    )

    st.write(f"End of actual data is used as the forecast start: {session.project.actual_end}")

    #debug
    res.write_to_csv("forecast_output.csv")
    # KPIs
    DTFMT = "%Y-%m-%d %H:%M"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Planned End", res.planned_end.strftime(DTFMT) if not pd.isna(res.planned_end) else "—")
    k2.metric("Forecast End", res.forecast_end.strftime(DTFMT) if not pd.isna(res.forecast_end) else "—",
              delta=("+" if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end) and res.forecast_end > res.planned_end) else "")
                    + (str((res.forecast_end - res.planned_end)) if (not pd.isna(res.planned_end) and not pd.isna(res.forecast_end)) else ""))
    k3.metric("Completed (to date)", f"{session.project.completed_hours()} h")
    print(type(session.project.completed_hours()), session.project.completed_hours())
    k4.metric("Total Planned", f"{res.planned_curve.iloc[-1]:,.1f} h")

    # Chart (logo will be pulled from assets/bta_logo.png or /mnt/data/bta_logo.png)
    fig = make_forecast_figure(res, project_name=session.project.name)
    st.plotly_chart(fig, use_container_width=True)

    # Details
    show_table = st.checkbox("Show forecasted task details", value=True)
    if show_table:
        view = raw[[
            "name",
            "phase" if "phase" in raw.columns else None,
            "planned_start", "planned_finish", "planned_duration",
            "actual_start", "actual_finish", "actual_duration",
        ]].dropna(axis=1, how='all')
        view.rename({old: str.capitalize(old) for old in view.columns})
        st.dataframe(view, use_container_width=True)
 