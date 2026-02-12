// Question Legend Component with Tailwind CSS
const legendItems = [
  { color: "bg-gray-100 border-gray-300", label: "Not Visited" },
  { color: "bg-red-100 border-red-300", label: "Not Answered" },
  { color: "bg-green-100 border-green-500", label: "Answered" },
  { color: "bg-purple-100 border-purple-500", label: "Marked for Review" },
  {
    color:
      "bg-purple-100 border-purple-500 ring-2 ring-green-500 ring-offset-1",
    label: "Answered & Marked",
  },
];

export default function QuestionLegend({ compact = false }) {
  if (compact) {
    return (
      <div className="flex flex-wrap gap-3 text-xs">
        {legendItems.map((item, index) => (
          <div key={index} className="flex items-center gap-1.5">
            <span className={`w-3 h-3 rounded border ${item.color}`} />
            <span className="text-gray-600">{item.label}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="p-4 bg-gray-50 rounded-lg">
      <h4 className="text-sm font-semibold text-gray-700 mb-3">
        Question Status Legend
      </h4>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {legendItems.map((item, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className={`w-6 h-6 rounded-lg border-2 ${item.color}`} />
            <span className="text-sm text-gray-600">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
