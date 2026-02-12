// Timer Display Component with Tailwind CSS
// UI only - reads from CBT engine. Logic lives in modules/cbt-engine/TimerController.js
import { useMemo } from "react";

const TIMER_WARNING_THRESHOLD = 300; // 5 minutes
const TIMER_CRITICAL_THRESHOLD = 60; // 1 minute

export default function TimerDisplay({ remainingTime, totalTime }) {
  // Determine timer status
  const status = useMemo(() => {
    if (remainingTime <= TIMER_CRITICAL_THRESHOLD) return "critical";
    if (remainingTime <= TIMER_WARNING_THRESHOLD) return "warning";
    return "normal";
  }, [remainingTime]);

  // Format time as HH:MM:SS
  const formatTime = (seconds) => {
    if (seconds < 0) seconds = 0;
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const statusClasses = {
    normal: "timer-normal",
    warning: "timer-warning",
    critical: "timer-critical",
  };

  return (
    <div className="flex items-center gap-3">
      {/* Clock icon */}
      <svg
        className="w-5 h-5 text-gray-500"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>

      {/* Timer display */}
      <div className={statusClasses[status]}>{formatTime(remainingTime)}</div>

      {/* Status indicator */}
      {status === "critical" && (
        <span className="text-xs text-red-600 font-medium animate-pulse">
          Time running out!
        </span>
      )}
    </div>
  );
}
