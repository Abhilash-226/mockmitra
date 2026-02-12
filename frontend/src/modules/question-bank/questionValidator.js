/**
 * Question Validator - Validates question data integrity
 */

export function validateQuestion(question) {
  const errors = [];

  if (!question.id) errors.push("Missing question ID");
  if (!question.stem) errors.push("Missing question stem");
  if (!question.options || question.options.length < 2) {
    errors.push("Insufficient options");
  }
  if (!question.correctAnswer) errors.push("Missing correct answer");

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function validateQuestionSet(questions) {
  const results = questions.map((q, index) => ({
    index,
    questionId: q.id,
    ...validateQuestion(q),
  }));

  return {
    totalQuestions: questions.length,
    validQuestions: results.filter((r) => r.isValid).length,
    invalidQuestions: results.filter((r) => !r.isValid),
  };
}

export default { validateQuestion, validateQuestionSet };
