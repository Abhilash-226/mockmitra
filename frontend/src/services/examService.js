import api from "./api";
import { API_ENDPOINTS } from "../config/apiEndpoints";

// Get dynamic exams from blueprints
export const getBlueprintExams = async () => {
  const response = await api.get("/blueprints/exams");
  return response.data;
};

// Get customization steps for an exam from blueprints
export const getBlueprintCustomization = async (examCode) => {
  const response = await api.get(`/blueprints/customization/${examCode}`);
  return response.data;
};
/**
 * Exam Service - Exam related API calls
 */

export const examService = {
  // Get all available exams
  getExams: async () => {
    const response = await api.get(API_ENDPOINTS.EXAMS.LIST);
    return response.data;
  },

  // Get exam details and config
  getExamConfig: async (examCode) => {
    const response = await api.get(API_ENDPOINTS.EXAMS.DETAILS(examCode));
    return response.data;
  },

  // Get exam sections
  getExamSections: async (examCode) => {
    const response = await api.get(API_ENDPOINTS.EXAMS.SECTIONS(examCode));
    return response.data;
  },

  // Get exam instructions
  getExamInstructions: async (examCode) => {
    const response = await api.get(API_ENDPOINTS.EXAMS.INSTRUCTIONS(examCode));
    return response.data;
  },

  // Generate a new test
  generateTest: async (testData) => {
    const response = await api.post(API_ENDPOINTS.TESTS.GENERATE, testData);
    return response.data;
  },

  // Start a test attempt
  startTest: async (testId) => {
    const response = await api.post(API_ENDPOINTS.TESTS.START(testId));
    return response.data;
  },

  // Get questions for a test
  getQuestions: async (testId) => {
    const response = await api.get(API_ENDPOINTS.TESTS.QUESTIONS(testId));
    return response.data;
  },

  // Get AI-generated questions for a test
  // Rule-based generation is fast; LLM generation can take longer
  getAIQuestions: async (testId) => {
    const response = await api.get(API_ENDPOINTS.TESTS.AI_QUESTIONS(testId), {
      timeout: 60000, // 1 minute should be plenty for rule-based generation
    });
    return response.data;
  },

  // Submit test
  submitTest: async (testId, answers) => {
    const response = await api.post(API_ENDPOINTS.TESTS.SUBMIT(testId), {
      responses: answers,
    });
    return response.data;
  },

  // Save individual response
  saveResponse: async (testId, responseData) => {
    const response = await api.post(
      API_ENDPOINTS.TESTS.SAVE_RESPONSE(testId),
      responseData,
    );
    return response.data;
  },

  // Get test review with solutions
  getTestReview: async (testId) => {
    const response = await api.get(API_ENDPOINTS.TESTS.REVIEW(testId));
    return response.data;
  },
};

export default examService;
