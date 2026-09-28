import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { colors, fonts } from '../styles/theme';
import { X, Lock, User, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, closeAuthModal, login, register } = useAuth();
  const [tab, setTab] = useState<'login' | 'register'>('login');

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (tab === 'login') {
        await login(username, password);
      } else {
        await register(username, password, displayName || undefined);
      }
      setUsername('');
      setPassword('');
      setDisplayName('');
    } catch (err: any) {
      setError(err?.detail || err?.message || '认证失败，请检查输入');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 2000,
        background: 'rgba(11, 16, 38, 0.75)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) closeAuthModal();
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 420,
          background: 'rgba(27, 42, 74, 0.9)',
          border: `1px solid ${colors.warmGold}40`,
          borderRadius: 16,
          padding: '32px 28px',
          boxShadow: `0 16px 48px rgba(0, 0, 0, 0.6), 0 0 40px ${colors.warmGold}15`,
          position: 'relative',
        }}
      >
        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          style={{
            position: 'absolute',
            top: 20,
            right: 20,
            background: 'transparent',
            border: 'none',
            color: colors.coldSilverBlue,
            cursor: 'pointer',
            padding: 4,
          }}
        >
          <X size={20} />
        </button>

        {/* Title */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div
            style={{
              display: 'inline-flex',
              padding: 10,
              borderRadius: '50%',
              background: 'rgba(212, 175, 122, 0.1)',
              marginBottom: 12,
            }}
          >
            <Sparkles size={24} color={colors.warmGold} />
          </div>
          <h2 style={{ fontFamily: fonts.heading, fontSize: 24, color: colors.moonlightSilver }}>
            {tab === 'login' ? '登入 Mangata 空间' : '创建开发者账号'}
          </h2>
          <p style={{ fontFamily: fonts.body, fontSize: 13, color: colors.coldSilverBlue, marginTop: 4 }}>
            基于 Redis 极速认证与多租户工作区隔离
          </p>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(11, 16, 38, 0.6)',
            borderRadius: 8,
            padding: 4,
            marginBottom: 20,
          }}
        >
          <button
            onClick={() => {
              setTab('login');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '8px 0',
              border: 'none',
              borderRadius: 6,
              background: tab === 'login' ? `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})` : 'transparent',
              color: tab === 'login' ? colors.midnightDeep : colors.coldSilverBlue,
              fontWeight: tab === 'login' ? 600 : 400,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            登录
          </button>
          <button
            onClick={() => {
              setTab('register');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '8px 0',
              border: 'none',
              borderRadius: 6,
              background: tab === 'register' ? `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})` : 'transparent',
              color: tab === 'register' ? colors.midnightDeep : colors.coldSilverBlue,
              fontWeight: tab === 'register' ? 600 : 400,
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            注册
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 14px',
              borderRadius: 8,
              background: 'rgba(248, 113, 113, 0.15)',
              border: '1px solid rgba(248, 113, 113, 0.4)',
              color: '#f87171',
              fontSize: 13,
              marginBottom: 16,
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
              用户名
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                required
                placeholder="例如: developer_alex"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.8)',
                  border: `1px solid ${colors.warmGold}30`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '10px 14px 10px 38px',
                  fontSize: 13,
                  outline: 'none',
                }}
              />
              <User
                size={16}
                color={colors.coldSilverBlue}
                style={{ position: 'absolute', left: 12, top: 12 }}
              />
            </div>
          </div>

          {tab === 'register' && (
            <div>
              <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
                用户昵称 (选填)
              </label>
              <input
                type="text"
                placeholder="显示名称"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.8)',
                  border: `1px solid ${colors.warmGold}30`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '10px 14px',
                  fontSize: 13,
                  outline: 'none',
                }}
              />
            </div>
          )}

          <div>
            <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
              密码
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                required
                placeholder="至少 6 位密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.8)',
                  border: `1px solid ${colors.warmGold}30`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '10px 14px 10px 38px',
                  fontSize: 13,
                  outline: 'none',
                }}
              />
              <Lock
                size={16}
                color={colors.coldSilverBlue}
                style={{ position: 'absolute', left: 12, top: 12 }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            style={{
              marginTop: 10,
              background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
              border: 'none',
              color: colors.midnightDeep,
              borderRadius: 8,
              padding: '12px',
              fontWeight: 600,
              fontSize: 14,
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.7 : 1,
            }}
          >
            {submitting ? '处理中...' : tab === 'login' ? '立即登录' : '立即注册'}
          </button>
        </form>
      </div>
    </div>
  );
};
