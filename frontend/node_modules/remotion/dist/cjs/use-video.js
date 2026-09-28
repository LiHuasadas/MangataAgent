"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.useVideo = void 0;
const react_1 = require("react");
const CompositionManagerContext_js_1 = require("./CompositionManagerContext.js");
const ResolveCompositionConfig_js_1 = require("./ResolveCompositionConfig.js");
const AssetPreviewComposition = () => null;
const useVideo = () => {
    var _a;
    const { canvasContent, compositions, currentCompositionMetadata, currentAssetMetadata, } = (0, react_1.useContext)(CompositionManagerContext_js_1.CompositionManager);
    const selected = compositions.find((c) => {
        return ((canvasContent === null || canvasContent === void 0 ? void 0 : canvasContent.type) === 'composition' &&
            c.id === canvasContent.compositionId);
    });
    const resolved = (0, ResolveCompositionConfig_js_1.useResolvedVideoConfig)((_a = selected === null || selected === void 0 ? void 0 : selected.id) !== null && _a !== void 0 ? _a : null);
    return (0, react_1.useMemo)(() => {
        var _a;
        if ((canvasContent === null || canvasContent === void 0 ? void 0 : canvasContent.type) === 'asset' &&
            (currentAssetMetadata === null || currentAssetMetadata === void 0 ? void 0 : currentAssetMetadata.asset) === canvasContent.asset) {
            return {
                ...currentAssetMetadata,
                id: (0, CompositionManagerContext_js_1.getAssetPreviewCompositionId)(canvasContent.asset),
                defaultProps: {},
                component: AssetPreviewComposition,
            };
        }
        if (!resolved) {
            return null;
        }
        if (resolved.type === 'error') {
            return null;
        }
        if (resolved.type === 'loading') {
            return null;
        }
        if (!selected) {
            return null;
        }
        return {
            ...resolved.result,
            defaultProps: (_a = selected.defaultProps) !== null && _a !== void 0 ? _a : {},
            id: selected.id,
            // We override the selected metadata with the metadata that was passed to renderMedia(),
            // and don't allow it to be changed during render anymore
            ...(currentCompositionMetadata !== null && currentCompositionMetadata !== void 0 ? currentCompositionMetadata : {}),
            component: selected.component,
        };
    }, [
        canvasContent,
        currentAssetMetadata,
        currentCompositionMetadata,
        resolved,
        selected,
    ]);
};
exports.useVideo = useVideo;
