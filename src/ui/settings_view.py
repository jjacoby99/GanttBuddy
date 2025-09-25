import streamlit as st
from models.project_settings import ProjectSettings
from models.session import SessionModel

@st.dialog(f"Project Settings")
def render_settings_view(session: SessionModel):
    if not session.project:
        st.warning("No project loaded.")
        return
    
    settings = session.project.settings

    with st.form("settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            work_start = st.time_input("Work Start Time", value=settings.work_start_time)
            work_end = st.time_input("Work End Time", value=settings.work_end_time)
            working_days = []
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            for i, day in enumerate(days):
                working_days.append(st.checkbox(day, value=settings.working_days[i]))
        
        with col2:
            province = None
            if st.checkbox("Observe State Holidays", value=settings.observe_state_holidays):
                province = st.selectbox(
                    "Province (for holidays)", 
                    options=["BC", "AB", "MB", "NB", "NL", "NS", "ON", "PE", "QC", "SK"],
                )

        submitted = st.form_submit_button("Save Settings")
        if submitted:
            settings.work_start_time = work_start
            settings.work_end_time = work_end
            settings.working_days = working_days
            settings.observe_state_holidays = province is not None
            settings.province = province
            st.success("Settings saved.")
        st.session_state.show_settings_dialog = False
