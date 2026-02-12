// Exam Selection Form Component
import { useState, useMemo, useEffect } from "react";
import { Card, CardContent } from "../../ui/Card";
import Spinner from "../../ui/Spinner";
import { examService } from "../../../services/examService";

const CATEGORIES = [
  { id: "all", label: "All Exams" },
  { id: "engineering", label: "Engineering" },
  { id: "ssc", label: "SSC" },
  { id: "banking", label: "Banking" },
  { id: "railway", label: "Railway" },
  { id: "state", label: "State PSC" },
  { id: "others", label: "Others" },
];

const EXAM_ICONS = {
  engineering: "🎓",
  banking: "🏦",
  railway: "🚆",
  ssc: "🏢",
  state: "🏛️",
  others: "📘",
  ts_eamcet: "🎓",
  ssc_cgl: "🏢",
  ssc_chsl: "📝",
  ibps_po: "🏦",
  ibps_clerk: "📋",
  rrb_ntpc: "🚂",
  default: "📚",
};
const FALLBACK_EXAMS = [
  {
    exam_code: "ssc_cgl",
    exam_name: "SSC CGL",
    description: "Tier I & II combined preparation",
    total_questions: 100,
    duration_minutes: 60,
    sections: ["Reasoning", "Quant", "English", "General Awareness"],
    popular: true,
  },
];

const slugify = (value = "") =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .trim();

const deriveCategory = (examCode = "", examName = "") => {
  const source = `${examCode} ${examName}`.toLowerCase();
  if (source.includes("ssc")) return "ssc";
  if (source.includes("bank")) return "banking";
  if (source.includes("rail")) return "railway";
  if (source.includes("psc")) return "state";
  if (source.includes("eamcet") || source.includes("jee")) return "engineering";
  return "others";
};

const normalizeExam = (exam) => {
  if (!exam) return null;

  const rawSections = Array.isArray(exam.sections) ? exam.sections : [];
  const questionCount = Number(exam.total_questions || exam.questionCount || 0);
  const durationMinutes = Number(exam.duration_minutes || exam.duration || 0);
  const examCode =
    exam.exam_code ||
    exam.id ||
    slugify(exam.exam_name || exam.name) ||
    `exam-${Math.random().toString(36).slice(2, 8)}`;
  const normalizedCode = examCode.toLowerCase();
  const displayName =
    exam.exam_name || exam.name || exam.fullName || examCode.toUpperCase();
  const category = exam.category || deriveCategory(normalizedCode, displayName);
  const statsBits = [];
  if (questionCount) statsBits.push(`${questionCount} questions`);
  if (durationMinutes) statsBits.push(`${durationMinutes} min`);
  if (rawSections.length) statsBits.push(`${rawSections.length} sections`);

  return {
    id: normalizedCode,
    name: displayName,
    fullName: exam.full_name || displayName,
    category,
    icon:
      EXAM_ICONS[normalizedCode] || EXAM_ICONS[category] || EXAM_ICONS.default,
    description: exam.description || `${displayName} preparation`,
    questionCount,
    durationMinutes,
    sections: rawSections,
    difficulty: exam.difficulty || "Medium",
    statsLabel: statsBits.join(" • ") || "Adaptive practice",
    popular: Boolean(exam.popular),
  };
};

const markPopularExams = (examList) => {
  if (!Array.isArray(examList) || examList.length === 0) return [];
  const sorted = [...examList].sort(
    (a, b) => (b.questionCount || 0) - (a.questionCount || 0),
  );
  const topIds = sorted.slice(0, 3).map((exam) => exam.id);
  return examList.map((exam) => ({
    ...exam,
    popular: exam.popular || topIds.includes(exam.id),
  }));
};

export default function ExamSelectionForm({ exams: propExams, onSelect }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [exams, setExams] = useState(() =>
    markPopularExams(
      (propExams && propExams.length > 0 ? propExams : FALLBACK_EXAMS)
        .map(normalizeExam)
        .filter(Boolean),
    ),
  );
  const [loading, setLoading] = useState(!propExams || propExams.length === 0);
  const [error, setError] = useState(null);

  // Fetch exams from API if not provided via props
  useEffect(() => {
    if (propExams && propExams.length > 0) {
      setExams(markPopularExams(propExams.map(normalizeExam).filter(Boolean)));
      setLoading(false);
      return;
    }

    const fetchExams = async () => {
      try {
        setLoading(true);
        const response = await examService.getExams();
        const transformedExams = (response?.data || response || [])
          .map(normalizeExam)
          .filter(Boolean);
        const hydrated = transformedExams.length
          ? markPopularExams(transformedExams)
          : markPopularExams(FALLBACK_EXAMS.map(normalizeExam));
        setExams(hydrated);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch exams:", err);
        setError("Failed to load exams");
        setExams(markPopularExams(FALLBACK_EXAMS.map(normalizeExam)));
      } finally {
        setLoading(false);
      }
    };

    fetchExams();
  }, [propExams]);

  const filteredExams = useMemo(() => {
    return exams.filter((exam) => {
      const matchesSearch =
        exam.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        exam.fullName.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory =
        selectedCategory === "all" || exam.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [exams, searchQuery, selectedCategory]);

  const popularExams = useMemo(() => {
    return exams.filter((exam) => exam.popular);
  }, [exams]);

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div className="relative">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          placeholder="Search exams..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg"
        />
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-hide">
        {CATEGORIES.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
              selectedCategory === category.id
                ? "bg-blue-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {category.label}
          </button>
        ))}
      </div>

      {/* Popular Exams (only when showing all) */}
      {selectedCategory === "all" &&
        !searchQuery &&
        popularExams.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Popular Exams
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {popularExams.map((exam) => (
                <button
                  key={exam.id}
                  onClick={() => onSelect?.(exam)}
                  className="flex items-center gap-3 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl hover:from-blue-100 hover:to-indigo-100 transition-colors text-left"
                >
                  <span className="text-2xl">{exam.icon}</span>
                  <div>
                    <p className="font-semibold text-gray-900">{exam.name}</p>
                    <p className="text-xs text-gray-500">{exam.statsLabel}</p>
                  </div>
                  <svg
                    className="w-5 h-5 text-blue-600 ml-auto"
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
                </button>
              ))}
            </div>
          </div>
        )}

      {/* All Exams Grid */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
          {selectedCategory === "all"
            ? "All Exams"
            : CATEGORIES.find((c) => c.id === selectedCategory)?.label}
          <span className="ml-2 text-gray-400 font-normal">
            ({filteredExams.length})
          </span>
        </h3>

        {loading ? (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        ) : error ? (
          <div className="text-center py-12 bg-red-50 rounded-xl">
            <p className="text-red-600">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Retry
            </button>
          </div>
        ) : filteredExams.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-xl">
            <svg
              className="w-12 h-12 text-gray-300 mx-auto mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-gray-500">No exams found</p>
            <button
              onClick={() => {
                setSearchQuery("");
                setSelectedCategory("all");
              }}
              className="mt-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredExams.map((exam) => (
              <Card
                key={exam.id}
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => onSelect?.(exam)}
              >
                <CardContent className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center text-2xl flex-shrink-0">
                      {exam.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-semibold text-gray-900">
                            {exam.name}
                          </h4>
                          <p className="text-xs text-gray-500 truncate">
                            {exam.fullName}
                          </p>
                        </div>
                        {exam.popular && (
                          <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded-full">
                            Popular
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                        {exam.description}
                      </p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
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
                          {exam.questionCount.toLocaleString()} Q
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
                          {exam.durationMinutes
                            ? `${exam.durationMinutes} min`
                            : `${exam.sections.length} section${
                                exam.sections.length === 1 ? "" : "s"
                              }`}
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
