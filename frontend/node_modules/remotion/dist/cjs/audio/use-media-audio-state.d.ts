export type MediaAudioState = {
    readonly isMutedForTimeline: boolean;
    readonly isMutedForPlayback: boolean;
    readonly shouldUseAudio: boolean;
};
export declare const resolveMediaAudioState: ({ muted, playerMuted, volume, isInsideFreeze, audioEnabled, }: {
    readonly muted: boolean;
    readonly playerMuted: boolean;
    readonly volume: number | null;
    readonly isInsideFreeze: boolean;
    readonly audioEnabled: boolean;
}) => MediaAudioState;
export declare const useMediaAudioState: ({ muted, volume, audioEnabled, }: {
    readonly muted: boolean;
    readonly volume: number | null;
    readonly audioEnabled: boolean;
}) => MediaAudioState;
