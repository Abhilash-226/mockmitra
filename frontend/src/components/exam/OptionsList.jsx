// Options List Component with Tailwind CSS
import "katex/dist/katex.min.css";
import LatexText from "../ui/LatexText";

const OPTION_LABELS = ["A", "B", "C", "D", "E", "F"];

export default function OptionsList({
  options = [],
  selectedOption,
  correctOption = null,
  onSelect,
  disabled = false,
}) {
  const getOptionClass = (optionValue) => {
    const isSelected = selectedOption === optionValue;
    const isCorrect = correctOption === optionValue;
    const isIncorrect = correctOption && isSelected && !isCorrect;

    if (isCorrect) return "option option-correct";
    if (isIncorrect) return "option option-incorrect";
    if (isSelected) return "option option-selected";
    return "option";
  };

  return (
    <div className="space-y-3">
      {options.map((option, index) => {
        const optionValue = option.value || option.id || index;
        const optionText = option.text || option.label || option;
        const isSelected = selectedOption === optionValue;

        return (
          <button
            key={optionValue}
            onClick={() => !disabled && onSelect?.(optionValue)}
            disabled={disabled}
            className={`${getOptionClass(optionValue)} w-full text-left ${
              disabled ? "cursor-not-allowed" : ""
            }`}
          >
            {/* Option label (A, B, C, D) */}
            <span
              className={`option-label ${
                isSelected ? "bg-primary-500 text-white" : ""
              }`}
            >
              {OPTION_LABELS[index]}
            </span>

            {/* Option text or image */}
            <span className="flex-1 text-gray-800">
              {typeof optionText === "object" && optionText?.image ? (
                <div className="py-2">
                  <img
                    src={optionText.image}
                    alt={`Option ${OPTION_LABELS[index]}`}
                    className="max-h-32 object-contain rounded-md"
                  />
                </div>
              ) : (
                <LatexText>{optionText}</LatexText>
              )}
            </span>

            {/* Correct/Incorrect indicator */}
            {correctOption && (
              <span className="ml-2">
                {correctOption === optionValue && (
                  <svg
                    className="w-5 h-5 text-green-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
                {isSelected && correctOption !== optionValue && (
                  <svg
                    className="w-5 h-5 text-red-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
