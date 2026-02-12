// Results Summary Page
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import ProgressBar from "../../components/ui/ProgressBar";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";

const DEFAULT_RESULTS = {
  examName: "Test",
  date: new Date().toISOString(),
  timeTaken: "0:00",
  totalTime: "60:00",
  score: 0,
  maxScore: 200,
  percentage: 0,
  rank: "-",
  totalParticipants: 0,
  correct: 0,
  incorrect: 0,
  skipped: 0,
  total: 0,
  accuracy: 0,
  sectionWise: [],
};

export default function ResultsSummaryPage() {
  const { attemptId } = useParams();
  const [results, setResults] = useState(DEFAULT_RESULTS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true);
        const response = await analyticsService.getAttemptAnalytics(attemptId);
        const data = response.data || response;

        // Transform data to match the component format
        const transformedResults = {
          examName: data.test_name || data.exam_name || "Test",
          date: data.completed_at || new Date().toISOString(),
          timeTaken: formatTime(data.time_taken_seconds),
          totalTime: data.total_time ? formatTime(data.total_time) : "60:00",
          score: data.score || 0,
          maxScore: data.max_score || 200,
          percentage:
            data.percentage ||
            Math.round((data.score / (data.max_score || 200)) * 100) ||
            0,
          rank: data.rank || "-",
          totalParticipants: data.total_participants || 0,
          correct: data.correct || data.correct_answers || 0,
          incorrect: data.wrong || data.wrong_answers || 0,
          skipped: data.skipped || 0,
          total:
            data.total_questions ||
            data.correct + data.wrong + data.skipped ||
            0,
          accuracy:
            data.accuracy ||
            (data.correct && data.correct + data.wrong > 0
              ? Math.round(
                  (data.correct / (data.correct + data.wrong)) * 1000,
                ) / 10
              : 0),
          sectionWise: (data.section_results || []).map((section) => ({
            name: section.name || section.section_name,
            correct: section.correct || section.correct_answers || 0,
            incorrect: section.wrong || section.wrong_answers || 0,
            skipped: section.skipped || 0,
            total: section.total || section.total_questions || 0,
            score: section.score || 0,
          })),
        };

        setResults(transformedResults);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch results:", err);
        setError("Failed to load results");
        setResults(DEFAULT_RESULTS);
      } finally {
        setLoading(false);
      }
    };

    if (attemptId) {
      fetchResults();
    }
  }, [attemptId]);

  const formatTime = (seconds) => {
    if (!seconds) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const getScoreColor = (percentage) => {
    if (percentage >= 80) return "text-green-600";
    if (percentage >= 60) return "text-yellow-600";
    return "text-red-600";
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
      {/* Score Card */}
      <Card className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
        <CardContent className="p-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="text-center md:text-left mb-6 md:mb-0">
              <h2 className="text-lg opacity-90">Your Score</h2>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-6xl font-bold">{results.score}</span>
                <span className="text-2xl opacity-75">
                  / {results.maxScore}
                </span>
              </div>
              <p className="text-lg mt-2 opacity-90">
                {results.percentage}% • {results.accuracy}% Accuracy
              </p>
            </div>

            <div className="flex gap-8">
              <div className="text-center">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2">
                  <span className="text-2xl font-bold">
                    {results.rank !== "-" ? `#${results.rank}` : "-"}
                  </span>
                </div>
                <p className="text-sm opacity-75">All India Rank</p>
              </div>
              <div className="text-center">
                <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center mb-2">
                  <span className="text-xl font-bold">{results.timeTaken}</span>
                </div>
                <p className="text-sm opacity-75">Time Taken</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-green-600">
              {results.correct}
            </p>
            <p className="text-sm text-green-700">Correct</p>
          </CardContent>
        </Card>
        <Card className="bg-red-50 border-red-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-red-600">
              {results.incorrect}
            </p>
            <p className="text-sm text-red-700">Incorrect</p>
          </CardContent>
        </Card>
        <Card className="bg-gray-50 border-gray-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-gray-600">
              {results.skipped}
            </p>
            <p className="text-sm text-gray-700">Skipped</p>
          </CardContent>
        </Card>
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">{results.total}</p>
            <p className="text-sm text-blue-700">Total</p>
          </CardContent>
        </Card>
      </div>

      {/* Section-wise Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Section-wise Performance</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {results.sectionWise.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {results.sectionWise.map((section, index) => (
                <div key={index} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium text-gray-900">
                      {section.name}
                    </h3>
                    <span
                      className={`font-bold ${getScoreColor(section.total > 0 ? (section.correct / section.total) * 100 : 0)}`}
                    >
                      {section.score} / {section.total * 2}
                    </span>
                  </div>
                  <ProgressBar
                    value={section.correct}
                    max={section.total || 1}
                    color="success"
                    size="sm"
                  />
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span className="text-green-600">
                      ✓ {section.correct} correct
                    </span>
                    <span className="text-red-600">
                      ✗ {section.incorrect} incorrect
                    </span>
                    <span className="text-gray-500">
                      ○ {section.skipped} skipped
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-6">
              No section-wise data available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex flex-wrap items-center justify-center gap-4">
        <Link to={`/results/${attemptId}/analysis`}>
          <Button variant="primary" size="lg">
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
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            View Detailed Analysis
          </Button>
        </Link>
        <Link to="/dashboard/exams">
          <Button variant="outline" size="lg">
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Take Another Test
          </Button>
        </Link>
        <Button variant="ghost" size="lg">
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
              d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"
            />
          </svg>
          Share Result
        </Button>
      </div>
    </div>
  );
}
