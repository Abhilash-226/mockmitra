/**
 * QuestionNavigator - Handles question navigation logic
 *
 * Responsibilities:
 * - Previous/Next navigation
 * - Jump to specific question
 * - Track visited questions
 */

class QuestionNavigator {
  constructor(totalQuestions = 0) {
    this.totalQuestions = totalQuestions;
    this.currentIndex = 0;
    this.visitedQuestions = new Set();
  }

  markVisited(index) {
    this.visitedQuestions.add(index);
  }

  goToNext() {
    if (this.currentIndex < this.totalQuestions - 1) {
      this.currentIndex++;
      this.markVisited(this.currentIndex);
      return true;
    }
    return false;
  }

  goToPrevious() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.markVisited(this.currentIndex);
      return true;
    }
    return false;
  }

  jumpToQuestion(index) {
    if (index >= 0 && index < this.totalQuestions) {
      this.currentIndex = index;
      this.markVisited(index);
      return true;
    }
    return false;
  }

  getCurrentIndex() {
    return this.currentIndex;
  }

  isFirstQuestion() {
    return this.currentIndex === 0;
  }

  isLastQuestion() {
    return this.currentIndex === this.totalQuestions - 1;
  }
}

export default QuestionNavigator;
