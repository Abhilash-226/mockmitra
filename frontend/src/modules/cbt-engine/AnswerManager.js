/**
 * AnswerManager - Handles answer state and persistence
 *
 * Responsibilities:
 * - Store answers
 * - Mark for review
 * - Persist to local storage / IndexedDB
 * - Sync with server
 */

class AnswerManager {
  constructor() {
    this.answers = new Map(); // questionId -> selectedOption
    this.markedForReview = new Set();
  }

  setAnswer(questionId, option) {
    this.answers.set(questionId, option);
    this.persistLocally();
  }

  clearAnswer(questionId) {
    this.answers.delete(questionId);
    this.persistLocally();
  }

  getAnswer(questionId) {
    return this.answers.get(questionId) || null;
  }

  toggleMarkForReview(questionId) {
    if (this.markedForReview.has(questionId)) {
      this.markedForReview.delete(questionId);
    } else {
      this.markedForReview.add(questionId);
    }
    this.persistLocally();
  }

  isMarkedForReview(questionId) {
    return this.markedForReview.has(questionId);
  }

  getAllAnswers() {
    return Object.fromEntries(this.answers);
  }

  persistLocally() {
    // Save to IndexedDB / localStorage
    try {
      const data = {
        answers: Object.fromEntries(this.answers),
        markedForReview: Array.from(this.markedForReview),
        timestamp: Date.now(),
      };
      localStorage.setItem("exam_progress", JSON.stringify(data));
    } catch (error) {
      console.error("Failed to persist answers:", error);
    }
  }

  restoreFromLocal() {
    try {
      const data = JSON.parse(localStorage.getItem("exam_progress"));
      if (data) {
        this.answers = new Map(Object.entries(data.answers || {}));
        this.markedForReview = new Set(data.markedForReview || []);
        return true;
      }
    } catch (error) {
      console.error("Failed to restore answers:", error);
    }
    return false;
  }
}

export default AnswerManager;
