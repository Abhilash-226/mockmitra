/**
 * Question Selector - Selects questions based on criteria
 *
 * Handles:
 * - Topic-based selection
 * - Difficulty-based selection
 * - Random selection
 * - PYQ filtering
 */

export function selectQuestions(questionPool, criteria) {
  let selected = [...questionPool];

  // Filter by topics
  if (criteria.topics && criteria.topics.length > 0) {
    selected = selected.filter((q) => criteria.topics.includes(q.topic));
  }

  // Filter by difficulty
  if (criteria.difficulty && criteria.difficulty !== "mixed") {
    selected = selected.filter((q) => q.difficulty === criteria.difficulty);
  }

  // Filter by year (for PYQs)
  if (criteria.years && criteria.years.length > 0) {
    selected = selected.filter((q) => criteria.years.includes(q.year));
  }

  // Shuffle for randomness
  selected = shuffleArray(selected);

  // Limit to required count
  if (criteria.count) {
    selected = selected.slice(0, criteria.count);
  }

  return selected;
}

function shuffleArray(array) {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

export default { selectQuestions };
