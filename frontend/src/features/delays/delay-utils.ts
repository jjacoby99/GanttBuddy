import type { Delay, DelayInput, DelayType, Phase, Task } from "../../types/api";

export type DelayDraft = DelayInput & {
  local_id: string;
};

export type DelayBreakdownRow = {
  delay_type: DelayType;
  label: string;
  count: number;
  hours: number;
  minutes: number;
};

export type AffectedTask = {
  task: Task;
  phase: Phase | null;
  varianceHours: number | null;
};

export const DELAY_TYPES: DelayType[] = [
  "PERFORMANCE",
  "EQUIPMENT",
  "SAFETY",
  "FOUND_WORK",
  "PREPARATION",
  "MANPOWER_SHORTAGE",
  "OTHER",
];

export const DELAY_META: Record<
  DelayType,
  { label: string; accent: string; surface: string; chart: string; icon: string }
> = {
  PERFORMANCE: {
    label: "Performance",
    accent: "delay-pill--performance",
    surface: "delay-swatch--performance",
    chart: "#2f6fd0",
    icon: "PF",
  },
  EQUIPMENT: {
    label: "Equipment",
    accent: "delay-pill--equipment",
    surface: "delay-swatch--equipment",
    chart: "#9156d4",
    icon: "EQ",
  },
  SAFETY: {
    label: "Safety",
    accent: "delay-pill--safety",
    surface: "delay-swatch--safety",
    chart: "#cf4d4d",
    icon: "SF",
  },
  FOUND_WORK: {
    label: "Found Work",
    accent: "delay-pill--found-work",
    surface: "delay-swatch--found-work",
    chart: "#2c9d6f",
    icon: "FW",
  },
  PREPARATION: {
    label: "Preparation",
    accent: "delay-pill--preparation",
    surface: "delay-swatch--preparation",
    chart: "#c08a23",
    icon: "PR",
  },
  MANPOWER_SHORTAGE: {
    label: "Manpower Shortage",
    accent: "delay-pill--manpower",
    surface: "delay-swatch--manpower",
    chart: "#de7a43",
    icon: "MS",
  },
  OTHER: {
    label: "Other",
    accent: "delay-pill--other",
    surface: "delay-swatch--other",
    chart: "#607086",
    icon: "OT",
  },
};

export function delayTypeLabel(type: DelayType) {
  return DELAY_META[type].label;
}

export function createEmptyDelay(): DelayDraft {
  return {
    local_id: crypto.randomUUID(),
    id: null,
    delay_type: "OTHER",
    duration_minutes: 30,
    description: "",
    start_dt: null,
    end_dt: null,
    shift_assignment_id: null,
  };
}

export function mapDelayToDraft(delay: Delay): DelayDraft {
  return {
    local_id: delay.id ?? crypto.randomUUID(),
    id: delay.id,
    delay_type: delay.delay_type,
    duration_minutes: delay.duration_minutes,
    description: delay.description ?? "",
    start_dt: delay.start_dt,
    end_dt: delay.end_dt,
    shift_assignment_id: delay.shift_assignment_id,
  };
}

export function stripLocalId(rows: DelayDraft[]) {
  return rows.map(({ local_id, ...row }) => row);
}

export function normalizeDelayRows(rows: DelayDraft[]) {
  return rows.map((row) => ({
    ...row,
    description: row.description.trim(),
    duration_minutes: Number.isFinite(row.duration_minutes) ? Math.max(1, Math.round(row.duration_minutes)) : 30,
  }));
}

export function delaysEqual(left: DelayDraft[], right: DelayDraft[]) {
  return JSON.stringify(stripLocalId(normalizeDelayRows(left))) === JSON.stringify(stripLocalId(normalizeDelayRows(right)));
}

export function computeDeletedCount(baseline: DelayDraft[], current: DelayDraft[]) {
  const currentIds = new Set(current.map((row) => row.id).filter(Boolean));
  return baseline.filter((row) => row.id && !currentIds.has(row.id)).length;
}

export function toDelayPayload(rows: DelayDraft[]): DelayInput[] {
  return normalizeDelayRows(rows).map(({ local_id, ...row }) => row);
}

export function resolveDelayEnd(row: DelayDraft) {
  if (row.end_dt) {
    return row.end_dt;
  }
  if (!row.start_dt) {
    return null;
  }
  return new Date(new Date(row.start_dt).getTime() + row.duration_minutes * 60 * 1000).toISOString();
}

export function formatDelayHours(minutes: number) {
  return `${(minutes / 60).toFixed(1)} h`;
}

export function buildDelayBreakdown(rows: DelayDraft[]) {
  const grouped = new Map<DelayType, DelayBreakdownRow>();

  for (const row of rows) {
    const entry = grouped.get(row.delay_type) ?? {
      delay_type: row.delay_type,
      label: delayTypeLabel(row.delay_type),
      count: 0,
      hours: 0,
      minutes: 0,
    };
    entry.count += 1;
    entry.minutes += Math.max(0, row.duration_minutes);
    entry.hours = entry.minutes / 60;
    grouped.set(row.delay_type, entry);
  }

  return Array.from(grouped.values()).sort((left, right) => right.hours - left.hours);
}

export function overlapTasksForDelay(row: DelayDraft, tasks: Task[], phases: Phase[]) {
  if (!row.start_dt) {
    return [] satisfies AffectedTask[];
  }

  const delayStart = new Date(row.start_dt).getTime();
  const delayEndValue = resolveDelayEnd(row);
  if (!delayEndValue) {
    return [] satisfies AffectedTask[];
  }
  const delayEnd = new Date(delayEndValue).getTime();
  const phaseMap = new Map(phases.map((phase) => [phase.id, phase]));

  return tasks
    .filter((task) => task.actual_start && task.actual_end)
    .filter((task) => {
      const actualStart = new Date(task.actual_start!).getTime();
      const actualEnd = new Date(task.actual_end!).getTime();
      return actualStart < delayEnd && actualEnd > delayStart;
    })
    .map((task) => {
      const planned = new Date(task.planned_end).getTime() - new Date(task.planned_start).getTime();
      const actual = new Date(task.actual_end!).getTime() - new Date(task.actual_start!).getTime();
      return {
        task,
        phase: phaseMap.get(task.phase_id) ?? null,
        varianceHours: (actual - planned) / 1000 / 60 / 60,
      };
    })
    .sort((left, right) => (right.varianceHours ?? Number.NEGATIVE_INFINITY) - (left.varianceHours ?? Number.NEGATIVE_INFINITY));
}
