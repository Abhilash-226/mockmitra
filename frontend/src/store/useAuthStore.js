/**
 * Auth Store - User authentication state
 *
 * Manages: login status, user info, tokens
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

const useAuthStore = create(
  persist(
    (set, get) => ({
      // State
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      // Actions
      actions: {
        setUser: (user, token) =>
          set({
            user,
            token,
            isAuthenticated: !!user,
          }),

        logout: () =>
          set({
            user: null,
            token: null,
            isAuthenticated: false,
          }),

        setLoading: (isLoading) => set({ isLoading }),

        updateUser: (updates) =>
          set((state) => ({
            user: state.user ? { ...state.user, ...updates } : null,
          })),
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);

// Named export for components using { useAuthStore }
export { useAuthStore };
export default useAuthStore;
