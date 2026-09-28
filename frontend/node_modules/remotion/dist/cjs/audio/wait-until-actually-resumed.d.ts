export type AudioContextResumeResult = 'resumed' | 'cancelled' | 'failed';
export declare const waitUntilActuallyResumed: (audioContext: AudioContext, logLevel: "error" | "info" | "trace" | "verbose" | "warn", signal: AbortSignal, isAutoPlayAttempt: boolean) => Promise<AudioContextResumeResult>;
