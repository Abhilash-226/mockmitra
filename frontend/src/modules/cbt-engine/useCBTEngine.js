/**
 * useCBTEngine - Main hook for CBT functionality
 *
 * This hook orchestrates all CBT components and provides
 * a unified interface for exam pages.
 *
 * Usage:
 * const { timer, navigation, answers, actions } = useCBTEngine(examConfig);
 */

import { useCallback, useEffect } from "react";
import { useExamStore } from "../../store";

export default function useCBTEngine(examConfig) {
  const examStore = useExamStore();

  // Initialize exam
  const initializeExam = useCallback((config) => {
    examStore.actions.initExam(config);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cleanup timer, save state, etc.
    };
  }, []);

  return {
    // State (read-only for UI)
    currentSection: examStore.currentSectionIndex,
    currentQuestion: examStore.currentQuestionIndex,
    answers: examStore.answers,
    markedForReview: examStore.markedForReview,
    remainingTime: examStore.remainingTime,
    status: examStore.status,

    // Actions (only way to mutate)
    actions: {
      initializeExam,
      selectAnswer: examStore.actions.selectAnswer,
      toggleMark: examStore.actions.toggleMarkForReview,
      navigateTo: examStore.actions.navigateToQuestion,
      submit: examStore.actions.submitExam,
    },
  };
}
