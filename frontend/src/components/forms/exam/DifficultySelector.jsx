// Difficulty Selector Component
const DIFFICULTY_OPTIONS = [
  {
    value: "easy",
    label: "Easy",
    description: "Basic concepts, ideal for beginners",
    color: "green",
    icon: (
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
          d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
  },
  {
    value: "medium",
    label: "Medium",
    description: "Moderate difficulty, previous year level",
    color: "yellow",
    icon: (
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
          d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
        />
      </svg>
    ),
  },
  {
    value: "hard",
    label: "Hard",
    description: "Challenging questions for advanced prep",
    color: "red",
    icon: (
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
          d="M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z"
        />
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.879 16.121A3 3 0 1012.015 11L11 14H9c0 .768.293 1.536.879 2.121z"
        />
      </svg>
    ),
  },
  {
    value: "mixed",
    label: "Mixed",
    description: "Balanced mix of all difficulty levels",
    color: "blue",
    icon: (
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
          d="M4 6h16M4 10h16M4 14h16M4 18h16"
        />
      </svg>
    ),
  },
];

const COLOR_CLASSES = {
  green: {
    selected: "border-green-500 bg-green-50 text-green-700",
    icon: "text-green-500",
    ring: "ring-green-500",
  },
  yellow: {
    selected: "border-yellow-500 bg-yellow-50 text-yellow-700",
    icon: "text-yellow-500",
    ring: "ring-yellow-500",
  },
  red: {
    selected: "border-red-500 bg-red-50 text-red-700",
    icon: "text-red-500",
    ring: "ring-red-500",
  },
  blue: {
    selected: "border-blue-500 bg-blue-50 text-blue-700",
    icon: "text-blue-500",
    ring: "ring-blue-500",
  },
};

export default function DifficultySelector({ value, onChange }) {
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Difficulty Level
      </label>
      <div className="grid grid-cols-2 gap-3">
        {DIFFICULTY_OPTIONS.map((option) => {
          const isSelected = value === option.value;
          const colors = COLOR_CLASSES[option.color];

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={`relative flex items-start gap-3 p-4 rounded-lg border-2 transition-all text-left ${
                isSelected
                  ? colors.selected
                  : "border-gray-200 hover:border-gray-300 bg-white"
              }`}
            >
              <div
                className={`flex-shrink-0 ${isSelected ? colors.icon : "text-gray-400"}`}
              >
                {option.icon}
              </div>
              <div>
                <p
                  className={`font-medium ${isSelected ? "" : "text-gray-900"}`}
                >
                  {option.label}
                </p>
                <p
                  className={`text-xs mt-0.5 ${isSelected ? "opacity-75" : "text-gray-500"}`}
                >
                  {option.description}
                </p>
              </div>
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <svg
                    className={`w-5 h-5 ${colors.icon}`}
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
    </div>
  );
}
