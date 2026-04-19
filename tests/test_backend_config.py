from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.backend import config


def test_backend_environment_defaults_to_production(monkeypatch) -> None:
    monkeypatch.delenv("GANTTBUDDY_ENV", raising=False)
    monkeypatch.delenv("GANTTBUDDY_API_BASE_URL", raising=False)
    monkeypatch.delenv("GANTTBUDDY_OIDC_PROVIDER", raising=False)
    monkeypatch.setattr(config, "st", SimpleNamespace(secrets={}))

    resolved = config.get_backend_environment_config()

    assert resolved.name == "production"
    assert resolved.api_base_url == config.DEFAULT_API_BASE_URLS["production"]
    assert resolved.oidc_provider is None


def test_backend_environment_uses_aliases_and_secret_mapping(monkeypatch) -> None:
    monkeypatch.setenv("GANTTBUDDY_ENV", "prod")
    monkeypatch.delenv("GANTTBUDDY_API_BASE_URL", raising=False)
    monkeypatch.delenv("GANTTBUDDY_OIDC_PROVIDER", raising=False)
    monkeypatch.setattr(
        config,
        "st",
        SimpleNamespace(
            secrets={
                "ganttbuddy": {
                    "environments": {
                        "production": {
                            "api_base_url": "https://frontend.example/api/",
                            "oidc_provider": "googleprod",
                        }
                    }
                }
            }
        ),
    )

    resolved = config.get_backend_environment_config()

    assert resolved.name == "production"
    assert resolved.api_base_url == "https://frontend.example/api"
    assert resolved.oidc_provider == "googleprod"


def test_backend_environment_prefers_explicit_env_over_secrets(monkeypatch) -> None:
    monkeypatch.setenv("GANTTBUDDY_ENV", "staging")
    monkeypatch.setenv("GANTTBUDDY_API_BASE_URL", "https://override.example/api/")
    monkeypatch.setenv("GANTTBUDDY_OIDC_PROVIDER", "google-workspace")
    monkeypatch.setattr(
        config,
        "st",
        SimpleNamespace(
            secrets={
                "ganttbuddy": {
                    "environment": "production",
                    "environments": {
                        "staging": {
                            "api_base_url": "https://staging.example/api",
                            "oidc_provider": "googlestaging",
                        }
                    },
                }
            }
        ),
    )

    resolved = config.get_backend_environment_config()

    assert resolved.name == "staging"
    assert resolved.api_base_url == "https://override.example/api"
    assert resolved.oidc_provider == "google-workspace"
