"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useBuffering = void 0;
const react_1 = require("react");
const TimelineContext_js_1 = require("./TimelineContext.js");
const use_sync_external_store_js_1 = require("./use-sync-external-store.js");
const useBuffering = () => {
    const { isBuffering, subscribeBuffering } = (0, react_1.useContext)(TimelineContext_js_1.SetTimelineContext);
    return (0, use_sync_external_store_js_1.useSyncExternalStore)(subscribeBuffering, isBuffering, isBuffering);
};
exports.useBuffering = useBuffering;
