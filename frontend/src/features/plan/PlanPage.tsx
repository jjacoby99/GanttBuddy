import { Fragment, useEffect, useMemo, useState, type CSSProperties } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";
import { formatDateTime, fromInputDateTime, hoursBetween, toInputDateTime } from "../../lib/utils";
import type { Phase, Task } from "../../types/api";
import { useWorkspaceStore } from "./workspace-store";

type ScaleMode = "auto" | "2h" | "6h" | "12h" | "1d";

type HoveredBar = {
  task: Task;
  x: number;
  y: number;
};

function statusMeta(status: string) {
  switch (status) {
    case "COMPLETE":
    case "DONE":
      return { label: "Complete", tone: "success" };
    case "IN_PROGRESS":
      return { label: "In Progress", tone: "info" };
    case "BLOCKED":
      return { label: "Blocked", tone: "danger" };
    case "NOT_STARTED":
    default:
      return { label: "Not Started", tone: "neutral" };
  }
}

function progressMeta(task: Task) {
  const isComplete = task.status === "COMPLETE" || task.status === "DONE";
  if (isComplete) {
    return { label: "Complete", tone: "success" };
  }
  if (task.actual_start) {
    return { label: "In Flight", tone: "info" };
  }
  return { label: "Open", tone: "neutral" };
}

function scopeMeta(task: Task) {
  return task.planned
    ? { label: "Planned", tone: "planned", description: "Included in the original project scope" }
    : { label: "Unplanned", tone: "unplanned", description: "Added after the original project plan" };
}

function formatScaleDate(value: Date, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat(undefined, options).format(value);
}

function alignToUnit(value: Date, unitMs: number) {
  return new Date(Math.floor(value.getTime() / unitMs) * unitMs);
}

function ceilToUnit(value: Date, unitMs: number) {
  return new Date(Math.ceil(value.getTime() / unitMs) * unitMs);
}

function addUnits(value: Date, amount: number, unitMs: number) {
  return new Date(value.getTime() + amount * unitMs);
}

function timelineStyle(width: number, segmentWidth: number): CSSProperties {
  const style = {
    width: `${width}px`,
    "--gantt-segment-width": `${segmentWidth}px`,
  };
  return style as CSSProperties;
}

function getStringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function getSiteCode(metadata: Record<string, unknown> | null): string | null {
  if (!metadata) {
    return null;
  }

  const direct =
    getStringValue(metadata.site_code) ??
    getStringValue(metadata.siteCode) ??
    getStringValue(metadata.site);
  if (direct) {
    return direct;
  }

  const nestedSite = metadata.site_details;
  if (nestedSite && typeof nestedSite === "object") {
    const nestedCode =
      getStringValue((nestedSite as Record<string, unknown>).code) ??
      getStringValue((nestedSite as Record<string, unknown>).site_code);
    if (nestedCode) {
      return nestedCode;
    }
  }

  return null;
}

function TaskEditor({ task }: { task: Task }) {
  const setTask = useWorkspaceStore((state) => state.setTask);

  return (
    <div className="task-editor">
      <div className="form-grid">
        <label>
          <span>Name</span>
          <input
            value={task.name}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                name: event.target.value,
              }))
            }
          />
        </label>
        <label>
          <span>Status</span>
          <select
            value={task.status}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                status: event.target.value,
              }))
            }
          >
            <option value="NOT_STARTED">Not Started</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="COMPLETE">Complete</option>
            <option value="BLOCKED">Blocked</option>
          </select>
        </label>
      </div>

      <div className="form-grid">
        <label>
          <span>Planned start</span>
          <input
            type="datetime-local"
            value={toInputDateTime(task.planned_start)}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                planned_start: fromInputDateTime(event.target.value) ?? current.planned_start,
              }))
            }
          />
        </label>
        <label>
          <span>Planned finish</span>
          <input
            type="datetime-local"
            value={toInputDateTime(task.planned_end)}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                planned_end: fromInputDateTime(event.target.value) ?? current.planned_end,
              }))
            }
          />
        </label>
      </div>

      <div className="form-grid">
        <label>
          <span>Actual start</span>
          <input
            type="datetime-local"
            value={toInputDateTime(task.actual_start)}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                actual_start: fromInputDateTime(event.target.value),
              }))
            }
          />
        </label>
        <label>
          <span>Actual finish</span>
          <input
            type="datetime-local"
            value={toInputDateTime(task.actual_end)}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                actual_end: fromInputDateTime(event.target.value),
              }))
            }
          />
        </label>
      </div>

      <div className="form-grid">
        <label>
          <span>Scope</span>
          <select
            value={task.planned ? "planned" : "unplanned"}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                planned: event.target.value === "planned",
              }))
            }
          >
            <option value="planned">Planned task</option>
            <option value="unplanned">Unplanned task</option>
          </select>
        </label>
        <label>
          <span>Task type</span>
          <select
            value={task.task_type}
            onChange={(event) =>
              setTask(task.id, (current) => ({
                ...current,
                task_type: event.target.value,
              }))
            }
          >
            <option value="GENERIC">Generic</option>
            <option value="INCH">Inch</option>
            <option value="STRIP">Strip</option>
            <option value="INSTALL">Install</option>
          </select>
        </label>
      </div>

      <label>
        <span>Notes</span>
        <textarea
          value={task.note}
          rows={3}
          onChange={(event) =>
            setTask(task.id, (current) => ({
              ...current,
              note: event.target.value,
            }))
          }
        />
      </label>
    </div>
  );
}

function PhaseSection({
  phase,
  tasks,
  showActuals,
}: {
  phase: Phase;
  tasks: Task[];
  showActuals: boolean;
}) {
  const expandedPhaseIds = useWorkspaceStore((state) => state.expandedPhaseIds);
  const setPhase = useWorkspaceStore((state) => state.setPhase);
  const addTask = useWorkspaceStore((state) => state.addTask);
  const togglePhase = useWorkspaceStore((state) => state.togglePhase);
  const expanded = expandedPhaseIds.includes(phase.id);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);

  return (
    <article className="phase-card">
      <div className="phase-card__header">
        <button className="link-button phase-card__toggle" onClick={() => togglePhase(phase.id)} type="button">
          {expanded ? "Hide" : "Show"}
        </button>
        <input
          className="phase-card__title"
          value={phase.name}
          onChange={(event) =>
            setPhase(phase.id, (current) => ({
              ...current,
              name: event.target.value,
            }))
          }
        />
        <span className="chip">{tasks.length} tasks</span>
        <button className="button button--ghost" onClick={() => addTask(phase.id)} type="button">
          Add task
        </button>
      </div>

      {expanded ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Planned start</th>
                <th>Planned end</th>
                {showActuals ? <th>Actual start</th> : null}
                {showActuals ? <th>Actual finish</th> : null}
                <th>Status</th>
                <th>Scope</th>
                <th>Edit</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <Fragment key={task.id}>
                  <tr>
                    <td>
                      <div className="task-name-cell">
                        <strong>{task.name}</strong>
                        <span className="muted task-meta">
                          {hoursBetween(task.planned_start, task.planned_end).toFixed(1)} h
                        </span>
                      </div>
                    </td>
                    <td>{formatDateTime(task.planned_start)}</td>
                    <td>{formatDateTime(task.planned_end)}</td>
                    {showActuals ? <td>{formatDateTime(task.actual_start)}</td> : null}
                    {showActuals ? <td>{formatDateTime(task.actual_end)}</td> : null}
                    <td>
                      <span className={`status-pill status-pill--${statusMeta(task.status).tone}`}>
                        {statusMeta(task.status).label}
                      </span>
                    </td>
                    <td>
                      <span className={`scope-pill ${task.planned ? "scope-pill--planned" : "scope-pill--unplanned"}`}>
                        {task.planned ? "Planned" : "Unplanned"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="button button--ghost"
                        onClick={() => setEditingTaskId((current) => (current === task.id ? null : task.id))}
                        type="button"
                      >
                        {editingTaskId === task.id ? "Close" : "Edit"}
                      </button>
                    </td>
                  </tr>
                  {editingTaskId === task.id ? (
                    <tr className="task-editor-row">
                      <td colSpan={showActuals ? 8 : 6}>
                        <TaskEditor task={task} />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}

function GanttPreview({
  tasksByPhase,
  showActuals,
  scaleMode,
  expandedPhaseIds,
  onTogglePhase,
}: {
  tasksByPhase: Array<{ phase: Phase; tasks: Task[] }>;
  showActuals: boolean;
  scaleMode: ScaleMode;
  expandedPhaseIds: string[];
  onTogglePhase: (phaseId: string) => void;
}) {
  const tasks = tasksByPhase.flatMap((entry) => entry.tasks);
  const [hoveredBar, setHoveredBar] = useState<HoveredBar | null>(null);

  if (!tasks.length) {
    return <p className="muted">Add tasks to preview the planned sequence.</p>;
  }

  const starts = tasks.map((task) => new Date(task.planned_start).getTime());
  const ends = tasks.map((task) => {
    const actualEnd = showActuals && task.actual_end ? new Date(task.actual_end).getTime() : null;
    return actualEnd && actualEnd > new Date(task.planned_end).getTime()
      ? actualEnd
      : new Date(task.planned_end).getTime();
  });

  const totalSpanMs = Math.max(Math.max(...ends) - Math.min(...starts), 1);
  const resolvedScale: Exclude<ScaleMode, "auto"> =
    scaleMode === "auto"
      ? totalSpanMs <= 4 * 24 * 60 * 60 * 1000
        ? "2h"
        : totalSpanMs <= 12 * 24 * 60 * 60 * 1000
          ? "6h"
          : totalSpanMs <= 28 * 24 * 60 * 60 * 1000
            ? "12h"
            : "1d"
      : scaleMode;
  const unitMs =
    resolvedScale === "2h"
      ? 2 * 60 * 60 * 1000
      : resolvedScale === "6h"
        ? 6 * 60 * 60 * 1000
        : resolvedScale === "12h"
          ? 12 * 60 * 60 * 1000
          : 24 * 60 * 60 * 1000;
  const pxPerSegment = resolvedScale === "2h" ? 88 : resolvedScale === "6h" ? 78 : resolvedScale === "12h" ? 70 : 76;

  const timelineStart = alignToUnit(new Date(Math.min(...starts)), unitMs);
  const timelineEnd = addUnits(ceilToUnit(new Date(Math.max(...ends)), unitMs), 1, unitMs);
  const span = timelineEnd.getTime() - timelineStart.getTime();
  const segmentCount = Math.max(1, Math.ceil(span / unitMs));
  const timelineWidth = Math.max(segmentCount * pxPerSegment, 1280);
  const today = new Date();
  const todayOffset = ((today.getTime() - timelineStart.getTime()) / span) * 100;
  const todayVisible = todayOffset >= 0 && todayOffset <= 100;

  const scaleMarkers = Array.from({ length: segmentCount }, (_, index) => {
    const date = addUnits(timelineStart, index, unitMs);
    return {
      key: date.toISOString(),
      label:
        resolvedScale === "1d"
          ? formatScaleDate(date, { month: "short", day: "numeric" })
          : formatScaleDate(date, { hour: "numeric" }),
      sublabel:
        resolvedScale === "1d"
          ? formatScaleDate(date, { weekday: "short" })
          : formatScaleDate(date, { month: "short", day: "numeric" }),
      isMajor: resolvedScale === "1d" ? index === 0 || date.getDay() === 1 : date.getHours() === 0,
    };
  });

  const palette = ["phase-a", "phase-b", "phase-c", "phase-d", "phase-e"];

  return (
    <div className="gantt-board">
      <div className="gantt-board__header">
        <div>
          <h3>Project timeline</h3>
          <p>See the schedule across phases, planned work, and actual progress.</p>
        </div>
        <div className="gantt-legend">
          <span className="legend-chip legend-chip--planned">
            <span className="legend-bar legend-bar--planned" />
            Planned window
          </span>
          {showActuals ? (
            <span className="legend-chip legend-chip--actual">
              <span className="legend-bar legend-bar--actual" />
              Actual progress
            </span>
          ) : null}
          <span className="legend-chip legend-chip--planned-task">
            <span className="legend-symbol legend-symbol--planned-task" />
            Planned task
          </span>
          <span className="legend-chip legend-chip--unplanned-task">
            <span className="legend-symbol legend-symbol--unplanned-task" />
            Unplanned task
          </span>
          <span className="legend-chip legend-chip--complete">
            <span className="legend-symbol legend-symbol--complete" />
            Complete
          </span>
          <span className="legend-chip legend-chip--open">
            <span className="legend-symbol legend-symbol--open" />
            Not complete
          </span>
          {todayVisible ? (
            <span className="legend-chip legend-chip--today">
              <span className="legend-bar legend-bar--today" />
              Today
            </span>
          ) : null}
        </div>
      </div>

      <div className="gantt-scroll">
        <div className="gantt-scale" style={{ width: `${timelineWidth + 280}px` }}>
          <div className="gantt-scale__labels">Activity</div>
          <div className="gantt-scale__timeline" style={timelineStyle(timelineWidth, pxPerSegment)}>
            {scaleMarkers.map((marker) => (
              <div className={`gantt-scale__cell ${marker.isMajor ? "gantt-scale__cell--major" : ""}`} key={marker.key}>
                <span>{marker.label}</span>
                <small>{marker.sublabel}</small>
              </div>
            ))}
            {todayVisible ? <div className="gantt-today" style={{ left: `${todayOffset}%` }} /> : null}
          </div>
        </div>

        {tasksByPhase.map(({ phase, tasks: phaseTasks }, phaseIndex) => {
          const phaseClass = palette[phaseIndex % palette.length];
          const expanded = expandedPhaseIds.includes(phase.id);
          const phasePlannedStart = Math.min(...phaseTasks.map((task) => new Date(task.planned_start).getTime()));
          const phasePlannedEnd = Math.max(...phaseTasks.map((task) => new Date(task.planned_end).getTime()));
          const phaseActualStarts = phaseTasks
            .map((task) => (task.actual_start ? new Date(task.actual_start).getTime() : null))
            .filter((value): value is number => value !== null);
          const phaseActualEnds = phaseTasks
            .map((task) => {
              if (task.actual_end) {
                return new Date(task.actual_end).getTime();
              }
              if (task.actual_start) {
                return new Date(task.actual_start).getTime();
              }
              return null;
            })
            .filter((value): value is number => value !== null);
          const phaseLeft = ((phasePlannedStart - timelineStart.getTime()) / span) * 100;
          const phaseWidth = ((phasePlannedEnd - phasePlannedStart) / span) * 100;
          const phaseHasActual = showActuals && phaseActualStarts.length > 0 && phaseActualEnds.length > 0;
          const phaseActualLeft = phaseHasActual
            ? ((Math.min(...phaseActualStarts) - timelineStart.getTime()) / span) * 100
            : null;
          const phaseActualWidth = phaseHasActual
            ? ((Math.max(...phaseActualEnds) - Math.min(...phaseActualStarts)) / span) * 100
            : null;

          return (
            <div className="gantt-phase-group" key={phase.id}>
              <div className="gantt-phase-group__header">
                <div className="gantt-phase-group__label">
                  <button
                    aria-label={expanded ? `Collapse ${phase.name}` : `Expand ${phase.name}`}
                    className="gantt-phase-group__toggle"
                    onClick={() => onTogglePhase(phase.id)}
                    type="button"
                  >
                    {expanded ? "^" : "v"}
                  </button>
                  <span className={`phase-dot ${phaseClass}`} />
                  <div className="gantt-phase-group__title">
                    <strong>{phase.name}</strong>
                    <span>{phaseTasks.length} tasks</span>
                  </div>
                </div>
                <div className="gantt-phase-group__track" style={timelineStyle(timelineWidth, pxPerSegment)}>
                  <div className="gantt-track-grid" />
                  {todayVisible ? <div className="gantt-today" style={{ left: `${todayOffset}%` }} /> : null}
                  <div
                    className={`gantt-phase-bar gantt-phase-bar--planned ${phaseClass} ${
                      phaseWidth <= 0 ? "gantt-phase-bar--milestone" : ""
                    }`}
                    style={{ left: `${phaseLeft}%`, width: phaseWidth <= 0 ? "12px" : `${phaseWidth}%` }}
                  />
                  {phaseHasActual && phaseActualLeft !== null && phaseActualWidth !== null ? (
                    <div
                      className={`gantt-phase-bar gantt-phase-bar--actual ${phaseClass} ${
                        phaseActualWidth <= 0 ? "gantt-phase-bar--milestone" : ""
                      }`}
                      style={{ left: `${phaseActualLeft}%`, width: phaseActualWidth <= 0 ? "12px" : `${phaseActualWidth}%` }}
                    />
                  ) : null}
                </div>
              </div>

              {expanded
                ? phaseTasks.map((task) => {
                const plannedStart = new Date(task.planned_start).getTime();
                const plannedEnd = new Date(task.planned_end).getTime();
                const plannedLeft = ((plannedStart - timelineStart.getTime()) / span) * 100;
                const plannedWidth = ((plannedEnd - plannedStart) / span) * 100;
                const actualStart = task.actual_start ? new Date(task.actual_start).getTime() : null;
                const actualEnd = task.actual_end ? new Date(task.actual_end).getTime() : null;
                const actualLeft =
                  actualStart !== null ? ((actualStart - timelineStart.getTime()) / span) * 100 : null;
                const actualWidth =
                  actualStart !== null && actualEnd !== null ? ((actualEnd - actualStart) / span) * 100 : null;
                const isActive = hoveredBar?.task.id === task.id;
                const scope = scopeMeta(task);
                const progress = progressMeta(task);
                const isPlannedMilestone = plannedWidth <= 0;
                const isActualMilestone =
                  actualLeft !== null && (actualWidth === null || actualWidth <= 0);
                const handleHover = (event: React.MouseEvent<HTMLDivElement>) => {
                  const rect = event.currentTarget.getBoundingClientRect();
                  const parent = event.currentTarget.offsetParent as HTMLElement | null;
                  const parentRect = parent?.getBoundingClientRect();
                  setHoveredBar({
                    task,
                    x: rect.left - (parentRect?.left ?? 0) + rect.width / 2,
                    y: rect.top - (parentRect?.top ?? 0),
                  });
                };

                return (
                  <div className={`gantt-timeline-row ${isActive ? "gantt-timeline-row--active" : ""}`} key={task.id}>
                    <div className="gantt-timeline-row__label">
                      <strong>{task.name}</strong>
                      <div className="gantt-timeline-row__meta">
                        <span
                          className={`timeline-indicator timeline-indicator--${scope.tone}`}
                          title={scope.description}
                        />
                        <span
                          className={`timeline-indicator timeline-indicator--${progress.tone}`}
                          title={progress.label}
                        />
                        <span className="muted">{hoursBetween(task.planned_start, task.planned_end).toFixed(1)} h planned</span>
                      </div>
                    </div>
                    <div className="gantt-timeline-row__track" style={timelineStyle(timelineWidth, pxPerSegment)}>
                      <div className="gantt-track-grid" />
                      {todayVisible ? <div className="gantt-today" style={{ left: `${todayOffset}%` }} /> : null}
                      <div
                        className={`gantt-bar gantt-bar--planned ${phaseClass} ${task.planned ? "" : "gantt-bar--unplanned"} ${progress.tone === "success" ? "gantt-bar--complete" : ""} ${isActive ? "gantt-bar--active" : ""} ${isPlannedMilestone ? "gantt-bar--milestone" : ""}`}
                        style={{ left: `${plannedLeft}%`, width: isPlannedMilestone ? "10px" : `${plannedWidth}%` }}
                        onMouseEnter={handleHover}
                        onMouseMove={handleHover}
                        onMouseLeave={() => setHoveredBar(null)}
                      />
                      {showActuals && actualLeft !== null && actualWidth !== null ? (
                        <div
                          className={`gantt-bar gantt-bar--actual ${phaseClass} ${isActive ? "gantt-bar--active" : ""} ${isActualMilestone ? "gantt-bar--milestone" : ""}`}
                          style={{ left: `${actualLeft}%`, width: isActualMilestone ? "10px" : `${actualWidth}%` }}
                          onMouseEnter={handleHover}
                          onMouseMove={handleHover}
                          onMouseLeave={() => setHoveredBar(null)}
                        />
                      ) : showActuals && actualLeft !== null ? (
                        <div
                          className={`gantt-bar gantt-bar--actual gantt-bar--actual-point gantt-bar--milestone ${phaseClass} ${isActive ? "gantt-bar--active" : ""}`}
                          style={{ left: `${actualLeft}%`, width: "10px" }}
                          onMouseEnter={handleHover}
                          onMouseMove={handleHover}
                          onMouseLeave={() => setHoveredBar(null)}
                        />
                      ) : null}
                    </div>
                  </div>
                );
              })
                : null}
            </div>
          );
        })}

        {hoveredBar ? (
          <div
            className="gantt-tooltip"
            style={{
              left: `${Math.max(320, hoveredBar.x + 320)}px`,
              top: `${Math.max(120, hoveredBar.y + 115)}px`,
            }}
          >
            <strong>{hoveredBar.task.name}</strong>
            <div className="gantt-tooltip__badges">
              <span className={`status-pill status-pill--${statusMeta(hoveredBar.task.status).tone}`}>
                {statusMeta(hoveredBar.task.status).label}
              </span>
              <span
                className={`scope-pill ${hoveredBar.task.planned ? "scope-pill--planned" : "scope-pill--unplanned"}`}
              >
                {scopeMeta(hoveredBar.task).label}
              </span>
            </div>
            <div className="gantt-tooltip__grid">
              <span>Planned window</span>
              <strong>{`${formatDateTime(hoveredBar.task.planned_start)} to ${formatDateTime(hoveredBar.task.planned_end)}`}</strong>
              <span>Planned duration</span>
              <strong>{hoursBetween(hoveredBar.task.planned_start, hoveredBar.task.planned_end).toFixed(1)} h</strong>
              <span>Actual window</span>
              <strong>
                {hoveredBar.task.actual_start && hoveredBar.task.actual_end
                  ? `${formatDateTime(hoveredBar.task.actual_start)} to ${formatDateTime(hoveredBar.task.actual_end)}`
                  : hoveredBar.task.actual_start
                    ? `Started ${formatDateTime(hoveredBar.task.actual_start)}`
                    : "Not started"}
              </strong>
              <span>Actual duration</span>
              <strong>
                {hoveredBar.task.actual_start && hoveredBar.task.actual_end
                  ? `${hoursBetween(hoveredBar.task.actual_start, hoveredBar.task.actual_end).toFixed(1)} h`
                  : hoveredBar.task.actual_start
                    ? "Started"
                    : "Not started"}
              </strong>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function PlanPage() {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const draft = useWorkspaceStore((state) => state.draft);
  const addPhase = useWorkspaceStore((state) => state.addPhase);
  const markSaved = useWorkspaceStore((state) => state.markSaved);
  const setPlanViewMode = useWorkspaceStore((state) => state.setPlanViewMode);
  const planViewMode = useWorkspaceStore((state) => state.planViewMode);
  const expandedPhaseIds = useWorkspaceStore((state) => state.expandedPhaseIds);
  const togglePhase = useWorkspaceStore((state) => state.togglePhase);
  const isDirty = useWorkspaceStore((state) => state.isDirty);
  const toImportPayload = useWorkspaceStore((state) => state.toImportPayload);
  const [showActuals, setShowActuals] = useState(false);
  const [scaleMode, setScaleMode] = useState<ScaleMode>("auto");

  const tasksByPhase = useMemo(
    () =>
      draft
        ? draft.phases.map((phase) => ({
            phase,
            tasks: draft.tasks
              .filter((task) => task.phase_id === phase.id)
              .sort((left, right) => left.position - right.position),
          }))
        : [],
    [draft],
  );

  useEffect(() => {
    if (!draft) {
      navigate("/projects", { replace: true });
    }
  }, [draft, navigate]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toImportPayload();
      if (!token || !payload) {
        throw new Error("No loaded project to save.");
      }
      return api.saveProject(token, payload);
    },
    onSuccess: () => {
      markSaved();
    },
  });

  if (!draft) {
    return null;
  }

  const hasUnsavedChanges = isDirty();
  const siteCode = draft.project.site_code ?? getSiteCode(draft.metadata);

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">Planning</span>
          <h1>{draft.project.name}</h1>
          <div className="hero__details">
            {siteCode ? (
              <span className="chip chip--site">
                <span className="chip__icon chip__icon--site" aria-hidden="true" />
                {siteCode}
              </span>
            ) : null}
            <span className="chip chip--muted">{draft.project.timezone_name}</span>
          </div>
          <p>Shape the schedule, adjust timing, and keep the plan readable from phase to task level.</p>
        </div>
        <div className="hero__meta">
          <span className="chip">Updated {formatDateTime(draft.project.updated_at)}</span>
          {hasUnsavedChanges || saveMutation.isPending ? (
            <button
              className="button button--icon"
              disabled={!hasUnsavedChanges || saveMutation.isPending}
              onClick={() => saveMutation.mutate()}
              type="button"
            >
              <span className="button__icon button__icon--save" aria-hidden="true" />
              {saveMutation.isPending ? "Saving..." : "Save project"}
            </button>
          ) : null}
        </div>
      </section>

      <section className="panel panel--elevated">
        <div className="panel__header">
          <div>
            <h2>Workspace</h2>
            <p>Switch between views and keep the timeline controls close at hand without crowding the chart.</p>
          </div>
          <div className="workspace-toolbar">
            <button
              className="button button--ghost button--icon"
              onClick={() => setPlanViewMode(planViewMode === "phases" ? "tasks" : "phases")}
              type="button"
            >
              <span
                className={`button__icon ${
                  planViewMode === "phases" ? "button__icon--timeline" : "button__icon--list"
                }`}
                aria-hidden="true"
              />
              {planViewMode === "phases" ? "Show gantt" : "Show phase list"}
            </button>
            {planViewMode === "phases" ? (
              <button className="button button--ghost button--icon" onClick={addPhase} type="button">
                <span className="button__icon button__icon--plus" aria-hidden="true" />
                Add phase
              </button>
            ) : null}
          </div>
        </div>

        <div className="workspace-summary">
          {planViewMode === "tasks" ? (
            <details className="plot-controls">
              <summary className="plot-controls__summary">
                <span className="button__icon button__icon--sliders" aria-hidden="true" />
                Timeline controls
              </summary>
              <div className="plot-controls__body">
                <button
                  className="button button--ghost button--icon"
                  onClick={() => setShowActuals((current) => !current)}
                  type="button"
                >
                  <span className="button__icon button__icon--eye" aria-hidden="true" />
                  {showActuals ? "Hide actuals" : "Show actuals"}
                </button>
                <label className="plot-controls__field">
                  <span>Scale</span>
                  <select value={scaleMode} onChange={(event) => setScaleMode(event.target.value as ScaleMode)}>
                    <option value="auto">Auto scale</option>
                    <option value="2h">2-hour scale</option>
                    <option value="6h">6-hour scale</option>
                    <option value="12h">12-hour scale</option>
                    <option value="1d">1-day scale</option>
                  </select>
                </label>
              </div>
            </details>
          ) : (
            <span className="workspace-hint">Phase editing controls appear directly in each phase section below.</span>
          )}
        </div>

        {saveMutation.isError ? <p className="error-text">{(saveMutation.error as Error).message}</p> : null}
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>{planViewMode === "phases" ? "Phases and tasks" : "Project timeline"}</h2>
            <p>
              {planViewMode === "phases"
                ? "Review the schedule row by row and edit tasks as needed."
                : "Visualize the project in a tighter, more legible timeline view."}
            </p>
          </div>
        </div>
        {planViewMode === "phases" ? (
          <div className="stack">
            {tasksByPhase.map(({ phase, tasks }) => (
              <PhaseSection key={phase.id} phase={phase} tasks={tasks} showActuals={showActuals} />
            ))}
          </div>
        ) : (
          <GanttPreview
            tasksByPhase={tasksByPhase}
            showActuals={showActuals}
            scaleMode={scaleMode}
            expandedPhaseIds={expandedPhaseIds}
            onTogglePhase={togglePhase}
          />
        )}
      </section>
    </div>
  );
}
