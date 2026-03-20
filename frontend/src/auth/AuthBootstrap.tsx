import { useEffect } from "react";

import { useAuthStore } from "./auth-store";

export function AuthBootstrap({ children }: { children: React.ReactNode }) {
  const bootstrap = useAuthStore((state) => state.bootstrap);
  const initialized = useAuthStore((state) => state.initialized);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  if (!initialized) {
    return (
      <div className="screen-center">
        <div className="panel panel--narrow">
          <h1>Loading GanttBuddy</h1>
          <p>Connecting your React frontend to the existing backend session model.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
