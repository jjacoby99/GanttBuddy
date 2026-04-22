import streamlit as st
from models.project_settings import ProjectSettings
from models.session import SessionModel
from logic.backend.project_permissions import project_is_read_only

@st.dialog(f"Project Settings")
def render_settings_view(session: SessionModel):
    if not session.project:
        st.warning("No project loaded.")
        return
    if project_is_read_only():
        st.info("This project is read-only, so settings can only be viewed right now.")
        return
    
    settings = session.project.settings
    work_all_day_val = settings.work_all_day
    work_all_day = st.checkbox(
        label="Work all day?",
        value=settings.work_all_day,
        help="Select if work is 24 hrs/day for this project."
    )
    work_start = work_end = None

    if not work_all_day:
        col1, col2 = st.columns(2)
        with col1:
            work_start = st.time_input("Work Start Time", value=settings.work_start_time)
            
        with col2:
            work_end = st.time_input("Work End Time", value=settings.work_end_time)

    working_days = []
    day_map = {
            0: "Mon.",
            1: "Tues.",
            2: "Wed.",
            3: "Thurs.",
            4: "Fri.",
            5: "Sat.",
            6: "Sun."
        }
    
    working_days_selected = st.pills(
        label="Working Days",
        options=sorted(list(day_map.keys())),
        default=[i for i, day in enumerate(session.project.settings.working_days) if day],
        format_func=lambda d: day_map[d],
        selection_mode="multi"
    )

    working_days_selected = sorted(working_days_selected)
    working_days = []
    for i in sorted(list(day_map.keys())):
        if i in working_days_selected:
            working_days.append(True)
        else:
            working_days.append(False)
    
    province = None
    observe_holidays = st.checkbox(
        "Observe Provincial Holidays", 
        value=settings.observe_state_holidays
    )

    if observe_holidays:
        province = st.selectbox(
            "Province (for holidays)", 
            options=["BC", "AB", "MB", "NB", "NL", "NS", "ON", "PE", "QC", "SK"],
            index=0
        )
    
    duration_resolution = st.radio(
        label="Duration Resolution",
        options=["hours", "days"],
        index=0 if settings.duration_resolution == "hours" else 1,
        help="Choose whether task durations are measured in hours or days."
    )

    submitted = st.button("Save Settings", disabled=project_is_read_only())
    if submitted:
        settings.work_all_day = work_all_day
        settings.work_start_time = work_start
        settings.work_end_time = work_end
        settings.working_days = working_days
        settings.observe_state_holidays = province is not None
        settings.province = province
        st.success("Settings saved.")
        
        st.session_state.show_settings_dialog = False
        st.rerun()
