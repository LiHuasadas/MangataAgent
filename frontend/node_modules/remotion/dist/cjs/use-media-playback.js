"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useMediaPlayback = void 0;
const react_1 = require("react");
const use_audio_frame_js_1 = require("./audio/use-audio-frame.js");
const buffer_until_first_frame_js_1 = require("./buffer-until-first-frame.js");
const get_media_sync_action_js_1 = require("./get-media-sync-action.js");
const log_level_context_js_1 = require("./log-level-context.js");
const log_js_1 = require("./log.js");
const media_tag_current_time_timestamp_js_1 = require("./media-tag-current-time-timestamp.js");
const play_and_handle_not_allowed_error_js_1 = require("./play-and-handle-not-allowed-error.js");
const playback_logging_js_1 = require("./playback-logging.js");
const seek_js_1 = require("./seek.js");
const SequenceContext_js_1 = require("./SequenceContext.js");
const timeline_position_state_js_1 = require("./timeline-position-state.js");
const use_buffering_js_1 = require("./use-buffering.js");
const use_current_frame_js_1 = require("./use-current-frame.js");
const use_media_buffering_js_1 = require("./use-media-buffering.js");
const use_remotion_environment_js_1 = require("./use-remotion-environment.js");
const use_request_video_callback_time_js_1 = require("./use-request-video-callback-time.js");
const use_video_config_js_1 = require("./use-video-config.js");
const get_current_time_js_1 = require("./video/get-current-time.js");
const warn_about_non_seekable_media_js_1 = require("./warn-about-non-seekable-media.js");
// In Safari, amplified media can lag behind by around 0.4 seconds.
const DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_AMPLIFICATION = 0.65;
const getPauseReason = ({ reason, isPremounting, isPostmounting, }) => {
    if (reason === 'buffering') {
        return 'player is buffering but media tag is not';
    }
    if (isPremounting) {
        return 'media is premounting';
    }
    if (isPostmounting) {
        return 'media is postmounting';
    }
    return 'Player is not playing';
};
const useMediaPlayback = ({ mediaRef, src, mediaType, playbackRate: localPlaybackRate, preservePitch = true, onlyWarnForMediaSeekingError, acceptableTimeshift, pauseWhenBuffering, isPremounting, isPostmounting, onAutoPlayError, }) => {
    var _a;
    const { playbackRate: globalPlaybackRate } = (0, timeline_position_state_js_1.usePlaybackRate)();
    const frame = (0, use_current_frame_js_1.useCurrentFrame)();
    const absoluteFrame = (0, timeline_position_state_js_1.useTimelinePosition)();
    const playing = (0, timeline_position_state_js_1.usePlaying)();
    const playerBuffering = (0, use_buffering_js_1.useBuffering)();
    const { fps } = (0, use_video_config_js_1.useVideoConfig)();
    const mediaTrimBefore = (0, react_1.useContext)(use_audio_frame_js_1.Html5MediaTrimContext);
    const lastSeekDueToShift = (0, react_1.useRef)(null);
    const lastSeek = (0, react_1.useRef)(null);
    const logLevel = (0, log_level_context_js_1.useLogLevel)();
    const mountTime = (0, log_level_context_js_1.useMountTime)();
    const isVariableFpsVideoMap = (0, react_1.useRef)({});
    const onVariableFpsVideoDetected = (0, react_1.useCallback)(() => {
        if (!src) {
            return;
        }
        if (isVariableFpsVideoMap.current[src]) {
            return;
        }
        log_js_1.Log.verbose({ logLevel, tag: null }, `Detected ${src} as a variable FPS video. Disabling buffering while seeking.`);
        isVariableFpsVideoMap.current[src] = true;
    }, [logLevel, src]);
    const rvcCurrentTime = (0, use_request_video_callback_time_js_1.useRequestVideoCallbackTime)({
        mediaRef,
        mediaType,
        lastSeek,
        onVariableFpsVideoDetected,
    });
    const mediaTagCurrentTime = (0, media_tag_current_time_timestamp_js_1.useCurrentTimeOfMediaTagWithUpdateTimeStamp)(mediaRef);
    const desiredUnclampedTime = (0, get_current_time_js_1.getMediaTime)({
        frame,
        playbackRate: localPlaybackRate,
        startFrom: mediaTrimBefore,
        fps,
    });
    const isMediaTagBuffering = (0, use_media_buffering_js_1.useMediaBuffering)({
        element: mediaRef,
        shouldBuffer: pauseWhenBuffering,
        isPremounting,
        isPostmounting,
        logLevel,
        mountTime,
        src: src !== null && src !== void 0 ? src : null,
    });
    const { bufferUntilFirstFrame, isBuffering } = (0, buffer_until_first_frame_js_1.useBufferUntilFirstFrame)({
        mediaRef,
        mediaType,
        onVariableFpsVideoDetected,
        pauseWhenBuffering,
        logLevel,
        mountTime,
    });
    const sequenceContext = (0, react_1.useContext)(SequenceContext_js_1.SequenceContext);
    const playbackRate = localPlaybackRate *
        globalPlaybackRate *
        ((_a = sequenceContext === null || sequenceContext === void 0 ? void 0 : sequenceContext.playbackRate) !== null && _a !== void 0 ? _a : 1);
    const acceptableTimeShiftButLessThanDuration = (() => {
        var _a;
        // For short audio, a lower acceptable time shift is used
        if ((_a = mediaRef.current) === null || _a === void 0 ? void 0 : _a.duration) {
            return Math.min(mediaRef.current.duration, acceptableTimeshift !== null && acceptableTimeshift !== void 0 ? acceptableTimeshift : DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_AMPLIFICATION);
        }
        return (acceptableTimeshift !== null && acceptableTimeshift !== void 0 ? acceptableTimeshift : DEFAULT_ACCEPTABLE_TIMESHIFT_WITH_AMPLIFICATION);
    })();
    const env = (0, use_remotion_environment_js_1.useRemotionEnvironment)();
    // This must be a useLayoutEffect, because afterwards, useVolume() looks at the playbackRate
    // and it is also in a useLayoutEffect.
    (0, react_1.useLayoutEffect)(() => {
        const playbackRateToSet = Math.max(0, playbackRate);
        // Loading a resource resets playbackRate to defaultPlaybackRate.
        if (mediaRef.current &&
            mediaRef.current.defaultPlaybackRate !== playbackRateToSet) {
            mediaRef.current.defaultPlaybackRate = playbackRateToSet;
        }
        if (mediaRef.current &&
            mediaRef.current.playbackRate !== playbackRateToSet) {
            mediaRef.current.playbackRate = playbackRateToSet;
        }
        if (mediaRef.current && mediaRef.current.preservesPitch !== preservePitch) {
            mediaRef.current.preservesPitch = preservePitch;
        }
    }, [mediaRef, playbackRate, preservePitch]);
    (0, react_1.useEffect)(() => {
        var _a, _b;
        var _c, _d;
        const tagName = mediaType === 'audio' ? '<Html5Audio>' : '<Html5Video>';
        if (!mediaRef.current) {
            throw new Error(`No ${mediaType} ref found`);
        }
        if (!src) {
            throw new Error(`No 'src' attribute was passed to the ${tagName} element.`);
        }
        const { current } = mediaRef;
        const isMediaTagBufferingOrStalled = isMediaTagBuffering || isBuffering();
        let pauseReason = null;
        if (!playing) {
            pauseReason = 'not-playing';
        }
        else if (playerBuffering && !isMediaTagBufferingOrStalled) {
            pauseReason = 'buffering';
        }
        if (!current.paused && pauseReason !== null) {
            (0, playback_logging_js_1.playbackLogging)({
                logLevel,
                tag: 'pause',
                message: `Pausing ${current.src} because ${getPauseReason({
                    reason: pauseReason,
                    isPremounting,
                    isPostmounting,
                })}`,
                mountTime,
            });
            current.pause();
        }
        const action = (0, get_media_sync_action_js_1.getMediaSyncAction)({
            duration: current.duration,
            currentTime: current.currentTime,
            paused: current.paused,
            ended: current.ended,
            desiredUnclampedTime,
            mediaTagTime: mediaTagCurrentTime.current.time,
            mediaTagLastUpdate: mediaTagCurrentTime.current.lastUpdate,
            rvcTime: (_c = (_a = rvcCurrentTime.current) === null || _a === void 0 ? void 0 : _a.time) !== null && _c !== void 0 ? _c : null,
            rvcLastUpdate: (_d = (_b = rvcCurrentTime.current) === null || _b === void 0 ? void 0 : _b.lastUpdate) !== null && _d !== void 0 ? _d : null,
            isVariableFpsVideo: Boolean(isVariableFpsVideoMap.current[src]),
            acceptableTimeShift: acceptableTimeShiftButLessThanDuration,
            lastSeekDueToShift: lastSeekDueToShift.current,
            playing,
            playbackRate,
            mediaTagBufferingOrStalled: isMediaTagBufferingOrStalled,
            playerBuffering,
            absoluteFrame,
            onlyWarnForMediaSeekingError,
            isPremounting,
            isPostmounting,
            pauseWhenBuffering,
        });
        if (action.type === 'none') {
            return;
        }
        if (action.type === 'seek-due-to-shift') {
            lastSeek.current = (0, seek_js_1.seek)({
                mediaRef: current,
                time: action.shouldBeTime,
                logLevel,
                why: action.why,
                mountTime,
            });
            lastSeekDueToShift.current = lastSeek.current;
            if (action.bufferUntilFirstFrame) {
                bufferUntilFirstFrame(action.shouldBeTime);
            }
            if (action.playReason !== null) {
                (0, play_and_handle_not_allowed_error_js_1.playAndHandleNotAllowedError)({
                    mediaRef,
                    mediaType,
                    onAutoPlayError,
                    logLevel,
                    mountTime,
                    reason: action.playReason,
                    isPlayer: env.isPlayer,
                });
            }
            if (action.warnAboutNonSeekable) {
                (0, warn_about_non_seekable_media_js_1.warnAboutNonSeekableMedia)(current, 'console-error');
            }
            return;
        }
        if (action.type === 'seek-if-not-playing') {
            if (action.why !== null) {
                lastSeek.current = (0, seek_js_1.seek)({
                    mediaRef: current,
                    time: action.shouldBeTime,
                    logLevel,
                    why: action.why,
                    mountTime,
                });
            }
            return;
        }
        // action.type === 'play-and-seek'
        if (action.why !== null) {
            lastSeek.current = (0, seek_js_1.seek)({
                mediaRef: current,
                time: action.shouldBeTime,
                logLevel,
                why: action.why,
                mountTime,
            });
        }
        (0, play_and_handle_not_allowed_error_js_1.playAndHandleNotAllowedError)({
            mediaRef,
            mediaType,
            onAutoPlayError,
            logLevel,
            mountTime,
            reason: action.playReason,
            isPlayer: env.isPlayer,
        });
        if (action.bufferUntilFirstFrame) {
            bufferUntilFirstFrame(action.shouldBeTime);
        }
    }, [
        absoluteFrame,
        acceptableTimeShiftButLessThanDuration,
        bufferUntilFirstFrame,
        rvcCurrentTime,
        logLevel,
        desiredUnclampedTime,
        isBuffering,
        isMediaTagBuffering,
        mediaRef,
        mediaType,
        onlyWarnForMediaSeekingError,
        playbackRate,
        playerBuffering,
        playing,
        src,
        onAutoPlayError,
        isPremounting,
        isPostmounting,
        pauseWhenBuffering,
        mountTime,
        mediaTagCurrentTime,
        env.isPlayer,
    ]);
};
exports.useMediaPlayback = useMediaPlayback;
