/**
 * Exam Analytics - Calculate and analyze exam performance
 *
 * READ-ONLY: Never mutates exam state
 */

export function calculateScore(answers, questions, markingScheme) {
  let score = 0;
  let correct = 0;
  let incorrect = 0;
  let unattempted = 0;

  questions.forEach((question) => {
    const userAnswer = answers[question.id];

    if (!userAnswer) {
      unattempted++;
      score += markingScheme.unattemptedMarks;
    } else if (userAnswer === question.correctAnswer) {
      correct++;
      score += markingScheme.correctMarks;
    } else {
      incorrect++;
      score += markingScheme.incorrectMarks;
    }
  });

  return {
    score,
    correct,
    incorrect,
    unattempted,
    total: questions.length,
    accuracy:
      correct > 0 ? Math.round((correct / (correct + incorrect)) * 100) : 0,
    attemptRate: Math.round(((correct + incorrect) / questions.length) * 100),
  };
}

export function calculateSectionWiseStats(answers, sections, markingScheme) {
  return sections.map((section) => {
    const sectionQuestions = section.questions || [];
    return {
      sectionId: section.id,
      sectionName: section.name,
      ...calculateScore(answers, sectionQuestions, markingScheme),
    };
  });
}

export default { calculateScore, calculateSectionWiseStats };
