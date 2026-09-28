import type { AnyZodObject } from './any-zod-type.js';
import type { CalculateMetadataFunction } from './Composition.js';
import type { InferProps } from './props-if-has-props.js';
import type { VideoConfig } from './video-config.js';
type ResolveVideoConfigParams = {
    compositionId: string;
    compositionWidth: number | null;
    compositionHeight: number | null;
    compositionFps: number | null;
    compositionDurationInFrames: number | null;
    calculateMetadata: CalculateMetadataFunction<InferProps<AnyZodObject, Record<string, unknown>>> | null;
    signal: AbortSignal;
    defaultProps: Record<string, unknown>;
    inputProps: Record<string, unknown>;
};
export type VideoConfigMetadataSource = {
    readonly durationInFrames: 'calculate-metadata' | 'composition';
    readonly fps: 'calculate-metadata' | 'composition';
    readonly height: 'calculate-metadata' | 'composition';
    readonly width: 'calculate-metadata' | 'composition';
};
export type VideoConfigWithMetadata = {
    readonly metadataSource: VideoConfigMetadataSource;
    readonly videoConfig: VideoConfig;
};
export declare const resolveVideoConfigWithMetadata: ({ calculateMetadata, signal, defaultProps, inputProps: originalProps, compositionId, compositionDurationInFrames, compositionFps, compositionHeight, compositionWidth, }: ResolveVideoConfigParams) => Promise<VideoConfigWithMetadata> | VideoConfigWithMetadata;
export declare const resolveVideoConfig: (params: ResolveVideoConfigParams) => Promise<VideoConfig> | VideoConfig;
export declare const resolveVideoConfigWithMetadataOrCatch: (params: ResolveVideoConfigParams) => {
    type: "success";
    result: Promise<VideoConfigWithMetadata> | VideoConfigWithMetadata;
} | {
    type: "error";
    error: Error;
};
export declare const resolveVideoConfigOrCatch: (params: ResolveVideoConfigParams) => {
    type: "success";
    result: Promise<VideoConfig> | VideoConfig;
} | {
    type: "error";
    error: Error;
};
export {};
