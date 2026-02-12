/**
 * Config Loader - Fetches and caches exam configurations
 *
 * New exam = config change, not UI rewrite
 */

const configCache = new Map();

export async function loadExamConfig(examId) {
  // Check cache first
  if (configCache.has(examId)) {
    return configCache.get(examId);
  }

  // Fetch from API
  try {
    const response = await fetch(`/api/exams/${examId}/config`);
    const config = await response.json();

    // Cache for future use
    configCache.set(examId, config);

    return config;
  } catch (error) {
    console.error("Failed to load exam config:", error);
    throw error;
  }
}

export function clearConfigCache(examId = null) {
  if (examId) {
    configCache.delete(examId);
  } else {
    configCache.clear();
  }
}

export default { loadExamConfig, clearConfigCache };
