"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Folder = exports.FolderContext = void 0;
const jsx_runtime_1 = require("react/jsx-runtime");
const react_1 = require("react");
const CompositionManagerContext_js_1 = require("./CompositionManagerContext.js");
const sequence_order_marker_js_1 = require("./sequence-order-marker.js");
const truthy_js_1 = require("./truthy.js");
const use_remotion_environment_js_1 = require("./use-remotion-environment.js");
const validate_folder_name_js_1 = require("./validation/validate-folder-name.js");
exports.FolderContext = (0, react_1.createContext)({
    folderName: null,
    parentName: null,
});
/*
 * @description By wrapping a <Composition /> inside a <Folder />, you can visually categorize it in your sidebar, should you have many compositions.
 * @see [Documentation](https://remotion.dev/docs/folder)
 */
const Folder = (props) => {
    var _a;
    const { name, children } = props;
    const parent = (0, react_1.useContext)(exports.FolderContext);
    const { registerFolder, unregisterFolder } = (0, react_1.useContext)(CompositionManagerContext_js_1.CompositionSetters);
    const environment = (0, use_remotion_environment_js_1.useRemotionEnvironment)();
    const stack = (_a = props
        ._remotionInternalStack) !== null && _a !== void 0 ? _a : null;
    (0, validate_folder_name_js_1.validateFolderName)(name);
    const parentNameArr = [parent.parentName, parent.folderName].filter(truthy_js_1.truthy);
    const parentName = parentNameArr.length === 0 ? null : parentNameArr.join('/');
    const value = (0, react_1.useMemo)(() => {
        return {
            folderName: name,
            parentName,
        };
    }, [name, parentName]);
    (0, react_1.useEffect)(() => {
        registerFolder(name, parentName, stack);
        return () => {
            unregisterFolder(name, parentName);
        };
    }, [
        name,
        parent.folderName,
        parentName,
        registerFolder,
        unregisterFolder,
        stack,
    ]);
    const folder = (jsx_runtime_1.jsx(exports.FolderContext.Provider, { value: value, children: children }));
    return environment.isStudio ? (jsx_runtime_1.jsx(sequence_order_marker_js_1.FolderOrderMarker, { folderId: (0, sequence_order_marker_js_1.getFolderOrderId)({ name, parent: parentName }), children: folder })) : (folder);
};
exports.Folder = Folder;
