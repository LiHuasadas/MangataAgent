"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useMediaTag = void 0;
const react_1 = require("react");
const log_level_context_js_1 = require("./log-level-context.js");
const play_and_handle_not_allowed_error_js_1 = require("./play-and-handle-not-allowed-error.js");
const playback_logging_js_1 = require("./playback-logging.js");
const timeline_position_state_js_1 = require("./timeline-position-state.js");
const TimelineContext_js_1 = require("./TimelineContext.js");
const use_remotion_environment_js_1 = require("./use-remotion-environment.js");
const useMediaTag = ({ mediaRef, id, mediaType, onAutoPlayError, isPremounting, isPostmounting, }) => {
    const { audioAndVideoTags, isPlaying } = (0, timeline_position_state_js_1.useTimelineContext)();
    const { subscribePlaying } = (0, react_1.useContext)(TimelineContext_js_1.SetTimelineContext);
    const isPlayingRef = (0, react_1.useRef)(isPlaying);
    isPlayingRef.current = isPlaying;
    const logLevel = (0, log_level_context_js_1.useLogLevel)();
    const mountTime = (0, log_level_context_js_1.useMountTime)();
    const env = (0, use_remotion_environment_js_1.useRemotionEnvironment)();
    (0, react_1.useEffect)(() => {
        const tag = {
            id,
            play: (reason) => {
                if (!isPlayingRef.current()) {
                    // Don't play if for example in a <Freeze> state.
                    return;
                }
                if (isPremounting || isPostmounting) {
                    return;
                }
                return (0, play_and_handle_not_allowed_error_js_1.playAndHandleNotAllowedError)({
                    mediaRef,
                    mediaType,
                    onAutoPlayError,
                    logLevel,
                    mountTime,
                    reason,
                    isPlayer: env.isPlayer,
                });
            },
        };
        audioAndVideoTags.current.push(tag);
        const unsubscribe = subscribePlaying((state) => {
            if (state.playing) {
                return;
            }
            const media = mediaRef.current;
            if (!media || media.paused) {
                return;
            }
            (0, playback_logging_js_1.playbackLogging)({
                logLevel,
                tag: 'pause',
                message: `Pausing ${media.src} because Player is not playing`,
                mountTime,
            });
            media.pause();
        });
        return () => {
            unsubscribe();
            audioAndVideoTags.current = audioAndVideoTags.current.filter((a) => a.id !== id);
        };
    }, [
        audioAndVideoTags,
        id,
        mediaRef,
        mediaType,
        onAutoPlayError,
        isPremounting,
        isPostmounting,
        logLevel,
        mountTime,
        env.isPlayer,
        subscribePlaying,
    ]);
};
exports.useMediaTag = useMediaTag;
