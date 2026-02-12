// Settings Page Component
import { useState } from "react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import Button from "../../components/ui/Button";

const NOTIFICATION_SETTINGS = [
  {
    id: "email_results",
    label: "Email me test results",
    description: "Get a summary after each test",
  },
  {
    id: "email_reminders",
    label: "Practice reminders",
    description: "Remind me to practice daily",
  },
  {
    id: "email_tips",
    label: "Tips & strategies",
    description: "Receive exam tips and study strategies",
  },
  {
    id: "email_updates",
    label: "Platform updates",
    description: "New features and improvements",
  },
];

const EXAM_SETTINGS = [
  {
    id: "auto_save",
    label: "Auto-save responses",
    description: "Save answers automatically every 30 seconds",
  },
  {
    id: "sound_timer",
    label: "Timer sound alerts",
    description: "Play sound when timer reaches 5 minutes",
  },
  {
    id: "confirm_submit",
    label: "Confirm before submit",
    description: "Show confirmation dialog before submitting",
  },
  {
    id: "show_calculator",
    label: "Show calculator",
    description: "Display on-screen calculator during tests",
  },
];

export default function SettingsPage() {
  const [notifications, setNotifications] = useState({
    email_results: true,
    email_reminders: true,
    email_tips: false,
    email_updates: false,
  });

  const [examSettings, setExamSettings] = useState({
    auto_save: true,
    sound_timer: true,
    confirm_submit: true,
    show_calculator: false,
  });

  const [theme, setTheme] = useState("light");
  const [language, setLanguage] = useState("en");
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState("");

  const handleNotificationChange = (id) => {
    setNotifications((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleExamSettingChange = (id) => {
    setExamSettings((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setMessage("Settings saved successfully!");
      setTimeout(() => setMessage(""), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-1">Customize your experience</p>
      </div>

      {message && (
        <div className="p-4 bg-green-50 text-green-700 border border-green-200 rounded-lg">
          {message}
        </div>
      )}

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Theme
              </label>
              <div className="flex gap-3">
                {["light", "dark", "system"].map((option) => (
                  <button
                    key={option}
                    onClick={() => setTheme(option)}
                    className={`px-4 py-2 rounded-lg border capitalize ${
                      theme === option
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full sm:w-auto px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="en">English</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="ta">தமிழ் (Tamil)</option>
                <option value="te">తెలుగు (Telugu)</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Exam Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Exam Settings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {EXAM_SETTINGS.map((setting) => (
              <div
                key={setting.id}
                className="flex items-center justify-between"
              >
                <div>
                  <p className="font-medium text-gray-900">{setting.label}</p>
                  <p className="text-sm text-gray-500">{setting.description}</p>
                </div>
                <button
                  onClick={() => handleExamSettingChange(setting.id)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    examSettings[setting.id] ? "bg-blue-600" : "bg-gray-200"
                  }`}
                >
                  <span
                    className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      examSettings[setting.id] ? "translate-x-6" : ""
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {NOTIFICATION_SETTINGS.map((setting) => (
              <div
                key={setting.id}
                className="flex items-center justify-between"
              >
                <div>
                  <p className="font-medium text-gray-900">{setting.label}</p>
                  <p className="text-sm text-gray-500">{setting.description}</p>
                </div>
                <button
                  onClick={() => handleNotificationChange(setting.id)}
                  className={`relative w-12 h-6 rounded-full transition-colors ${
                    notifications[setting.id] ? "bg-blue-600" : "bg-gray-200"
                  }`}
                >
                  <span
                    className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${
                      notifications[setting.id] ? "translate-x-6" : ""
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-900">Clear Test History</p>
                <p className="text-sm text-gray-500">
                  Delete all your test attempts and analytics data
                </p>
              </div>
              <Button
                variant="outline"
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                Clear Data
              </Button>
            </div>
            <div className="flex items-center justify-between pt-4 border-t">
              <div>
                <p className="font-medium text-gray-900">Delete Account</p>
                <p className="text-sm text-gray-500">
                  Permanently delete your account and all data
                </p>
              </div>
              <Button
                variant="outline"
                className="text-red-600 border-red-300 hover:bg-red-50"
              >
                Delete Account
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} isLoading={isSaving}>
          Save Settings
        </Button>
      </div>
    </div>
  );
}
