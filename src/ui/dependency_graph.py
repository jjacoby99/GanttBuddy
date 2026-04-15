from __future__ import annotations

from dataclasses import dataclass
import math

import plotly.graph_objects as go
import streamlit as st

from models.constraint import Constraint, ConstraintRelation
from models.project import Project


PHASE_X_GAP = 6.0
TASK_Y_GAP = 1.6
PHASE_HEADER_Y = 1.2


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    label: str
    x: float
    y: float
    phase_id: str | None = None
    phase_name: str | None = None


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    source_kind: str
    target_kind: str
    relation: ConstraintRelation
    lag_hours: float
    predecessor_kind: str
    label: str


@dataclass(frozen=True)
class PhaseBubble:
    phase_id: str
    phase_name: str
    x0: float
    x1: float
    y0: float
    y1: float
    color: str


@dataclass(frozen=True)
class DependencyGraphData:
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    bubbles: list[PhaseBubble]


def _phase_palette(index: int) -> tuple[str, str]:
    fills = [
        "rgba(14, 116, 144, 0.14)",
        "rgba(21, 128, 61, 0.14)",
        "rgba(180, 83, 9, 0.14)",
        "rgba(190, 24, 93, 0.14)",
        "rgba(79, 70, 229, 0.14)",
        "rgba(8, 145, 178, 0.14)",
    ]
    lines = [
        "rgba(14, 116, 144, 0.85)",
        "rgba(21, 128, 61, 0.85)",
        "rgba(180, 83, 9, 0.85)",
        "rgba(190, 24, 93, 0.85)",
        "rgba(79, 70, 229, 0.85)",
        "rgba(8, 145, 178, 0.85)",
    ]
    return fills[index % len(fills)], lines[index % len(lines)]


def _format_lag_hours(lag_hours: float) -> str:
    if math.isclose(lag_hours, 0.0, abs_tol=1e-9):
        return ""
    rounded = round(lag_hours, 2)
    return f" ({rounded:g}h)"


def _build_edge_label(constraint: Constraint) -> str:
    lag_hours = constraint.lag.total_seconds() / 3600
    return f"{constraint.relation_type.value}{_format_lag_hours(lag_hours)}"


def build_dependency_graph_data(project: Project) -> DependencyGraphData:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    bubbles: list[PhaseBubble] = []

    for phase_index, phase_id in enumerate(project.phase_order):
        phase = project.phases[phase_id]
        fill, line = _phase_palette(phase_index)
        center_x = phase_index * PHASE_X_GAP
        task_ids = list(phase.task_order)
        task_count = max(len(task_ids), 1)
        bottom_y = -(task_count - 1) * TASK_Y_GAP

        nodes.append(
            GraphNode(
                id=phase.uuid,
                kind="phase",
                label=phase.name,
                x=center_x,
                y=PHASE_HEADER_Y,
                phase_id=phase.uuid,
                phase_name=phase.name,
            )
        )

        bubbles.append(
            PhaseBubble(
                phase_id=phase.uuid,
                phase_name=phase.name,
                x0=center_x - 2.15,
                x1=center_x + 2.15,
                y0=bottom_y - 0.9,
                y1=PHASE_HEADER_Y + 0.8,
                color=fill,
            )
        )

        for task_index, task_id in enumerate(task_ids):
            task = phase.tasks[task_id]
            nodes.append(
                GraphNode(
                    id=task.uuid,
                    kind="task",
                    label=task.name,
                    x=center_x,
                    y=-(task_index * TASK_Y_GAP),
                    phase_id=phase.uuid,
                    phase_name=phase.name,
                )
            )

            for constraint in task.constraints:
                edges.append(
                    GraphEdge(
                        source_id=constraint.predecessor_id,
                        target_id=task.uuid,
                        source_kind=constraint.predecessor_kind,
                        target_kind="task",
                        relation=constraint.relation_type,
                        lag_hours=constraint.lag.total_seconds() / 3600,
                        predecessor_kind=constraint.predecessor_kind,
                        label=_build_edge_label(constraint),
                    )
                )

        for constraint in phase.constraints:
            edges.append(
                GraphEdge(
                    source_id=constraint.predecessor_id,
                    target_id=phase.uuid,
                    source_kind=constraint.predecessor_kind,
                    target_kind="phase",
                    relation=constraint.relation_type,
                    lag_hours=constraint.lag.total_seconds() / 3600,
                    predecessor_kind=constraint.predecessor_kind,
                    label=_build_edge_label(constraint),
                )
            )

    return DependencyGraphData(nodes=nodes, edges=edges, bubbles=bubbles)


def build_dependency_figure(
    project: Project,
    *,
    show_task_edges: bool = True,
    show_phase_edges: bool = True,
    show_labels: bool = True,
) -> go.Figure:
    graph = build_dependency_graph_data(project)
    node_lookup = {node.id: node for node in graph.nodes}

    fig = go.Figure()

    for bubble in graph.bubbles:
        fig.add_shape(
            type="rect",
            x0=bubble.x0,
            x1=bubble.x1,
            y0=bubble.y0,
            y1=bubble.y1,
            line={"color": "rgba(71, 85, 105, 0.5)", "width": 1.5},
            fillcolor=bubble.color,
            layer="below",
        )

    for edge in graph.edges:
        if edge.target_kind == "task" and not show_task_edges:
            continue
        if edge.target_kind == "phase" and not show_phase_edges:
            continue

        source = node_lookup.get(edge.source_id)
        target = node_lookup.get(edge.target_id)
        if source is None or target is None:
            continue

        is_phase_edge = edge.target_kind == "phase"
        line_color = "rgba(30, 41, 59, 0.85)" if not is_phase_edge else "rgba(124, 58, 237, 0.8)"
        line_dash = "solid" if not is_phase_edge else "dash"

        fig.add_annotation(
            x=target.x,
            y=target.y,
            ax=source.x,
            ay=source.y,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.1,
            arrowwidth=1.8 if not is_phase_edge else 2.2,
            arrowcolor=line_color,
            opacity=0.95,
            standoff=14 if not is_phase_edge else 18,
            startstandoff=14 if source.kind == "task" else 18,
            text=edge.label if show_labels else "",
            font={"size": 11, "color": line_color},
            bgcolor="rgba(255,255,255,0.72)" if show_labels else None,
            borderpad=2,
        )

        midpoint_x = (source.x + target.x) / 2
        midpoint_y = (source.y + target.y) / 2
        fig.add_trace(
            go.Scatter(
                x=[source.x, midpoint_x, target.x],
                y=[source.y, midpoint_y, target.y],
                mode="lines",
                line={"color": line_color, "width": 1.2, "dash": line_dash},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    phase_nodes = [node for node in graph.nodes if node.kind == "phase"]
    task_nodes = [node for node in graph.nodes if node.kind == "task"]

    fig.add_trace(
        go.Scatter(
            x=[node.x for node in phase_nodes],
            y=[node.y for node in phase_nodes],
            mode="markers+text",
            text=[node.label for node in phase_nodes],
            textposition="top center",
            textfont={"size": 13, "color": "#0f172a"},
            marker={
                "size": 24,
                "symbol": "diamond",
                "color": "#7c3aed",
                "line": {"width": 1.5, "color": "#4c1d95"},
            },
            customdata=[[node.phase_name, node.id, "phase"] for node in phase_nodes],
            hovertemplate="<b>%{text}</b><br>Phase node<extra></extra>",
            name="Phases",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[node.x for node in task_nodes],
            y=[node.y for node in task_nodes],
            mode="markers+text",
            text=[node.label for node in task_nodes],
            textposition="middle center",
            textfont={"size": 11, "color": "#0f172a"},
            marker={
                "size": 34,
                "symbol": "square",
                "color": "#f8fafc",
                "line": {"width": 1.5, "color": "#0f172a"},
            },
            customdata=[[node.phase_name, node.id, "task"] for node in task_nodes],
            hovertemplate="<b>%{text}</b><br>Phase: %{customdata[0]}<extra></extra>",
            name="Tasks",
        )
    )

    fig.update_layout(
        height=max(480, 200 + max((len(project.get_task_list()) * 38), 0)),
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        showlegend=True,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def _render_dependency_summary(project: Project) -> None:
    task_constraint_count = sum(len(task.constraints) for task in project.get_task_list())
    phase_constraint_count = sum(len(project.phases[pid].constraints) for pid in project.phase_order)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Phases", len(project.phase_order))
    c2.metric("Tasks", len(project.get_task_list()))
    c3.metric("Task Constraints", task_constraint_count)
    c4.metric("Phase Constraints", phase_constraint_count)


def render_dependency_graph(project: Project) -> None:
    if not project.phases:
        st.info("Add phases and tasks to your project to view dependency flow.")
        return

    if not project.has_task:
        st.info("Add tasks to your phases to view dependency flow.")
        return

    controls = st.columns([1, 1, 1, 5])
    show_task_edges = controls[0].toggle("Task edges", value=True)
    show_phase_edges = controls[1].toggle("Phase edges", value=True)
    show_labels = controls[2].toggle("Relation labels", value=True)

    fig = build_dependency_figure(
        project,
        show_task_edges=show_task_edges,
        show_phase_edges=show_phase_edges,
        show_labels=show_labels,
    )
    st.plotly_chart(fig, use_container_width=True)

    _render_dependency_summary(project)

    with st.expander("Constraint legend", expanded=False):
        st.markdown(
            "\n".join(
                [
                    "`FS` = Finish-to-Start",
                    "`SS` = Start-to-Start",
                    "`FF` = Finish-to-Finish",
                    "`SF` = Start-to-Finish",
                    "Dashed arrows connect whole phases.",
                    "Solid arrows connect task-level constraints.",
                ]
            )
        )
