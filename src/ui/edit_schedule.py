import streamlit as st
from ui.shift_config import render_shift_schedule_table, render_tz_info
from models.shift_schedule import ShiftSchedule

from zoneinfo import ZoneInfo

@st.dialog(f"Edit Shift Schedule")
def edit_shift_schedule():
    tz = render_tz_info(edit=True)
    df = render_shift_schedule_table(edit=True)
    c1, c2 = st.columns(2)
    if c1.button("Update Schedule"):            
        try:
            sched = ShiftSchedule.from_df(df)
            sched.timezone = ZoneInfo(tz)
        except Exception as e:
            st.error(f"Error updating project schedule: {e}")
            return
        st.session_state.session.project.shift_schedule = sched
        st.success(f"Schedule updated successfully")
        st.rerun()
    
    if c2.button("Cancel"):
        st.rerun()