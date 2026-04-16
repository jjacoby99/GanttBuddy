import streamlit as st

from models.session import SessionModel

from ui.phases_view import render_phases_view
from ui.tasks_view import render_tasks_table
from ui.utils.project_info import render_project_info

from models.plan_state import PlanState
from models.project import Project

def project_glance_popover(project: Project):
    with st.popover("Project at a glance", icon=":material/dashboard:"):
        render_project_info(project)

def render_display_preferences(plan_ui_state: PlanState):
    with st.popover("Display Preferences", icon=":material/display_settings:"):
        options = {
            "Simple": ":material/layers: Simple",
            "Detailed": ":material/format_list_bulleted: Detailed"
        }
        plan_ui_state.view_mode = st.segmented_control(
            label="Project View",
            options=options.keys(),
            format_func=lambda t: options[t],
            default="Simple",
            width=300
        )

        plan_ui_state.show_actuals = st.toggle(
            label="Show actual start / end",
            value=False
        )

# @st.cache_data: throws Unhashable Error for SessionModel
def render_plan(session: SessionModel):
    
    plan_ui_state: PlanState = st.session_state.plan_state
    plan_ui_state.sync_with_project(
        project_id=session.project.uuid,
        phase_ids=list(session.project.phase_order),
    )

    if notice := st.session_state.pop("plan_constraint_update_notice", None):
        st.info(notice)
    
    with st.container(horizontal=True):
        render_display_preferences(plan_ui_state)
        st.space("stretch")
        project_glance_popover(session.project)
    
    match plan_ui_state.view_mode:
        case "Simple":
            render_phases_view(session)
        case "Detailed":
            render_tasks_table(session, plan_ui_state)
        case _:
            st.info("Select a project view option")
