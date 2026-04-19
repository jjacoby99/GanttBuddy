from __future__ import annotations

from io import BytesIO

import streamlit as st

from logic.report_export import (
    ReportExportError,
    build_excel_report_buffer,
    build_powerpoint_report_buffer,
)
from models.session import SessionModel


def _reset_export_state(project_id: str) -> dict:
    state = st.session_state.setdefault("report_export_state", {})
    if state.get("project_id") != project_id:
        state.clear()
        state["project_id"] = project_id
    return state


@st.dialog("Export Post-Mortem Report")
def render_report_export_dialog(session: SessionModel):
    state = _reset_export_state(session.project.uuid)
    metadata = st.session_state.get("reline_metadata")
    headers = st.session_state.get("auth_headers", {})

    st.caption("Prepare either the existing Excel workbook or the PowerPoint deck built from the mill reline template.")
    include_figures = st.toggle(
        "Include figures in PowerPoint",
        value=state.get("include_figures", False),
        help="Turn this off to isolate deck structure and table formatting while we validate the template output.",
    )
    state["include_figures"] = include_figures

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Prepare Excel", width="stretch", icon=":material/table_view:"):
            with st.spinner("Preparing Excel report..."):
                buffer = build_excel_report_buffer(session.project)
                state["excel_bytes"] = buffer.getvalue()
                state["excel_error"] = None

    with c2:
        if st.button("Prepare PowerPoint", width="stretch", icon=":material/slideshow:"):
            with st.spinner("Preparing PowerPoint report..."):
                try:
                    buffer = build_powerpoint_report_buffer(
                        project=session.project,
                        headers=headers,
                        metadata=metadata,
                        include_figures=include_figures,
                    )
                    state["powerpoint_bytes"] = buffer.getvalue()
                    state["powerpoint_error"] = None
                except ReportExportError as exc:
                    state["powerpoint_error"] = str(exc)
                except Exception as exc:
                    state["powerpoint_error"] = f"PowerPoint export failed: {exc}"

    if state.get("excel_bytes"):
        st.download_button(
            label="Download Excel Report",
            data=BytesIO(state["excel_bytes"]),
            file_name=f"{session.project.name}_post_mortem.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if state.get("powerpoint_error"):
        st.error(state["powerpoint_error"])

    if state.get("powerpoint_bytes"):
        st.download_button(
            label="Download PowerPoint Report",
            data=BytesIO(state["powerpoint_bytes"]),
            file_name=f"{session.project.name}_post_mortem.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
