export type RuntimeValueSnapshot = Readonly<Record<string, unknown>>;
export type RuntimeValueStore<TSnapshot extends RuntimeValueSnapshot = RuntimeValueSnapshot> = {
    getSnapshot: () => TSnapshot;
    subscribe: (listener: (snapshot: TSnapshot) => void) => () => void;
};
export type RuntimeValueStoreController<TSnapshot extends RuntimeValueSnapshot = RuntimeValueSnapshot> = {
    store: RuntimeValueStore<TSnapshot>;
    setSnapshot: (newSnapshot: TSnapshot) => void;
};
export declare const createRuntimeValueStore: <TSnapshot extends Readonly<Record<string, unknown>>>(initialSnapshot: TSnapshot) => RuntimeValueStoreController<TSnapshot>;
