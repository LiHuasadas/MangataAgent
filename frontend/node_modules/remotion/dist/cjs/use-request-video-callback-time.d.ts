import type { RefObject } from 'react';
export declare const useRequestVideoCallbackTime: ({ mediaRef, mediaType, lastSeek, onVariableFpsVideoDetected, }: {
    mediaRef: RefObject<HTMLAudioElement | HTMLVideoElement | null>;
    mediaType: "audio" | "video";
    lastSeek: RefObject<number | null>;
    onVariableFpsVideoDetected: () => void;
}) => RefObject<{
    time: number;
    lastUpdate: number;
} | null>;
