/**
 * PYQ Papers Page - Browse and attempt past year question papers
 */
import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { pyqService } from "../../services/pyqService";
import { setPageSeo } from "../../utils/seo";
import Button from "../../components/ui/Button";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
} from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";

export default function PYQPapersPage() {
  const navigate = useNavigate();
  const [papers, setPapers] = useState([]);
  const [years, setYears] = useState([]);
  const [selectedYear, setSelectedYear] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setPageSeo({
      title: "TS EAPCET Previous Year Papers",
      description:
        "Practice TS EAPCET previous year question papers with exam-like CBT interface and detailed performance tracking.",
      path: "/pyq-papers",
    });
  }, []);

  useEffect(() => {
    fetchPapers();
  }, []);

  const fetchPapers = async () => {
    try {
      setLoading(true);
      const papersData = await pyqService.getPapers("ts_eamcet");
      const fetchedPapers = papersData.papers || [];
      setPapers(fetchedPapers);

      // Derive year filters from papers list to avoid an extra API round-trip.
      const yearsFromPapers = [
        ...new Set(fetchedPapers.map((paper) => paper.year)),
      ]
        .filter((year) => Number.isFinite(year))
        .map((year) => ({ year }));
      setYears(yearsFromPapers);
    } catch (err) {
      console.error("Failed to fetch PYQ papers:", err);
      setError(err.message || "Failed to load papers");
    } finally {
      setLoading(false);
    }
  };

  // Group papers by year
  const papersByYear = useMemo(() => {
    const grouped = {};
    papers.forEach((paper) => {
      const year = paper.year;
      if (!grouped[year]) {
        grouped[year] = [];
      }
      grouped[year].push(paper);
    });
    // Sort papers within each year by shift
    Object.keys(grouped).forEach((year) => {
      grouped[year].sort((a, b) => a.shift - b.shift);
    });
    return grouped;
  }, [papers]);

  // Filter papers by selected year
  const filteredPapers = useMemo(() => {
    if (!selectedYear) return papersByYear;
    return { [selectedYear]: papersByYear[selectedYear] || [] };
  }, [papersByYear, selectedYear]);

  const handleStartPaper = (paper) => {
    // Navigate to exam instructions with paper info
    navigate(`/pyq/${paper.id}/instructions`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-500 mb-4">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Failed to Load Papers
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <Button onClick={fetchPapers}>Try Again</Button>
      </div>
    );
  }

  if (papers.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-400 mb-4">
          <svg
            className="w-16 h-16 mx-auto"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No Papers Available
        </h3>
        <p className="text-gray-600">
          PYQ papers are being extracted. Check back soon!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            TS EAMCET Previous Year Papers
          </h1>
          <p className="text-gray-600 mt-1">
            Attempt actual past papers to prepare for your exam
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">
            {papers.length} Papers Available
          </span>
        </div>
      </div>

      {/* Year Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedYear(null)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            selectedYear === null
              ? "bg-blue-500 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          All Years
        </button>
        {[...years]
          .sort((a, b) => b.year - a.year)
          .map((yearData) => (
            <button
              key={yearData.year}
              onClick={() => setSelectedYear(yearData.year)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedYear === yearData.year
                  ? "bg-blue-500 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {yearData.year}
            </button>
          ))}
      </div>

      {/* Papers Grid */}
      <div className="space-y-8">
        {Object.entries(filteredPapers)
          .sort(([a], [b]) => b - a)
          .map(([year, yearPapers]) => (
            <div key={year}>
              <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-lg">
                  {year}
                </span>
                <span className="text-sm font-normal text-gray-500">
                  {yearPapers.length}{" "}
                  {yearPapers.length === 1 ? "paper" : "papers"}
                </span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {yearPapers.map((paper) => (
                  <PaperCard
                    key={paper.id}
                    paper={paper}
                    onStart={() => handleStartPaper(paper)}
                  />
                ))}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}

function PaperCard({ paper, onStart }) {
  const getShiftLabel = (shift) => {
    if (shift === 1) return "Morning Shift";
    if (shift === 2) return "Afternoon Shift";
    return `Shift ${shift}`;
  };

  const getStatusBadge = () => {
    if (!paper.is_extracted) {
      return (
        <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">
          Coming Soon
        </span>
      );
    }
    return (
      <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">
        Available
      </span>
    );
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardContent className="p-5">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">
              {paper.exam_name || "TS EAMCET"} {paper.year}
            </h3>
            <p className="text-sm text-gray-600">
              {getShiftLabel(paper.shift)}
            </p>
          </div>
          {getStatusBadge()}
        </div>

        <div className="space-y-2 mb-4">
          <div className="flex items-center text-sm text-gray-600">
            <svg
              className="w-4 h-4 mr-2 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            {paper.total_questions || 160} Questions
          </div>
          <div className="flex items-center text-sm text-gray-600">
            <svg
              className="w-4 h-4 mr-2 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {paper.duration || 180} Minutes
          </div>
          {paper.sections && (
            <div className="flex items-center text-sm text-gray-600">
              <svg
                className="w-4 h-4 mr-2 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 10h16M4 14h16M4 18h16"
                />
              </svg>
              {paper.sections.length} Sections
            </div>
          )}
        </div>

        <Button
          onClick={onStart}
          disabled={!paper.is_extracted}
          className="w-full"
          variant={paper.is_extracted ? "primary" : "secondary"}
        >
          {paper.is_extracted ? "Start Test" : "Coming Soon"}
        </Button>
      </CardContent>
    </Card>
  );
}
