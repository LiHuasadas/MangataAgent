import { type PlaybackRateContextValue, type TimelineContextValue } from './TimelineContext.js';
export type PlayableMediaTag = {
    play: (reason: string) => void;
    id: string;
};
type CurrentTimePerComposition = Record<string, number>;
export declare const persistCurrentFrame: (time: CurrentTimePerComposition) => void;
export declare const getInitialFrameState: () => CurrentTimePerComposition;
export declare const getFrameForComposition: (composition: string) => number;
export declare const clampFrameToCompositionRange: (frame: number, durationInFrames: number) => number;
export declare const useTimelineContext: () => TimelineContextValue;
export declare const usePlaybackRate: () => PlaybackRateContextValue;
export declare const useTimelinePosition: () => number;
export declare const useIsInsideFreeze: () => boolean;
export declare const useAbsoluteTimelinePosition: () => number;
export declare const useTimelineSetFrameWithoutSeek: () => (u: import("react").SetStateAction<Record<string, number>>) => void;
export declare const useTimelineSeekFrame: () => (frame: import("react").SetStateAction<Record<string, number>>) => void;
export { usePlaying } from './use-playing.js';
export { useBuffering } from './use-buffering.js';
