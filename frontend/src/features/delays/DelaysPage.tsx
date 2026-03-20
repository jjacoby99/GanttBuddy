import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";
import { formatDateTime, fromInputDateTime, toInputDateTime } from "../../lib/utils";
import { useWorkspaceStore } from "../plan/workspace-store";
import {
  buildDelayBreakdown,
  computeDeletedCount,
  createEmptyDelay,
  DELAY_META,
  DELAY_TYPES,
  delayTypeLabel,
  delaysEqual,
  formatDelayHours,
  mapDelayToDraft,
  overlapTasksForDelay,
  resolveDelayEnd,
  toDelayPayload,
  type DelayDraft,
} from "./delay-utils";

type DelayTab = "register" | "breakdown";

function formatTooltipHours(value: number | string | ReadonlyArray<number | string> | undefined) {
  const resolved = Array.isArray(value) ? Number(value[0]) : Number(value);
  if (!Number.isFinite(resolved)) {
    return "0.0 h";
  }
  return `${resolved.toFixed(1)} h`;
}

function DelayTypePill({ type }: { type: keyof typeof DELAY_META }) {
  const meta = DELAY_META[type];
  return (
    <span className={`delay-pill ${meta.accent}`}>
      <span className={`delay-pill__icon ${meta.surface}`}>{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function DelayInsights({
  row,
  taskCount,
  topTasks,
}: {
  row: DelayDraft | null;
  taskCount: number;
  topTasks: ReturnType<typeof overlapTasksForDelay>;
}) {
  if (!row) {
    return (
      <aside className="delay-sidebar">
        <div className="delay-sidebar__empty">
          <strong>Select a delay</strong>
          <p>Choose a row from the register to see affected work, timing, and quick context.</p>
        </div>
      </aside>
    );
  }

  const resolvedEnd = resolveDelayEnd(row);

  return (
    <aside className="delay-sidebar">
      <article className="delay-story">
        <div className="delay-story__header">
          <div>
            <span className="eyebrow">Selected delay</span>
            <h3>{row.description || "Untitled delay"}</h3>
          </div>
          <DelayTypePill type={row.delay_type} />
        </div>

        <div className="delay-kpi-grid">
          <div className="delay-kpi-card">
            <span>Tracked delay</span>
            <strong>{formatDelayHours(row.duration_minutes)}</strong>
          </div>
          <div className="delay-kpi-card">
            <span>Tasks affected</span>
            <strong>{taskCount}</strong>
          </div>
        </div>

        <div className="delay-story__grid">
          <span>Start</span>
          <strong>{formatDateTime(row.start_dt)}</strong>
          <span>End</span>
          <strong>{formatDateTime(resolvedEnd)}</strong>
        </div>
      </article>

      <article className="panel delay-panel-card">
        <div className="panel__header">
          <div>
            <h2>Affected tasks</h2>
            <p>Tasks whose actual execution window intersects this delay.</p>
          </div>
        </div>
        {topTasks.length ? (
          <div className="stack">
            {topTasks.slice(0, 5).map(({ task, phase, varianceHours }) => (
              <div className="delay-task-card" key={task.id}>
                <div>
                  <strong>{task.name}</strong>
                  <p>{phase?.name ?? "Unassigned phase"}</p>
                </div>
                <div className="delay-task-card__meta">
                  <span>{varianceHours !== null ? `${varianceHours.toFixed(1)} h variance` : "Variance unavailable"}</span>
                  <span>{formatDateTime(task.actual_start)} to {formatDateTime(task.actual_end)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">No completed tasks intersect this delay window yet.</p>
        )}
      </article>
    </aside>
  );
}

function DelayBreakdownView({
  rows,
  activeTypes,
  setActiveTypes,
}: {
  rows: DelayDraft[];
  activeTypes: string[];
  setActiveTypes: (types: string[]) => void;
}) {
  const breakdown = useMemo(() => buildDelayBreakdown(rows), [rows]);
  const visibleBreakdown = breakdown.filter((entry) => activeTypes.includes(entry.delay_type));
  const totalMinutes = visibleBreakdown.reduce((sum, entry) => sum + entry.minutes, 0);
  const avgMinutes = rows.length ? totalMinutes / Math.max(visibleBreakdown.reduce((sum, entry) => sum + entry.count, 0), 1) : 0;

  return (
    <div className="stack">
      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>Breakdown controls</h2>
            <p>Focus on the delay categories you want to compare.</p>
          </div>
        </div>
        <div className="delay-filter-row">
          {DELAY_TYPES.map((type) => {
            const active = activeTypes.includes(type);
            return (
              <button
                className={`filter-chip ${active ? "filter-chip--active" : ""}`}
                key={type}
                onClick={() =>
                  setActiveTypes(
                    active ? activeTypes.filter((item) => item !== type) : [...activeTypes, type],
                  )
                }
                type="button"
              >
                {delayTypeLabel(type)}
              </button>
            );
          })}
        </div>
      </section>

      <section className="stats-grid">
        <article className="stat-card delay-stat-card">
          <span>Delays tracked</span>
          <strong>{visibleBreakdown.reduce((sum, entry) => sum + entry.count, 0)}</strong>
        </article>
        <article className="stat-card delay-stat-card">
          <span>Total delay</span>
          <strong>{(totalMinutes / 60).toFixed(1)} h</strong>
        </article>
        <article className="stat-card delay-stat-card">
          <span>Average duration</span>
          <strong>{avgMinutes.toFixed(0)} min</strong>
        </article>
      </section>

      <div className="two-column">
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Delay hours by type</h2>
              <p>Where the schedule is absorbing the most lost time.</p>
            </div>
          </div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={[...visibleBreakdown].sort((left, right) => left.hours - right.hours)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hours" type="number" />
                <YAxis dataKey="label" type="category" width={130} />
                <Tooltip formatter={formatTooltipHours} />
                <Bar dataKey="hours" radius={[0, 12, 12, 0]}>
                  {visibleBreakdown.map((entry) => (
                    <Cell fill={DELAY_META[entry.delay_type].chart} key={entry.delay_type} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Share of delays</h2>
              <p>Relative mix of recorded delay categories.</p>
            </div>
          </div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={visibleBreakdown}
                  dataKey="minutes"
                  innerRadius={74}
                  outerRadius={108}
                  paddingAngle={3}
                  nameKey="label"
                >
                  {visibleBreakdown.map((entry) => (
                    <Cell fill={DELAY_META[entry.delay_type].chart} key={entry.delay_type} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => {
                  const resolved = Array.isArray(value) ? Number(value[0]) : Number(value);
                  if (!Number.isFinite(resolved)) {
                    return "0.0 h";
                  }
                  return `${(resolved / 60).toFixed(1)} h`;
                }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>Summary table</h2>
            <p>Counts and tracked hours by delay category.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Count</th>
                <th>Tracked hours</th>
              </tr>
            </thead>
            <tbody>
              {visibleBreakdown.map((entry) => (
                <tr key={entry.delay_type}>
                  <td><DelayTypePill type={entry.delay_type} /></td>
                  <td>{entry.count}</td>
                  <td>{entry.hours.toFixed(1)} h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export function DelaysPage() {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const draft = useWorkspaceStore((state) => state.draft);
  const [rows, setRows] = useState<DelayDraft[]>([]);
  const [baselineRows, setBaselineRows] = useState<DelayDraft[]>([]);
  const [selectedDelayId, setSelectedDelayId] = useState<string | null>(null);
  const [tab, setTab] = useState<DelayTab>("register");
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [activeTypes, setActiveTypes] = useState<string[]>(DELAY_TYPES);

  const projectId = draft?.project.id;

  useEffect(() => {
    if (!draft) {
      navigate("/projects", { replace: true });
    }
  }, [draft, navigate]);

  const delaysQuery = useQuery({
    queryKey: ["delays", projectId],
    queryFn: () => api.getDelays(token!, projectId!),
    enabled: Boolean(token && projectId),
  });

  useEffect(() => {
    if (!delaysQuery.data) {
      return;
    }
    const nextRows = delaysQuery.data.map(mapDelayToDraft);
    setRows(nextRows);
    setBaselineRows(nextRows);
    setSelectedDelayId((current) => current ?? nextRows[0]?.local_id ?? null);
  }, [delaysQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async (replace: boolean) => api.saveDelays(token!, projectId!, toDelayPayload(rows), { replace }),
    onSuccess: (saved) => {
      const nextRows = saved.map(mapDelayToDraft);
      setRows(nextRows);
      setBaselineRows(nextRows);
      setSelectedDelayId(nextRows[0]?.local_id ?? null);
      setShowConfirmDelete(false);
    },
  });

  const deletedCount = useMemo(() => computeDeletedCount(baselineRows, rows), [baselineRows, rows]);
  const dirty = useMemo(() => !delaysEqual(rows, baselineRows), [rows, baselineRows]);
  const selectedDelay = rows.find((row) => row.local_id === selectedDelayId) ?? null;
  const affectedTasks = useMemo(
    () => (selectedDelay && draft ? overlapTasksForDelay(selectedDelay, draft.tasks, draft.phases) : []),
    [draft, selectedDelay],
  );

  if (!draft) {
    return null;
  }

  const handleSave = () => {
    if (deletedCount > 0) {
      setShowConfirmDelete(true);
      return;
    }
    saveMutation.mutate(false);
  };

  return (
    <div className="page">
      <section className="hero hero--delays">
        <div>
          <span className="eyebrow">Delay management</span>
          <h1>Delay register</h1>
          <p>Capture schedule friction, understand the work it touched, and turn delay data into a cleaner operating picture.</p>
        </div>
        <div className="hero__meta">
          <span className={`chip ${dirty ? "chip--warn" : ""}`}>{dirty ? "Unsaved delay edits" : "Delay register saved"}</span>
          <button className="button button--ghost" onClick={() => navigate("/workspace/plan")} type="button">
            Open gantt
          </button>
        </div>
      </section>

      <section className="delay-tabs">
        <button className={`delay-tab ${tab === "register" ? "delay-tab--active" : ""}`} onClick={() => setTab("register")} type="button">
          Register
        </button>
        <button className={`delay-tab ${tab === "breakdown" ? "delay-tab--active" : ""}`} onClick={() => setTab("breakdown")} type="button">
          Breakdown
        </button>
      </section>

      {delaysQuery.isLoading ? <p>Loading delays...</p> : null}
      {delaysQuery.isError ? <p className="error-text">{(delaysQuery.error as Error).message}</p> : null}

      {showConfirmDelete ? (
        <section className="panel delay-confirm">
          <div>
            <h2>Confirm deletion</h2>
            <p>{deletedCount} saved delay {deletedCount === 1 ? "entry is" : "entries are"} being removed. Saving now will replace the server list.</p>
          </div>
          <div className="button-row">
            <button className="button" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate(true)} type="button">
              {saveMutation.isPending ? "Saving..." : "Proceed with delete"}
            </button>
            <button className="button button--ghost" onClick={() => setShowConfirmDelete(false)} type="button">
              Cancel
            </button>
          </div>
        </section>
      ) : null}

      {tab === "register" ? (
        <div className="delay-layout">
          <section className="panel delay-register-panel">
            <div className="panel__header">
              <div>
                <h2>Registered delays</h2>
                <p>Add, edit, and curate the delay log directly from this register.</p>
              </div>
              <div className="button-row">
                <button
                  className="button button--ghost"
                  onClick={() => {
                    const next = [...rows, createEmptyDelay()];
                    setRows(next);
                    setSelectedDelayId(next.at(-1)?.local_id ?? null);
                  }}
                  type="button"
                >
                  Add delay
                </button>
                <button className="button" disabled={!dirty || saveMutation.isPending} onClick={handleSave} type="button">
                  {saveMutation.isPending ? "Saving..." : "Save delays"}
                </button>
              </div>
            </div>

            <div className="table-wrap delay-table-wrap">
              <table className="data-table delay-table">
                <thead>
                  <tr>
                    <th>View</th>
                    <th>Description</th>
                    <th>Type</th>
                    <th>Duration (min)</th>
                    <th>Start</th>
                    <th>End</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr className={selectedDelayId === row.local_id ? "delay-row--selected" : ""} key={row.local_id}>
                      <td>
                        <button
                          className={`delay-select ${selectedDelayId === row.local_id ? "delay-select--active" : ""}`}
                          onClick={() => setSelectedDelayId(row.local_id)}
                          type="button"
                        >
                          View
                        </button>
                      </td>
                      <td>
                        <input
                          placeholder="Describe the delay"
                          value={row.description}
                          onChange={(event) =>
                            setRows((current) =>
                              current.map((item) =>
                                item.local_id === row.local_id ? { ...item, description: event.target.value } : item,
                              ),
                            )
                          }
                        />
                      </td>
                      <td>
                        <select
                          value={row.delay_type}
                          onChange={(event) =>
                            setRows((current) =>
                              current.map((item) =>
                                item.local_id === row.local_id
                                  ? { ...item, delay_type: event.target.value as DelayDraft["delay_type"] }
                                  : item,
                              ),
                            )
                          }
                        >
                          {DELAY_TYPES.map((type) => (
                            <option key={type} value={type}>
                              {delayTypeLabel(type)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          min={1}
                          type="number"
                          value={row.duration_minutes}
                          onChange={(event) =>
                            setRows((current) =>
                              current.map((item) =>
                                item.local_id === row.local_id
                                  ? { ...item, duration_minutes: Number(event.target.value) || 0 }
                                  : item,
                              ),
                            )
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="datetime-local"
                          value={toInputDateTime(row.start_dt)}
                          onChange={(event) =>
                            setRows((current) =>
                              current.map((item) =>
                                item.local_id === row.local_id
                                  ? { ...item, start_dt: fromInputDateTime(event.target.value) }
                                  : item,
                              ),
                            )
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="datetime-local"
                          value={toInputDateTime(row.end_dt)}
                          onChange={(event) =>
                            setRows((current) =>
                              current.map((item) =>
                                item.local_id === row.local_id
                                  ? { ...item, end_dt: fromInputDateTime(event.target.value) }
                                  : item,
                              ),
                            )
                          }
                        />
                      </td>
                      <td>
                        <button
                          className="link-button delay-delete"
                          onClick={() =>
                            setRows((current) => current.filter((item) => item.local_id !== row.local_id))
                          }
                          type="button"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!rows.length ? (
                    <tr>
                      <td colSpan={7}>
                        <div className="delay-empty-state">
                          <strong>No delays registered yet</strong>
                          <p>Start the log with the first delay entry for this project.</p>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>

            {saveMutation.isError ? <p className="error-text">{(saveMutation.error as Error).message}</p> : null}
          </section>

          <DelayInsights row={selectedDelay} taskCount={affectedTasks.length} topTasks={affectedTasks} />
        </div>
      ) : (
        <DelayBreakdownView rows={rows} activeTypes={activeTypes} setActiveTypes={setActiveTypes} />
      )}
    </div>
  );
}
