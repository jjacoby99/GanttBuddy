import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "./auth-store";

export function AuthCallbackPage() {
  const token = useAuthStore((state) => state.token);
  const finishLogin = useAuthStore((state) => state.finishLogin);
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const attempted = useRef(false);

  useEffect(() => {
    if (attempted.current) {
      return;
    }
    attempted.current = true;
    const search = new URLSearchParams(location.search);
    void finishLogin(search).catch((err) => {
      setError(err instanceof Error ? err.message : "Sign in failed");
    });
  }, [finishLogin, location.search]);

  if (token) {
    return <Navigate to="/projects" replace />;
  }

  return (
    <div className="screen-center">
      <div className="panel panel--narrow">
        <h1>Signing you in</h1>
        <p>{error ?? "Finishing your secure login and loading your workspace."}</p>
      </div>
    </div>
  );
}
