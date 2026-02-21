/**
 * Analytics Service - Analytics API calls
 */

import api from "./api";
import { API_ENDPOINTS } from "../config/apiEndpoints";

export const analyticsService = {
  // Get user's dashboard analytics
  getDashboard: async () => {
    const response = await api.get(API_ENDPOINTS.ANALYTICS.DASHBOARD);
    return response.data;
  },

  // Get performance for a specific exam
  getExamPerformance: async (examCode) => {
    const response = await api.get(
      API_ENDPOINTS.ANALYTICS.PERFORMANCE(examCode),
    );
    return response.data;
  },

  // Get detailed analytics for an attempt
  getAttemptAnalytics: async (attemptId) => {
    const response = await api.get(API_ENDPOINTS.ANALYTICS.ATTEMPT(attemptId));
    return response.data;
  },

  // Generate a step-by-step solution via LLM
  generateSolution: async ({ questionText, options, correctAnswer, topic, section }) => {
    const response = await api.post(API_ENDPOINTS.ANALYTICS.GENERATE_SOLUTION, {
      question_text: questionText,
      options,
      correct_answer: correctAnswer,
      topic,
      section,
    });
    return response.data;
  },

  // Get blueprint statistics
  getBlueprintStats: async () => {
    const response = await api.get(API_ENDPOINTS.BLUEPRINTS.STATISTICS);
    return response.data;
  },
};

export default analyticsService;
