"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.createRuntimeValueStore = void 0;
const createRuntimeValueStore = (initialSnapshot) => {
    let snapshot = initialSnapshot;
    const listeners = new Set();
    const store = {
        getSnapshot: () => snapshot,
        subscribe: (listener) => {
            listeners.add(listener);
            return () => {
                listeners.delete(listener);
            };
        },
    };
    return {
        store,
        setSnapshot: (newSnapshot) => {
            if (snapshot === newSnapshot) {
                return;
            }
            snapshot = newSnapshot;
            for (const listener of listeners) {
                listener(snapshot);
            }
        },
    };
};
exports.createRuntimeValueStore = createRuntimeValueStore;
