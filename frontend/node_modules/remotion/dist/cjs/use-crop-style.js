"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useCropStyle = void 0;
const react_1 = require("react");
const sequence_crop_js_1 = require("./sequence-crop.js");
const useCropStyle = ({ cropLeft, cropRight, cropTop, cropBottom, style, componentName, }) => {
    (0, sequence_crop_js_1.validateSequenceCrop)({ cropLeft, cropRight, cropTop, cropBottom }, componentName);
    return (0, react_1.useMemo)(() => {
        const cropClipPath = (0, sequence_crop_js_1.getSequenceCropClipPath)({
            ...(0, sequence_crop_js_1.resolveSequenceCrop)({ cropLeft, cropRight, cropTop, cropBottom }),
            style,
        });
        if (cropClipPath === null) {
            return style;
        }
        return { ...style, clipPath: cropClipPath };
    }, [cropBottom, cropLeft, cropRight, cropTop, style]);
};
exports.useCropStyle = useCropStyle;
