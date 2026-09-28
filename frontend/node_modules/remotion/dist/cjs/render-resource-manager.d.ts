import React from 'react';
export type RenderResourceManager = {
    getOrCreateResource: <T>({ key, create }: {
        key: string;
        create: () => {
            resource: T;
            dispose: () => void;
        };
    }) => T;
    dispose: () => void;
};
export declare const makeRenderResourceManager: () => RenderResourceManager;
export declare const RenderResourceManagerContext: React.Context<RenderResourceManager | null>;
