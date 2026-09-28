import React from 'react';
import type { EffectDefinitionAndStack } from '../effects/effect-types.js';
export type AnimatedImageCanvasRef = {
    readonly draw: (imageData: VideoFrame) => Promise<boolean>;
    readonly getCanvas: () => HTMLCanvasElement | null;
    clear: () => void;
};
export declare const Canvas: React.ForwardRefExoticComponent<{
    readonly width?: number | undefined;
    readonly height?: number | undefined;
    readonly fit: import("../calculate-image-fit.js").ImageFit;
    readonly className?: string | undefined;
    readonly style?: React.CSSProperties | undefined;
    readonly effects: EffectDefinitionAndStack<unknown>[];
} & React.AriaAttributes & Record<`data-${string}`, string | undefined> & React.RefAttributes<AnimatedImageCanvasRef>>;
