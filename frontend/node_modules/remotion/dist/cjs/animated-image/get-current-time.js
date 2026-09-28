"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getCurrentTime = void 0;
const getCurrentTime = ({ frame, playbackRate, fps, }) => {
    return (frame * playbackRate) / fps;
};
exports.getCurrentTime = getCurrentTime;
