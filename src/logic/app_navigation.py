from __future__ import annotations

from dataclasses import dataclass

from logic.feature_flags import signals_enabled


@dataclass(frozen=True)
class PageDefinition:
    path: str
    title: str
    icon: str | None = None


def login_page_definition() -> PageDefinition:
    return PageDefinition(path="pages/login.py", title="Sign in")


def build_navigation_sections(*, is_admin: bool) -> dict[str, list[PageDefinition]]:
    workspace_pages = [
        PageDefinition("pages/plan.py", "Plan", ":material/view_timeline:"),
        PageDefinition("pages/execute.py", "Execute", ":material/construction:"),
    ]
    if signals_enabled():
        workspace_pages.append(PageDefinition("pages/signals.py", "Signals", ":material/sensors:"))
    workspace_pages.extend(
        [
            PageDefinition("pages/analyze.py", "Delays", ":material/timer:"),
            PageDefinition("pages/analytics.py", "Analytics", ":material/query_stats:"),
        ]
    )

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
        "Workspace": workspace_pages,
        "Manage": [
            PageDefinition("pages/manage.py", "Manage", ":material/manage_accounts:"),
        ],
    }

    if is_admin:
        sections["Admin"] = [
            PageDefinition("pages/admin.py", "Overview", ":material/admin_panel_settings:"),
            PageDefinition("pages/admin_projects.py", "Projects", ":material/folder_open:"),
            PageDefinition("pages/admin_users.py", "Users", ":material/group:"),
        ]

    return sections
