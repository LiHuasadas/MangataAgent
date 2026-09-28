"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.resolveV5Default = exports.ENABLE_V5_BREAKING_CHANGES = void 0;
exports.ENABLE_V5_BREAKING_CHANGES = false;
const resolveV5Default = (value) => {
    return value !== null && value !== void 0 ? value : exports.ENABLE_V5_BREAKING_CHANGES;
};
exports.resolveV5Default = resolveV5Default;
