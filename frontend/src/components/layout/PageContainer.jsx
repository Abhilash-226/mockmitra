// Page Container Component - Wrapper for consistent page layout
import { useEffect } from "react";

const VARIANTS = {
  default: "pt-16", // Account for fixed navbar
  withSidebar: "pt-16 pl-64", // Account for navbar + sidebar
  withCollapsedSidebar: "pt-16 pl-16", // Account for navbar + collapsed sidebar
  fullWidth: "pt-16 px-0",
  centered: "pt-16 flex items-center justify-center min-h-screen",
  exam: "pt-0", // No navbar during exam
};

const WIDTHS = {
  default: "max-w-7xl",
  narrow: "max-w-3xl",
  wide: "max-w-screen-2xl",
  full: "max-w-full",
};

export default function PageContainer({
  children,
  className = "",
  variant = "default",
  width = "default",
  noPadding = false,
  title,
  description,
}) {
  // Update document title
  useEffect(() => {
    if (title) {
      document.title = `${title} | MockMitra`;
    }
    return () => {
      document.title = "MockMitra";
    };
  }, [title]);

  return (
    <main
      className={`min-h-screen bg-gray-50 ${VARIANTS[variant] || VARIANTS.default} ${className}`}
    >
      <div
        className={`mx-auto ${WIDTHS[width] || WIDTHS.default} ${noPadding ? "" : "px-4 sm:px-6 lg:px-8 py-8"}`}
      >
        {/* Page Header */}
        {(title || description) && (
          <div className="mb-8">
            {title && (
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                {title}
              </h1>
            )}
            {description && <p className="mt-2 text-gray-600">{description}</p>}
          </div>
        )}

        {/* Page Content */}
        {children}
      </div>
    </main>
  );
}

// Specialized containers for common layouts
export function DashboardContainer({
  children,
  title,
  description,
  className = "",
}) {
  return (
    <PageContainer
      title={title}
      description={description}
      className={className}
    >
      {children}
    </PageContainer>
  );
}

export function AuthContainer({ children, className = "" }) {
  return (
    <PageContainer variant="centered" width="narrow" className={className}>
      <div className="w-full max-w-md">{children}</div>
    </PageContainer>
  );
}

export function ExamContainer({ children, className = "" }) {
  return (
    <main className={`min-h-screen bg-gray-100 ${className}`}>{children}</main>
  );
}
