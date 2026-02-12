// Syllabus Customizer Component - Main customization form
import { useEffect, useMemo, useRef, useState } from "react";
import Button from "../../ui/Button";
import FormRadioGroup from "../common/FormRadioGroup";
import DifficultySelector from "./DifficultySelector";
import QuestionCountSelector from "./QuestionCountSelector";
import TimeSettings from "./TimeSettings";
import TopicSelector from "./TopicSelector";

const TEST_MODES = [
  {
    value: "full",
    label: "Full Mock",
    description: "Complete blueprint practice",
  },
  {
    value: "sectional",
    label: "Sectional Drill",
    description: "Focus on one section at a time",
  },
  {
    value: "topic",
    label: "Topic Focus",
    description: "Target specific topics or weak areas",
  },
  {
    value: "pyq",
    label: "PYQ Mix",
    description: "Practice curated previous year questions",
  },
];

const CATEGORY_METADATA = {
  engineering: { label: "Engineering", badge: "bg-blue-100 text-blue-700" },
  medical: { label: "Medical", badge: "bg-rose-100 text-rose-700" },
  government: { label: "Govt Exams", badge: "bg-amber-100 text-amber-700" },
  aptitude: { label: "Aptitude", badge: "bg-violet-100 text-violet-700" },
  commerce: { label: "Commerce", badge: "bg-emerald-100 text-emerald-700" },
  default: { label: "General", badge: "bg-gray-100 text-gray-700" },
};

const EXAM_ICON_MAP = [
  { match: /eamcet|jee|engineering|ts/i, icon: "🧮" },
  { match: /neet|medical|bio/i, icon: "🧬" },
  { match: /ssc|cgl|gov|civil/i, icon: "🏛️" },
  { match: /bank|ibps|po/i, icon: "🏦" },
  { match: /aptitude|mock|quiz/i, icon: "🧠" },
];

const DEFAULT_CONFIG = {
  selectedExam: "",
  testMode: "full",
  selectedTopics: [],
  difficulty: "mixed",
  questionCount: 50,
  duration: 60,
  timerEnabled: true,
};

const slugify = (value = "") =>
  value
    .toString()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)+/g, "");

const clampQuestionCount = (value, max = 200) => {
  if (!value) return Math.min(50, max);
  return Math.max(1, Math.min(Number(value) || 1, max));
};

const getCategoryMeta = (category) =>
  CATEGORY_METADATA[category] || CATEGORY_METADATA.default;

const deriveExamCategory = (examId = "", fallback = "default") => {
  if (/jee|eamcet|bitsat|engineering/i.test(examId)) return "engineering";
  if (/neet|medical/i.test(examId)) return "medical";
  if (/ssc|cgl|gov|ias|civil/i.test(examId)) return "government";
  if (/bank|ibps|finance|cfa/i.test(examId)) return "commerce";
  if (/aptitude|mock|quiz/i.test(examId)) return "aptitude";
  return fallback || "default";
};

const pickExamIcon = (examId = "", category = "default") => {
  const matching = EXAM_ICON_MAP.find((entry) => entry.match.test(examId));
  if (matching) return matching.icon;

  const fallbackIcons = {
    engineering: "🧮",
    medical: "🧬",
    government: "🏛️",
    commerce: "💼",
    aptitude: "🧠",
    default: "📝",
  };

  return fallbackIcons[category] || fallbackIcons.default;
};

const normalizeExamOption = (exam = {}, context = {}) => {
  const id =
    exam.id ||
    exam.exam_code ||
    exam.examCode ||
    exam.slug ||
    context.fallbackId ||
    "";
  if (!id) return null;

  const category =
    exam.category ||
    context.category ||
    deriveExamCategory(id, context.defaultCategory);

  return {
    id,
    name:
      exam.name || exam.exam_name || context.fallbackName || id.toUpperCase(),
    description:
      exam.description ||
      context.fallbackDescription ||
      "Blueprint-aligned mock tests",
    category,
    icon: exam.icon || pickExamIcon(id, category),
    stats: {
      questions:
        exam.total_questions ||
        exam.questionCount ||
        context.maxQuestions ||
        null,
      duration:
        exam.duration ||
        exam.duration_minutes ||
        context.defaultDuration ||
        null,
      sections:
        exam.sections?.length || exam.sectionCount || context.sectionCount || 0,
    },
  };
};

const buildExamOptionFromConfig = (examConfig = {}) =>
  normalizeExamOption(
    {
      id: examConfig.examCode || examConfig.exam_code,
      name: examConfig.examName || examConfig.exam_name,
      description: examConfig.description,
      total_questions: examConfig.maxQuestions,
      duration_minutes: examConfig.defaultDuration,
      sections: examConfig.sections,
    },
    {
      fallbackId: examConfig.examCode || slugify(examConfig.examName || ""),
      fallbackName: examConfig.examName || "Custom Exam",
      fallbackDescription: examConfig.description,
      sectionCount: examConfig.sections?.length,
      maxQuestions: examConfig.maxQuestions,
      defaultDuration: examConfig.defaultDuration,
      defaultCategory: examConfig.category,
    },
  );

const buildInitialConfig = (examConfig = {}, preferredExamId) => ({
  ...DEFAULT_CONFIG,
  selectedExam: preferredExamId || examConfig?.examCode || "",
  questionCount: Math.min(
    DEFAULT_CONFIG.questionCount,
    examConfig?.maxQuestions || DEFAULT_CONFIG.questionCount,
  ),
  duration: examConfig?.defaultDuration || DEFAULT_CONFIG.duration,
});

export default function SyllabusCustomizer({
  examConfig = {},
  availableExams = [],
  onConfigChange,
  onSubmit,
  isLoading = false,
}) {
  const [config, setConfig] = useState(() => buildInitialConfig(examConfig));
  const [step, setStep] = useState(1);
  const totalSteps = 4;
  const maxQuestionCap = Math.max(5, examConfig?.maxQuestions || 200);
  const [isDropdownOpen, setDropdownOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const dropdownRef = useRef(null);

  useEffect(() => {
    setConfig((prev) => {
      const base = buildInitialConfig(examConfig, prev.selectedExam);
      return {
        ...base,
        ...prev,
        selectedExam: prev.selectedExam || base.selectedExam,
        questionCount: clampQuestionCount(prev.questionCount, maxQuestionCap),
      };
    });
  }, [examConfig?.examCode, maxQuestionCap, examConfig?.defaultDuration]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const examOptions = useMemo(() => {
    const primarySource =
      Array.isArray(availableExams) && availableExams.length > 0
        ? availableExams
        : examConfig?.availableExams;

    if (Array.isArray(primarySource) && primarySource.length > 0) {
      return primarySource
        .map((exam) =>
          normalizeExamOption(exam, {
            fallbackId: examConfig.examCode,
            fallbackName: examConfig.examName,
            fallbackDescription: examConfig.description,
            sectionCount: examConfig.sections?.length,
            maxQuestions: examConfig.maxQuestions,
            defaultDuration: examConfig.defaultDuration,
            defaultCategory: examConfig.category,
          }),
        )
        .filter(Boolean);
    }

    const fallback = buildExamOptionFromConfig(examConfig);
    return fallback ? [fallback] : [];
  }, [availableExams, examConfig]);

  useEffect(() => {
    setSearchTerm("");
    setDropdownOpen(false);
  }, [examOptions.length]);

  useEffect(() => {
    if (!examOptions.length) return;
    setConfig((prev) => {
      if (
        prev.selectedExam &&
        examOptions.some((exam) => exam.id === prev.selectedExam)
      ) {
        return prev;
      }
      return { ...prev, selectedExam: examOptions[0].id };
    });
  }, [examOptions]);

  useEffect(() => {
    onConfigChange?.(config);
  }, [config, onConfigChange]);

  const selectedExamDetails = useMemo(() => {
    if (!examOptions.length) return null;
    return (
      examOptions.find((option) => option.id === config.selectedExam) ||
      examOptions[0]
    );
  }, [examOptions, config.selectedExam]);

  const filteredExamOptions = useMemo(() => {
    if (!searchTerm.trim()) return examOptions;
    const term = searchTerm.trim().toLowerCase();
    return examOptions.filter((exam) => {
      const pool =
        `${exam.name} ${exam.description || ""} ${exam.id}`.toLowerCase();
      return pool.includes(term);
    });
  }, [examOptions, searchTerm]);

  const topicSections = useMemo(() => {
    const sections = Array.isArray(examConfig?.sections)
      ? examConfig.sections
      : [];
    if (config.testMode !== "topic") {
      return sections;
    }

    return sections.map((section) => {
      const topicBank =
        (Array.isArray(section.topicBank) && section.topicBank.length > 0
          ? section.topicBank
          : Array.isArray(section.topic_bank) && section.topic_bank.length > 0
            ? section.topic_bank
            : section.topics) || [];

      if (topicBank === section.topics) {
        return section;
      }

      return {
        ...section,
        topics: topicBank,
      };
    });
  }, [examConfig?.sections, config.testMode]);

  const updateConfig = (key, value) => {
    setConfig((prev) => {
      if (key === "selectedExam") {
        return { ...prev, selectedExam: value, selectedTopics: [] };
      }
      if (key === "questionCount") {
        return {
          ...prev,
          questionCount: clampQuestionCount(value, maxQuestionCap),
        };
      }
      return { ...prev, [key]: value };
    });
  };

  const handleNext = () => {
    if (step < totalSteps) {
      setStep((prev) => prev + 1);
    } else {
      onSubmit?.(config);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep((prev) => prev - 1);
    }
  };

  const canProceed = () => {
    if (!selectedExamDetails) return false;
    switch (step) {
      case 1:
        return Boolean(config.selectedExam && config.testMode);
      case 2:
        return config.testMode === "full" || config.selectedTopics.length > 0;
      case 3:
        return Boolean(config.difficulty);
      case 4:
        return config.questionCount > 0;
      default:
        return true;
    }
  };

  const getStepTitle = () => {
    switch (step) {
      case 1:
        return "Choose Exam & Test Mode";
      case 2:
        return "Select Topics";
      case 3:
        return "Set Difficulty";
      case 4:
        return "Configure Test";
      default:
        return "";
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-xl font-semibold text-gray-900">
          Customize Your Test
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure the test according to your preparation needs
        </p>

        {/* Progress Steps */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
                    s < step
                      ? "bg-blue-600 text-white"
                      : s === step
                        ? "bg-blue-100 text-blue-600 ring-2 ring-blue-600"
                        : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {s < step ? (
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    s
                  )}
                </div>
                {s < 4 && (
                  <div
                    className={`w-16 sm:w-24 h-1 mx-2 rounded ${
                      s < step ? "bg-blue-600" : "bg-gray-200"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
          <p className="text-sm font-medium text-gray-700">
            Step {step}: {getStepTitle()}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 min-h-[400px]">
        {/* Step 1: Choose Exam & Test Mode */}
        {step === 1 && (
          <div className="space-y-8">
            {/* Exam Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                Select Exam
              </label>

              {/* Selected Exam Display */}
              {selectedExamDetails && (
                <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl">
                        {selectedExamDetails.icon}
                      </span>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {selectedExamDetails.name}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {selectedExamDetails.description ||
                            "Blueprint-aligned mock tests"}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs font-semibold px-3 py-1 rounded-full ${
                        getCategoryMeta(selectedExamDetails.category).badge
                      }`}
                    >
                      {getCategoryMeta(selectedExamDetails.category).label}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-gray-600">
                    <span className="flex items-center gap-1">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                      {selectedExamDetails.stats.questions ||
                        examConfig?.maxQuestions ||
                        "--"}{" "}
                      Q bank
                    </span>
                    <span className="flex items-center gap-1">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3"
                        />
                      </svg>
                      {selectedExamDetails.stats.duration ||
                        examConfig?.defaultDuration ||
                        "--"}{" "}
                      min
                    </span>
                    <span className="flex items-center gap-1">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 6h16M4 10h16M4 14h16M4 18h16"
                        />
                      </svg>
                      {selectedExamDetails.stats.sections ||
                        examConfig?.sections?.length ||
                        0}{" "}
                      sections
                    </span>
                  </div>
                </div>
              )}

              {/* Exam Dropdown */}
              {examOptions.length > 0 ? (
                <div ref={dropdownRef} className="relative">
                  <button
                    type="button"
                    onClick={() => setDropdownOpen((prev) => !prev)}
                    className={`w-full flex items-center justify-between rounded-xl border-2 px-4 py-3 transition-all ${
                      isDropdownOpen
                        ? "border-blue-500 ring-2 ring-blue-200 bg-blue-50"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">
                        {selectedExamDetails?.icon || "📝"}
                      </span>
                      <div className="text-left">
                        <p className="font-semibold text-gray-900">
                          {selectedExamDetails?.name || "Select an exam"}
                        </p>
                        <p className="text-sm text-gray-500">
                          {selectedExamDetails?.description ||
                            "Choose from the available blueprints"}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {selectedExamDetails && (
                        <span
                          className={`text-xs font-semibold px-3 py-1 rounded-full ${
                            getCategoryMeta(selectedExamDetails.category).badge
                          }`}
                        >
                          {getCategoryMeta(selectedExamDetails.category).label}
                        </span>
                      )}
                      <svg
                        className={`w-5 h-5 text-gray-500 transition-transform ${
                          isDropdownOpen ? "rotate-180" : ""
                        }`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 9l-7 7-7-7"
                        />
                      </svg>
                    </div>
                  </button>

                  {isDropdownOpen && (
                    <div className="absolute z-20 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-xl">
                      <div className="p-3 border-b border-gray-100">
                        <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg">
                          <svg
                            className="w-4 h-4 text-gray-400"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"
                            />
                          </svg>
                          <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Search exam"
                            className="flex-1 bg-transparent text-sm text-gray-700 focus:outline-none"
                          />
                        </div>
                      </div>

                      <div className="max-h-64 overflow-y-auto divide-y divide-gray-100">
                        {filteredExamOptions.length > 0 ? (
                          filteredExamOptions.map((exam) => {
                            const isSelected = config.selectedExam === exam.id;
                            const categoryMeta = getCategoryMeta(exam.category);

                            return (
                              <button
                                key={exam.id}
                                type="button"
                                onClick={() => {
                                  updateConfig("selectedExam", exam.id);
                                  setDropdownOpen(false);
                                }}
                                className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors ${
                                  isSelected
                                    ? "bg-blue-50 text-blue-900"
                                    : "hover:bg-gray-50"
                                }`}
                              >
                                <span className="text-xl">{exam.icon}</span>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center justify-between gap-2">
                                    <h4 className="font-semibold truncate">
                                      {exam.name}
                                    </h4>
                                    <span
                                      className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${categoryMeta.badge}`}
                                    >
                                      {categoryMeta.label}
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-500 truncate">
                                    {exam.description}
                                  </p>
                                  <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-gray-500">
                                    <span className="flex items-center gap-1">
                                      <svg
                                        className="w-3.5 h-3.5"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          strokeWidth={2}
                                          d="M4 6h16M4 10h16M4 14h16M4 18h16"
                                        />
                                      </svg>
                                      {exam.stats.sections || 0} sections
                                    </span>
                                    <span className="flex items-center gap-1">
                                      <svg
                                        className="w-3.5 h-3.5"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          strokeWidth={2}
                                          d="M12 8v4l3 3"
                                        />
                                      </svg>
                                      {exam.stats.duration || "--"} min
                                    </span>
                                  </div>
                                </div>
                                {isSelected && (
                                  <svg
                                    className="w-5 h-5 text-blue-600 flex-shrink-0"
                                    fill="currentColor"
                                    viewBox="0 0 20 20"
                                  >
                                    <path
                                      fillRule="evenodd"
                                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                      clipRule="evenodd"
                                    />
                                  </svg>
                                )}
                              </button>
                            );
                          })
                        ) : (
                          <div className="p-4 text-sm text-gray-500 text-center">
                            No exams match your search
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-6 border border-dashed border-gray-300 rounded-xl bg-gray-50 text-sm text-gray-600">
                  Exam catalog not available yet. We will use the default
                  blueprint once the configuration loads.
                </div>
              )}
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-3 bg-white text-gray-500">then</span>
              </div>
            </div>

            {/* Test Mode */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-4">
                Select Test Mode
              </label>
              <FormRadioGroup
                name="testMode"
                value={config.testMode}
                onChange={(e) => updateConfig("testMode", e.target.value)}
                options={TEST_MODES}
                layout="vertical"
              />
            </div>
          </div>
        )}

        {/* Step 2: Topic Selection */}
        {step === 2 && (
          <div>
            {config.testMode === "full" ? (
              <div className="text-center py-12 bg-gray-50 rounded-lg">
                <svg
                  className="w-12 h-12 text-blue-500 mx-auto mb-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="text-gray-700 font-medium">All topics included</p>
                <p className="text-sm text-gray-500 mt-1">
                  Full mock test covers the complete syllabus
                </p>
              </div>
            ) : (
              <TopicSelector
                sections={topicSections}
                selectedTopics={config.selectedTopics}
                onTopicChange={(topics) =>
                  updateConfig("selectedTopics", topics)
                }
              />
            )}
          </div>
        )}

        {/* Step 3: Difficulty */}
        {step === 3 && (
          <DifficultySelector
            value={config.difficulty}
            onChange={(difficulty) => updateConfig("difficulty", difficulty)}
          />
        )}

        {/* Step 4: Time & Question Count */}
        {step === 4 && (
          <div className="space-y-8">
            <QuestionCountSelector
              value={config.questionCount}
              max={maxQuestionCap}
              examDuration={examConfig?.defaultDuration}
              examQuestionCount={examConfig?.maxQuestions}
              onChange={(count) => updateConfig("questionCount", count)}
            />

            <TimeSettings
              duration={config.duration}
              timerEnabled={config.timerEnabled}
              examDuration={examConfig?.defaultDuration}
              examQuestionCount={examConfig?.maxQuestions}
              questionCount={config.questionCount}
              onDurationChange={(duration) =>
                updateConfig("duration", duration)
              }
              onTimerToggle={(enabled) => updateConfig("timerEnabled", enabled)}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={handleBack}
            disabled={step === 1}
          >
            <svg
              className="w-5 h-5 mr-1"
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
            Back
          </Button>

          <div className="flex items-center gap-3">
            {/* Summary Preview */}
            <div className="hidden sm:flex items-center gap-4 text-sm text-gray-500">
              <span>{config.questionCount}Q</span>
              <span>{config.duration}min</span>
              <span className="capitalize">{config.difficulty}</span>
            </div>

            <Button
              type="button"
              variant="primary"
              onClick={handleNext}
              disabled={!canProceed()}
              isLoading={step === totalSteps && isLoading}
            >
              {step === totalSteps ? (
                <>
                  Start Test
                  <svg
                    className="w-5 h-5 ml-1"
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
                </>
              ) : (
                <>
                  Next
                  <svg
                    className="w-5 h-5 ml-1"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
