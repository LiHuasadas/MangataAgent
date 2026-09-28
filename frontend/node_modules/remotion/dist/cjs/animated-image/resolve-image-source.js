"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveAnimatedImageSource = void 0;
const resolveAnimatedImageSource = (src) => {
    if (typeof window === 'undefined') {
        return src;
    }
    return new URL(src, document.baseURI).href;
};
exports.resolveAnimatedImageSource = resolveAnimatedImageSource;
