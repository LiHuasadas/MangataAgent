import React, { createContext, useContext, useEffect, useState } from 'react';
import { getUserId, setUserId as saveUserId, workspaceApi, WorkspaceStatusResponse, WorkspaceTreeItem } from '../api';

interface WorkspaceContextType {
  userId: string;
  setUserId: (id: string) => void;
  workspaceId: string;
  setWorkspaceId: (id: string) => void;
  status: WorkspaceStatusResponse | null;
  tree: WorkspaceTreeItem | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const currentUid = getUserId();
  const [userId, setUserIdState] = useState<string>(currentUid);
  const [workspaceId, setWorkspaceId] = useState<string>(() => {
    const saved = localStorage.getItem('mangata_current_workspace');
    if (saved && saved !== 'default') return saved;
    return `${currentUid}_workspace`;
  });
  const [status, setStatus] = useState<WorkspaceStatusResponse | null>(null);
  const [tree, setTree] = useState<WorkspaceTreeItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const setUserId = (id: string) => {
    saveUserId(id);
    setUserIdState(id);
  };

  const handleSetWorkspaceId = (id: string) => {
    const safeId = id && id !== 'default' ? id : `${userId}_workspace`;
    setWorkspaceId(safeId);
    localStorage.setItem('mangata_current_workspace', safeId);
  };

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, treeRes] = await Promise.all([
        workspaceApi.getStatus(workspaceId),
        workspaceApi.getTree(workspaceId),
      ]);
      setStatus(statusRes);
      setTree(treeRes);
    } catch (err: any) {
      setError(err?.detail || err?.message || '获取工作空间状态失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, [workspaceId, userId]);

  return (
    <WorkspaceContext.Provider
      value={{
        userId,
        setUserId,
        workspaceId,
        setWorkspaceId: handleSetWorkspaceId,
        status,
        tree,
        loading,
        error,
        refresh,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export function useWorkspace(): WorkspaceContextType {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
