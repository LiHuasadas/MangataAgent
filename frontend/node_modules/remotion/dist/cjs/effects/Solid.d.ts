import React from 'react';
import type { InteractiveBaseProps, InteractivePremountProps, InteractiveCropProps } from '../Interactive.js';
import type { EffectsProp } from './effect-types.js';
type MandatoryProps = {
    readonly width: number;
    readonly height: number;
};
type OptionalProps = {
    readonly color: string | undefined;
    readonly effects: EffectsProp;
    readonly className: string | undefined;
    readonly style: React.CSSProperties | undefined;
    readonly pixelDensity: number | undefined;
};
export type SolidProps = MandatoryProps & Partial<OptionalProps> & InteractiveCropProps;
export declare const solidSchema: {
    readonly 'style.transformOrigin': {
        readonly type: "transform-origin";
        readonly step: 1;
        readonly default: "50% 50%";
        readonly description: "Transform origin";
    };
    readonly 'style.translate': {
        readonly type: "translate";
        readonly step: 1;
        readonly default: "0px 0px";
        readonly description: "Offset";
    };
    readonly 'style.scale': {
        readonly type: "scale";
        readonly max: 100;
        readonly step: 0.01;
        readonly default: 1;
        readonly description: "Scale";
        readonly defaultKeyframeOutput: "perceptual-scale";
    };
    readonly 'style.rotate': {
        readonly type: "rotation-css";
        readonly step: 1;
        readonly default: "0deg";
        readonly description: "Rotation";
    };
    readonly 'style.opacity': {
        readonly type: "number";
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.01;
        readonly default: 1;
        readonly description: "Opacity";
        readonly hiddenFromList: false;
    };
    readonly 'style.borderWidth': {
        readonly type: "number";
        readonly default: undefined;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Border width";
        readonly hiddenFromList: false;
    };
    readonly 'style.borderStyle': {
        readonly type: "enum";
        readonly default: "none";
        readonly description: "Border style";
        readonly variants: {
            readonly none: {};
            readonly hidden: {};
            readonly solid: {};
            readonly dashed: {};
            readonly dotted: {};
            readonly double: {};
            readonly groove: {};
            readonly ridge: {};
            readonly inset: {};
            readonly outset: {};
        };
    };
    readonly 'style.borderColor': {
        readonly type: "color";
        readonly default: undefined;
        readonly description: "Border color";
    };
    readonly 'style.borderRadius': {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Border radius";
        readonly hiddenFromList: false;
        readonly keyframable: true;
    };
    readonly 'style.borderTopLeftRadius': {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Top left radius";
        readonly hiddenFromList: false;
    };
    readonly 'style.borderTopRightRadius': {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Top right radius";
        readonly hiddenFromList: false;
    };
    readonly 'style.borderBottomRightRadius': {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Bottom right radius";
        readonly hiddenFromList: false;
    };
    readonly 'style.borderBottomLeftRadius': {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly description: "Bottom left radius";
        readonly hiddenFromList: false;
    };
    readonly 'style.backgroundColor': {
        readonly type: "color";
        readonly default: "transparent";
        readonly description: "Color";
    };
    readonly premountFor: {
        readonly type: "number";
        readonly default: 0;
        readonly description: "Premount For";
        readonly min: 0;
        readonly step: 1;
        readonly hiddenFromList: false;
        readonly keyframable: false;
    };
    readonly postmountFor: {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly hiddenFromList: true;
        readonly keyframable: false;
    };
    readonly cropLeft: {
        readonly type: "number";
        readonly default: 0;
        readonly description: "Crop left";
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.01;
        readonly hiddenFromList: false;
        readonly keyframable: true;
    };
    readonly cropRight: {
        readonly type: "number";
        readonly default: 0;
        readonly description: "Crop right";
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.01;
        readonly hiddenFromList: false;
        readonly keyframable: true;
    };
    readonly cropTop: {
        readonly type: "number";
        readonly default: 0;
        readonly description: "Crop top";
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.01;
        readonly hiddenFromList: false;
        readonly keyframable: true;
    };
    readonly cropBottom: {
        readonly type: "number";
        readonly default: 0;
        readonly description: "Crop bottom";
        readonly min: 0;
        readonly max: 1;
        readonly step: 0.01;
        readonly hiddenFromList: false;
        readonly keyframable: true;
    };
    readonly durationInFrames: {
        readonly type: "number";
        readonly default: undefined;
        readonly min: 1;
        readonly step: 1;
        readonly hiddenFromList: true;
    };
    readonly from: {
        readonly type: "number";
        readonly default: 0;
        readonly step: 1;
        readonly hiddenFromList: true;
    };
    readonly trimBefore: {
        readonly type: "number";
        readonly default: 0;
        readonly min: 0;
        readonly step: 1;
        readonly hiddenFromList: true;
    };
    readonly playbackRate: {
        readonly type: "number";
        readonly default: 1;
        readonly min: 0.01;
        readonly step: 0.1;
        readonly description: "Playback rate";
        readonly hiddenFromList: false;
        readonly keyframable: false;
    };
    readonly freeze: {
        readonly type: "number";
        readonly default: null;
        readonly step: 1;
        readonly hiddenFromList: true;
    };
    readonly hidden: import("../interactivity-schema.js").BooleanFieldSchema;
    readonly name: import("../interactivity-schema.js").HiddenFieldSchema;
    readonly showInTimeline: import("../interactivity-schema.js").HiddenFieldSchema;
    readonly color: {
        readonly type: "color";
        readonly default: "transparent";
        readonly description: "Color";
    };
    readonly width: {
        readonly type: "number";
        readonly min: 1;
        readonly step: 1;
        readonly default: 1920;
        readonly description: "Width";
        readonly hiddenFromList: false;
    };
    readonly height: {
        readonly type: "number";
        readonly min: 1;
        readonly step: 1;
        readonly default: 1080;
        readonly description: "Height";
        readonly hiddenFromList: false;
    };
    readonly pixelDensity: {
        readonly type: "number";
        readonly min: 1;
        readonly max: 3;
        readonly step: 0.1;
        readonly default: 1;
        readonly description: "Pixel density";
        readonly hiddenFromList: false;
    };
};
export declare const Solid: React.ComponentType<MandatoryProps & Partial<OptionalProps> & InteractiveCropProps & InteractiveBaseProps & InteractivePremountProps & React.RefAttributes<HTMLCanvasElement>>;
export {};
