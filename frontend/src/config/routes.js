/**
 * Route Configuration
 */

export const ROUTES = {
  // Public
  HOME: "/",
  LOGIN: "/login",
  REGISTER: "/register",
  FORGOT_PASSWORD: "/forgot-password",
  RESET_PASSWORD: "/reset-password",

  // Dashboard
  DASHBOARD: "/dashboard",
  PROFILE: "/profile",
  PYQ_PAPERS: "/pyq-papers",

  // Exams
  EXAMS: "/exams",
  EXAM_CUSTOMIZE: "/exam/:examId/customize",
  EXAM_INSTRUCTIONS: "/exam/:examId/instructions",
  EXAM_ATTEMPT: "/exam/:examId/attempt",
  EXAM_SUBMIT: "/exam/:examId/submit",

  // Results
  RESULTS: "/results/:attemptId",
  ANALYTICS: "/analytics",
};

// Helper to generate dynamic routes
export const generateRoute = {
  examCustomize: (examId) => `/exam/${examId}/customize`,
  examInstructions: (examId) => `/exam/${examId}/instructions`,
  examAttempt: (examId) => `/exam/${examId}/attempt`,
  examSubmit: (examId) => `/exam/${examId}/submit`,
  results: (attemptId) => `/results/${attemptId}`,
};
