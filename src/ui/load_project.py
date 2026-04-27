from __future__ import annotations

import datetime as dt
from html import escape
from textwrap import dedent
from zoneinfo import ZoneInfo

import streamlit as st

from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_list import get_projects
from logic.backend.project_permissions import resolve_project_access, store_project_access
from models.plan_state import PlanState
from models.project import Project, ProjectType
from models.project_summary import ProjectSummary
from ui.utils.page_header import render_registered_page_header


def _inject_project_browser_css() -> None:
    st.markdown(
        dedent(
            """
            <style>
            .gb-project-browser-panel {
                position: relative;
                overflow: hidden;
                padding: 1.05rem 1.1rem 1.15rem;
                border-radius: 24px;
                border: 1px solid rgba(15, 23, 42, 0.08);
                background:
                    radial-gradient(circle at top right, rgba(14, 165, 233, 0.1), transparent 30%),
                    linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.94));
                box-shadow: 0 16px 32px rgba(148, 163, 184, 0.1);
            }

            .gb-project-browser-panel.is-filter-panel {
                min-height: 100%;
            }

            .gb-project-browser-stack {
                display: grid;
                gap: 0.9rem;
            }

            .gb-project-browser-panel__eyebrow {
                margin: 0 0 0.4rem;
                color: #0369a1;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            .gb-project-browser-panel__title {
                margin: 0;
                color: #0f172a;
                font-size: 1.05rem;
                font-weight: 700;
            }

            .gb-project-browser-panel__body {
                margin: 0.4rem 0 0.9rem;
                color: #475569;
                font-size: 0.88rem;
                line-height: 1.5;
            }

            .gb-project-detail {
                position: relative;
                overflow: hidden;
                padding: 1.15rem 1.25rem 1.2rem;
                border-radius: 28px;
                border: 1px solid rgba(15, 23, 42, 0.08);
                background:
                    radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 28%),
                    radial-gradient(circle at left center, rgba(15, 118, 110, 0.08), transparent 24%),
                    linear-gradient(180deg, #fbfdff 0%, #f3f7fb 100%);
                box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
            }

            .gb-project-detail__eyebrow {
                margin: 0 0 0.45rem;
                color: #0369a1;
                font-size: 0.74rem;
                font-weight: 800;
                letter-spacing: 0.14em;
                text-transform: uppercase;
            }

            .gb-project-detail__header {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
            }

            .gb-project-detail__heading {
                min-width: 0;
                flex: 1 1 auto;
            }

            .gb-project-detail__meta-rail {
                display: grid;
                grid-template-columns: repeat(2, minmax(9rem, 1fr));
                gap: 0.45rem;
                min-width: min(100%, 18rem);
                flex: 0 0 18rem;
            }

            .gb-project-detail__meta-chip {
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 0.45rem;
                align-items: center;
                padding: 0.38rem 0.52rem;
                border-radius: 14px;
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(148, 163, 184, 0.16);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
            }

            .gb-project-detail__meta-chip[data-tone="status"] {
                background: linear-gradient(180deg, rgba(220, 252, 231, 0.92), rgba(240, 253, 244, 0.98));
                border-color: rgba(34, 197, 94, 0.2);
            }

            .gb-project-detail__meta-chip[data-tone="type"] {
                background: linear-gradient(180deg, rgba(219, 234, 254, 0.92), rgba(239, 246, 255, 0.98));
                border-color: rgba(59, 130, 246, 0.18);
            }

            .gb-project-detail__meta-chip[data-tone="access"] {
                background: linear-gradient(180deg, rgba(254, 243, 199, 0.92), rgba(255, 251, 235, 0.98));
                border-color: rgba(245, 158, 11, 0.2);
            }

            .gb-project-detail__meta-chip[data-tone="site"] {
                background: linear-gradient(180deg, rgba(237, 233, 254, 0.92), rgba(245, 243, 255, 0.98));
                border-color: rgba(139, 92, 246, 0.18);
            }

            .gb-project-detail__meta-icon {
                display: grid;
                place-items: center;
                width: 1.35rem;
                height: 1.35rem;
                border-radius: 999px;
                background: var(--chip-icon-bg, rgba(15, 23, 42, 0.06));
                color: var(--chip-icon-color, #0f172a);
                font-size: 0.7rem;
                font-weight: 800;
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
            }

            .gb-project-detail__meta-copy {
                min-width: 0;
            }

            .gb-project-detail__meta-label {
                margin: 0;
                color: #64748b;
                font-size: 0.54rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                line-height: 1.05;
            }

            .gb-project-detail__meta-value {
                margin: 0.05rem 0 0;
                color: #0f172a;
                font-size: 0.7rem;
                font-weight: 700;
                line-height: 1.1;
            }

            .gb-project-detail__title {
                margin: 0;
                color: #0f172a;
                font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
                font-size: clamp(1.5rem, 2vw, 2.2rem);
                font-weight: 700;
                line-height: 1.02;
                letter-spacing: -0.04em;
            }

            .gb-project-detail__sub {
                margin: 0.45rem 0 0;
                color: #475569;
                font-size: 0.92rem;
                line-height: 1.5;
                max-width: 58rem;
            }

            .gb-project-detail__timeline {
                position: relative;
                margin-top: 0.95rem;
                padding: 1rem 1.05rem 0.95rem;
                border-radius: 22px;
                border: 1px solid rgba(14, 116, 144, 0.12);
                background:
                    radial-gradient(circle at center, rgba(14, 165, 233, 0.08), transparent 42%),
                    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(240, 249, 255, 0.88));
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
            }

            .gb-project-detail__timeline-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.8rem;
                margin-bottom: 0.8rem;
            }

            .gb-project-detail__timeline-eyebrow {
                margin: 0;
                color: #0369a1;
                font-size: 0.66rem;
                font-weight: 800;
                letter-spacing: 0.12em;
                text-transform: uppercase;
            }

            .gb-project-detail__timeline-caption {
                margin: 0.18rem 0 0;
                color: #475569;
                font-size: 0.82rem;
                line-height: 1.4;
            }

            .gb-project-detail__timeline-duration {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                padding: 0.42rem 0.78rem;
                border-radius: 999px;
                background: rgba(14, 165, 233, 0.1);
                border: 1px solid rgba(14, 165, 233, 0.16);
                color: #075985;
                font-size: 0.78rem;
                font-weight: 800;
                white-space: nowrap;
            }

            .gb-project-detail__timeline-grid {
                display: grid;
                grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
                gap: 0.8rem;
                align-items: center;
            }

            .gb-project-detail__timeline-end {
                min-width: 0;
            }

            .gb-project-detail__timeline-end.is-right {
                text-align: right;
            }

            .gb-project-detail__timeline-label {
                margin: 0;
                color: #64748b;
                font-size: 0.64rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .gb-project-detail__timeline-value {
                margin: 0.28rem 0 0;
                color: #0f172a;
                font-size: 0.98rem;
                font-weight: 700;
                line-height: 1.25;
            }

            .gb-project-detail__timeline-support {
                margin: 0.16rem 0 0;
                color: #64748b;
                font-size: 0.76rem;
                line-height: 1.35;
            }

            .gb-project-detail__timeline-arrow {
                position: relative;
                display: grid;
                gap: 0.4rem;
                min-width: 14rem;
                justify-items: center;
            }

            .gb-project-detail__timeline-arrow-line {
                position: relative;
                width: 100%;
                height: 0.3rem;
                border-radius: 999px;
                background: linear-gradient(90deg, #38bdf8 0%, #0ea5e9 52%, #0284c7 100%);
                box-shadow: 0 8px 18px rgba(14, 165, 233, 0.18);
            }

            .gb-project-detail__timeline-arrow-line::after {
                content: "";
                position: absolute;
                right: -0.02rem;
                top: 50%;
                width: 0.82rem;
                height: 0.82rem;
                border-top: 0.22rem solid #0284c7;
                border-right: 0.22rem solid #0284c7;
                transform: translateY(-50%) rotate(45deg);
                border-radius: 0.08rem;
            }

            .gb-project-detail__timeline-arrow-note {
                color: #0369a1;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }

            .gb-project-detail__grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.65rem;
                margin-top: 0.8rem;
            }

            .gb-project-detail__fact {
                padding: 0.72rem 0.8rem;
                border-radius: 18px;
                background: rgba(255, 255, 255, 0.84);
                border: 1px solid rgba(148, 163, 184, 0.16);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
            }

            .gb-project-detail__label {
                margin: 0;
                color: #64748b;
                font-size: 0.69rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }

            .gb-project-detail__value {
                margin: 0.33rem 0 0;
                color: #0f172a;
                font-size: 0.92rem;
                font-weight: 700;
                line-height: 1.4;
            }

            .gb-project-actions {
                margin-top: 0.85rem;
            }

            @media (max-width: 980px) {
                .gb-project-detail__header {
                    display: grid;
                }

                .gb-project-detail__meta-rail {
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    min-width: 0;
                    flex: 1 1 auto;
                }

                .gb-project-detail__timeline-grid {
                    grid-template-columns: 1fr;
                }

                .gb-project-detail__timeline-end.is-right {
                    text-align: left;
                }

                .gb-project-detail__timeline-arrow {
                    min-width: 0;
                    width: 100%;
                }

                .gb-project-detail__grid {
                    grid-template-columns: 1fr;
                }
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def _fmt_dt(value: dt.datetime | None) -> str:
    if value is None:
        return "Not available"
    return value.strftime("%b %d, %Y at %I:%M %p")


def _fmt_compact_dt(value: dt.datetime | None) -> str:
    if value is None:
        return "Not set"
    return value.strftime("%b %d, %Y")


def _fmt_schedule(project: ProjectSummary) -> str:
    if project.planned_start is None or project.planned_finish is None:
        return "Not scheduled yet"
    return (
        f"{project.planned_start.strftime('%b %d, %Y %I:%M %p')} to "
        f"{project.planned_finish.strftime('%b %d, %Y %I:%M %p')}"
    )


def _fmt_timeline_point(value: dt.datetime | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.strftime("%b %d, %Y")


def _fmt_timeline_support(value: dt.datetime | None) -> str:
    if value is None:
        return "Waiting for schedule dates"
    return value.strftime("%I:%M %p")


def _fmt_duration(project: ProjectSummary) -> str:
    if project.planned_start is None or project.planned_finish is None:
        return "Pending schedule"
    duration = project.planned_finish - project.planned_start
    total_hours = max(duration.total_seconds() / 3600, 0)
    total_days = int(total_hours // 24)
    rem_hours = int(round(total_hours % 24))
    if total_days > 0 and rem_hours > 0:
        return f"{total_days}d {rem_hours}h"
    if total_days > 0:
        return f"{total_days} day{'s' if total_days != 1 else ''}"
    return f"{int(round(total_hours))} hour{'s' if int(round(total_hours)) != 1 else ''}"


def _project_type_display(project: ProjectSummary) -> str:
    mapping = {
        "GENERIC": "General schedule",
        "MILL_RELINE": "Mill reline",
        "CRUSHER_REBUILD": "Crusher rebuild",
        "CIVIL": "Civil work",
    }
    raw = (project.project_type or "GENERIC").strip().upper()
    return mapping.get(raw, project.type_label)


def _access_display(project: ProjectSummary) -> str:
    if project.can_edit is True:
        return "Can edit"
    if project.can_view is True:
        return "Read only"
    return "Not provided"


def _meta_chips_markup(project: ProjectSummary) -> str:
    chips = [
        {
            "label": "Status",
            "value": project.status_label,
            "tone": "status",
            "icon": "●",
            "icon_bg": "rgba(34, 197, 94, 0.16)" if not project.closed else "rgba(249, 115, 22, 0.18)",
            "icon_color": "#166534" if not project.closed else "#c2410c",
        },
        {
            "label": "Project Type",
            "value": _project_type_display(project),
            "tone": "type",
            "icon": "≈",
            "icon_bg": "rgba(59, 130, 246, 0.14)",
            "icon_color": "#1d4ed8",
        },
        {
            "label": "Access",
            "value": _access_display(project),
            "tone": "access",
            "icon": "=",
            "icon_bg": "rgba(245, 158, 11, 0.16)",
            "icon_color": "#b45309",
        },
        {
            "label": "Site",
            "value": project.site_code or "Unassigned",
            "tone": "site",
            "icon": "#",
            "icon_bg": "rgba(139, 92, 246, 0.14)",
            "icon_color": "#7c3aed",
        },
    ]
    return "".join(
        (
            f'<div class="gb-project-detail__meta-chip" data-tone="{chip["tone"]}">'
            f'<span class="gb-project-detail__meta-icon" '
            f'style="--chip-icon-bg:{chip["icon_bg"]}; --chip-icon-color:{chip["icon_color"]};">'
            f'{escape(chip["icon"])}</span>'
            '<div class="gb-project-detail__meta-copy">'
            f'<p class="gb-project-detail__meta-label">{escape(chip["label"])}</p>'
            f'<p class="gb-project-detail__meta-value">{escape(chip["value"])}</p>'
            "</div></div>"
        )
        for chip in chips
    )


def _timeline_markup(project: ProjectSummary) -> str:
    return "".join(
        [
            '<section class="gb-project-detail__timeline">',
            '<div class="gb-project-detail__timeline-head">',
            "<div>",
            '<p class="gb-project-detail__timeline-eyebrow">Project Window</p>',
            "</div>",
            f'<span class="gb-project-detail__timeline-duration">{escape(_fmt_duration(project))}</span>',
            "</div>",
            '<div class="gb-project-detail__timeline-grid">',
            '<div class="gb-project-detail__timeline-end">',
            '<p class="gb-project-detail__timeline-label">Planned Start</p>',
            f'<p class="gb-project-detail__timeline-value">{escape(_fmt_timeline_point(project.planned_start))}</p>',
            f'<p class="gb-project-detail__timeline-support">{escape(_fmt_timeline_support(project.planned_start))}</p>',
            "</div>",
            '<div class="gb-project-detail__timeline-arrow">',
            '<span class="gb-project-detail__timeline-arrow-note">Duration Window</span>',
            '<span class="gb-project-detail__timeline-arrow-line"></span>',
            "</div>",
            '<div class="gb-project-detail__timeline-end is-right">',
            '<p class="gb-project-detail__timeline-label">Planned Finish</p>',
            f'<p class="gb-project-detail__timeline-value">{escape(_fmt_timeline_point(project.planned_finish))}</p>',
            f'<p class="gb-project-detail__timeline-support">{escape(_fmt_timeline_support(project.planned_finish))}</p>',
            "</div>",
            "</div>",
            "</section>",
        ]
    )


def _project_count_chips(projects: dict[str, ProjectSummary], include_closed: bool) -> list[str]:
    all_projects = list(projects.values())
    active_count = sum(not project.closed for project in all_projects)
    closed_count = sum(project.closed for project in all_projects)
    scheduled_count = sum(project.is_scheduled for project in all_projects)
    chips = [
        f"{len(all_projects)} accessible",
        f"{active_count} active",
        f"{scheduled_count} scheduled",
    ]
    if include_closed:
        chips.append(f"{closed_count} closed")
    return chips


def _project_sort_options() -> list[str]:
    return [
        "Recently updated",
        "Recently created",
        "Planned start",
        "Name",
    ]


def _sort_projects(projects: list[ProjectSummary], sort_mode: str) -> list[ProjectSummary]:
    if sort_mode == "Recently created":
        return sorted(projects, key=lambda item: item.created, reverse=True)
    if sort_mode == "Planned start":
        return sorted(
            projects,
            key=lambda item: (
                item.planned_start is None,
                item.planned_start or dt.datetime.max.replace(tzinfo=ZoneInfo("UTC")),
                item.updated,
            ),
        )
    if sort_mode == "Name":
        return sorted(projects, key=lambda item: item.name.lower())
    return sorted(projects, key=lambda item: item.updated, reverse=True)


def _detail_markup(project: ProjectSummary) -> str:
    facts = [
        ("Created", _fmt_dt(project.created)),
        ("Last updated", _fmt_dt(project.updated)),
    ]
    fact_markup = "".join(
        (
            '<div class="gb-project-detail__fact">'
            f'<p class="gb-project-detail__label">{escape(label)}</p>'
            f'<p class="gb-project-detail__value">{escape(value)}</p>'
            "</div>"
        )
        for label, value in facts
    )
    description = project.description_text or "No description is available for this project yet."
    timeline_markup = _timeline_markup(project)
    return "".join(
        [
            '<section class="gb-project-detail">',
            '<p class="gb-project-detail__eyebrow">Project Inspector</p>',
            '<div class="gb-project-detail__header">',
            '<div class="gb-project-detail__heading">',
            f'<h2 class="gb-project-detail__title">{escape(project.name)}</h2>',
            "</div>",
            f'<div class="gb-project-detail__meta-rail">{_meta_chips_markup(project)}</div>',
            "</div>",
            f'<p class="gb-project-detail__sub">{escape(description)}</p>',
            timeline_markup,
            f'<div class="gb-project-detail__grid">{fact_markup}</div>',
            "</section>",
        ]
    )


def load_project_into_session(selected_project_id: str, project_summary: ProjectSummary) -> None:
    try:
        proj_snapshot = fetch_project_snapshot(
            project_id=selected_project_id,
            headers=st.session_state.auth_headers,
        )
    except Exception:
        st.error(f"Error loading project *{project_summary.name}*")
        st.stop()

    project, metadata = snapshot_to_project(proj_snapshot)
    st.session_state.session.project = project
    store_project_access(
        resolve_project_access(
            headers=st.session_state.auth_headers,
            project_id=selected_project_id,
            timezone=ZoneInfo(st.context.timezone),
            project_record=project_summary,
        )
    )

    if metadata and project.project_type == ProjectType.MILL_RELINE:
        st.session_state["reline_metadata"] = metadata
    st.session_state["selected_project_id"] = selected_project_id
    st.session_state.plan_state = PlanState(project_id=selected_project_id)
    st.success(f"*{project_summary.name}* loaded successfully.")
    st.cache_data.clear()


def render_project_browser(*, key_prefix: str, full_page: bool = False) -> str | None:
    _inject_project_browser_css()

    projects = get_projects(st.session_state.auth_headers, include_closed=True)

    if full_page:
        render_registered_page_header(
            "projects",
            chips=_project_count_chips(projects, include_closed=True),
        )

    if not projects:
        return None

    top_left, top_right = st.columns([0.9, 1.1], gap="large", vertical_alignment="top")
    with top_left:
        st.space("small")
        with st.popover(f"Filter Projects", icon=":material/filter_list:"):
            query = st.text_input(
                "Search projects",
                value="",
                placeholder="Search by project name, description, site code, or type",
                key=f"{key_prefix}_query",
            )
            sort_mode = st.selectbox(
                "Sort",
                options=_project_sort_options(),
                key=f"{key_prefix}_sort",
            )
            status_scope = st.selectbox(
                "Status",
                options=["All shown", "Active only", "Closed only"],
                key=f"{key_prefix}_status_scope",
            )

    filtered_projects = [project for project in projects.values() if project.matches_query(query)]
    if status_scope == "Active only":
        filtered_projects = [project for project in filtered_projects if not project.closed]
    elif status_scope == "Closed only":
        filtered_projects = [project for project in filtered_projects if project.closed]
    filtered_projects = _sort_projects(filtered_projects, sort_mode)

    selected_key = f"{key_prefix}_selected_project_id"
    if filtered_projects and st.session_state.get(selected_key) not in {project.id for project in filtered_projects}:
        st.session_state[selected_key] = filtered_projects[0].id

    selected_id = st.session_state.get(selected_key)
    selected_project = projects.get(selected_id) if selected_id else None

    if not filtered_projects:
        st.info("No projects match the current filters.")
        return None

    project_options = [project.id for project in filtered_projects]
    if selected_id not in project_options:
        selected_id = project_options[0]
        st.session_state[selected_key] = selected_id
    selected_project = next((project for project in filtered_projects if project.id == selected_id), None)

    with top_right:
        selected_id = st.selectbox(
            "Project",
            options=project_options,
            index=project_options.index(selected_id),
            format_func=lambda project_id: next(
                project.name_line for project in filtered_projects if project.id == project_id
            ),
            key=f"{key_prefix}_selectbox",
            help="Choose a project after filtering the backend list.",
        )
        st.session_state[selected_key] = selected_id
        selected_project = next((project for project in filtered_projects if project.id == selected_id), None)

    if selected_project is None:
        st.info("Pick a project from the list to inspect it before loading.")
        return None

    _, inspector_center, _ = st.columns([0.14, 1.72, 0.14], gap="medium")
    with inspector_center:
        st.markdown(_detail_markup(selected_project), unsafe_allow_html=True)
        access_copy = (
            ":material/check: You can load this project and make edits in the workspace."
            if selected_project.can_edit is True
            else ":material/info: You can load this project, but the workspace may open in read-only mode."
        )
        if selected_project.can_view is False:
            access_copy = ":material/error: This project appears in the list, but the API does not report view access."

        st.write("")
        if st.button(
            "Load project",
            icon=":material/open_in_browser:",
            type="primary",
            width="content",
            key=f"{key_prefix}_load",
        ):
            return selected_project.id
        st.info(access_copy)

    return None


@st.dialog(":material/open_in_browser: Load Saved Project")
def render_load_project() -> Project:
    selected_project_id = render_project_browser(key_prefix="dialog_project_browser")
    if selected_project_id is None:
        projects = get_projects(
            st.session_state.auth_headers,
            include_closed=st.session_state.get("dialog_project_browser_include_closed", False),
        )
        if not projects:
            st.info(":material/info: No accessible projects.")
            st.caption("Create one on the homepage to get started.")
            if st.button("Back", type="primary"):
                st.rerun()
            st.stop()
        st.stop()

    projects = get_projects(
        st.session_state.auth_headers,
        include_closed=st.session_state.get("dialog_project_browser_include_closed", False),
    )
    load_project_into_session(selected_project_id, projects[selected_project_id])
    st.switch_page("pages/plan.py")
