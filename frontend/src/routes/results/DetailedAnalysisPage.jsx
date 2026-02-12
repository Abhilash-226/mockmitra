// Detailed Analysis Page
import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/Card";
import { QuestionCard, OptionsList } from "../../components/exam";
import Spinner from "../../components/ui/Spinner";
import { analyticsService } from "../../services/analyticsService";

const DEFAULT_ANALYSIS = {
  questions: [],
  topicAnalysis: [],
  timeAnalysis: {
    avgTimePerQuestion: 0,
    fastestQuestion: 0,
    slowestQuestion: 0,
    recommendedTime: 36,
  },
};

export default function DetailedAnalysisPage() {
  const { attemptId } = useParams();
  const [analysis, setAnalysis] = useState(DEFAULT_ANALYSIS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnalysis = async () => {
      try {
        setLoading(true);
        const response = await analyticsService.getAttemptAnalytics(attemptId);
        const data = response.data || response;

        // Transform data
        const questions = (data.questions || []).map((q, index) => ({
          id: q.id || q.question_id || `q-${index}`,
          number: index + 1,
          text: q.text || q.question_text || "Question text not available",
          options: q.options || [],
          correctAnswer: q.correct_answer || q.correctAnswer,
          userAnswer: q.selected_option || q.user_answer,
          topic: q.topic || "General",
          section: q.section || "General",
          difficulty: q.difficulty || "Medium",
          solution: q.solution || q.explanation || "Solution not available",
          isCorrect: q.is_correct,
        }));

        // Calculate topic analysis from responses
        const topicStats = {};
        (data.responses || []).forEach((r) => {
          const topic = r.topic || "General";
          if (!topicStats[topic]) {
            topicStats[topic] = { correct: 0, total: 0 };
          }
          topicStats[topic].total++;
          if (r.is_correct) topicStats[topic].correct++;
        });

        const topicAnalysis = Object.entries(topicStats).map(
          ([topic, stats]) => ({
            topic,
            correct: stats.correct,
            total: stats.total,
            percentage:
              stats.total > 0
                ? Math.round((stats.correct / stats.total) * 100)
                : 0,
          }),
        );

        // Calculate time analysis
        const times = (data.responses || [])
          .map((r) => r.time_spent || r.time_spent_seconds || 0)
          .filter((t) => t > 0);

        const timeAnalysis = {
          avgTimePerQuestion:
            data.average_time_per_question ||
            (times.length > 0
              ? Math.round(times.reduce((a, b) => a + b, 0) / times.length)
              : 0),
          fastestQuestion: times.length > 0 ? Math.min(...times) : 0,
          slowestQuestion: times.length > 0 ? Math.max(...times) : 0,
          recommendedTime: 36,
        };

        setAnalysis({
          questions:
            questions.length > 0 ? questions : DEFAULT_ANALYSIS.questions,
          topicAnalysis:
            topicAnalysis.length > 0
              ? topicAnalysis
              : DEFAULT_ANALYSIS.topicAnalysis,
          timeAnalysis,
        });
        setError(null);
      } catch (err) {
        console.error("Failed to fetch analysis:", err);
        setError("Failed to load analysis data");
        setAnalysis(DEFAULT_ANALYSIS);
      } finally {
        setLoading(false);
      }
    };

    if (attemptId) {
      fetchAnalysis();
    }
  }, [attemptId]);

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
      {/* Topic Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Topic-wise Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {analysis.topicAnalysis.length > 0 ? (
            <div className="space-y-4">
              {analysis.topicAnalysis.map((topic, index) => (
                <div key={index} className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {topic.topic}
                      </span>
                      <span className="text-sm text-gray-500">
                        {topic.correct}/{topic.total} ({topic.percentage}%)
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          topic.percentage >= 80
                            ? "bg-green-500"
                            : topic.percentage >= 60
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        }`}
                        style={{ width: `${topic.percentage}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">
              No topic analysis available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Time Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Time Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">
                {analysis.timeAnalysis.avgTimePerQuestion}s
              </p>
              <p className="text-sm text-blue-700">Avg per Question</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">
                {analysis.timeAnalysis.fastestQuestion}s
              </p>
              <p className="text-sm text-green-700">Fastest Answer</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">
                {analysis.timeAnalysis.slowestQuestion}s
              </p>
              <p className="text-sm text-red-700">Slowest Answer</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <p className="text-2xl font-bold text-purple-600">
                {analysis.timeAnalysis.recommendedTime}s
              </p>
              <p className="text-sm text-purple-700">Recommended Time</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Question Review */}
      <Card>
        <CardHeader>
          <CardTitle>Question Review</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {analysis.questions.length > 0 ? (
            <div className="divide-y divide-gray-200">
              {analysis.questions.map((question) => (
                <div key={question.id} className="p-6">
                  <div className="flex items-start gap-4 mb-4">
                    <span
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${
                        question.isCorrect ? "bg-green-500" : "bg-red-500"
                      }`}
                    >
                      {question.number}
                    </span>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                          {question.section}
                        </span>
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                          {question.topic}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${
                            question.difficulty === "Easy"
                              ? "bg-green-100 text-green-600"
                              : question.difficulty === "Medium"
                                ? "bg-yellow-100 text-yellow-600"
                                : "bg-red-100 text-red-600"
                          }`}
                        >
                          {question.difficulty}
                        </span>
                      </div>
                      <p className="text-gray-900">{question.text}</p>
                    </div>
                  </div>

                  <OptionsList
                    options={question.options}
                    selectedOption={question.userAnswer}
                    correctOption={question.correctAnswer}
                    showCorrect={true}
                    disabled={true}
                  />

                  {/* Solution */}
                  <div className="mt-4 p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-medium text-blue-900 mb-2">Solution</h4>
                    <p className="text-sm text-blue-800 whitespace-pre-line">
                      {question.solution}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              No question review data available
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
