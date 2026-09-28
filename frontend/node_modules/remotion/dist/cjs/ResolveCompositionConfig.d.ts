import type { AnyComposition } from './CompositionManager.js';
import type { VideoConfigMetadataSource } from './resolve-video-config.js';
import type { VideoConfig } from './video-config.js';
type ResolveCompositionConfigContect = Record<string, VideoConfigState | undefined>;
export declare const ResolveCompositionContext: import("react").Context<ResolveCompositionConfigContect | null>;
export declare const resolveCompositionsRef: import("react").RefObject<{
    setCurrentRenderModalComposition: (compositionId: string | null) => void;
    reloadCurrentlySelectedComposition: () => void;
    resolveComposition: (compositionId: string) => Promise<VideoConfig>;
} | null>;
type VideoConfigState = {
    type: 'loading';
} | {
    type: 'success';
    result: VideoConfig;
    metadataSource: VideoConfigMetadataSource | null;
} | {
    type: 'success-and-refreshing';
    result: VideoConfig;
    metadataSource: VideoConfigMetadataSource | null;
} | {
    type: 'error';
    error: Error;
};
export declare const needsResolution: (composition: AnyComposition) => boolean;
export declare const useResolvedVideoConfig: (preferredCompositionId: string | null) => VideoConfigState | null;
export {};
