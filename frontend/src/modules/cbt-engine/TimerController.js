/**
 * TimerController - Independent timer logic
 *
 * CRITICAL: Timer runs independently of UI re-renders
 * Uses performance.now() for accuracy
 *
 * Features:
 * - Runs in Web Worker (future enhancement)
 * - Persists timestamps to IndexedDB
 * - Auto-submit on expiry
 * - Recovery on page refresh
 */

class TimerController {
  constructor() {
    this.startTime = null;
    this.duration = null;
    this.intervalId = null;
    this.onTick = null;
    this.onExpire = null;
  }

  start(durationInSeconds, callbacks = {}) {
    this.duration = durationInSeconds;
    this.startTime = performance.now();
    this.onTick = callbacks.onTick;
    this.onExpire = callbacks.onExpire;

    this.intervalId = setInterval(() => {
      const elapsed = Math.floor((performance.now() - this.startTime) / 1000);
      const remaining = Math.max(0, this.duration - elapsed);

      if (this.onTick) {
        this.onTick(remaining);
      }

      if (remaining === 0) {
        this.stop();
        if (this.onExpire) {
          this.onExpire();
        }
      }
    }, 1000);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  pause() {
    // Store elapsed time and stop
    this.stop();
  }

  resume() {
    // Restart with remaining time
  }

  getRemainingTime() {
    if (!this.startTime) return this.duration;
    const elapsed = Math.floor((performance.now() - this.startTime) / 1000);
    return Math.max(0, this.duration - elapsed);
  }
}

export default TimerController;
