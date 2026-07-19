'use client';
import React, { createContext, useCallback, useContext, useState } from 'react';
import { UserData } from './types';
import { api } from './api';
import { useQuery } from './hooks';

interface AppContextValue {
  currentUserId: string | null;
  setCurrentUserId: (id: string) => void;
  continueAsUser: (username: string) => Promise<UserData>;
  cacheUser: (user: UserData) => void;
  getCachedUser: (id: string) => UserData | undefined;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [userCache, setUserCache] = useState<Record<string, UserData>>({});

  const cacheUser = useCallback((user: UserData) => {
    setUserCache((prev) => ({ ...prev, [user.id]: user }));
  }, []);

  const getCachedUser = useCallback((id: string) => userCache[id], [userCache]);

  const continueAsUser = useCallback(async (username: string) => {
    const name = username.trim() || 'Athlete';
    const user = await api.users.create({ username: name });
    cacheUser(user);
    setCurrentUserId(user.id);
    return user;
  }, [cacheUser]);

  return (
    <AppContext.Provider value={{ currentUserId, setCurrentUserId, continueAsUser, cacheUser, getCachedUser }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

export function useCurrentUser() {
  const { currentUserId, getCachedUser, cacheUser } = useApp();
  const cached = currentUserId ? getCachedUser(currentUserId) : undefined;

  const query = useQuery<UserData>(async () => {
    const user = await api.users.get(currentUserId as string);
    cacheUser(user);
    return user;
  }, [currentUserId], !!currentUserId && !cached);

  return {
    user: cached ?? query.data,
    loading: !currentUserId ? false : (!cached && query.loading),
    error: query.error,
  };
}
