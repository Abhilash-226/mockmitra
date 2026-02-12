// Question Card Component with Tailwind CSS
import OptionsList from "./OptionsList";

export default function QuestionCard({
  question,
  questionNumber,
  totalQuestions,
  selectedAnswer,
  onAnswerSelect,
  onMarkForReview,
  isMarked = false,
  showSolution = false,
}) {
  if (!question) return null;

  return (
    <div className="flex flex-col h-full">
      {/* Question header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          <span className="bg-primary-100 text-primary-700 px-3 py-1 rounded-full text-sm font-medium">
            Question {questionNumber} of {totalQuestions}
          </span>
          {question.topic && (
            <span className="text-sm text-gray-500">{question.topic}</span>
          )}
        </div>

        {/* Mark for review button */}
        <button
          onClick={onMarkForReview}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
            isMarked
              ? "bg-purple-100 text-purple-700 border border-purple-300"
              : "bg-white text-gray-600 border border-gray-300 hover:bg-gray-50"
          }`}
        >
          <svg
            className="w-4 h-4"
            fill={isMarked ? "currentColor" : "none"}
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
            />
          </svg>
          {isMarked ? "Marked" : "Mark for Review"}
        </button>
      </div>

      {/* Question body */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Question stem */}
        <div className="mb-6">
          <p className="text-lg text-gray-800 leading-relaxed">
            {question.stem || question.text}
          </p>

          {/* Question image if exists */}
          {question.image && (
            <div className="mt-4">
              <img
                src={question.image}
                alt="Question diagram"
                className="max-w-full rounded-lg border border-gray-200"
              />
            </div>
          )}
        </div>

        {/* Options */}
        <OptionsList
          options={question.options}
          selectedOption={selectedAnswer}
          correctOption={showSolution ? question.correctAnswer : null}
          onSelect={onAnswerSelect}
          disabled={showSolution}
        />

        {/* Solution (if showing) */}
        {showSolution && question.explanation && (
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="font-semibold text-blue-800 mb-2">Explanation:</h4>
            <p className="text-blue-700">{question.explanation}</p>
          </div>
        )}
      </div>
    </div>
  );
}
