/**
 * Application Constants
 */

// API
export const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// Storage Keys
export const STORAGE_KEYS = {
  AUTH: "auth-storage",
  EXAM: "exam-storage",
  THEME: "mockmitra-theme",
};

// Timer
export const TIMER_WARNING_THRESHOLD = 300; // 5 minutes in seconds
export const TIMER_CRITICAL_THRESHOLD = 60; // 1 minute in seconds

// Auto-save
export const AUTO_SAVE_INTERVAL = 10000; // 10 seconds

// Pagination
export const DEFAULT_PAGE_SIZE = 20;

// Question palette colors
export const QUESTION_STATUS_COLORS = {
  NOT_VISITED: "#gray",
  VISITED: "#orange",
  ANSWERED: "#green",
  MARKED: "#purple",
  ANSWERED_AND_MARKED: "#purple-green",
};
