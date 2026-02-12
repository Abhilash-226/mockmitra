// Exam Customization Page
import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { SyllabusCustomizer } from "../../components/forms";
import Spinner from "../../components/ui/Spinner";
import { examService } from "../../services/examService";
import { useExamStore } from "../../store/useExamStore";

const DEFAULT_EXAM_CONFIG = {
  examCode: "",
  examName: "Exam",
  description: "Customize your practice session",
  sections: [],
  maxQuestions: 100,
  defaultDuration: 60,
  metadata: {},
};

const TEST_TYPE_MAP = {
  full: "full_length",
  sectional: "sectional",
  topic: "topic_wise",
  pyq: "custom",
};

const slugify = (value = "") =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .trim();

const normalizeTopic = (topic, index, sectionCode, indexOffset = 0) => {
  if (!topic) return null;
  const computedIndex = index + (indexOffset || 0);
  if (typeof topic === "string") {
    const topicCode =
      slugify(topic) || `${sectionCode || "topic"}-${computedIndex}`;
    return {
      id: `${topicCode}-${computedIndex}`,
      code: topicCode,
      name: topic,
      questionCount: null,
    };
  }

  const topicName = topic.name || `Topic ${index + 1}`;
  const topicCode =
    topic.code ||
    slugify(topicName) ||
    `${sectionCode || "topic"}-${computedIndex}`;

  return {
    id: `${topicCode}-${computedIndex}`,
    code: topicCode,
    name: topicName,
    questionCount: topic.question_count ?? topic.questionCount ?? null,
  };
};

const normalizeSections = (sections = [], defaults = {}) =>
  sections.map((section, index) => {
    const sectionName = section.name || `Section ${index + 1}`;
    const sectionCode =
      section.code || slugify(sectionName) || `section-${index}`;
    const topics = (section.topics || [])
      .map((topic, topicIndex) =>
        normalizeTopic(topic, topicIndex, sectionCode),
      )
      .filter(Boolean);
    const topicBankSource = section.topicBank || section.topic_bank || [];
    const topicBank = (topicBankSource || [])
      .map((topic, topicIndex) =>
        normalizeTopic(topic, topicIndex, sectionCode, topics.length),
      )
      .filter(Boolean);

    return {
      id: sectionCode,
      code: sectionCode,
      name: sectionName,
      totalQuestions: section.total_questions ?? section.totalQuestions ?? 0,
      marksPerQuestion:
        section.marks_per_question ?? defaults.defaultMarks ?? 1,
      negativeMarks: section.negative_marks ?? defaults.defaultNegative ?? 0,
      topics,
      topicBank,
    };
  });

const sumQuestions = (sections = []) =>
  sections.reduce((total, section) => total + (section.totalQuestions || 0), 0);

const transformExamConfig = (data, fallbackMeta = {}) => {
  const sections = normalizeSections(data.sections || [], {
    defaultMarks: data.default_marks_per_question,
    defaultNegative: data.default_negative_marks,
  });

  return {
    examCode: data.exam_code || fallbackMeta.examCode || "",
    examName:
      data.exam_name ||
      data.name ||
      fallbackMeta.examName ||
      fallbackMeta.name ||
      DEFAULT_EXAM_CONFIG.examName,
    description:
      data.description ||
      fallbackMeta.description ||
      DEFAULT_EXAM_CONFIG.description,
    sections,
    maxQuestions:
      data.total_questions ||
      sumQuestions(sections) ||
      fallbackMeta.questionCount ||
      DEFAULT_EXAM_CONFIG.maxQuestions,
    defaultDuration:
      data.total_duration_minutes ||
      data.duration_minutes ||
      fallbackMeta.durationMinutes ||
      DEFAULT_EXAM_CONFIG.defaultDuration,
    metadata: {
      conductingBody:
        data.conducting_body || fallbackMeta.conductingBody || undefined,
      frequency: data.frequency || fallbackMeta.frequency || undefined,
      officialWebsite:
        data.official_website || fallbackMeta.officialWebsite || undefined,
    },
  };
};

export default function ExamCustomizationPage() {
  const { examId: rawExamId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { actions } = useExamStore();

  // Filter out invalid examId values (like "customize" from route overlap)
  const examId =
    rawExamId && rawExamId !== "customize" && rawExamId !== "exam"
      ? rawExamId
      : null;

  const [examConfig, setExamConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [availableExams, setAvailableExams] = useState([]);
  const selectedExamFromState = location.state?.exam;
  const stateExamCode =
    selectedExamFromState?.id || selectedExamFromState?.exam_code || null;
  const stateExamName =
    selectedExamFromState?.name || selectedExamFromState?.exam_name || null;
  const stateExamDescription = selectedExamFromState?.description || null;
  const stateExamQuestions =
    selectedExamFromState?.questionCount ||
    selectedExamFromState?.total_questions ||
    null;
  const stateExamDuration =
    selectedExamFromState?.durationMinutes ||
    selectedExamFromState?.duration_minutes ||
    null;
  const [manualExamCode, setManualExamCode] = useState(null);
  const fallbackExamCode = examId || stateExamCode || null;
  const activeExamCode = manualExamCode || fallbackExamCode;

  // Debug logging
  console.log("ExamCustomization Debug:", {
    examId,
    stateExamCode,
    manualExamCode,
    fallbackExamCode,
    activeExamCode,
    availableExamsCount: availableExams.length,
  });

  useEffect(() => {
    let isMounted = true;

    const fetchExamList = async () => {
      try {
        const list = await examService.getExams();
        if (!isMounted) return;
        setAvailableExams(Array.isArray(list) ? list : []);
      } catch (err) {
        console.error("Failed to load exam catalog:", err);
        if (isMounted) {
          setAvailableExams([]);
        }
      }
    };

    fetchExamList();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (activeExamCode || availableExams.length === 0) return;

    const preferredExam =
      availableExams.find((exam) => exam?.is_default) || availableExams[0];

    const candidateCode =
      preferredExam?.exam_code ||
      preferredExam?.examCode ||
      preferredExam?.id ||
      preferredExam?.slug ||
      null;

    if (candidateCode) {
      setManualExamCode(candidateCode);
    }
  }, [activeExamCode, availableExams]);

  useEffect(() => {
    // Reset manual overrides when navigation changes the implied exam
    if (examId || stateExamCode) {
      setManualExamCode(null);
    }
  }, [examId, stateExamCode]);

  const getExamFallbackMeta = useCallback(
    (code) => {
      if (!code) return {};

      const fromList = availableExams.find(
        (exam) =>
          exam.exam_code === code ||
          exam.examCode === code ||
          exam.id === code ||
          exam.slug === code,
      );

      if (fromList) {
        return {
          examCode: code,
          examName: fromList.exam_name || fromList.examName || fromList.name,
          description: fromList.description,
          questionCount:
            fromList.total_questions ||
            fromList.totalQuestions ||
            fromList.questionCount ||
            fromList.questions,
          durationMinutes:
            fromList.duration_minutes ||
            fromList.durationMinutes ||
            fromList.duration,
        };
      }

      if (stateExamCode === code) {
        return {
          examCode: code,
          examName: stateExamName,
          description: stateExamDescription,
          questionCount: stateExamQuestions,
          durationMinutes: stateExamDuration,
        };
      }

      return { examCode: code };
    },
    [
      availableExams,
      stateExamCode,
      stateExamName,
      stateExamDescription,
      stateExamQuestions,
      stateExamDuration,
    ],
  );

  useEffect(() => {
    if (!activeExamCode) {
      setExamConfig({
        ...DEFAULT_EXAM_CONFIG,
        examCode: "",
        examName: stateExamName || DEFAULT_EXAM_CONFIG.examName,
        description: stateExamDescription || DEFAULT_EXAM_CONFIG.description,
        maxQuestions: stateExamQuestions || DEFAULT_EXAM_CONFIG.maxQuestions,
        defaultDuration:
          stateExamDuration || DEFAULT_EXAM_CONFIG.defaultDuration,
      });
      setError(null);
      setLoading(false);
      return;
    }

    let isMounted = true;

    const fetchExamConfig = async () => {
      try {
        setLoading(true);
        console.log("Fetching exam config for:", activeExamCode);
        const response = await examService.getExamConfig(activeExamCode);
        const data = response.data || response;
        const fallbackMeta = getExamFallbackMeta(activeExamCode);
        const transformedConfig = transformExamConfig(data, {
          ...fallbackMeta,
          examCode: activeExamCode,
        });

        if (isMounted) {
          setExamConfig(transformedConfig);
          setError(null);
        }
      } catch (err) {
        console.error("Failed to fetch exam config:", err);
        if (isMounted) {
          setError("Failed to load exam configuration");
          const fallbackMeta = getExamFallbackMeta(activeExamCode);
          setExamConfig({
            ...DEFAULT_EXAM_CONFIG,
            examCode: activeExamCode,
            examName: fallbackMeta.examName || DEFAULT_EXAM_CONFIG.examName,
            description:
              fallbackMeta.description || DEFAULT_EXAM_CONFIG.description,
            maxQuestions:
              fallbackMeta.questionCount || DEFAULT_EXAM_CONFIG.maxQuestions,
            defaultDuration:
              fallbackMeta.durationMinutes ||
              DEFAULT_EXAM_CONFIG.defaultDuration,
          });
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchExamConfig();

    return () => {
      isMounted = false;
    };
  }, [
    activeExamCode,
    getExamFallbackMeta,
    stateExamName,
    stateExamDescription,
    stateExamQuestions,
    stateExamDuration,
  ]);

  const handleConfigChange = (config) => {
    if (!config?.selectedExam) return;

    if (config.selectedExam === manualExamCode) return;

    if (config.selectedExam === fallbackExamCode) {
      setManualExamCode(null);
      return;
    }

    setManualExamCode(config.selectedExam);
  };

  const handleSubmit = async (config) => {
    console.log("Starting test with config:", config);
    const targetExamCode =
      config.selectedExam || examConfig?.examCode || examId;
    try {
      // Generate test with the config
      const testResponse = await examService.generateTest({
        title: `${examConfig?.examName || targetExamCode} ${
          config.testMode === "full" ? "Full Mock" : "Custom Test"
        }`,
        exam_code: targetExamCode,
        test_type: TEST_TYPE_MAP[config.testMode] || TEST_TYPE_MAP.full,
      });

      const testData = testResponse.data || testResponse;
      const testId = testData.id || testData._id || testData.test_id;

      // Set the exam in the store before navigating
      actions.setCurrentExam({
        ...testData,
        id: testId,
        config: config,
      });

      navigate(`/exam/${testId}/instructions`, {
        state: { config, testId: testId },
      });
    } catch (err) {
      console.error("Failed to generate test:", err);
      // Fallback to instructions page without generated test
      navigate(`/exam/${targetExamCode}/instructions`, { state: { config } });
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error && !examConfig) {
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
    <div className="max-w-4xl mx-auto">
      <SyllabusCustomizer
        examConfig={examConfig || DEFAULT_EXAM_CONFIG}
        availableExams={availableExams}
        onConfigChange={handleConfigChange}
        onSubmit={handleSubmit}
      />
    </div>
  );
}
