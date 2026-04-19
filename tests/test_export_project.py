from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.backend.export_project import project_to_import_payload
from models.project import Project
from models.project_metadata import RelineMetadata


def test_project_export_uses_authoritative_project_site_id_for_reline_metadata() -> None:
    project = Project(
        name="Reline",
        site_id="project-site",
        timezone=ZoneInfo("America/Edmonton"),
    )
    metadata = RelineMetadata(
        site_id="legacy-site",
        site_name="Legacy Site",
        mill_id="mill-1",
        mill_name="Mill 1",
        vendor="Metso",
        liner_system="Megaliner",
        supervisor="Supervisor",
        notes="",
    )

    payload = project_to_import_payload(project, metadata)

    assert payload["project"]["site_id"] == "project-site"
    assert payload["project"]["timezone_name"] == "America/Edmonton"
    assert payload["metadata"]["site_id"] == "project-site"
    assert payload["metadata"]["site_name"] == "Legacy Site"
