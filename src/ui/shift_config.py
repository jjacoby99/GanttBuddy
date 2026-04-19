import streamlit as st

from models.shift_schedule import Shift, ShiftSchedule
from models.session import SessionModel
from models.project import Project
from models.crew import CrewIn

from ui.add_crew import add_crew
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

from models.shift_schedule import ShiftAssignment, assignments_to_df

def render_shift_assignment_table(crews: list[CrewIn], project_id: str, edit: bool = False) -> pd.DataFrame:
    st.subheader(f"Shift Schedule")
    
    shift_assignments = st.session_state.get("shift_assignments", None)

    if not crews:
        st.info("No crews available for the selected site. Make some!")
        if st.button(f"Add Crew"):
            add_crew()
        return None
    
    # initialize some sensible defaults
    if not shift_assignments:
        a1 = ShiftAssignment(
            project_id=project_id,
            crew_id=next(iter([c.id for c in crews])),
            shift_type="day",
            start_date=dt.date.today(),
            end_date=dt.date.today() + dt.timedelta(days=4)
        )
        a2 = ShiftAssignment(
            project_id=project_id,
            crew_id=next(iter([c.id for c in crews])),
            shift_type="night",
            start_date=dt.date.today(),
            end_date=dt.date.today() + dt.timedelta(days=4)
        )
        shift_assignments = [a1, a2]

    crew_id_map = {crew.id: crew.name for crew in crews}
    
    st.caption("Set your schedule.")
    
    df = assignments_to_df(shift_assignments)
    
    edited = st.data_editor(
        data=df,
        column_order=["crew_id", "shift_type", "start_date", "end_date"],
        width="stretch",
        num_rows='dynamic',
        column_config={
            "crew_id": st.column_config.SelectboxColumn(
                label="Crew",
                required=True,
                options=list(crew_id_map.keys()),
                format_func=lambda c: crew_id_map[c]
            ),
            "start_date": st.column_config.DateColumn(
                label="Start Date",
                required=True,
                default=dt.date.today(),
            ),
            "end_date": st.column_config.DateColumn(
                label="End Date",
                required=True,
                default=dt.date.today(),
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
    

