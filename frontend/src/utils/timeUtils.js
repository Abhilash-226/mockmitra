/**
 * Time Utilities
 */

// Get elapsed time from start timestamp
export function getElapsedTime(startTimestamp) {
  return Math.floor((Date.now() - startTimestamp) / 1000);
}

// Get remaining time
export function getRemainingTime(startTimestamp, totalDuration) {
  const elapsed = getElapsedTime(startTimestamp);
  return Math.max(0, totalDuration - elapsed);
}

// Check if time is expired
export function isTimeExpired(startTimestamp, totalDuration) {
  return getRemainingTime(startTimestamp, totalDuration) <= 0;
}

// Format duration in human readable format
export function formatDuration(seconds) {
  if (seconds < 60) return `${seconds} seconds`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes`;
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}
