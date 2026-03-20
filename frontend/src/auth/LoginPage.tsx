import { useState } from "react";
import { Navigate } from "react-router-dom";

import { useAuthStore } from "./auth-store";

export function LoginPage() {
  const token = useAuthStore((state) => state.token);
  const login = useAuthStore((state) => state.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (token) {
    return <Navigate to="/projects" replace />;
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="screen-center">
      <form className="panel panel--narrow login-panel" onSubmit={handleSubmit}>
        <span className="eyebrow">GanttBuddy React MVP</span>
        <h1>Sign in</h1>
        <p>Authenticate against the existing FastAPI backend and keep Streamlit available in parallel.</p>

        <label>
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        <label>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        <button className="button" disabled={pending} type="submit">
          {pending ? "Signing in..." : "Sign in"}
        </button>

        {error ? <p className="error-text">{error}</p> : null}
      </form>
    </div>
  );
}
