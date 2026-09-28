"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useFrameForVolumeProp = exports.useMediaStartsAt = exports.Html5MediaTrimContext = void 0;
const react_1 = require("react");
const index_js_1 = require("../loop/index.js");
const SequenceContext_js_1 = require("../SequenceContext.js");
const use_current_frame_js_1 = require("../use-current-frame.js");
// A media trim is a source-frame offset, unlike elapsed time inherited from a Sequence.
exports.Html5MediaTrimContext = (0, react_1.createContext)(0);
const useMediaStartsAt = () => {
    var _a;
    const parentSequence = (0, react_1.useContext)(SequenceContext_js_1.SequenceContext);
    return (_a = parentSequence === null || parentSequence === void 0 ? void 0 : parentSequence.cumulatedNegativeFrom) !== null && _a !== void 0 ? _a : 0;
};
exports.useMediaStartsAt = useMediaStartsAt;
/**
 * When passing a function as the prop for `volume`,
 * we calculate the way more intuitive value for currentFrame
 */
const useFrameForVolumeProp = (behavior) => {
    var _a, _b;
    const loop = index_js_1.Loop.useLoop();
    const loopTimeline = (0, react_1.useContext)(index_js_1.LoopTimelineContext);
    const sequenceContext = (0, react_1.useContext)(SequenceContext_js_1.SequenceContext);
    const frame = (0, use_current_frame_js_1.useCurrentFrame)();
    const startsAt = (0, exports.useMediaStartsAt)();
    if (behavior === 'repeat' || loop === null) {
        return frame + startsAt;
    }
    // Loop durations use the parent's clock, while volume callbacks use the
    // media's clock, including rates applied inside the loop.
    return (frame +
        startsAt +
        (loop.durationInFrames *
            loop.iteration *
            ((_a = sequenceContext === null || sequenceContext === void 0 ? void 0 : sequenceContext.playbackRate) !== null && _a !== void 0 ? _a : 1)) /
            ((_b = loopTimeline === null || loopTimeline === void 0 ? void 0 : loopTimeline.playbackRate) !== null && _b !== void 0 ? _b : 1));
};
exports.useFrameForVolumeProp = useFrameForVolumeProp;
