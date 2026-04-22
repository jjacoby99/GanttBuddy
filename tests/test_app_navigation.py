from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from logic.app_navigation import build_navigation_sections, login_page_definition


def test_login_page_definition_matches_streamlit_entrypoint() -> None:
    page = login_page_definition()

    assert page.path == "pages/login.py"
    assert page.title == "Sign in"
    assert page.icon is None


def test_navigation_sections_include_workspace_for_signed_in_users() -> None:
    sections = build_navigation_sections(is_admin=False)

    assert list(sections.keys()) == ["Home", "Projects", "Workspace", "Manage"]
    assert [page.path for page in sections["Workspace"]] == [
        "pages/plan.py",
        "pages/execute.py",
        "pages/signals.py",
        "pages/analyze.py",
        "pages/analytics.py",
    ]


def test_navigation_sections_add_admin_page_for_admin_users() -> None:
    sections = build_navigation_sections(is_admin=True)

    assert "Admin" in sections
    assert [page.path for page in sections["Admin"]] == [
        "pages/admin.py",
        "pages/admin_projects.py",
        "pages/admin_users.py",
    ]
    assert [page.title for page in sections["Admin"]] == ["Overview", "Projects", "Users"]
