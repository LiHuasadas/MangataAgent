import type { LogLevel } from './log.js';
import type { RemotionEnvironment } from './remotion-environment-context.js';
export { DELAY_RENDER_CALLSTACK_TOKEN, DELAY_RENDER_CLEAR_TOKEN, DELAY_RENDER_RETRIES_LEFT, DELAY_RENDER_RETRY_TOKEN, } from './delay-render-constants.js';
export type DelayRenderScope = {
    remotion_renderReady: boolean;
    remotion_delayRenderTimeouts: {
        [key: string]: {
            label: string | null;
            timeout: number | Timer;
            startTime: number;
        };
    };
    remotion_puppeteerTimeout: number;
    remotion_attempt: number;
    remotion_delayRenderHandles: number[];
    remotion_cancelledError?: string;
};
export type DelayRenderOptions = {
    timeoutInMilliseconds?: number;
    retries?: number;
};
/**
 * Internal function that accepts environment as parameter.
 * This allows useDelayRender to control its own environment source.
 * @private
 */
type DelayRenderInternalOptions = {
    scope: DelayRenderScope;
    environment: RemotionEnvironment;
    label: string | null;
    options: DelayRenderOptions;
};
export declare const delayRenderInternal: ({ scope, environment, label, options, }: DelayRenderInternalOptions) => number;
export declare const delayRender: (label?: string | undefined, options?: DelayRenderOptions | undefined) => number;
/**
 * Internal function that accepts environment as parameter.
 * @private
 */
type ContinueRenderInternalOptions = {
    scope: DelayRenderScope;
    handle: number;
    environment: RemotionEnvironment;
    logLevel: LogLevel;
};
export declare const continueRenderInternal: ({ scope, handle, environment, logLevel, }: ContinueRenderInternalOptions) => void;
export declare const continueRender: (handle: number) => void;
