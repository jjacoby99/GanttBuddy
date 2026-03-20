import { env } from "../lib/env";
import type {
  AttentionResponse,
  CreateProjectInput,
  Delay,
  DelayInput,
  DashboardAnalytics,
  InchingAnalytics,
  ProjectImportPayload,
  ProjectSnapshot,
  ProjectSummary,
  SaveProjectResponse,
  Task,
  TaskActualsInput,
  TaskActionInput,
  TaskNoteInput,
  TaskStatusInput,
  TokenResponse,
  User,
} from "../types/api";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  token?: string | null;
  body?: BodyInit | null;
  headers?: HeadersInit;
};

function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
) {
  const url = new URL(`${env.apiBaseUrl}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }
  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
  params?: Record<string, string | number | boolean | undefined | null>,
) {
  const response = await fetch(buildUrl(path, params), {
    method: options.method ?? "GET",
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
      ...options.headers,
    },
    body: options.body,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      message = payload.detail ?? JSON.stringify(payload);
    } catch {
      const text = await response.text();
      if (text) {
        message = text;
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  login(email: string, password: string) {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  me(token: string) {
    return request<User>("/auth/me", { token });
  },

  listProjects(token: string, includeClosed = true) {
    return request<ProjectSummary[]>("/projects", { token }, { include_closed: includeClosed });
  },

  getAttention(token: string) {
    return request<AttentionResponse>("/projects/attention", { token });
  },

  createProject(token: string, payload: CreateProjectInput) {
    return request<ProjectSummary>("/projects", {
      method: "POST",
      token,
      body: JSON.stringify({
        name: payload.name,
        description: payload.description ?? null,
        sort_mode: "manual",
        closed: false,
        settings: null,
      }),
    });
  },

  getSnapshot(token: string, projectId: string) {
    return request<ProjectSnapshot>(`/projects/${projectId}/snapshot`, { token });
  },

  saveProject(token: string, payload: ProjectImportPayload) {
    return request<SaveProjectResponse>("/projects/import", {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    });
  },

  getDashboard(
    token: string,
    projectId: string,
    params?: { date_from?: string; date_to?: string },
  ) {
    return request<DashboardAnalytics>(
      `/projects/${projectId}/analytics/dashboard`,
      { token },
      params,
    );
  },

  getInching(
    token: string,
    projectId: string,
    params?: { date_from?: string; date_to?: string },
  ) {
    return request<InchingAnalytics>(
      `/projects/${projectId}/analytics/inching-performance`,
      { token },
      params,
    );
  },

  getDelays(
    token: string,
    projectId: string,
    params?: {
      delay_type?: string;
      shift_assignment_id?: string;
      time_min?: string;
      time_max?: string;
      limit?: number;
    },
  ) {
    return request<Delay[]>("/delays", { token }, { project_id: projectId, ...params });
  },

  saveDelays(
    token: string,
    projectId: string,
    payload: DelayInput[],
    options?: { replace?: boolean },
  ) {
    return request<Delay[]>(`/delays/${projectId}/delays`, {
      method: "PUT",
      token,
      body: JSON.stringify(payload),
    }, { replace: options?.replace ? "true" : undefined });
  },

  startTask(token: string, taskId: string, body: TaskActionInput) {
    return request<Task>(`/tasks/${taskId}/start`, {
      method: "POST",
      token,
      body: JSON.stringify(body),
    });
  },

  finishTask(token: string, taskId: string, body: TaskActionInput) {
    return request<Task>(`/tasks/${taskId}/finish`, {
      method: "POST",
      token,
      body: JSON.stringify(body),
    });
  },

  setTaskNote(token: string, taskId: string, body: TaskNoteInput) {
    return request<Task>(`/tasks/${taskId}/note`, {
      method: "POST",
      token,
      body: JSON.stringify(body),
    });
  },

  setTaskStatus(token: string, taskId: string, body: TaskStatusInput) {
    return request<Task>(`/tasks/${taskId}/status`, {
      method: "POST",
      token,
      body: JSON.stringify(body),
    });
  },

  editTaskActuals(token: string, taskId: string, body: TaskActualsInput) {
    return request<Task>(`/tasks/${taskId}/actuals`, {
      method: "PATCH",
      token,
      body: JSON.stringify(body),
    });
  },
};
