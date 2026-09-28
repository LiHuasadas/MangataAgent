/**
 * Authentication and User Account APIs backed by Redis
 */

import { request, setAuthToken, setUserId } from './client';
import { AuthResponse, UserResponse } from './types';

export const authApi = {
  /**
   * Register a new user
   */
  async register(username: string, password: string, displayName?: string): Promise<AuthResponse> {
    const res = await request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, display_name: displayName }),
    });
    if (res.token) {
      setAuthToken(res.token);
      setUserId(res.user.user_id);
    }
    return res;
  },

  /**
   * Login with username and password
   */
  async login(username: string, password: string): Promise<AuthResponse> {
    const res = await request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    if (res.token) {
      setAuthToken(res.token);
      setUserId(res.user.user_id);
    }
    return res;
  },

  /**
   * Get current authenticated user profile
   */
  async getMe(): Promise<UserResponse> {
    return request<UserResponse>('/auth/me');
  },

  /**
   * Logout and clear local tokens
   */
  async logout(): Promise<{ success: boolean; message: string }> {
    try {
      await request<{ success: boolean; message: string }>('/auth/logout', {
        method: 'POST',
      });
    } finally {
      localStorage.removeItem('mangata_auth_token');
    }
    return { success: true, message: '已退出登录' };
  },
};
