// Exam Guard Component - Extra protection for exam pages
import { useEffect, useCallback } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { useExamStore } from "../../store/useExamStore";
import { useAuthStore } from "../../store/useAuthStore";
import { PageLoader } from "../ui/Spinner";

export default function ExamGuard({ children }) {
  const navigate = useNavigate();
  const { examId: urlExamId } = useParams();
  const location = useLocation();
  const { isAuthenticated } = useAuthStore();
  const { currentExam, examState, examConfig } = useExamStore();

  // Check if we have exam data from store, URL, or router state
  const isInstructionsPage = location.pathname.includes("/instructions");
  const hasExamData = currentExam || examConfig;
  const hasRouterState = location.state?.testId || location.state?.config;
  const hasValidExamState =
    examState === "ready" || examState === "in_progress";

  // Handle beforeunload event
  const handleBeforeUnload = useCallback(
    (e) => {
      if (examState === "in_progress") {
        e.preventDefault();
        e.returnValue =
          "You have an ongoing test. Are you sure you want to leave?";
        return e.returnValue;
      }
    },
    [examState],
  );

  // Handle visibility change (tab switch detection)
  const handleVisibilityChange = useCallback(() => {
    if (document.hidden && examState === "in_progress") {
      // Log tab switch - can be used for proctoring
      console.warn("Tab switch detected during exam");
    }
  }, [examState]);

  // Prevent right-click context menu during exam
  const handleContextMenu = useCallback(
    (e) => {
      if (examState === "in_progress") {
        e.preventDefault();
        return false;
      }
    },
    [examState],
  );

  // Disable keyboard shortcuts during exam
  const handleKeyDown = useCallback(
    (e) => {
      if (examState === "in_progress") {
        // Disable common shortcuts
        if (
          (e.ctrlKey &&
            (e.key === "c" ||
              e.key === "v" ||
              e.key === "p" ||
              e.key === "u")) ||
          e.key === "F12" ||
          (e.ctrlKey && e.shiftKey && e.key === "I")
        ) {
          e.preventDefault();
          return false;
        }
      }
    },
    [examState],
  );

  useEffect(() => {
    // Add event listeners
    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    document.addEventListener("contextmenu", handleContextMenu);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      // Cleanup event listeners
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      document.removeEventListener("contextmenu", handleContextMenu);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    handleBeforeUnload,
    handleVisibilityChange,
    handleContextMenu,
    handleKeyDown,
  ]);

  // Handle navigation in useEffect to avoid calling during render
  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/login", { replace: true });
    } else if (
      !hasExamData &&
      !hasRouterState &&
      !isInstructionsPage &&
      examState !== "loading"
    ) {
      // Only redirect to dashboard if no exam data AND no router state AND not on instructions page
      navigate("/dashboard", { replace: true });
    }
  }, [
    isAuthenticated,
    hasExamData,
    hasRouterState,
    isInstructionsPage,
    examState,
    navigate,
  ]);

  // Check authentication
  if (!isAuthenticated) {
    return null;
  }

  // For instructions page, allow access if we have URL examId or router state
  if (isInstructionsPage && (urlExamId || hasRouterState)) {
    return (
      <div className="exam-guard min-h-screen bg-gray-100">{children}</div>
    );
  }

  // Check if exam is loaded
  if (!hasExamData && !hasRouterState && examState !== "loading") {
    return null;
  }

  // Show loading state
  if (examState === "loading") {
    return <PageLoader text="Loading exam..." />;
  }

  return (
    <div className="exam-guard min-h-screen bg-gray-100">
      {/* Fullscreen prompt for exam mode */}
      {examState === "in_progress" && (
        <div className="fixed top-0 left-0 right-0 bg-blue-600 text-white text-xs text-center py-1 z-[100]">
          <span className="animate-pulse">● </span>
          Exam in progress - Do not close or refresh this tab
        </div>
      )}
      {children}
    </div>
  );
}
