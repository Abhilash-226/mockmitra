/**
 * Exam Store - Core exam state
 *
 * CRITICAL RULE: UI components CANNOT mutate this state directly
 * Only CBT engine actions can change exam state
 *
 * State is immutable - updates only via actions
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

const useExamStore = create(
  persist(
    (set, get) => ({
      // Exam metadata
      examId: null,
      examConfig: null,
      currentExam: null, // Alias for current test data
      attemptId: null,
      examState: "idle", // idle | loading | ready | in_progress | submitted

      // Progress tracking
      currentSectionIndex: 0,
      currentQuestionIndex: 0,

      // Answer state
      answers: {}, // { [questionId]: selectedOption }
      markedForReview: [], // array of questionIds
      visitedQuestions: [], // array of questionIds

      // Timer (managed by TimerController, read-only for UI)
      startTimestamp: null,
      totalDuration: null,
      remainingTime: null,

      // Exam lifecycle
      status: "NOT_STARTED", // NOT_STARTED | IN_PROGRESS | PAUSED | SUBMITTED

      // Actions - ONLY way to mutate state
      actions: {
        setCurrentExam: (examData) =>
          set({
            currentExam: examData,
            examConfig: examData,
            examId: examData?.id || examData?._id || null,
            examState: "ready",
          }),

        setExamState: (state) => set({ examState: state }),

        initExam: (config) =>
          set({
            examId: config.examId,
            examConfig: config,
            attemptId: config.attemptId || `attempt_${Date.now()}`,
            currentSectionIndex: 0,
            currentQuestionIndex: 0,
            answers: {},
            markedForReview: [],
            visitedQuestions: [0],
            startTimestamp: Date.now(),
            totalDuration: config.totalDuration,
            remainingTime: config.totalDuration,
            status: "IN_PROGRESS",
            examState: "in_progress",
          }),

        selectAnswer: (questionId, option) =>
          set((state) => ({
            answers: { ...state.answers, [questionId]: option },
          })),

        clearAnswer: (questionId) =>
          set((state) => {
            const newAnswers = { ...state.answers };
            delete newAnswers[questionId];
            return { answers: newAnswers };
          }),

        toggleMarkForReview: (questionId) =>
          set((state) => {
            const isMarked = state.markedForReview.includes(questionId);
            return {
              markedForReview: isMarked
                ? state.markedForReview.filter((id) => id !== questionId)
                : [...state.markedForReview, questionId],
            };
          }),

        navigateToQuestion: (sectionIndex, questionIndex) =>
          set((state) => {
            const questionKey = `${sectionIndex}_${questionIndex}`;
            return {
              currentSectionIndex: sectionIndex,
              currentQuestionIndex: questionIndex,
              visitedQuestions: state.visitedQuestions.includes(questionKey)
                ? state.visitedQuestions
                : [...state.visitedQuestions, questionKey],
            };
          }),

        updateTimer: (remainingTime) => set({ remainingTime }),

        submitExam: () => set({ status: "SUBMITTED" }),

        resetExam: () =>
          set({
            examId: null,
            examConfig: null,
            currentExam: null,
            attemptId: null,
            currentSectionIndex: 0,
            currentQuestionIndex: 0,
            answers: {},
            markedForReview: [],
            visitedQuestions: [],
            startTimestamp: null,
            totalDuration: null,
            remainingTime: null,
            status: "NOT_STARTED",
            examState: "idle",
          }),
      },
    }),
    {
      name: "exam-storage",
      partialize: (state) => ({
        examId: state.examId,
        attemptId: state.attemptId,
        answers: state.answers,
        markedForReview: state.markedForReview,
        visitedQuestions: state.visitedQuestions,
        currentSectionIndex: state.currentSectionIndex,
        currentQuestionIndex: state.currentQuestionIndex,
        startTimestamp: state.startTimestamp,
        status: state.status,
        currentExam: state.currentExam,
        examState: state.examState,
      }),
    },
  ),
);

// Named export for components using { useExamStore }
export { useExamStore };
export default useExamStore;
