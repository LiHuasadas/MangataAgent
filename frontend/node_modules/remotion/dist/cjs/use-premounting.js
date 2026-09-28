"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.usePremounting = void 0;
const react_1 = require("react");
const get_sequence_boundary_tolerance_js_1 = require("./get-sequence-boundary-tolerance.js");
const PremountContext_js_1 = require("./PremountContext.js");
const SequenceContext_js_1 = require("./SequenceContext.js");
const timeline_position_state_js_1 = require("./timeline-position-state.js");
const use_current_frame_js_1 = require("./use-current-frame.js");
const use_remotion_environment_js_1 = require("./use-remotion-environment.js");
const use_video_config_js_1 = require("./use-video-config.js");
const v5_flag_js_1 = require("./v5-flag.js");
const usePremounting = ({ from, durationInFrames, premountFor, postmountFor, style, styleWhilePremounted, styleWhilePostmounted, hideWhilePremounted, }) => {
    var _a;
    const parentPremountContext = (0, react_1.useContext)(PremountContext_js_1.PremountContext);
    const frame = (0, use_current_frame_js_1.useCurrentFrame)() - parentPremountContext.premountFramesRemaining;
    const environment = (0, use_remotion_environment_js_1.useRemotionEnvironment)();
    const { fps } = (0, use_video_config_js_1.useVideoConfig)();
    const effectivePremountFor = v5_flag_js_1.ENABLE_V5_BREAKING_CHANGES
        ? (premountFor !== null && premountFor !== void 0 ? premountFor : fps)
        : (premountFor !== null && premountFor !== void 0 ? premountFor : 0);
    const effectivePostmountFor = postmountFor !== null && postmountFor !== void 0 ? postmountFor : 0;
    const endExclusive = from + durationInFrames;
    const sequenceContext = (0, react_1.useContext)(SequenceContext_js_1.SequenceContext);
    const boundaryTolerance = (0, get_sequence_boundary_tolerance_js_1.getSequenceBoundaryTolerance)({
        absoluteFrame: (0, timeline_position_state_js_1.useTimelinePosition)(),
        cumulatedFrom: sequenceContext
            ? sequenceContext.cumulatedFrom + sequenceContext.relativeFrom
            : 0,
        from,
        parentPlaybackRate: (_a = sequenceContext === null || sequenceContext === void 0 ? void 0 : sequenceContext.playbackRate) !== null && _a !== void 0 ? _a : 1,
        durationInFrames,
    });
    const premountingActive = !environment.isRendering &&
        frame - from < -boundaryTolerance &&
        frame - (from - effectivePremountFor) >= -boundaryTolerance;
    const postmountingActive = !environment.isRendering &&
        frame - endExclusive >= -boundaryTolerance &&
        frame - (endExclusive + effectivePostmountFor) < -boundaryTolerance;
    const isPremountingOrPostmounting = premountingActive || postmountingActive;
    const freezeFrame = premountingActive
        ? from
        : postmountingActive
            ? from + durationInFrames - 1
            : 0;
    const premountingStyle = (0, react_1.useMemo)(() => {
        if (!isPremountingOrPostmounting) {
            return style;
        }
        return {
            ...style,
            ...(hideWhilePremounted === 'opacity' ? { opacity: 0 } : { display: 'none' }),
            pointerEvents: 'none',
            ...(premountingActive ? styleWhilePremounted : {}),
            ...(postmountingActive ? styleWhilePostmounted : {}),
        };
    }, [
        isPremountingOrPostmounting,
        hideWhilePremounted,
        postmountingActive,
        premountingActive,
        style,
        styleWhilePostmounted,
        styleWhilePremounted,
    ]);
    return {
        effectivePremountFor,
        effectivePostmountFor,
        premountingActive,
        postmountingActive,
        isPremountingOrPostmounting,
        freezeFrame,
        premountingStyle,
    };
};
exports.usePremounting = usePremounting;
