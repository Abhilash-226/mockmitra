/**
 * API Endpoints Configuration
 */

export const API_ENDPOINTS = {
  // Auth
  AUTH: {
    LOGIN: "/auth/login",
    REGISTER: "/auth/register",
    LOGOUT: "/auth/logout",
    FORGOT_PASSWORD: "/auth/forgot-password",
    RESET_PASSWORD: "/auth/reset-password",
    VERIFY_EMAIL: "/auth/verify-email",
    PROFILE: "/auth/profile",
    CHANGE_PASSWORD: "/auth/change-password",
  },

  // Exams
  EXAMS: {
    LIST: "/exams",
    DETAILS: (examCode) => `/exams/${examCode}`,
    SECTIONS: (examCode) => `/exams/${examCode}/sections`,
    INSTRUCTIONS: (examCode) => `/exams/${examCode}/instructions`,
  },

  // Tests
  TESTS: {
    GENERATE: "/tests/generate",
    START: (testId) => `/tests/${testId}/start`,
    QUESTIONS: (testId) => `/tests/${testId}/questions`,
    AI_QUESTIONS: (testId) => `/tests/${testId}/ai-questions`,
    SUBMIT: (testId) => `/tests/${testId}/submit`,
    SAVE_RESPONSE: (testId) => `/tests/${testId}/response`,
    REVIEW: (testId) => `/tests/${testId}/review`,
    HISTORY: "/tests/history",
  },

  // Analytics
  ANALYTICS: {
    DASHBOARD: "/analytics/dashboard",
    PERFORMANCE: (examCode) => `/analytics/performance/${examCode}`,
    ATTEMPT: (attemptId) => `/analytics/attempt/${attemptId}`,
    GENERATE_SOLUTION: "/analytics/generate-solution",
  },

  // Blueprints
  BLUEPRINTS: {
    LIST: "/blueprints",
    STATISTICS: "/blueprints/statistics",
    GENERATE: "/blueprints/generate",
    GENERATE_TEST: "/blueprints/generate-test",
  },

  // PYQ Papers
  PYQ: {
    LIST: "/pyq/papers",
    YEARS: "/pyq/years",
    DETAILS: (paperId) => `/pyq/papers/${paperId}`,
    QUESTIONS: (paperId) => `/pyq/papers/${paperId}/questions`,
    SUBMIT: "/pyq/submit",
    SOLUTION: (paperId, questionNumber) =>
      `/pyq/solutions/${paperId}/${questionNumber}`,
  },
};
