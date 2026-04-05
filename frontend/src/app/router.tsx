import { createBrowserRouter, Navigate } from "react-router-dom";

import { AuthCallbackPage } from "../auth/AuthCallbackPage";
import { LoginPage } from "../auth/LoginPage";
import { AnalyticsPage } from "../features/analytics/AnalyticsPage";
import { DelaysPage } from "../features/delays/DelaysPage";
import { ExecutePage } from "../features/execute/ExecutePage";
import { PlanPage } from "../features/plan/PlanPage";
import { ProjectsPage } from "../features/projects/ProjectsPage";
import { AppShell } from "../components/AppShell";
import { ProtectedRoute } from "../components/ProtectedRoute";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/auth/callback",
    element: <AuthCallbackPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <Navigate to="/projects" replace /> },
          { path: "/projects", element: <ProjectsPage /> },
          { path: "/workspace/plan", element: <PlanPage /> },
          { path: "/workspace/execute", element: <ExecutePage /> },
          { path: "/workspace/delays", element: <DelaysPage /> },
          { path: "/workspace/analytics", element: <AnalyticsPage /> },
        ],
      },
    ],
  },
]);
