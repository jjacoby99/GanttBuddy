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

  const burnupRows =
    dashboardQuery.data?.burnup.cumulative_planned_hours.map((point, index) => ({
      x: point.x,
      planned: point.y,
      actual: dashboardQuery.data?.burnup.cumulative_actual_hours[index]?.y ?? 0,
    })) ?? [];

  if (!draft) {
    return null;
  }

  return (
    <div className="page">
      <section className="hero">
        <div>
          <span className="eyebrow">Analytics</span>
          <h1>Backend-driven charts</h1>
          <p>The React app reuses the dashboard and inching endpoints instead of rebuilding analytics rules in TypeScript.</p>
        </div>
      </section>

      <section className="panel">
        <div className="panel__header">
          <div>
            <h2>Filters</h2>
            <p>Date windows are passed straight through to the backend analytics contract.</p>
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

      {dashboardQuery.data ? (
        <>
          <section className="stats-grid">
            {dashboardQuery.data.overview.kpis.map((kpi) => (
              <article className="stat-card" key={kpi.key}>
                <span>{kpi.label}</span>
                <strong>
                  {kpi.value}
                  {kpi.unit ? ` ${kpi.unit}` : ""}
                </strong>
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
                  <p>Directly shaped from the backend breakdown response.</p>
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

      {inchingQuery.data ? (
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Inching performance</h2>
              <p>Using the existing inching analytics endpoint for the first React cut.</p>
            </div>
          </div>
          <div className="stats-grid">
            {inchingQuery.data.kpis.slice(0, 6).map((kpi) => (
              <article className="stat-card" key={kpi.key}>
                <span>{kpi.label}</span>
                <strong>{kpi.value}</strong>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
