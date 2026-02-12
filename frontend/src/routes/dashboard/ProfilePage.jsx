// Profile Page Component
import { useEffect, useState } from "react";
import { useAuthStore } from "../../store/useAuthStore";
import { ProfileForm } from "../../components/forms";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import { analyticsService } from "../../services/analyticsService";

export default function ProfilePage() {
  const { user, updateUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [stats, setStats] = useState({
    testsTaken: 0,
    bestScore: 0,
    avgScore: 0,
    accuracy: 0,
    totalQuestions: 0,
    practiceTime: "0h",
  });
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setStatsLoading(true);
        const response = await analyticsService.getDashboard();
        const data = response.data || response;
        const attempts = data.recent_attempts || [];
        const bestScore = attempts.length
          ? Math.max(
              ...attempts.map(
                (attempt) => attempt.percentage ?? attempt.score ?? 0,
              ),
            )
          : 0;

        setStats({
          testsTaken: data.total_tests || attempts.length,
          bestScore,
          avgScore: data.average_percentage || data.average_score || 0,
          accuracy: data.overall_accuracy || 0,
          totalQuestions: data.total_questions_attempted || 0,
          practiceTime: formatPracticeTime(data.total_time_spent_hours),
        });
        setStatsError(null);
      } catch (error) {
        console.error("Failed to fetch profile stats:", error);
        setStatsError("Unable to load stats right now.");
      } finally {
        setStatsLoading(false);
      }
    };

    fetchStats();
  }, []);

  const formatPracticeTime = (hours) => {
    if (!hours) return "0h";
    const wholeHours = Math.floor(hours);
    const minutes = Math.round((hours - wholeHours) * 60);
    if (wholeHours === 0) return `${minutes}m`;
    if (minutes === 0) return `${wholeHours}h`;
    return `${wholeHours}h ${minutes}m`;
  };

  const handleSubmit = async (formData) => {
    setIsLoading(true);
    setMessage({ type: "", text: "" });

    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      updateUser(formData);
      setMessage({ type: "success", text: "Profile updated successfully!" });
    } catch (error) {
      setMessage({ type: "error", text: "Failed to update profile." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
        <p className="text-gray-600 mt-1">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
            </CardHeader>
            <CardContent>
              {message.text && (
                <div
                  className={`mb-4 p-3 rounded-lg ${
                    message.type === "success"
                      ? "bg-green-50 text-green-700 border border-green-200"
                      : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  {message.text}
                </div>
              )}
              <ProfileForm
                initialData={{
                  name: user?.name || "",
                  email: user?.email || "",
                  phone: user?.phone || "",
                  targetExam: user?.targetExam || "",
                }}
                onSubmit={handleSubmit}
                isLoading={isLoading}
              />
            </CardContent>
          </Card>
        </div>

        {/* Stats & Achievements */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Your Stats</CardTitle>
            </CardHeader>
            <CardContent>
              {statsLoading ? (
                <p className="text-sm text-gray-500">Loading stats...</p>
              ) : statsError ? (
                <p className="text-sm text-red-600">{statsError}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Total Tests</span>
                    <span className="font-semibold">{stats.testsTaken}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Best Score</span>
                    <span className="font-semibold text-green-600">
                      {stats.bestScore}%
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Avg. Score</span>
                    <span className="font-semibold">{stats.avgScore}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Accuracy</span>
                    <span className="font-semibold">{stats.accuracy}%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Questions Attempted</span>
                    <span className="font-semibold">
                      {stats.totalQuestions}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Practice Time</span>
                    <span className="font-semibold">{stats.practiceTime}</span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Achievements */}
          <Card>
            <CardHeader>
              <CardTitle>Achievements</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="p-4 bg-gray-50 border border-dashed border-gray-200 rounded-lg text-center text-sm text-gray-600">
                Skill badges will appear here once analytics-based achievements
                are enabled.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
