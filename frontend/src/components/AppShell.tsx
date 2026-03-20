import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuthStore } from "../auth/auth-store";
import { useWorkspaceStore } from "../features/plan/workspace-store";

const navItems = [
  { to: "/projects", label: "Projects" },
  { to: "/workspace/plan", label: "Plan" },
  { to: "/workspace/execute", label: "Execute" },
  { to: "/workspace/analytics", label: "Analytics" },
];

export function AppShell() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const project = useWorkspaceStore((state) => state.snapshot?.project);
  const location = useLocation();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__eyebrow">GanttBuddy</div>
          <div className="brand__title">Project Workspace</div>
          <p className="brand__copy">Plan, track, and review project schedules in one place.</p>
        </div>

        <nav className="nav">
          {navItems.map((item) => {
            const disabled = item.to !== "/projects" && !project;
            return (
              <NavLink
                key={item.to}
                to={disabled ? location.pathname : item.to}
                className={({ isActive }) =>
                  `nav__item ${isActive ? "nav__item--active" : ""} ${disabled ? "nav__item--disabled" : ""}`
                }
              >
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar__footer">
          <div className="user-card">
            <strong>{user?.name ?? "Unknown user"}</strong>
            <span>{user?.email ?? ""}</span>
            <span>{project ? `Project: ${project.name}` : "No project loaded"}</span>
          </div>
          <button className="button button--ghost" onClick={logout} type="button">
            Log out
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
