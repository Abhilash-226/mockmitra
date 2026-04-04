// History Page Component
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import { examService } from "../../services/examService"; // Changed from analyticsService
import { analyticsService } from "../../services/analyticsService"; // Keep for stats if needed

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [sectionFilter, setSectionFilter] = useState("all");
  const [stats, setStats] = useState({
    totalTests: 0,
    avgScore: 0,
    accuracy: 0,
    practiceTime: "0h",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const pollingTimerRef = useRef(null);
  const isFetchingRef = useRef(false);
  const latestHistoryRef = useRef([]);

  const fetchHistory = async () => {
    if (isFetchingRef.current) return null;
    isFetchingRef.current = true;
    try {
      const [historyResult, dashboardResult] = await Promise.allSettled([
        examService.getHistory(),
        analyticsService.getDashboard(),
      ]);

      const historyData =
        historyResult.status === "fulfilled"
          ? historyResult.value
          : latestHistoryRef.current;
      const dashboardData =
        dashboardResult.status === "fulfilled" ? dashboardResult.value : {};

      if (historyResult.status === "rejected") {
        console.warn(
          "History fetch timed out/failed. Retaining previous data.",
        );
      }

      // Extract history from API
      // The backend now returns TestAttemptResponse list
      const testHistory = (historyData || []).map((attempt) => ({
        id: attempt.id || attempt._id,
        testId: attempt.test_id, // For resuming/starting
        examName: attempt.test_title || attempt.exam_code || "Untitled Test",
        date: attempt.started_at || attempt.created_at,
        completedDate: attempt.completed_at,
        score: attempt.score ?? 0,
        percentage: attempt.percentage ?? 0,
        status: attempt.status, // generating, not_started, in_progress, completed, abandoned
      }));

      setHistory(testHistory);
      latestHistoryRef.current = testHistory;

      // Set stats from dashboard data (or calculate locally if needed)
      setStats({
        totalTests:
          dashboardData.total_tests ||
          testHistory.filter((t) => t.status === "completed").length,
        avgScore: dashboardData.average_percentage || 0,
        accuracy: dashboardData.overall_accuracy || 0,
        practiceTime: formatPracticeTime(
          dashboardData.total_time_spent_hours || 0,
        ),
      });

      if (historyResult.status === "fulfilled") {
        setError(null);
      }
      return {
        ok: historyResult.status === "fulfilled",
        hasGenerating: testHistory.some((t) => t.status === "generating"),
      };
    } catch (err) {
      console.error("Failed to fetch history:", err);
      setError("Failed to load test history");
      return { ok: false, hasGenerating: false };
    } finally {
      isFetchingRef.current = false;
      setLoading(false);
    }
  };

  useEffect(() => {
    let isUnmounted = false;

    const scheduleNextPoll = (delayMs) => {
      if (isUnmounted) return;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
      pollingTimerRef.current = setTimeout(runPoll, delayMs);
    };

    const runPoll = async () => {
      const result = await fetchHistory();
      if (isUnmounted) return;

      if (!result || !result.ok) {
        scheduleNextPoll(45000);
      } else if (result.hasGenerating) {
        scheduleNextPoll(15000);
      } else {
        scheduleNextPoll(60000);
      }
    };

    runPoll();

    return () => {
      isUnmounted = true;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, []);

  const formatPracticeTime = (hours) => {
    if (!hours) return "0h";
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    if (wholeHours === 0) return `${minutes}m`;
    if (minutes === 0) return `${wholeHours}h`;
    return `${wholeHours}h ${minutes}m`;
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "generating":
        return (
          <span className="flex items-center gap-2 text-blue-600 bg-blue-50 px-3 py-1 rounded-full text-sm font-medium">
            <Spinner size="sm" /> Generating...
          </span>
        );
      case "not_started":
        return (
          <span className="text-gray-600 bg-gray-100 px-3 py-1 rounded-full text-sm font-medium">
            Ready to Start
          </span>
        );
      case "in_progress":
        return (
          <span className="text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full text-sm font-medium">
            In Progress
          </span>
        );
      case "abandoned":
        return (
          <span className="text-red-600 bg-red-50 px-3 py-1 rounded-full text-sm font-medium">
            Abandoned
          </span>
        );
      default:
        return null; // Completed shows score
    }
  };

  const isPyqMock = (test) => {
    const name = (test.examName || "").toLowerCase();
    return name.startsWith("pyq") || name.includes("past year");
  };

  const pyqMocks = history.filter(isPyqMock);
  const aiMocks = history.filter((test) => !isPyqMock(test));
  const aiSubmitted = aiMocks.filter((test) => test.status === "completed");
  const aiInGenerationOrGenerated = aiMocks.filter(
    (test) => test.status !== "completed",
  );

  const formatDate = (dateStr) => {
    if (!dateStr) return "...";
    const normalizedDateStr =
      dateStr.endsWith("Z") || dateStr.includes("+") ? dateStr : dateStr + "Z";
    return new Date(normalizedDateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderHistoryRows = (tests) => {
    if (!tests.length) {
      return (
        <div className="p-4 text-sm text-gray-500">
          No tests in this section
        </div>
      );
    }

    return tests.map((test) => (
      <div key={test.id} className="p-4 hover:bg-gray-50 transition-colors">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex-1">
            <h3 className="font-medium text-gray-900">{test.examName}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {formatDate(test.date)}
            </p>
          </div>

          <div className="flex items-center gap-6">
            {test.status === "completed" ? (
              <>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">
                    {test.score}
                  </p>
                  <p className="text-xs text-gray-500">Score</p>
                </div>
                <div className="text-center">
                  <p
                    className={`text-2xl font-bold ${
                      test.percentage >= 80
                        ? "text-green-600"
                        : test.percentage >= 60
                          ? "text-yellow-600"
                          : "text-red-600"
                    }`}
                  >
                    {test.percentage}%
                  </p>
                  <p className="text-xs text-gray-500">Percentage</p>
                </div>
                <Link to={`/results/${test.id}`}>
                  <button className="px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                    View Results
                  </button>
                </Link>
              </>
            ) : (
              getStatusBadge(test.status)
            )}

            {(test.status === "not_started" ||
              test.status === "in_progress") && (
              <Link to={`/exam/${test.testId}/test`}>
                <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors">
                  {test.status === "in_progress" ? "Resume Test" : "Start Test"}
                </button>
              </Link>
            )}
          </div>
        </div>
      </div>
    ));
  };

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
      {/* Stats Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-blue-50 border-blue-100">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">
              {stats.totalTests}
            </p>
            <p className="text-sm text-blue-700">Total Tests</p>
          </CardContent>
        </Card>
        <Card className="bg-green-50 border-green-100">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-600">
              {stats.avgScore}%
            </p>
            <p className="text-sm text-green-700">Avg Score</p>
          </CardContent>
        </Card>
        <Card className="bg-purple-50 border-purple-100">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">
              {stats.accuracy}%
            </p>
            <p className="text-sm text-purple-700">Accuracy</p>
          </CardContent>
        </Card>
        <Card className="bg-orange-50 border-orange-100">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-orange-600">
              {stats.practiceTime}
            </p>
            <p className="text-sm text-orange-700">Practice Time</p>
          </CardContent>
        </Card>
      </div>

      {/* Test History List */}
      {history.length > 0 ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            {[
              { key: "all", label: "All", count: history.length },
              { key: "ai", label: "AI Mocks", count: aiMocks.length },
              { key: "pyq", label: "PYQ Mocks", count: pyqMocks.length },
            ].map((item) => (
              <button
                key={item.key}
                onClick={() => setSectionFilter(item.key)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                  sectionFilter === item.key
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                }`}
              >
                {item.label} ({item.count})
              </button>
            ))}
          </div>

          {(sectionFilter === "all" || sectionFilter === "ai") && (
            <Card>
              <CardContent className="p-0">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                  <h2 className="text-lg font-semibold text-gray-900">
                    AI Mocks ({aiMocks.length})
                  </h2>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2">
                  <div className="min-w-0 lg:border-r lg:border-gray-200">
                    <div className="px-4 py-3 border-b border-gray-100 bg-white">
                      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        Submitted
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {renderHistoryRows(aiSubmitted)}
                    </div>
                  </div>

                  <div className="min-w-0 border-t border-gray-100 lg:border-t-0">
                    <div className="px-4 py-3 border-b border-gray-100 bg-white">
                      <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                        In Generation / Generated
                      </h3>
                    </div>
                    <div className="divide-y divide-gray-200">
                      {renderHistoryRows(aiInGenerationOrGenerated)}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {(sectionFilter === "all" || sectionFilter === "pyq") && (
            <Card>
              <CardContent className="p-0">
                <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                  <h2 className="text-lg font-semibold text-gray-900">
                    PYQ Mocks ({pyqMocks.length})
                  </h2>
                </div>
                <div className="divide-y divide-gray-200">
                  {renderHistoryRows(pyqMocks)}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <svg
            className="w-16 h-16 text-gray-300 mx-auto mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No test history
          </h3>
          <p className="text-gray-500 mb-4">
            Start taking tests to see your history here
          </p>
          <Link to="/exam/custom/customize">
            {" "}
            {/* Adjust link as needed */}
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors">
              Take a Test
            </button>
          </Link>
        </div>
      )}
    </div>
  );
}
