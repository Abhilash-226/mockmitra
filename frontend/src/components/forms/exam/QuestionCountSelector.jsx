// Question Count Selector Component
import { useEffect, useMemo, useState } from "react";

const PRESETS = [
  {
    id: "quick",
    label: "Quick Practice",
    questions: 10,
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
          d="M13 10V3L4 14h7v7l9-11h-7z"
        />
      </svg>
    ),
  },
  {
    id: "mini",
    label: "Mini Test",
    questions: 25,
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
  },
  {
    id: "standard",
    label: "Standard Test",
    questions: 50,
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
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
        />
      </svg>
    ),
  },
  {
    id: "full",
    label: "Full Exam",
    questions: 100,
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
          d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
        />
      </svg>
    ),
  },
];

const formatDurationLabel = (minutes) => {
  if (!minutes || minutes <= 0) return "0m";
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hrs > 0 && mins > 0) return `${hrs}h ${mins}m`;
  if (hrs > 0) return `${hrs}h`;
  return `${mins}m`;
};

export default function QuestionCountSelector({
  value,
  max = 200,
  onChange,
  examDuration,
  examQuestionCount,
}) {
  const dynamicPresets = useMemo(() => {
    const list = [...PRESETS];

    if (examQuestionCount && examQuestionCount <= max) {
      const fullIndex = list.findIndex((preset) => preset.id === "full");

      if (fullIndex >= 0) {
        list[fullIndex] = {
          ...list[fullIndex],
          label: "Full Exam",
          questions: examQuestionCount,
          description: "Official blueprint",
        };
      } else {
        list.push({
          id: "full-exam",
          label: "Full Exam",
          questions: examQuestionCount,
          description: "Official blueprint",
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
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          ),
        });
      }
    }

    return list.sort((a, b) => a.questions - b.questions);
  }, [examQuestionCount, max]);

  const [isCustom, setIsCustom] = useState(
    !dynamicPresets.some((p) => p.questions === value),
  );

  useEffect(() => {
    const matchesPreset = dynamicPresets.some(
      (preset) => preset.questions === value,
    );
    if (!matchesPreset && !isCustom) {
      setIsCustom(true);
    }
  }, [dynamicPresets, value, isCustom]);

  const perQuestionMinutes =
    examDuration && examQuestionCount
      ? examDuration / Math.max(1, examQuestionCount)
      : null;

  const officialDurationLabel = examDuration
    ? formatDurationLabel(Math.max(1, examDuration))
    : null;

  const handlePresetSelect = (questions) => {
    setIsCustom(false);
    onChange(Math.min(questions, max));
  };

  const handleCustomChange = (e) => {
    const newValue = Math.max(1, Math.min(max, parseInt(e.target.value) || 0));
    onChange(newValue);
  };

  const handleSliderChange = (e) => {
    onChange(parseInt(e.target.value));
  };

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Number of Questions
      </label>

      {(examQuestionCount || examDuration) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {examQuestionCount && (
            <div className="flex items-center gap-3 p-3 border border-blue-100 rounded-lg bg-blue-50/60">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold">
                {examQuestionCount}
              </div>
              <div className="text-sm">
                <p className="text-gray-900 font-semibold">
                  Official question bank
                </p>
                <p className="text-gray-500">Auto-limited to blueprint</p>
              </div>
            </div>
          )}
          {examDuration && (
            <div className="flex items-center gap-3 p-3 border border-indigo-100 rounded-lg bg-indigo-50/60">
              <div className="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 font-semibold">
                {officialDurationLabel}
              </div>
              <div className="text-sm">
                <p className="text-gray-900 font-semibold">
                  Official time limit
                </p>
                <p className="text-gray-500">{examDuration} minutes total</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Presets */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {dynamicPresets.map((preset) => {
          const isDisabled = preset.questions > max;
          const isSelected = !isCustom && value === preset.questions;
          const estimatedDuration = perQuestionMinutes
            ? Math.max(1, Math.round(preset.questions * perQuestionMinutes))
            : null;
          const description = estimatedDuration
            ? `~${formatDurationLabel(estimatedDuration)}`
            : null;

          return (
            <button
              key={preset.id}
              type="button"
              onClick={() =>
                !isDisabled && handlePresetSelect(preset.questions)
              }
              disabled={isDisabled}
              className={`relative flex flex-col items-center gap-2 p-4 rounded-lg border-2 transition-all ${
                isSelected
                  ? "border-blue-500 bg-blue-50"
                  : isDisabled
                    ? "border-gray-100 bg-gray-50 opacity-50 cursor-not-allowed"
                    : "border-gray-200 hover:border-gray-300 bg-white"
              }`}
            >
              <div className={isSelected ? "text-blue-600" : "text-gray-400"}>
                {preset.icon}
              </div>
              <div className="text-center">
                <p
                  className={`font-semibold ${isSelected ? "text-blue-700" : "text-gray-900"}`}
                >
                  {preset.questions}Q
                </p>
                <p className="text-xs text-gray-500">{preset.label}</p>
                {description && (
                  <p className="text-xs text-gray-400">{description}</p>
                )}
              </div>
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <svg
                    className="w-4 h-4 text-blue-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Custom Option */}
      <div className="border-t pt-4">
        <label className="flex items-center gap-2 mb-3 cursor-pointer">
          <input
            type="checkbox"
            checked={isCustom}
            onChange={(e) => setIsCustom(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">
            Custom count
          </span>
        </label>

        {isCustom && (
          <div className="space-y-3 pl-6">
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="1"
                max={max}
                value={value}
                onChange={handleSliderChange}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              />
              <input
                type="number"
                min="1"
                max={max}
                value={value}
                onChange={handleCustomChange}
                className="w-20 px-3 py-2 border border-gray-300 rounded-lg text-center focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex justify-between text-xs text-gray-400">
              <span>1</span>
              <span>{max} (max available)</span>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
        <svg
          className="w-5 h-5 text-blue-600"
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
        <span className="text-sm text-gray-700">
          Selected: <strong className="text-blue-600">{value} questions</strong>
          {perQuestionMinutes && value > 0 && (
            <span className="ml-2 text-xs text-gray-500">
              (~
              {formatDurationLabel(
                Math.max(1, Math.round(value * perQuestionMinutes)),
              )}
              )
            </span>
          )}
        </span>
      </div>
    </div>
  );
}
