from __future__ import annotations

from dataclasses import dataclass
from html import escape

import streamlit as st


@dataclass(frozen=True)
class HeaderPalette:
    accent: str
    accent_soft: str
    glow: str
    surface_start: str
    surface_end: str
    ink: str = "#0f172a"
    muted: str = "#475569"


@dataclass(frozen=True)
class PageHeaderPreset:
    eyebrow: str
    title: str
    description: str
    palette: str


HEADER_PALETTES: dict[str, HeaderPalette] = {
    "teal": HeaderPalette(
        accent="#0f766e",
        accent_soft="rgba(15, 118, 110, 0.14)",
        glow="rgba(15, 118, 110, 0.18)",
        surface_start="#f7fbfa",
        surface_end="#edf5f3",
    ),
    "sky": HeaderPalette(
        accent="#0369a1",
        accent_soft="rgba(3, 105, 161, 0.14)",
        glow="rgba(14, 165, 233, 0.18)",
        surface_start="#f5fbff",
        surface_end="#e9f5ff",
    ),
    "amber": HeaderPalette(
        accent="#b45309",
        accent_soft="rgba(180, 83, 9, 0.14)",
        glow="rgba(245, 158, 11, 0.18)",
        surface_start="#fffaf1",
        surface_end="#fff2dc",
    ),
    "slate": HeaderPalette(
        accent="#334155",
        accent_soft="rgba(51, 65, 85, 0.14)",
        glow="rgba(71, 85, 105, 0.18)",
        surface_start="#f8fafc",
        surface_end="#edf2f7",
    ),
    "rose": HeaderPalette(
        accent="#be185d",
        accent_soft="rgba(190, 24, 93, 0.14)",
        glow="rgba(244, 114, 182, 0.16)",
        surface_start="#fff7fb",
        surface_end="#fdf0f6",
    ),
    "indigo": HeaderPalette(
        accent="#4338ca",
        accent_soft="rgba(67, 56, 202, 0.14)",
        glow="rgba(99, 102, 241, 0.16)",
        surface_start="#f7f8ff",
        surface_end="#eef0ff",
    ),
    "navy": HeaderPalette(
        accent="#f8fafc",
        accent_soft="rgba(224, 242, 254, 0.16)",
        glow="rgba(56, 189, 248, 0.18)",
        surface_start="#0f172a",
        surface_end="#1e293b",
        ink="#ffffff",
        muted="rgba(248, 250, 252, 0.9)",
    ),
}


PAGE_HEADER_PRESETS: dict[str, PageHeaderPreset] = {
    "account": PageHeaderPreset(
        eyebrow="Account",
        title="Your Account",
        description="Review who you are signed in as, the roles attached to your account, and the organizations you can access.",
        palette="teal",
    ),
    "admin_overview": PageHeaderPreset(
        eyebrow="Organization Admin Overview",
        title="Organization Overview",
        description="Monitor adoption, project momentum, and follow-up opportunities across the organization from one workspace.",
        palette="navy",
    ),
    "admin_projects": PageHeaderPreset(
        eyebrow="Admin Projects",
        title="Projects and Access",
        description="Review portfolio health, inspect project activity, and manage who can view or edit each workspace.",
        palette="navy",
    ),
    "admin_users": PageHeaderPreset(
        eyebrow="Admin Users",
        title="Users and Adoption",
        description="Inspect participation, follow-up gaps, and organization roles across the members in your admin scope.",
        palette="navy",
    ),
    "home": PageHeaderPreset(
        eyebrow="Home",
        title="Workspace Home",
        description="Start from your current project signals, recent activity, and PM follow-ups without hunting across the app.",
        palette="sky",
    ),
    "projects": PageHeaderPreset(
        eyebrow="Projects",
        title="Load a Project",
        description="Browse the schedules you can access, review the project details, and drop straight back into the workspace.",
        palette="sky",
    ),
    "excel_import": PageHeaderPreset(
        eyebrow="Projects",
        title="Import from Excel",
        description="Preview a workbook before import, adjust the scan settings, and validate what will become a GanttBuddy project.",
        palette="amber",
    ),
    "feed": PageHeaderPreset(
        eyebrow="Projects",
        title="Activity Feed",
        description="Track project changes, recent events, and the workspaces that are moving fastest across your portfolio.",
        palette="indigo",
    ),
    "build": PageHeaderPreset(
        eyebrow="Projects",
        title="Build from Template",
        description="Spin up a new schedule from a supported template and shape the first version with project-specific inputs.",
        palette="amber",
    ),
    "plan": PageHeaderPreset(
        eyebrow="Workspace",
        title="Planning Workspace",
        description="Edit tasks, validate dependencies, and shape the schedule structure before execution.",
        palette="teal",
    ),
    "execute": PageHeaderPreset(
        eyebrow="Workspace",
        title="Execution Workspace",
        description="Capture progress, compare actuals against the plan, and keep field updates flowing back into the schedule.",
        palette="rose",
    ),
    "analyze": PageHeaderPreset(
        eyebrow="Workspace",
        title="Delay Analysis",
        description="Review delay records, inspect breakdowns, and understand where schedule pressure is accumulating.",
        palette="amber",
    ),
    "analytics": PageHeaderPreset(
        eyebrow="Workspace",
        title="Analytics",
        description="Track project performance, progress against plan, and inefficiencies.",
        palette="indigo",
    ),
    "signals": PageHeaderPreset(
        eyebrow="Workspace",
        title="Signals",
        description="Track time series data, set up alerts, and get ahead of project risks with automated insights on schedule health and progress.",
        palette="rose",
    ),
    "todos": PageHeaderPreset(
        eyebrow="Home",
        title="PM Todos",
        description="Manage action items for your projects, all in one place.",
        palette="teal",
    ),
    "manage": PageHeaderPreset(
        eyebrow="Manage",
        title="Operations Setup",
        description="Control the supporting pieces behind delivery, including crews, sites, and the operational structure around projects.",
        palette="slate",
    ),
    "login": PageHeaderPreset(
        eyebrow="Welcome",
        title="Sign in to GanttBuddy",
        description="Continue with your organization identity provider.",
        palette="sky",
    ),
}


def _inject_page_header_css() -> None:
    st.markdown(
        """
        <style>
        .gb-page-hero {
            position: relative;
            overflow: hidden;
            margin: 0 0 1.1rem;
            padding: 2rem 2.2rem 1.7rem;
            border-radius: 28px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background:
                radial-gradient(circle at top right, var(--gb-glow), transparent 28%),
                radial-gradient(circle at left center, var(--gb-accent-soft), transparent 24%),
                linear-gradient(135deg, var(--gb-surface-start) 0%, var(--gb-surface-end) 100%);
            box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
        }

        .gb-page-hero::after {
            content: "";
            position: absolute;
            right: -4.5rem;
            bottom: -5.5rem;
            width: 15rem;
            height: 15rem;
            border-radius: 999px;
            background: var(--gb-accent-soft);
            filter: blur(10px);
        }

        .gb-page-hero__content {
            position: relative;
            z-index: 1;
            max-width: 52rem;
        }

        .gb-page-hero__eyebrow {
            margin: 0 0 0.8rem;
            color: var(--gb-accent);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }

        .gb-page-hero__title {
            margin: 0;
            color: var(--gb-ink) !important;
            -webkit-text-fill-color: var(--gb-ink);
            font-family: "Space Grotesk", "Avenir Next", "Segoe UI", sans-serif;
            font-size: clamp(2rem, 3.4vw, 3.25rem);
            font-weight: 700;
            line-height: 0.96;
            letter-spacing: -0.04em;
            text-shadow: 0 1px 1px rgba(15, 23, 42, 0.32);
        }

        .gb-page-hero__description {
            margin: 0.85rem 0 0;
            color: var(--gb-muted) !important;
            font-size: 1rem;
            line-height: 1.6;
            max-width: 46rem;
        }

        .gb-page-hero__chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
            margin-top: 1.15rem;
        }

        .gb-page-hero__chip {
            display: inline-flex;
            align-items: center;
            min-height: 36px;
            padding: 0.46rem 0.82rem;
            border-radius: 999px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background: rgba(255, 255, 255, 0.72);
            color: var(--gb-ink);
            font-size: 0.9rem;
            line-height: 1;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.35);
        }

        .gb-page-hero[data-theme="navy"] .gb-page-hero__chip {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.12);
            color: #f8fafc;
        }

        .gb-page-aside {
            position: relative;
            overflow: hidden;
            margin: 0 0 1.1rem;
            padding: 1.35rem 1.35rem 1.2rem;
            border-radius: 24px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background:
                radial-gradient(circle at top right, rgba(255, 255, 255, 0.45), transparent 30%),
                linear-gradient(145deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%);
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
        }

        .gb-page-aside__eyebrow {
            margin: 0 0 0.5rem;
            color: var(--gb-aside-accent);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .gb-page-aside__title {
            margin: 0;
            color: #0f172a;
            font-size: 1.2rem;
            line-height: 1.08;
            font-weight: 700;
        }

        .gb-page-aside__body {
            margin: 0.65rem 0 0;
            color: #475569;
            font-size: 0.94rem;
            line-height: 1.55;
        }

        .gb-page-aside__chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin: 0.9rem 0 0;
        }

        .gb-page-aside__chip {
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: 0.42rem 0.72rem;
            border-radius: 999px;
            background: var(--gb-aside-soft);
            color: #0f172a;
            border: 1px solid rgba(15, 23, 42, 0.08);
            font-size: 0.84rem;
            line-height: 1;
        }

        .gb-page-stats {
            position: relative;
            overflow: hidden;
            margin: 0 0 1.1rem;
            padding: 1.2rem;
            border-radius: 24px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            background:
                radial-gradient(circle at top right, var(--gb-stats-soft), transparent 30%),
                linear-gradient(145deg, rgba(255,255,255,0.98) 0%, rgba(248,250,252,0.96) 100%);
            box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
        }

        .gb-page-stats__eyebrow {
            margin: 0 0 0.7rem;
            color: var(--gb-stats-accent);
            font-size: 0.76rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .gb-page-stats__grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
        }

        .gb-page-stats__item {
            padding: 0.9rem 0.95rem;
            border-radius: 18px;
            background: linear-gradient(145deg, var(--gb-stat-surface, rgba(255, 255, 255, 0.82)), rgba(255,255,255,0.92));
            border: 1px solid var(--gb-stat-border, rgba(15, 23, 42, 0.07));
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.45);
        }

        .gb-page-stats__label {
            margin: 0;
            color: var(--gb-stat-accent, #64748b);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .gb-page-stats__value {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin: 0.35rem 0 0;
            color: var(--gb-stat-value, #0f172a);
            font-size: 1.5rem;
            line-height: 1;
            font-weight: 800;
        }

        .gb-page-stats__value::before {
            content: "";
            width: 0.62rem;
            height: 0.62rem;
            border-radius: 999px;
            background: var(--gb-stat-dot, var(--gb-stat-accent, #64748b));
            box-shadow: 0 0 0 0.24rem color-mix(in srgb, var(--gb-stat-dot, var(--gb-stat-accent, #64748b)) 18%, transparent);
            flex-shrink: 0;
        }

        .gb-page-stats__sub {
            margin: 0.45rem 0 0;
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.35;
        }

        @media (max-width: 900px) {
            .gb-page-hero {
                padding: 1.55rem 1.25rem 1.4rem;
                border-radius: 24px;
            }

            .gb-page-hero__description {
                font-size: 0.95rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(
    *,
    title: str,
    description: str,
    eyebrow: str,
    palette: str = "teal",
    chips: list[str] | None = None,
) -> None:
    _inject_page_header_css()
    theme = HEADER_PALETTES.get(palette, HEADER_PALETTES["teal"])
    chip_markup = "".join(
        f'<span class="gb-page-hero__chip">{escape(chip)}</span>'
        for chip in (chips or [])
        if chip and chip.strip()
    )
    content_parts = [
        f'<p class="gb-page-hero__eyebrow">{escape(eyebrow)}</p>',
        f'<h1 class="gb-page-hero__title">{escape(title)}</h1>',
        f'<p class="gb-page-hero__description">{escape(description)}</p>',
    ]
    if chip_markup:
        content_parts.append(f'<div class="gb-page-hero__chips">{chip_markup}</div>')
    content_html = "".join(content_parts)
    st.markdown(
        f"""
        <section
            class="gb-page-hero"
            data-theme="{escape(palette)}"
            style="
                --gb-accent: {theme.accent};
                --gb-accent-soft: {theme.accent_soft};
                --gb-glow: {theme.glow};
                --gb-surface-start: {theme.surface_start};
                --gb-surface-end: {theme.surface_end};
                --gb-ink: {theme.ink};
                --gb-muted: {theme.muted};
            "
        >
            <div class="gb-page-hero__content">{content_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_registered_page_header(
    key: str,
    *,
    title: str | None = None,
    description: str | None = None,
    eyebrow: str | None = None,
    palette: str | None = None,
    chips: list[str] | None = None,
) -> None:
    preset = PAGE_HEADER_PRESETS[key]
    render_page_header(
        title=title or preset.title,
        description=description or preset.description,
        eyebrow=eyebrow or preset.eyebrow,
        palette=palette or preset.palette,
        chips=chips,
    )


def render_page_aside(
    *,
    eyebrow: str,
    title: str,
    body: str,
    chips: list[str] | None = None,
    accent: str = "#0369a1",
    accent_soft: str = "rgba(3, 105, 161, 0.12)",
) -> None:
    _inject_page_header_css()
    chip_markup = "".join(
        f'<span class="gb-page-aside__chip">{escape(chip)}</span>'
        for chip in (chips or [])
        if chip and chip.strip()
    )
    content_parts = [
        f'<p class="gb-page-aside__eyebrow">{escape(eyebrow)}</p>',
        f'<h2 class="gb-page-aside__title">{escape(title)}</h2>',
        f'<p class="gb-page-aside__body">{escape(body)}</p>',
    ]
    if chip_markup:
        content_parts.append(f'<div class="gb-page-aside__chips">{chip_markup}</div>')
    content_html = "".join(content_parts)
    st.markdown(
        f"""
        <section
            class="gb-page-aside"
            style="--gb-aside-accent: {accent}; --gb-aside-soft: {accent_soft};"
        >{content_html}</section>
        """,
        unsafe_allow_html=True,
    )


def render_page_stats_aside(
    *,
    eyebrow: str,
    stats: list[dict[str, str]],
    accent: str = "#0f766e",
    accent_soft: str = "rgba(15, 118, 110, 0.12)",
) -> None:
    _inject_page_header_css()
    items_html = "".join(
        (
            '<div class="gb-page-stats__item" '
            f'style="--gb-stat-accent: {escape(item.get("accent", "#64748b"))}; '
            f'--gb-stat-dot: {escape(item.get("dot", item.get("accent", "#64748b")))}; '
            f'--gb-stat-surface: {escape(item.get("surface", "rgba(255,255,255,0.82)"))}; '
            f'--gb-stat-border: {escape(item.get("border", "rgba(15, 23, 42, 0.07)"))}; '
            f'--gb-stat-value: {escape(item.get("value_color", "#0f172a"))};">'
            f'<p class="gb-page-stats__label">{escape(item["label"])}</p>'
            f'<p class="gb-page-stats__value">{escape(item["value"])}</p>'
            f'<p class="gb-page-stats__sub">{escape(item.get("sub", ""))}</p>'
            "</div>"
        )
        for item in stats
    )
    st.markdown(
        f"""
        <section
            class="gb-page-stats"
            style="--gb-stats-accent: {accent}; --gb-stats-soft: {accent_soft};"
        >
            <p class="gb-page-stats__eyebrow">{escape(eyebrow)}</p>
            <div class="gb-page-stats__grid">{items_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
