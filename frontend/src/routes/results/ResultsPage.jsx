// Results Page Component - Shows list of all completed tests
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Badge from "../../components/ui/Badge";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";

const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getScoreColor = (percentage) => {
  if (percentage >= 80) return "text-green-600";
  if (percentage >= 60) return "text-yellow-600";
  return "text-red-600";
};

export default function ResultsPage() {
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState({
    testsTaken: 0,
    bestScore: 0,
    average: 0,
    bestRank: "-",
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        const response = await analyticsService.getDashboard();
        const data = response.data || response;

        // Transform recent_attempts to results format
        const transformedResults = (data.recent_attempts || []).map(
          (attempt, index) => ({
            id: attempt.id || `result-${index}`,
            testName: attempt.test_name || `Test ${index + 1}`,
            date: attempt.completed_at || new Date().toISOString(),
            score: attempt.score || 0,
            maxScore: attempt.max_score || 200,
            percentage: attempt.percentage || 0,
            duration: attempt.time_taken
              ? `${Math.round(attempt.time_taken / 60)} min`
              : "N/A",
            rank: attempt.rank || null,
            totalAttempts: attempt.total_participants || null,
            sections: attempt.sections || [],
          }),
        );

        setResults(transformedResults);

        // Calculate stats
        const percentages = transformedResults.map((r) => r.percentage);
        const ranks = transformedResults
          .filter((r) => r.rank)
          .map((r) => r.rank);

        setStats({
          testsTaken: data.total_tests || transformedResults.length,
          bestScore: percentages.length > 0 ? Math.max(...percentages) : 0,
          average:
            data.average_percentage ||
            (percentages.length > 0
              ? Math.round(
                  percentages.reduce((a, b) => a + b, 0) / percentages.length,
                )
              : 0),
          bestRank: ranks.length > 0 ? `#${Math.min(...ranks)}` : "-",
        });

        setError(null);
      } catch (err) {
        console.error("Failed to fetch results:", err);
        setError("Failed to load test results");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, []);

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
          <h1 className="text-2xl font-bold text-gray-900">Test Results</h1>
          <p className="text-gray-600 mt-1">
            Review your performance across all tests
          </p>
        </div>
        <Link to="/analytics">
          <Button variant="outline">
            <svg
              className="w-4 h-4 mr-2"
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
            View Analytics
          </Button>
        </Link>
      </div>

      {/* Results Summary Cards */}
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
              {stats.bestScore}%
            </p>
            <p className="text-sm text-gray-500">Best Score</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-purple-600">
              {stats.average}%
            </p>
            <p className="text-sm text-gray-500">Average</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-orange-600">
              {stats.bestRank}
            </p>
            <p className="text-sm text-gray-500">Best Rank</p>
          </CardContent>
        </Card>
      </div>

      {/* Results List */}
      {results.length > 0 ? (
        <div className="space-y-4">
          {results.map((result) => (
            <Card key={result.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {result.testName}
                      </h3>
                      {result.rank && (
                        <Badge variant="info">Rank #{result.rank}</Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                      <span>📅 {formatDate(result.date)}</span>
                      <span>⏱️ Duration: {result.duration}</span>
                      {result.totalAttempts && (
                        <span>
                          👥 {result.totalAttempts.toLocaleString()} attempts
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    {/* Section Scores */}
                    {result.sections.length > 0 && (
                      <div className="hidden md:flex items-center gap-2">
                        {result.sections.map((section, idx) => (
                          <div
                            key={idx}
                            className="text-center px-3 py-1 bg-gray-50 rounded"
                          >
                            <p className="text-xs text-gray-500">
                              {section.name}
                            </p>
                            <p className="text-sm font-semibold">
                              {section.score}/{section.maxScore}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Total Score */}
                    <div className="text-center">
                      <p
                        className={`text-2xl font-bold ${getScoreColor(result.percentage)}`}
                      >
                        {result.percentage}%
                      </p>
                      <p className="text-xs text-gray-500">
                        {result.score}/{result.maxScore}
                      </p>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <Link to={`/results/${result.id}`}>
                        <Button size="sm">View Details</Button>
                      </Link>
                      <Link to={`/results/${result.id}/analysis`}>
                        <Button size="sm" variant="outline">
                          Analysis
                        </Button>
                      </Link>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
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
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
            />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No test results yet
          </h3>
          <p className="text-gray-500 mb-4">
            Complete your first test to see results here
          </p>
          <Link to="/exams">
            <Button>Take a Test</Button>
          </Link>
        </div>
      )}
    </div>
  );
}
