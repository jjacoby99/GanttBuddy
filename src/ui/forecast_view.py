import streamlit as st
import pandas as pd
from models.session import SessionModel
from models.phase import Phase
from models.task import Task
from models.project import Project
from logic.forecast import build_forecast_df

def render_forecast(session: SessionModel):
    
    df = build_forecast_df(session.project)
    # --- Filters / quick actions ---
    cols = st.columns([1,1,2,2,2])
    with cols[0]:
        phase_filter = st.selectbox("Phase filter", ["All"] + sorted(df["Phase"].unique().tolist()))
    with cols[1]:
        search = st.text_input("Search")

    grid = df.copy()
    if phase_filter != "All":
        grid = grid[grid["Phase"] == phase_filter]
    if search:
        s = search.lower()
        grid = grid[grid["Task"].str.lower().str.contains(s) | grid["Notes"].str.lower().str.contains(s)]

    # --- Editable grid ---
    edited = st.data_editor(
        grid,
        key="forecast_grid",                  # so we can read selection reliably
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "Planned Start": st.column_config.DatetimeColumn(
                label="Planned Start",
                disabled=True,                 
                format="YYYY-MM-DD HH:mm"      # optional
            ),
            "Planned End": st.column_config.DatetimeColumn(
                label="Planned End",
                disabled=True,
                format="YYYY-MM-DD HH:mm"
            ),
            "Est. Duration (h)": st.column_config.NumberColumn(
                label="Est. Duration (h)",
                disabled=True,
                step=1
            ),
            "Actual Start": st.column_config.DatetimeColumn(
                label="Actual Start",
                format="YYYY-MM-DD HH:mm"
            ),
            "Actual End": st.column_config.DatetimeColumn(
                label="Actual End",
                format="YYYY-MM-DD HH:mm"
            ),
            "% Complete": st.column_config.NumberColumn(
                min_value=0, max_value=100, step=5
            )
            
        }
    )


    # Example: bulk actions on selected rows
    selection = st.session_state.get("data_editor", {}).get("selection", {})
    selected_rows = selection.get("rows", []) if selection else []

    with st.expander("Bulk actions"):
        c1,c2,c3,c4 = st.columns(4)
        if c1.button("Actual Start = Now", disabled=not selected_rows):
            now = pd.Timestamp.now()
            edited.loc[edited.index[selected_rows],"Actual Start"] = now
        if c2.button("Actual End = Now", disabled=not selected_rows):
            now = pd.Timestamp.now()
            edited.loc[edited.index[selected_rows],"Actual End"] = now
        if c3.button("Backfill End = Start + Est", disabled=not selected_rows):
            idx = edited.index[selected_rows]
            edited.loc[idx,"Actual End"] = edited.loc[idx,"Actual Start"] + pd.to_timedelta(edited.loc[idx,"Est. Duration (h)"], unit="h")
        if c4.button("Mark Done", disabled=not selected_rows):
            idx = edited.index[selected_rows]
            now = pd.Timestamp.now()
            edited.loc[idx,"% Complete"] = 100
            edited.loc[idx,"Actual End"] = edited.loc[idx,"Actual End"].fillna(now)

    # --- Forecast compute stub ---
    #if recalc:
        # 1) Merge edited back into full df (by a stable key in your real app)
        # 2) Build schedule respecting settings
        # 3) Produce: forecasted end date, cumulative hours series, gantt for remaining
        #st.success("Forecast recomputed. (Plug in your scheduling function here.)")
        # st.altair_chart(...); st.plotly_chart(...)
                
@st.dialog(f"Actual Duration")
def render_actual_duration(session: SessionModel):
    phases = session.project.phases
    if not phases:
        st.info(f"Add phases to your project to start forecasting")
        return
    
    if not session.project.has_task:
        st.info(f"Add tasks to your project to start forecasting")

    phase = st.selectbox(
        label="Select a phase to start forecasting",
        options = phases,
        format_func= lambda p: p.name if p else ""
    )

    st.write(type(phase))


                