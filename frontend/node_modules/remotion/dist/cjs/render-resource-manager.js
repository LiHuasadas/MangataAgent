"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.RenderResourceManagerContext = exports.makeRenderResourceManager = void 0;
const react_1 = __importDefault(require("react"));
const makeRenderResourceManager = () => {
    const resources = new Map();
    let disposed = false;
    return {
        getOrCreateResource: ({ key, create, }) => {
            if (disposed) {
                throw new Error('Render resource manager has already been disposed');
            }
            const existing = resources.get(key);
            if (existing) {
                return existing.resource;
            }
            const created = create();
            resources.set(key, created);
            return created.resource;
        },
        dispose: () => {
            if (disposed) {
                return;
            }
            disposed = true;
            const resourcesToDispose = Array.from(resources.values());
            resources.clear();
            let firstError = null;
            for (const resource of resourcesToDispose) {
                try {
                    resource.dispose();
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
exports.makeRenderResourceManager = makeRenderResourceManager;
exports.RenderResourceManagerContext = react_1.default.createContext(null);
