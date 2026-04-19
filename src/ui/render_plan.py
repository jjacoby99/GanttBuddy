import streamlit as st
import pandas as pd

from models.session import SessionModel

from logic.constraint_inference import infer_missing_project_constraints
from ui.tasks_view import render_tasks_table
from ui.utils.project_info import render_project_info

from models.plan_state import PlanState
from models.project import Project

def project_glance_popover(project: Project):
    with st.popover("Project at a glance", icon=":material/dashboard:"):
        render_project_info(project)

def render_display_preferences(plan_ui_state: PlanState):
    with st.popover("Display Preferences", icon=":material/display_settings:"):
        plan_ui_state.show_actuals = st.toggle(
            label="Show actual start / end",
            value=plan_ui_state.show_actuals,
        )


def render_constraint_inference_controls(session: SessionModel) -> None:
    with st.popover("Infer Constraints", icon=":material/auto_fix_high:"):
        st.caption(
            "Infer missing finish-to-start constraints with zero lag when a successor starts exactly when another item ends."
        )
        st.caption(
            "Tasks are inferred within the same phase. Phases are inferred across the project. Existing constraints are left alone."
        )

        if st.button(
            "Infer Missing Constraints",
            type="primary",
            width="stretch",
            key="infer_missing_constraints",
        ):
            report = infer_missing_project_constraints(session.project, apply=True)
            st.session_state["plan_constraint_inference_report"] = report


def render_constraint_inference_preview(session: SessionModel) -> None:
    report = st.session_state.get("plan_constraint_inference_report")
    if not report or report.get("project_id") != session.project.uuid:
        return

    with st.container(border=True):
        header_left, header_right = st.columns([5, 1], vertical_alignment="center")
        with header_left:
            st.subheader("Inferred Constraint Preview")
            st.caption("Results from the latest inference run on this project.")
        with header_right:
            if st.button("OK", key="dismiss_constraint_inference_preview", width="stretch"):
                del st.session_state["plan_constraint_inference_report"]
                st.rerun()

        c1, c2 = st.columns(2)
        c1.metric("Tasks Updated", report["task_successor_count"])
        c2.metric("Task Constraints Added", report["task_constraint_count"])
        c3, c4 = st.columns(2)
        c3.metric("Phases Updated", report["phase_successor_count"])
        c4.metric("Phase Constraints Added", report["phase_constraint_count"])

        preview_rows = report["preview_rows"]
        if not preview_rows:
            st.info("No missing zero-lag FS constraints were inferred for this project.")
            return

        st.dataframe(pd.DataFrame(preview_rows), hide_index=True, width="stretch")

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
        render_constraint_inference_controls(session)
        st.space("stretch")
        project_glance_popover(session.project)

    render_constraint_inference_preview(session)
    render_tasks_table(session, plan_ui_state)
