import streamlit as st
from zoneinfo import ZoneInfo
import datetime as dt

from models.shift_schedule import ShiftDefinition

def render_shift_definition(current_tz: ZoneInfo = ZoneInfo("America/Vancouver")):
    st.subheader(f"Shift Definition")
    st.caption(f"Specify the start of day / night shift during the project.")
    
    shift_definition = st.session_state.get("shift_definition", None)
    
    
    cols = st.columns(3)
    with cols[0]:
        st.write(f"Day Shift Start")
        day_shift_start = st.time_input(
            label="Day shift start time",
            label_visibility="collapsed",
            value=shift_definition.day_start_time if shift_definition else dt.time(hour=7, minute=0)
        )

    with cols[1]:
        st.write(f"Night Shift Start")
        night_shift_start = st.time_input(
            label="Night shift start",
            label_visibility="collapsed",
            value=shift_definition.night_start_time if shift_definition else dt.time(hour=19, minute=0)
        )
        if night_shift_start < day_shift_start:
            st.error(f"Night shift must start after day shift.")
            st.stop()
    
    with cols[2]:
        st.write("Shift Length (hours)")
        shift_length = st.number_input(
            label="Shift length (hours)",
            label_visibility="collapsed",
            value=float(shift_definition.shift_length_hours) if shift_definition else 12.0,
            min_value=1.0,
            step=0.5
        )
    
    defn = ShiftDefinition(
        day_start_time=day_shift_start,
        night_start_time=night_shift_start,
        shift_length_hours=shift_length,
    )
            
    return defn