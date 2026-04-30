from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.backend import api_client


def test_fetch_project_summary_by_id_returns_matching_project(monkeypatch) -> None:
    monkeypatch.setattr(
        api_client,
        "fetch_projects",
        lambda headers, include_closed=False: [
            {
                "id": "proj-1",
                "name": "Existing Project",
                "closed": False,
                "created_at": "2026-04-20T12:00:00Z",
                "updated_at": "2026-04-21T12:00:00Z",
                "timezone_name": "America/Vancouver",
            }
        ],
    )

    summary = api_client.fetch_project_summary_by_id(
        headers={"Authorization": "Bearer test"},
        project_id="proj-1",
    )

    assert summary is not None
    assert summary.id == "proj-1"
    assert summary.name == "Existing Project"


def test_fetch_project_summary_by_id_returns_none_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(api_client, "fetch_projects", lambda headers, include_closed=False: [])

    summary = api_client.fetch_project_summary_by_id(
        headers={"Authorization": "Bearer test"},
        project_id="proj-missing",
    )

    assert summary is None
