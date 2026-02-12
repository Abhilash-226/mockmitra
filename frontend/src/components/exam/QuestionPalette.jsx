// Question Palette Component with Tailwind CSS
// Color-coded question status grid
import { useMemo } from "react";

const getQuestionStatus = (index, answers, markedForReview, visited) => {
  const questionId = index;
  const isAnswered = answers && answers[questionId] !== undefined;
  const isMarked = markedForReview && markedForReview.includes(questionId);
  const isVisited = visited && visited.includes(questionId);

  if (isAnswered && isMarked) return "answered-marked";
  if (isMarked) return "marked";
  if (isAnswered) return "answered";
  if (isVisited) return "not-answered";
  return "not-visited";
};

const statusClasses = {
  "not-visited": "q-badge-not-visited",
  "not-answered": "q-badge-not-answered",
  answered: "q-badge-answered",
  marked: "q-badge-marked",
  "answered-marked": "q-badge-answered-marked",
};

export default function QuestionPalette({
  totalQuestions = 0,
  currentQuestion = 0,
  answers = {},
  markedForReview = [],
  visited = [],
  onQuestionClick,
}) {
  // Generate question array
  const questions = useMemo(
    () => Array.from({ length: totalQuestions }, (_, i) => i),
    [totalQuestions],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-gray-200 bg-gray-50">
        <h3 className="font-semibold text-gray-800">Question Navigator</h3>
      </div>

      {/* Question grid */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="grid grid-cols-5 gap-2">
          {questions.map((index) => {
            const status = getQuestionStatus(
              index,
              answers,
              markedForReview,
              visited,
            );
            const isCurrent = index === currentQuestion;

            return (
              <button
                key={index}
                onClick={() => onQuestionClick?.(index)}
                className={`
                  ${statusClasses[status]}
                  ${isCurrent ? "q-badge-current" : ""}
                `}
              >
                {index + 1}
              </button>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <p className="text-xs font-medium text-gray-600 mb-2">Legend:</p>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-gray-100 border border-gray-300" />
            <span className="text-gray-600">Not Visited</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-red-100 border border-red-300" />
            <span className="text-gray-600">Not Answered</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-green-100 border border-green-500" />
            <span className="text-gray-600">Answered</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 rounded bg-purple-100 border border-purple-500" />
            <span className="text-gray-600">Marked</span>
          </div>
        </div>
      </div>
    </div>
  );
}
