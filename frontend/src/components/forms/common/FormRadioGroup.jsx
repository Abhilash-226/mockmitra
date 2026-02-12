// Reusable Form Radio Group Component
import { forwardRef } from "react";

const FormRadioGroup = forwardRef(
  (
    {
      label,
      name,
      value,
      onChange,
      options = [],
      error,
      disabled = false,
      required = false,
      layout = "vertical", // 'vertical' | 'horizontal'
      className = "",
      ...props
    },
    ref,
  ) => {
    return (
      <div
        className={`space-y-2 ${className}`}
        role="radiogroup"
        aria-labelledby={`${name}-label`}
      >
        {label && (
          <p id={`${name}-label`} className="text-sm font-medium text-gray-700">
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </p>
        )}

        <div
          className={`
            ${layout === "horizontal" ? "flex flex-wrap gap-4" : "space-y-3"}
          `}
        >
          {options.map((opt, index) => (
            <label
              key={opt.value}
              className={`
                flex items-start gap-3 cursor-pointer group
                ${opt.disabled || disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
            >
              <div className="flex items-center h-5">
                <input
                  ref={index === 0 ? ref : undefined}
                  type="radio"
                  name={name}
                  value={opt.value}
                  checked={value === opt.value}
                  onChange={onChange}
                  disabled={opt.disabled || disabled}
                  className={`
                    w-4 h-4 border transition-colors cursor-pointer
                    focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                    ${
                      error
                        ? "border-red-300 text-red-600 focus:ring-red-500"
                        : "border-gray-300 text-blue-600"
                    }
                    ${opt.disabled || disabled ? "cursor-not-allowed" : ""}
                  `}
                  aria-invalid={error ? "true" : "false"}
                  {...props}
                />
              </div>
              <div className="flex flex-col">
                <span
                  className={`
                    text-sm font-medium
                    ${error ? "text-red-700" : "text-gray-700"}
                    ${opt.disabled || disabled ? "" : "group-hover:text-gray-900"}
                  `}
                >
                  {opt.label}
                </span>
                {opt.description && (
                  <span className="text-sm text-gray-500">
                    {opt.description}
                  </span>
                )}
              </div>
            </label>
          ))}
        </div>

        {error && (
          <p className="text-sm text-red-600 flex items-center gap-1">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            {error}
          </p>
        )}
      </div>
    );
  },
);

FormRadioGroup.displayName = "FormRadioGroup";
export default FormRadioGroup;
