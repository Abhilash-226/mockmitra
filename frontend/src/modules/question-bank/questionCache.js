/**
 * Question Cache - Caches questions for offline/fast access
 */

const cache = new Map();

export function cacheQuestions(examId, questions) {
  cache.set(examId, {
    questions,
    cachedAt: Date.now(),
  });
}

export function getCachedQuestions(examId) {
  const cached = cache.get(examId);
  if (cached) {
    // Check if cache is still valid (e.g., 1 hour)
    const isExpired = Date.now() - cached.cachedAt > 60 * 60 * 1000;
    if (!isExpired) {
      return cached.questions;
    }
    cache.delete(examId);
  }
  return null;
}

export function clearCache(examId = null) {
  if (examId) {
    cache.delete(examId);
  } else {
    cache.clear();
  }
}

export default { cacheQuestions, getCachedQuestions, clearCache };
