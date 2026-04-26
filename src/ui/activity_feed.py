from __future__ import annotations

import datetime as dt
from html import escape
from textwrap import dedent
from typing import Callable, Optional

import streamlit as st

from models.event import EventIn
from ui.utils.status_badges import STATUS_BADGES

OpenProjectCallback = Callable[[str], None]

TASK_EXECUTION_EVENT_TYPES = {"STARTED", "FINISHED", "NOTE", "STATUS", "EDITED_ACTUALS"}


def inject_activity_feed_css() -> None:
    st.markdown(
        dedent(
            """
            <style>
            .gb-activity-shell {
                position: relative;
                overflow: hidden;
                padding: 1.15rem;
                border-radius: 26px;
                border: 1px solid rgba(15, 23, 42, 0.08);
                background:
                    radial-gradient(circle at top right, rgba(14, 165, 233, 0.14), transparent 28%),
                    radial-gradient(circle at left center, rgba(15, 118, 110, 0.10), transparent 22%),
                    linear-gradient(180deg, #fbfdff 0%, #f3f7fb 100%);
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
            }

            .gb-activity-shell--feed {
                padding: 1.05rem;
                border-radius: 24px;
            }

            .gb-activity-header {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 0.85rem;
                margin-bottom: 0.95rem;
            }

            .gb-activity-title {
                margin: 0;
                font-size: 1.05rem;
                font-weight: 700;
                color: #0f172a;
            }

            .gb-activity-eyebrow {
                margin: 0 0 0.2rem;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: #0369a1;
            }

            .gb-activity-subtitle {
                margin: 0;
                font-size: 0.9rem;
                color: #475569;
            }

            .gb-activity-stats {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                justify-content: flex-start;
            }

            .gb-activity-stat {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.42rem 0.72rem;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.78);
                border: 1px solid rgba(148, 163, 184, 0.24);
                color: #0f172a;
                font-size: 0.76rem;
                font-weight: 700;
            }

            .gb-activity-stat strong {
                font-size: 0.9rem;
            }

            .gb-activity-list {
                display: grid;
                gap: 0.78rem;
                margin-top: 0.9rem;
            }

            .gb-activity-item {
                display: grid;
                grid-template-columns: auto 1fr auto;
                gap: 0.8rem;
                align-items: start;
                padding: 1rem;
                border-radius: 22px;
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid rgba(148, 163, 184, 0.18);
                box-shadow: 0 10px 26px rgba(148, 163, 184, 0.08);
                transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
            }

            .gb-activity-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 18px 34px rgba(148, 163, 184, 0.14);
                border-color: rgba(51, 65, 85, 0.18);
            }

            .gb-activity-item--unread {
                border-color: color-mix(in srgb, var(--activity-accent) 32%, white);
                box-shadow:
                    0 18px 34px rgba(148, 163, 184, 0.12),
                    0 0 0 1px color-mix(in srgb, var(--activity-accent) 22%, white);
            }

            .gb-activity-icon {
                display: grid;
                place-items: center;
                width: 2.6rem;
                height: 2.6rem;
                border-radius: 18px;
                background: var(--activity-soft);
                color: var(--activity-accent);
                font-size: 1.1rem;
                box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.65);
            }

            .gb-activity-main {
                min-width: 0;
                display: grid;
                gap: 0.6rem;
            }

            .gb-activity-meta {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 0.45rem;
            }

            .gb-activity-chip {
                display: inline-flex;
                align-items: center;
                gap: 0.32rem;
                padding: 0.28rem 0.62rem;
                border-radius: 999px;
                background: var(--activity-soft);
                color: var(--activity-accent);
                font-size: 0.72rem;
                font-weight: 700;
                line-height: 1;
            }

            .gb-activity-chip--read {
                background: rgba(226, 232, 240, 0.82);
                color: #475569;
            }

            .gb-activity-chip--unread {
                background: color-mix(in srgb, var(--activity-accent) 16%, white);
                color: var(--activity-accent);
                box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--activity-accent) 18%, white);
            }

            .gb-activity-headline {
                margin: 0;
                color: #0f172a;
                font-size: 1rem;
                line-height: 1.3;
                font-weight: 700;
            }

            .gb-activity-summary {
                margin: 0;
                color: #475569;
                font-size: 0.88rem;
                line-height: 1.5;
            }

            .gb-activity-context {
                display: flex;
                flex-wrap: wrap;
                gap: 0.6rem;
                align-items: flex-start;
            }

            .gb-activity-fact {
                display: inline-grid;
                grid-auto-rows: min-content;
                padding: 0.72rem 0.8rem;
                border-radius: 16px;
                border: 1px solid rgba(148, 163, 184, 0.18);
                background: linear-gradient(180deg, rgba(248, 250, 252, 0.94), rgba(241, 245, 249, 0.82));
                width: fit-content;
                max-width: min(100%, 22rem);
            }

            .gb-activity-fact--project {
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.06), rgba(30, 41, 59, 0.02));
            }

            .gb-activity-fact--status {
                background: linear-gradient(
                    135deg,
                    var(--status-soft, rgba(71, 85, 105, 0.12)),
                    rgba(255, 255, 255, 0.92)
                );
                border-color: color-mix(in srgb, var(--status-accent, #475569) 18%, white);
                box-shadow:
                    inset 0 1px 0 rgba(255, 255, 255, 0.72),
                    0 10px 22px color-mix(in srgb, var(--status-accent, #475569) 10%, transparent);
            }

            .gb-activity-fact__label {
                display: block;
                margin-bottom: 0.25rem;
                font-size: 0.68rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #64748b;
            }

            .gb-activity-fact__value {
                display: block;
                color: var(--status-accent, #0f172a);
                font-size: 0.92rem;
                font-weight: 700;
                line-height: 1.3;
            }

            .gb-activity-fact__status-badge {
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                padding: 0.35rem 0.62rem;
                border-radius: 999px;
                background: color-mix(in srgb, var(--status-accent, #475569) 10%, white);
                box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--status-accent, #475569) 12%, white);
                width: fit-content;
            }

            .gb-activity-fact__status-icon {
                display: inline-grid;
                place-items: center;
                width: 1.25rem;
                height: 1.25rem;
                border-radius: 999px;
                background: var(--status-accent, #475569);
                color: white;
                font-size: 0.74rem;
                line-height: 1;
                font-weight: 900;
                flex: 0 0 auto;
            }

            .gb-activity-fact--project .gb-activity-fact__value,
            .gb-activity-fact--default .gb-activity-fact__value {
                color: #0f172a;
            }

            .gb-activity-side {
                display: grid;
                justify-items: end;
                gap: 0.45rem;
                min-width: 5.5rem;
            }

            .gb-activity-avatar {
                display: grid;
                place-items: center;
                width: 2rem;
                height: 2rem;
                border-radius: 999px;
                background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
                color: #f8fafc;
                font-size: 0.72rem;
                font-weight: 800;
                letter-spacing: 0.04em;
            }

            .gb-activity-time {
                text-align: right;
                color: #475569;
                font-size: 0.72rem;
                line-height: 1.35;
            }

            .gb-activity-actions {
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
                margin-top: 0.15rem;
            }

            .gb-activity-day {
                margin: 1rem 0 0.55rem;
            }

            .gb-activity-day__label {
                margin: 0;
                font-size: 0.84rem;
                font-weight: 800;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #0f172a;
            }

            .gb-activity-day__meta {
                margin: 0.15rem 0 0;
                font-size: 0.8rem;
                color: #64748b;
            }

            @media (max-width: 900px) {
                .gb-activity-header {
                    align-items: flex-start;
                }

                .gb-activity-stats {
                    width: 100%;
                }

                .gb-activity-item {
                    grid-template-columns: auto 1fr;
                }

                .gb-activity-side {
                    grid-column: 2;
                    justify-items: start;
                    grid-auto-flow: column;
                    align-items: center;
                }

                .gb-activity-context {
                    display: grid;
                    grid-template-columns: 1fr;
                }

                .gb-activity-time {
                    text-align: left;
                }
            }
            </style>
            """
        ),
        unsafe_allow_html=True,
    )


def render_recent_activity_preview(activity: list[EventIn]) -> None:
    render_activity_collection(
        activity,
        shell_variant="preview",
        eyebrow="Recent Activity",
        title="Project pulse across the workspace",
        subtitle="Keep up to date with your team's latest activity.",
        read_event_ids=None,
        show_day_groups=False,
        card_key_prefix="home_recent_activity",
        show_custom_header=True
    )


def render_activity_collection(
    events: list[EventIn],
    *,
    shell_variant: str = "feed",
    eyebrow: str = "Feed",
    title: str,
    subtitle: str,
    read_event_ids: Optional[set[str]] = None,
    show_day_groups: bool = True,
    card_key_prefix: str = "activity",
    on_open_project: Optional[OpenProjectCallback] = None,
    allow_read_toggle: bool = False,
    show_custom_header: bool = False,
) -> None:
    unique_projects = len({item.project_id for item in events})
    active_people = len({item.user_id for item in events})
    shell_class = "gb-activity-shell gb-activity-shell--feed" if shell_variant == "feed" else "gb-activity-shell"

    st.markdown(f'<div class="{shell_class}">', unsafe_allow_html=True)

    if show_custom_header:
        st.markdown(
            (
                f'<div class="gb-activity-header">'
                f'<div>'
                f'<p class="gb-activity-eyebrow">{escape(eyebrow)}</p>'
                f'<h3 class="gb-activity-title">{escape(title)}</h3>'
                f'<p class="gb-activity-subtitle">{escape(subtitle)}</p>'
                f"</div>"
                f'<div class="gb-activity-stats">'
                f'<span class="gb-activity-stat"><strong>{len(events)}</strong> events</span>'
                f'<span class="gb-activity-stat"><strong>{unique_projects}</strong> projects</span>'
                f'<span class="gb-activity-stat"><strong>{active_people}</strong> contributors</span>'
                f"</div>"
                f"</div>"
            ),
            unsafe_allow_html=True,
        )

    if show_day_groups:
        now = dt.datetime.now(events[0].ts.tzinfo) if events else dt.datetime.now()
        for index, (day, day_events) in enumerate(_group_events_by_day(events).items()):
            label, meta = _format_day_label(day, len(day_events), now=now)
            st.markdown(
                (
                    '<div class="gb-activity-day">'
                    f'<p class="gb-activity-day__label">{escape(label)}</p>'
                    f'<p class="gb-activity-day__meta">{escape(meta)}</p>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            _render_activity_list(
                day_events,
                read_event_ids=read_event_ids,
                card_key_prefix=f"{card_key_prefix}_{index}",
                on_open_project=on_open_project,
                allow_read_toggle=allow_read_toggle,
            )
    else:
        _render_activity_list(
            events,
            read_event_ids=read_event_ids,
            card_key_prefix=card_key_prefix,
            on_open_project=on_open_project,
            allow_read_toggle=allow_read_toggle,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_activity_list(
    events: list[EventIn],
    *,
    read_event_ids: Optional[set[str]],
    card_key_prefix: str,
    on_open_project: Optional[OpenProjectCallback],
    allow_read_toggle: bool,
) -> None:
    st.markdown('<div class="gb-activity-list">', unsafe_allow_html=True)
    now = dt.datetime.now(dt.timezone.utc).astimezone(events[0].ts.tzinfo if events else None)
    show_read_state = read_event_ids is not None

    for index, item in enumerate(events):
        is_read = False if read_event_ids is None else item.id in read_event_ids
        card_id = f"{card_key_prefix}_{index}_{item.id}"
        _render_activity_card(
            item,
            now=now,
            is_read=is_read,
            show_read_state=show_read_state,
            card_id=card_id,
            on_open_project=on_open_project,
            allow_read_toggle=allow_read_toggle,
        )
        st.write("")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_activity_card(
    item: EventIn,
    *,
    now: dt.datetime,
    is_read: bool,
    show_read_state: bool,
    card_id: str,
    on_open_project: Optional[OpenProjectCallback],
    allow_read_toggle: bool,
) -> None:
    visuals = _event_visuals(item.event_type)
    context_markup = _context_markup(item)
    unread_class = "" if is_read else " gb-activity-item--unread"
    unread_chip_markup = ""
    if show_read_state:
        unread_label = "Read" if is_read else "Unread"
        unread_chip_class = "gb-activity-chip gb-activity-chip--read" if is_read else "gb-activity-chip gb-activity-chip--unread"
        unread_chip_markup = f'<span class="{unread_chip_class}">{escape(unread_label)}</span>'

    if on_open_project or allow_read_toggle:
        content_col, action_col = st.columns([6.4, 1.0], gap="small")
        with content_col:
            st.markdown(
                (
                    f'<div class="gb-activity-item{unread_class}" style="--activity-accent:{visuals["accent"]}; --activity-soft:{visuals["soft"]};">'
                    f'<div class="gb-activity-icon">{visuals["icon"]}</div>'
                    f'<div class="gb-activity-main">'
                    f'<div class="gb-activity-meta">'
                    f'<span class="gb-activity-chip">{escape(visuals["label"])}</span>'
                    f"{unread_chip_markup}"
                    f"</div>"
                    f'<p class="gb-activity-headline">{escape(_headline(item))}</p>'
                    f'<p class="gb-activity-summary">{escape(_summary(item))}</p>'
                    f'<div class="gb-activity-context">{context_markup}</div>'
                    f"</div>"
                    f'<div class="gb-activity-side">'
                    f'<div class="gb-activity-avatar">{escape(_actor_initials(item.user_name))}</div>'
                    f'<div class="gb-activity-time">{escape(_relative_time(item.ts, now))}<br>{escape(item.ts.strftime("%b %d, %I:%M %p"))}</div>'
                    f"</div>"
                    f"</div>"
                ),
                unsafe_allow_html=True,
            )
        with action_col:
            if on_open_project is not None:
                if st.button(
                    "Open",
                    icon=":material/open_in_new:",
                    key=f"{card_id}_open",
                    width="stretch",
                    type="primary" if not is_read else "secondary",
                ):
                    on_open_project(item.project_id)
                    if "feed_read_event_ids" in st.session_state:
                        st.session_state.feed_read_event_ids.add(item.id)
            if allow_read_toggle:
                button_label = "Mark unread" if is_read else "Mark read"
                button_icon = ":material/mark_email_unread:" if is_read else ":material/done:"
                if st.button(
                    button_label,
                    icon=button_icon,
                    key=f"{card_id}_read_toggle",
                    width="stretch",
                ):
                    if "feed_read_event_ids" in st.session_state:
                        if is_read:
                            st.session_state.feed_read_event_ids.discard(item.id)
                        else:
                            st.session_state.feed_read_event_ids.add(item.id)
                    st.rerun()
        return

    st.markdown(
        (
            f'<div class="gb-activity-item{unread_class}" style="--activity-accent:{visuals["accent"]}; --activity-soft:{visuals["soft"]};">'
            f'<div class="gb-activity-icon">{visuals["icon"]}</div>'
            f'<div class="gb-activity-main">'
            f'<div class="gb-activity-meta">'
            f'<span class="gb-activity-chip">{escape(visuals["label"])}</span>'
            f"{unread_chip_markup}"
            f"</div>"
            f'<p class="gb-activity-headline">{escape(_headline(item))}</p>'
            f'<p class="gb-activity-summary">{escape(_summary(item))}</p>'
            f'<div class="gb-activity-context">{context_markup}</div>'
            f"</div>"
            f'<div class="gb-activity-side">'
            f'<div class="gb-activity-avatar">{escape(_actor_initials(item.user_name))}</div>'
            f'<div class="gb-activity-time">{escape(_relative_time(item.ts, now))}<br>{escape(item.ts.strftime("%b %d, %I:%M %p"))}</div>'
            f"</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


def _group_events_by_day(events: list[EventIn]) -> dict[dt.date, list[EventIn]]:
    groups: dict[dt.date, list[EventIn]] = {}
    for item in events:
        groups.setdefault(item.ts.date(), []).append(item)
    return dict(sorted(groups.items(), key=lambda kv: kv[0], reverse=True))


def _format_day_label(day: dt.date, count: int, *, now: dt.datetime) -> tuple[str, str]:
    today = now.date()
    if day == today:
        label = "Today"
    elif day == today - dt.timedelta(days=1):
        label = "Yesterday"
    else:
        label = day.strftime("%A, %b %d")
    meta = f"{count} event{'s' if count != 1 else ''}"
    return label, meta


def _relative_time(value: dt.datetime, now: dt.datetime) -> str:
    delta = now - value
    if delta < dt.timedelta(minutes=1):
        return "Just now"
    if delta < dt.timedelta(hours=1):
        minutes = max(int(delta.total_seconds() // 60), 1)
        return f"{minutes}m ago"
    if delta < dt.timedelta(days=1):
        hours = max(int(delta.total_seconds() // 3600), 1)
        return f"{hours}h ago"
    if delta < dt.timedelta(days=7):
        return f"{delta.days}d ago"
    return value.strftime("%b %d")


def _payload_dict(item: EventIn) -> dict:
    return item.payload if isinstance(item.payload, dict) else {}


def _field_changes(item: EventIn) -> dict[str, dict]:
    payload = _payload_dict(item)
    field_changes = payload.get("field_changes", {})
    return field_changes if isinstance(field_changes, dict) else {}


def _format_field_name(name: str) -> str:
    return name.replace("_", " ").strip()


def _format_field_list(names: list[str], *, limit: int = 3) -> str:
    pretty = [_format_field_name(name) for name in names if name]
    if not pretty:
        return "details"
    if len(pretty) == 1:
        return pretty[0]
    if len(pretty) == 2:
        return f"{pretty[0]} and {pretty[1]}"
    visible = pretty[:limit]
    remaining = len(pretty) - len(visible)
    if remaining <= 0:
        return f"{', '.join(visible[:-1])}, and {visible[-1]}"
    return f"{', '.join(visible)}, and {remaining} more"


def _headline(item: EventIn) -> str:
    user_name = item.user_name or "Someone"

    headline_map = {
        "PROJECT_CREATED": f"{user_name} created a new project",
        "PROJECT_UPDATED": f"{user_name} updated the project",
        "PROJECT_SETTINGS_CREATED": f"{user_name} added project settings",
        "PROJECT_SETTINGS_UPDATED": f"{user_name} changed project settings",
        "PROJECT_METADATA_UPDATED": f"{user_name} refreshed project metadata",
        "PROJECT_SHIFT_DEFINITION_UPDATED": f"{user_name} updated shift definitions",
        "PROJECT_SHIFT_ASSIGNMENTS_UPDATED": f"{user_name} updated shift assignments",
        "PHASE_CREATED": f"{user_name} added a phase",
        "PHASE_UPDATED": f"{user_name} updated a phase",
        "PHASE_UNDELETED": f"{user_name} restored a phase",
        "PHASE_DELETED": f"{user_name} removed a phase",
        "TASK_CREATED": f"{user_name} added a task",
        "TASK_UPDATED": f"{user_name} updated a task",
        "TASK_ACTUALS_UPDATED": f"{user_name} updated task actuals",
        "TASK_UNDELETED": f"{user_name} restored a task",
        "TASK_DELETED": f"{user_name} removed a task",
        "STARTED": f"{user_name} started work on a task",
        "FINISHED": f"{user_name} finished a task",
        "NOTE": f"{user_name} added a task note",
        "STATUS": f"{user_name} changed task status",
        "EDITED_ACTUALS": f"{user_name} edited task actuals",
        "PROJECT_CLOSED": f"{user_name} closed the project",
    }
    return headline_map.get(item.event_type, f"{user_name} recorded activity")


def _summary(item: EventIn) -> str:
    payload = _payload_dict(item)
    field_changes = _field_changes(item)

    if item.event_type == "PROJECT_CREATED":
        project_type = str(payload.get("project_type", "")).replace("_", " ").strip().lower()
        if project_type:
            return f"Started a {project_type} workspace."
        return "Started a new workspace."

    if item.event_type == "PROJECT_UPDATED":
        return f"Changed {_format_field_list(list(field_changes.keys()))}." if field_changes else "Updated project details."

    if item.event_type == "PROJECT_SETTINGS_CREATED":
        keys = payload.get("keys", [])
        if isinstance(keys, list) and keys:
            return f"Configured {_format_field_list([str(key) for key in keys])}."
        return "Configured project settings."

    if item.event_type == "PROJECT_SETTINGS_UPDATED":
        return f"Adjusted {_format_field_list(list(field_changes.keys()))}." if field_changes else "Adjusted project settings."

    if item.event_type == "PROJECT_METADATA_UPDATED":
        return "Refreshed the metadata record for this project."

    if item.event_type == "PROJECT_SHIFT_DEFINITION_UPDATED":
        return "Updated the shift definition used to plan the schedule."

    if item.event_type == "PROJECT_SHIFT_ASSIGNMENTS_UPDATED":
        if isinstance(item.payload, list):
            return f"Synced {len(item.payload)} shift assignment{'s' if len(item.payload) != 1 else ''}."
        return "Synced shift assignments for the project."

    if item.event_type == "PHASE_CREATED":
        position = payload.get("position")
        name = item.phase_name or str(payload.get("name") or "Unnamed phase")
        if isinstance(position, int):
            return f"Added {name} as phase {position + 1}."
        return f"Added {name} to the plan."

    if item.event_type == "PHASE_UPDATED":
        return f"Changed {_format_field_list(list(field_changes.keys()))}." if field_changes else f"Updated {item.phase_name or 'the phase'}."

    if item.event_type == "PHASE_UNDELETED":
        return "Returned the phase to the active plan."

    if item.event_type == "PHASE_DELETED":
        return "Removed the phase from the active import."

    if item.event_type == "TASK_CREATED":
        status = item.get_task_status()
        if status in STATUS_BADGES:
            return f"Created {item.task_name or 'the task'} with status {_status_label(status)}."
        return f"Created {item.task_name or 'a new task'}."

    if item.event_type == "TASK_UPDATED":
        return f"Changed {_format_field_list(list(field_changes.keys()))}." if field_changes else f"Updated {item.task_name or 'the task'}."

    if item.event_type == "TASK_ACTUALS_UPDATED":
        return _actuals_summary(field_changes) or "Updated task actuals."

    if item.event_type == "TASK_UNDELETED":
        return "Returned the task to the active plan."

    if item.event_type == "TASK_DELETED":
        return "Removed the task from the active import."

    if item.event_type == "STARTED":
        return "Captured an actual start and moved the task into progress."

    if item.event_type == "FINISHED":
        return "Marked the task complete and captured the finish time."

    if item.event_type == "NOTE":
        note = str(payload.get("note") or "").strip()
        if note:
            return _truncate(note, 120)
        return "Added a note to the task."

    if item.event_type == "STATUS":
        status = str(payload.get("status") or "").strip()
        if status in STATUS_BADGES:
            return f"Moved the task to {_status_label(status)}."
        return "Changed the task status."

    if item.event_type == "EDITED_ACTUALS":
        reason = str(payload.get("reason") or "").strip()
        summary = _actuals_summary(payload.get("new", {}), payload.get("old", {}))
        if summary and reason:
            return f"{summary} Reason: {_truncate(reason, 80)}"
        if summary:
            return summary
        return "Edited the task's actual dates."

    if item.event_type == "PROJECT_CLOSED":
        return "Completed project closeout."

    fallback = item.message.strip()
    return fallback if fallback else "Recorded activity on the project."


def _actuals_summary(current: dict, previous: Optional[dict] = None) -> str:
    if not isinstance(current, dict):
        return ""

    if previous is not None:
        start = current.get("actual_start")
        end = current.get("actual_end")
        parts = []
        if start is not None:
            parts.append("actual start")
        if end is not None:
            parts.append("actual finish")
        if parts:
            return f"Updated {_format_field_list(parts, limit=2)}."
        return ""

    fields = []
    for field_name, change in current.items():
        if isinstance(change, dict) and change.get("to") is not None:
            fields.append(field_name)
    if fields:
        return f"Updated {_format_field_list(fields, limit=2)}."
    return ""


def _context_markup(item: EventIn) -> str:
    parts = []
    for fact in _context_items(item):
        tone = fact.get("tone", "default")
        style = ""
        if tone == "status":
            style = (
                f' style="--status-accent:{fact.get("accent", "#475569")};'
                f' --status-soft:{fact.get("soft", "rgba(71, 85, 105, 0.12)")};"'
            )
        value_markup = (
            f'<span class="gb-activity-fact__value gb-activity-fact__status-badge">'
            f'<span class="gb-activity-fact__status-icon">{fact.get("icon", "&#8226;")}</span>'
            f'<span>{escape(str(fact["value"]))}</span>'
            f"</span>"
            if tone == "status"
            else f'<span class="gb-activity-fact__value">{escape(str(fact["value"]))}</span>'
        )
        parts.append(
            f'<div class="gb-activity-fact gb-activity-fact--{escape(tone)}"{style}>'
            f'<span class="gb-activity-fact__label">{escape(str(fact["label"]))}</span>'
            f"{value_markup}"
            f"</div>"
        )
    return "".join(parts)


def _context_items(item: EventIn) -> list[dict[str, str]]:
    items: list[dict[str, str]] = [
        {"label": "Project", "value": item.project_name or "Unknown project", "tone": "project"}
    ]

    if item.task_name:
        items.append({"label": "Task", "value": item.task_name, "tone": "default"})
    elif item.phase_name:
        items.append({"label": "Phase", "value": item.phase_name, "tone": "default"})

    status_theme = _status_theme(item)
    if status_theme is not None:
        items.append(
            {
                "label": "Status",
                "value": status_theme["label"],
                "tone": "status",
                "icon": status_theme["icon"],
                "accent": status_theme["accent"],
                "soft": status_theme["soft"],
            }
        )

    return items[:3]


def _status_theme(item: EventIn) -> Optional[dict[str, str]]:
    status = item.get_task_status()
    if not status:
        return None

    label, icon, tone_name = STATUS_BADGES.get(status, ("Unknown", "", "gray"))
    tone_map = {
        "gray": ("#475569", "rgba(71, 85, 105, 0.12)"),
        "blue": ("#2563eb", "rgba(37, 99, 235, 0.12)"),
        "green": ("#15803d", "rgba(21, 128, 61, 0.12)"),
        "red": ("#b91c1c", "rgba(185, 28, 28, 0.12)"),
    }
    icon_map = {
        ":material/schedule:": "&#9683;",
        ":material/autorenew:": "&#8635;",
        ":material/check_circle:": "&#10003;",
        ":material/block:": "&#9940;",
    }
    accent, soft = tone_map.get(tone_name, ("#475569", "rgba(71, 85, 105, 0.12)"))
    return {"label": label, "icon": icon_map.get(icon, "&#8226;"), "accent": accent, "soft": soft}


def _status_label(status: str) -> str:
    return STATUS_BADGES.get(status, (status.replace("_", " ").title(), "", ""))[0]


def _actor_initials(user_name: str) -> str:
    parts = [part for part in user_name.split() if part]
    if not parts:
        return "GB"
    return "".join(part[0] for part in parts[:2]).upper()


def _truncate(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _event_visuals(event_type: str) -> dict[str, str]:
    event_map = {
        "PROJECT_CREATED": {"icon": "&#10024;", "label": "Project created", "accent": "#2563eb", "soft": "rgba(37, 99, 235, 0.14)"},
        "PROJECT_UPDATED": {"icon": "&#128736;", "label": "Project updated", "accent": "#0f766e", "soft": "rgba(15, 118, 110, 0.14)"},
        "PROJECT_METADATA_UPDATED": {"icon": "&#128221;", "label": "Metadata updated", "accent": "#4f46e5", "soft": "rgba(79, 70, 229, 0.14)"},
        "PROJECT_SETTINGS_CREATED": {"icon": "&#9874;", "label": "Settings created", "accent": "#0d9488", "soft": "rgba(13, 148, 136, 0.14)"},
        "PROJECT_SETTINGS_UPDATED": {"icon": "&#9881;", "label": "Settings changed", "accent": "#7c3aed", "soft": "rgba(124, 58, 237, 0.14)"},
        "PROJECT_SHIFT_DEFINITION_UPDATED": {"icon": "&#9200;", "label": "Shift definition", "accent": "#0f766e", "soft": "rgba(15, 118, 110, 0.14)"},
        "PROJECT_SHIFT_ASSIGNMENTS_UPDATED": {"icon": "&#128197;", "label": "Shift assignments", "accent": "#0891b2", "soft": "rgba(8, 145, 178, 0.14)"},
        "TASK_CREATED": {"icon": "&#10133;", "label": "Task created", "accent": "#0891b2", "soft": "rgba(8, 145, 178, 0.14)"},
        "TASK_UPDATED": {"icon": "&#9998;", "label": "Task updated", "accent": "#d97706", "soft": "rgba(217, 119, 6, 0.14)"},
        "TASK_ACTUALS_UPDATED": {"icon": "&#9201;", "label": "Actuals updated", "accent": "#ea580c", "soft": "rgba(234, 88, 12, 0.14)"},
        "TASK_UNDELETED": {"icon": "&#8635;", "label": "Task restored", "accent": "#2563eb", "soft": "rgba(37, 99, 235, 0.14)"},
        "TASK_DELETED": {"icon": "&#8722;", "label": "Task removed", "accent": "#be123c", "soft": "rgba(190, 18, 60, 0.14)"},
        "PHASE_CREATED": {"icon": "&#129517;", "label": "Phase added", "accent": "#9333ea", "soft": "rgba(147, 51, 234, 0.14)"},
        "PHASE_UPDATED": {"icon": "&#129681;", "label": "Phase updated", "accent": "#8b5cf6", "soft": "rgba(139, 92, 246, 0.14)"},
        "PHASE_UNDELETED": {"icon": "&#8635;", "label": "Phase restored", "accent": "#2563eb", "soft": "rgba(37, 99, 235, 0.14)"},
        "PHASE_DELETED": {"icon": "&#8722;", "label": "Phase removed", "accent": "#be123c", "soft": "rgba(190, 18, 60, 0.14)"},
        "STARTED": {"icon": "&#9654;", "label": "Task started", "accent": "#2563eb", "soft": "rgba(37, 99, 235, 0.14)"},
        "FINISHED": {"icon": "&#10003;", "label": "Task finished", "accent": "#15803d", "soft": "rgba(21, 128, 61, 0.14)"},
        "NOTE": {"icon": "&#128221;", "label": "Task note", "accent": "#7c3aed", "soft": "rgba(124, 58, 237, 0.14)"},
        "STATUS": {"icon": "&#9873;", "label": "Status changed", "accent": "#1d4ed8", "soft": "rgba(29, 78, 216, 0.14)"},
        "EDITED_ACTUALS": {"icon": "&#128340;", "label": "Actuals edited", "accent": "#c2410c", "soft": "rgba(194, 65, 12, 0.14)"},
        "PROJECT_CLOSED": {"icon": "&#10003;", "label": "Project closed", "accent": "#be123c", "soft": "rgba(190, 18, 60, 0.14)"},
    }
    return event_map.get(
        event_type,
        {"icon": "&#9679;", "label": "Activity", "accent": "#334155", "soft": "rgba(51, 65, 85, 0.14)"},
    )
