"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.waitUntilActuallyResumed = void 0;
const log_js_1 = require("../log.js");
const RESUME_WAIT_TIMEOUT = 1000;
const waitUntilActuallyResumed = (audioContext, logLevel, signal, isAutoPlayAttempt) => {
    return new Promise((resolve) => {
        const startCurrentTime = audioContext.currentTime;
        const start = audioContext.getOutputTimestamp();
        const startOutputPerformanceTime = start.performanceTime;
        const startWallClock = performance.now();
        let animationFrame = null;
        let timeout = null;
        let settled = false;
        let onAbort = () => undefined;
        const finish = (result) => {
            if (settled) {
                return;
            }
            settled = true;
            if (animationFrame !== null) {
                cancelAnimationFrame(animationFrame);
            }
            if (timeout !== null) {
                clearTimeout(timeout);
            }
            signal.removeEventListener('abort', onAbort);
            resolve(result);
        };
        onAbort = () => finish('cancelled');
        const hasAudiblyStarted = (startPerformanceTime) => {
            const outputTimestamp = audioContext.getOutputTimestamp();
            return (startPerformanceTime !== undefined &&
                outputTimestamp.performanceTime !== undefined &&
                outputTimestamp.performanceTime > startPerformanceTime &&
                outputTimestamp.contextTime !== undefined &&
                outputTimestamp.contextTime > startCurrentTime);
        };
        const check = () => {
            var _a, _b;
            var _c;
            animationFrame = null;
            const { currentTime } = audioContext;
            const outputTimestamp = audioContext.getOutputTimestamp();
            const elapsedWallClock = performance.now() - startWallClock;
            if (hasAudiblyStarted(startOutputPerformanceTime)) {
                log_js_1.Log.verbose({ logLevel, tag: 'audio' }, `waitUntilActuallyResumed: getOutputTimestamp.performanceTime advanced from ${startOutputPerformanceTime.toFixed(6)} to ${(_a = outputTimestamp.performanceTime) === null || _a === void 0 ? void 0 : _a.toFixed(6)} after ${elapsedWallClock.toFixed(1)}ms. currentTime=${currentTime.toFixed(6)} (advanced by ${(currentTime - startCurrentTime).toFixed(6)}), getOutputTimestamp.performanceTime=${(_c = (_b = outputTimestamp.performanceTime) === null || _b === void 0 ? void 0 : _b.toFixed(1)) !== null && _c !== void 0 ? _c : 'undefined'}`);
                finish('resumed');
                return;
            }
            animationFrame = requestAnimationFrame(check);
        };
        if (signal.aborted) {
            finish('cancelled');
            return;
        }
        signal.addEventListener('abort', onAbort, { once: true });
        if (isAutoPlayAttempt) {
            timeout = setTimeout(() => {
                // The success check is scheduled with requestAnimationFrame, which can
                // be starved while the main thread is busy. Re-check once before
                // declaring failure so a resume that actually completed is not
                // reported as failed - the Player would otherwise mute itself even
                // though playback was started by a user gesture and audio is running.
                if (hasAudiblyStarted(startOutputPerformanceTime)) {
                    finish('resumed');
                    return;
                }
                log_js_1.Log.warn({ logLevel, tag: 'audio' }, 'WARNING: You enabled autoPlay on an unmuted <Player /> and the browser did not allow the video to be started. Remotion muted the <Player /> so it can play. To properly handle this, either set the `muted` prop or remove the `autoPlay` prop');
                finish('failed');
            }, RESUME_WAIT_TIMEOUT);
        }
        animationFrame = requestAnimationFrame(check);
    });
};
exports.waitUntilActuallyResumed = waitUntilActuallyResumed;
