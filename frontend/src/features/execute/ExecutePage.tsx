import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";
import { formatDateTime, fromInputDateTime, toInputDateTime } from "../../lib/utils";
import type { Task } from "../../types/api";
import { useWorkspaceStore } from "../plan/workspace-store";

type ActionKind = "start" | "finish" | "status" | "note" | "actuals";

export function ExecutePage() {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const draft = useWorkspaceStore((state) => state.draft);
  const applyServerTask = useWorkspaceStore((state) => state.applyServerTask);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [statusValue, setStatusValue] = useState("IN_PROGRESS");
  const [noteValue, setNoteValue] = useState("");
  const [actualStart, setActualStart] = useState("");
  const [actualEnd, setActualEnd] = useState("");

  useEffect(() => {
    if (!draft) {
      navigate("/projects", { replace: true });
    }
  }, [draft, navigate]);

  const selectedTask = useMemo(
    () => draft?.tasks.find((task) => task.id === selectedTaskId) ?? draft?.tasks[0] ?? null,
    [draft, selectedTaskId],
  );

  const taskMutation = useMutation({
    mutationFn: async (kind: ActionKind) => {
      if (!token || !selectedTask) {
        throw new Error("Select a task first.");
      }

      switch (kind) {
        case "start":
          return api.startTask(token, selectedTask.id, { occurred_at: new Date().toISOString() });
        case "finish":
          return api.finishTask(token, selectedTask.id, { occurred_at: new Date().toISOString() });
        case "status":
          return api.setTaskStatus(token, selectedTask.id, { status: statusValue });
        case "note":
          return api.setTaskNote(token, selectedTask.id, { note: noteValue });
        case "actuals":
          return api.editTaskActuals(token, selectedTask.id, {
            actual_start: fromInputDateTime(actualStart),
            actual_end: fromInputDateTime(actualEnd),
            reason: "Edited from React MVP execute workspace",
          });
      }
    },
    onSuccess: (task: Task) => {
      applyServerTask(task);
    },
  });

  if (!draft) {
    return null;
  }

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">Execute workspace</span>
          <h1>Task execution</h1>
          <p>Update progress, capture actuals, and keep task notes current as the project moves.</p>
        </div>
      </section>

      <div className="two-column two-column--wide">
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Task list</h2>
              <p>Pick a task and update it as work happens in the field.</p>
            </div>
          </div>
          <div className="stack">
            {draft.tasks.map((task) => (
              <button
                className={`task-card ${selectedTask?.id === task.id ? "task-card--active" : ""}`}
                key={task.id}
                onClick={() => {
                  setSelectedTaskId(task.id);
                  setStatusValue(task.status);
                  setNoteValue(task.note);
                  setActualStart(toInputDateTime(task.actual_start));
                  setActualEnd(toInputDateTime(task.actual_end));
                }}
                type="button"
              >
                <strong>{task.name}</strong>
                <span>{task.status}</span>
                <span>
                  {formatDateTime(task.planned_start)} to {formatDateTime(task.planned_end)}
                </span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>{selectedTask?.name ?? "Select a task"}</h2>
              <p>Capture the latest status, actual times, and notes for the selected task.</p>
            </div>
          </div>

          {selectedTask ? (
            <div className="stack">
              <div className="stats-grid">
                <article className="stat-card">
                  <span>Status</span>
                  <strong>{selectedTask.status}</strong>
                </article>
                <article className="stat-card">
                  <span>Planned</span>
                  <strong>{formatDateTime(selectedTask.planned_start)}</strong>
                </article>
                <article className="stat-card">
                  <span>Actual start</span>
                  <strong>{formatDateTime(selectedTask.actual_start)}</strong>
                </article>
                <article className="stat-card">
                  <span>Actual finish</span>
                  <strong>{formatDateTime(selectedTask.actual_end)}</strong>
                </article>
              </div>

              <div className="button-row">
                <button className="button" onClick={() => taskMutation.mutate("start")} type="button" disabled={taskMutation.isPending}>
                  Start now
                </button>
                <button className="button button--ghost" onClick={() => taskMutation.mutate("finish")} type="button" disabled={taskMutation.isPending}>
                  Finish now
                </button>
              </div>

              <label>
                <span>Status</span>
                <div className="inline-form">
                  <select value={statusValue} onChange={(event) => setStatusValue(event.target.value)}>
                    <option value="NOT_STARTED">NOT_STARTED</option>
                    <option value="IN_PROGRESS">IN_PROGRESS</option>
                    <option value="COMPLETE">COMPLETE</option>
                    <option value="BLOCKED">BLOCKED</option>
                  </select>
                  <button className="button button--ghost" onClick={() => taskMutation.mutate("status")} type="button" disabled={taskMutation.isPending}>
                    Update status
                  </button>
                </div>
              </label>

              <label>
                <span>Note</span>
                <textarea rows={4} value={noteValue} onChange={(event) => setNoteValue(event.target.value)} />
                <button className="button button--ghost" onClick={() => taskMutation.mutate("note")} type="button" disabled={taskMutation.isPending}>
                  Save note
                </button>
              </label>

              <div className="form-grid">
                <label>
                  <span>Actual start</span>
                  <input type="datetime-local" value={actualStart} onChange={(event) => setActualStart(event.target.value)} />
                </label>
                <label>
                  <span>Actual end</span>
                  <input type="datetime-local" value={actualEnd} onChange={(event) => setActualEnd(event.target.value)} />
                </label>
              </div>
              <button className="button button--ghost" onClick={() => taskMutation.mutate("actuals")} type="button" disabled={taskMutation.isPending}>
                Save actuals
              </button>
              {taskMutation.isError ? <p className="error-text">{(taskMutation.error as Error).message}</p> : null}
            </div>
          ) : (
            <p className="muted">Pick a task from the left.</p>
          )}
        </section>
      </div>
    </div>
  );
}
