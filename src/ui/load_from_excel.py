from __future__ import annotations

import streamlit as st

from logic.load_project import ExcelProjectLoader, ExcelParameters, DataColumn
from ui.utils.page_header import render_registered_page_header


def default_excel_parameters(start_row: int = 8) -> ExcelParameters:
    return ExcelParameters(
        start_row=start_row,
        columns=[
            DataColumn(name="ACTIVITY", column=2),
            DataColumn(name="PLANNED DURATION (HOURS)", column=3),
            DataColumn(name="PLANNED START", column=4),
            DataColumn(name="PLANNED END", column=5),
            DataColumn(name="ACTUAL DURATION", column=7),
            DataColumn(name="ACTUAL START", column=8),
            DataColumn(name="ACTUAL END", column=9),
            DataColumn(name="NOTES", column=10),
            DataColumn(name="PREDECESSOR", column=11),
            DataColumn(name="UUID", column=12),
            DataColumn(name="PLANNED", column=13),
        ],
    )


def go_to_excel_import() -> None:
    st.switch_page("pages/excel_import.py")


def _render_project_preview(analysis: dict) -> None:
    summary = st.container(border=True)
    with summary:
        top_left, top_right = st.columns([2, 1], vertical_alignment="center")
        with top_left:
            st.subheader(analysis["project_name"])
            st.caption(f"Project type: `{analysis['project_type'].name}`")
            if analysis["project_id"]:
                st.caption(f"Workbook project id: `{analysis['project_id']}`")
        with top_right:
            st.metric("Phases", analysis["phase_count"])
            st.metric("Tasks", analysis["task_count"])

        m1, m2 = st.columns(2)
        with m1:
            st.metric("Rows with provided links", analysis["provided_predecessor_count"])
        with m2:
            st.metric("Task constraint rows inferred", analysis["inferred_predecessor_count"])
        m3, _ = st.columns(2)
        with m3:
            st.metric("Phase constraint rows inferred", analysis["inferred_phase_predecessor_count"])


def render_excel_import_page() -> None:
    render_registered_page_header(
        "excel_import",
        chips=["Workbook preview", "Constraint inference"],
    )

    st.session_state.setdefault("excel_import_start_row", 8)
    st.session_state.setdefault("excel_import_preview_limit", 100)
    st.session_state.setdefault("excel_import_infer_predecessors", True)

    controls = st.container(border=True)
    with controls:
        c1, c2, c3 = st.columns([1, 1, 1], vertical_alignment="bottom")
        with c1:
            start_row = st.number_input(
                "First schedule row",
                min_value=2,
                value=st.session_state["excel_import_start_row"],
                step=1,
                help="Defaults to the first schedule row in the BTA template. Change this to re-scan the workbook preview.",
            )
        with c2:
            preview_limit = st.selectbox(
                "Preview rows",
                options=[25, 50, 100, 200],
                index=[25, 50, 100, 200].index(st.session_state["excel_import_preview_limit"]),
            )
        with c3:
            infer_predecessors = st.toggle(
                "Infer constraints",
                value=st.session_state["excel_import_infer_predecessors"],
                help="When the predecessor column is blank, infer FS, SS, FF, or SF constraints from simple planned start and finish formulas.",
            )

        st.session_state["excel_import_start_row"] = int(start_row)
        st.session_state["excel_import_preview_limit"] = int(preview_limit)
        st.session_state["excel_import_infer_predecessors"] = bool(infer_predecessors)

        uploaded_file = st.file_uploader(
            "Excel workbook",
            type=["xls", "xlsx"],
            help="Select a BTA Excel template file to preview and import.",
        )

    if uploaded_file is None:
        st.info("Upload a workbook to inspect the schedule, project type, shift details, and metadata before import.")
        return

    params = default_excel_parameters(start_row=int(start_row))

    try:
        with st.spinner("Reading workbook preview..."):
            analysis = ExcelProjectLoader.analyze_excel_project(
                uploaded_file,
                params=params,
                infer_predecessors=bool(infer_predecessors),
                preview_limit=int(preview_limit),
            )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Failed to analyze workbook: {exc}")
        return

    _render_project_preview(analysis)

    tabs = st.tabs(
        [
            "Schedule Preview",
            "Project Inputs",
            "Shift Definition",
            "Shift Assignments",
            "Metadata",
        ]
    )

    with tabs[0]:
        st.dataframe(analysis["schedule_preview"], hide_index=True, width="stretch")
        st.caption(
            "Provided IDs stay authoritative. When that column is blank, simple start and finish formulas can infer typed constraints and lag."
        )

    with tabs[1]:
        st.dataframe(analysis["column_mapping"], hide_index=True, width="stretch")
        st.caption(f"Current scan starts on row `{start_row}` in the `{params.sheet_name}` sheet.")

    with tabs[2]:
        st.dataframe(analysis["shift_definition_preview"], hide_index=True, width="stretch")

    with tabs[3]:
        if analysis["shift_assignments_preview"].empty:
            st.info("No shift assignments were found in the workbook.")
        else:
            st.dataframe(analysis["shift_assignments_preview"], hide_index=True, width="stretch")

    with tabs[4]:
        if analysis["metadata_preview"].empty:
            st.info("No project-specific metadata was found for this workbook.")
        else:
            st.dataframe(analysis["metadata_preview"], hide_index=True, width="stretch")

    actions = st.container()
    with actions:
        left, right = st.columns([1, 1], vertical_alignment="center")
        with left:
            if st.button("Back to Home", width="stretch"):
                st.switch_page("pages/home.py")
        with right:
            if st.button("Import Project", type="primary", width="stretch"):
                try:
                    with st.spinner("Importing workbook into GanttBuddy..."):
                        project, metadata = ExcelProjectLoader.load_excel_project(
                            uploaded_file,
                            params=params,
                            infer_predecessors=bool(infer_predecessors),
                        )
                except (FileNotFoundError, ValueError, KeyError) as exc:
                    st.error(str(exc))
                    return
                except Exception as exc:
                    st.error(f"Failed to import workbook: {exc}")
                    return

                st.session_state.session.project = project
                if metadata is not None:
                    st.session_state["reline_metadata"] = metadata
                elif "reline_metadata" in st.session_state:
                    del st.session_state["reline_metadata"]

                st.cache_data.clear()
                st.switch_page("pages/plan.py")
