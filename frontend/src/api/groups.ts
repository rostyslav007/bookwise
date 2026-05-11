import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { del, get, post, put } from "@/api/client";

export interface Group {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
}

interface CreateGroupPayload {
  name: string;
}

interface UpdateGroupPayload {
  id: string;
  name: string;
}

const GROUPS_QUERY_KEY = ["groups"] as const;
const GROUPS_URL = "/api/v1/groups/";

export function useGroups() {
  return useQuery<Group[]>({
    queryKey: GROUPS_QUERY_KEY,
    queryFn: () => get<Group[]>(GROUPS_URL),
  });
}

export function useCreateGroup() {
  const queryClient = useQueryClient();

  return useMutation<Group, Error, CreateGroupPayload>({
    mutationFn: (payload) => post<Group>(GROUPS_URL, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GROUPS_QUERY_KEY });
    },
  });
}

export function useUpdateGroup() {
  const queryClient = useQueryClient();

  return useMutation<Group, Error, UpdateGroupPayload>({
    mutationFn: ({ id, name }) =>
      put<Group>(`${GROUPS_URL}${id}`, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GROUPS_QUERY_KEY });
    },
  });
}

export function useDeleteGroup() {
  const queryClient = useQueryClient();

  return useMutation<void, Error, string>({
    mutationFn: (id) => del(`${GROUPS_URL}${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: GROUPS_QUERY_KEY });
    },
  });
}
