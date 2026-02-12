/**
 * Exam Types
 */

export const ExamStatus = {
  NOT_STARTED: "NOT_STARTED",
  IN_PROGRESS: "IN_PROGRESS",
  PAUSED: "PAUSED",
  SUBMITTED: "SUBMITTED",
};

export const QuestionStatus = {
  NOT_VISITED: "NOT_VISITED",
  VISITED: "VISITED",
  ANSWERED: "ANSWERED",
  MARKED: "MARKED",
  ANSWERED_AND_MARKED: "ANSWERED_AND_MARKED",
};

export const TestMode = {
  FULL_MOCK: "full",
  SECTIONAL: "sectional",
  TOPIC_WISE: "topic",
  PYQ: "pyq",
};

export const Difficulty = {
  EASY: "easy",
  MEDIUM: "medium",
  HARD: "hard",
  MIXED: "mixed",
};
