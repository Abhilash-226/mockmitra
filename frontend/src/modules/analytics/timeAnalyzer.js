/**
 * Time Analyzer - Analyze time spent on questions and sections
 */

export function analyzeTimeSpent(timeData, questions) {
  const totalTime = Object.values(timeData).reduce((sum, t) => sum + t, 0);
  const avgTimePerQuestion = totalTime / questions.length;

  return {
    totalTime,
    avgTimePerQuestion,
    questionsAboveAvg: Object.entries(timeData).filter(
      ([_, time]) => time > avgTimePerQuestion,
    ).length,
  };
}

export function getSectionTimeBreakdown(timeData, sections) {
  return sections.map((section) => {
    const sectionTime = section.questionIds.reduce(
      (sum, qId) => sum + (timeData[qId] || 0),
      0,
    );
    return {
      sectionId: section.id,
      sectionName: section.name,
      timeSpent: sectionTime,
    };
  });
}

export default { analyzeTimeSpent, getSectionTimeBreakdown };
