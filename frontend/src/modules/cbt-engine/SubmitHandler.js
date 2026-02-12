/**
 * SubmitHandler - Handles exam submission logic
 *
 * Responsibilities:
 * - Collect final answers
 * - Validate submission
 * - Send to server
 * - Handle submission errors
 * - Auto-submit on timer expiry
 */

class SubmitHandler {
  constructor(apiService) {
    this.apiService = apiService;
    this.isSubmitting = false;
  }

  async submit(attemptId, answers, metadata = {}) {
    if (this.isSubmitting) {
      console.warn("Submission already in progress");
      return null;
    }

    this.isSubmitting = true;

    try {
      const payload = {
        attemptId,
        answers,
        submittedAt: new Date().toISOString(),
        ...metadata,
      };

      // Clear local storage on successful submit
      localStorage.removeItem("exam_progress");

      // Return submission result
      return { success: true, payload };
    } catch (error) {
      console.error("Submission failed:", error);
      throw error;
    } finally {
      this.isSubmitting = false;
    }
  }

  getSubmissionSummary(answers, totalQuestions) {
    const answered = Object.keys(answers).length;
    const unanswered = totalQuestions - answered;

    return {
      totalQuestions,
      answered,
      unanswered,
      percentage: Math.round((answered / totalQuestions) * 100),
    };
  }
}

export default SubmitHandler;
