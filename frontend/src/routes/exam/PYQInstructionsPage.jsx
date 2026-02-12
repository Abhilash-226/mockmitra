// PYQ Instructions Page - For Past Year Question Papers
import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import { pyqService } from "../../services/pyqService";

// Status legend items matching real CBT
const STATUS_LEGEND = [
  {
    id: 1,
    label: "You have not visited the question yet.",
    className: "w-10 h-10 bg-gray-300 border-2 border-gray-400 rounded",
    shape: "square",
  },
  {
    id: 2,
    label: "You have not answered the question.",
    className:
      "w-0 h-0 border-l-[20px] border-r-[20px] border-b-[35px] border-l-transparent border-r-transparent border-b-red-500",
    shape: "triangle",
  },
  {
    id: 3,
    label: "You have answered the question.",
    className:
      "w-0 h-0 border-l-[20px] border-r-[20px] border-b-[35px] border-l-transparent border-r-transparent border-b-green-500",
    shape: "triangle",
  },
  {
    id: 4,
    label:
      "You have NOT answered the question, but have marked the question for review.",
    className: "w-10 h-10 bg-purple-600 rounded-full",
    shape: "circle",
  },
  {
    id: 5,
    label:
      'The question(s) "Answered and Marked for Review" will be considered for evaluation.',
    className: "w-10 h-10 bg-purple-600 rounded-full relative",
    shape: "circle-tick",
  },
];

export default function PYQInstructionsPage() {
  const { paperId } = useParams();
  const navigate = useNavigate();
  const [accepted, setAccepted] = useState(false);
  const [language, setLanguage] = useState("English");
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPaper = async () => {
      try {
        setLoading(true);
        const data = await pyqService.getPaper(paperId);
        setPaper(data);
      } catch (err) {
        console.error("Failed to fetch paper:", err);
        setError(err.message || "Failed to load paper details");
      } finally {
        setLoading(false);
      }
    };
    fetchPaper();
  }, [paperId]);

  const handleStartTest = () => {
    if (!accepted) {
      alert("Please accept the declaration to proceed.");
      return;
    }
    navigate(`/pyq/${paperId}/test`, { state: { paper } });
  };

  const handleGoBack = () => {
    navigate("/pyq-papers");
  };

  // Render status icon based on shape
  const renderStatusIcon = (item) => {
    if (item.shape === "circle-tick") {
      return (
        <div className="relative">
          <div className={item.className}></div>
          <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
            <svg
              className="w-3 h-3 text-white"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
      );
    }
    return <div className={item.className}></div>;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-red-500">{error}</p>
        <Button onClick={handleGoBack}>Go Back</Button>
      </div>
    );
  }

  const examName = paper?.exam || "TS EAMCET";
  const year = paper?.year || "";
  const shift = paper?.shift || 1;
  const duration = paper?.metadata?.duration_minutes || 180;
  const totalQuestions = paper?.metadata?.total_questions || 160;

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header - Navy Blue Bar */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white py-4 px-6 flex justify-between items-center shadow-lg">
        <h1 className="text-xl font-bold tracking-wide">
          {examName} {year} - Shift {shift} | INSTRUCTIONS
        </h1>
        <div className="flex items-center gap-2">
          <span className="text-sm">Choose Your Default Language</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-white text-gray-800 px-4 py-2 rounded border-0 text-sm font-medium min-w-[120px]"
          >
            <option value="English">English</option>
            <option value="Hindi">Hindi</option>
            <option value="Telugu">Telugu</option>
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-5xl mx-auto bg-white rounded-lg shadow-md p-8">
          {/* Title */}
          <h2 className="text-xl font-bold text-center text-gray-800 mb-8">
            Please read the instructions carefully
          </h2>

          {/* Paper Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-blue-800 mb-2">Paper Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Exam:</span>
                <span className="ml-2 font-medium">{examName}</span>
              </div>
              <div>
                <span className="text-gray-600">Year:</span>
                <span className="ml-2 font-medium">{year}</span>
              </div>
              <div>
                <span className="text-gray-600">Duration:</span>
                <span className="ml-2 font-medium">{duration} minutes</span>
              </div>
              <div>
                <span className="text-gray-600">Questions:</span>
                <span className="ml-2 font-medium">{totalQuestions}</span>
              </div>
            </div>
          </div>

          {/* General Instructions */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              General Instructions:
            </h3>
            <ol className="list-decimal list-inside space-y-3 text-gray-700">
              <li>
                Total duration of examination is{" "}
                <strong>{duration} minutes</strong>.
              </li>
              <li>
                The clock will be set at the server. The countdown timer in the
                top right corner of screen will display the remaining time
                available for you to complete the examination.
              </li>
              <li>
                The Question Palette displayed on the right side of screen will
                show the status of each question using different symbols.
              </li>
              <li>
                You can click on the question number in the Question Palette to
                go to that question directly.
              </li>
              <li>
                You can click on <strong>Save &amp; Next</strong> to save your
                answer for the current question and move to the next question.
              </li>
              <li>
                You can click on <strong>Mark for Review &amp; Next</strong> to
                save your answer and mark it for review, and then go to the next
                question.
              </li>
            </ol>
          </div>

          {/* Question Status Legend */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              Question Status Legend:
            </h3>
            <div className="space-y-4">
              {STATUS_LEGEND.map((item) => (
                <div key={item.id} className="flex items-center gap-4">
                  <div className="w-12 h-12 flex items-center justify-center">
                    {renderStatusIcon(item)}
                  </div>
                  <span className="text-gray-700">{item.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sections */}
          {paper?.sections && paper.sections.length > 0 && (
            <div className="mb-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                Sections:
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {paper.sections.map((section) => (
                  <div
                    key={section.code}
                    className="bg-gray-50 border rounded-lg p-4"
                  >
                    <h4 className="font-semibold text-gray-800">
                      {section.name}
                    </h4>
                    <p className="text-sm text-gray-600">
                      {section.question_count} Questions
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Declaration */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="mt-1 w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
              />
              <span className="text-gray-700">
                I have read and understood the instructions. I agree to comply
                with all the rules and regulations for this examination. I
                understand that any violation may result in cancellation of my
                candidature.
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t shadow-lg py-4 px-6">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <Button variant="secondary" onClick={handleGoBack}>
            ← Go Back
          </Button>
          <Button
            onClick={handleStartTest}
            disabled={!accepted}
            className={!accepted ? "opacity-50 cursor-not-allowed" : ""}
          >
            I am ready to begin →
          </Button>
        </div>
      </div>
    </div>
  );
}
