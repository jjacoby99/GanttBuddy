import streamlit as st

from time import sleep

from models.project import Project
from models.session import SessionModel

from logic.backend.api_client import closeout_project, fetch_attention_tasks # to clear cache
from logic.backend.project_permissions import project_is_read_only

@st.dialog("Project Closeout")
def render_closeout(session: SessionModel):
    if project_is_read_only():
        st.info("This project is read-only, so closeout is unavailable.")
        return

    st.info(f":material/info: A project should only be closed when it has been completed.")

    total_tasks = session.project.total_tasks

    completed_tasks = session.project.tasks_completed

    remaining_tasks = session.project.tasks_remaining

    st.write(f"Task summary")

    c1, c2, c3 = st.columns(3)

    c1.caption(f"Total")
    c1.badge(
        label=f"**{total_tasks}**",
        color="blue",
        icon=":material/info:"
    )

    c2.caption(f"Incomplete")
    c2.badge(
        label=f"**{remaining_tasks}**",
        color="yellow",
        icon=":material/warning:"
    )

    c3.caption(f"Completed")
    c3.badge(
        label=f"**{completed_tasks}**",
        color="green",
        icon=":material/check:"
    )


    closeout = c1.button(
        label=":material/task_alt: Complete closeout",
        help="Mark project as closed. You can change this later.",
        type="primary",
        disabled=project_is_read_only(),
    )

    cancel = c3.button(
        label=":material/cancel: Cancel closeout",
        type="secondary"
    )

    if closeout:
        session.project.closed = True
        try:
            closeout_project(
                headers=st.session_state.get("auth_headers", {}),
                project_id=session.project.uuid
            )
        except Exception:
            st.error(f"Error closing project.")
            sleep(2)
            st.rerun()

        st.success(f":material/check: Project closed successfully!")
        fetch_attention_tasks.clear()
        sleep(2)
        st.rerun()

    if cancel:
        st.rerun()
