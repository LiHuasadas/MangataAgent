import type { RefObject } from 'react';
import React from 'react';
import { type PlayableMediaTag } from './timeline-position-state';
import { type TimelineSeek } from './use-timeline-seek';
export type TimelineContextValue = {
    frame: Record<string, number>;
    isPlaying: () => boolean;
    isInsideFreeze: boolean;
    audioAndVideoTags: RefObject<PlayableMediaTag[]>;
};
export type PlaybackRateContextValue = {
    playbackRate: number;
    setPlaybackRate: (u: React.SetStateAction<number>) => void;
};
export type PlayingState = Readonly<{
    playing: boolean;
}>;
export type BufferingState = Readonly<{
    buffering: boolean;
}>;
export type SetTimelineContextValue = {
    seek: TimelineSeek | null;
    setFrameWithoutSeek: (u: React.SetStateAction<Record<string, number>>) => void;
    setPlaying: (u: React.SetStateAction<boolean>) => void;
    setBuffering: (buffering: boolean) => void;
    subscribePlaying: (listener: (state: PlayingState) => void) => () => void;
    subscribeBuffering: (listener: (state: BufferingState) => void) => () => void;
    isPlaying: () => boolean;
    isBuffering: () => boolean;
    frameRef: RefObject<Record<string, number>>;
    audioAndVideoTags: RefObject<PlayableMediaTag[]>;
};
export declare const SetTimelineContext: React.Context<SetTimelineContextValue>;
export declare const TimelineContext: React.Context<TimelineContextValue | null>;
export declare const PlaybackRateContext: React.Context<PlaybackRateContextValue | null>;
export declare const AbsoluteTimeContext: React.Context<TimelineContextValue | null>;
export declare const TimelineContextProvider: React.FC<{
    readonly children: React.ReactNode;
    readonly frameState: Record<string, number> | null;
}>;
