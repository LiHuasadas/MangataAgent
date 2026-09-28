"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CompositionSetters = exports.CompositionManager = exports.getAssetPreviewCompositionId = void 0;
const react_1 = require("react");
const getAssetPreviewCompositionId = (asset) => `asset:${asset}`;
exports.getAssetPreviewCompositionId = getAssetPreviewCompositionId;
exports.CompositionManager = (0, react_1.createContext)({
    compositions: [],
    folders: [],
    currentCompositionMetadata: null,
    currentAssetMetadata: null,
    canvasContent: null,
});
exports.CompositionSetters = (0, react_1.createContext)({
    registerComposition: () => undefined,
    unregisterComposition: () => undefined,
    registerFolder: () => undefined,
    unregisterFolder: () => undefined,
    setCanvasContent: () => undefined,
    setCurrentAssetMetadata: () => undefined,
    onlyRenderComposition: null,
});
