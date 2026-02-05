import streamlit as st

from models.session import SessionModel
from models.shift_schedule import ShiftSchedule

from ui.phases_view import render_phases_view
from ui.tasks_view import render_tasks_table

from ui.shift_config import render_shift_schedule_table, render_tz_info

from zoneinfo import ZoneInfo

# @st.cache_data: throws Unhashable Error for SessionModel
def render_plan(session: SessionModel):
    options = {
        "Simple": ":material/layers: Simple",
        "Detailed": ":material/format_list_bulleted: Detailed"
    }
    with st.container(horizontal=True):
        view_option = st.segmented_control(
            label="Project View",
            options=options.keys(),
            format_func=lambda t: options[t],
            width=300
        )
        st.space("stretch")

        with st.container():
            st.space("small")
            edit_schedule = st.button(
                label="Shift Schedule",
                icon=":material/calendar_month:",
                help="Click to edit the shift schedule associated with the project"
            )

        if edit_schedule:
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
                    session.project.shift_schedule = sched
                    st.success(f"Schedule updated successfully")
                    st.rerun()
                
                if c2.button("Cancel"):
                    st.rerun()
            
            edit_shift_schedule()

    match view_option:
        case "Simple":
            render_phases_view(session)
        case "Detailed":
            render_tasks_table(session)
        case _:
            st.info("Select a project view option")