/**
 * TypeScript Data Models matching MangataAgent Backend Schemas
 */

export interface GitCloneRequest {
  repo_url: string;
  workspace_id?: string;
  branch?: string;
  depth?: number;
  auth_token?: string;
  clean_existing?: boolean;
}

export interface GitOperationResponse {
  success: boolean;
  action: 'clone' | 'pull' | string;
  workspace_id: string;
  workspace_path: string;
  repo_url: string;
  branch?: string;
  commit_hash?: string;
  commit_message?: string;
  author?: string;
  file_count: number;
  total_size_bytes: number;
}

export interface WorkspaceUploadResponse {
  success: boolean;
  workspace_id: string;
  workspace_path: string;
  file_count: number;
  total_size_bytes: number;
  files: string[];
  message?: string;
}

export interface WorkspaceTreeItem {
  name: string;
  path: string;
  is_dir: boolean;
  size?: number;
  children?: WorkspaceTreeItem[];
  is_git_root?: boolean;
  exists?: boolean;
}

export interface WorkspaceStatusResponse {
  workspace_id: string;
  user_id: string;
  exists: boolean;
  absolute_path: string;
  file_count: number;
  total_size_bytes: number;
  is_git_repo: boolean;
  git_branch?: string;
  git_commit?: string;
  git_commit_message?: string;
  git_author?: string;
  git_remote_url?: string;
}

export interface ConversationResponse {
  conversation_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  items: ConversationResponse[];
}

export interface MessageItemResponse {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  sequence?: number;
  reply_to_message_id?: string;
  metadata?: Record<string, any>;
}

export interface MessageListResponse {
  items: MessageItemResponse[];
  after_sequence: number;
  limit: number;
}

export interface SendMessageRequest {
  content: string;
  request_id?: string;
  workspace_id?: string;
  validation_command?: string;
}

export interface AgentResultItem {
  agent_name: string;
  output: string;
  status?: string;
  metadata?: Record<string, any>;
}

export interface TurnResponse {
  conversation_id: string;
  request_id: string;
  status: 'COMPLETED' | 'FAILED' | 'PROCESSING' | string;
  user_message_id: string;
  assistant_message_id?: string;
  answer?: string;
  agent_results?: AgentResultItem[];
  artifacts?: any[];
  error?: string;
}

export interface ApiErrorPayload {
  detail: string;
  status?: number;
}

export interface UserResponse {
  user_id: string;
  username: string;
  display_name: string;
  created_at?: string;
}

export interface AuthResponse {
  success: boolean;
  token: string;
  user: UserResponse;
  message: string;
}
