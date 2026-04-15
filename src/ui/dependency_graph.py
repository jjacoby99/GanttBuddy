from __future__ import annotations

from dataclasses import dataclass
import math
import textwrap

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


@dataclass(frozen=True)
class EdgeRoute:
    points_x: list[float]
    points_y: list[float]
    label_x: float
    label_y: float
    label_dx: float
    label_dy: float
    arrow_tail_x: float
    arrow_tail_y: float


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


def _format_duration_hours(hours: float) -> str:
    rounded = round(hours, 2)
    return f"{rounded:g}h"


def _wrap_node_label(label: str, *, width: int = 14, max_lines: int = 3) -> str:
    wrapped = textwrap.wrap(label, width=width, break_long_words=False, break_on_hyphens=False)
    if not wrapped:
        return label
    if len(wrapped) > max_lines:
        remaining = " ".join(wrapped[max_lines - 1 :])
        wrapped = wrapped[: max_lines - 1] + textwrap.wrap(
            remaining,
            width=width,
            max_lines=1,
            placeholder="...",
            break_long_words=False,
            break_on_hyphens=False,
        )
    return "<br>".join(wrapped)


def _build_edge_label(constraint: Constraint) -> str:
    lag_hours = constraint.lag.total_seconds() / 3600
    return f"{constraint.relation_type.value}{_format_lag_hours(lag_hours)}"


def _offset_point_toward(
    start: tuple[float, float],
    end: tuple[float, float],
    distance: float,
) -> tuple[float, float]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.hypot(dx, dy)
    if math.isclose(length, 0.0, abs_tol=1e-9):
        return start
    unit_x = dx / length
    unit_y = dy / length
    return start[0] + (unit_x * distance), start[1] + (unit_y * distance)


def _quadratic_bezier_point(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    inv_t = 1 - t
    x = (inv_t * inv_t * p0[0]) + (2 * inv_t * t * p1[0]) + (t * t * p2[0])
    y = (inv_t * inv_t * p0[1]) + (2 * inv_t * t * p1[1]) + (t * t * p2[1])
    return x, y


def _build_edge_route(
    source: GraphNode,
    target: GraphNode,
    *,
    lane_offset: float,
    is_phase_edge: bool,
) -> EdgeRoute:
    p0 = (source.x, source.y)
    p2 = (target.x, target.y)
    midpoint_x = (source.x + target.x) / 2
    midpoint_y = (source.y + target.y) / 2

    same_column = math.isclose(source.x, target.x, abs_tol=0.05)
    bend_direction = 1.0 if lane_offset >= 0 else -1.0
    if math.isclose(lane_offset, 0.0, abs_tol=1e-9):
        bend_direction = 1.0 if target.x >= source.x else -1.0

    if is_phase_edge:
        bend_strength = 0.55 + abs(target.x - source.x) * 0.05
        control_x = midpoint_x
        control_y = midpoint_y + 0.9 + lane_offset
    else:
        base_bend = 1.2 if same_column else 0.75
        bend_strength = base_bend + abs(target.y - source.y) * 0.12 + abs(lane_offset) * 1.4
        control_x = midpoint_x + bend_direction * bend_strength
        control_y = midpoint_y + (lane_offset * 0.55)

    p1 = (control_x, control_y)
    samples = [
        _quadratic_bezier_point(p0, p1, p2, t)
        for t in (0.0, 0.18, 0.36, 0.5, 0.64, 0.82, 1.0)
    ]
    label_x, label_y = _quadratic_bezier_point(p0, p1, p2, 0.5)
    tangent_before = _quadratic_bezier_point(p0, p1, p2, 0.46)
    tangent_after = _quadratic_bezier_point(p0, p1, p2, 0.54)
    tangent_x = tangent_after[0] - tangent_before[0]
    tangent_y = tangent_after[1] - tangent_before[1]
    tangent_length = math.hypot(tangent_x, tangent_y)
    if math.isclose(tangent_length, 0.0, abs_tol=1e-9):
        normal_x, normal_y = 0.0, 1.0
    else:
        normal_x = -tangent_y / tangent_length
        normal_y = tangent_x / tangent_length
    label_offset = 0.14 if not is_phase_edge else 0.18
    arrow_tail_x, arrow_tail_y = _quadratic_bezier_point(p0, p1, p2, 0.88)
    return EdgeRoute(
        points_x=[point[0] for point in samples],
        points_y=[point[1] for point in samples],
        label_x=label_x + (normal_x * label_offset),
        label_y=label_y + (normal_y * label_offset),
        label_dx=normal_x,
        label_dy=normal_y,
        arrow_tail_x=arrow_tail_x,
        arrow_tail_y=arrow_tail_y,
    )


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
                    label=_wrap_node_label(task.name),
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
    visible_edges: list[GraphEdge] = []
    for edge in graph.edges:
        if edge.target_kind == "task" and not show_task_edges:
            continue
        if edge.target_kind == "phase" and not show_phase_edges:
            continue
        if edge.source_id not in node_lookup or edge.target_id not in node_lookup:
            continue
        visible_edges.append(edge)

    incoming_edges_by_target: dict[str, list[GraphEdge]] = {}
    for edge in visible_edges:
        incoming_edges_by_target.setdefault(edge.target_id, []).append(edge)

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

    for edge in visible_edges:
        source = node_lookup[edge.source_id]
        target = node_lookup[edge.target_id]

        is_phase_edge = edge.target_kind == "phase"
        line_color = "rgba(30, 41, 59, 0.85)" if not is_phase_edge else "rgba(124, 58, 237, 0.8)"
        line_dash = "solid" if not is_phase_edge else "dash"
        target_edges = incoming_edges_by_target.get(edge.target_id, [])
        edge_index = target_edges.index(edge)
        lane_offset = (edge_index - ((len(target_edges) - 1) / 2)) * (0.95 if not is_phase_edge else 0.55)
        route = _build_edge_route(
            source,
            target,
            lane_offset=lane_offset,
            is_phase_edge=is_phase_edge,
        )
        target_radius = 0.42 if not is_phase_edge else 0.2
        source_radius = 0.42 if source.kind == "task" else 0.2
        line_start = _offset_point_toward(
            (source.x, source.y),
            (route.points_x[1], route.points_y[1]),
            source_radius,
        )
        line_end = _offset_point_toward(
            (target.x, target.y),
            (route.arrow_tail_x, route.arrow_tail_y),
            target_radius,
        )
        line_x = list(route.points_x)
        line_y = list(route.points_y)
        line_x[0], line_y[0] = line_start
        line_x[-1], line_y[-1] = line_end

        fig.add_annotation(
            x=line_end[0],
            y=line_end[1],
            ax=route.arrow_tail_x,
            ay=route.arrow_tail_y,
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
            standoff=0,
            startstandoff=0,
            text="",
        )

        fig.add_trace(
            go.Scatter(
                x=line_x,
                y=line_y,
                mode="lines",
                line={"color": line_color, "width": 1.2, "dash": line_dash, "shape": "spline", "smoothing": 1.15},
                hoverinfo="skip",
                showlegend=False,
            )
        )

        if show_labels and edge.label:
            fig.add_trace(
                go.Scatter(
                    x=[route.label_x],
                    y=[route.label_y],
                    mode="text",
                    text=[edge.label],
                    textfont={"size": 11, "color": line_color},
                    textposition="top center",
                    marker={"size": 1, "color": "rgba(0,0,0,0)"},
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
            textfont={"size": 12, "color": "#0f172a"},
            marker={
                "size": 72,
                "symbol": "square",
                "color": "#f8fafc",
                "line": {"width": 1.5, "color": "#0f172a"},
            },
            customdata=[
                [
                    node.phase_name,
                    node.id,
                    "task",
                    _format_duration_hours(
                        project.phases[node.phase_id].tasks[node.id].planned_duration.total_seconds() / 3600
                    ),
                ]
                for node in task_nodes
            ],
            hovertemplate="<b>%{text}</b><br>Phase: %{customdata[0]}<br>Planned duration: %{customdata[3]}<extra></extra>",
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
