/**
 * useExamSecurity Hook - Exam security measures
 *
 * Features:
 * - Disable copy/paste
 * - Detect tab switching
 * - Prevent back button
 * - Full screen mode
 */

import { useEffect, useCallback, useState } from "react";

export default function useExamSecurity(options = {}) {
  const {
    enabled = true,
    onTabChange = () => {},
    onCopyAttempt = () => {},
  } = options;

  const [tabSwitchCount, setTabSwitchCount] = useState(0);

  // Disable copy/paste
  useEffect(() => {
    if (!enabled) return;

    const handleCopy = (e) => {
      e.preventDefault();
      onCopyAttempt();
    };

    const handlePaste = (e) => {
      e.preventDefault();
    };

    document.addEventListener("copy", handleCopy);
    document.addEventListener("paste", handlePaste);
    document.addEventListener("cut", handleCopy);

    return () => {
      document.removeEventListener("copy", handleCopy);
      document.removeEventListener("paste", handlePaste);
      document.removeEventListener("cut", handleCopy);
    };
  }, [enabled, onCopyAttempt]);

  // Detect tab/window switch
  useEffect(() => {
    if (!enabled) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        setTabSwitchCount((prev) => prev + 1);
        onTabChange(tabSwitchCount + 1);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [enabled, onTabChange, tabSwitchCount]);

  // Disable back button
  useEffect(() => {
    if (!enabled) return;

    const handlePopState = (e) => {
      window.history.pushState(null, "", window.location.href);
    };

    window.history.pushState(null, "", window.location.href);
    window.addEventListener("popstate", handlePopState);

    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [enabled]);

  // Request full screen
  const enterFullScreen = useCallback(() => {
    if (document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen();
    }
  }, []);

  const exitFullScreen = useCallback(() => {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }, []);

  return {
    tabSwitchCount,
    enterFullScreen,
    exitFullScreen,
  };
}
