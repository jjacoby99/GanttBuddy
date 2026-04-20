import streamlit as st

from logic.feature_flags import signals_enabled
from ui.signals_view import render_signals_view
from ui.utils.workspace import render_workspace_buttons

if not signals_enabled():
    st.title("Signals")
    st.info(":material/info: Coming soon!")
    st.caption("We're working hard to bring you actionable insights and alerts to keep your projects on track. Stay tuned!")
    st.stop()

render_workspace_buttons()
render_signals_view(st.session_state.session)
