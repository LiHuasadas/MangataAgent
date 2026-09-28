import type { TSequence } from './CompositionManager.js';
export declare const useSequenceRegistration: ({ getSequence, id, }: {
    getSequence: (() => TSequence) | null;
    id: string;
}) => void;
