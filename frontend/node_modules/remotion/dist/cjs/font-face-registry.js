"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getRegisteredFontFaces = exports.registerFontFace = exports.fetchFontData = void 0;
const registeredFontFaces = [];
const fontDataByUrl = new Map();
const fetchFontData = (fontUrl) => {
    const cached = fontDataByUrl.get(fontUrl);
    if (cached) {
        return cached;
    }
    const promise = fetch(fontUrl)
        .then((response) => {
        if (!response.ok) {
            throw new Error(`Failed to load font ${JSON.stringify(fontUrl)}: ${response.status} ${response.statusText}`);
        }
        return response.arrayBuffer();
    })
        .catch((error) => {
        fontDataByUrl.delete(fontUrl);
        throw error;
    });
    fontDataByUrl.set(fontUrl, promise);
    return promise;
};
exports.fetchFontData = fetchFontData;
const registerFontFace = (fontFace) => {
    if (registeredFontFaces.some((registered) => registered.ascentOverride === fontFace.ascentOverride &&
        registered.descentOverride === fontFace.descentOverride &&
        registered.display === fontFace.display &&
        registered.featureSettings === fontFace.featureSettings &&
        registered.fontFamily === fontFace.fontFamily &&
        registered.fontUrl === fontFace.fontUrl &&
        registered.format === fontFace.format &&
        registered.lineGapOverride === fontFace.lineGapOverride &&
        registered.style === fontFace.style &&
        registered.weight === fontFace.weight &&
        registered.stretch === fontFace.stretch &&
        registered.unicodeRange === fontFace.unicodeRange &&
        registered.variant === fontFace.variant)) {
        return;
    }
    registeredFontFaces.push(fontFace);
};
exports.registerFontFace = registerFontFace;
const getRegisteredFontFaces = () => {
    return registeredFontFaces.slice();
};
exports.getRegisteredFontFaces = getRegisteredFontFaces;
