import streamlit as st

from models.session import SessionModel

# @st.cache_data: throws Unhashable Error for SessionModel
def render_phases_view(session: SessionModel):
    
    phases = session.project.phases
    if not phases:
        st.info("Add phases to your project to see the phases view.")
        return
    
    st.divider()

    st.subheader("Project Phases Overview")
    
    phase_df = session.project.get_phase_df()
    view = phase_df[["phase", "planned_start", "planned_end", "planned_duration", "num_tasks"]]
    st.dataframe(
        data=view,
        column_order=["phase", "planned_start", "planned_end", "planned_duration", "num_tasks"],
        column_config={
            "phase": st.column_config.TextColumn("Phase Name"),
            "planned_start": st.column_config.DatetimeColumn(
                label="Planned Start",
                format="localized",
                ),
            "planned_end": st.column_config.DatetimeColumn(
                label="Planned End",
                format="localized",
                ),
            "planned_duration": st.column_config.NumberColumn(
                label="Planned Duration (hrs)",
                width="small",
                format="%.1f"
                ),
            "num_tasks": st.column_config.NumberColumn(
                label="Number of Tasks",
                width="small"
                ),
        }
    )