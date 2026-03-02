import streamlit as st
from uuid import UUID

from logic.backend.delays import get_delays
from logic.backend.api_client import save_delays
from models.delay import DelayType, DelayEditorRow

PENDING_KEY = "delays_pending_save"
SOURCE_DF_KEY = "delays_editor_source_df"
BASE_ROWS_KEY = "delays_rows_last_saved"
EDITOR_VER_KEY = "delays_editor_ver"

def _format_delay_type(dt: DelayType) -> str:
    return dt.name.replace("_", " ").title()

def _editor_key() -> str:
    ver = st.session_state.get(EDITOR_VER_KEY, 0)
    return f"delays_editor_df_{ver}"

def _load_last_saved_from_server(*, project_id: str | UUID) -> None:
    delays = get_delays(
        headers=st.session_state.get("auth_headers", {}),
        project_id=project_id,
    )
    rows = DelayEditorRow.from_delay(delays)
    df = DelayEditorRow.to_df(rows)

    # store baseline + source df
    st.session_state[BASE_ROWS_KEY] = rows
    st.session_state[SOURCE_DF_KEY] = df

    # bump editor version to force a reset
    st.session_state[EDITOR_VER_KEY] = st.session_state.get(EDITOR_VER_KEY, 0) + 1

def render_pending_confirmations(*, project_id: str | UUID) -> None:
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
        _load_last_saved_from_server(project_id=project_id)
        st.success(f"Saved {len(saved)} delays.")
        st.rerun()

    if c2.button(":material/undo: Cancel"):
        del st.session_state[PENDING_KEY]

        # revert editor to last-saved (server truth)
        _load_last_saved_from_server(project_id=project_id)
        st.info("Cancelled.")
        st.rerun()

def render_delay_register():
    project_id = st.session_state.session.project.uuid

    # initial load
    if SOURCE_DF_KEY not in st.session_state or BASE_ROWS_KEY not in st.session_state:
        _load_last_saved_from_server(project_id=project_id)
        st.rerun()

    pending = st.session_state.get(PENDING_KEY) is not None

    # You can put this above or below the form. If you hate it at the top, move it below.
    render_pending_confirmations(project_id=project_id)

    rows_last_saved: list[DelayEditorRow] = st.session_state[BASE_ROWS_KEY]
    df_source = st.session_state[SOURCE_DF_KEY]

    delay_options = list(DelayType)

    with st.form("delay_register", border=False):
        edited_df = st.data_editor(
            data=df_source,
            key=_editor_key(),
            hide_index=True,
            width="content",
            disabled=pending,
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
                ),
                "end_dt": st.column_config.DatetimeColumn(
                    label="End",
                    help="Date and time the delay ended (optional)",
                    required=False,
                    step=5,
                ),
                "duration_minutes": st.column_config.NumberColumn(
                    label="Duration (mins)",
                    help="The duration of the delay: total lost time.",
                ),
                "_select": st.column_config.SelectboxColumn(
                    label="View Details",
                    help="Select to view tasks affected by a given delay"
                )
            },
            num_rows="dynamic",
        )

        update = st.form_submit_button(
            label=":material/sync: Update Delays",
            help="Sync delays for the project.",
            type="primary",
            disabled=pending,
        )

    if not update:
        return

    edited_rows = DelayEditorRow.from_df(edited_df)
    diff = DelayEditorRow.diff(rows_last_saved, edited_rows)

    if diff["removed"]:
        st.session_state[PENDING_KEY] = {
            "edited_rows": edited_rows,
            "diff": {"removed": diff["removed"], "added": diff["added"]},
            "project_id": project_id,
            "replace": True,
        }
        st.rerun()

    # no deletions -> save immediately
    saved = save_delays(
        headers=st.session_state.get("auth_headers", {}),
        project_id=project_id,
        edited_rows=edited_rows,
        replace=False,
    )

    # refresh baseline + reset editor after save
    _load_last_saved_from_server(project_id=project_id)
    st.success(f"Saved {len(saved)} delays.")
    st.rerun()