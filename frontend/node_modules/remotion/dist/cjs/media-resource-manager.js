"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.globalMediaResourceManager = exports.MEDIABUNNY_DURATION_VALUE_KEY = exports.getMediabunnyInputResourceKey = exports.makeMediaResourceManager = void 0;
const disposeResource = (resource) => {
    if (resource.disposed) {
        return;
    }
    resource.disposed = true;
    resource.values.clear();
    resource.dispose();
};
const makeMediaResourceManager = () => {
    const resources = new Map();
    let disposed = false;
    return {
        acquire: ({ key, create, }) => {
            if (disposed) {
                throw new Error('Media resource manager has already been disposed');
            }
            let entry = resources.get(key);
            if (!entry) {
                const created = create();
                entry = {
                    resource: created.resource,
                    dispose: created.dispose,
                    refCount: 0,
                    disposeGeneration: 0,
                    disposed: false,
                    values: new Map(),
                };
                resources.set(key, entry);
            }
            entry.refCount++;
            entry.disposeGeneration++;
            let released = false;
            return {
                resource: entry.resource,
                getOrCreateValue: (valueKey, createValue) => {
                    if (entry.values.has(valueKey)) {
                        return entry.values.get(valueKey);
                    }
                    const value = createValue();
                    entry.values.set(valueKey, value);
                    return value;
                },
                release: () => {
                    if (released) {
                        return;
                    }
                    released = true;
                    entry.refCount--;
                    if (entry.refCount !== 0) {
                        return;
                    }
                    const disposeGeneration = ++entry.disposeGeneration;
                    queueMicrotask(() => {
                        if (entry.refCount !== 0 ||
                            entry.disposeGeneration !== disposeGeneration) {
                            return;
                        }
                        if (resources.get(key) === entry) {
                            resources.delete(key);
                        }
                        disposeResource(entry);
                    });
                },
            };
        },
        invalidate: (key) => {
            const entry = resources.get(key);
            if (!entry) {
                return;
            }
            resources.delete(key);
            entry.disposeGeneration++;
            if (entry.refCount === 0) {
                disposeResource(entry);
            }
        },
        dispose: () => {
            if (disposed) {
                return;
            }
            disposed = true;
            const entries = Array.from(resources.values());
            resources.clear();
            let firstError = null;
            for (const entry of entries) {
                try {
                    disposeResource(entry);
                }
                catch (error) {
                    firstError !== null && firstError !== void 0 ? firstError : (firstError = error);
                }
            }
            if (firstError !== null) {
                throw firstError;
            }
        },
    };
};
exports.makeMediaResourceManager = makeMediaResourceManager;
const getMediabunnyInputResourceKey = ({ src, credentials, requestInitFingerprint, revision, }) => JSON.stringify([
    'mediabunny-input',
    src,
    credentials,
    requestInitFingerprint,
    revision,
]);
exports.getMediabunnyInputResourceKey = getMediabunnyInputResourceKey;
exports.MEDIABUNNY_DURATION_VALUE_KEY = 'mediabunny-duration';
exports.globalMediaResourceManager = (0, exports.makeMediaResourceManager)();
