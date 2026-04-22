from __future__ import annotations

import os

import streamlit as st


def _flag_from_value(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _ganttbuddy_features() -> dict:
    try:
        return st.secrets.get("ganttbuddy", {}).get("features", {})
    except Exception:
        return {}


def signals_enabled() -> bool:
    env_value = _flag_from_value(os.getenv("GANTTBUDDY_SIGNALS_ENABLED"))
    if env_value is not None:
        return env_value

    secret_value = _flag_from_value(_ganttbuddy_features().get("signals_enabled"))
    if secret_value is not None:
        return secret_value

    return True
