/**
 * useExamConfig Hook - Load and manage exam configuration
 */

import { useState, useEffect, useCallback } from "react";
import { examService } from "../services";

export default function useExamConfig(examId) {
  const [config, setConfig] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadConfig = useCallback(async () => {
    if (!examId) return;

    setIsLoading(true);
    setError(null);

    try {
      const data = await examService.getExamConfig(examId);
      setConfig(data);
    } catch (err) {
      setError(err.message || "Failed to load exam config");
    } finally {
      setIsLoading(false);
    }
  }, [examId]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  return {
    config,
    isLoading,
    error,
    reload: loadConfig,
  };
}
