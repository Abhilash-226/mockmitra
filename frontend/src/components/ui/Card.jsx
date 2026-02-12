// Card Component with Tailwind CSS
function Card({
  children,
  className = "",
  hover = false,
  padding = true,
  ...props
}) {
  const baseClass = hover ? "card-hover" : "card";
  const paddingClass = padding ? "p-6" : "";

  return (
    <div className={`${baseClass} ${paddingClass} ${className}`} {...props}>
      {children}
    </div>
  );
}

// Card subcomponents
export function CardHeader({ children, className = "" }) {
  return (
    <div className={`border-b border-gray-200 pb-4 mb-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = "" }) {
  return (
    <h3 className={`text-lg font-semibold text-gray-900 ${className}`}>
      {children}
    </h3>
  );
}

export function CardDescription({ children, className = "" }) {
  return (
    <p className={`text-sm text-gray-500 mt-1 ${className}`}>{children}</p>
  );
}

export function CardContent({ children, className = "" }) {
  return <div className={className}>{children}</div>;
}

export function CardFooter({ children, className = "" }) {
  return (
    <div className={`border-t border-gray-200 pt-4 mt-4 ${className}`}>
      {children}
    </div>
  );
}

// Named export for { Card } imports
export { Card };
export default Card;
