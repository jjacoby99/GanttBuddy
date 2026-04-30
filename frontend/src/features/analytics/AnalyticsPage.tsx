import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useNavigate } from "react-router-dom";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";
import { formatDate } from "../../lib/utils";
import { useWorkspaceStore } from "../plan/workspace-store";

const componentKpiKeys = [
  "strip_feed_rows",
  "strip_feed_pieces",
  "strip_shell_rows",
  "strip_shell_pieces",
  "strip_discharge_rows",
  "strip_discharge_pieces",
  "install_feed_rows",
  "install_feed_pieces",
  "install_shell_rows",
  "install_shell_pieces",
  "install_discharge_rows",
  "install_discharge_pieces",
] as const;

function formatKpiValue(value: number | string | null, unit?: string | null) {
  if (value === null || value === "") {
    return "Not set";
  }
  return unit ? `${value} ${unit}` : String(value);
}

export function AnalyticsPage() {
  const navigate = useNavigate();
  const token = useAuthStore((state) => state.token);
  const draft = useWorkspaceStore((state) => state.draft);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const projectId = draft?.project.id;

  useEffect(() => {
    if (!draft) {
      navigate("/projects", { replace: true });
    }
  }, [draft, navigate]);

  const params = {
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const dashboardQuery = useQuery({
    queryKey: ["dashboard", projectId, params],
    queryFn: () => api.getDashboard(token!, projectId!, params),
    enabled: Boolean(token && projectId),
  });

  const inchingQuery = useQuery({
    queryKey: ["inching", projectId, params],
    queryFn: () => api.getInching(token!, projectId!, params),
    enabled: Boolean(token && projectId),
  });

  const normalizedOverviewQuery = useQuery({
    queryKey: ["normalized-overview", projectId],
    queryFn: () => api.getNormalizedOverview(token!, projectId!),
    enabled: Boolean(token && projectId),
  });

  const normalizedCombinedQuery = useQuery({
    queryKey: ["normalized-work-type-component", projectId],
    queryFn: () => api.getNormalizedByWorkTypeAndComponent(token!, projectId!),
    enabled: Boolean(token && projectId),
  });

  const burnupRows =
    dashboardQuery.data?.burnup.cumulative_planned_hours.map((point, index) => ({
      x: point.x,
      planned: point.y,
      actual: dashboardQuery.data?.burnup.cumulative_actual_hours[index]?.y ?? 0,
    })) ?? [];

  const componentCountKpis = normalizedOverviewQuery.data?.kpis.filter((kpi) =>
    componentKpiKeys.includes(kpi.key as (typeof componentKpiKeys)[number]),
  );

  if (!draft) {
    return null;
  }

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">Analytics</span>
          <h1>Project analytics</h1>
          <p>Review progress, production trends, and execution performance across the full project window.</p>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>Filters</h2>
            <p>Focus the charts on the date window that matters most.</p>
          </div>
        </div>
        <div className="form-grid">
          <label>
            <span>From</span>
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label>
            <span>To</span>
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
        </div>
      </section>

      {dashboardQuery.isLoading ? <p>Loading dashboard...</p> : null}
      {dashboardQuery.isError ? <p className="error-text">{(dashboardQuery.error as Error).message}</p> : null}
      {normalizedOverviewQuery.isError ? (
        <p className="error-text">{(normalizedOverviewQuery.error as Error).message}</p>
      ) : null}
      {normalizedCombinedQuery.isError ? (
        <p className="error-text">{(normalizedCombinedQuery.error as Error).message}</p>
      ) : null}

      {dashboardQuery.data ? (
        <>
          <section className="stats-grid">
            {dashboardQuery.data.overview.kpis.map((kpi) => (
              <article className="stat-card" key={kpi.key}>
                <span>{kpi.label}</span>
                <strong>{formatKpiValue(kpi.value, kpi.unit)}</strong>
              </article>
            ))}
          </section>

          <div className="two-column two-column--wide">
            <section className="panel">
              <div className="panel__header">
                <div>
                  <h2>Burnup</h2>
                  <p>As of {formatDate(dashboardQuery.data.as_of)}</p>
                </div>
              </div>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={burnupRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="x" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="planned" stroke="#0f3a5d" strokeWidth={3} />
                    <Line type="monotone" dataKey="actual" stroke="#bd632f" strokeWidth={3} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="panel">
              <div className="panel__header">
                <div>
                  <h2>By task type</h2>
                  <p>Compare planned and actual hours across task categories.</p>
                </div>
              </div>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={dashboardQuery.data.by_task_type.rows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="task_type" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="planned_hours" fill="#0f3a5d" />
                    <Bar dataKey="actual_hours" fill="#bd632f" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </div>
        </>
      ) : null}

      {normalizedOverviewQuery.data ? (
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Normalized component counts</h2>
              <p>Rows and pieces broken out by strip/install and top-level liner component.</p>
            </div>
          </div>
          <div className="stats-grid">
            {componentCountKpis?.map((kpi) => (
              <article className="stat-card" key={kpi.key}>
                <span>{kpi.label}</span>
                <strong>{formatKpiValue(kpi.value, kpi.unit)}</strong>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {normalizedCombinedQuery.data ? (
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>By work type and component</h2>
              <p>{normalizedCombinedQuery.data.allocation_basis}</p>
            </div>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Bucket</th>
                  <th>Tasks</th>
                  <th>Coverage</th>
                  <th>Hours / Row</th>
                  <th>Hours / Liner</th>
                  <th>Rows / Hour</th>
                  <th>Liners / Hour</th>
                </tr>
              </thead>
              <tbody>
                {normalizedCombinedQuery.data.rows.map((row) => (
                  <tr key={row.key}>
                    <td>{row.label}</td>
                    <td>{row.task_count}</td>
                    <td>{row.quantified_actual_hours_pct == null ? "Not set" : `${(row.quantified_actual_hours_pct * 100).toFixed(0)}%`}</td>
                    <td>{row.actual_hours_per_row == null ? "Not set" : row.actual_hours_per_row.toFixed(3)}</td>
                    <td>{row.actual_hours_per_liner == null ? "Not set" : row.actual_hours_per_liner.toFixed(3)}</td>
                    <td>{row.actual_rows_per_hour == null ? "Not set" : row.actual_rows_per_hour.toFixed(3)}</td>
                    <td>{row.actual_liners_per_hour == null ? "Not set" : row.actual_liners_per_hour.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {inchingQuery.data ? (
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Inching performance</h2>
              <p>Track shift-by-shift performance and overall inching trends.</p>
            </div>
          </div>
          <div className="stats-grid">
            {inchingQuery.data.kpis.slice(0, 6).map((kpi) => (
              <article className="stat-card" key={kpi.key}>
                <span>{kpi.label}</span>
                <strong>{formatKpiValue(kpi.value, kpi.unit)}</strong>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
