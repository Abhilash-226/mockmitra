// Topic Selector Component - Checkbox tree for topics
import { useState } from "react";

export default function TopicSelector({
  sections = [],
  selectedTopics = [],
  onTopicChange,
}) {
  const [expandedSections, setExpandedSections] = useState(
    sections.map((s) => s.id),
  );

  const toggleSection = (sectionId) => {
    setExpandedSections((prev) =>
      prev.includes(sectionId)
        ? prev.filter((id) => id !== sectionId)
        : [...prev, sectionId],
    );
  };

  const isSectionSelected = (section) => {
    return section.topics?.every((topic) => selectedTopics.includes(topic.id));
  };

  const isSectionPartiallySelected = (section) => {
    const selectedCount = section.topics?.filter((topic) =>
      selectedTopics.includes(topic.id),
    ).length;
    return selectedCount > 0 && selectedCount < section.topics?.length;
  };

  const handleSectionToggle = (section) => {
    const topicIds = section.topics?.map((t) => t.id) || [];
    if (isSectionSelected(section)) {
      // Unselect all topics in section
      onTopicChange(selectedTopics.filter((id) => !topicIds.includes(id)));
    } else {
      // Select all topics in section
      const newSelected = new Set([...selectedTopics, ...topicIds]);
      onTopicChange(Array.from(newSelected));
    }
  };

  const handleTopicToggle = (topicId) => {
    if (selectedTopics.includes(topicId)) {
      onTopicChange(selectedTopics.filter((id) => id !== topicId));
    } else {
      onTopicChange([...selectedTopics, topicId]);
    }
  };

  const selectAll = () => {
    const allTopicIds = sections.flatMap(
      (s) => s.topics?.map((t) => t.id) || [],
    );
    onTopicChange(allTopicIds);
  };

  const clearAll = () => {
    onTopicChange([]);
  };

  return (
    <div className="space-y-4">
      {/* Header with Select All / Clear */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">
          {selectedTopics.length} topic{selectedTopics.length !== 1 ? "s" : ""}{" "}
          selected
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={selectAll}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Select All
          </button>
          <span className="text-gray-300">|</span>
          <button
            type="button"
            onClick={clearAll}
            className="text-sm text-gray-600 hover:text-gray-700 font-medium"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Sections */}
      <div className="border border-gray-200 rounded-lg divide-y divide-gray-200 max-h-80 overflow-y-auto">
        {sections.map((section) => (
          <div key={section.id} className="bg-white">
            {/* Section Header */}
            <div
              className="flex items-center gap-3 px-4 py-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => toggleSection(section.id)}
            >
              <input
                type="checkbox"
                checked={isSectionSelected(section)}
                ref={(el) => {
                  if (el)
                    el.indeterminate = isSectionPartiallySelected(section);
                }}
                onChange={(e) => {
                  e.stopPropagation();
                  handleSectionToggle(section);
                }}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="flex-1 font-medium text-gray-900">
                {section.name}
              </span>
              <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                {section.topics?.length || 0} topics
              </span>
              <svg
                className={`w-5 h-5 text-gray-400 transition-transform ${
                  expandedSections.includes(section.id) ? "rotate-180" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>

            {/* Topics */}
            {expandedSections.includes(section.id) && section.topics && (
              <div className="px-4 py-2 space-y-2 bg-white">
                {section.topics.map((topic) => (
                  <label
                    key={topic.id}
                    className="flex items-center gap-3 py-1.5 px-2 rounded hover:bg-gray-50 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedTopics.includes(topic.id)}
                      onChange={() => handleTopicToggle(topic.id)}
                      className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 flex-1">
                      {topic.name}
                    </span>
                    {topic.questionCount && (
                      <span className="text-xs text-gray-400">
                        {topic.questionCount} Q
                      </span>
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {sections.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No topics available
        </div>
      )}
    </div>
  );
}
