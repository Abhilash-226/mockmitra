/**
 * PYQ Papers Service
 */
import api from "./api";
import { API_ENDPOINTS } from "../config/apiEndpoints";

export const pyqService = {
  /**
   * Get list of all available PYQ papers
   */
  getPapers: async (examCode = null) => {
    const params = examCode ? { exam_code: examCode } : {};
    const response = await api.get(API_ENDPOINTS.PYQ.LIST, { params });
    return response.data;
  },

  /**
   * Get available years for PYQ papers
   */
  getYears: async (examCode = null) => {
    const params = examCode ? { exam_code: examCode } : {};
    const response = await api.get(API_ENDPOINTS.PYQ.YEARS, { params });
    return response.data;
  },

  /**
   * Get paper details
   */
  getPaper: async (paperId) => {
    const response = await api.get(API_ENDPOINTS.PYQ.DETAILS(paperId));
    return response.data;
  },

  /**
   * Get questions for a paper
   */
  getQuestions: async (paperId) => {
    const response = await api.get(API_ENDPOINTS.PYQ.QUESTIONS(paperId));
    return response.data;
  },

  /**
   * Submit a PYQ test attempt.
   * Persists to DB so it appears in history & supports detailed analytics.
   */
  submitPyqTest: async ({ paperId, answers, timeTakenSeconds }) => {
    const response = await api.post(
      API_ENDPOINTS.PYQ.SUBMIT,
      {
        paper_id: paperId,
        answers,
        time_taken_seconds: timeTakenSeconds,
      },
      {
        timeout: 120000,
      },
    );
    return response.data;
  },
};

export default pyqService;
