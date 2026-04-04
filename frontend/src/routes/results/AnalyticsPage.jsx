// Analytics Page Component - pulls live analytics instead of mock data
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";
import { examService } from "../../services/examService";

const formatPracticeTime = (hours) => {
  if (!hours) return "0h";
  const wholeHours = Math.floor(hours);
  const minutes = Math.round((hours - wholeHours) * 60);
  if (wholeHours === 0) return `${minutes}m`;
  if (minutes === 0) return `${wholeHours}h`;
  return `${wholeHours}h ${minutes}m`;
};

const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const isPyqMock = (name = "") => {
  const normalized = String(name).toLowerCase();
  return normalized.startsWith("pyq") || normalized.includes("past year");
};

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState("all");
  const [stats, setStats] = useState({
    testsTaken: 0,
    avgScore: 0,
    avgAccuracy: 0,
    practiceTime: "0h",
  });
  const [recentAttempts, setRecentAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const [response, historyData] = await Promise.all([
          analyticsService.getDashboard(),
          examService.getHistory().catch(() => []),
        ]);
        const data = response.data || response;

        const historyNameByAttemptId = new Map(
          (historyData || []).map((attempt) => [
            attempt.id || attempt._id,
            attempt.test_title || attempt.exam_code || "Untitled Test",
          ]),
        );

        const attempts = (data.recent_attempts || []).map((attempt, index) => ({
          id: attempt.id || `attempt-${index}`,
          testName:
            historyNameByAttemptId.get(attempt.id || attempt._id) ||
            attempt.test_title ||
            attempt.exam_code ||
            "Untitled Test",
          score: attempt.score ?? 0,
          percentage: attempt.percentage ?? 0,
          completedAt: attempt.completed_at || null,
        }));

        setStats({
          testsTaken: data.total_tests || attempts.length,
          avgScore: data.average_percentage || data.average_score || 0,
          avgAccuracy: data.overall_accuracy || 0,
          practiceTime: formatPracticeTime(data.total_time_spent_hours),
        });

        setRecentAttempts(attempts);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch analytics:", err);
        setError("Unable to load analytics right now. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const filteredAttempts = recentAttempts.filter((attempt) => {
    if (!attempt.completedAt) return true;
    const attemptDate = new Date(attempt.completedAt).getTime();
    if (Number.isNaN(attemptDate)) return true;
    if (timeRange === "week") {
      return Date.now() - attemptDate <= 7 * 24 * 60 * 60 * 1000;
    }
    if (timeRange === "month") {
      return Date.now() - attemptDate <= 30 * 24 * 60 * 60 * 1000;
    }
    return true;
  });

  const aiAttempts = filteredAttempts.filter(
    (attempt) => !isPyqMock(attempt.testName),
  );
  const pyqAttempts = filteredAttempts.filter((attempt) =>
    isPyqMock(attempt.testName),
  );

  const renderAttemptRows = (attempts) => {
    if (!attempts.length) {
      return (
        <p className="text-gray-500 text-center py-8">
          No attempts in this section
        </p>
      );
    }

    return (
      <div className="divide-y divide-gray-200">
        {attempts.map((attempt) => (
          <div
            key={attempt.id}
            className="p-3 hover:bg-gray-50 transition-colors"
          >
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-base font-semibold text-gray-900 truncate">
                  {attempt.testName}
                </p>
                <p className="text-[11px] text-gray-500 mt-1">
                  {formatDate(attempt.completedAt)}
                </p>
              </div>

              <div className="flex items-center gap-5">
                <div className="text-center min-w-[70px]">
                  <p className="text-xl font-bold text-gray-900">
                    {attempt.score}
                  </p>
                  <p className="text-[11px] text-gray-500">Score</p>
                </div>

                <div className="text-center min-w-[90px]">
                  <p
                    className={`text-xl font-bold ${
                      attempt.percentage >= 80
                        ? "text-green-600"
                        : attempt.percentage >= 60
                          ? "text-yellow-600"
                          : "text-red-600"
                    }`}
                  >
                    {attempt.percentage}%
                  </p>
                  <p className="text-[11px] text-gray-500">Percentage</p>
                </div>

                <Link
                  to={`/results/${attempt.id}`}
                  className="shrink-0 whitespace-nowrap text-sm font-medium text-blue-600 hover:text-blue-700"
                >
                  View Results
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Performance Analytics
          </h1>
          <p className="text-gray-600 mt-1">
            Your latest performance metrics from completed tests
          </p>
        </div>
        <div className="flex gap-2">
          {["week", "month", "all"].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${
                timeRange === range
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {range === "all" ? "All Time" : `Last ${range}`}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">
              {stats.testsTaken}
            </p>
            <p className="text-sm text-gray-500">Tests Taken</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-600">
              {stats.avgScore}%
            </p>
            <p className="text-sm text-gray-500">Average Score</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">
              {stats.avgAccuracy}%
            </p>
            <p className="text-sm text-gray-500">Overall Accuracy</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-orange-600">
              {stats.practiceTime}
            </p>
            <p className="text-sm text-gray-500">Practice Time</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Latest Attempts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <div>
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
                AI Mocks
              </h4>
              <div className="rounded-lg border border-gray-200 bg-white">
                {renderAttemptRows(aiAttempts)}
              </div>
            </div>

            <div className="xl:border-l xl:border-gray-200 xl:pl-6">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
                PYQ Mocks
              </h4>
              <div className="rounded-lg border border-gray-200 bg-white">
                {renderAttemptRows(pyqAttempts)}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
