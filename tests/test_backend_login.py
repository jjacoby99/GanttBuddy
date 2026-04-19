from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.backend import login


class FakeStreamlit:
    def __init__(self, *, button_result: bool = False, user: SimpleNamespace | None = None):
        self.session_state: dict = {}
        self.user = user or SimpleNamespace(is_logged_in=False, tokens={})
        self._button_result = button_result
        self.login_calls: list[str | None] = []
        self.logout_called = False

    def button(self, *_args, **_kwargs) -> bool:
        return self._button_result

    def login(self, provider: str | None = None) -> None:
        self.login_calls.append(provider)

    def logout(self) -> None:
        self.logout_called = True


def test_sync_backend_auth_from_streamlit_exchanges_id_token(monkeypatch) -> None:
    fake_st = FakeStreamlit(user=SimpleNamespace(is_logged_in=True, tokens={"id": "id-token"}))
    monkeypatch.setattr(login, "st", fake_st)
    monkeypatch.setattr(login, "exchange_oidc_token", lambda id_token: f"access-for:{id_token}")
    monkeypatch.setattr(
        login,
        "get_current_user",
        lambda auth_headers: {"email": "user@example.com", "headers": auth_headers},
    )

    assert login.sync_backend_auth_from_streamlit() is True
    assert fake_st.session_state["access_token"] == "access-for:id-token"
    assert fake_st.session_state["auth_headers"] == {"Authorization": "Bearer access-for:id-token"}
    assert fake_st.session_state["auth"]["email"] == "user@example.com"
    assert fake_st.session_state["backend_auth_ready"] is True


def test_is_logged_in_resets_failed_streamlit_exchange(monkeypatch) -> None:
    fake_st = FakeStreamlit(user=SimpleNamespace(is_logged_in=True, tokens={"id": "broken"}))
    fake_st.session_state.update(
        {
            "access_token": "old-token",
            "auth_headers": {"Authorization": "Bearer old-token"},
            "auth": {"email": "old@example.com"},
            "backend_auth_ready": True,
        }
    )
    monkeypatch.setattr(login, "st", fake_st)
    monkeypatch.setattr(login, "sync_backend_auth_from_streamlit", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    assert login.is_logged_in() is False
    assert fake_st.session_state["access_token"] is None
    assert fake_st.session_state["auth_headers"] is None
    assert fake_st.session_state["auth"] == {}
    assert fake_st.session_state["backend_auth_ready"] is False


def test_is_logged_in_accepts_existing_backend_session(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.session_state["auth_headers"] = {"Authorization": "Bearer existing-token"}
    monkeypatch.setattr(login, "st", fake_st)
    monkeypatch.setattr(login, "get_current_user", lambda auth_headers: {"is_active": True, "headers": auth_headers})

    assert login.is_logged_in() is True
    assert fake_st.session_state["auth"]["is_active"] is True
    assert fake_st.session_state["backend_auth_ready"] is True


def test_render_oidc_login_button_uses_named_provider(monkeypatch) -> None:
    fake_st = FakeStreamlit(button_result=True)
    monkeypatch.setattr(login, "st", fake_st)
    monkeypatch.setattr(login, "_auth_provider_name", lambda: "googleprod")

    login.render_oidc_login_button()

    assert fake_st.login_calls == ["googleprod"]


def test_render_oidc_login_button_falls_back_to_default_provider(monkeypatch) -> None:
    fake_st = FakeStreamlit(button_result=True)
    monkeypatch.setattr(login, "st", fake_st)
    monkeypatch.setattr(login, "_auth_provider_name", lambda: None)

    login.render_oidc_login_button()

    assert fake_st.login_calls == [None]
