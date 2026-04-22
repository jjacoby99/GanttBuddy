from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from logic.backend.signals import (
    as_project_utc_window,
    create_data_source,
    create_signal_definition,
    create_signal_observations,
    delete_data_source,
    delete_signal_definition,
    delete_signal_observations,
    fetch_data_sources,
    fetch_ingestion_run,
    fetch_ingestion_runs,
    fetch_signal_definitions,
    fetch_signal_intervals,
    fetch_signal_observations,
    intervals_to_frame,
    observations_to_frame,
    rollback_ingestion_run,
    test_data_source,
    trigger_manual_ingestion,
    update_data_source,
    update_signal_definition,
)
from models.session import SessionModel
from models.signals import DataSource, DataSourceType, SignalDataType, SignalDefinition, SignalValueMode


SOURCE_SELECT_KEY = "signals_selected_source_id"
SIGNAL_SELECT_KEY = "signals_selected_signal_id"


def _signals_css() -> None:
    st.markdown(
        """
        <style>
        .signals-hero {
            padding: 24px 26px;
            border-radius: 22px;
            background:
                radial-gradient(circle at top left, rgba(35, 88, 160, 0.20), transparent 32%),
                linear-gradient(135deg, #f7fbff 0%, #eef5ff 42%, #f8f1e5 100%);
            border: 1px solid rgba(35, 88, 160, 0.12);
            margin-bottom: 1rem;
        }
        .signals-step {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: white;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }
        .signals-step-number {
            display: inline-block;
            min-width: 28px;
            height: 28px;
            line-height: 28px;
            text-align: center;
            border-radius: 999px;
            background: #10243e;
            color: white;
            font-weight: 700;
            margin-right: 10px;
        }
        .signals-kpi {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: white;
            padding: 16px 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }
        .signals-kpi-label {
            font-size: 0.80rem;
            color: rgba(15, 23, 42, 0.62);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .signals-kpi-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #10243e;
        }
        .signals-kpi-note {
            font-size: 0.9rem;
            color: rgba(15, 23, 42, 0.62);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="signals-kpi">
            <div class="signals-kpi-label">{label}</div>
            <div class="signals-kpi-value">{value}</div>
            <div class="signals-kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_step_header(step: int, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="signals-step">
            <div style="font-size: 1.15rem; font-weight: 700; color: #10243e; margin-bottom: 0.35rem;">
                <span class="signals-step-number">{step}</span>{title}
            </div>
            <div style="color: rgba(16, 36, 62, 0.75);">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _pretty_enum(value: str) -> str:
    return value.replace("_", " ").title()


def _generate_signal_key(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    slug = slug.strip("_")
    return slug or "signal"


def _default_config_text(source_type: DataSourceType) -> str:
    defaults = {
        DataSourceType.MANUAL: "{}",
        DataSourceType.CSV: json.dumps({"path": "", "delimiter": ",", "mappings": {}}, indent=2),
        DataSourceType.EXCEL: json.dumps({"path": "", "sheet_name": "", "mappings": {}}, indent=2),
        DataSourceType.API: json.dumps({"base_url": "", "endpoint": "", "auth": {}}, indent=2),
        DataSourceType.COMPUTED: json.dumps({"expression": "", "dependencies": []}, indent=2),
    }
    return defaults[source_type]


def _safe_json(text: str, *, label: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc.msg}.") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return value


def _empty_observation_editor(signal: SignalDefinition, rows: int = 5) -> pd.DataFrame:
    base = pd.DataFrame(
        {
            "timestamp_local": [pd.NaT] * rows,
            "quality_code": ["GOOD"] * rows,
            "source_record_key": [""] * rows,
        }
    )
    if signal.data_type == SignalDataType.NUMERIC:
        base["numeric_value"] = pd.Series([None] * rows, dtype="float")
    elif signal.data_type == SignalDataType.BOOLEAN:
        base["boolean_value"] = pd.Series([""] * rows, dtype="object")
    else:
        base["text_value"] = pd.Series([""] * rows, dtype="object")
    return base


def _sample_editor_rows(signal: SignalDefinition, timezone, rows: int = 6) -> pd.DataFrame:
    sample_rows = _empty_observation_editor(signal, rows=rows)
    current_time = dt.datetime.now(timezone).replace(minute=0, second=0, microsecond=0)
    sample_rows["timestamp_local"] = [current_time - dt.timedelta(hours=(rows - 1 - idx)) for idx in range(rows)]
    sample_rows["source_record_key"] = [f"{signal.key}-{idx+1}" for idx in range(rows)]
    if signal.data_type == SignalDataType.NUMERIC:
        sample_rows["numeric_value"] = [round(120 + idx * 8.5, 2) for idx in range(rows)]
    elif signal.data_type == SignalDataType.BOOLEAN:
        sample_rows["boolean_value"] = ["true" if idx % 2 == 0 else "false" for idx in range(rows)]
    else:
        labels = ["Idle", "Ramp", "Running", "Paused", "Running", "Complete"]
        sample_rows["text_value"] = labels[:rows]
    return sample_rows


def _rows_to_observations(df: pd.DataFrame, signal: SignalDefinition, timezone) -> list[dict[str, Any]]:
    records = []
    for row in df.to_dict(orient="records"):
        timestamp_local = row.get("timestamp_local")
        if pd.isna(timestamp_local) or timestamp_local is None:
            continue
        if hasattr(timestamp_local, "to_pydatetime"):
            timestamp_local = timestamp_local.to_pydatetime()
        if timestamp_local.tzinfo is None:
            timestamp_local = timestamp_local.replace(tzinfo=timezone)

        payload: dict[str, Any] = {
            "timestamp_utc": timestamp_local.astimezone(dt.UTC).isoformat().replace("+00:00", "Z"),
            "quality_code": row.get("quality_code") or None,
            "source_record_key": row.get("source_record_key") or None,
        }
        if signal.data_type == SignalDataType.NUMERIC:
            numeric_value = row.get("numeric_value")
            if pd.isna(numeric_value) or numeric_value is None:
                continue
            payload["numeric_value"] = float(numeric_value)
        elif signal.data_type == SignalDataType.BOOLEAN:
            boolean_value = str(row.get("boolean_value") or "").strip().lower()
            if boolean_value not in {"true", "false"}:
                continue
            payload["boolean_value"] = boolean_value == "true"
        else:
            text_value = str(row.get("text_value") or "").strip()
            if not text_value:
                continue
            payload["text_value"] = text_value
        records.append(payload)
    return records


def _render_observation_chart(df: pd.DataFrame, signal: SignalDefinition) -> None:
    if df.empty:
        st.info("No observations yet. Add a few rows below to create the first dataset for this signal.")
        return
    if signal.data_type == SignalDataType.NUMERIC:
        chart = (
            alt.Chart(df)
            .mark_line(point=True, strokeWidth=3, color="#215ca3")
            .encode(
                x=alt.X("timestamp_local:T", title="Timestamp"),
                y=alt.Y("value:Q", title=signal.unit or signal.name),
                tooltip=["timestamp_local:T", "value:Q", "quality_code:N", "source_record_key:N"],
            )
            .properties(height=280)
        )
    else:
        chart = (
            alt.Chart(df)
            .mark_circle(size=110, color="#c46a1a")
            .encode(
                x=alt.X("timestamp_local:T", title="Timestamp"),
                y=alt.Y("value_label:N", title="State"),
                tooltip=["timestamp_local:T", "value_label:N", "quality_code:N", "source_record_key:N"],
            )
            .properties(height=280)
        )
    st.altair_chart(chart, use_container_width=True)


def _get_selected_source(data_sources: list[DataSource]) -> DataSource | None:
    if not data_sources:
        st.session_state[SOURCE_SELECT_KEY] = None
        return None
    selected_id = st.session_state.get(SOURCE_SELECT_KEY)
    selected = next((item for item in data_sources if item.id == selected_id), None)
    if selected is None:
        selected = next((item for item in data_sources if item.source_type == DataSourceType.MANUAL), data_sources[0])
        st.session_state[SOURCE_SELECT_KEY] = selected.id
    return selected


def _get_selected_signal(signals: list[SignalDefinition]) -> SignalDefinition | None:
    if not signals:
        st.session_state[SIGNAL_SELECT_KEY] = None
        return None
    selected_id = st.session_state.get(SIGNAL_SELECT_KEY)
    selected = next((item for item in signals if item.id == selected_id), None)
    if selected is None:
        selected = signals[0]
        st.session_state[SIGNAL_SELECT_KEY] = selected.id
    return selected


def _observation_editor(signal: SignalDefinition, timezone, *, key_prefix: str, submit_label: str) -> pd.DataFrame | None:
    draft_key = f"{key_prefix}_{signal.id}_draft"
    if draft_key not in st.session_state:
        st.session_state[draft_key] = _empty_observation_editor(signal)

    tool_a, tool_b = st.columns(2)
    if tool_a.button("Load sample rows", key=f"{draft_key}_sample", use_container_width=True):
        st.session_state[draft_key] = _sample_editor_rows(signal, timezone)
        st.rerun()
    if tool_b.button("Clear draft", key=f"{draft_key}_clear", use_container_width=True):
        st.session_state[draft_key] = _empty_observation_editor(signal)
        st.rerun()

    typed_column = (
        "numeric_value"
        if signal.data_type == SignalDataType.NUMERIC
        else "boolean_value"
        if signal.data_type == SignalDataType.BOOLEAN
        else "text_value"
    )
    config: dict[str, Any] = {
        "timestamp_local": st.column_config.DatetimeColumn("Timestamp", format="D MMM YYYY, h:mm a", step=15),
        "quality_code": st.column_config.TextColumn("Quality"),
        "source_record_key": st.column_config.TextColumn("Source Record Key"),
    }
    if signal.data_type == SignalDataType.NUMERIC:
        config["numeric_value"] = st.column_config.NumberColumn(signal.unit or "Value")
    elif signal.data_type == SignalDataType.BOOLEAN:
        config["boolean_value"] = st.column_config.SelectboxColumn("Boolean Value", options=["", "true", "false"])
    else:
        config["text_value"] = st.column_config.TextColumn("State / Label")

    with st.form(f"{draft_key}_form", clear_on_submit=False):
        edited_df = st.data_editor(
            st.session_state[draft_key],
            key=f"{draft_key}_widget",
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_order=["timestamp_local", typed_column, "quality_code", "source_record_key"],
            column_config=config,
        )
        submitted = st.form_submit_button(submit_label, type="primary", use_container_width=True)

    if submitted:
        return edited_df
    return None


def _render_overview(signals: list[SignalDefinition], data_sources: list[DataSource], selected_signal: SignalDefinition | None) -> None:
    st.markdown(
        """
        <div class="signals-hero">
            <h3 style="margin: 0 0 0.35rem 0; color: #10243e;">Signals Workbench</h3>
            <p style="margin: 0; color: rgba(16, 36, 62, 0.75); max-width: 58rem;">
                Pick a signal, inspect its timeline, and add test data without the admin controls living on the page all the time.
                Source management and signal editing stay tucked behind dialogs so the workspace feels focused.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _render_kpi("Signals", str(len(signals)), "Definitions available in this project.")
    with c2:
        _render_kpi("Sources", str(len(data_sources)), "Reusable source configs.")
    with c3:
        _render_kpi("Current Signal", selected_signal.name if selected_signal else "None", "The active signal for data entry.")


@st.dialog("Manage Sources", width="large")
def _render_source_dialog(project_id: str, headers: dict, data_sources: list[DataSource], selected_source: DataSource | None) -> None:
    source_options = [None] + data_sources
    editing_source = st.selectbox(
        "Source",
        options=source_options,
        index=source_options.index(selected_source) if selected_source in source_options else 0,
        format_func=lambda item: "Create new source" if item is None else item.display_name,
        key="signals_source_dialog_select",
    )
    source_type_default = editing_source.source_type if editing_source else DataSourceType.MANUAL

    with st.form("signals_source_dialog_form", clear_on_submit=editing_source is None):
        name = st.text_input("Source name", value=editing_source.name if editing_source else "Manual Signals Entry")
        source_type = st.selectbox(
            "Source type",
            options=list(DataSourceType),
            index=list(DataSourceType).index(source_type_default),
            format_func=lambda item: _pretty_enum(item.value),
        )
        is_active = st.toggle("Active", value=editing_source.is_active if editing_source else True)
        config_text = st.text_area(
            "Config JSON",
            value=json.dumps(editing_source.config_json, indent=2) if editing_source else _default_config_text(source_type),
            height=180,
        )
        save = st.form_submit_button("Save source", type="primary")
        if save:
            try:
                payload = {
                    "name": name.strip(),
                    "source_type": source_type.value,
                    "config_json": _safe_json(config_text, label="Config JSON"),
                    "is_active": is_active,
                }
                if not payload["name"]:
                    raise ValueError("Source name is required.")
                if editing_source:
                    saved = update_data_source(headers, project_id, editing_source.id, payload)
                    st.success("Source updated.")
                else:
                    saved = create_data_source(headers, project_id, payload)
                    st.success("Source created.")
                st.session_state[SOURCE_SELECT_KEY] = saved.id
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if editing_source:
        a, b, c = st.columns(3)
        if a.button("Test source", key=f"test_source_{editing_source.id}", use_container_width=True):
            try:
                result = test_data_source(headers, project_id, editing_source.id)
                st.success("Data source test completed.")
                if result:
                    st.json(result)
            except Exception as exc:
                st.error(str(exc))
        delete_ok = b.checkbox("Confirm delete", key=f"delete_source_ok_{editing_source.id}")
        if c.button("Delete source", disabled=not delete_ok, key=f"delete_source_{editing_source.id}", use_container_width=True):
            try:
                delete_data_source(headers, project_id, editing_source.id)
                st.success("Source deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.dataframe(DataSource.to_frame(data_sources), hide_index=True, use_container_width=True)


def _render_signal_dialog(
    *,
    project_id: str,
    headers: dict,
    data_sources: list[DataSource],
    selected_source: DataSource | None,
    signal: SignalDefinition | None,
    create_mode: bool,
) -> None:
    linked_source_default = next(
        (item for item in data_sources if signal and item.id == signal.data_source_id),
        selected_source,
    )
    linked_source_options = [None] + data_sources

    with st.form(f"signals_signal_dialog_form_{'create' if create_mode else signal.id}", clear_on_submit=create_mode):
        name = st.text_input("Signal name", value="" if create_mode else signal.name)
        generated_key = _generate_signal_key(name) if create_mode else signal.key
        st.text_input("Generated key", value=generated_key, disabled=True)
        description = st.text_area("Description", value="" if create_mode else signal.description or "", height=96)
        data_type_default = SignalDataType.NUMERIC if create_mode else signal.data_type
        value_mode_default = SignalValueMode.SAMPLE if create_mode else signal.value_mode
        data_type = st.selectbox(
            "Data type",
            options=list(SignalDataType),
            index=list(SignalDataType).index(data_type_default),
            format_func=lambda item: _pretty_enum(item.value),
        )
        value_mode = st.selectbox(
            "Value mode",
            options=list(SignalValueMode),
            index=list(SignalValueMode).index(value_mode_default),
            format_func=lambda item: _pretty_enum(item.value),
        )
        unit = st.text_input("Unit", value="" if create_mode else signal.unit or "")
        linked_source = st.selectbox(
            "Linked source",
            options=linked_source_options,
            index=linked_source_options.index(linked_source_default) if linked_source_default in linked_source_options else 0,
            format_func=lambda item: "None" if item is None else item.display_name,
            help="Optional for raw observations, recommended for ingestion testing.",
        )
        metadata_text = st.text_area(
            "Metadata JSON",
            value="{}" if create_mode else json.dumps(signal.metadata_json or {}, indent=2),
            height=120,
        )
        save = st.form_submit_button("Create signal" if create_mode else "Save changes", type="primary")
        if save:
            try:
                payload = {
                    "key": _generate_signal_key(name) if create_mode else signal.key,
                    "name": name.strip(),
                    "description": description.strip() or None,
                    "data_type": data_type.value,
                    "value_mode": value_mode.value,
                    "unit": unit.strip() or None,
                    "data_source_id": linked_source.id if linked_source else None,
                    "metadata_json": _safe_json(metadata_text, label="Metadata JSON"),
                }
                if not payload["name"]:
                    raise ValueError("Signal name is required.")
                if create_mode:
                    saved = create_signal_definition(headers, project_id, payload)
                    st.success("Signal created.")
                else:
                    saved = update_signal_definition(headers, project_id, signal.id, payload)
                    st.success("Signal updated.")
                st.session_state[SIGNAL_SELECT_KEY] = saved.id
                if saved.data_source_id:
                    st.session_state[SOURCE_SELECT_KEY] = saved.data_source_id
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if not create_mode and signal is not None:
        delete_ok = st.checkbox("Confirm delete signal", key=f"delete_signal_ok_{signal.id}")
        if st.button("Delete signal", disabled=not delete_ok, key=f"delete_signal_{signal.id}", use_container_width=True):
            try:
                delete_signal_definition(headers, project_id, signal.id)
                st.success("Signal deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


@st.dialog("Create Signal", width="large")
def _render_create_signal_dialog(project_id: str, headers: dict, data_sources: list[DataSource], selected_source: DataSource | None) -> None:
    _render_signal_dialog(
        project_id=project_id,
        headers=headers,
        data_sources=data_sources,
        selected_source=selected_source,
        signal=None,
        create_mode=True,
    )


@st.dialog("Edit Signal", width="large")
def _render_edit_signal_dialog(project_id: str, headers: dict, data_sources: list[DataSource], selected_source: DataSource | None, signal: SignalDefinition) -> None:
    _render_signal_dialog(
        project_id=project_id,
        headers=headers,
        data_sources=data_sources,
        selected_source=selected_source,
        signal=signal,
        create_mode=False,
    )


def _render_signal_toolbar(
    project_id: str,
    headers: dict,
    signals: list[SignalDefinition],
    data_sources: list[DataSource],
    selected_source: DataSource | None,
    selected_signal: SignalDefinition | None,
) -> None:
    _render_step_header(
        1,
        "Choose Your Signal",
        "Signal selection stays visible here. Creating or editing signals and sources happens in dialogs so the main workspace stays clean.",
    )
    card_left, card_right = st.columns([1.35, 1])
    with card_left:
        if signals:
            current = st.selectbox(
                "Signal",
                options=signals,
                index=signals.index(selected_signal) if selected_signal in signals else 0,
                format_func=lambda item: item.display_name,
                key="signals_current_signal_select",
            )
            st.session_state[SIGNAL_SELECT_KEY] = current.id
            linked_source = next((item for item in data_sources if item.id == current.data_source_id), None)
            st.caption(f"Source: {linked_source.display_name if linked_source else 'Unlinked'}")
        else:
            st.info("No signals yet. Create one to start exploring data.")

    with card_right:
        a, b, c = st.columns(3)
        if a.button("New signal", type="primary", use_container_width=True):
            _render_create_signal_dialog(project_id, headers, data_sources, selected_source)
        if b.button("Edit signal", disabled=selected_signal is None, use_container_width=True):
            _render_edit_signal_dialog(project_id, headers, data_sources, selected_source, selected_signal)
        if c.button("Manage sources", use_container_width=True):
            _render_source_dialog(project_id, headers, data_sources, selected_source)


def _render_observation_step(
    project_id: str,
    headers: dict,
    selected_signal: SignalDefinition | None,
    data_sources: list[DataSource],
    timezone,
) -> None:
    _render_step_header(
        2,
        "Add Data",
        "This editor is form-backed, so values are committed together when you submit instead of being overwritten on every rerun.",
    )
    if selected_signal is None:
        st.info("Create a signal first, then this step becomes your data entry workspace.")
        return

    c1, c2, c3 = st.columns([1, 1, 0.65])
    default_end = dt.datetime.now(timezone).replace(minute=0, second=0, microsecond=0)
    default_start = default_end - dt.timedelta(days=7)
    start_local = c1.datetime_input("Window start", value=default_start, step=dt.timedelta(minutes=15), key="signals_window_start")
    end_local = c2.datetime_input("Window end", value=default_end, step=dt.timedelta(minutes=15), key="signals_window_end")
    limit = c3.number_input("Limit", min_value=50, max_value=5000, value=500, step=50, key="signals_window_limit")
    start_utc, end_utc = as_project_utc_window(start_local, end_local, timezone=timezone)

    try:
        observations = fetch_signal_observations(headers, project_id, selected_signal.id, start=start_utc, end=end_utc, limit=int(limit))
    except Exception as exc:
        st.error(str(exc))
        return

    df = observations_to_frame(observations, timezone=timezone, data_type=selected_signal.data_type)
    left, right = st.columns([1.35, 1])
    with left:
        _render_observation_chart(df, selected_signal)
    with right:
        st.metric("Rows in window", len(observations))
        st.metric("Data type", _pretty_enum(selected_signal.data_type.value))
        source_name = next((item.name for item in data_sources if item.id == selected_signal.data_source_id), "Unlinked")
        st.metric("Linked source", source_name)

    display_df = df[["timestamp_local", "value", "quality_code", "source_record_key", "ingestion_run_id"]] if not df.empty else df
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    submitted_df = _observation_editor(selected_signal, timezone, key_prefix="signals_observations", submit_label="Create observation batch")
    if submitted_df is not None:
        try:
            payload = _rows_to_observations(submitted_df, selected_signal, timezone)
            if not payload:
                raise ValueError("Add at least one complete row before submitting.")
            create_signal_observations(headers, project_id, selected_signal.id, payload)
            st.session_state[f"signals_observations_{selected_signal.id}_draft"] = _empty_observation_editor(selected_signal)
            st.success(f"Inserted {len(payload)} observations.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

    delete_col, _ = st.columns([1, 1])
    with delete_col.popover("Delete observations"):
        delete_start = st.datetime_input("Delete start", value=start_local, key=f"delete_obs_start_{selected_signal.id}")
        delete_end = st.datetime_input("Delete end", value=end_local, key=f"delete_obs_end_{selected_signal.id}")
        delete_confirm = st.checkbox("Confirm observation deletion", key=f"delete_obs_confirm_{selected_signal.id}")
        if st.button("Delete matching rows", disabled=not delete_confirm, key=f"delete_obs_btn_{selected_signal.id}"):
            try:
                delete_start_utc, delete_end_utc = as_project_utc_window(delete_start, delete_end, timezone=timezone)
                delete_signal_observations(headers, project_id, selected_signal.id, start=delete_start_utc, end=delete_end_utc)
                st.success("Observation range deleted.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if selected_signal.data_type in {SignalDataType.BOOLEAN, SignalDataType.CATEGORICAL}:
        st.caption("Derived intervals")
        try:
            intervals = fetch_signal_intervals(headers, project_id, selected_signal.id, start=start_utc, end=end_utc)
            intervals_df = intervals_to_frame(intervals, timezone=timezone)
            if intervals_df.empty:
                st.info("No intervals available for the current window.")
            else:
                st.dataframe(intervals_df, hide_index=True, use_container_width=True)
        except Exception as exc:
            st.error(str(exc))


def _render_ingestion_step(
    project_id: str,
    headers: dict,
    signals: list[SignalDefinition],
    selected_source: DataSource | None,
    timezone,
) -> None:
    with st.expander("3. Optional: Manual ingestion and run history", expanded=False):
        if selected_source is None or selected_source.source_type != DataSourceType.MANUAL:
            st.info("Choose a MANUAL source above to test ingestion runs.")
            return

        linked_signals = [signal for signal in signals if signal.data_source_id == selected_source.id]
        if not linked_signals:
            st.info("Link at least one signal to this manual source before running an ingestion.")
            return

        active_signal = _get_selected_signal(linked_signals)
        selected_signal = st.selectbox(
            "Signal for manual ingestion",
            options=linked_signals,
            index=linked_signals.index(active_signal) if active_signal in linked_signals else 0,
            format_func=lambda item: item.display_name,
            key="signals_ingestion_signal_select",
        )
        st.session_state[SIGNAL_SELECT_KEY] = selected_signal.id

        submitted_df = _observation_editor(selected_signal, timezone, key_prefix="signals_ingestion", submit_label="Trigger manual ingestion")
        source_version = st.text_input("Source version", value="manual-v1", key=f"ingest_source_version_{selected_source.id}")
        fingerprint = st.text_input(
            "Fingerprint",
            value=f"{selected_signal.key}-{dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')}",
            key=f"ingest_fingerprint_{selected_source.id}",
        )

        if submitted_df is not None:
            try:
                observations = _rows_to_observations(submitted_df, selected_signal, timezone)
                if not observations:
                    raise ValueError("Add at least one complete observation row.")
                payload = {
                    "source_version": source_version.strip(),
                    "fingerprint": fingerprint.strip() or None,
                    "observation_batches": [{"signal_id": selected_signal.id, "observations": observations}],
                }
                trigger_manual_ingestion(headers, project_id, selected_source.id, payload)
                st.session_state[f"signals_ingestion_{selected_signal.id}_draft"] = _empty_observation_editor(selected_signal)
                st.success("Manual ingestion triggered.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        try:
            runs = fetch_ingestion_runs(headers, project_id, selected_source.id)
        except Exception as exc:
            st.error(str(exc))
            return

        if not runs:
            st.info("No ingestion runs yet for this source.")
            return

        runs_df = pd.DataFrame(
            [
                {
                    "id": item.id,
                    "status": item.status.value,
                    "started_at": item.started_at.astimezone(timezone) if item.started_at else None,
                    "completed_at": item.completed_at.astimezone(timezone) if item.completed_at else None,
                    "fingerprint": item.fingerprint or "",
                }
                for item in runs
            ]
        )
        st.dataframe(runs_df, hide_index=True, use_container_width=True)

        selected_run = st.selectbox(
            "Inspect run",
            options=runs,
            format_func=lambda item: f"{item.status.value} | {item.id[:8]}",
            key=f"ingestion_run_select_{selected_source.id}",
        )
        detail = fetch_ingestion_run(headers, project_id, selected_run.id)
        st.json(detail.model_dump(mode="json"))
        rollback_ok = st.checkbox("Confirm rollback", key=f"rollback_ok_{selected_run.id}")
        if st.button("Rollback ingestion", disabled=not rollback_ok, key=f"rollback_btn_{selected_run.id}"):
            try:
                rollback_ingestion_run(headers, project_id, selected_run.id)
                st.success("Rollback requested.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render_signals_view(session: SessionModel) -> None:
    _signals_css()

    project = session.project
    headers = st.session_state.get("auth_headers", {})
    project_id = project.uuid
    timezone = project.timezone

    try:
        data_sources = fetch_data_sources(headers, project_id)
        signals = fetch_signal_definitions(headers, project_id)
    except Exception as exc:
        st.error(str(exc))
        return

    selected_source = _get_selected_source(data_sources)
    selected_signal = _get_selected_signal(signals)

    _render_overview(signals, data_sources, selected_signal)
    _render_signal_toolbar(project_id, headers, signals, data_sources, selected_source, selected_signal)

    data_sources = fetch_data_sources(headers, project_id)
    signals = fetch_signal_definitions(headers, project_id)
    selected_source = _get_selected_source(data_sources)
    selected_signal = _get_selected_signal(signals)

    _render_observation_step(project_id, headers, selected_signal, data_sources, timezone)
    _render_ingestion_step(project_id, headers, signals, selected_source, timezone)
