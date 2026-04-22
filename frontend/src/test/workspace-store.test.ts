import { beforeEach, describe, expect, it } from "vitest";

import { useWorkspaceStore } from "../features/plan/workspace-store";
import type { ProjectSnapshot } from "../types/api";

const snapshot: ProjectSnapshot = {
  project: {
    id: "project-1",
    name: "Test Project",
    description: null,
    sort_mode: "manual",
    closed: false,
    created_by_user_id: null,
    created_at: "2026-03-20T16:00:00Z",
    updated_at: "2026-03-20T16:00:00Z",
    project_type: "GENERIC",
    planned_start: null,
    planned_finish: null,
    site_id: null,
    timezone_name: "America/Vancouver",
  },
  settings: null,
  phases: [
    {
      id: "phase-1",
      project_id: "project-1",
      name: "Phase 1",
      sort_mode: "manual",
      position: 0,
      planned: true,
    },
  ],
  tasks: [
    {
      id: "task-1",
      project_id: "project-1",
      phase_id: "phase-1",
      name: "Task 1",
      planned_start: "2026-03-20T16:00:00Z",
      planned_end: "2026-03-20T18:00:00Z",
      actual_start: null,
      actual_end: null,
      note: "",
      status: "PLANNED",
      position: 0,
      planned: true,
      task_type: "GENERIC",
    },
  ],
  task_predecessors: [],
  phase_predecessors: [],
  metadata: null,
  shift_definition: null,
  shift_assignments: null,
};

describe("workspace store", () => {
  beforeEach(() => {
    useWorkspaceStore.getState().clearWorkspace();
  });

  it("converts draft state into import payload", () => {
    useWorkspaceStore.getState().loadSnapshot(snapshot);
    useWorkspaceStore.getState().setTask("task-1", (task) => ({ ...task, name: "Updated task" }));

    const payload = useWorkspaceStore.getState().toImportPayload();

    expect(payload?.project.id).toBe("project-1");
    expect(payload?.tasks[0].name).toBe("Updated task");
    expect(useWorkspaceStore.getState().isDirty()).toBe(true);
  });

  it("marks the workspace clean after save", () => {
    useWorkspaceStore.getState().loadSnapshot(snapshot);
    useWorkspaceStore.getState().setProject((project) => ({ ...project, name: "Updated project" }));

    expect(useWorkspaceStore.getState().isDirty()).toBe(true);

    useWorkspaceStore.getState().markSaved();

    expect(useWorkspaceStore.getState().isDirty()).toBe(false);
  });
});
