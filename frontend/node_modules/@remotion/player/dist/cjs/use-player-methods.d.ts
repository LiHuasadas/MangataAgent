import type { SyntheticEvent } from 'react';
import type { PlayerEmitter } from './event-emitter.js';
export type UsePlayerMethods = {
    frameBack: (frames: number) => void;
    frameForward: (frames: number) => void;
    emitter: PlayerEmitter;
    play: (e?: SyntheticEvent | PointerEvent) => void;
    playAsAutoPlay: () => void;
    pause: () => void;
    pauseAndReturnToPlayStart: () => void;
    seek: (newFrame: number) => void;
    getCurrentFrame: () => number;
    isPlaying: () => boolean;
    isBuffering: () => boolean;
    toggle: (e?: SyntheticEvent | PointerEvent) => void;
};
export declare const usePlayerMethods: () => UsePlayerMethods;
