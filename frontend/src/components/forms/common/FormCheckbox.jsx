// Reusable Form Checkbox Component
import { forwardRef } from "react";

const FormCheckbox = forwardRef(
  (
    {
      label,
      name,
      checked,
      onChange,
      error,
      disabled = false,
      description,
      className = "",
      ...props
    },
    ref,
  ) => {
    return (
      <div className={`space-y-1 ${className}`}>
        <label className="flex items-start gap-3 cursor-pointer group">
          <div className="flex items-center h-5">
            <input
              ref={ref}
              type="checkbox"
              id={name}
              name={name}
              checked={checked}
              onChange={onChange}
              disabled={disabled}
              className={`
                w-4 h-4 rounded border transition-colors cursor-pointer
                focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
                ${
                  error
                    ? "border-red-300 text-red-600 focus:ring-red-500"
                    : "border-gray-300 text-blue-600"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
              aria-invalid={error ? "true" : "false"}
              aria-describedby={
                error
                  ? `${name}-error`
                  : description
                    ? `${name}-desc`
                    : undefined
              }
              {...props}
            />
          </div>
          <div className="flex flex-col">
            <span
              className={`
                text-sm font-medium
                ${error ? "text-red-700" : "text-gray-700"}
                ${disabled ? "opacity-50" : "group-hover:text-gray-900"}
              `}
            >
              {label}
            </span>
            {description && (
              <span id={`${name}-desc`} className="text-sm text-gray-500">
                {description}
              </span>
            )}
          </div>
        </label>

        {error && (
          <p id={`${name}-error`} className="text-sm text-red-600 ml-7">
            {error}
          </p>
        )}
      </div>
    );
  },
);

FormCheckbox.displayName = "FormCheckbox";
export default FormCheckbox;
