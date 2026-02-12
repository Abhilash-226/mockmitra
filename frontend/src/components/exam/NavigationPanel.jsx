// Navigation Panel Component with Tailwind CSS
import { Button } from "../ui";

export default function NavigationPanel({
  currentQuestion,
  totalQuestions,
  onPrevious,
  onNext,
  onClearResponse,
  onSaveAndNext,
  canGoPrevious = true,
  canGoNext = true,
}) {
  return (
    <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-white">
      {/* Left side - Clear response */}
      <Button
        variant="ghost"
        onClick={onClearResponse}
        className="text-gray-600"
      >
        Clear Response
      </Button>

      {/* Center - Question indicator */}
      <span className="text-sm text-gray-500">
        {currentQuestion + 1} of {totalQuestions}
      </span>

      {/* Right side - Navigation buttons */}
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          onClick={onPrevious}
          disabled={!canGoPrevious}
          className="flex items-center gap-1"
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
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Previous
        </Button>

        {canGoNext ? (
          <Button
            variant="primary"
            onClick={onSaveAndNext || onNext}
            className="flex items-center gap-1"
          >
            Save & Next
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
                d="M9 5l7 7-7 7"
              />
            </svg>
          </Button>
        ) : (
          <Button
            variant="success"
            onClick={onSaveAndNext}
            className="flex items-center gap-1"
          >
            Save
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
                d="M5 13l4 4L19 7"
              />
            </svg>
          </Button>
        )}
      </div>
    </div>
  );
}
