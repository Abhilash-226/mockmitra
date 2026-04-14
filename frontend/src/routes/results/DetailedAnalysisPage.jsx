// Detailed Analysis Page
import { useState, useEffect } from "react";
import { useParams, Link, useLocation } from "react-router-dom";
import "katex/dist/katex.min.css";
import LatexText from "../../components/ui/LatexText";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";
import { pyqService } from "../../services/pyqService";

const API_ORIGIN = (import.meta.env.VITE_API_URL || "/api").replace(
  /\/api\/?$/,
  "",
);

const formatTime = (seconds) => {
  if (!seconds) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};
const parseOptionValue = (val) => {
  if (typeof val !== "string") return val;
  if (val.startsWith("{'") && val.endsWith("'}") && val.includes("'image':")) {
    try {
      // Basic Python dict -> JSON conversion for image paths
      return JSON.parse(val.replace(/'/g, '"'));
    } catch (_error) {
      return val;
    }
  }
  return val;
};

const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

const toPositiveInt = (value) => {
  const n = Number(value);
  return Number.isInteger(n) && n > 0 ? n : null;
};

const parsePyqPaperIdFromTestName = (testName) => {
  if (!testName || typeof testName !== "string") return null;

  // Expected shape: PYQ TS EAMCET 2020 Shift-1
  const m = testName
    .trim()
    .match(/^PYQ\s+([A-Za-z\s]+?)\s+(\d{4})\s+Shift-(\d+)$/i);
  if (!m) return null;

  const exam = m[1].trim().toLowerCase().replace(/\s+/g, "_");
  const year = m[2];
  const shift = m[3];
  return `${exam}_${year}_${shift}`;
};

// Individual Question Card matching the reference UI
function QuestionReviewCard({ question }) {
  const [showSolution, setShowSolution] = useState(false);
  const [solution, setSolution] = useState(null); // null = not fetched yet
  const [solutionLoading, setSolutionLoading] = useState(false);
  const [solutionError, setSolutionError] = useState(null);

  const handleViewSolution = async (forceGenerateOrEvent) => {
    const forceGenerate = forceGenerateOrEvent === true;
    if (showSolution && !forceGenerate) {
      setShowSolution(false);
      return;
    }
    setShowSolution(true);

    // Already fetched — just show
    if (solution !== null) return;

    setSolutionLoading(true);
    setSolutionError(null);
    try {
      if (isPyqQuestion) {
        const result = await pyqService.getSolution(
          question.paperId,
          question.questionNumber,
        );
        setSolution(result.solution);
      } else {
        const result = await analyticsService.generateSolution({
          questionId: question.id,
          questionText: question.text,
          options: question.options,
          correctAnswer: question.correctAnswer,
          topic: question.topic,
          section: question.section,
        });
        setSolution(result.solution);
      }
    } catch (err) {
      console.error("Solution generation failed:", err);
      const backendDetail = err?.response?.data?.detail;
      setSolutionError(backendDetail || "Solution not available yet.");
      // Fallback to stored explanation
      if (
        !isPyqQuestion &&
        question.solution &&
        question.solution !== "No explanation available"
      ) {
        setSolution(question.solution);
        setSolutionError(null);
      }
    } finally {
      setSolutionLoading(false);
    }
  };

  const getOptionStyle = (opt) => {
    const isCorrect = opt.value === question.correctAnswer;
    const isSelected = opt.value === question.userAnswer;
    const isWrong = isSelected && !isCorrect;

    if (isCorrect)
      return {
        wrapper: "border border-green-200 bg-green-50",
        label: "bg-green-500 text-white",
        icon: (
          <svg
            className="w-5 h-5 text-green-500 flex-shrink-0"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        ),
      };
    if (isWrong)
      return {
        wrapper: "border border-red-200 bg-red-50",
        label: "bg-red-400 text-white",
        icon: (
          <svg
            className="w-5 h-5 text-red-400 flex-shrink-0"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        ),
      };
    return {
      wrapper: "border border-gray-200 bg-white",
      label: "bg-gray-100 text-gray-600",
      icon: null,
    };
  };

  const borderColor = question.isCorrect
    ? "border-l-green-500"
    : question.userAnswer
      ? "border-l-red-500"
      : "border-l-gray-400";

  const skipped = !question.userAnswer;
  const isPyqQuestion =
    Boolean(question.paperId) && Number.isInteger(question.questionNumber);

  return (
    <div
      className={`bg-white rounded-xl border border-gray-200 border-l-4 ${borderColor} shadow-sm overflow-hidden`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-800">
            Question {question.number}
          </span>
          {question.isCorrect ? (
            <svg
              className="w-5 h-5 text-green-500"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
          ) : skipped ? (
            <svg
              className="w-5 h-5 text-gray-400"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM7 9a1 1 0 000 2h6a1 1 0 100-2H7z"
                clipRule="evenodd"
              />
            </svg>
          ) : (
            <svg
              className="w-5 h-5 text-red-500"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 border border-gray-300 rounded-full px-3 py-0.5">
            Multiple Choice
          </span>
          {/* Difficulty badge */}
          <span
            className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
              question.difficulty === "Easy"
                ? "bg-green-100 text-green-700"
                : question.difficulty === "Medium"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-red-100 text-red-700"
            }`}
          >
            {question.difficulty}
          </span>
        </div>
      </div>

      <div className="px-6 py-5">
        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-md">
            {question.section}
          </span>
          <span className="text-xs bg-blue-50 text-blue-600 px-2.5 py-1 rounded-md">
            {question.topic}
          </span>
        </div>

        {/* Question Text */}
        <p className="text-gray-800 leading-relaxed mb-5 text-[15px]">
          <LatexText>{question.text}</LatexText>
        </p>

        {/* Question Image */}
        {question.image && (
          <div className="mb-5 flex justify-center">
            <img
              src={
                question.image.startsWith("http")
                  ? question.image
                  : `${API_ORIGIN}${question.image}`
              }
              alt="Question diagram"
              className="max-w-full h-auto max-h-64 object-contain rounded-lg border border-gray-200"
            />
          </div>
        )}

        {/* Options */}
        <div className="space-y-2 mb-5">
          {question.options.map((opt, idx) => {
            const style = getOptionStyle(opt);
            return (
              <div
                key={opt.value ?? idx}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg ${style.wrapper}`}
              >
                <span
                  className={`w-8 h-8 rounded-md flex items-center justify-center text-sm font-bold flex-shrink-0 ${style.label}`}
                >
                  {OPTION_LABELS[idx]}
                </span>
                <span className="flex-1 text-gray-800 text-[15px]">
                  {typeof opt.text === "object" && opt.text?.image ? (
                    <div className="py-1">
                      <img
                        src={
                          opt.text.image.startsWith("http")
                            ? opt.text.image
                            : `${API_ORIGIN}${opt.text.image}`
                        }
                        alt={`Option (${OPTION_LABELS[idx]})`}
                        className="max-h-32 object-contain rounded"
                      />
                    </div>
                  ) : (
                    <LatexText>{opt.text}</LatexText>
                  )}
                </span>
                {style.icon}
              </div>
            );
          })}
        </div>

        {/* Answer Summary Row */}
        <div className="bg-gray-50 rounded-lg px-4 py-3 mb-4 text-sm space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-gray-500 w-36">Your Answer:</span>
            {question.userAnswer ? (
              <span
                className={`font-semibold ${question.isCorrect ? "text-green-600" : "text-red-500"}`}
              >
                {OPTION_LABELS[
                  question.options.findIndex(
                    (o) => o.value === question.userAnswer,
                  )
                ] ?? question.userAnswer.toUpperCase()}
              </span>
            ) : (
              <span className="text-gray-400 italic">Not Answered</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500 w-36">Correct Answer:</span>
            <span className="font-semibold text-green-600">
              {OPTION_LABELS[
                question.options.findIndex(
                  (o) => o.value === question.correctAnswer,
                )
              ] ?? question.correctAnswer?.toUpperCase()}
            </span>
          </div>
        </div>

        {/* View Solution Toggle */}
        <button
          onClick={handleViewSolution}
          disabled={solutionLoading}
          className="inline-flex items-center gap-2 text-sm font-medium text-blue-600 border border-blue-300 rounded-lg px-4 py-2 hover:bg-blue-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {solutionLoading ? (
            <>
              <svg
                className="w-4 h-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              {isPyqQuestion
                ? "Fetching Solution..."
                : "Generating Solution..."}
            </>
          ) : (
            <>
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              {showSolution ? "Hide Solution" : "View Solution"}
            </>
          )}
        </button>

        {/* Solution Panel */}
        {showSolution && (
          <div className="mt-3 rounded-xl border border-blue-100 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-blue-600">
              <svg
                className="w-4 h-4 text-white"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              <span className="text-sm font-semibold text-white">
                {isPyqQuestion
                  ? "Stored PYQ Solution"
                  : "AI-Generated Solution"}
              </span>
              <span className="ml-auto text-xs text-blue-200">
                {isPyqQuestion ? "from solution database" : "powered by Gemini"}
              </span>
            </div>
            <div className="bg-blue-50 px-5 py-4">
              {solutionLoading ? (
                <div className="space-y-2 animate-pulse">
                  <div className="h-3 bg-blue-200 rounded w-full" />
                  <div className="h-3 bg-blue-200 rounded w-5/6" />
                  <div className="h-3 bg-blue-200 rounded w-4/6" />
                  <div className="h-3 bg-blue-200 rounded w-full" />
                  <div className="h-3 bg-blue-200 rounded w-3/4" />
                </div>
              ) : solutionError && !solution ? (
                <div className="flex items-start gap-3 text-red-700">
                  <svg
                    className="w-5 h-5 flex-shrink-0 mt-0.5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div>
                    <p className="text-sm font-medium">{solutionError}</p>
                    <button
                      onClick={() => {
                        setSolution(null);
                        setSolutionError(null);
                        handleViewSolution(true);
                      }}
                      className="mt-1 text-xs underline hover:no-underline"
                    >
                      Retry
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-blue-900 leading-relaxed whitespace-pre-line">
                  <LatexText>{solution}</LatexText>
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
const SECTION_COLORS = {
  Mathematics: {
    bg: "bg-blue-50",
    border: "border-blue-400",
    text: "text-blue-700",
    ring: "text-blue-500",
    light: "bg-blue-100",
  },
  Physics: {
    bg: "bg-amber-50",
    border: "border-amber-400",
    text: "text-amber-700",
    ring: "text-amber-500",
    light: "bg-amber-100",
  },
  Chemistry: {
    bg: "bg-emerald-50",
    border: "border-emerald-400",
    text: "text-emerald-700",
    ring: "text-emerald-500",
    light: "bg-emerald-100",
  },
};
const DEFAULT_SECTION_COLOR = {
  bg: "bg-gray-50",
  border: "border-gray-400",
  text: "text-gray-700",
  ring: "text-gray-500",
  light: "bg-gray-100",
};

const DEFAULT_SUMMARY = {
  testName: "Test",
  score: 0,
  maxScore: 0,
  percentage: 0,
  accuracy: 0,
  rank: "-",
  timeTaken: "0:00",
  correct: 0,
  incorrect: 0,
  skipped: 0,
  total: 0,
};

const DEFAULT_ANALYSIS = {
  questions: [],
  sectionAnalysis: [],
  timeAnalysis: {
    avgTimePerQuestion: 0,
    fastestQuestion: 0,
    slowestQuestion: 0,
    recommendedTime: 36,
  },
};

export default function DetailedAnalysisPage() {
  const { attemptId } = useParams();
  const location = useLocation();
  const [summary, setSummary] = useState(DEFAULT_SUMMARY);
  const [analysis, setAnalysis] = useState(DEFAULT_ANALYSIS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        const loadAttemptAnalytics = async () => {
          let latestData = null;

          for (let attempt = 0; attempt < 3; attempt += 1) {
            const response =
              await analyticsService.getAttemptAnalytics(attemptId);
            const data = response.data || response;
            latestData = data;

            const correct = data.correct || data.correct_answers || 0;
            const wrong = data.wrong || data.wrong_answers || 0;
            const skippedCount = data.skipped || 0;
            const totalQ =
              data.total_questions || correct + wrong + skippedCount || 0;
            const hasQuestions =
              Array.isArray(data.questions) && data.questions.length > 0;

            if (hasQuestions || totalQ === 0 || attempt === 2) {
              return data;
            }

            await new Promise((resolve) =>
              setTimeout(resolve, 300 * (attempt + 1)),
            );
          }

          return latestData;
        };

        const data = await loadAttemptAnalytics();

        // Build results summary from same data
        const correct = data.correct || data.correct_answers || 0;
        const wrong = data.wrong || data.wrong_answers || 0;
        const skippedCount = data.skipped || 0;
        const totalQ =
          data.total_questions || correct + wrong + skippedCount || 0;
        const attempted = correct + wrong;
        const accuracyPct =
          attempted > 0 ? Math.round((correct / attempted) * 1000) / 10 : 0;

        setSummary({
          testName: data.test_name || data.exam_name || "Test",
          score: data.score || 0,
          maxScore: data.max_score || totalQ,
          percentage:
            data.percentage ||
            (totalQ > 0 ? Math.round((correct / totalQ) * 100) : 0),
          accuracy: accuracyPct,
          rank: data.rank || "-",
          timeTaken: formatTime(data.time_taken_seconds),
          correct,
          incorrect: wrong,
          skipped: skippedCount,
          total: totalQ,
        });

        const inferredPaperId =
          data.paper_id ||
          location?.state?.paperId ||
          location?.state?.paper_id ||
          parsePyqPaperIdFromTestName(data.test_name || "");

        // Transform questions
        const questions = (data.questions || []).map((q, index) => {
          const options = (q.options || []).map((opt) => {
            if (typeof opt === "string")
              return { value: opt, text: parseOptionValue(opt) };
            return {
              value: opt.key ?? opt.value,
              text: parseOptionValue(opt.text ?? opt.label ?? opt),
            };
          });
          return {
            id: q.id || q.question_id || `q-${index}`,
            number: index + 1,
            text: q.question_text || q.text || "Question text not available",
            options,
            correctAnswer: q.correct_answer || q.correctAnswer,
            userAnswer: q.selected_option || q.user_answer || null,
            topic: q.topic || "General",
            section: q.section || "General",
            difficulty: q.difficulty
              ? q.difficulty.charAt(0).toUpperCase() +
                q.difficulty.slice(1).toLowerCase()
              : "Medium",
            solution: q.solution || q.explanation || "No explanation available",
            isCorrect: q.is_correct,
            image: q.image || null,
            paperId: q.paper_id || inferredPaperId || null,
            questionNumber:
              toPositiveInt(q.question_number) ||
              toPositiveInt(q.number) ||
              (inferredPaperId ? index + 1 : null),
          };
        });

        // Section analysis (group by section / subject)
        const sectionStats = {};
        questions.forEach((q) => {
          const sec = q.section || "General";
          if (!sectionStats[sec])
            sectionStats[sec] = { correct: 0, wrong: 0, skipped: 0, total: 0 };
          sectionStats[sec].total++;
          if (q.isCorrect === true) sectionStats[sec].correct++;
          else if (q.userAnswer) sectionStats[sec].wrong++;
          else sectionStats[sec].skipped++;
        });
        const sectionAnalysis = Object.entries(sectionStats).map(
          ([section, s]) => ({
            section,
            correct: s.correct,
            wrong: s.wrong,
            skipped: s.skipped,
            total: s.total,
            percentage:
              s.total > 0 ? Math.round((s.correct / s.total) * 100) : 0,
          }),
        );

        // Time analysis
        const times = (data.responses || [])
          .map((r) => r.time_spent || r.time_spent_seconds || 0)
          .filter((t) => t > 0);
        const timeAnalysis = {
          avgTimePerQuestion:
            data.average_time_per_question ||
            (times.length > 0
              ? Math.round(times.reduce((a, b) => a + b, 0) / times.length)
              : 0),
          fastestQuestion: times.length > 0 ? Math.min(...times) : 0,
          slowestQuestion: times.length > 0 ? Math.max(...times) : 0,
          recommendedTime: 36,
        };

        setAnalysis({
          questions:
            questions.length > 0 ? questions : DEFAULT_ANALYSIS.questions,
          sectionAnalysis:
            sectionAnalysis.length > 0
              ? sectionAnalysis
              : DEFAULT_ANALYSIS.sectionAnalysis,
          timeAnalysis,
        });
        setError(null);
      } catch (err) {
        console.error("Failed to fetch analysis:", err);
        setError("Failed to load analysis data");
        setAnalysis(DEFAULT_ANALYSIS);
      } finally {
        setLoading(false);
      }
    };

    if (attemptId) fetchAnalysis();
  }, [attemptId, location]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 bg-red-50 rounded-xl">
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── Results Overview ── */}
      {(() => {
        const scoreCirc = 2 * Math.PI * 54;
        const scoreOffset = scoreCirc - (summary.percentage / 100) * scoreCirc;
        const pctColor =
          summary.percentage >= 60
            ? "text-green-500"
            : summary.percentage >= 30
              ? "text-amber-500"
              : "text-red-500";
        const strokeColor =
          summary.percentage >= 60
            ? "stroke-green-500"
            : summary.percentage >= 30
              ? "stroke-amber-500"
              : "stroke-red-500";
        return (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-8">
            {/* Test name + actions row */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-800 truncate">
                {summary.testName}
              </h2>
              <div className="flex items-center gap-3 text-sm text-gray-500">
                <span className="flex items-center gap-1.5">
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v6l4 2" />
                  </svg>
                  {summary.timeTaken}
                </span>
                <Link
                  to="/dashboard/exams"
                  className="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 font-medium hover:bg-blue-100 transition-colors text-xs"
                >
                  Take Another Test
                </Link>
              </div>
            </div>

            {/* Main content: donut + stats */}
            <div className="flex flex-col md:flex-row items-center gap-8">
              {/* Donut Chart */}
              <div className="relative w-36 h-36 flex-shrink-0">
                <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
                  <circle
                    cx="60"
                    cy="60"
                    r="54"
                    fill="none"
                    className="stroke-gray-100"
                    strokeWidth="8"
                  />
                  <circle
                    cx="60"
                    cy="60"
                    r="54"
                    fill="none"
                    className={`${strokeColor} transition-all duration-1000 ease-out`}
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={scoreCirc}
                    strokeDashoffset={scoreOffset}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={`text-3xl font-extrabold ${pctColor}`}>
                    {summary.percentage}%
                  </span>
                  <span className="text-xs text-gray-400 mt-0.5">Score</span>
                </div>
              </div>

              {/* Score details + stat grid */}
              <div className="flex-1 w-full">
                {/* Score line */}
                <div className="flex items-baseline gap-1.5 mb-1">
                  <span className="text-4xl font-extrabold text-gray-900">
                    {summary.score}
                  </span>
                  <span className="text-lg text-gray-400 font-medium">
                    / {summary.maxScore}
                  </span>
                </div>
                <p className="text-sm text-gray-500 mb-5">
                  {summary.accuracy}% Accuracy
                  {summary.rank !== "-" && <span> • Rank #{summary.rank}</span>}
                </p>

                {/* Stat pills grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="flex items-center gap-3 rounded-xl bg-green-50 border border-green-100 px-4 py-3">
                    <div className="w-1 h-8 rounded-full bg-green-500" />
                    <div>
                      <p className="text-xl font-bold text-green-600">
                        {summary.correct}
                      </p>
                      <p className="text-xs text-green-700">Correct</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-red-50 border border-red-100 px-4 py-3">
                    <div className="w-1 h-8 rounded-full bg-red-500" />
                    <div>
                      <p className="text-xl font-bold text-red-600">
                        {summary.incorrect}
                      </p>
                      <p className="text-xs text-red-700">Incorrect</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-gray-50 border border-gray-200 px-4 py-3">
                    <div className="w-1 h-8 rounded-full bg-gray-400" />
                    <div>
                      <p className="text-xl font-bold text-gray-600">
                        {summary.skipped}
                      </p>
                      <p className="text-xs text-gray-500">Skipped</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 rounded-xl bg-blue-50 border border-blue-100 px-4 py-3">
                    <div className="w-1 h-8 rounded-full bg-blue-500" />
                    <div>
                      <p className="text-xl font-bold text-blue-600">
                        {summary.total}
                      </p>
                      <p className="text-xs text-blue-700">Total</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ── Section-wise Analysis ── */}
      <Card>
        <CardHeader>
          <CardTitle>Section-wise Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {analysis.sectionAnalysis.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-3">
              {analysis.sectionAnalysis.map((sec) => {
                const c = SECTION_COLORS[sec.section] || DEFAULT_SECTION_COLOR;
                const circumference = 2 * Math.PI * 28;
                const offset =
                  circumference - (sec.percentage / 100) * circumference;
                return (
                  <div
                    key={sec.section}
                    className={`rounded-xl border-l-4 ${c.border} ${c.bg} p-5 flex flex-col items-center gap-3 shadow-sm`}
                  >
                    {/* Section name */}
                    <h3 className={`text-base font-bold ${c.text}`}>
                      {sec.section}
                    </h3>

                    {/* Donut ring */}
                    <div className="relative w-20 h-20">
                      <svg
                        viewBox="0 0 64 64"
                        className="w-full h-full -rotate-90"
                      >
                        <circle
                          cx="32"
                          cy="32"
                          r="28"
                          fill="none"
                          className="stroke-gray-200"
                          strokeWidth="5"
                        />
                        <circle
                          cx="32"
                          cy="32"
                          r="28"
                          fill="none"
                          className={`${c.ring} transition-all duration-700`}
                          stroke="currentColor"
                          strokeWidth="5"
                          strokeLinecap="round"
                          strokeDasharray={circumference}
                          strokeDashoffset={offset}
                        />
                      </svg>
                      <span
                        className={`absolute inset-0 flex items-center justify-center text-lg font-bold ${c.text}`}
                      >
                        {sec.percentage}%
                      </span>
                    </div>

                    {/* Stat pills */}
                    <div className="flex gap-2 text-xs font-medium">
                      <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                        ✓ {sec.correct}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                        ✗ {sec.wrong}
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-gray-200 text-gray-600">
                        — {sec.skipped}
                      </span>
                    </div>

                    <p className="text-xs text-gray-500">
                      {sec.correct} / {sec.total} correct
                    </p>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No section analysis available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Time Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Time Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">
                {analysis.timeAnalysis.avgTimePerQuestion}s
              </p>
              <p className="text-sm text-blue-700">Avg per Question</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">
                {analysis.timeAnalysis.fastestQuestion}s
              </p>
              <p className="text-sm text-green-700">Fastest Answer</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">
                {analysis.timeAnalysis.slowestQuestion}s
              </p>
              <p className="text-sm text-red-700">Slowest Answer</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <p className="text-2xl font-bold text-purple-600">
                {analysis.timeAnalysis.recommendedTime}s
              </p>
              <p className="text-sm text-purple-700">Recommended Time</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Question Review */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <svg
            className="w-5 h-5 text-gray-700"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
          <h2 className="text-lg font-bold text-gray-800">Question Review</h2>
        </div>

        {analysis.questions.length > 0 ? (
          <div className="space-y-4">
            {analysis.questions.map((question, index) => (
              <QuestionReviewCard
                key={`${question.id ?? "question"}-${index}`}
                question={question}
              />
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-gray-500">
            No question review data available
          </div>
        )}
      </div>
    </div>
  );
}
