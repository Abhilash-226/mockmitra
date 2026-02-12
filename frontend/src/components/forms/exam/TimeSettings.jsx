// Time Settings Component
import { useEffect, useMemo, useState } from "react";

const DEFAULT_PRESETS = [15, 30, 60, 90, 120];
const FRACTION_PRESETS = [0.125, 0.25, 0.5, 0.75, 1];

const formatLabel = (minutes) => {
  if (minutes < 60) return `${minutes} min`;
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (mins === 0) return `${hrs} hr`;
  return `${hrs} hr ${mins} min`;
};

const formatPerQuestion = (minutes) => {
  if (!minutes || minutes <= 0) return "0 min";
  if (minutes >= 1) return `${minutes.toFixed(1)} min`;
  return `${Math.max(5, Math.round(minutes * 60))} sec`;
};

const buildPresetTimes = (examDuration) => {
  if (!examDuration) {
    return DEFAULT_PRESETS.map((value) => ({ value }));
  }

  const rawValues = FRACTION_PRESETS.map((fraction) =>
    Math.max(5, Math.round((examDuration * fraction) / 5) * 5),
  );
  const uniqueValues = [...new Set(rawValues)];
  return uniqueValues.map((value) => ({ value }));
};

export default function TimeSettings({
  duration,
  timerEnabled = true,
  onDurationChange,
  onTimerToggle,
  examDuration,
  examQuestionCount,
  questionCount,
}) {
  const presets = useMemo(
    () => buildPresetTimes(examDuration || duration),
    [examDuration, duration],
  );

  const [isCustom, setIsCustom] = useState(
    () => !presets.some((p) => p.value === duration),
  );
  const [customMinutes, setCustomMinutes] = useState(
    duration || examDuration || 60,
  );

  useEffect(() => {
    setIsCustom(!presets.some((p) => p.value === duration));
  }, [duration, presets]);

  useEffect(() => {
    if (isCustom) {
      setCustomMinutes(duration || examDuration || 60);
    }
  }, [duration, examDuration, isCustom]);

  const perQuestionMinutes =
    examDuration && examQuestionCount
      ? examDuration / Math.max(1, examQuestionCount)
      : null;

  const recommendedDuration =
    perQuestionMinutes && questionCount
      ? Math.max(1, Math.round(perQuestionMinutes * questionCount))
      : null;

  const handlePresetSelect = (value) => {
    setIsCustom(false);
    onDurationChange(value);
  };

  const handleCustomChange = (e) => {
    const value = Math.max(1, Math.min(300, parseInt(e.target.value) || 0));
    setCustomMinutes(value);
    onDurationChange(value);
  };

  const formatTime = (minutes) => {
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hrs === 0) return `${mins} min`;
    if (mins === 0) return `${hrs} hr`;
    return `${hrs} hr ${mins} min`;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">
          Test Duration
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={timerEnabled}
            onChange={(e) => onTimerToggle(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-600">Enable timer</span>
        </label>
      </div>

      {timerEnabled && (
        <>
          {/* Preset Options */}
          <div className="flex flex-wrap gap-2">
            {presets.map((preset) => {
              const isSelected = !isCustom && duration === preset.value;
              const isRecommended = recommendedDuration === preset.value;
              return (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => handlePresetSelect(preset.value)}
                  className={`relative px-4 py-2 rounded-lg border-2 transition-all ${
                    isSelected
                      ? "border-blue-500 bg-blue-50 text-blue-700"
                      : "border-gray-200 hover:border-gray-300 bg-white text-gray-700"
                  } ${isRecommended ? "ring-1 ring-blue-200" : ""}`}
                >
                  <span className="font-medium">
                    {formatLabel(preset.value)}
                  </span>
                  {isRecommended && (
                    <span className="absolute -top-2 right-2 text-[10px] font-semibold text-blue-600 bg-white px-1.5 py-0.5 rounded-full border border-blue-100">
                      Recommended
                    </span>
                  )}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setIsCustom(true)}
              className={`px-4 py-2 rounded-lg border-2 transition-all ${
                isCustom
                  ? "border-blue-500 bg-blue-50 text-blue-700"
                  : "border-gray-200 hover:border-gray-300 bg-white text-gray-700"
              }`}
            >
              Custom
            </button>
          </div>

          {recommendedDuration && (
            <div className="text-sm text-gray-500">
              Recommended for {questionCount} questions:{" "}
              <strong className="text-gray-700">
                {formatLabel(recommendedDuration)}
              </strong>
            </div>
          )}
          {perQuestionMinutes && (
            <div className="text-xs text-gray-400">
              Official pacing ~{formatPerQuestion(perQuestionMinutes)} per
              question
            </div>
          )}

          {/* Custom Time Input */}
          {isCustom && (
            <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min="1"
                  max="300"
                  value={customMinutes}
                  onChange={handleCustomChange}
                  className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="text-gray-600">minutes</span>
              </div>
              <div className="text-sm text-gray-500">
                = {formatTime(customMinutes)}
              </div>
            </div>
          )}

          {/* Time per Question Estimate */}
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>
              Selected duration:{" "}
              <strong className="text-gray-700">{formatTime(duration)}</strong>
            </span>
          </div>
        </>
      )}

      {!timerEnabled && (
        <div className="flex items-center gap-2 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <svg
            className="w-5 h-5 text-yellow-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span className="text-sm text-yellow-800">
            Timer disabled - Practice mode without time pressure
          </span>
        </div>
      )}
    </div>
  );
}
