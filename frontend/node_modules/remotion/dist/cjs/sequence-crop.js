"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.validateSequenceCrop = exports.getSequenceCropClipPath = exports.resolveSequenceCrop = void 0;
const clampCrop = (value) => {
    return Math.min(1, Math.max(0, value !== null && value !== void 0 ? value : 0));
};
const resolveAxis = (start, end) => {
    const resolvedStart = clampCrop(start);
    const resolvedEnd = clampCrop(end);
    if (resolvedStart + resolvedEnd > 1) {
        return [0.5, 0.5];
    }
    return [resolvedStart, resolvedEnd];
};
const resolveSequenceCrop = ({ cropLeft, cropRight, cropTop, cropBottom, }) => {
    const [left, right] = resolveAxis(cropLeft, cropRight);
    const [top, bottom] = resolveAxis(cropTop, cropBottom);
    return { left, right, top, bottom };
};
exports.resolveSequenceCrop = resolveSequenceCrop;
const getSequenceCropClipPath = ({ left, right, top, bottom, style, }) => {
    if (left === 0 && right === 0 && top === 0 && bottom === 0) {
        return null;
    }
    const serializeRadius = (radius) => typeof radius === 'number' ? `${radius}px` : radius;
    const shorthand = serializeRadius(style === null || style === void 0 ? void 0 : style.borderRadius);
    const longhands = [
        style === null || style === void 0 ? void 0 : style.borderTopLeftRadius,
        style === null || style === void 0 ? void 0 : style.borderTopRightRadius,
        style === null || style === void 0 ? void 0 : style.borderBottomRightRadius,
        style === null || style === void 0 ? void 0 : style.borderBottomLeftRadius,
    ];
    const serializedBorderRadius = shorthand ||
        (longhands.some((radius) => radius !== undefined)
            ? longhands.map((radius) => {
                var _a;
                return (_a = serializeRadius(radius)) !== null && _a !== void 0 ? _a : '0px';
            }).join(' ')
            : undefined);
    const rounded = serializedBorderRadius
        ? ` round ${serializedBorderRadius}`
        : '';
    return `inset(${top * 100}% ${right * 100}% ${bottom * 100}% ${left * 100}%${rounded})`;
};
exports.getSequenceCropClipPath = getSequenceCropClipPath;
const validateSequenceCrop = (crop, componentName = '<Sequence />') => {
    for (const [name, value] of Object.entries(crop)) {
        if (value === undefined) {
            continue;
        }
        if (typeof value !== 'number' || !Number.isFinite(value)) {
            throw new TypeError(`The "${name}" prop of ${componentName} must be a finite number, but got ${String(value)}.`);
        }
        if (value > 100) {
            throw new RangeError(`The "${name}" prop of ${componentName} must be between 0 and 1, but got ${value}. The crop range is 0 to 1, not 0 to 100.`);
        }
    }
};
exports.validateSequenceCrop = validateSequenceCrop;
