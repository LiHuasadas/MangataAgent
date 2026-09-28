"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useMediaAudioState = exports.resolveMediaAudioState = void 0;
const timeline_position_state_js_1 = require("../timeline-position-state.js");
const volume_position_state_js_1 = require("../volume-position-state.js");
const resolveMediaAudioState = ({ muted, playerMuted, volume, isInsideFreeze, audioEnabled, }) => {
    const isMutedForTimeline = muted || isInsideFreeze;
    const isMutedForPlayback = isMutedForTimeline || playerMuted || (volume !== null && volume <= 0);
    return {
        isMutedForTimeline,
        isMutedForPlayback,
        shouldUseAudio: audioEnabled && !isMutedForPlayback,
    };
};
exports.resolveMediaAudioState = resolveMediaAudioState;
const useMediaAudioState = ({ muted, volume, audioEnabled, }) => {
    const [playerMuted] = (0, volume_position_state_js_1.usePlayerMutedState)();
    const isInsideFreeze = (0, timeline_position_state_js_1.useIsInsideFreeze)();
    return (0, exports.resolveMediaAudioState)({
        muted,
        playerMuted,
        volume,
        isInsideFreeze,
        audioEnabled,
    });
};
exports.useMediaAudioState = useMediaAudioState;
