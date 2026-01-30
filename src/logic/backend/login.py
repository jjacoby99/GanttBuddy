import requests
import streamlit as st


API_BASE = "http://127.0.0.1:8000"  # change for deployed

def login(email: str, password: str) -> str:
    # OAuth2PasswordRequestForm expects form-encoded fields:
    # username=<email>&password=<password>
    r = requests.post(
        f"{API_BASE}/auth/login",
        data={"username": email, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        # show server-provided detail if available
        try:
            detail = r.json()
        except Exception:
            detail = r.text
        raise RuntimeError(f"Login failed ({r.status_code}): {detail}")

    token = r.json()["access_token"]
    return token


@st.cache_data
def get_current_user(auth_headers: dict) -> dict:
    r = requests.get(f"{API_BASE}/auth/me", headers=auth_headers, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"Failed to get current user: {r.text}")
    return r.json()


def set_auth(token: str) -> None:
    st.session_state["access_token"] = token
    st.session_state["auth_headers"] = {"Authorization": f"Bearer {token}"}

    st.session_state["auth"] = get_current_user(st.session_state["auth_headers"])

def reset_auth() -> None:
    st.session_state["access_token"] = None
    st.session_state["auth_headers"] = None

def is_logged_in() -> bool:
    if "access_token" not in st.session_state or "auth_headers" not in st.session_state:
        return False
    
    headers = st.session_state.get("auth_headers")

    try:
        data = get_current_user(auth_headers=headers)
        return True
    except Exception:
        return False