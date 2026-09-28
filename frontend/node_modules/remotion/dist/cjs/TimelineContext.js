"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TimelineContextProvider = exports.AbsoluteTimeContext = exports.PlaybackRateContext = exports.TimelineContext = exports.SetTimelineContext = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const runtime_value_store_js_1 = require("./runtime-value-store.js");
const timeline_position_state_1 = require("./timeline-position-state");
const use_delay_render_1 = require("./use-delay-render");
const use_remotion_environment_1 = require("./use-remotion-environment");
const use_timeline_seek_1 = require("./use-timeline-seek");
const missingSetTimelineContext = () => {
    throw new Error('SetTimelineContext is missing. This is likely caused by a Remotion version mismatch.');
};
exports.SetTimelineContext = (0, react_1.createContext)({
    seek: null,
    setFrameWithoutSeek: missingSetTimelineContext,
    setPlaying: missingSetTimelineContext,
    setBuffering: missingSetTimelineContext,
    subscribePlaying: () => () => undefined,
    subscribeBuffering: () => () => undefined,
    isPlaying: () => false,
    isBuffering: missingSetTimelineContext,
    frameRef: { current: {} },
    audioAndVideoTags: { current: [] },
});
exports.TimelineContext = (0, react_1.createContext)(null);
exports.PlaybackRateContext = (0, react_1.createContext)(null);
exports.AbsoluteTimeContext = (0, react_1.createContext)(null);
const TimelineContextProvider = ({ children, frameState }) => {
    const playingStore = (0, react_1.useMemo)(() => (0, runtime_value_store_js_1.createRuntimeValueStore)({ playing: false }), []);
    const bufferingStore = (0, react_1.useMemo)(() => (0, runtime_value_store_js_1.createRuntimeValueStore)({ buffering: false }), []);
    const [playbackRate, setPlaybackRate] = (0, react_1.useState)(1);
    const audioAndVideoTags = (0, react_1.useRef)([]);
    const [_frame, setFrame] = (0, react_1.useState)(() => (0, timeline_position_state_1.getInitialFrameState)());
    const timelineSeek = (0, use_timeline_seek_1.useTimelineSeek)(setFrame);
    const { isStudio } = (0, use_remotion_environment_1.useRemotionEnvironment)();
    const seek = isStudio ? timelineSeek : null;
    const frame = frameState !== null && frameState !== void 0 ? frameState : _frame;
    const frameRef = (0, react_1.useRef)(frame);
    frameRef.current = frame;
    const readIsPlaying = (0, react_1.useCallback)(() => playingStore.store.getSnapshot().playing, [playingStore]);
    const readIsBuffering = (0, react_1.useCallback)(() => bufferingStore.store.getSnapshot().buffering, [bufferingStore]);
    const { delayRender, continueRender } = (0, use_delay_render_1.useDelayRender)();
    if (typeof window !== 'undefined') {
        // eslint-disable-next-line react-hooks/rules-of-hooks
        (0, react_1.useLayoutEffect)(() => {
            window.remotion_setFrame = (f, composition, attempt) => {
                window.remotion_attempt = attempt;
                const id = delayRender(`Setting the current frame to ${f}`);
                let asyncUpdate = true;
                setFrame((s) => {
                    var _a;
                    const currentFrame = (_a = s[composition]) !== null && _a !== void 0 ? _a : window.remotion_initialFrame;
                    // Avoid cloning the object
                    if (currentFrame === f) {
                        asyncUpdate = false;
                        return s;
                    }
                    return {
                        ...s,
                        [composition]: f,
                    };
                });
                // After setting the state, need to wait until it is applied in the next cycle
                if (asyncUpdate) {
                    requestAnimationFrame(() => continueRender(id));
                }
                else {
                    continueRender(id);
                }
            };
            window.remotion_isPlayer = false;
        }, [continueRender, delayRender]);
    }
    const timelineContextValue = (0, react_1.useMemo)(() => {
        return {
            frame,
            isPlaying: readIsPlaying,
            isInsideFreeze: false,
            audioAndVideoTags,
        };
    }, [frame, readIsPlaying]);
    const playbackRateContextValue = (0, react_1.useMemo)(() => {
        return {
            playbackRate,
            setPlaybackRate,
        };
    }, [playbackRate]);
    const setTimelineContextValue = (0, react_1.useMemo)(() => {
        return {
            setFrameWithoutSeek: setFrame,
            seek,
            setPlaying: (updater) => {
                const current = playingStore.store.getSnapshot().playing;
                const next = typeof updater === 'function' ? updater(current) : updater;
                if (current !== next) {
                    playingStore.setSnapshot({ playing: next });
                }
            },
            setBuffering: (buffering) => {
                if (readIsBuffering() !== buffering) {
                    bufferingStore.setSnapshot({ buffering });
                }
            },
            subscribePlaying: playingStore.store.subscribe,
            subscribeBuffering: bufferingStore.store.subscribe,
            isPlaying: readIsPlaying,
            isBuffering: readIsBuffering,
            frameRef,
            audioAndVideoTags,
        };
    }, [bufferingStore, playingStore, readIsBuffering, readIsPlaying, seek]);
    return (jsx_runtime_1.jsx(exports.AbsoluteTimeContext.Provider, { value: timelineContextValue, children: jsx_runtime_1.jsx(exports.PlaybackRateContext.Provider, { value: playbackRateContextValue, children: jsx_runtime_1.jsx(exports.TimelineContext.Provider, { value: timelineContextValue, children: jsx_runtime_1.jsx(exports.SetTimelineContext.Provider, { value: setTimelineContextValue, children: children }) }) }) }));
};
exports.TimelineContextProvider = TimelineContextProvider;
