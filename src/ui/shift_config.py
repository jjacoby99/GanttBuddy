import streamlit as st

from models.shift_schedule import Shift, ShiftSchedule
from models.session import SessionModel
from models.project import Project

import datetime as dt

import pandas as pd

from ui.utils.timezones import label_timezones_relative_to_user

def get_tz_index(zone: str, available_tzs: list[tuple[str,str]]) -> int:
    i_user = 0
    for i, (tz, label) in enumerate(available_tzs):
        if tz == zone:
            return i
    return -1

def render_tz_info(current_tz = None):
    label_info = f"(current: {current_tz})" if current_tz else f"(default: America/Vancouver)"
    
    if not st.checkbox(
            label=f"Change Timezone {label_info}",
            help="Select to change the timezone associated with the project."
        ):
            return "America/Vancouver"
    
    st.subheader("Timezone")   
    formatted = label_timezones_relative_to_user("America/Vancouver")

    i_user = [tz for (tz, _) in formatted].index(current_tz if current_tz else "America/Vancouver")
    
    tz = st.selectbox(
            label=f"Select timezone",
            options=formatted,
            format_func=lambda t: t[1],
            width=400,
            index=i_user
        )

    return tz[0]

def render_shift_schedule_table(edit: bool = False):
    st.subheader(f"Shift Schedule")
    if not edit or st.session_state.session.project.shift_schedule is None:
        default_day = Shift(
            start=dt.time(hour=7),
            duration=dt.timedelta(hours=12),
            shift_type="day",
            crew="A Crew"
        )

        default_night = Shift(
            start=dt.time(hour=19),
            duration=dt.timedelta(hours=12),
            shift_type="night",
            crew="B Crew"
        )

        schedule = ShiftSchedule(
            shifts=[default_day, default_night]
        )
    elif st.session_state.session.project.shift_schedule is not None:
        schedule = st.session_state.session.project.shift_schedule
   
    st.caption("Set your schedule.")
    data = schedule.to_dict()
    df = pd.DataFrame(data)

    view = df.drop("duration", axis=1)
    with st.container():
        edited = st.data_editor(
            data=view,
            column_order=["shift_type", "start", "end", "crew"],
            width="stretch",
            num_rows='dynamic',
            column_config={
                "crew": st.column_config.TextColumn(
                    label="Crew(s)",
                    required=False,
                    default=""
                ),
                "start": st.column_config.TimeColumn(
                    label="Start Time",
                    required=True,
                    default=dt.time(hour=7),
                    format="hh:mm a",
                    step=dt.timedelta(minutes=15)
                ),
                "end": st.column_config.TimeColumn(
                    label="End Time",
                    required=True,
                    default=dt.time(hour=19),
                    format="hh:mm a",
                    step=dt.timedelta(minutes=15)
                ),
                "shift_type": st.column_config.SelectboxColumn(
                    label="Shift Type",
                    required=True,
                    options=["day", "night"],
                    format_func=lambda t: t.capitalize()
                )
            }
        )
        return edited
    

