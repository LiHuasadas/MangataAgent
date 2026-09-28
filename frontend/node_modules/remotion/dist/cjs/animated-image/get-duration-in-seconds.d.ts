export declare const getAnimatedImageDurationInSeconds: ({ resolvedSrc, signal, requestInit, contentType, }: {
    resolvedSrc: string;
    signal: AbortSignal;
    requestInit?: RequestInit | undefined;
    contentType: string | null;
}) => Promise<number>;
