import React from 'react';
type BufferManager = {
    addBlock: () => {
        unblock: () => void;
    };
};
export declare const BufferingContextReact: React.Context<BufferManager | null>;
export declare const BufferingProvider: React.FC<{
    readonly children: React.ReactNode;
}>;
export {};
