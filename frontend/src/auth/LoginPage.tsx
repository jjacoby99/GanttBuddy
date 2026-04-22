import { useState } from "react";
import { Navigate } from "react-router-dom";

import { env } from "../lib/env";
import { useAuthStore } from "./auth-store";

export function LoginPage() {
  const token = useAuthStore((state) => state.token);
  const beginLogin = useAuthStore((state) => state.beginLogin);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) {
    return <Navigate to="/projects" replace />;
  }

  const handleLogin = async () => {
    setPending(true);
    setError(null);
    try {
      await beginLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
      setPending(false);
    }
  };

  return (
    <div className="screen-center">
      <div className="panel panel--narrow login-panel">
        <span className="eyebrow">GanttBuddy</span>
        <h1>Sign in</h1>
        <p>
          Authenticate with your organization account to enter the project workspace.
        </p>

        <button className="button" disabled={pending} onClick={handleLogin} type="button">
          {pending ? "Redirecting..." : `Continue with ${env.oidcProviderName}`}
        </button>

        {error ? <p className="error-text">{error}</p> : null}
      </div>
    </div>
  );
}
