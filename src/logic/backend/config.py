from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st


DEFAULT_API_BASE_URLS = {
    "local": "http://127.0.0.1:8000",
    "staging": "https://ganttbuddy-api-staging-364477301326.us-west1.run.app",
    "production": "https://ganttbuddy-api-production-469799823422.us-west1.run.app",
}

ENV_ALIASES = {
    "dev": "local",
    "prod": "production",
}


@dataclass(frozen=True)
class BackendEnvironmentConfig:
    name: str
    api_base_url: str
    oidc_provider: str | None


def _ganttbuddy_secrets() -> dict:
    try:
        return st.secrets.get("ganttbuddy", {})
    except Exception:
        return {}


def _normalize_environment_name(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return "production"
    return ENV_ALIASES.get(normalized, normalized)


def get_backend_environment_config() -> BackendEnvironmentConfig:
    ganttbuddy = _ganttbuddy_secrets()
    environment_name = _normalize_environment_name(
        os.getenv("GANTTBUDDY_ENV") or ganttbuddy.get("environment")
    )

    environment_map = ganttbuddy.get("environments", {})
    environment_settings = environment_map.get(environment_name, {})

    api_base_url = (
        os.getenv("GANTTBUDDY_API_BASE_URL")
        or environment_settings.get("api_base_url")
        or DEFAULT_API_BASE_URLS.get(environment_name)
        or DEFAULT_API_BASE_URLS["production"]
    )

    oidc_provider = (
        os.getenv("GANTTBUDDY_OIDC_PROVIDER")
        or environment_settings.get("oidc_provider")
        or ganttbuddy.get("oidc_provider")
    )

    return BackendEnvironmentConfig(
        name=environment_name,
        api_base_url=api_base_url.rstrip("/"),
        oidc_provider=oidc_provider,
    )
