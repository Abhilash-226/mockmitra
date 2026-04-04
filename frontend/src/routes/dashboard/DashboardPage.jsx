// Dashboard Page Component
import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";
import { analyticsService } from "../../services/analyticsService";
import { examService } from "../../services/examService";
import Button from "../../components/ui/Button";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

const QUICK_ACTIONS = [
  {
    icon: (
      <svg
        className="w-6 h-6"
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
    ),
    title: "PYQ Papers",
    description: "Attempt actual past papers",
    to: "/pyq-papers",
    color: "bg-blue-500",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
        />
      </svg>
    ),
    title: "Custom Test",
    description: "Create personalized practice",
    to: "/exam/customize",
    color: "bg-green-500",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
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
    ),
    title: "Recent Tests",
    description: "Review your past attempts",
    to: "/history",
    color: "bg-purple-500",
  },
  {
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    title: "Analytics",
    description: "View detailed insights",
    to: "/analytics",
    color: "bg-orange-500",
  },
];

export default function DashboardPage() {
  const { user } = useAuthStore();
  const [dashboardData, setDashboardData] = useState(null);
  const [historyData, setHistoryData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const pollingTimerRef = useRef(null);
  const isFetchingRef = useRef(false);

  useEffect(() => {
    let isUnmounted = false;

    const fetchDashboardData = async (showLoading = true) => {
      if (isFetchingRef.current) return null;
      isFetchingRef.current = true;
      try {
        if (showLoading) setLoading(true);
        const [dashboard, history] = await Promise.all([
          analyticsService.getDashboard().catch(() => null),
          examService.getHistory().catch(() => []),
        ]);
        setDashboardData(dashboard);
        setHistoryData(history || []);
        setError(null);
        return {
          ok: true,
          hasGenerating: (history || []).some(
            (attempt) => attempt.status === "generating",
          ),
        };
      } catch (err) {
        setError(err.message);
        return { ok: false, hasGenerating: false };
      } finally {
        isFetchingRef.current = false;
        if (showLoading) setLoading(false);
      }
    };

    const scheduleNextPoll = (delayMs) => {
      if (isUnmounted) return;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
      pollingTimerRef.current = setTimeout(runPoll, delayMs);
    };

    const runPoll = async (showLoading = false) => {
      const result = await fetchDashboardData(showLoading);
      if (isUnmounted) return;

      if (!result || !result.ok) {
        scheduleNextPoll(45000);
      } else if (result.hasGenerating) {
        scheduleNextPoll(20000);
      } else {
        scheduleNextPoll(60000);
      }
    };

    runPoll(true);

    return () => {
      isUnmounted = true;
      if (pollingTimerRef.current) clearTimeout(pollingTimerRef.current);
    };
  }, []);

  // Format relative time
  const formatRelativeTime = (dateStr) => {
    if (!dateStr) return "N/A";
    const normalizedDateStr =
      dateStr.endsWith("Z") || dateStr.includes("+") ? dateStr : dateStr + "Z";
    const date = new Date(normalizedDateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours} hours ago`;
    if (diffDays === 1) return "Yesterday";
    return `${diffDays} days ago`;
  };

  // Default values when no data
  const stats = {
    total_tests: dashboardData?.total_tests || 0,
    average_percentage: dashboardData?.average_percentage || 0,
    total_time_spent_hours: dashboardData?.total_time_spent_hours || 0,
    overall_accuracy: dashboardData?.overall_accuracy || 0,
  };

  const historyNameByAttemptId = new Map(
    (historyData || []).map((attempt) => [
      attempt.id || attempt._id,
      attempt.test_title || attempt.exam_code || "Untitled Test",
    ]),
  );

  const recentTests = (dashboardData?.recent_attempts || [])
    .map((attempt) => ({
      ...attempt,
      test_name:
        historyNameByAttemptId.get(attempt.id || attempt._id) ||
        attempt.test_title ||
        attempt.exam_code ||
        "Untitled Test",
    }))
    .slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          Failed to load dashboard data. Please try again.
        </div>
      )}

      {/* Welcome Section */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl p-6 text-white">
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.name || "Aspirant"}! 👋
        </h1>
        <p className="mt-2 text-blue-100">
          {stats.total_tests > 0
            ? "You're making great progress. Keep up the momentum!"
            : "Start your preparation journey today!"}
        </p>
        <div className="mt-4 flex flex-wrap gap-4">
          <div className="bg-white/20 rounded-lg px-4 py-2">
            <p className="text-sm text-blue-100">Tests Taken</p>
            <p className="text-2xl font-bold">{stats.total_tests}</p>
          </div>
          <div className="bg-white/20 rounded-lg px-4 py-2">
            <p className="text-sm text-blue-100">Avg. Score</p>
            <p className="text-2xl font-bold">{stats.average_percentage}%</p>
          </div>
          <div className="bg-white/20 rounded-lg px-4 py-2">
            <p className="text-sm text-blue-100">Practice Hours</p>
            <p className="text-2xl font-bold">
              {stats.total_time_spent_hours}h
            </p>
          </div>
          <div className="bg-white/20 rounded-lg px-4 py-2">
            <p className="text-sm text-blue-100">Accuracy</p>
            <p className="text-2xl font-bold">{stats.overall_accuracy}%</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {QUICK_ACTIONS.map((action, index) => (
          <Link
            key={index}
            to={action.to}
            className="group block p-4 bg-white rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all"
          >
            <div
              className={`w-12 h-12 ${action.color} text-white rounded-lg flex items-center justify-center mb-3`}
            >
              {action.icon}
            </div>
            <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
              {action.title}
            </h3>
            <p className="text-sm text-gray-500 mt-1">{action.description}</p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Tests */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Tests</CardTitle>
            <Link
              to="/history"
              className="text-sm text-blue-600 hover:underline"
            >
              View All
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentTests.length === 0 ? (
                <div className="text-center py-6 text-gray-500">
                  <p>No tests taken yet.</p>
                  <Link to="/exams" className="text-blue-600 hover:underline">
                    Start your first test
                  </Link>
                </div>
              ) : (
                recentTests.map((test) => (
                  <div
                    key={test.id}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">
                        {test.test_name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {test.status === "generating"
                          ? "Processing..."
                          : formatRelativeTime(
                              test.completed_at || test.created_at,
                            )}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {test.status === "generating" ? (
                        <span className="flex items-center gap-2 text-sm text-blue-600 font-medium px-3 py-1 bg-blue-50 rounded-full border border-blue-200">
                          <Spinner size="sm" /> Generating
                        </span>
                      ) : test.status === "not_started" ? (
                        <Link to={`/exam/${test.test_id}/instructions`}>
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700 text-white"
                          >
                            Start Test
                          </Button>
                        </Link>
                      ) : (
                        <>
                          <span
                            className={`text-lg font-bold ${
                              test.percentage >= 70
                                ? "text-green-600"
                                : test.percentage >= 50
                                  ? "text-yellow-600"
                                  : "text-red-600"
                            }`}
                          >
                            {test.percentage}%
                          </span>
                          <Link to={`/results/${test.id}`}>
                            <Button size="sm" variant="outline">
                              Review
                            </Button>
                          </Link>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Performance Analytics */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Performance Analytics</CardTitle>
            <Link
              to="/analytics"
              className="text-sm text-blue-600 hover:underline"
            >
              Details
            </Link>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center rounded-lg bg-blue-50 p-3">
                <p className="text-2xl font-bold text-blue-600">
                  {stats.total_tests}
                </p>
                <p className="text-sm text-gray-600">Tests Taken</p>
              </div>
              <div className="text-center rounded-lg bg-green-50 p-3">
                <p className="text-2xl font-bold text-green-600">
                  {stats.average_percentage}%
                </p>
                <p className="text-sm text-gray-600">Average Score</p>
              </div>
              <div className="text-center rounded-lg bg-purple-50 p-3">
                <p className="text-2xl font-bold text-purple-600">
                  {stats.overall_accuracy}%
                </p>
                <p className="text-sm text-gray-600">Accuracy</p>
              </div>
              <div className="text-center rounded-lg bg-orange-50 p-3">
                <p className="text-2xl font-bold text-orange-600">
                  {stats.total_time_spent_hours}h
                </p>
                <p className="text-sm text-gray-600">Practice Time</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recommended Section */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended for You</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 border border-orange-200 bg-orange-50 rounded-lg">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">📚</span>
                <h4 className="font-semibold text-gray-900">
                  Practice General Awareness
                </h4>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                Your weakest area. Take a focused practice session.
              </p>
              <Button size="sm" className="w-full">
                Start Practice
              </Button>
            </div>
            <div className="p-4 border border-blue-200 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">🎯</span>
                <h4 className="font-semibold text-gray-900">Full Mock Test</h4>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                It's been 3 days since your last full test.
              </p>
              <Button size="sm" className="w-full">
                Take Test
              </Button>
            </div>
            <div className="p-4 border border-green-200 bg-green-50 rounded-lg">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">🔄</span>
                <h4 className="font-semibold text-gray-900">Review Mistakes</h4>
              </div>
              <p className="text-sm text-gray-600 mb-3">
                You have 15 marked questions to review.
              </p>
              <Button size="sm" className="w-full">
                Review Now
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
