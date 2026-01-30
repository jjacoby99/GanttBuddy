import streamlit as st
from models.session import SessionModel
from models.ui_state import UIState

def initialize_session_state():
    if "access_token" not in st.session_state:
        st.session_state["access_token"] = None
    if "auth_headers" not in st.session_state:
        st.session_state["auth_headers"] = None
    if "session" not in st.session_state:
        st.session_state.session = SessionModel()
    if "selected_project_id" not in st.session_state:
        st.session_state["selected_project_id"] = None
    if "ui" not in st.session_state:
        st.session_state.ui = UIState()


def state_initialized() -> bool:
    state_vars = ["access_token", "auth_headers", "session"]
    for var in state_vars:
        if not var in st.session_state:
            return False
    return True