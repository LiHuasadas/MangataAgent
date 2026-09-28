"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getAssetDisplayName = void 0;
const getAssetDisplayName = (filename) => {
    var _a;
    if (filename.startsWith('data:')) {
        return 'Data URL';
    }
    if (filename.startsWith('blob:')) {
        const staticFile = typeof window === 'undefined'
            ? undefined
            : (_a = window.remotion_staticFiles) === null || _a === void 0 ? void 0 : _a.find((file) => file.src === filename);
        return staticFile ? (0, exports.getAssetDisplayName)(staticFile.name) : 'Blob URL';
    }
    const splitted = filename
        .split('/')
        .map((s) => s.split('\\'))
        .flat(1);
    const name = splitted[splitted.length - 1];
    try {
        return decodeURIComponent(name);
    }
    catch (_b) {
        return name;
    }
};
exports.getAssetDisplayName = getAssetDisplayName;
