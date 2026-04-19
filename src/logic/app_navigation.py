from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageDefinition:
    path: str
    title: str
    icon: str | None = None


def login_page_definition() -> PageDefinition:
    return PageDefinition(path="pages/login.py", title="Sign in")


def build_navigation_sections(*, is_admin: bool) -> dict[str, list[PageDefinition]]:
    sections = {
        "Home": [
            PageDefinition("pages/home.py", "Home", ":material/home:"),
            PageDefinition("pages/todo.py", "Todos", ":material/checklist:"),
            PageDefinition("pages/account.py", "Account", ":material/person:"),
        ],
        "Projects": [
            PageDefinition("pages/projects.py", "Load", ":material/folder_open:"),
            PageDefinition("pages/excel_import.py", "Excel Import", ":material/table_view:"),
            PageDefinition("pages/feed.py", "Feed", ":material/view_list:"),
            PageDefinition("pages/build.py", "Build", ":material/build:"),
        ],
        "Workspace": [
            PageDefinition("pages/plan.py", "Plan", ":material/view_timeline:"),
            PageDefinition("pages/execute.py", "Execute", ":material/construction:"),
            PageDefinition("pages/signals.py", "Signals", ":material/sensors:"),
            PageDefinition("pages/analyze.py", "Delays", ":material/timer:"),
            PageDefinition("pages/analytics.py", "Analytics", ":material/query_stats:"),
        ],
        "Manage": [
            PageDefinition("pages/manage.py", "Manage", ":material/manage_accounts:"),
        ],
    }

    if is_admin:
        sections["Admin"] = [
            PageDefinition("pages/admin.py", "Admin", ":material/admin_panel_settings:")
        ]

    return sections
