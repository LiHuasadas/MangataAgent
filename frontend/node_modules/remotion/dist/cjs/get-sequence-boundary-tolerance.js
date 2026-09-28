"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSequenceBoundaryTolerance = void 0;
const getSequenceBoundaryTolerance = ({ absoluteFrame, cumulatedFrom, from, parentPlaybackRate, durationInFrames, }) => {
    // Nested rates can put exact boundaries a few floating-point units apart.
    return Math.min(durationInFrames / 2, Number.EPSILON *
        Math.max(Math.abs(absoluteFrame * parentPlaybackRate), Math.abs(cumulatedFrom * parentPlaybackRate), Math.abs(from)) *
        4);
};
exports.getSequenceBoundaryTolerance = getSequenceBoundaryTolerance;
