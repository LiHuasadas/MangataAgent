"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommitOrderInternals = exports.CompositionManagerOrderMarker = exports.FolderOrderMarker = exports.CompositionOrderMarker = exports.SequenceManagerOrderMarker = exports.SequenceOrderMarker = exports.getFolderOrderId = exports.getCompositionAndFolderOrderKey = exports.COMMIT_ORDER_EVENT = exports.COMPOSITION_MANAGER_ORDER_MARKER = exports.FOLDER_ORDER_MARKER = exports.COMPOSITION_ORDER_MARKER = exports.SEQUENCE_MANAGER_ORDER_MARKER = exports.SEQUENCE_ORDER_MARKER = void 0;
exports.SEQUENCE_ORDER_MARKER = Symbol.for('remotion.sequence-order-marker');
exports.SEQUENCE_MANAGER_ORDER_MARKER = Symbol.for('remotion.sequence-manager-order-marker');
exports.COMPOSITION_ORDER_MARKER = Symbol.for('remotion.composition-order-marker');
exports.FOLDER_ORDER_MARKER = Symbol.for('remotion.folder-order-marker');
exports.COMPOSITION_MANAGER_ORDER_MARKER = Symbol.for('remotion.composition-manager-order-marker');
exports.COMMIT_ORDER_EVENT = 'remotion:commit-order';
const getCompositionAndFolderOrderKey = (item) => `${item.type}:${item.id}`;
exports.getCompositionAndFolderOrderKey = getCompositionAndFolderOrderKey;
const getFolderOrderId = ({ name, parent, }) => [parent, name].filter(Boolean).join('/');
exports.getFolderOrderId = getFolderOrderId;
const SequenceOrderMarker = ({ children }) => children;
exports.SequenceOrderMarker = SequenceOrderMarker;
Object.defineProperty(exports.SequenceOrderMarker, exports.SEQUENCE_ORDER_MARKER, {
    value: true,
});
const SequenceManagerOrderMarker = ({ children }) => children;
exports.SequenceManagerOrderMarker = SequenceManagerOrderMarker;
Object.defineProperty(exports.SequenceManagerOrderMarker, exports.SEQUENCE_MANAGER_ORDER_MARKER, {
    value: true,
});
const CompositionOrderMarker = ({ children }) => children;
exports.CompositionOrderMarker = CompositionOrderMarker;
Object.defineProperty(exports.CompositionOrderMarker, exports.COMPOSITION_ORDER_MARKER, {
    value: true,
});
const FolderOrderMarker = ({ children }) => children;
exports.FolderOrderMarker = FolderOrderMarker;
Object.defineProperty(exports.FolderOrderMarker, exports.FOLDER_ORDER_MARKER, {
    value: true,
});
const CompositionManagerOrderMarker = ({ children }) => children;
exports.CompositionManagerOrderMarker = CompositionManagerOrderMarker;
Object.defineProperty(exports.CompositionManagerOrderMarker, exports.COMPOSITION_MANAGER_ORDER_MARKER, { value: true });
exports.CommitOrderInternals = {
    compositionManagerMarker: exports.COMPOSITION_MANAGER_ORDER_MARKER,
    compositionMarker: exports.COMPOSITION_ORDER_MARKER,
    folderMarker: exports.FOLDER_ORDER_MARKER,
    sequenceManagerMarker: exports.SEQUENCE_MANAGER_ORDER_MARKER,
    sequenceMarker: exports.SEQUENCE_ORDER_MARKER,
    eventName: exports.COMMIT_ORDER_EVENT,
};
