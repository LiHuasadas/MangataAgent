"use strict";
// Pure decision logic for `useMediaPlayback`.
//
// Every frame, the media element's clock has to be reconciled with the
// timeline clock. This function takes a snapshot of the relevant state and
// decides *what* should happen (seek / play / buffer / nothing). The effect in
// `use-media-playback.ts` is responsible for actually executing the returned
// action. Keeping the decision separate makes the branch ordering testable
// without a DOM or a real media element.
Object.defineProperty(exports, "__esModule", { value: true });
exports.getMediaSyncAction = void 0;
const getMediaSyncAction = (input) => {
    const { duration, currentTime, paused, ended, desiredUnclampedTime, mediaTagTime, mediaTagLastUpdate, rvcTime, rvcLastUpdate, isVariableFpsVideo, acceptableTimeShift, lastSeekDueToShift, playing, playbackRate, mediaTagBufferingOrStalled, playerBuffering, absoluteFrame, onlyWarnForMediaSeekingError, isPremounting, isPostmounting, pauseWhenBuffering, } = input;
    const shouldBeTime = !Number.isNaN(duration) && Number.isFinite(duration)
        ? Math.min(duration, desiredUnclampedTime)
        : desiredUnclampedTime;
    const timeShiftMediaTag = Math.abs(shouldBeTime - mediaTagTime);
    const timeShiftRvcTag = rvcTime ? Math.abs(shouldBeTime - rvcTime) : null;
    const mostRecentTimeshift = rvcLastUpdate && rvcTime > mediaTagLastUpdate
        ? timeShiftRvcTag
        : timeShiftMediaTag;
    const timeShift = timeShiftRvcTag && !isVariableFpsVideo
        ? mostRecentTimeshift
        : timeShiftMediaTag;
    if (timeShift > acceptableTimeShift && lastSeekDueToShift !== shouldBeTime) {
        // If scrubbing around, adjust timing
        // or if time shift is bigger than 0.45sec
        return {
            type: 'seek-due-to-shift',
            shouldBeTime,
            why: `because time shift is too big. shouldBeTime = ${shouldBeTime}, isTime = ${mediaTagTime}, requestVideoCallbackTime = ${rvcTime}, timeShift = ${timeShift}${isVariableFpsVideo ? ', isVariableFpsVideo = true' : ''}, isPremounting = ${isPremounting}, isPostmounting = ${isPostmounting}, pauseWhenBuffering = ${pauseWhenBuffering}`,
            bufferUntilFirstFrame: playing && playbackRate > 0,
            playReason: playing && paused
                ? 'player is playing but media tag is paused, and just seeked'
                : null,
            warnAboutNonSeekable: !onlyWarnForMediaSeekingError,
        };
    }
    const seekThreshold = playing ? 0.15 : 0.01;
    // Only perform a seek if the time is not already the same.
    // Chrome rounds to 6 digits, so 0.033333333 -> 0.033333,
    // therefore a threshold is allowed.
    // Refer to the https://github.com/remotion-dev/video-buffering-example
    // which is fixed by only seeking conditionally.
    const makesSenseToSeek = Math.abs(currentTime - shouldBeTime) > seekThreshold;
    const isSomethingElseBuffering = playerBuffering && !mediaTagBufferingOrStalled;
    if (!playing || isSomethingElseBuffering) {
        return {
            type: 'seek-if-not-playing',
            shouldBeTime,
            why: makesSenseToSeek
                ? `not playing or something else is buffering. time offset is over seek threshold (${seekThreshold})`
                : null,
        };
    }
    if (!playing || playerBuffering) {
        return { type: 'none' };
    }
    // We now assured we are in playing state and not buffering
    const pausedCondition = paused && !ended;
    const firstFrameCondition = absoluteFrame === 0;
    if (pausedCondition || firstFrameCondition) {
        const reason = pausedCondition
            ? 'media tag is paused'
            : 'absolute frame is 0';
        return {
            type: 'play-and-seek',
            shouldBeTime,
            why: makesSenseToSeek
                ? `is over timeshift threshold (threshold = ${seekThreshold}) and ${reason}`
                : null,
            playReason: `player is playing and ${reason}`,
            bufferUntilFirstFrame: !isVariableFpsVideo && playbackRate > 0,
        };
    }
    return { type: 'none' };
};
exports.getMediaSyncAction = getMediaSyncAction;
