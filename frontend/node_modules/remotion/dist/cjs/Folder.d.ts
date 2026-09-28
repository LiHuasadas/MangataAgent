import type { FC, ReactNode } from 'react';
export type TFolder = {
    name: string;
    parent: string | null;
    order: number | null;
    stack: string | null;
};
type FolderContextType = {
    folderName: string | null;
    parentName: string | null;
};
export declare const FolderContext: import("react").Context<FolderContextType>;
export declare const Folder: FC<{
    readonly name: string;
    readonly children?: ReactNode;
}>;
export {};
