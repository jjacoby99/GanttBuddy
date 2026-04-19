
from models.project import Project

from typing import Literal
from pathlib import Path
from PIL import Image
import pandas as pd
import plotly.graph_objects as go

UNIT_FACTORS = {
    "hours": 3600,
    "days": 86400,
    "weeks": 604800,
}
def generate_phase_delay_plot(
    project: Project,
    units: Literal["hours", "days", "weeks"] = "hours",
):
    """
    Generate a post-mortem chart of per-phase delay and cumulative delay.
    Units can be one of: "hours", "days", "weeks".
    Returns a Plotly Figure.
    """
    import textwrap  # local import to keep the rest of your file untouched

    def _wrap_label(label: str, width: int = 22, max_lines: int = 3) -> str:
        """
        Wrap label for Plotly ticks using <br>.
        Caps number of lines so super-long names don't make the chart too tall.
        """
        if not label:
            return ""
        lines = textwrap.wrap(str(label), width=width)
        if len(lines) <= max_lines:
            return "<br>".join(lines)

        kept = lines[:max_lines]
        # Truncate final line with ellipsis
        if len(kept[-1]) >= 3:
            kept[-1] = kept[-1][:-3] + "..."
        else:
            kept[-1] = kept[-1] + "..."
        return "<br>".join(kept)

    # Validate
    if units not in UNIT_FACTORS:
        raise ValueError(f"Invalid units '{units}'. Expected one of {list(UNIT_FACTORS.keys())}.")

    phase_ids = project.phase_order
    if not phase_ids:
        return go.Figure()

    seconds_per_unit = UNIT_FACTORS[units]
    rows = []

    phase_ids = project.phase_order

    for pid in phase_ids:
        phase = project.phases[pid]

        planned = phase.planned_duration
        actual = phase.actual_duration

        # Skip phases without required time data
        if planned is None or actual is None:
            continue

        # Phase delay
        delay_td = actual - planned
        delay_val = delay_td.total_seconds() / seconds_per_unit

        # Cumulative delay at this phase
        if phase.actual_end is None or phase.end_date is None:
            cumulative = None
        else:
            cum_td = phase.actual_end - phase.end_date
            cumulative = cum_td.total_seconds() / seconds_per_unit

        rows.append(
            {
                "phase_name": phase.name,
                "delay": delay_val,
                "cumulative": cumulative,
            }
        )

    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)

    # NEW: wrapped x-axis labels (display) + keep full names for hover
    df["phase_label"] = df["phase_name"].apply(lambda s: _wrap_label(s, width=22, max_lines=3))

    # Color scheme similar to Excel inspiration
    bar_colors = ["#e67e22"] * len(df)  # orange bars
    line_color = "#2c3e50"              # dark line

    fig = go.Figure()

    # Bar plot
    fig.add_trace(
        go.Bar(
            x=df["phase_label"],
            y=df["delay"],
            name=f"Phase Delay ({units})",
            marker=dict(color=bar_colors),
            customdata=df["phase_name"],  # full name for hover
            hovertemplate="<b>%{customdata}</b><br>Phase Delay: %{y:.1f} " + units + "<extra></extra>",
        )
    )

    # Line plot
    fig.add_trace(
        go.Scatter(
            x=df["phase_label"],
            y=df["cumulative"],
            name=f"Cumulative Delay ({units})",
            mode="lines+markers",
            line=dict(color=line_color, width=3),
            marker=dict(size=8, color=line_color),
            customdata=df["phase_name"],  # full name for hover
            hovertemplate="<b>%{customdata}</b><br>Cumulative: %{y:.1f} " + units + "<extra></extra>",
        )
    )

    # Add BTA logo
    logo_path = Path("src/assets/bta_logo.png")
    if logo_path.exists():
        try:
            logo = Image.open(logo_path)
            fig.add_layout_image(
                dict(
                    source=logo,
                    xref="paper", yref="paper",
                    x=0.925, y=0.85,
                    sizex=0.15, sizey=0.15,
                    xanchor="left", yanchor="bottom",
                    layer="above"
                )
            )
        except Exception:
            pass

    # Style & layout
    fig.update_layout(
        title=f"Delays By Phase",
        title_font=dict(size=26, color="#2c3e50"),
        barmode="group",
        template="plotly_white",
        xaxis_title="Phase",
        yaxis_title=f"Delay ({units})",
        hovermode="x unified",
        margin=dict(l=80, r=110, t=100, b=80),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=0.95,
            xanchor="left", x=0,
        ),
    )

    # Aesthetic tweaks like Excel
    fig.update_xaxes(
        tickangle=0,
        showgrid=True,
        gridcolor="#d0d8e8",
        linecolor="#7f8c8d",
        automargin=True,  # let Plotly expand margins if wrapped labels need room
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#d0d8e8",
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="#95a5a6",
    )

    # Light gradient background
    fig.update_layout(
        plot_bgcolor="rgba(240,248,255,1)",
        paper_bgcolor="white",
    )

    return fig