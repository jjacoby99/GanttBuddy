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

    if "ui" not in st.session_state:
        st.session_state.ui = UIState()