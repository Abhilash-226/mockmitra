/**
 * usePersistence Hook - Handle local data persistence
 *
 * Manages IndexedDB / localStorage for exam data
 */

import { useCallback, useEffect } from "react";

const STORAGE_KEY = "mockmitra_exam_state";

export default function usePersistence(key = STORAGE_KEY) {
  const save = useCallback(
    (data) => {
      try {
        const payload = {
          data,
          timestamp: Date.now(),
        };
        localStorage.setItem(key, JSON.stringify(payload));
        return true;
      } catch (error) {
        console.error("Failed to save to storage:", error);
        return false;
      }
    },
    [key],
  );

  const load = useCallback(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored) {
        const { data, timestamp } = JSON.parse(stored);
        return { data, timestamp };
      }
    } catch (error) {
      console.error("Failed to load from storage:", error);
    }
    return null;
  }, [key]);

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (error) {
      console.error("Failed to clear storage:", error);
      return false;
    }
  }, [key]);

  const hasStoredData = useCallback(() => {
    return localStorage.getItem(key) !== null;
  }, [key]);

  return {
    save,
    load,
    clear,
    hasStoredData,
  };
}
