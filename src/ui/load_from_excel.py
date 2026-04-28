from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import streamlit as st

from logic.load_project import ExcelProjectLoader, ExcelParameters, DataColumn
from logic.backend.api_client import fetch_site
from logic.backend.crews.fetch_crews import get_crews
from models.project_type import ProjectType
from models.shift_schedule import ShiftAssignment
from ui.project_metadata import render_reline_metadata_inputs
from ui.shift_config import render_shift_assignment_table
from ui.shift_definition import render_shift_definition
from ui.utils.timezones import label_timezones_relative_to_user
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


def _import_widget_prefix(uploaded_file, analysis: dict) -> str:
    token = hash(
        (
            getattr(uploaded_file, "name", "workbook"),
            getattr(uploaded_file, "size", 0),
            analysis["project_name"],
            analysis["project_id"],
            analysis["task_count"],
            analysis["phase_count"],
        )
    )
    return f"excel_import_{abs(token)}"


def _default_assignment_window(analysis: dict) -> tuple[dt.date, dt.date]:
    preview = analysis["schedule_preview"]
    if preview.empty:
        start = dt.date.today()
        return start, start + dt.timedelta(days=4)

    for value in preview["Planned Start"].tolist():
        if hasattr(value, "date"):
            start = value.date()
            return start, start + dt.timedelta(days=4)

    start = dt.date.today()
    return start, start + dt.timedelta(days=4)


def _mill_reline_inputs_complete(
    metadata,
    shift_definition,
    shift_assignments,
) -> bool:
    return metadata is not None and shift_definition is not None and bool(shift_assignments)


def _default_project_context(analysis: dict) -> tuple[str, str]:
    default_site_id = ""
    metadata = analysis.get("metadata")
    if metadata is not None and getattr(metadata, "site_id", None):
        default_site_id = metadata.site_id

    shift_definition = analysis.get("shift_definition")
    default_timezone = "America/Vancouver"
    if shift_definition is not None and getattr(shift_definition, "timezone", None) is not None:
        default_timezone = str(shift_definition.timezone)

    return default_site_id, default_timezone


def _render_project_context_inputs(
    analysis: dict,
    widget_prefix: str,
) -> tuple[str | None, str]:
    default_site_id, default_timezone = _default_project_context(analysis)
    user_timezone = getattr(st.context, "timezone", "America/Vancouver")
    timezone_options = label_timezones_relative_to_user(user_timezone)
    timezone_names = [name for name, _ in timezone_options]
    timezone_labels = {name: label for name, label in timezone_options}
    if default_timezone not in timezone_names:
        timezone_names.insert(0, default_timezone)
        timezone_labels[default_timezone] = default_timezone

    shell = st.container(border=True)
    with shell:
        st.subheader("Project Context")
        st.caption("Set the site id and timezone that should be stored on the imported project.")

        left, right = st.columns([1, 1], vertical_alignment="bottom")
        with left:
            site_id = st.text_input(
                "Project site ID",
                value=default_site_id,
                placeholder="site-123",
                key=f"{widget_prefix}_project_site_id",
            ).strip()
        with right:
            timezone_name = st.selectbox(
                "Project timezone",
                options=timezone_names,
                index=timezone_names.index(default_timezone),
                format_func=lambda name: timezone_labels[name],
                key=f"{widget_prefix}_project_timezone",
            )

        if site_id:
            st.caption(f"Imported project will use site id `{site_id}`.")

    return site_id or None, timezone_name


def _render_mill_reline_inputs(analysis: dict, widget_prefix: str) -> tuple[object, object, list[object]]:
    resolved_metadata = analysis["metadata"]
    resolved_shift_definition = analysis["shift_definition"]
    resolved_shift_assignments = analysis["shift_assignments"]

    shell = st.container(border=True)
    with shell:
        if analysis["input_issues"]:
            st.warning("Some mill reline inputs were missing or invalid in the workbook. Review and confirm them below before import.")
            for issue in analysis["input_issues"]:
                st.caption(f"- {issue}")
        elif analysis["is_new_project"]:
            st.info("This workbook looks like a new mill reline project. Confirm the project setup, shift definition, and crew assignments before import.")

        metadata = render_reline_metadata_inputs(
            existing=analysis["metadata"],
            template_version=getattr(analysis["metadata"], "template_version", None),
            title="Project Setup (Mill Reline)",
            require_submit=False,
            state_key=f"{widget_prefix}_metadata_state",
            key_prefix=f"{widget_prefix}_metadata",
        )
        if metadata is not None:
            resolved_metadata = metadata

        site_tz = "America/Vancouver"
        crews = []
        if resolved_metadata is not None and resolved_metadata.site_id:
            headers = st.session_state.get("auth_headers", {})
            try:
                site = fetch_site(headers=headers, site_id=resolved_metadata.site_id)
                site_tz = site.get("timezone") or site_tz
            except Exception as exc:
                st.warning(f"Unable to read site timezone from the backend: {exc}")

            try:
                crews = get_crews(headers=headers, site_id=resolved_metadata.site_id)
            except Exception as exc:
                st.warning(f"Unable to load crews for the selected site: {exc}")

        st.divider()
        resolved_shift_definition = render_shift_definition(
            project_id=analysis["project_id"] or "new-project",
            current_tz=site_tz,
            existing=analysis["shift_definition"],
            key_prefix=f"{widget_prefix}_shift_definition",
        )

        default_start, default_end = _default_assignment_window(analysis)
        edited_assignments = render_shift_assignment_table(
            crews,
            project_id=analysis["project_id"] or "new-project",
            initial_assignments=analysis["shift_assignments"],
            default_start_date=default_start,
            default_end_date=default_end,
            key=f"{widget_prefix}_shift_assignments",
        )
        if edited_assignments is not None:
            resolved_shift_assignments = ShiftAssignment.from_df(
                edited_assignments,
                project_id=analysis["project_id"] or "new-project",
            )

    return resolved_metadata, resolved_shift_definition, resolved_shift_assignments


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

    widget_prefix = _import_widget_prefix(uploaded_file, analysis)
    resolved_metadata = analysis["metadata"]
    resolved_shift_definition = analysis["shift_definition"]
    resolved_shift_assignments = analysis["shift_assignments"]
    resolved_site_id, resolved_timezone_name = _render_project_context_inputs(
        analysis,
        widget_prefix,
    )

    if analysis["project_type"] == ProjectType.MILL_RELINE and analysis["requires_mill_reline_inputs"]:
        resolved_metadata, resolved_shift_definition, resolved_shift_assignments = _render_mill_reline_inputs(
            analysis,
            widget_prefix,
        )
        if resolved_metadata is not None and not resolved_site_id:
            resolved_site_id = resolved_metadata.site_id
        if not _mill_reline_inputs_complete(
            resolved_metadata,
            resolved_shift_definition,
            resolved_shift_assignments,
        ):
            st.info("Finish the required mill reline inputs above to unlock the workbook preview and import action.")
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

    if analysis["project_type"] == ProjectType.MILL_RELINE and not analysis["requires_mill_reline_inputs"]:
        resolved_metadata, resolved_shift_definition, resolved_shift_assignments = _render_mill_reline_inputs(
            analysis,
            widget_prefix,
        )
        if resolved_metadata is not None and not resolved_site_id:
            resolved_site_id = resolved_metadata.site_id

    actions = st.container()
    with actions:
        left, right = st.columns([1, 1], vertical_alignment="center")
        with left:
            if st.button("Back to Home", width="stretch"):
                st.switch_page("pages/home.py")
        with right:
            if st.button("Import Project", type="primary", width="stretch"):
                if analysis["project_type"] == ProjectType.MILL_RELINE:
                    if resolved_metadata is None:
                        st.error("Mill reline imports need project setup details before they can be loaded.")
                        return
                    if resolved_shift_definition is None:
                        st.error("Mill reline imports need a valid shift definition before they can be loaded.")
                        return
                    if not resolved_shift_assignments:
                        st.error("Mill reline imports need at least one shift assignment before they can be loaded.")
                        return

                try:
                    with st.spinner("Importing workbook into GanttBuddy..."):
                        project, metadata = ExcelProjectLoader.load_excel_project(
                            uploaded_file,
                            params=params,
                            infer_predecessors=bool(infer_predecessors),
                            metadata_override=resolved_metadata,
                            shift_definition_override=resolved_shift_definition,
                            shift_assignments_override=resolved_shift_assignments,
                            site_id_override=resolved_site_id,
                            timezone_override=ZoneInfo(resolved_timezone_name),
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
