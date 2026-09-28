"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.interpolateKeyframedStatus = exports.setInterpolatePaths = void 0;
const bezier_js_1 = require("./bezier.js");
const easing_js_1 = require("./easing.js");
const interpolate_colors_js_1 = require("./interpolate-colors.js");
const interpolate_js_1 = require("./interpolate.js");
// Studio supplies the path interpolator to avoid a dependency from remotion
// to @remotion/paths, which itself uses remotion's interpolation timing.
let interpolatePaths = null;
const setInterpolatePaths = (interpolator) => {
    interpolatePaths = interpolator;
};
exports.setInterpolatePaths = setInterpolatePaths;
const easingToFn = ({ easing, forceSpringAllowTail, }) => {
    var _a, _b;
    switch (easing.type) {
        case 'linear':
            return easing_js_1.Easing.linear;
        case 'step1':
            return easing_js_1.Easing.step1;
        case 'spring':
            return easing_js_1.Easing.spring({
                allowTail: (_a = forceSpringAllowTail !== null && forceSpringAllowTail !== void 0 ? forceSpringAllowTail : easing.allowTail) !== null && _a !== void 0 ? _a : undefined,
                damping: easing.damping,
                durationRestThreshold: (_b = easing.durationRestThreshold) !== null && _b !== void 0 ? _b : undefined,
                mass: easing.mass,
                overshootClamping: easing.overshootClamping,
                stiffness: easing.stiffness,
            });
        case 'bezier':
            return (0, bezier_js_1.bezier)(easing.x1, easing.y1, easing.x2, easing.y2);
        default:
            throw new TypeError(`Unsupported easing: ${JSON.stringify(easing)}`);
    }
};
const interpolateKeyframedStatus = ({ frame, forceSpringAllowTail, status, }) => {
    const { keyframes, easing, clamping, interpolationFunction } = status;
    if (keyframes.length === 0) {
        return null;
    }
    const sortedKeyframes = [...keyframes].sort((a, b) => a.frame - b.frame);
    const inputRange = sortedKeyframes.map((k) => k.frame);
    const outputs = sortedKeyframes.map((k) => k.value);
    if (interpolationFunction === 'interpolatePaths') {
        if (!outputs.every((v) => typeof v === 'string')) {
            return null;
        }
        if (keyframes.length === 1) {
            return outputs[0];
        }
        if (!interpolatePaths ||
            clamping.left === 'identity' ||
            clamping.right === 'identity') {
            return null;
        }
        try {
            return interpolatePaths(frame, inputRange, outputs, {
                easing: easing.map((e) => easingToFn({ easing: e, forceSpringAllowTail })),
                extrapolateLeft: clamping.left,
                extrapolateRight: clamping.right,
                posterize: status.posterize,
            });
        }
        catch (_a) {
            return null;
        }
    }
    if (interpolationFunction === 'interpolateColors') {
        if (!outputs.every((v) => typeof v === 'string')) {
            return null;
        }
        if (keyframes.length === 1) {
            return outputs[0];
        }
        try {
            return (0, interpolate_colors_js_1.interpolateColors)(frame, inputRange, outputs, {
                easing: easing.map((e) => easingToFn({ easing: e, forceSpringAllowTail })),
                posterize: status.posterize,
            });
        }
        catch (_b) {
            return null;
        }
    }
    if (interpolationFunction !== 'interpolate') {
        return null;
    }
    try {
        return (0, interpolate_js_1.interpolate)(frame, inputRange, outputs, {
            easing: easing.map((e) => easingToFn({ easing: e, forceSpringAllowTail })),
            extrapolateLeft: clamping.left,
            extrapolateRight: clamping.right,
            output: status.output,
            posterize: status.posterize,
        });
    }
    catch (_c) {
        return null;
    }
};
exports.interpolateKeyframedStatus = interpolateKeyframedStatus;
