/**
 * Conversations and Agent Messaging APIs
 */

import { API_BASE, ApiError, getAuthToken, getUserId, request } from './client';
import {
  ConversationListResponse,
  ConversationResponse,
  MessageListResponse,
  SendMessageRequest,
  TurnResponse,
} from './types';

export type ConversationStreamEvent =
  | { type: 'ack'; conversation_id: string }
  | { type: 'progress'; stage: string; message: string; agent_type?: string; state?: string; success?: boolean; agents?: string[] }
  | { type: 'agent_result'; agent_type: string; success: boolean; response: string }
  | { type: 'delta'; content: string }
  | { type: 'answer'; data: TurnResponse }
  | { type: 'error'; detail: string };

export const conversationApi = {
  /**
   * Create a new conversation session
   */
  async createConversation(): Promise<ConversationResponse> {
    return request<ConversationResponse>('/conversations', {
      method: 'POST',
    });
  },

  /**
   * List conversations for the current user
   */
  async listConversations(offset: number = 0, limit: number = 20): Promise<ConversationListResponse> {
    return request<ConversationListResponse>('/conversations', {
      params: { offset, limit },
    });
  },

  /**
   * Get single conversation details
   */
  async getConversation(conversationId: string): Promise<ConversationResponse> {
    return request<ConversationResponse>(`/conversations/${encodeURIComponent(conversationId)}`);
  },

  /**
   * List message history for a conversation
   */
  async listMessages(
    conversationId: string,
    afterSequence: number = 0,
    limit: number = 50
  ): Promise<MessageListResponse> {
    return request<MessageListResponse>(`/conversations/${encodeURIComponent(conversationId)}/messages`, {
      params: { after_sequence: afterSequence, limit },
    });
  },

  /**
   * Send a prompt message to HostAgent and await multi-agent pipeline turn completion
   */
  async sendMessage(conversationId: string, data: SendMessageRequest): Promise<TurnResponse> {
    return request<TurnResponse>(`/conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async streamMessage(
    conversationId: string,
    data: SendMessageRequest,
    onEvent: (event: ConversationStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}/messages/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': getUserId(),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new ApiError(response.status, payload.detail || response.statusText);
    }
    if (!response.body) throw new Error('浏览器未提供流式响应');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let receivedAnswer = false;
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
        const frames = buffer.split('\n\n');
        buffer = frames.pop() || '';
        for (const frame of frames) {
          const dataLine = frame.split('\n').filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trimStart()).join('\n');
          if (!dataLine || dataLine === '[DONE]') continue;
          const event = JSON.parse(dataLine) as ConversationStreamEvent;
          if (event.type === 'error') throw new Error(event.detail);
          if (event.type === 'answer') receivedAnswer = true;
          onEvent(event);
        }
      }
      if (!receivedAnswer) throw new Error('流式连接已结束，未收到最终回答');
    } finally {
      reader.releaseLock();
    }
  },
};
