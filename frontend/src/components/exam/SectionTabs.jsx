// Section Tabs Component with Tailwind CSS
export default function SectionTabs({
  sections = [],
  activeSection = 0,
  onSectionChange,
  sectionStats = {},
}) {
  return (
    <div className="bg-white border-b border-gray-200">
      <div className="flex gap-1 px-4 pt-2 overflow-x-auto scrollbar-hide">
        {sections.map((section, index) => {
          const isActive = index === activeSection;
          const stats = sectionStats[section.id] || {};

          return (
            <button
              key={section.id || index}
              onClick={() => onSectionChange?.(index)}
              className={
                isActive ? "section-tab-active" : "section-tab-inactive"
              }
            >
              <div className="flex items-center gap-2 whitespace-nowrap">
                <span>{section.name}</span>
                {stats.answered !== undefined && (
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded-full ${
                      isActive
                        ? "bg-primary-200 text-primary-800"
                        : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {stats.answered}/{stats.total}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
