import { RouterProvider } from "react-router-dom";

import { AuthBootstrap } from "../auth/AuthBootstrap";
import { AppQueryProvider } from "./QueryProvider";
import { router } from "./router";

export function App() {
  return (
    <AppQueryProvider>
      <AuthBootstrap>
        <RouterProvider router={router} />
      </AuthBootstrap>
    </AppQueryProvider>
  );
}
