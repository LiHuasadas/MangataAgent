"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.usePlaying = void 0;
const react_1 = require("react");
const timeline_position_state_js_1 = require("./timeline-position-state.js");
const TimelineContext_js_1 = require("./TimelineContext.js");
const use_sync_external_store_js_1 = require("./use-sync-external-store.js");
const usePlaying = () => {
    const { isPlaying } = (0, timeline_position_state_js_1.useTimelineContext)();
    const { subscribePlaying } = (0, react_1.useContext)(TimelineContext_js_1.SetTimelineContext);
    // Read the local Freeze override, but subscribe to the shared playing store.
    return (0, use_sync_external_store_js_1.useSyncExternalStore)(subscribePlaying, isPlaying, isPlaying);
};
exports.usePlaying = usePlaying;
