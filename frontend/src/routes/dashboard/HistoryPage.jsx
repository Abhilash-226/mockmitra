// History Page Component
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";

export default function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState({
    totalTests: 0,
    avgScore: 0,
    accuracy: 0,
    practiceTime: "0h",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const response = await analyticsService.getDashboard();
        const data = response.data || response;

        // Extract history from dashboard data
        const testHistory = (data.recent_attempts || []).map(
          (attempt, index) => ({
            id: attempt.id || attempt._id || `attempt-${index}`,
            examName: attempt.test_name || `Attempt ${index + 1}`,
            date: attempt.completed_at || new Date().toISOString(),
            score: attempt.score ?? 0,
            percentage: attempt.percentage ?? 0,
          }),
        );

        setHistory(testHistory);

        // Set stats from dashboard data
        setStats({
          totalTests: data.total_tests || testHistory.length,
          avgScore: data.average_percentage || data.average_score || 0,
          accuracy: data.overall_accuracy || 0,
          practiceTime: formatPracticeTime(data.total_time_spent_hours),
        });

        setError(null);
      } catch (err) {
        console.error("Failed to fetch history:", err);
        setError("Failed to load test history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const formatPracticeTime = (hours) => {
    if (!hours) return "0h";
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    if (wholeHours === 0) return `${minutes}m`;
    if (minutes === 0) return `${wholeHours}h`;
    return `${wholeHours}h ${minutes}m`;
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
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-200">
              {history.map((test) => (
                <div
                  key={test.id}
                  className="p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">
                        {test.examName}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {new Date(test.date).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    <div className="flex items-center gap-6">
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
                          View Details
                        </button>
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
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
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors">
            Take a Test
          </button>
        </div>
      )}
    </div>
  );
}
