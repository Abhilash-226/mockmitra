/**
 * useAuth Hook - Authentication utilities
 */

import { useCallback } from "react";
import { useAuthStore } from "../store";
import { authService } from "../services";

export default function useAuth() {
  const { user, token, isAuthenticated, isLoading, actions } = useAuthStore();

  const login = useCallback(
    async (credentials) => {
      actions.setLoading(true);
      try {
        const response = await authService.login(credentials);
        actions.setUser(response.user, response.access_token);
        return response;
      } finally {
        actions.setLoading(false);
      }
    },
    [actions],
  );

  const register = useCallback(
    async (userData) => {
      actions.setLoading(true);
      try {
        const response = await authService.register(userData);
        actions.setUser(response.user, response.access_token);
        return response;
      } finally {
        actions.setLoading(false);
      }
    },
    [actions],
  );

  const logout = useCallback(() => {
    actions.logout();
  }, [actions]);

  const getProfile = useCallback(async () => {
    try {
      const profile = await authService.getProfile();
      actions.updateUser(profile);
      return profile;
    } catch (error) {
      // If profile fetch fails, user might be logged out
      if (error.response?.status === 401) {
        actions.logout();
      }
      throw error;
    }
  }, [actions]);

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    getProfile,
  };
}
