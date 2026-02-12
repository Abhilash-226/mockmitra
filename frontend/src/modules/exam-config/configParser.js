/**
 * Config Parser - Transforms raw config to usable format
 *
 * Handles different exam config formats
 */

export function parseExamConfig(rawConfig) {
  return {
    examId: rawConfig.exam_id,
    examName: rawConfig.name,
    sections: parseSections(rawConfig.sections || []),
    markingScheme: parseMarkingScheme(rawConfig.marking_scheme),
    timingRules: parseTimingRules(rawConfig.timing),
    totalQuestions: rawConfig.total_questions,
    totalDuration: rawConfig.duration_minutes * 60, // Convert to seconds
  };
}

function parseSections(sections) {
  return sections.map((section, index) => ({
    id: section.id || `section_${index}`,
    name: section.name,
    questionCount: section.question_count,
    topics: section.topics || [],
    timeLimit: section.time_limit ? section.time_limit * 60 : null,
  }));
}

function parseMarkingScheme(scheme = {}) {
  return {
    correctMarks: scheme.correct || 2,
    incorrectMarks: scheme.incorrect || -0.5,
    unattemptedMarks: scheme.unattempted || 0,
  };
}

function parseTimingRules(timing = {}) {
  return {
    totalDuration: timing.total_minutes * 60,
    sectionWise: timing.section_wise || false,
    canSwitchSections: timing.can_switch_sections !== false,
  };
}

export default { parseExamConfig };
