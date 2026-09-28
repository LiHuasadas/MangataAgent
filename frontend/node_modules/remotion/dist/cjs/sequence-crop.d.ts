import type { CSSProperties } from 'react';
export type ResolvedSequenceCrop = {
    readonly left: number;
    readonly right: number;
    readonly top: number;
    readonly bottom: number;
};
type ResolvedSequenceCropWithStyle = ResolvedSequenceCrop & {
    readonly style: CSSProperties | null | undefined;
};
export type SequenceCropInput = {
    readonly cropLeft?: number;
    readonly cropRight?: number;
    readonly cropTop?: number;
    readonly cropBottom?: number;
};
export declare const resolveSequenceCrop: ({ cropLeft, cropRight, cropTop, cropBottom, }: SequenceCropInput) => ResolvedSequenceCrop;
export declare const getSequenceCropClipPath: ({ left, right, top, bottom, style, }: ResolvedSequenceCropWithStyle) => string | null;
export declare const validateSequenceCrop: (crop: SequenceCropInput, componentName?: string) => void;
export {};
