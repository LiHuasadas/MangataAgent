export type MediaResourceLease<T> = {
    resource: T;
    getOrCreateValue: <Value>(key: string, create: () => Value) => Value;
    release: () => void;
};
export type MediaResourceManager = {
    acquire: <T>({ key, create }: {
        key: string;
        create: () => {
            resource: T;
            dispose: () => void;
        };
    }) => MediaResourceLease<T>;
    invalidate: (key: string) => void;
    dispose: () => void;
};
export declare const makeMediaResourceManager: () => MediaResourceManager;
export declare const getMediabunnyInputResourceKey: ({ src, credentials, requestInitFingerprint, revision, }: {
    src: string;
    credentials: RequestCredentials | null;
    requestInitFingerprint: unknown;
    revision: string | null;
}) => string;
export declare const MEDIABUNNY_DURATION_VALUE_KEY = "mediabunny-duration";
export declare const globalMediaResourceManager: MediaResourceManager;
