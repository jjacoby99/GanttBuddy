from __future__ import annotations

import os
import requests
import streamlit as st

from logic.backend.api_client import get_current_user
from logic.backend.config import get_backend_environment_config

CONFIG = get_backend_environment_config()
API_BASE = CONFIG.api_base_url


def _auth_provider_name() -> str | None:
    return CONFIG.oidc_provider


def exchange_oidc_token(id_token: str) -> str:
    response = requests.post(
        f"{API_BASE}/auth/oidc/exchange",
        json={"id_token": id_token},
        timeout=10,
    )
    if response.status_code != 200:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"OIDC exchange failed ({response.status_code}): {detail}")
    return response.json()["access_token"]


def set_auth(token: str) -> None:
    st.session_state["access_token"] = token
    st.session_state["auth_headers"] = {"Authorization": f"Bearer {token}"}
    st.session_state["auth"] = get_current_user(st.session_state["auth_headers"])
    st.session_state["backend_auth_ready"] = True


def sync_backend_auth_from_streamlit() -> bool:
    if not getattr(st.user, "is_logged_in", False):
        return False

    id_token = st.user.tokens.get("id")
    if not id_token:
        raise RuntimeError(
            "Streamlit login is active, but no ID token is exposed. Set [auth].expose_tokens = \"id\"."
        )

    if st.session_state.get("backend_auth_ready") and st.session_state.get("access_token"):
        return True

    token = exchange_oidc_token(id_token)
    set_auth(token)
    return True


def reset_auth() -> None:
    st.session_state["access_token"] = None
    st.session_state["auth_headers"] = None
    st.session_state["auth"] = {}
    st.session_state["backend_auth_ready"] = False
    st.session_state["project_access"] = None


def logout() -> None:
    reset_auth()
    if getattr(st.user, "is_logged_in", False):
        st.logout()


def is_logged_in() -> bool:
    if getattr(st.user, "is_logged_in", False):

        try:
            return sync_backend_auth_from_streamlit()
        except Exception as e:
            reset_auth()
            return False

    headers = st.session_state.get("auth_headers")
    if not headers:
        return False

    try:
        st.session_state["auth"] = get_current_user(auth_headers=headers)
        st.session_state["backend_auth_ready"] = True
        return True
    except Exception:
        reset_auth()
        return False


def render_oidc_login_button(label: str = ":material/login: Sign in") -> None:
    provider = _auth_provider_name()
    if st.button(label, type="tertiary"):
        if provider:
            st.login(provider)
        else:
            st.login()
