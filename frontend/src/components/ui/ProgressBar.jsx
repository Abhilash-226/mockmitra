// Progress Bar Component with Tailwind CSS
const colorVariants = {
  primary: "bg-primary-600",
  success: "bg-green-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
};

export default function ProgressBar({
  value,
  max = 100,
  showLabel = false,
  color = "primary",
  size = "md",
  className = "",
}) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  const colorClass = colorVariants[color] || colorVariants.primary;

  const sizeClasses = {
    sm: "h-1",
    md: "h-2",
    lg: "h-3",
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size] || sizeClasses.md}`}
      >
        <div
          className={`${colorClass} ${sizeClasses[size] || sizeClasses.md} rounded-full transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between mt-1">
          <span className="text-sm text-gray-600">
            {Math.round(percentage)}%
          </span>
          <span className="text-sm text-gray-500">
            {value}/{max}
          </span>
        </div>
      )}
    </div>
  );
}
