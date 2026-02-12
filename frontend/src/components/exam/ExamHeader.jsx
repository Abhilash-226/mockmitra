// Exam Header Component with Tailwind CSS
import { Button } from "../ui";
import TimerDisplay from "./TimerDisplay";

export default function ExamHeader({
  examName,
  remainingTime,
  totalTime,
  onSubmit,
  userName,
}) {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Left - Exam info */}
          <div className="flex items-center gap-4">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">M</span>
              </div>
              <span className="font-semibold text-gray-800 hidden sm:inline">
                MockMitra
              </span>
            </div>

            {/* Divider */}
            <div className="h-6 w-px bg-gray-300 hidden sm:block" />

            {/* Exam name */}
            <h1 className="text-lg font-semibold text-gray-900">{examName}</h1>
          </div>

          {/* Center - Timer */}
          <TimerDisplay remainingTime={remainingTime} totalTime={totalTime} />

          {/* Right - User & Submit */}
          <div className="flex items-center gap-4">
            {/* User name */}
            {userName && (
              <div className="hidden md:flex items-center gap-2">
                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                  <span className="text-gray-600 font-medium text-sm">
                    {userName.charAt(0).toUpperCase()}
                  </span>
                </div>
                <span className="text-sm text-gray-600">{userName}</span>
              </div>
            )}

            {/* Submit button */}
            <Button
              variant="success"
              onClick={onSubmit}
              className="flex items-center gap-2"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="hidden sm:inline">Submit</span>
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
