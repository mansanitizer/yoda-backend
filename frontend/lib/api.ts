import { apiClient } from './api-client';
import { UserData, SessionData } from './types';

export interface CreateUserPayload {
  username: string;
}

export type SessionWithOwner = SessionData & { userId: string };

export const api = {
  users: {
    get: (id: string) => apiClient.get<UserData>(`/users/${encodeURIComponent(id)}`),
    search: (query: string) => apiClient.get<UserData[]>(`/users?q=${encodeURIComponent(query)}`),
    create: (payload: CreateUserPayload) => apiClient.post<UserData>('/users', payload),
  },
  sessions: {
    get: (id: string) => apiClient.get<SessionWithOwner>(`/sessions/${encodeURIComponent(id)}`),
  },
};
