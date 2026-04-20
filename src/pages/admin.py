from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import altair as alt
import pandas as pd
import streamlit as st

from logic.backend.api_client import (
    fetch_organization_activity,
    fetch_organization_dashboard,
    fetch_organization_projects_summary,
    fetch_organization_user_detail,
    fetch_organization_users_summary,
    headers_for_organization,
    update_organization_user_role,
)
from logic.backend.guards import require_admin
from logic.backend.users import get_user
from logic.backend.utils.parse_datetime import parse_backend_utc

ADMIN_ROLES = {"ORG_OWNER", "ORG_ADMIN"}
ORG_ROLE_OPTIONS = ["MEMBER", "PROJECT_MANAGER", "ORG_ADMIN"]
ORG_ROLE_ASSIGNMENT_LIMITS = {
    "ORG_OWNER": {"MEMBER", "PROJECT_MANAGER", "ORG_ADMIN"},
    "ORG_ADMIN": {"MEMBER", "PROJECT_MANAGER"},
}
USER_STATUS_LABELS = {
    "active": "Active",
    "inactive": "Inactive",
    "never_logged_in": "Never logged in",
    "logged_in_no_activity": "Logged in, no activity",
}
USER_STATUS_COLORS = {
    "active": "#18794e",
    "inactive": "#b42318",
    "never_logged_in": "#9a6700",
    "logged_in_no_activity": "#1d4ed8",
}
PROJECT_HEALTH_COLORS = {
    "Healthy": "#18794e",
    "Needs attention": "#c2410c",
    "Dormant": "#7c3aed",
    "Closed": "#475467",
}


def _clear_admin_caches() -> None:
    fetch_organization_dashboard.clear()
    fetch_organization_projects_summary.clear()
    fetch_organization_users_summary.clear()
    fetch_organization_user_detail.clear()
    fetch_organization_activity.clear()


def _assignable_org_roles(actor_role: str) -> list[str]:
    allowed = ORG_ROLE_ASSIGNMENT_LIMITS.get(actor_role, set())
    return [role for role in ORG_ROLE_OPTIONS if role in allowed]


def _can_manage_org_role(actor_role: str, target_role: str | None) -> bool:
    if not target_role:
        return False
    return target_role in ORG_ROLE_ASSIGNMENT_LIMITS.get(actor_role, set())


def _page_css() -> None:
    st.markdown(
        """
        <style>
        .admin-shell {
            padding: 1.2rem 1.4rem;
            border-radius: 24px;
            background:
                radial-gradient(circle at top right, rgba(253, 224, 71, 0.28), transparent 25%),
                radial-gradient(circle at left center, rgba(56, 189, 248, 0.18), transparent 22%),
                linear-gradient(135deg, #0f172a 0%, #162033 50%, #1f2937 100%);
            color: white;
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
        }
        .admin-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 0.75rem;
            opacity: 0.75;
            margin-bottom: 0.5rem;
        }
        .admin-hero-title {
            font-size: 2rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 0.45rem;
        }
        .admin-hero-copy {
            font-size: 0.98rem;
            line-height: 1.5;
            color: rgba(255,255,255,0.82);
            max-width: 44rem;
        }
        .admin-hero-stat {
            padding: 0.8rem 1rem;
            border-radius: 18px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.1);
        }
        .admin-hero-stat-label {
            font-size: 0.8rem;
            color: rgba(255,255,255,0.92);
            margin-bottom: 0.25rem;
            font-weight: 700;
        }
        .admin-hero-stat-value {
            font-size: 1.35rem;
            font-weight: 800;
        }
        .admin-card {
            border-radius: 18px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98));
            padding: 1rem 1rem 0.9rem 1rem;
            min-height: 100%;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }
        .admin-card-title {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #667085;
            margin-bottom: 0.35rem;
        }
        .admin-card-value {
            font-size: 1.85rem;
            font-weight: 800;
            line-height: 1.05;
            color: #101828;
        }
        .admin-card-sub {
            margin-top: 0.35rem;
            color: #475467;
            font-size: 0.92rem;
        }
        .admin-pill {
            display: inline-block;
            padding: 0.22rem 0.6rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            background: #eef2ff;
            color: #3730a3;
            margin-top: 0.55rem;
        }
        .admin-insight {
            border-left: 4px solid #0ea5e9;
            background: linear-gradient(180deg, rgba(14, 165, 233, 0.06), rgba(14, 165, 233, 0.02));
            border-radius: 12px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.75rem;
        }
        .admin-feed-item {
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(15, 23, 42, 0.08);
        }
        .admin-feed-item:last-child {
            border-bottom: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _parse_ts(value: str | None, timezone: ZoneInfo) -> dt.datetime | None:
    try:
        return parse_backend_utc(value, timezone) if value else None
    except Exception:
        return None


def _series_df(points: list[dict[str, Any]], timezone: ZoneInfo, series_name: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for point in points or []:
        ts = _parse_ts(point.get("x"), timezone)
        if ts is None and point.get("x"):
            try:
                ts = dt.datetime.fromisoformat(str(point.get("x"))).replace(tzinfo=timezone)
            except Exception:
                ts = None
        rows.append(
            {
                "date": ts.date() if ts else point.get("x"),
                "value": float(point.get("y", 0) or 0),
                "series": series_name,
            }
        )
    return pd.DataFrame(rows)


def _kpi_lookup(kpis: list[dict[str, Any]]) -> dict[str, Any]:
    return {item["key"]: item.get("value") for item in (kpis or [])}


def _metric_card(title: str, value: Any, subtitle: str, pill: str | None = None) -> None:
    rendered = f"{int(value):,}" if isinstance(value, (int, float)) and float(value).is_integer() else f"{value}"
    pill_html = f'<div class="admin-pill">{pill}</div>' if pill else ""
    st.markdown(
        f"""
        <div class="admin-card">
          <div class="admin-card-title">{title}</div>
          <div class="admin-card-value">{rendered}</div>
          <div class="admin-card-sub">{subtitle}</div>
          {pill_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_ts(value: str | None, timezone: ZoneInfo, fallback: str = "—") -> str:
    ts = _parse_ts(value, timezone)
    return ts.strftime("%Y-%m-%d %H:%M") if ts else fallback


def _format_date(value: str | None, timezone: ZoneInfo, fallback: str = "—") -> str:
    ts = _parse_ts(value, timezone)
    return ts.strftime("%Y-%m-%d") if ts else fallback


def _days_since(value: str | None, timezone: ZoneInfo) -> int | None:
    ts = _parse_ts(value, timezone)
    if ts is None:
        return None
    return max((dt.datetime.now(timezone) - ts).days, 0)


def _safe_strftime(value: Any, fmt: str, fallback: str = "—") -> str:
    if value is None or pd.isna(value):
        return fallback
    return value.strftime(fmt)


def _project_health(row: pd.Series, stale_days: int) -> str:
    if bool(row.get("closed")):
        return "Closed"
    days_since_activity = row.get("days_since_activity")
    if pd.isna(days_since_activity):
        return "Dormant" if int(row.get("members_count", 0)) <= 1 else "Needs attention"
    if int(days_since_activity) >= stale_days:
        return "Needs attention"
    return "Healthy"


def _load_all_projects(headers: dict, organization_id: str) -> dict:
    first_page = fetch_organization_projects_summary(
        headers=headers,
        organization_id=organization_id,
        status="all",
        sort="last_activity_at",
        page=1,
        page_size=100,
    )
    items = list(first_page.get("items", []))
    total = int(first_page.get("total", len(items)))
    pages = max((total - 1) // 100 + 1, 1)
    for page in range(2, pages + 1):
        payload = fetch_organization_projects_summary(
            headers=headers,
            organization_id=organization_id,
            status="all",
            sort="last_activity_at",
            page=page,
            page_size=100,
        )
        items.extend(payload.get("items", []))
    first_page["items"] = items
    return first_page


def _load_all_users(headers: dict, organization_id: str) -> dict:
    first_page = fetch_organization_users_summary(
        headers=headers,
        organization_id=organization_id,
        status="all",
        sort="last_login_at",
        page=1,
        page_size=100,
    )
    items = list(first_page.get("items", []))
    total = int(first_page.get("total", len(items)))
    pages = max((total - 1) // 100 + 1, 1)
    for page in range(2, pages + 1):
        payload = fetch_organization_users_summary(
            headers=headers,
            organization_id=organization_id,
            status="all",
            sort="last_login_at",
            page=page,
            page_size=100,
        )
        items.extend(payload.get("items", []))
    first_page["items"] = items
    return first_page


def _project_dataframe(items: list[dict[str, Any]], timezone: ZoneInfo, stale_days: int) -> pd.DataFrame:
    df = pd.DataFrame(items or [])
    if df.empty:
        return pd.DataFrame(
            columns=[
                "name",
                "site_code",
                "closed",
                "created_at",
                "created_by_name",
                "last_activity_at",
                "members_count",
                "task_count",
                "completed_task_count",
                "percent_complete",
            ]
        )

    df["created_at_dt"] = df["created_at"].map(lambda value: _parse_ts(value, timezone))
    df["last_activity_at_dt"] = df["last_activity_at"].map(lambda value: _parse_ts(value, timezone))
    df["created_on"] = df["created_at_dt"].map(lambda value: _safe_strftime(value, "%Y-%m-%d"))
    df["last_activity"] = df["last_activity_at_dt"].map(lambda value: _safe_strftime(value, "%Y-%m-%d %H:%M"))
    df["days_since_activity"] = df["last_activity_at_dt"].map(
        lambda value: (dt.datetime.now(timezone) - value).days if value is not None and not pd.isna(value) else pd.NA
    )
    df["progress_pct"] = (pd.to_numeric(df["percent_complete"], errors="coerce").fillna(0) * 100).round(1)
    df["health"] = df.apply(lambda row: _project_health(row, stale_days), axis=1)
    return df


def _user_dataframe(items: list[dict[str, Any]], timezone: ZoneInfo) -> pd.DataFrame:
    df = pd.DataFrame(items or [])
    if df.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "name",
                "email",
                "role",
                "status",
                "joined_at",
                "last_login_at",
                "last_activity_at",
            ]
        )

    for source_col, target_col in (
        ("joined_at", "joined_at_dt"),
        ("last_login_at", "last_login_at_dt"),
        ("last_activity_at", "last_activity_at_dt"),
    ):
        df[target_col] = df[source_col].map(lambda value: _parse_ts(value, timezone))
    df["joined_on"] = df["joined_at_dt"].map(lambda value: _safe_strftime(value, "%Y-%m-%d"))
    df["last_login"] = df["last_login_at_dt"].map(lambda value: _safe_strftime(value, "%Y-%m-%d %H:%M"))
    df["last_activity"] = df["last_activity_at_dt"].map(lambda value: _safe_strftime(value, "%Y-%m-%d %H:%M"))
    df["status_label"] = df["status"].map(lambda value: USER_STATUS_LABELS.get(value, str(value).replace("_", " ").title()))
    return df


def _trend_chart(df: pd.DataFrame, title: str, color_scale: alt.Scale | None = None) -> None:
    if df.empty:
        st.info(f"No {title.lower()} data yet.")
        return

    chart = (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title=None),
            color=alt.Color("series:N", title=None, scale=color_scale),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("value:Q", title="Value", format=",.0f"),
            ],
        )
        .properties(height=280, title=title)
    )
    st.altair_chart(chart, width="stretch")


def _bar_chart(df: pd.DataFrame, x: str, y: str, color: str, title: str, *, height: int = 280) -> None:
    if df.empty:
        st.info(f"No {title.lower()} data yet.")
        return
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
        .encode(
            x=alt.X(f"{x}:N", sort="-y", title=None),
            y=alt.Y(f"{y}:Q", title=None),
            color=alt.Color(f"{color}:N", title=None, scale=alt.Scale(domain=df[color].tolist(), range=df["color"].tolist())),
            tooltip=[alt.Tooltip(f"{x}:N", title=x.replace("_", " ").title()), alt.Tooltip(f"{y}:Q", format=",.0f")],
        )
        .properties(height=height, title=title)
    )
    st.altair_chart(chart, width="stretch")


def _render_activity_feed(items: list[dict[str, Any]], timezone: ZoneInfo) -> None:
    if not items:
        st.info("No recent organization activity yet.")
        return
    for item in items:
        headline = item.get("project_name") or item.get("user_name") or "Organization"
        context = []
        if item.get("user_name"):
            context.append(item["user_name"])
        if item.get("project_name"):
            context.append(item["project_name"])
        suffix = " • ".join(context)
        st.markdown(
            f"""
            <div class="admin-feed-item">
              <div><strong>{headline}</strong> • {str(item.get("event_type", "")).replace("_", " ").title()}</div>
              <div style="color:#475467; font-size:0.92rem;">{suffix or item.get("source", "activity")} • {_format_ts(item.get("ts"), timezone)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_projects_tab(projects_df: pd.DataFrame, timezone: ZoneInfo) -> None:
    st.subheader("Projects")
    if projects_df.empty:
        st.info("No projects found for this organization.")
        return

    with st.popover("Filters", icon=":material/filter_alt:"):
        status_filter = st.multiselect("Project state", ["Open", "Closed"], default=["Open", "Closed"])
        health_filter = st.multiselect(
            "Health",
            sorted(projects_df["health"].unique().tolist()),
            default=sorted(projects_df["health"].unique().tolist()),
        )
        owner_options = sorted([value for value in projects_df["created_by_name"].dropna().unique().tolist() if value])
        owner_filter = st.multiselect("Owner", owner_options, default=owner_options)
        sort_choice = st.selectbox("Sort", ["Most recent activity", "Newest", "Highest completion", "Most tasks"])

    filtered = projects_df.copy()
    if status_filter and len(status_filter) < 2:
        want_closed = "Closed" in status_filter
        filtered = filtered[filtered["closed"] == want_closed]
    if health_filter:
        filtered = filtered[filtered["health"].isin(health_filter)]
    if owner_filter:
        filtered = filtered[filtered["created_by_name"].fillna("Unknown").isin(owner_filter)]

    if sort_choice == "Newest":
        filtered = filtered.sort_values("created_at_dt", ascending=False)
    elif sort_choice == "Highest completion":
        filtered = filtered.sort_values(["progress_pct", "task_count"], ascending=[False, False])
    elif sort_choice == "Most tasks":
        filtered = filtered.sort_values(["task_count", "progress_pct"], ascending=[False, False])
    else:
        filtered = filtered.sort_values("last_activity_at_dt", ascending=False, na_position="last")

    top_left, top_right = st.columns([1.25, 1])
    with top_left:
        health_counts = filtered["health"].value_counts().rename_axis("health").reset_index(name="count")
        health_counts["color"] = health_counts["health"].map(PROJECT_HEALTH_COLORS)
        _bar_chart(health_counts, "health", "count", "health", "Project health mix")
    with top_right:
        stale = filtered[
            (~filtered["closed"])
            & (filtered["days_since_activity"].fillna(9999) >= 14)
        ][["name", "site_code", "days_since_activity", "created_by_name", "progress_pct"]].copy()
        st.markdown("##### Needs follow-up")
        if stale.empty:
            st.success("No open projects are currently stale.")
        else:
            stale = stale.rename(
                columns={
                    "name": "Project",
                    "site_code": "Site",
                    "days_since_activity": "Days idle",
                    "created_by_name": "Owner",
                    "progress_pct": "Complete (%)",
                }
            )
            st.dataframe(stale.head(8), width="stretch", hide_index=True)

    st.markdown("##### Portfolio rollup")
    project_view = filtered[
        [
            "name",
            "site_code",
            "health",
            "created_on",
            "created_by_name",
            "last_activity",
            "members_count",
            "task_count",
            "completed_task_count",
            "progress_pct",
        ]
    ].rename(
        columns={
            "name": "Project",
            "site_code": "Site",
            "health": "Health",
            "created_on": "Created",
            "created_by_name": "Owner",
            "last_activity": "Last activity",
            "members_count": "Members",
            "task_count": "Tasks",
            "completed_task_count": "Completed",
            "progress_pct": "Complete (%)",
        }
    )
    st.dataframe(project_view, width="stretch", hide_index=True)


def _render_users_tab(
    users_df: pd.DataFrame,
    organization_id: str,
    scoped_headers: dict,
    timezone: ZoneInfo,
    actor_role: str,
    current_user_id: str,
) -> None:
    st.subheader("Users")
    if users_df.empty:
        st.info("No users found for this organization.")
        return

    with st.popover("Filters", icon=":material/filter_alt:"):
        segment = st.pills(
            "Segment",
            options=[
                "All",
                "Active in 7d",
                "Active in 30d",
                "Never logged in",
                "Inactive",
                "Org admins",
                "Project managers",
            ],
            default="All",
        )
        role_options = sorted(users_df["role"].dropna().unique().tolist())
        role_filter = st.multiselect("Role", role_options, default=role_options)
        sort_choice = st.selectbox("Sort", ["Last login", "Last activity", "Joined", "Most projects"])

    filtered = users_df.copy()
    if role_filter:
        filtered = filtered[filtered["role"].isin(role_filter)]

    if segment == "Active in 7d":
        filtered = filtered[filtered["login_count_7d"] > 0]
    elif segment == "Active in 30d":
        filtered = filtered[filtered["login_count_30d"] > 0]
    elif segment == "Never logged in":
        filtered = filtered[filtered["status"] == "never_logged_in"]
    elif segment == "Inactive":
        filtered = filtered[filtered["status"] == "inactive"]
    elif segment == "Org admins":
        filtered = filtered[filtered["role"].isin(["ORG_OWNER", "ORG_ADMIN"])]
    elif segment == "Project managers":
        filtered = filtered[filtered["role"] == "PROJECT_MANAGER"]

    if sort_choice == "Joined":
        filtered = filtered.sort_values("joined_at_dt", ascending=False)
    elif sort_choice == "Last activity":
        filtered = filtered.sort_values("last_activity_at_dt", ascending=False, na_position="last")
    elif sort_choice == "Most projects":
        filtered = filtered.sort_values(["project_count", "owned_project_count"], ascending=[False, False])
    else:
        filtered = filtered.sort_values("last_login_at_dt", ascending=False, na_position="last")

    top_left, top_right = st.columns([1.1, 1])
    with top_left:
        status_counts = filtered["status_label"].value_counts().rename_axis("status").reset_index(name="count")
        status_counts["color"] = status_counts["status"].map(
            lambda label: USER_STATUS_COLORS.get(
                next((key for key, value in USER_STATUS_LABELS.items() if value == label), "inactive"),
                "#475467",
            )
        )
        _bar_chart(status_counts, "status", "count", "status", "Adoption segments")
    with top_right:
        st.markdown("##### Follow-up queue")
        follow_up = filtered[
            (filtered["status"].isin(["never_logged_in", "inactive", "logged_in_no_activity"]))
        ][["name", "email", "role", "status_label", "last_login", "project_count"]].copy()
        if follow_up.empty:
            st.success("Everyone has healthy recent usage signals.")
        else:
            follow_up = follow_up.rename(
                columns={
                    "name": "User",
                    "email": "Email",
                    "role": "Role",
                    "status_label": "Status",
                    "last_login": "Last login",
                    "project_count": "Projects",
                }
            )
            st.dataframe(follow_up.head(8), width="stretch", hide_index=True)

    st.markdown("##### User rollup")
    users_view = filtered[
        [
            "name",
            "email",
            "role",
            "status_label",
            "joined_on",
            "last_login",
            "last_activity",
            "login_count_7d",
            "login_count_30d",
            "active_days_30d",
            "project_count",
            "owned_project_count",
        ]
    ].rename(
        columns={
            "name": "User",
            "email": "Email",
            "role": "Role",
            "status_label": "Status",
            "joined_on": "Joined",
            "last_login": "Last login",
            "last_activity": "Last activity",
            "login_count_7d": "Logins (7d)",
            "login_count_30d": "Logins (30d)",
            "active_days_30d": "Active days (30d)",
            "project_count": "Projects",
            "owned_project_count": "Owned",
        }
    )
    st.dataframe(users_view, width="stretch", hide_index=True)

    detail_source = filtered if not filtered.empty else users_df
    detail_options = detail_source[["user_id", "name", "email"]].drop_duplicates().to_dict("records")
    selected_user = st.selectbox(
        "Inspect user",
        options=detail_options,
        format_func=lambda item: f"{item['name']} • {item['email']}",
        index=0,
    )
    if not selected_user:
        return

    detail = fetch_organization_user_detail(
        headers=scoped_headers,
        organization_id=organization_id,
        user_id=selected_user["user_id"],
    )
    user = detail["user"]
    selected_user_role = str(user.get("role") or "")
    assignable_roles = _assignable_org_roles(actor_role)

    st.markdown("##### User detail")
    detail_left, detail_right = st.columns([1.2, 1])
    with detail_left:
        a, b, c, d = st.columns(4)
        with a:
            st.metric("Last login", _format_date(user.get("last_login_at"), timezone))
        with b:
            st.metric("Last activity", _format_date(user.get("last_activity_at"), timezone))
        with c:
            st.metric("Projects", int(user.get("project_count", 0)))
        with d:
            st.metric("Owned", int(user.get("owned_project_count", 0)))

        login_df = _series_df(detail.get("login_timeline_30d", []), timezone, "Logins")
        _trend_chart(login_df, "30-day login trend", alt.Scale(domain=["Logins"], range=["#0ea5e9"]))

    with detail_right:
        activity_items = detail.get("recent_activity", [])
        st.markdown("###### Recent activity")
        _render_activity_feed(activity_items[:8], timezone)

        st.markdown("###### Role access")
        st.caption(f"Your assignment ceiling for this org is based on your role: {actor_role}.")
        if str(selected_user["user_id"]) == str(current_user_id):
            st.info("Your own org role can’t be changed from this panel.")
        elif not assignable_roles:
            st.info("Your current role does not allow organization role changes.")
        elif not _can_manage_org_role(actor_role, selected_user_role):
            st.info(f"This user currently has `{selected_user_role}` access, which you can’t modify from your role.")
        else:
            default_role = selected_user_role if selected_user_role in assignable_roles else assignable_roles[0]
            target_role = st.selectbox(
                "Assign org role",
                options=assignable_roles,
                index=assignable_roles.index(default_role),
                key=f"assign_org_role_{selected_user['user_id']}",
                help="Role changes follow the backend ceiling rules and cannot assign ORG_OWNER from normal admin actions.",
            )
            if st.button(
                "Update org role",
                key=f"update_org_role_{selected_user['user_id']}",
                type="primary",
                width="stretch",
                disabled=target_role == selected_user_role,
            ):
                try:
                    update_organization_user_role(
                        headers=scoped_headers,
                        organization_id=organization_id,
                        user_id=selected_user["user_id"],
                        role=target_role,
                    )
                except Exception as exc:
                    st.error(f"Unable to update org role: {exc}")
                else:
                    _clear_admin_caches()
                    st.success(f"Updated {selected_user['name']} to {target_role}.")
                    st.rerun()

    memberships_col, projects_col = st.columns(2)
    with memberships_col:
        member_projects = pd.DataFrame(detail.get("projects", []))
        st.markdown("###### Member projects")
        if member_projects.empty:
            st.info("This user is not assigned to any projects.")
        else:
            member_projects["percent_complete"] = (pd.to_numeric(member_projects["percent_complete"], errors="coerce").fillna(0) * 100).round(1)
            member_projects = member_projects[["name", "site_code", "members_count", "task_count", "percent_complete"]].rename(
                columns={
                    "name": "Project",
                    "site_code": "Site",
                    "members_count": "Members",
                    "task_count": "Tasks",
                    "percent_complete": "Complete (%)",
                }
            )
            st.dataframe(member_projects, width="stretch", hide_index=True)
    with projects_col:
        owned_projects = pd.DataFrame(detail.get("owned_projects", []))
        st.markdown("###### Owned projects")
        if owned_projects.empty:
            st.info("This user has not created any projects.")
        else:
            owned_projects["percent_complete"] = (pd.to_numeric(owned_projects["percent_complete"], errors="coerce").fillna(0) * 100).round(1)
            owned_projects = owned_projects[["name", "site_code", "task_count", "completed_task_count", "percent_complete"]].rename(
                columns={
                    "name": "Project",
                    "site_code": "Site",
                    "task_count": "Tasks",
                    "completed_task_count": "Completed",
                    "percent_complete": "Complete (%)",
                }
            )
            st.dataframe(owned_projects, width="stretch", hide_index=True)


def main() -> None:
    require_admin()
    _page_css()
    timezone = ZoneInfo(st.context.timezone)
    base_headers = st.session_state.get("auth_headers", {}) or {}
    user = get_user(base_headers, timezone=timezone)

    memberships = [membership for membership in user.organizations if membership.is_active]
    if not memberships:
        st.info("No active organizations are attached to this account.")
        return

    admin_memberships = [membership for membership in memberships if membership.role in ADMIN_ROLES]
    org_options = admin_memberships or memberships

    default_org_id = st.session_state.get("admin_org_id")
    if default_org_id not in {membership.organization_id for membership in org_options}:
        default_org_id = org_options[0].organization_id
        st.session_state["admin_org_id"] = default_org_id

    with st.sidebar:
        st.subheader("Admin dashboard")
        selected_org_id = st.selectbox(
            "Organization",
            options=org_options,
            index=next(
                (index for index, item in enumerate(org_options) if item.organization_id == default_org_id),
                0,
            ),
            format_func=lambda membership: f"{membership.organization.name if membership.organization else membership.organization_id} ({membership.role})",
        )
        st.session_state["admin_org_id"] = selected_org_id.organization_id
        stale_days = st.slider("Stale threshold (days)", min_value=7, max_value=45, value=14, step=1)
        refresh = st.button("Refresh data", type="primary", width="stretch")
        st.caption("Project and user rollups update against the selected organization context.")

    if refresh:
        _clear_admin_caches()

    scoped_headers = headers_for_organization(base_headers, selected_org_id.organization_id)
    organization_id = selected_org_id.organization_id

    try:
        dashboard = fetch_organization_dashboard(headers=scoped_headers, organization_id=organization_id)
        projects_payload = _load_all_projects(scoped_headers, organization_id)
        users_payload = _load_all_users(scoped_headers, organization_id)
        activity_payload = fetch_organization_activity(
            headers=scoped_headers,
            organization_id=organization_id,
            limit=12,
        )
    except Exception as exc:
        st.error(f"Unable to load organization admin data: {exc}")
        return

    organization = dashboard.get("organization", {})
    kpis = _kpi_lookup(dashboard.get("kpis", []))
    projects_df = _project_dataframe(projects_payload.get("items", []), timezone, stale_days)
    users_df = _user_dataframe(users_payload.get("items", []), timezone)
    as_of = _format_ts(dashboard.get("as_of"), timezone)

    dau_df = _series_df(dashboard.get("daily_active_users", []), timezone, "Daily active users")
    login_df = _series_df(dashboard.get("login_events_by_day", []), timezone, "Login events")
    project_activity_df = _series_df(dashboard.get("project_activity_by_day", []), timezone, "Project activity")
    top_trend_df = pd.concat([dau_df, login_df, project_activity_df], ignore_index=True)

    inactive_share = 0
    if not users_df.empty:
        inactive_share = round(
            100
            * float(
                users_df["status"].isin(["inactive", "never_logged_in", "logged_in_no_activity"]).sum()
                / max(len(users_df), 1)
            )
        )
    project_velocity = round(
        float(project_activity_df["value"].tail(7).sum() / max(min(len(project_activity_df), 7), 1)),
        1,
    ) if not project_activity_df.empty else 0.0

    st.markdown(
        f"""
        <div class="admin-shell">
          <div class="admin-eyebrow">Organization Admin Dashboard</div>
          <div class="admin-hero-title">{organization.get("name", "Organization overview")}</div>
          <div class="admin-hero-copy">
            Monitor adoption, project momentum, and follow-up opportunities across the organization.
            Snapshot captured {as_of}.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    hero_stats = st.columns(3)
    with hero_stats[0]:
        st.markdown(
            f"""
            <div class="admin-hero-stat">
              <div class="admin-hero-stat-label">Adoption pulse</div>
              <div class="admin-hero-stat-value">{int(kpis.get("active_users_30d", 0)):,} active users / 30d</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_stats[1]:
        st.markdown(
            f"""
            <div class="admin-hero-stat">
              <div class="admin-hero-stat-label">Portfolio motion</div>
              <div class="admin-hero-stat-value">{project_velocity} project events / day</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with hero_stats[2]:
        st.markdown(
            f"""
            <div class="admin-hero-stat">
              <div class="admin-hero-stat-label">Follow-up exposure</div>
              <div class="admin-hero-stat-value">{inactive_share}% of users need outreach</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    metrics = st.columns(4)
    with metrics[0]:
        _metric_card(
            "Users",
            kpis.get("total_users", 0),
            f"{int(kpis.get('active_users_7d', 0)):,} active in the last 7 days",
            pill=f"{int(kpis.get('pending_invites', 0)):,} pending invites",
        )
    with metrics[1]:
        _metric_card(
            "Projects",
            kpis.get("total_projects", 0),
            f"{int(kpis.get('open_projects', 0)):,} open • {int(kpis.get('closed_projects', 0)):,} closed",
            pill=f"{int(kpis.get('projects_updated_7d', 0)):,} updated in 7d",
        )
    with metrics[2]:
        _metric_card(
            "Activity",
            int(login_df["value"].tail(7).sum()) if not login_df.empty else 0,
            "Login events in the last 7 days",
        )
    with metrics[3]:
        stale_open_count = int((projects_df["health"] == "Needs attention").sum()) if not projects_df.empty else 0
        _metric_card(
            "Risk",
            stale_open_count,
            "Open projects beyond the stale threshold",
        )

    insight_left, insight_right = st.columns([1.5, 1])
    with insight_left:
        st.markdown("#### Usage trends")
        _trend_chart(
            top_trend_df,
            "30-day organization trend",
            alt.Scale(
                domain=["Daily active users", "Login events", "Project activity"],
                range=["#0ea5e9", "#f97316", "#10b981"],
            ),
        )
    with insight_right:
        st.markdown("#### Admin cues")
        stale_projects = pd.DataFrame(dashboard.get("stale_projects", []))
        recent_users = pd.DataFrame(dashboard.get("recent_users", []))

        if int(kpis.get("pending_invites", 0)) > 0:
            st.markdown(
                f'<div class="admin-insight"><strong>{int(kpis.get("pending_invites", 0))} pending invite(s)</strong><br/>There are users who have been invited but have not completed onboarding yet.</div>',
                unsafe_allow_html=True,
            )
        if stale_projects.empty:
            st.markdown(
                '<div class="admin-insight"><strong>Project momentum looks healthy</strong><br/>No stale projects were surfaced in the dashboard snapshot.</div>',
                unsafe_allow_html=True,
            )
        else:
            names = ", ".join(stale_projects["name"].head(3).tolist())
            st.markdown(
                f'<div class="admin-insight"><strong>Stale project watchlist</strong><br/>{names} should be checked for blockers or ownership gaps.</div>',
                unsafe_allow_html=True,
            )
        if not recent_users.empty:
            recent_names = ", ".join(recent_users["name"].head(3).tolist())
            st.markdown(
                f'<div class="admin-insight"><strong>Newest members</strong><br/>{recent_names} joined recently and are good candidates for onboarding follow-up.</div>',
                unsafe_allow_html=True,
            )

        with st.expander("Recent activity feed", expanded=False):
            _render_activity_feed(activity_payload.get("items", []), timezone)

    projects_tab, users_tab = st.tabs(["Projects", "Users"])
    with projects_tab:
        _render_projects_tab(projects_df, timezone)
    with users_tab:
        _render_users_tab(users_df, organization_id, scoped_headers, timezone, selected_org_id.role, user.id)


if __name__ == "__main__":
    main()
