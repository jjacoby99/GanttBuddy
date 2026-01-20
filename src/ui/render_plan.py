import streamlit as st

from models.session import SessionModel

from ui.phases_view import render_phases_view
from ui.tasks_view import render_tasks_table

# @st.cache_data: throws Unhashable Error for SessionModel
def render_plan(session: SessionModel):
    options = {
        "Simple": ":material/layers: Simple",
        "Detailed": ":material/format_list_bulleted: Detailed"
    }

    view_option = st.segmented_control(
        label="Project View",
        options=options.keys(),
        format_func=lambda t: options[t],
        width=300
    )

    match view_option:
        case "Simple":
            render_phases_view(session)
        case "Detailed":
            render_tasks_table(session)
        case _:
            st.info("Select a project view option")