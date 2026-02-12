// Reusable Form Input Component
import { forwardRef } from "react";

const FormInput = forwardRef(
  (
    {
      label,
      type = "text",
      name,
      value,
      onChange,
      error,
      required = false,
      disabled = false,
      placeholder,
      helperText,
      leftIcon,
      rightIcon,
      size = "md",
      className = "",
      ...props
    },
    ref,
  ) => {
    const sizes = {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2",
      lg: "px-4 py-3 text-lg",
    };

    const inputClasses = `
      block w-full rounded-lg border transition-colors
      ${sizes[size]}
      ${leftIcon ? "pl-10" : ""}
      ${rightIcon ? "pr-10" : ""}
      ${
        error
          ? "border-red-300 text-red-900 placeholder-red-300 focus:ring-red-500 focus:border-red-500"
          : "border-gray-300 focus:ring-blue-500 focus:border-blue-500"
      }
      ${disabled ? "bg-gray-100 text-gray-500 cursor-not-allowed" : "bg-white"}
      focus:outline-none focus:ring-2
      ${className}
    `;

    return (
      <div className="space-y-1">
        {label && (
          <label
            htmlFor={name}
            className="block text-sm font-medium text-gray-700"
          >
            {label}
            {required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            type={type}
            id={name}
            name={name}
            value={value}
            onChange={onChange}
            disabled={disabled}
            placeholder={placeholder}
            className={inputClasses}
            aria-invalid={error ? "true" : "false"}
            aria-describedby={
              error
                ? `${name}-error`
                : helperText
                  ? `${name}-helper`
                  : undefined
            }
            {...props}
          />

          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              {rightIcon}
            </div>
          )}
        </div>

        {error && (
          <p
            id={`${name}-error`}
            className="text-sm text-red-600 flex items-center gap-1"
          >
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

        {helperText && !error && (
          <p id={`${name}-helper`} className="text-sm text-gray-500">
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

FormInput.displayName = "FormInput";
export default FormInput;
