import type React from 'react';
export declare const usePremounting: ({ from, durationInFrames, premountFor, postmountFor, style, styleWhilePremounted, styleWhilePostmounted, hideWhilePremounted, }: {
    readonly from: number;
    readonly durationInFrames: number;
    readonly premountFor: number | null;
    readonly postmountFor: number | null;
    readonly style: React.CSSProperties | null;
    readonly styleWhilePremounted: React.CSSProperties | null;
    readonly styleWhilePostmounted: React.CSSProperties | null;
    readonly hideWhilePremounted: "display-none" | "opacity";
}) => {
    effectivePremountFor: number;
    effectivePostmountFor: number;
    premountingActive: boolean;
    postmountingActive: boolean;
    isPremountingOrPostmounting: boolean;
    freezeFrame: number;
    premountingStyle: React.CSSProperties | null;
};
