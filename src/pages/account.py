from __future__ import annotations

import datetime as dt
from textwrap import dedent
from zoneinfo import ZoneInfo

import streamlit as st

from logic.backend.guards import require_login
from logic.backend.users import get_user
from models.organization import OrganizationMembership
from models.user import User
from ui.utils.page_header import render_registered_page_header


def _format_timestamp(value: dt.datetime | None) -> str:
    if value is None:
        return "Never"
    return value.strftime("%b %d, %Y at %I:%M %p")


def _format_provider(provider: str | None) -> str:
    if not provider:
        return "Unknown"
    normalized = provider.replace("_", " ").replace("-", " ").strip()
    if not normalized:
        return "Unknown"
    return normalized.title()


def _format_role(role: str | None) -> str:
    if not role:
        return "Member"
    normalized = role.replace("_", " ").replace("-", " ").strip()
    if not normalized:
        return "Member"
    return normalized.title()


def _initials(name: str) -> str:
    parts = [part for part in name.split() if part.strip()]
    if not parts:
        return "?"
    return "".join(part[0] for part in parts[:2]).upper()


def _status_label(is_active: bool) -> str:
    return "Active" if is_active else "Inactive"


def _inject_account_css() -> None:
    st.markdown(
        """
        <style>
        .stMainBlockContainer {
            max-width: 1220px;
            padding-top: 2.1rem;
            padding-bottom: 3rem;
        }

        .account-shell {
            --ink: #132124;
            --muted: #5f6f72;
            --line: rgba(19, 33, 36, 0.12);
            --soft: #eef3f1;
            --panel: rgba(255, 255, 255, 0.78);
            --accent: #0f766e;
            --accent-soft: rgba(15, 118, 110, 0.12);
            color: var(--ink);
        }

        .account-hero {
            position: relative;
            overflow: hidden;
            padding: 2.4rem 2.5rem 2.2rem;
            border: 1px solid rgba(19, 33, 36, 0.08);
            border-radius: 28px;
            background:
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.18), transparent 28%),
                linear-gradient(135deg, #f7fbfa 0%, #edf5f3 48%, #f8fbfb 100%);
        }

        .account-hero::after {
            content: "";
            position: absolute;
            inset: auto -8% -35% auto;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: rgba(15, 118, 110, 0.08);
            filter: blur(6px);
        }

        .account-kicker {
            margin: 0 0 0.8rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: var(--accent);
        }

        .account-hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1.5rem;
            align-items: end;
        }

        .account-title {
            margin: 0;
            font-size: clamp(2rem, 3.6vw, 3.4rem);
            line-height: 0.95;
            letter-spacing: -0.04em;
            font-weight: 700;
            color: #102628;
        }

        .account-subtitle {
            margin: 0.8rem 0 0;
            max-width: 46rem;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.6;
        }

        .account-identity {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 92px;
            height: 92px;
            border-radius: 24px;
            background: linear-gradient(135deg, #123c3d 0%, #0f766e 100%);
            color: white;
            font-size: 1.8rem;
            font-weight: 700;
            box-shadow: 0 20px 40px rgba(18, 60, 61, 0.18);
        }

        .account-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin-top: 1.35rem;
        }

        .account-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            min-height: 36px;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            border: 1px solid rgba(19, 33, 36, 0.08);
            background: rgba(255, 255, 255, 0.72);
            color: #183235;
            font-size: 0.92rem;
        }

        .account-section {
            margin-top: 1.1rem;
            padding: 1.5rem 1.6rem 1.3rem;
            border-radius: 24px;
            border: 1px solid var(--line);
            background: var(--panel);
            backdrop-filter: blur(10px);
        }

        .account-section-title {
            margin: 0;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--muted);
        }

        .account-section-copy {
            margin: 0.45rem 0 0;
            color: var(--muted);
            font-size: 0.96rem;
            line-height: 1.55;
        }

        .account-detail-list {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 1rem;
            margin-top: 1.4rem;
        }

        .account-detail-row {
            display: grid;
            grid-template-columns: 9rem minmax(0, 1fr);
            gap: 1rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(19, 33, 36, 0.08);
        }

        .account-detail-row:first-child {
            padding-top: 0;
            border-top: 0;
        }

        .account-label {
            color: var(--muted);
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
        }

        .account-value {
            color: var(--ink);
            font-size: 1rem;
            line-height: 1.55;
            word-break: break-word;
        }

        .account-badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .account-badge {
            display: inline-flex;
            align-items: center;
            padding: 0.42rem 0.75rem;
            border-radius: 999px;
            background: var(--soft);
            color: #183235;
            font-size: 0.86rem;
            font-weight: 600;
        }

        .account-badge--accent {
            background: var(--accent-soft);
            color: var(--accent);
        }

        .account-membership-list {
            display: grid;
            gap: 0.95rem;
            margin-top: 1.35rem;
        }

        .account-membership {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1rem;
            padding: 1.15rem 1.1rem;
            border: 1px solid rgba(19, 33, 36, 0.07);
            border-radius: 22px;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(244,248,247,0.95) 100%);
            box-shadow: 0 10px 30px rgba(19, 33, 36, 0.04);
        }

        .account-membership:first-child {
            padding-top: 0;
            border-top: 0;
        }

        .account-membership-name {
            margin: 0;
            font-size: 1.08rem;
            font-weight: 600;
            color: #102628;
        }

        .account-membership-meta {
            margin: 0.42rem 0 0;
            color: var(--muted);
            font-size: 0.93rem;
            line-height: 1.55;
        }

        .account-membership-side {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            justify-content: center;
            gap: 0.6rem;
            text-align: right;
        }

        .account-status {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.45rem 0.72rem;
            border-radius: 999px;
            font-size: 0.84rem;
            font-weight: 700;
            background: #eaf4f1;
            color: #0d5d57;
        }

        .account-org-mark {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            color: #17393b;
        }

        .account-org-mark::before {
            content: "";
            width: 0.7rem;
            height: 0.7rem;
            border-radius: 50%;
            background: linear-gradient(135deg, #123c3d 0%, #0f766e 100%);
            box-shadow: 0 0 0 0.22rem rgba(15, 118, 110, 0.12);
            flex-shrink: 0;
        }

        .account-status::before {
            content: "";
            width: 0.5rem;
            height: 0.5rem;
            border-radius: 50%;
            background: currentColor;
        }

        .account-status--inactive {
            background: #f3f1ed;
            color: #7a6751;
        }

        .account-timeline {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 1.35rem;
        }

        .account-timeline-item {
            padding: 1rem 1.05rem;
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255,255,255,0.88) 0%, rgba(238,243,241,0.92) 100%);
            border: 1px solid rgba(19, 33, 36, 0.06);
        }

        .account-timeline-label {
            margin: 0;
            color: var(--muted);
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .account-timeline-value {
            margin: 0.45rem 0 0;
            color: var(--ink);
            font-size: 1rem;
            line-height: 1.45;
            font-weight: 600;
        }

        @media (max-width: 900px) {
            .account-hero {
                padding: 1.6rem 1.4rem;
                border-radius: 24px;
            }

            .account-hero-grid,
            .account-membership,
            .account-detail-row {
                grid-template-columns: minmax(0, 1fr);
            }

            .account-identity,
            .account-membership-side {
                justify-self: start;
                align-items: flex-start;
                text-align: left;
            }

            .account-membership {
                padding: 1rem;
            }

            .account-timeline {
                grid-template-columns: minmax(0, 1fr);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_profile_section(user: User) -> None:
    roles_markup = "".join(
        f"<span class='account-badge'>{role.get('name', 'Unknown role')}</span>"
        for role in user.roles
    ) or "<span class='account-badge'>No global roles assigned</span>"

    st.markdown(
        dedent(
            f"""
            <section class="account-section">
                <p class="account-section-title">Profile</p>
                <p class="account-section-copy">
                    The essentials tied to your signed-in GanttBuddy account.
                </p>
                <div class="account-detail-list">
                    <div class="account-detail-row">
                        <div class="account-label">Name</div>
                        <div class="account-value">{user.name}</div>
                    </div>
                    <div class="account-detail-row">
                        <div class="account-label">Email</div>
                        <div class="account-value">{user.email}</div>
                    </div>
                    <div class="account-detail-row">
                        <div class="account-label">Status</div>
                        <div class="account-value">
                            <span class="account-status{' account-status--inactive' if not user.is_active else ''}">
                                {_status_label(user.is_active)}
                            </span>
                        </div>
                    </div>
                    <div class="account-detail-row">
                        <div class="account-label">Sign-in</div>
                        <div class="account-value">{_format_provider(user.auth_provider)}</div>
                    </div>
                    <div class="account-detail-row">
                        <div class="account-label">Roles</div>
                        <div class="account-value">
                            <div class="account-badge-row">{roles_markup}</div>
                        </div>
                    </div>
                </div>
            </section>
            """
        ),
        unsafe_allow_html=True,
    )


def _render_access_section(memberships: list[OrganizationMembership]) -> None:
    if not memberships:
        st.markdown(
            dedent(
                """
                <section class="account-section">
                    <p class="account-section-title">Access</p>
                    <p class="account-section-copy">
                        You do not belong to any active organizations yet.
                    </p>
                </section>
                """
            ),
            unsafe_allow_html=True,
        )
        return

    items_markup = []
    for membership in memberships:
        organization = membership.organization
        org_name = organization.name if organization is not None else "Organization"
        org_state = "Active org" if organization is None or organization.is_active else "Inactive org"
        items_markup.append(
            dedent(
                f"""
                <div class="account-membership">
                    <div>
                        <p class="account-membership-name">
                            <span class="account-org-mark">{org_name}</span>
                        </p>
                        <p class="account-membership-meta">
                            Joined {_format_timestamp(membership.joined_at)}
                        </p>
                    </div>
                    <div class="account-membership-side">
                        <span class="account-badge account-badge--accent">{_format_role(membership.role)}</span>
                        <span class="account-membership-meta">{org_state}</span>
                    </div>
                </div>
                """
            ).strip()
        )

    st.markdown(
        dedent(
            f"""
            <section class="account-section">
                <p class="account-section-title">Access</p>
                <p class="account-section-copy">
                    Your current organization memberships and the role attached to each one.
                </p>
                <div class="account-membership-list">{''.join(items_markup)}</div>
            </section>
            """
        ),
        unsafe_allow_html=True,
    )


def _render_activity_section(user: User) -> None:
    st.markdown(
        dedent(
            f"""
            <section class="account-section">
                <p class="account-section-title">Account Activity</p>
                <p class="account-section-copy">
                    A quick view of when this account was created and most recently used.
                </p>
                <div class="account-timeline">
                    <div class="account-timeline-item">
                        <p class="account-timeline-label">Created</p>
                        <p class="account-timeline-value">{_format_timestamp(user.created_at)}</p>
                    </div>
                    <div class="account-timeline-item">
                        <p class="account-timeline-label">Last Login</p>
                        <p class="account-timeline-value">{_format_timestamp(user.last_login_at)}</p>
                    </div>
                </div>
            </section>
            """
        ),
        unsafe_allow_html=True,
    )


def main() -> None:
    require_login()
    _inject_account_css()

    timezone = ZoneInfo(st.context.timezone)
    auth_headers = st.session_state.get("auth_headers", {})

    try:
        user = get_user(auth_headers, timezone=timezone)
    except Exception as exc:
        st.error(f"Unable to load your account details right now. {exc}")
        st.stop()

    active_memberships = sorted(
        [membership for membership in user.organizations if membership.is_active],
        key=lambda membership: membership.joined_at,
    )
    primary_org_name = (
        active_memberships[0].organization.name
        if active_memberships and active_memberships[0].organization is not None
        else "No organization selected"
    )

    role_count = len(user.roles)
    org_count = len(active_memberships)

    st.markdown('<div class="account-shell">', unsafe_allow_html=True)
    render_registered_page_header(
        "account",
        title=user.name,
        description=f"Signed in as {user.email}. Review account activity, global roles, and organization access from one place.",
        chips=[
            _status_label(user.is_active),
            f"{role_count} global role{'s' if role_count != 1 else ''}" if role_count > 0 else "",
            f"{org_count} organization{'s' if org_count != 1 else ''}" if org_count > 1 else "",
            primary_org_name if org_count >= 1 else "",
        ],
    )

    left_col, right_col = st.columns([1.05, 1.2], gap="large")
    with left_col:
        _render_profile_section(user)
        _render_activity_section(user)

    with right_col:
        _render_access_section(active_memberships)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
