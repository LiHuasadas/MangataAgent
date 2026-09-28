"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useTimelineSeek = void 0;
const react_1 = require("react");
// One instance per timeline, shared by Studio and Player. Keep the revision
// outside the React updater: updaters may be deferred or run more than once.
const useTimelineSeek = (setFrame) => {
    const revision = (0, react_1.useRef)(0);
    return (0, react_1.useMemo)(() => ({
        revision,
        seekFrame: (frame) => {
            // Even a same-frame seek is a boundary for the next media update.
            revision.current++;
            setFrame(frame);
        },
    }), [setFrame]);
};
exports.useTimelineSeek = useTimelineSeek;
