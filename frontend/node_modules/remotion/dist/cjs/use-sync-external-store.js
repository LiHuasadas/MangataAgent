"use strict";
/**
 * @license React
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 * Adapted from use-sync-external-store 1.5.0.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var _a;
Object.defineProperty(exports, "__esModule", { value: true });
exports.useSyncExternalStore = void 0;
const React = __importStar(require("react"));
const objectIs = typeof Object.is === 'function'
    ? Object.is
    : (first, second) => (first === second &&
        (first !== 0 || 1 / first === 1 / second)) ||
        (Number.isNaN(first) && Number.isNaN(second));
let didWarnAboutUncachedGetSnapshot = false;
const checkIfSnapshotChanged = (instance) => {
    try {
        return !objectIs(instance.value, instance.getSnapshot());
    }
    catch (_a) {
        return true;
    }
};
const useSyncExternalStoreShimClient = (subscribe, getSnapshot) => {
    const value = getSnapshot();
    if (process.env.NODE_ENV !== 'production' &&
        !didWarnAboutUncachedGetSnapshot &&
        !objectIs(value, getSnapshot())) {
        // eslint-disable-next-line no-console
        console.error('The result of getSnapshot should be cached to avoid an infinite loop');
        didWarnAboutUncachedGetSnapshot = true;
    }
    const [{ instance }, forceUpdate] = React.useState({
        instance: { value, getSnapshot },
    });
    React.useLayoutEffect(() => {
        instance.value = value;
        instance.getSnapshot = getSnapshot;
        if (checkIfSnapshotChanged(instance)) {
            forceUpdate({ instance });
        }
    }, [getSnapshot, instance, subscribe, value]);
    React.useEffect(() => {
        if (checkIfSnapshotChanged(instance)) {
            forceUpdate({ instance });
        }
        return subscribe(() => {
            if (checkIfSnapshotChanged(instance)) {
                forceUpdate({ instance });
            }
        });
    }, [instance, subscribe]);
    React.useDebugValue(value);
    return value;
};
const useSyncExternalStoreShimServer = (_subscribe, getSnapshot) => getSnapshot();
const shim = typeof window === 'undefined' ||
    typeof window.document === 'undefined' ||
    typeof window.document.createElement === 'undefined'
    ? useSyncExternalStoreShimServer
    : useSyncExternalStoreShimClient;
exports.useSyncExternalStore = (_a = React.useSyncExternalStore) !== null && _a !== void 0 ? _a : shim;
