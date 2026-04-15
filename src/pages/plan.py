import streamlit as st

from ui.plot import render_gantt, render_task_details
from ui.dependency_graph import render_dependency_graph
from ui.render_plan import render_plan
from ui.closeout import render_closeout

from ui.utils.workspace import render_workspace_buttons

render_workspace_buttons()


task_tab, plot_tab, dependency_tab = st.tabs(
    [":material/list_alt: Plan", 
     ":material/view_timeline: Visualize",
     ":material/account_tree: Dependencies"]
)

with task_tab:
    render_plan(st.session_state.session)


with plot_tab:
    render_gantt(st.session_state.session)
    st.divider()
    render_task_details(st.session_state.session)

with dependency_tab:
    render_dependency_graph(st.session_state.session.project)


if not st.session_state.session.project.closed:
    close_button = st.button(
        label=":material/task_alt: Closeout Project",
        help="Initiate project closeout process. Closed projects no longer show up on feed & home pages.",
        type="primary"
    ) 

    if close_button:
        render_closeout(session=st.session_state.session)
