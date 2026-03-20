import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import { useAuthStore } from "../../auth/auth-store";

export function useProjectsQuery() {
  const token = useAuthStore((state) => state.token);
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.listProjects(token!, true),
    enabled: Boolean(token),
  });
}

export function useAttentionQuery() {
  const token = useAuthStore((state) => state.token);
  return useQuery({
    queryKey: ["attention"],
    queryFn: () => api.getAttention(token!),
    enabled: Boolean(token),
  });
}
