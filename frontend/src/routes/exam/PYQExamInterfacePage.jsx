// PYQ Exam Interface Page - For Past Year Question Papers
import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate, useLocation, useBlocker, useBeforeUnload } from "react-router-dom";
import "katex/dist/katex.min.css";
import Latex from "react-latex-next";
import Modal from "../../components/ui/Modal";

// Helper: renders text with LaTeX, preserving \n as line breaks
// Handles both actual newlines and literal \n sequences (from YAML single-quoted strings)
function LatexText({ children }) {
  if (!children) return null;
  // Split on actual newlines OR literal \n (two chars: backslash + n)
  const parts = String(children).split(/\n|\\n/);
  return (
    <>
      {parts.map((part, i) => (
        <span key={i}>
          <Latex>{part}</Latex>
          {i < parts.length - 1 && <br />}
        </span>
      ))}
    </>
  );
}
import Button from "../../components/ui/Button";
import { pyqService } from "../../services/pyqService";

// Question Status Types
const STATUS = {
  NOT_VISITED: "not_visited",
  NOT_ANSWERED: "not_answered",
  ANSWERED: "answered",
  MARKED_FOR_REVIEW: "marked_review",
  ANSWERED_MARKED: "answered_marked",
};

// Status Legend Component
function StatusLegend({ stats }) {
  const legendItems = [
    {
      status: STATUS.NOT_VISITED,
      count: stats.notVisited,
      label: "Not Visited",
      bgClass: "bg-gray-200 border border-gray-400",
      shape: "square",
    },
    {
      status: STATUS.NOT_ANSWERED,
      count: stats.notAnswered,
      label: "Not Answered",
      bgClass: "bg-red-500 text-white",
      shape: "square",
    },
    {
      status: STATUS.ANSWERED,
      count: stats.answered,
      label: "Answered",
      bgClass: "bg-green-500 text-white",
      shape: "square",
    },
    {
      status: STATUS.MARKED_FOR_REVIEW,
      count: stats.markedReview,
      label: "Marked for Review",
      bgClass: "bg-purple-600 text-white",
      shape: "circle",
    },
    {
      status: STATUS.ANSWERED_MARKED,
      count: stats.answeredMarked,
      label: "Answered & Marked for Review",
      bgClass: "bg-purple-600 text-white ring-2 ring-green-400",
      shape: "circle",
      subLabel: "(will be considered for evaluation)",
    },
  ];

  return (
    <div className="space-y-2 p-3 bg-gray-50 border-b">
      {legendItems.map((item) => (
        <div key={item.status} className="flex items-center gap-3">
          <div
            className={`w-10 h-10 flex items-center justify-center font-bold text-sm ${item.bgClass} ${item.shape === "circle" ? "rounded-full" : "rounded"}`}
          >
            {item.count}
          </div>
          <div className="text-sm text-gray-700">
            <span>{item.label}</span>
            {item.subLabel && (
              <div className="text-xs text-gray-500">{item.subLabel}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// Question Palette Grid
function QuestionPaletteGrid({ questions, currentIndex, onQuestionClick }) {
  const getButtonStyle = (status) => {
    switch (status) {
      case STATUS.ANSWERED:
        return "bg-green-500 text-white hover:bg-green-600";
      case STATUS.NOT_ANSWERED:
        return "bg-red-500 text-white hover:bg-red-600";
      case STATUS.MARKED_FOR_REVIEW:
        return "bg-purple-600 text-white rounded-full hover:bg-purple-700";
      case STATUS.ANSWERED_MARKED:
        return "bg-purple-600 text-white rounded-full ring-2 ring-green-400 hover:bg-purple-700";
      default:
        return "bg-gray-200 text-gray-700 border border-gray-400 hover:bg-gray-300";
    }
  };

  return (
    <div className="grid grid-cols-7 gap-1.5 p-3">
      {questions.map((q, idx) => (
        <button
          key={idx}
          onClick={() => onQuestionClick(idx)}
          className={`w-9 h-9 flex items-center justify-center text-xs font-bold transition-all rounded ${getButtonStyle(
            q.status,
          )} ${currentIndex === idx ? "ring-2 ring-blue-500 ring-offset-2" : ""}`}
          title={`Question ${idx + 1}`}
        >
          {String(idx + 1).padStart(2, "0")}
        </button>
      ))}
    </div>
  );
}

// Timer Display
function Timer({ seconds, onTimeUp }) {
  const [time, setTime] = useState(seconds);

  useEffect(() => {
    if (time <= 0) {
      onTimeUp?.();
      return;
    }
    const interval = setInterval(() => setTime((t) => t - 1), 1000);
    return () => clearInterval(interval);
  }, [time, onTimeUp]);

  const hours = Math.floor(time / 3600);
  const minutes = Math.floor((time % 3600) / 60);
  const secs = time % 60;

  const isWarning = time < 300; // Less than 5 minutes
  const isCritical = time < 60; // Less than 1 minute

  return (
    <div
      className={`px-3 py-1 rounded font-mono text-lg font-bold ${
        isCritical
          ? "bg-red-600 text-white animate-pulse"
          : isWarning
            ? "bg-yellow-500 text-black"
            : "bg-blue-600 text-white"
      }`}
    >
      {String(hours).padStart(2, "0")}:{String(minutes).padStart(2, "0")}:
      {String(secs).padStart(2, "0")}
    </div>
  );
}

export default function PYQExamInterfacePage() {
  const { paperId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const paperData = location.state?.paper;

  // Loading and error state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [examInfo, setExamInfo] = useState({
    candidateName: "Student",
    examName: paperData?.exam || "TS EAMCET",
    year: paperData?.year || "",
    shift: paperData?.shift || 1,
    duration: (paperData?.metadata?.duration_minutes || 180) * 60, // in seconds
    sections: paperData?.sections || [],
  });

  // Exam state
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [markedForReview, setMarkedForReview] = useState(new Set());
  const [visitedQuestions, setVisitedQuestions] = useState(new Set([0]));
  const [showPalette, setShowPalette] = useState(true);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [language, setLanguage] = useState("English");
  const [currentSection, setCurrentSection] = useState(0);
  const [isSubmitted, setIsSubmitted] = useState(false);

  // Loading state
  const [loadingMessage, setLoadingMessage] = useState("Loading paper...");

  // Prevent accidental navigation
  useBeforeUnload(
    useCallback((e) => {
      if (!loading && questions.length > 0) {
        e.preventDefault();
        return (e.returnValue = "Are you sure you want to leave the exam? Your progress may not be saved.");
      }
    }, [loading, questions.length])
  );

  // Block internal navigation (back button, etc.)
  useBlocker(({ nextLocation, currentLocation }) => {
    return !loading && questions.length > 0 && !isSubmitted && nextLocation.pathname !== currentLocation.pathname;
  });

  // Store correct answers for result calculation
  const [correctAnswers, setCorrectAnswers] = useState({});

  // Fetch questions from PYQ API
  useEffect(() => {
    const loadQuestions = async () => {
      try {
        setLoading(true);
        setError(null);
        setLoadingMessage("Loading questions...");

        const response = await pyqService.getQuestions(paperId);
        const pyqQuestions = response.questions || [];

        if (pyqQuestions.length === 0) {
          throw new Error("No questions available for this paper");
        }

        setLoadingMessage("Preparing exam interface...");

        // Transform questions to display format
        // PYQ format: { number, section, text, options: {A, B, C, D} }
        const transformedQuestions = pyqQuestions.map((q, index) => ({
          id: q.number || index + 1,
          number: q.number || index + 1,
          text: q.text || "Question text not available",
          options: [
            { id: "A", text: q.options?.A || "Option A" },
            { id: "B", text: q.options?.B || "Option B" },
            { id: "C", text: q.options?.C || "Option C" },
            { id: "D", text: q.options?.D || "Option D" },
          ],
          section: q.section || "general",
          topic: q.topic,
          subject: q.subject,
          image: q.image,
        }));

        setQuestions(transformedQuestions);

        // Store correct answers mapping (index -> correct option letter)
        // Note: The API doesn't expose correct answers in exam mode
        // We'll fetch full paper for results later

        // Update sections from actual questions - Grouping by Subject
        const uniqueSubjects = [...new Set(pyqQuestions.map((q) => q.subject || q.section))];
        
        // Define subject order
        const subjectOrder = ["Mathematics", "Physics", "Chemistry"];
        uniqueSubjects.sort((a, b) => {
          const indexA = subjectOrder.indexOf(a);
          const indexB = subjectOrder.indexOf(b);
          if (indexA !== -1 && indexB !== -1) return indexA - indexB;
          if (indexA !== -1) return -1;
          if (indexB !== -1) return 1;
          return a.localeCompare(b);
        });

        const sections = uniqueSubjects.map((subject) => {
          const sectionQuestions = pyqQuestions.filter(
            (q) => q.subject === subject || q.section === subject,
          );
          const subjectDisplayNames = {
            Mathematics: "Maths",
            Physics: "Phy",
            Chemistry: "Che",
          };
          return {
            id: subject,
            code: subject,
            name: subjectDisplayNames[subject] || subject,
            questionCount: sectionQuestions.length,
          };
        });

        setExamInfo((prev) => ({ ...prev, sections }));
        setLoading(false);
      } catch (err) {
        console.error("Failed to load questions:", err);
        setError(err.message || "Failed to load questions. Please try again.");
        setLoading(false);
      }
    };

    if (paperId) {
      loadQuestions();
    }
  }, [paperId]);

  // Computed values
  const examData = useMemo(
    () => ({
      ...examInfo,
      questions,
    }),
    [examInfo, questions],
  );

  const totalQuestions = examData.questions.length;
  const currentQuestion = examData.questions[currentIndex] || {
    id: 0,
    number: 1,
    text: "Loading...",
    options: [],
    section: "",
  };

  // Get question status
  const getQuestionStatus = useCallback(
    (idx) => {
      const hasAnswer = answers[idx] !== undefined;
      const isMarked = markedForReview.has(idx);
      const isVisited = visitedQuestions.has(idx);

      if (hasAnswer && isMarked) return STATUS.ANSWERED_MARKED;
      if (isMarked) return STATUS.MARKED_FOR_REVIEW;
      if (hasAnswer) return STATUS.ANSWERED;
      if (isVisited) return STATUS.NOT_ANSWERED;
      return STATUS.NOT_VISITED;
    },
    [answers, markedForReview, visitedQuestions],
  );

  // Calculate stats
  const stats = useMemo(() => {
    let notVisited = 0,
      notAnswered = 0,
      answered = 0,
      markedReview = 0,
      answeredMarked = 0;

    for (let i = 0; i < totalQuestions; i++) {
      const status = getQuestionStatus(i);
      switch (status) {
        case STATUS.NOT_VISITED:
          notVisited++;
          break;
        case STATUS.NOT_ANSWERED:
          notAnswered++;
          break;
        case STATUS.ANSWERED:
          answered++;
          break;
        case STATUS.MARKED_FOR_REVIEW:
          markedReview++;
          break;
        case STATUS.ANSWERED_MARKED:
          answeredMarked++;
          break;
      }
    }
    return { notVisited, notAnswered, answered, markedReview, answeredMarked };
  }, [totalQuestions, getQuestionStatus]);

  // Question list with status
  const questionsWithStatus = useMemo(
    () =>
      examData.questions.map((q, idx) => ({
        ...q,
        status: getQuestionStatus(idx),
      })),
    [examData.questions, getQuestionStatus],
  );

  // Navigation handlers
  const goToQuestion = (idx) => {
    setCurrentIndex(idx);
    setVisitedQuestions((prev) => new Set([...prev, idx]));
  };

  const saveAndNext = () => {
    if (currentIndex < totalQuestions - 1) {
      goToQuestion(currentIndex + 1);
    }
  };

  const markForReviewAndNext = () => {
    setMarkedForReview((prev) => new Set([...prev, currentIndex]));
    if (currentIndex < totalQuestions - 1) {
      goToQuestion(currentIndex + 1);
    }
  };

  const saveMarkAndNext = () => {
    if (answers[currentIndex] !== undefined) {
      setMarkedForReview((prev) => new Set([...prev, currentIndex]));
    }
    if (currentIndex < totalQuestions - 1) {
      goToQuestion(currentIndex + 1);
    }
  };

  const clearResponse = () => {
    setAnswers((prev) => {
      const newAnswers = { ...prev };
      delete newAnswers[currentIndex];
      return newAnswers;
    });
  };

  const selectOption = (optionId) => {
    setAnswers((prev) => ({ ...prev, [currentIndex]: optionId }));
  };

  const handleTimeUp = () => {
    setShowSubmitModal(true);
  };

  const handleSubmit = async () => {
    // For PYQ, we calculate results locally
    // Navigate to results with answers state
    setIsSubmitted(true);
    navigate(`/pyq/${paperId}/results`, {
      state: {
        paperId,
        answers,
        totalQuestions,
        attemptedQuestions: stats.answered + stats.answeredMarked,
      },
    });
  };

  // Loading state
  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-100">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-600 mb-4"></div>
        <h2 className="text-xl font-semibold text-gray-700">
          {loadingMessage}
        </h2>
        <p className="text-gray-500 mt-2 text-center max-w-md">
          Loading your PYQ paper. Please wait...
        </p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-100">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            Failed to Load Paper
          </h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="flex gap-4 justify-center">
            <button
              onClick={() => window.location.reload()}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-semibold"
            >
              Try Again
            </button>
            <button
              onClick={() => navigate("/pyq-papers")}
              className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded font-semibold"
            >
              Go Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // No questions state
  if (totalQuestions === 0) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-100">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
          <div className="text-yellow-500 text-5xl mb-4">📝</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">
            No Questions Available
          </h2>
          <p className="text-gray-600 mb-6">
            This paper has not been extracted yet. Please try another paper.
          </p>
          <button
            onClick={() => navigate("/pyq-papers")}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-semibold"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100 overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b-2 border-gray-300 px-4 py-2">
        <div className="flex items-center justify-between">
          {/* Left: Paper Info */}
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gray-200 rounded border-2 border-gray-400 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-500"
                fill="currentColor"
                viewBox="0 0 24 24"
              >
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
              </svg>
            </div>
            <div className="text-sm">
              <div className="flex gap-2">
                <span className="text-gray-600">Candidate Name :</span>
                <span className="font-semibold">{examData.candidateName}</span>
              </div>
              <div className="flex gap-2">
                <span className="text-gray-600">Paper</span>
                <span className="text-blue-600 font-semibold">
                  : {examData.examName} {examData.year} - Shift {examData.shift}
                </span>
              </div>
              <div className="flex gap-2 items-center">
                <span className="text-gray-600">Remaining Time :</span>
                <Timer seconds={examData.duration} onTimeUp={handleTimeUp} />
              </div>
            </div>
          </div>

          {/* Right: Language & Submit */}
          <div className="flex items-center gap-4">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm"
            >
              <option value="English">English</option>
              <option value="Hindi">Hindi</option>
              <option value="Telugu">Telugu</option>
            </select>
            <button
              onClick={() => setShowSubmitModal(true)}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              Submit
            </button>
          </div>
        </div>
      </div>

      {/* Section Tabs */}
      <div className="bg-slate-700 text-white flex">
        {examData.sections.map((section, idx) => (
          <button
            key={section.id}
            onClick={() => {
              setCurrentSection(idx);
              // Find first question of this subject/section
              const firstQIdx = examData.questions.findIndex(
                (q) => (q.subject === section.id || q.section === section.id),
              );
              if (firstQIdx !== -1) goToQuestion(firstQIdx);
            }}
            className={`px-6 py-3 text-sm font-medium transition-colors ${
              currentSection === idx
                ? "bg-blue-600 text-white"
                : "hover:bg-slate-600"
            }`}
          >
            {section.name} ({section.questionCount})
          </button>
        ))}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Question Area */}
        <div className="flex-1 flex flex-col">
          {/* Question Content */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-6">
              {/* Question Header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold text-gray-800">
                  Question {currentIndex + 1}:
                </h2>
                <div className="flex gap-2">
                  <span className="text-sm text-gray-500">
                    {currentQuestion.subject && `${currentQuestion.subject} > `}
                    {currentQuestion.section}
                    {currentQuestion.topic && ` > ${currentQuestion.topic}`}
                  </span>
                </div>
              </div>

              {/* Question Text */}
              <div className="bg-white p-6 rounded-lg shadow-sm border mb-6">
                <p className="text-gray-800 text-lg leading-relaxed">
                  <LatexText>{currentQuestion.text}</LatexText>
                </p>
                {currentQuestion.image && (
                  <div className="mt-4 flex justify-center bg-white p-2 border rounded">
                    <img 
                      src={currentQuestion.image.startsWith('http') 
                        ? currentQuestion.image 
                        : `${import.meta.env.VITE_API_URL?.replace('/api', '') || 'http://localhost:8000'}${currentQuestion.image}`} 
                      alt="Question Diagram" 
                      className="max-w-full h-auto max-h-[300px] object-contain"
                    />
                  </div>
                )}
              </div>

              {/* Options */}
              <div className="space-y-3">
                {currentQuestion.options.map((option) => {
                  const isSelected = answers[currentIndex] === option.id;

                  return (
                    <button
                      key={option.id}
                      onClick={() => selectOption(option.id)}
                      className={`w-full flex items-center gap-4 p-4 rounded-lg border-2 transition-all text-left ${
                        isSelected
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-300 bg-white hover:border-gray-400"
                      }`}
                    >
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                          isSelected
                            ? "bg-blue-500 text-white"
                            : "bg-gray-200 text-gray-700"
                        }`}
                      >
                        ({option.id})
                      </div>
                      <span className="text-gray-800">
                        <LatexText>{option.text}</LatexText>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="bg-gray-200 border-t-2 border-gray-300 p-3 flex items-center gap-2">
            <button
              onClick={saveAndNext}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              SAVE & NEXT
            </button>
            <button
              onClick={clearResponse}
              className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              CLEAR
            </button>
            <button
              onClick={saveMarkAndNext}
              className="bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              SAVE & MARK FOR REVIEW
            </button>
            <button
              onClick={markForReviewAndNext}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              MARK FOR REVIEW & NEXT
            </button>
            <div className="flex-1"></div>
            <button
              onClick={() => currentIndex > 0 && goToQuestion(currentIndex - 1)}
              disabled={currentIndex === 0}
              className="bg-gray-500 hover:bg-gray-600 disabled:opacity-50 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              ← BACK
            </button>
            <button
              onClick={() =>
                currentIndex < totalQuestions - 1 &&
                goToQuestion(currentIndex + 1)
              }
              disabled={currentIndex === totalQuestions - 1}
              className="bg-gray-500 hover:bg-gray-600 disabled:opacity-50 text-white px-4 py-2 rounded font-semibold text-sm"
            >
              NEXT →
            </button>
          </div>
        </div>

        {/* Palette Toggle Button */}
        <button
          onClick={() => setShowPalette(!showPalette)}
          className="bg-blue-600 hover:bg-blue-700 text-white w-6 flex items-center justify-center"
        >
          {showPalette ? "›" : "‹"}
        </button>

        {/* Question Palette Sidebar */}
        {showPalette && (
          <div className="w-80 bg-white border-l-2 border-gray-300 flex flex-col overflow-hidden">
            {/* Status Legend */}
            <StatusLegend stats={stats} />

            {/* Question Grid */}
            <div className="flex-1 overflow-y-auto">
              <QuestionPaletteGrid
                questions={questionsWithStatus}
                currentIndex={currentIndex}
                onQuestionClick={goToQuestion}
              />
            </div>
          </div>
        )}
      </div>

      {/* Submit Confirmation Modal */}
      <Modal
        isOpen={showSubmitModal}
        onClose={() => setShowSubmitModal(false)}
        title="Submit Examination"
        size="lg"
      >
        <div className="space-y-6">
          <p className="text-gray-700">
            Are you sure you want to submit your examination? This action cannot
            be undone.
          </p>

          {/* Summary Stats */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h3 className="font-semibold text-gray-800 mb-4">
              Examination Summary
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex justify-between">
                <span className="text-gray-600">Total Questions:</span>
                <span className="font-semibold">{totalQuestions}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Answered:</span>
                <span className="font-semibold text-green-600">
                  {stats.answered + stats.answeredMarked}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Not Answered:</span>
                <span className="font-semibold text-red-600">
                  {stats.notAnswered}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Marked for Review:</span>
                <span className="font-semibold text-purple-600">
                  {stats.markedReview}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Not Visited:</span>
                <span className="font-semibold text-gray-600">
                  {stats.notVisited}
                </span>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button variant="outline" onClick={() => setShowSubmitModal(false)}>
              Go Back to Exam
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              className="bg-green-600 hover:bg-green-700"
            >
              Confirm Submit
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
