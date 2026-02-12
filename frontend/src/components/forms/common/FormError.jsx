// Form Error Display Component
export default function FormError({ message, className = "" }) {
  if (!message) return null;

  return (
    <div
      className={`flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 ${className}`}
      role="alert"
    >
      <svg
        className="w-5 h-5 text-red-500 flex-shrink-0"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
          clipRule="evenodd"
        />
      </svg>
      <span className="text-sm text-red-700">{message}</span>
    </div>
  );
}

// Success Message Component
export function FormSuccess({ message, className = "" }) {
  if (!message) return null;

  return (
    <div
      className={`flex items-center gap-2 p-3 rounded-lg bg-green-50 border border-green-200 ${className}`}
      role="alert"
    >
      <svg
        className="w-5 h-5 text-green-500 flex-shrink-0"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
          clipRule="evenodd"
        />
      </svg>
      <span className="text-sm text-green-700">{message}</span>
    </div>
  );
}
