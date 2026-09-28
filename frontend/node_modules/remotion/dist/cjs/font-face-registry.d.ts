export type RegisteredFontFace = {
    ascentOverride: string | null;
    descentOverride: string | null;
    display: 'auto' | 'block' | 'fallback' | 'optional' | 'swap' | null;
    featureSettings: string | null;
    fontFamily: string;
    fontData: ArrayBuffer;
    fontUrl: string;
    format: 'woff2' | 'woff' | 'opentype' | 'truetype';
    lineGapOverride: string | null;
    style: string | null;
    weight: string | null;
    stretch: string | null;
    unicodeRange: string | null;
    variant: string | null;
};
export declare const fetchFontData: (fontUrl: string) => Promise<ArrayBuffer>;
export declare const registerFontFace: (fontFace: RegisteredFontFace) => void;
export declare const getRegisteredFontFaces: () => RegisteredFontFace[];
