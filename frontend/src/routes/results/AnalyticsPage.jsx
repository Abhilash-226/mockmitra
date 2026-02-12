// Analytics Page Component - pulls live analytics instead of mock data
import { useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import ProgressBar from "../../components/ui/ProgressBar";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";

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

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState("all");
  const [stats, setStats] = useState({
    testsTaken: 0,
    avgScore: 0,
    avgAccuracy: 0,
    totalQuestions: 0,
    practiceTime: "0h",
    bestScore: 0,
  });
  const [recentAttempts, setRecentAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        const response = await analyticsService.getDashboard();
        const data = response.data || response;

        const attempts = (data.recent_attempts || []).map((attempt, index) => ({
          id: attempt.id || `attempt-${index}`,
          testId: attempt.test_id || null,
          score: attempt.score ?? 0,
          percentage: attempt.percentage ?? 0,
          completedAt: attempt.completed_at || null,
        }));

        const bestScore = attempts.length
          ? Math.max(...attempts.map((attempt) => attempt.percentage))
          : 0;

        setStats({
          testsTaken: data.total_tests || attempts.length,
          avgScore: data.average_percentage || data.average_score || 0,
          avgAccuracy: data.overall_accuracy || 0,
          totalQuestions: data.total_questions_attempted || 0,
          practiceTime: formatPracticeTime(data.total_time_spent_hours),
          bestScore,
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

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.testsTaken}</p>
                <p className="text-sm text-gray-500">Tests Taken</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 text-green-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5"
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
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.avgScore}%</p>
                <p className="text-sm text-gray-500">Average Score</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                  />
                </svg>
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.avgAccuracy}%</p>
                <p className="text-sm text-gray-500">Overall Accuracy</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-orange-100 text-orange-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-5 h-5"
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
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.practiceTime}</p>
                <p className="text-sm text-gray-500">Practice Time</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Performance */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent Performance</CardTitle>
          </CardHeader>
          <CardContent>
            {filteredAttempts.length > 0 ? (
              <div className="space-y-4">
                {filteredAttempts.map((attempt) => (
                  <div
                    key={attempt.id}
                    className="flex flex-col sm:flex-row sm:items-center gap-4"
                  >
                    <div className="sm:w-48">
                      <p className="text-sm font-medium text-gray-900">
                        Attempt {attempt.id.slice(-4)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatDate(attempt.completedAt)}
                      </p>
                    </div>
                    <div className="flex-1">
                      <ProgressBar
                        value={attempt.percentage}
                        max={100}
                        color={
                          attempt.percentage >= 70
                            ? "success"
                            : attempt.percentage >= 50
                              ? "warning"
                              : "danger"
                        }
                        showLabel
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-700">
                      {attempt.score} pts
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">
                No attempts in this range yet
              </p>
            )}
          </CardContent>
        </Card>

        {/* Activity Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Activity Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-500">Questions Attempted</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.totalQuestions}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Best Score</p>
                <p className="text-2xl font-bold text-green-600">
                  {stats.bestScore || 0}%
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Average Score</p>
                <p className="text-2xl font-bold text-blue-600">
                  {stats.avgScore}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Attempts Table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Attempts</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {recentAttempts.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {recentAttempts.map((attempt) => (
                <div
                  key={attempt.id}
                  className="p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3"
                >
                  <div>
                    <p className="font-medium text-gray-900">
                      Attempt {attempt.id.slice(-6)}
                    </p>
                    <p className="text-sm text-gray-500">
                      {formatDate(attempt.completedAt)}
                    </p>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <p
                        className={`text-2xl font-bold ${
                          attempt.percentage >= 80
                            ? "text-green-600"
                            : attempt.percentage >= 60
                              ? "text-yellow-600"
                              : "text-red-600"
                        }`}
                      >
                        {attempt.percentage}%
                      </p>
                      <p className="text-xs text-gray-500">Percentage</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-gray-900">
                        {attempt.score}
                      </p>
                      <p className="text-xs text-gray-500">Score</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              No attempts available yet
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
