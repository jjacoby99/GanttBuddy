import streamlit as st
from uuid import UUID
import datetime as dt
import pandas as pd
from zoneinfo import ZoneInfo

from logic.backend.delays import get_delays
from logic.backend.api_client import save_delays
from logic.backend.project_permissions import project_is_read_only
from models.delay import DelayType, DelayEditorRow, DELAY_BADGE
from models.project import Project

PENDING_KEY = "delays_pending_save"
SOURCE_DF_KEY = "delays_editor_source_df"
BASE_ROWS_KEY = "delays_rows_last_saved"
EDITOR_VER_KEY = "delays_editor_ver"

def _format_delay_type(dt: DelayType) -> str:
    return dt.name.replace("_", " ").title()

def _editor_key() -> str:
    ver = st.session_state.get(EDITOR_VER_KEY, 0)
    return f"delays_editor_df_{ver}"

def _load_last_saved_from_server(*, project_id: str | UUID, timezone: ZoneInfo) -> None:
    delays = get_delays(
        headers=st.session_state.get("auth_headers", {}),
        project_id=project_id,
        timezone=timezone
    )
    rows = DelayEditorRow.from_delay(delays)
    df = DelayEditorRow.to_df(rows)

    # store baseline + source df
    st.session_state[BASE_ROWS_KEY] = rows
    st.session_state[SOURCE_DF_KEY] = df

    # bump editor version to force a reset
    st.session_state[EDITOR_VER_KEY] = st.session_state.get(EDITOR_VER_KEY, 0) + 1

def write_delay_info(delay: DelayEditorRow, project: Project):
    start = delay.start_dt
    if not start:
        return
    

    end = delay.end_dt
    if not end:
        end = start + dt.timedelta(minutes=delay.duration_minutes)


    tasks_affected = project.tasks_in_range(
        start_dt=start,
        end_dt=end,
        planned=False,
        mode="overlap"
    )
    left, right = st.columns(2)
    with left:
        st.caption("Description")
        description = delay.description if delay.description else "No description provided"
        st.markdown(f"{description}" )

        st.metric(
            label="Tasks Affected",
            value=len(tasks_affected)
        )

    with right:
        st.caption("Type")
        color, icon, text = DELAY_BADGE[delay.delay_type]
        st.badge(text, icon=icon, color=color)

        st.metric(
            label="Tracked Delay (hrs)",
            value= delay.duration_minutes / 60
        )

    data = {
        "Name": [],
        "Variance": []
    }

    for task in tasks_affected:
        data["Name"].append(task.name)
        var = task.variance if task.completed else None
        data["Variance"].append(var)

    
    
    df = pd.DataFrame(data)
    df = df.dropna()

    df = df.sort_values(by="Variance", ascending=False)

    st.caption(f"Affected Tasks (top {min(5, len(tasks_affected))} by variance)")
    st.dataframe(
        df.head(5),
        hide_index=True
        )
    
    st.caption(":material/info: **Affected tasks** are tasks that *overlap* with a tracked delay's time window. They may not have started *and* ended during the delay window.")


def render_pending_confirmations(*, project_id: str | UUID, timezone: ZoneInfo) -> None:
    if project_is_read_only():
        return
    pending = st.session_state.get(PENDING_KEY)
    if not pending:
        return
    removed = pending["diff"]["removed"]

    st.warning(f"{len(removed)} delays deleted. Proceed?")
    with st.popover("Show removed delays"):
        for i, r in enumerate(removed):
            st.write(f"**{i+1}.** *{r.description}*")

    c1, c2 = st.columns(2)

    if c1.button(":material/delete_forever: Proceed", type="primary"):
        saved = save_delays(
            headers=st.session_state.get("auth_headers", {}),
            project_id=pending["project_id"],
            edited_rows=pending["edited_rows"],
            replace=pending["replace"],
        )
        del st.session_state[PENDING_KEY]

        # refresh UI to server truth after save
        _load_last_saved_from_server(project_id=project_id,timezone=timezone)
        st.success(f"Saved {len(saved)} delays.")
        st.rerun()

    if c2.button(":material/undo: Cancel"):
        del st.session_state[PENDING_KEY]

        # revert editor to last-saved (server truth)
        _load_last_saved_from_server(project_id=project_id, timezone=timezone)
        st.info("Cancelled.")
        st.rerun()

def render_delay_register():
    read_only = project_is_read_only()
    
    with st.container(horizontal=True):
        st.subheader("Delay Register")
        
        st.space("stretch")

        to_visualizer = st.button(
            label="Visualize delays",
            help="Click to go to Gantt view to visualize project delays."
        )

        if to_visualizer:
            st.switch_page("pages/plan.py")

    proj = st.session_state.session.project
    project_id = proj.uuid
    timezone = proj.timezone

    # initial load
    if SOURCE_DF_KEY not in st.session_state or BASE_ROWS_KEY not in st.session_state:
        _load_last_saved_from_server(project_id=project_id, timezone=timezone)
        st.rerun()

    pending = st.session_state.get(PENDING_KEY) is not None

    # You can put this above or below the form. If you hate it at the top, move it below.
    render_pending_confirmations(project_id=project_id, timezone=timezone)
    if read_only:
        st.info("This project is read-only, so delay updates are disabled.")

    rows_last_saved: list[DelayEditorRow] = st.session_state[BASE_ROWS_KEY]
    df_source = st.session_state[SOURCE_DF_KEY]

    view = df_source.copy()

    # add view column
    view["_select"] = False

    delay_options = list(DelayType)

    with st.container(border=False):
        c1, c2 = st.columns([2,1])

        edited_df = c1.data_editor(
            data=view,
            key=_editor_key(),
            hide_index=True,
            width="content",
            disabled=read_only or pending,
            column_order=["description", "delay_type", "duration_minutes", "start_dt", "end_dt", "_select"],
            column_config={
                "description": st.column_config.TextColumn(
                    label="Delay Description",
                    help="What happened to cause this delay?",
                ),
                "delay_type": st.column_config.SelectboxColumn(
                    label="Category",
                    help="Group the delay into common categories.",
                    options=delay_options,
                    format_func=_format_delay_type,
                ),
                "start_dt": st.column_config.DatetimeColumn(
                    label="Start",
                    help="Date and time the delay started (optional)",
                    required=False,
                    step=5,
                    format="D MMM YYYY, h:mm a",
                ),
                "end_dt": st.column_config.DatetimeColumn(
                    label="End",
                    help="Date and time the delay ended (optional)",
                    required=False,
                    step=5,
                    format="D MMM YYYY, h:mm a",
                ),
                "duration_minutes": st.column_config.NumberColumn(
                    label="Duration (mins)",
                    help="The duration of the delay: total lost time.",
                ),
                "_select": st.column_config.CheckboxColumn(
                    label="View Details",
                    help="Select to view tasks affected by a given delay"
                )
            },
            num_rows="dynamic",
        )

        with c2:
            selected_delay_ids = list(edited_df.loc[edited_df["_select"] == True, 'id'])
            
            if not selected_delay_ids:
                st.info(":material/info: Select *View Details* to see tasks affected by a registered delay.", width=456)
            
            if len(selected_delay_ids) > 1:
                st.info(":material/info: Select a single delay")
            else:
                project = st.session_state.session.project
                selected_delays = []
                for row in rows_last_saved:
                    if row.id in selected_delay_ids:
                        selected_delays.append(row)
                
                for delay in selected_delays:
                    write_delay_info(delay, project)

        edited_df.drop("_select", axis=1,inplace=True)

    edited_rows = DelayEditorRow.from_df(edited_df)
    diff = DelayEditorRow.diff(rows_last_saved, edited_rows)

    changes_made = diff["removed"] or diff["added"] or diff["modified"]
    if changes_made:
        # only need to update if edits have been made
        update = st.button(
            label=":material/sync: Update Delays",
            help="Sync delays for the project.",
            type="primary",
            disabled=read_only or pending,
        )

    if diff["removed"] and update:
        st.session_state[PENDING_KEY] = {
            "edited_rows": edited_rows,
            "diff": {"removed": diff["removed"], "added": diff["added"]},
            "project_id": project_id,
            "replace": True,
        }
        st.rerun()

    if changes_made and update:
        # no deletions -> save immediately
        saved = save_delays(
            headers=st.session_state.get("auth_headers", {}),
            project_id=project_id,
            edited_rows=edited_rows,
            replace=False,
        )

        # refresh baseline + reset editor after save
        _load_last_saved_from_server(project_id=project_id, timezone=timezone)
        st.success(f"Saved {len(saved)} delays.")
        st.rerun()
