import streamlit as st

from ui.analyze_view import render_analysis
from ui.delay_register import render_delay_register
from ui.delay_breakdown import render_delay_breakdown_charts
from ui.utils.workspace import render_workspace_buttons

import ui.utils.custom_tabs as ct

# if this tab is available, we know project has been loaded. No need to check.
st.header(f"{st.session_state.session.project.name} - Delays")

delay_register, breakdown, delay_plot = st.tabs(
    [
        ":material/hourglass_bottom: Register",
        ":material/bar_chart: Breakdown",
        ":material/timeline: Phase-By-Phase"
    ]
)

with delay_register:    
    render_delay_register()

with breakdown:
    delays = st.session_state.get("delays_rows_last_saved", None)
    if delays is None:
        st.info(":material/info: No delays registered. Add some to view the breakdown.")
        st.stop()
    
    render_delay_breakdown_charts(delays)
    
with delay_plot:
    render_analysis(st.session_state.session)
