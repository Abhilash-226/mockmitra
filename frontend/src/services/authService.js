/**
 * Auth Service - Authentication API calls
 */

import api from "./api";

// Google OAuth Client ID - Replace with your actual client ID from Google Cloud Console
export const GOOGLE_CLIENT_ID =
  import.meta.env.VITE_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID";

export const authService = {
  /**
   * Login user with email and password
   * @param {Object} credentials - { email, password }
   * @returns {Promise<{ access_token, token_type, user }>}
   */
  login: async (credentials) => {
    const response = await api.post("/auth/login", {
      email: credentials.email,
      password: credentials.password,
    });
    return response.data;
  },

  /**
   * Register new user
   * @param {Object} userData - { email, password, full_name, target_exam }
   * @returns {Promise<{ access_token, token_type, user }>}
   */
  register: async (userData) => {
    const response = await api.post("/auth/register", {
      email: userData.email,
      password: userData.password,
      full_name: userData.full_name || userData.name,
      target_exam: userData.target_exam || userData.targetExam,
    });
    return response.data;
  },

  /**
   * Login/Register with Google OAuth
   * @param {string} credential - Google ID token
   * @returns {Promise<{ access_token, token_type, user }>}
   */
  googleLogin: async (credential) => {
    const response = await api.post("/auth/google", { credential });
    return response.data;
  },

  /**
   * Get current user profile
   * @returns {Promise<User>}
   */
  getProfile: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  /**
   * Forgot password - request reset link
   * @param {string} email
   */
  forgotPassword: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  /**
   * Reset password with token
   * @param {Object} data - { token, password }
   */
  resetPassword: async (data) => {
    const response = await api.post("/auth/reset-password", data);
    return response.data;
  },

  /**
   * Verify email with token
   * @param {string} token
   */
  verifyEmail: async (token) => {
    const response = await api.post("/auth/verify-email", { token });
    return response.data;
  },

  /**
   * Update user profile
   * @param {Object} data
   */
  updateProfile: async (data) => {
    const response = await api.put("/auth/me", data);
    return response.data;
  },

  /**
   * Change password
   * @param {Object} data - { current_password, new_password }
   */
  changePassword: async (data) => {
    const response = await api.put("/auth/change-password", data);
    return response.data;
  },
};

export default authService;
