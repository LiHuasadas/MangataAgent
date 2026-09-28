import type React from 'react';
import { type SequenceCropInput } from './sequence-crop.js';
export declare const useCropStyle: ({ cropLeft, cropRight, cropTop, cropBottom, style, componentName, }: SequenceCropInput & {
    readonly style: React.CSSProperties | null;
    readonly componentName: string;
}) => React.CSSProperties | null;
