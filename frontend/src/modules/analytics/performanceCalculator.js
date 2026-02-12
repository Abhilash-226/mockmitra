/**
 * Performance Calculator - Percentile and ranking calculations
 */

export function calculatePercentile(userScore, allScores) {
  const belowCount = allScores.filter((score) => score < userScore).length;
  return Math.round((belowCount / allScores.length) * 100);
}

export function compareWithAverage(userScore, averageScore) {
  const difference = userScore - averageScore;
  return {
    difference,
    isAboveAverage: difference > 0,
    percentageDiff: Math.round((difference / averageScore) * 100),
  };
}

export default { calculatePercentile, compareWithAverage };
