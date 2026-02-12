// Spinner/Loader Component with Tailwind CSS
const sizes = {
  sm: "w-4 h-4",
  md: "w-8 h-8",
  lg: "w-12 h-12",
  xl: "w-16 h-16",
};

export default function Spinner({
  size = "md",
  className = "",
  color = "primary",
}) {
  const sizeClass = sizes[size] || sizes.md;
  const colorClass = color === "white" ? "border-white" : "border-primary-600";

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div
        className={`${sizeClass} ${colorClass} border-2 border-t-transparent rounded-full animate-spin`}
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}

// Full page loading spinner
export function PageLoader() {
  return (
    <div className="fixed inset-0 bg-white/80 flex items-center justify-center z-50">
      <div className="text-center">
        <Spinner size="xl" />
        <p className="mt-4 text-gray-600 font-medium">Loading...</p>
      </div>
    </div>
  );
}
