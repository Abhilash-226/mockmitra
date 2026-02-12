// Exam Instructions Page - JEE Main Style
import { useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import Button from "../../components/ui/Button";

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

export default function ExamInstructionsPage() {
  const { examId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const config = location.state?.config;
  const [accepted, setAccepted] = useState(false);
  const [language, setLanguage] = useState("English");

  const examName = config?.examName || "Mock Test";
  const duration = config?.duration || 180;

  const handleStartTest = () => {
    if (!accepted) {
      alert("Please accept the declaration to proceed.");
      return;
    }
    navigate(`/exam/${examId}/test`, { state: { config } });
  };

  const handleGoBack = () => {
    navigate(`/exam/${examId}/customize`);
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

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Header - Navy Blue Bar */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white py-4 px-6 flex justify-between items-center shadow-lg">
        <h1 className="text-xl font-bold tracking-wide">
          GENERAL INSTRUCTIONS
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

          {/* General Instructions Section */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 underline mb-4">
              General Instructions:
            </h3>
            <ol className="space-y-4 text-gray-700 list-decimal list-inside">
              <li className="leading-relaxed">
                <span className="ml-2">
                  Total duration of <strong>{examName}</strong> is{" "}
                  <strong>{duration} min</strong>.
                </span>
              </li>
              <li className="leading-relaxed">
                <span className="ml-2">
                  The clock will be set at the server. The countdown timer in
                  the top right corner of screen will display the remaining time
                  available for you to complete the examination. When the timer
                  reaches zero, the examination will end by itself. You will not
                  be required to end or submit your examination.
                </span>
              </li>
              <li className="leading-relaxed">
                <span className="ml-2">
                  The Questions Palette displayed on the right side of screen
                  will show the status of each question using one of the
                  following symbols:
                </span>

                {/* Status Legend */}
                <div className="mt-4 ml-6 space-y-4">
                  {STATUS_LEGEND.map((item) => (
                    <div key={item.id} className="flex items-center gap-4">
                      <span className="text-gray-600 w-6">{item.id}.</span>
                      <div className="w-12 flex justify-center">
                        {renderStatusIcon(item)}
                      </div>
                      <span className="text-gray-700">{item.label}</span>
                    </div>
                  ))}
                </div>
              </li>
              <li className="leading-relaxed">
                <span className="ml-2">
                  You can click on the {'">"'} arrow which appears to the left
                  of question palette to collapse the question palette thereby
                  maximizing the question window. To view the question palette
                  again, you can click on {'"<"'} which appears on the right
                  side of question window.
                </span>
              </li>
              <li className="leading-relaxed">
                <span className="ml-2">
                  You can click on your "Profile" image on top right corner of
                  your screen to change the language during the exam for entire
                  question paper. On clicking of Profile image you will get a
                  drop-down to change the question content to the desired
                  language.
                </span>
              </li>
              <li className="leading-relaxed">
                <span className="ml-2">
                  You can click on{" "}
                  <span className="inline-block w-6 h-6 bg-blue-500 text-white text-xs leading-6 text-center rounded">
                    ↓
                  </span>{" "}
                  to navigate to the bottom and{" "}
                  <span className="inline-block w-6 h-6 bg-blue-500 text-white text-xs leading-6 text-center rounded">
                    ↑
                  </span>{" "}
                  to navigate to top of the question area, without scrolling.
                </span>
              </li>
            </ol>
          </div>

          {/* Navigating to a Question */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 underline mb-4">
              Navigating to a Question:
            </h3>
            <ol className="space-y-3 text-gray-700 list-decimal list-inside">
              <li className="leading-relaxed">
                <span className="ml-2">
                  To answer a question, do the following:
                </span>
              </li>
              <ol className="ml-8 mt-2 space-y-2 list-decimal list-inside text-gray-600">
                <li>
                  Click on the question number in the Question Palette at the
                  right of your screen to go to that numbered question directly.
                  Note that using this option does NOT save your answer to the
                  current question.
                </li>
                <li>
                  Click on <strong>Save & Next</strong> to save your answer for
                  the current question and then go to the next question.
                </li>
                <li>
                  Click on <strong>Mark for Review & Next</strong> to save your
                  answer for the current question, mark it for review, and then
                  go to the next question.
                </li>
              </ol>
            </ol>
          </div>

          {/* Answering a Question */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 underline mb-4">
              Answering a Question:
            </h3>
            <p className="text-gray-700 mb-3">
              Procedure for answering a multiple choice type question:
            </p>
            <ol className="space-y-2 text-gray-700 list-decimal list-inside ml-4">
              <li>
                To select your answer, click on the button of one of the
                options.
              </li>
              <li>
                To deselect your chosen answer, click on the button of the
                chosen option again or click on the{" "}
                <strong>Clear Response</strong> button.
              </li>
              <li>
                To change your chosen answer, click on the button of another
                option.
              </li>
              <li>
                To save your answer, you MUST click on the{" "}
                <strong>Save & Next</strong> button.
              </li>
              <li>
                To mark the question for review, click on the{" "}
                <strong>Mark for Review & Next</strong> button.
              </li>
              <li>
                To change your answer to a question that has already been
                answered, first select that question for answering and then
                follow the procedure for answering that type of question.
              </li>
            </ol>
          </div>

          {/* Navigating through sections */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-800 underline mb-4">
              Navigating through sections:
            </h3>
            <ol className="space-y-2 text-gray-700 list-decimal list-inside ml-4">
              <li>
                Sections in this question paper are displayed on the top bar of
                the screen. Questions in a section can be viewed by clicking on
                the section name. The section you are currently viewing is
                highlighted.
              </li>
              <li>
                After clicking the Save & Next button on the last question for a
                section, you will automatically be taken to the first question
                of the next section.
              </li>
              <li>
                You can shuffle between sections and questions anytime during
                the examination as per your convenience only during the time
                stipulated.
              </li>
              <li>
                Candidate can view the corresponding section summary as part of
                the legend that appears in every section above the question
                palette.
              </li>
            </ol>
          </div>

          {/* Declaration Checkbox */}
          <div className="mt-10 p-4 bg-yellow-50 border border-yellow-300 rounded-lg">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="w-5 h-5 mt-0.5 rounded border-gray-400 text-green-600 focus:ring-green-500"
              />
              <span className="text-sm text-gray-700 leading-relaxed">
                I have read and understood the instructions. All computer
                hardware allotted to me are in proper working condition. I
                declare that I am not in possession of / not wearing / not
                carrying any prohibited gadget like mobile phone, bluetooth
                devices etc. / any prohibited material with me into the
                Examination Hall. I agree that in case of not adhering to the
                instructions, I shall be liable to be debarred from this Test
                and/or to disciplinary action, which may include ban from future
                Tests / Examinations.
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Footer Buttons */}
      <div className="bg-white border-t border-gray-200 px-8 py-4 flex items-center justify-between">
        <Button variant="outline" onClick={handleGoBack}>
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
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

        <Button
          variant="primary"
          size="lg"
          onClick={handleStartTest}
          disabled={!accepted}
          className={`px-8 py-3 text-lg font-semibold ${
            !accepted
              ? "opacity-50 cursor-not-allowed"
              : "bg-green-600 hover:bg-green-700"
          }`}
        >
          I am ready to begin
          <svg
            className="w-5 h-5 ml-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Button>
      </div>
    </div>
  );
}
