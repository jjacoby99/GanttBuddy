import streamlit as st

from ui.plot import render_gantt, render_task_details
from ui.dependency_graph import render_dependency_graph
from ui.render_plan import render_plan
from ui.closeout import render_closeout

from ui.utils.workspace import render_workspace_buttons
from logic.backend.project_permissions import project_is_read_only

render_workspace_buttons()

VIEW_OPTIONS = {
    "Plan": ":material/list_alt: Plan",
    "Visualize": ":material/view_timeline: Visualize",
    "Dependencies": ":material/account_tree: Dependencies",
}

selected_view = st.segmented_control(
    "Workspace View",
    options=list(VIEW_OPTIONS.keys()),
    format_func=lambda view: VIEW_OPTIONS[view],
    default="Plan",
    selection_mode="single",
    width="stretch",
)

if selected_view == "Plan":
    render_plan(st.session_state.session)
elif selected_view == "Visualize":
    render_gantt(st.session_state.session)
    st.divider()
    render_task_details(st.session_state.session)
elif selected_view == "Dependencies":
    render_dependency_graph(st.session_state.session.project)


if not st.session_state.session.project.closed:
    close_button = st.button(
        label=":material/task_alt: Closeout Project",
        help="Initiate project closeout process. Closed projects no longer show up on feed & home pages.",
        type="primary",
        disabled=project_is_read_only(),
    ) 

    if close_button:
        render_closeout(session=st.session_state.session)
