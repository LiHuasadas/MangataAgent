export type MediaSyncAction = {
    type: 'seek-due-to-shift';
    shouldBeTime: number;
    why: string;
    bufferUntilFirstFrame: boolean;
    playReason: string | null;
    warnAboutNonSeekable: boolean;
} | {
    type: 'seek-if-not-playing';
    shouldBeTime: number;
    why: string | null;
} | {
    type: 'play-and-seek';
    shouldBeTime: number;
    why: string | null;
    playReason: string;
    bufferUntilFirstFrame: boolean;
} | {
    type: 'none';
};
export type GetMediaSyncActionInput = {
    duration: number;
    currentTime: number;
    paused: boolean;
    ended: boolean;
    desiredUnclampedTime: number;
    mediaTagTime: number;
    mediaTagLastUpdate: number;
    rvcTime: number | null;
    rvcLastUpdate: number | null;
    isVariableFpsVideo: boolean;
    acceptableTimeShift: number;
    lastSeekDueToShift: number | null;
    playing: boolean;
    playbackRate: number;
    mediaTagBufferingOrStalled: boolean;
    playerBuffering: boolean;
    absoluteFrame: number;
    onlyWarnForMediaSeekingError: boolean;
    isPremounting: boolean;
    isPostmounting: boolean;
    pauseWhenBuffering: boolean;
};
export declare const getMediaSyncAction: (input: GetMediaSyncActionInput) => MediaSyncAction;
