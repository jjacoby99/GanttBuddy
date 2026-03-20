import { useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";
import { formatDateTime, fromInputDateTime, hoursBetween, toInputDateTime } from "../../lib/utils";
import type { Phase, Task } from "../../types/api";
import { useWorkspaceStore } from "./workspace-store";

function PhaseSection({ phase, tasks }: { phase: Phase; tasks: Task[] }) {
  const expandedPhaseIds = useWorkspaceStore((state) => state.expandedPhaseIds);
  const setPhase = useWorkspaceStore((state) => state.setPhase);
  const setTask = useWorkspaceStore((state) => state.setTask);
  const addTask = useWorkspaceStore((state) => state.addTask);
  const togglePhase = useWorkspaceStore((state) => state.togglePhase);
  const expanded = expandedPhaseIds.includes(phase.id);

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
                <th>Status</th>
                <th>Type</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    <input
                      value={task.name}
                      onChange={(event) =>
                        setTask(task.id, (current) => ({
                          ...current,
                          name: event.target.value,
                        }))
                      }
                    />
                    <textarea
                      value={task.note}
                      rows={2}
                      onChange={(event) =>
                        setTask(task.id, (current) => ({
                          ...current,
                          note: event.target.value,
                        }))
                      }
                    />
                  </td>
                  <td>
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
                  </td>
                  <td>
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
                  </td>
                  <td>
                    <select
                      value={task.status}
                      onChange={(event) =>
                        setTask(task.id, (current) => ({
                          ...current,
                          status: event.target.value,
                        }))
                      }
                    >
                      <option value="PLANNED">PLANNED</option>
                      <option value="IN_PROGRESS">IN_PROGRESS</option>
                      <option value="DONE">DONE</option>
                      <option value="BLOCKED">BLOCKED</option>
                    </select>
                  </td>
                  <td>
                    <select
                      value={task.task_type}
                      onChange={(event) =>
                        setTask(task.id, (current) => ({
                          ...current,
                          task_type: event.target.value,
                        }))
                      }
                    >
                      <option value="GENERIC">GENERIC</option>
                      <option value="INCH">INCH</option>
                      <option value="STRIP">STRIP</option>
                      <option value="INSTALL">INSTALL</option>
                    </select>
                  </td>
                  <td>{hoursBetween(task.planned_start, task.planned_end).toFixed(1)} h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}

function GanttPreview({ tasks }: { tasks: Task[] }) {
  if (!tasks.length) {
    return <p className="muted">Add tasks to preview the planned sequence.</p>;
  }

  const starts = tasks.map((task) => new Date(task.planned_start).getTime());
  const ends = tasks.map((task) => new Date(task.planned_end).getTime());
  const min = Math.min(...starts);
  const max = Math.max(...ends);
  const span = Math.max(max - min, 1);

  return (
    <div className="gantt-preview">
      {tasks.map((task) => {
        const left = ((new Date(task.planned_start).getTime() - min) / span) * 100;
        const width = ((new Date(task.planned_end).getTime() - new Date(task.planned_start).getTime()) / span) * 100;
        return (
          <div className="gantt-row" key={task.id}>
            <span className="gantt-row__label">{task.name}</span>
            <div className="gantt-row__track">
              <div className="gantt-row__bar" style={{ left: `${left}%`, width: `${Math.max(width, 2)}%` }}>
                <span>{task.status}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function PlanPage() {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const draft = useWorkspaceStore((state) => state.draft);
  const setProject = useWorkspaceStore((state) => state.setProject);
  const addPhase = useWorkspaceStore((state) => state.addPhase);
  const markSaved = useWorkspaceStore((state) => state.markSaved);
  const setPlanViewMode = useWorkspaceStore((state) => state.setPlanViewMode);
  const planViewMode = useWorkspaceStore((state) => state.planViewMode);
  const isDirty = useWorkspaceStore((state) => state.isDirty);
  const toImportPayload = useWorkspaceStore((state) => state.toImportPayload);

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

  const tasksByPhase = draft.phases.map((phase) => ({
    phase,
    tasks: draft.tasks.filter((task) => task.phase_id === phase.id).sort((left, right) => left.position - right.position),
  }));

  const allTasks = draft.tasks.slice().sort(
    (left, right) => new Date(left.planned_start).getTime() - new Date(right.planned_start).getTime(),
  );

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">Plan workspace</span>
          <h1>{draft.project.name}</h1>
          <p>Loaded from the backend snapshot contract and saved back through <code>/projects/import</code>.</p>
        </div>
        <div className="hero__meta">
          <span className={`chip ${isDirty() ? "chip--warn" : ""}`}>{isDirty() ? "Unsaved changes" : "Saved"}</span>
          <span className="chip">Updated {formatDateTime(draft.project.updated_at)}</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>Project details</h2>
            <p>Keep the editing model close to the backend snapshot while React owns the draft state.</p>
          </div>
          <div className="button-row">
            <button className="button button--ghost" onClick={() => setPlanViewMode("phases")} type="button">
              Phase view
            </button>
            <button className="button button--ghost" onClick={() => setPlanViewMode("tasks")} type="button">
              Task view
            </button>
            <button className="button button--ghost" onClick={addPhase} type="button">
              Add phase
            </button>
            <button className="button" disabled={!isDirty() || saveMutation.isPending} onClick={() => saveMutation.mutate()} type="button">
              {saveMutation.isPending ? "Saving..." : "Save snapshot"}
            </button>
          </div>
        </div>

        <div className="form-grid form-grid--three">
          <label>
            <span>Project name</span>
            <input
              value={draft.project.name}
              onChange={(event) =>
                setProject((project) => ({
                  ...project,
                  name: event.target.value,
                }))
              }
            />
          </label>
          <label>
            <span>Project type</span>
            <input value={draft.project.project_type} disabled />
          </label>
          <label>
            <span>Timezone</span>
            <input value={draft.project.timezone_name} disabled />
          </label>
        </div>

        {saveMutation.isError ? <p className="error-text">{(saveMutation.error as Error).message}</p> : null}
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>{planViewMode === "phases" ? "Phases and tasks" : "Task timeline preview"}</h2>
            <p>The MVP keeps planning edits simple and explicit while preserving the existing backend save contract.</p>
          </div>
        </div>
        {planViewMode === "phases" ? (
          <div className="stack">
            {tasksByPhase.map(({ phase, tasks }) => (
              <PhaseSection key={phase.id} phase={phase} tasks={tasks} />
            ))}
          </div>
        ) : (
          <GanttPreview tasks={allTasks} />
        )}
      </section>
    </div>
  );
}
