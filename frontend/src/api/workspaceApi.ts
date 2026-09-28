/**
 * Workspace and Project Storage APIs
 */

import { request } from './client';
import {
  GitCloneRequest,
  GitOperationResponse,
  WorkspaceStatusResponse,
  WorkspaceTreeItem,
  WorkspaceUploadResponse,
} from './types';

export const workspaceApi = {
  /**
   * Clone or pull a remote Git repository into the cloud workspace
   */
  async gitClone(data: GitCloneRequest): Promise<GitOperationResponse> {
    return request<GitOperationResponse>('/workspaces/git-clone', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Upload and extract a local project archive (.zip, .tar, .tar.gz, .tgz)
   */
  async uploadArchive(
    file: File,
    workspaceId: string = 'default',
    cleanExisting: boolean = false,
    stripRootDir: boolean = true
  ): Promise<WorkspaceUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('workspace_id', workspaceId);
    formData.append('clean_existing', String(cleanExisting));
    formData.append('strip_root_dir', String(stripRootDir));

    return request<WorkspaceUploadResponse>('/workspaces/upload-archive', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Upload multiple local files with folder hierarchy preserved
   */
  async uploadFiles(
    files: File[],
    relativePaths?: string[],
    workspaceId: string = 'default',
    cleanExisting: boolean = false
  ): Promise<WorkspaceUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    if (relativePaths && relativePaths.length > 0) {
      relativePaths.forEach((path) => {
        formData.append('relative_paths', path);
      });
    }

    formData.append('workspace_id', workspaceId);
    formData.append('clean_existing', String(cleanExisting));

    return request<WorkspaceUploadResponse>('/workspaces/upload-files', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * Get workspace statistics, size, file count, and Git metadata
   */
  async getStatus(workspaceId: string = 'default'): Promise<WorkspaceStatusResponse> {
    return request<WorkspaceStatusResponse>(`/workspaces/${encodeURIComponent(workspaceId)}/status`);
  },

  /**
   * Get workspace directory tree
   */
  async getTree(
    workspaceId: string = 'default',
    path: string = '',
    maxDepth: number = 4
  ): Promise<WorkspaceTreeItem> {
    return request<WorkspaceTreeItem>(`/workspaces/${encodeURIComponent(workspaceId)}/tree`, {
      params: { path, max_depth: maxDepth },
    });
  },

  /**
   * Delete or reset a cloud workspace
   */
  async deleteWorkspace(workspaceId: string): Promise<{ success: boolean; message: string }> {
    return request<{ success: boolean; message: string }>(`/workspaces/${encodeURIComponent(workspaceId)}`, {
      method: 'DELETE',
    });
  },
};
