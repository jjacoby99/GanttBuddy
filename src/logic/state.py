import streamlit as st
from models.session import SessionModel
from models.ui_state import UIState
from models.gantt_state import GanttState
from models.plan_state import PlanState
def initialize_session_state():
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "auth_headers" not in st.session_state:
        st.session_state["auth_headers"] = None
    if "auth" not in st.session_state:
        st.session_state["auth"] = {}
    if "backend_auth_ready" not in st.session_state:
        st.session_state["backend_auth_ready"] = False
    if "session" not in st.session_state:
        st.session_state.session = SessionModel()
    if "selected_project_id" not in st.session_state:
        st.session_state["selected_project_id"] = None
    if "ui" not in st.session_state:
        st.session_state.ui = UIState()
    if "gantt_state" not in st.session_state:
        st.session_state.gantt_state = GanttState()
    if "plan_state" not in st.session_state:
        st.session_state.plan_state = PlanState()


def state_initialized() -> bool:
    state_vars = ["access_token", "auth_headers", "auth", "backend_auth_ready", "session"]
    for var in state_vars:
        if not var in st.session_state:
            return False
    return True
