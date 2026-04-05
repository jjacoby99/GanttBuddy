export type Id = string;

export interface Role {
  id: Id;
  name: string;
}

export interface User {
  id: Id;
  email: string;
  name: string;
  is_active: boolean;
  created_at: string;
  auth_provider?: string | null;
  last_login_at?: string | null;
  roles: Role[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OIDCExchangeRequest {
  id_token: string;
}

export interface ProjectSettings {
  project_id?: Id;
  work_all_day: boolean;
  work_start_time: string | null;
  work_end_time: string | null;
  working_days_mask: number;
  observe_state_holidays: boolean;
  province: string | null;
  duration_resolution: string;
}

export interface ProjectSummary {
  id: Id;
  name: string;
  description: string | null;
  sort_mode: string;
  closed: boolean;
  created_by_user_id: Id | null;
  created_at: string;
  updated_at: string;
  project_type: string;
  planned_start: string | null;
  planned_finish: string | null;
  site_id: Id | null;
  site_code?: string | null;
  timezone_name: string;
}

export interface Phase {
  id: Id;
  project_id: Id;
  name: string;
  sort_mode: string;
  position: number;
  planned: boolean;
}

export interface Task {
  id: Id;
  project_id: Id;
  project_name?: string | null;
  phase_id: Id;
  name: string;
  planned_start: string;
  planned_end: string;
  actual_start: string | null;
  actual_end: string | null;
  note: string;
  status: string;
  position: number;
  planned: boolean;
  task_type: string;
}

export interface TaskPredecessor {
  task_id: Id;
  predecessor_task_id: Id;
}

export interface PhasePredecessor {
  phase_id: Id;
  predecessor_phase_id: Id;
}

export interface ShiftDefinition {
  id?: Id;
  project_id: Id;
  day_start_time: string;
  night_start_time: string;
  shift_length_hours: number;
  timezone?: string;
}

export interface ShiftAssignment {
  id?: Id;
  project_id: Id;
  crew_id: Id;
  shift_type: string;
  start_date: string;
  end_date: string;
}

export type DelayType =
  | "PERFORMANCE"
  | "EQUIPMENT"
  | "SAFETY"
  | "FOUND_WORK"
  | "PREPARATION"
  | "MANPOWER_SHORTAGE"
  | "OTHER";

export interface Delay {
  id: Id;
  project_id: Id;
  delay_type: DelayType;
  duration_minutes: number;
  description: string;
  start_dt: string | null;
  end_dt: string | null;
  shift_assignment_id: Id | null;
  created_by: Id;
  created_at: string;
  updated_at: string | null;
  updated_by: Id | null;
}

export interface DelayInput {
  id?: Id | null;
  delay_type: DelayType;
  duration_minutes: number;
  description: string;
  start_dt: string | null;
  end_dt: string | null;
  shift_assignment_id?: Id | null;
}

export interface ProjectSnapshot {
  project: ProjectSummary;
  settings: ProjectSettings | null;
  phases: Phase[];
  tasks: Task[];
  task_predecessors: TaskPredecessor[];
  phase_predecessors: PhasePredecessor[];
  metadata: Record<string, unknown> | null;
  shift_definition: ShiftDefinition | null;
  shift_assignments: ShiftAssignment[] | null;
}

export interface AttentionResponse {
  late_tasks: Task[];
  upcoming_tasks: Task[];
  awaiting_actuals: Task[];
}

export interface CreateProjectInput {
  name: string;
  description?: string;
}

export interface ProjectImportProject {
  id: Id;
  name: string;
  description: string | null;
  sort_mode: string;
  closed: boolean;
  project_type: string;
  site_id: Id | null;
  site_code?: string | null;
  timezone_name: string;
}

export interface ProjectImportPayload {
  project: ProjectImportProject;
  settings: ProjectSettings | null;
  phases: Phase[];
  tasks: Task[];
  task_predecessors: TaskPredecessor[];
  phase_predecessors: PhasePredecessor[];
  metadata: Record<string, unknown> | null;
  shift_definition: ShiftDefinition | null;
  shift_assignments: ShiftAssignment[] | null;
}

export interface SaveProjectResponse {
  project_id: Id;
}

export interface Kpi {
  key: string;
  label: string;
  value: number | string | null;
  unit?: string | null;
}

export interface EventCountRow {
  event_type: string;
  count: number;
}

export interface SeriesPoint {
  x: string;
  y: number;
}

export interface NamedSeries {
  name: string;
  points: SeriesPoint[];
}

export interface OverviewAnalytics {
  project_id: Id;
  as_of: string;
  kpis: Kpi[];
  events_by_type: EventCountRow[];
  task_counts: Record<string, number>;
}

export interface BurnupAnalytics {
  project_id: Id;
  as_of: string;
  cumulative_planned_hours: SeriesPoint[];
  cumulative_actual_hours: SeriesPoint[];
}

export interface PhaseBreakdownRow {
  phase_id: Id;
  phase_name: string;
  task_count: number;
  planned_hours: number;
  actual_hours: number;
  delta_hours: number;
  pct_complete: number;
}

export interface PhaseAnalytics {
  project_id: Id;
  as_of: string;
  rows: PhaseBreakdownRow[];
}

export interface TaskTypeBreakdownRow {
  task_type: string;
  task_count: number;
  planned_hours: number;
  actual_hours: number;
}

export interface TaskTypeAnalytics {
  project_id: Id;
  as_of: string;
  rows: TaskTypeBreakdownRow[];
}

export interface EventsTimelineAnalytics {
  project_id: Id;
  as_of: string;
  series: NamedSeries[];
}

export interface DashboardAnalytics {
  project_id: Id;
  as_of: string;
  metadata: Record<string, unknown> | null;
  reline_metadata: Record<string, unknown> | null;
  overview: OverviewAnalytics;
  burnup: BurnupAnalytics;
  by_phase: PhaseAnalytics;
  by_task_type: TaskTypeAnalytics;
  events_timeline: EventsTimelineAnalytics;
}

export interface ShiftInchRow {
  crew_id: Id;
  crew_name: string;
  shift_type: string;
  shift_date: string;
  kpis: Kpi[];
  task_series: {
    name: string;
    points: { x: string; y: number }[];
  };
}

export interface InchingAnalytics {
  project_id: Id;
  as_of: string;
  kpis: Kpi[];
  series: NamedSeries[];
  shift_inch_performance: ShiftInchRow[];
}

export interface TaskActionInput {
  occurred_at?: string;
}

export interface TaskNoteInput {
  note: string;
}

export interface TaskStatusInput {
  status: string;
}

export interface TaskActualsInput {
  actual_start?: string | null;
  actual_end?: string | null;
  reason: string;
}
