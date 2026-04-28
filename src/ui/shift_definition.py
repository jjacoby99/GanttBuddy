import streamlit as st
from zoneinfo import ZoneInfo
import datetime as dt

from models.shift_schedule import ShiftDefinition

def render_shift_definition(
    project_id: str,
    current_tz: ZoneInfo | str = ZoneInfo("America/Vancouver"),
    *,
    existing: ShiftDefinition | None = None,
    key_prefix: str = "shift_definition",
) -> ShiftDefinition:
    st.subheader(f"Shift Definition")
    st.caption(f"Specify the start of day / night shift during the project.")

    shift_definition = existing or st.session_state.get("shift_definition", None)
    current_tz_name = str(current_tz)
    
    cols = st.columns(3)
    with cols[0]:
        st.write(f"Day Shift Start")
        day_shift_start = st.time_input(
            label="Day shift start time",
            label_visibility="collapsed",
            value=shift_definition.day_start_time if shift_definition else dt.time(hour=7, minute=0),
            key=f"{key_prefix}_day_start_time",
        )

    with cols[1]:
        st.write(f"Night Shift Start")
        night_shift_start = st.time_input(
            label="Night shift start",
            label_visibility="collapsed",
            value=shift_definition.night_start_time if shift_definition else dt.time(hour=19, minute=0),
            key=f"{key_prefix}_night_start_time",
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
            step=0.5,
            key=f"{key_prefix}_shift_length_hours",
        )
    
    defn = ShiftDefinition(
        id=shift_definition.id if shift_definition else None,
        project_id=project_id,
        day_start_time=day_shift_start,
        night_start_time=night_shift_start,
        shift_length_hours=shift_length,
        timezone=current_tz_name,
    )
            
    return defn
