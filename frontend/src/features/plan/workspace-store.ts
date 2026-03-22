import { create } from "zustand";

import type { Phase, ProjectImportPayload, ProjectSnapshot, ProjectSummary, Task } from "../../types/api";

export type PlanViewMode = "phases" | "tasks";

type WorkspaceState = {
  snapshot: ProjectSnapshot | null;
  draft: ProjectSnapshot | null;
  selectedProjectId: string | null;
  planViewMode: PlanViewMode;
  expandedPhaseIds: string[];
  setPlanViewMode: (mode: PlanViewMode) => void;
  loadSnapshot: (snapshot: ProjectSnapshot) => void;
  clearWorkspace: () => void;
  setProject: (updater: (project: ProjectSummary) => ProjectSummary) => void;
  setPhase: (phaseId: string, updater: (phase: Phase) => Phase) => void;
  setTask: (taskId: string, updater: (task: Task) => Task) => void;
  addPhase: () => void;
  addTask: (phaseId: string) => void;
  togglePhase: (phaseId: string) => void;
  applyServerTask: (task: Task) => void;
  markSaved: () => void;
  isDirty: () => boolean;
  toImportPayload: () => ProjectImportPayload | null;
};

function cloneSnapshot(snapshot: ProjectSnapshot): ProjectSnapshot {
  return JSON.parse(JSON.stringify(snapshot)) as ProjectSnapshot;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  snapshot: null,
  draft: null,
  selectedProjectId: null,
  planViewMode: "phases",
  expandedPhaseIds: [],
  setPlanViewMode: (mode) => set({ planViewMode: mode }),
  loadSnapshot: (snapshot) =>
    set({
      snapshot,
      draft: cloneSnapshot(snapshot),
      selectedProjectId: snapshot.project.id,
      expandedPhaseIds: snapshot.phases.map((phase) => phase.id),
    }),
  clearWorkspace: () =>
    set({
      snapshot: null,
      draft: null,
      selectedProjectId: null,
      expandedPhaseIds: [],
    }),
  setProject: (updater) =>
    set((state) => {
      if (!state.draft) {
        return state;
      }
      return {
        draft: {
          ...state.draft,
          project: updater(state.draft.project),
        },
      };
    }),
  setPhase: (phaseId, updater) =>
    set((state) => {
      if (!state.draft) {
        return state;
      }
      return {
        draft: {
          ...state.draft,
          phases: state.draft.phases.map((phase) => (phase.id === phaseId ? updater(phase) : phase)),
        },
      };
    }),
  setTask: (taskId, updater) =>
    set((state) => {
      if (!state.draft) {
        return state;
      }
      return {
        draft: {
          ...state.draft,
          tasks: state.draft.tasks.map((task) => (task.id === taskId ? updater(task) : task)),
        },
      };
    }),
  addPhase: () =>
    set((state) => {
      if (!state.draft) {
        return state;
      }

      const phaseId = crypto.randomUUID();
      const position = state.draft.phases.length;
      return {
        draft: {
          ...state.draft,
          phases: [
            ...state.draft.phases,
            {
              id: phaseId,
              project_id: state.draft.project.id,
              name: `New Phase ${position + 1}`,
              sort_mode: "manual",
              position,
              planned: true,
            },
          ],
        },
        expandedPhaseIds: [...state.expandedPhaseIds, phaseId],
      };
    }),
  addTask: (phaseId) =>
    set((state) => {
      if (!state.draft) {
        return state;
      }

      const now = new Date();
      const plannedStart = now.toISOString();
      const plannedEnd = new Date(now.getTime() + 60 * 60 * 1000).toISOString();
      const taskPosition = state.draft.tasks.filter((task) => task.phase_id === phaseId).length;
      return {
        draft: {
          ...state.draft,
          tasks: [
            ...state.draft.tasks,
            {
              id: crypto.randomUUID(),
              project_id: state.draft.project.id,
              phase_id: phaseId,
              name: `New Task ${taskPosition + 1}`,
              planned_start: plannedStart,
              planned_end: plannedEnd,
              actual_start: null,
              actual_end: null,
              note: "",
              status: "NOT_STARTED",
              position: taskPosition,
              planned: true,
              task_type: "GENERIC",
            },
          ],
        },
      };
    }),
  togglePhase: (phaseId) =>
    set((state) => ({
      expandedPhaseIds: state.expandedPhaseIds.includes(phaseId)
        ? state.expandedPhaseIds.filter((id) => id !== phaseId)
        : [...state.expandedPhaseIds, phaseId],
    })),
  applyServerTask: (task) =>
    set((state) => {
      if (!state.draft) {
        return state;
      }
      const nextDraft = {
        ...state.draft,
        tasks: state.draft.tasks.map((candidate) => (candidate.id === task.id ? task : candidate)),
      };
      return { draft: nextDraft, snapshot: cloneSnapshot(nextDraft) };
    }),
  markSaved: () =>
    set((state) => {
      if (!state.draft) {
        return state;
      }
      return { snapshot: cloneSnapshot(state.draft) };
    }),
  isDirty: () => {
    const { snapshot, draft } = get();
    if (!snapshot || !draft) {
      return false;
    }
    return JSON.stringify(snapshot) !== JSON.stringify(draft);
  },
  toImportPayload: () => {
    const draft = get().draft;
    if (!draft) {
      return null;
    }

    return {
      project: {
        id: draft.project.id,
        name: draft.project.name,
        description: draft.project.description,
        sort_mode: draft.project.sort_mode,
        closed: draft.project.closed,
        project_type: draft.project.project_type,
        site_id: draft.project.site_id,
        site_code: draft.project.site_code,
        timezone_name: draft.project.timezone_name,
      },
      settings: draft.settings,
      phases: draft.phases,
      tasks: draft.tasks,
      task_predecessors: draft.task_predecessors,
      phase_predecessors: draft.phase_predecessors,
      metadata: draft.metadata,
      shift_definition: draft.shift_definition,
      shift_assignments: draft.shift_assignments,
    };
  },
}));
