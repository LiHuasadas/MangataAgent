import React, { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { colors, fonts } from '../../styles/theme';
import { Sparkles, User, Lock, ArrowLeft, AlertCircle, CheckCircle2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, register, user } = useAuth();

  const redirectUrl = searchParams.get('redirect') || '/chat';

  // If already logged in, redirect immediately
  React.useEffect(() => {
    if (user) {
      navigate(redirectUrl);
    }
  }, [user, navigate, redirectUrl]);

  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
      navigate(redirectUrl);
    } catch (err: any) {
      setError(err?.detail || err?.message || '认证失败，请检查账号密码');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: `radial-gradient(ellipse at 50% 30%, ${colors.midnightMid}40 0%, ${colors.midnightDeep} 70%)`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 20px',
        position: 'relative',
      }}
    >
      {/* Back to Home Link */}
      <Link
        to="/"
        style={{
          position: 'absolute',
          top: 32,
          left: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          color: colors.coldSilverBlue,
          fontSize: 14,
          textDecoration: 'none',
          transition: 'color 0.2s ease',
        }}
        onMouseEnter={(e) => ((e.target as HTMLElement).style.color = colors.warmGold)}
        onMouseLeave={(e) => ((e.target as HTMLElement).style.color = colors.coldSilverBlue)}
      >
        <ArrowLeft size={16} /> 返回首页
      </Link>

      {/* Main Auth Card */}
      <div
        style={{
          width: '100%',
          maxWidth: 440,
          background: 'rgba(27, 42, 74, 0.45)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: `1px solid ${colors.warmGold}30`,
          borderRadius: 20,
          padding: '40px 36px',
          boxShadow: `0 24px 64px rgba(0, 0, 0, 0.5), 0 0 50px ${colors.warmGold}15`,
        }}
      >
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div
            style={{
              display: 'inline-flex',
              padding: 12,
              borderRadius: '50%',
              background: 'rgba(212, 175, 122, 0.12)',
              border: `1px solid ${colors.warmGold}35`,
              marginBottom: 16,
            }}
          >
            <Sparkles size={28} color={colors.warmGold} />
          </div>

          <h1
            style={{
              fontFamily: fonts.heading,
              fontSize: 28,
              color: colors.moonlightSilver,
              fontWeight: 600,
              letterSpacing: '-0.01em',
              marginBottom: 8,
            }}
          >
            MangataAgent
          </h1>
          <p
            style={{
              fontFamily: fonts.body,
              fontSize: 13,
              color: colors.warmGold,
              lineHeight: 1.6,
            }}
          >
            请先注册账户或登录，开启多智能体编程创作
          </p>
        </div>

        {/* Tab Switcher */}
        <div
          style={{
            display: 'flex',
            background: 'rgba(11, 16, 38, 0.7)',
            borderRadius: 10,
            padding: 4,
            marginBottom: 24,
            border: `1px solid ${colors.warmGold}15`,
          }}
        >
          <button
            type="button"
            onClick={() => {
              setTab('login');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '9px 0',
              border: 'none',
              borderRadius: 8,
              background:
                tab === 'login'
                  ? `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`
                  : 'transparent',
              color: tab === 'login' ? colors.midnightDeep : colors.coldSilverBlue,
              fontWeight: tab === 'login' ? 600 : 400,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.25s ease',
            }}
          >
            账号登录
          </button>
          <button
            type="button"
            onClick={() => {
              setTab('register');
              setError(null);
            }}
            style={{
              flex: 1,
              padding: '9px 0',
              border: 'none',
              borderRadius: 8,
              background:
                tab === 'register'
                  ? `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`
                  : 'transparent',
              color: tab === 'register' ? colors.midnightDeep : colors.coldSilverBlue,
              fontWeight: tab === 'register' ? 600 : 400,
              fontSize: 14,
              cursor: 'pointer',
              transition: 'all 0.25s ease',
            }}
          >
            注册新账号
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '12px 16px',
              borderRadius: 8,
              background: 'rgba(248, 113, 113, 0.15)',
              border: '1px solid rgba(248, 113, 113, 0.4)',
              color: '#f87171',
              fontSize: 13,
              marginBottom: 20,
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div>
            <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
              用户名
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                required
                placeholder="请输入 3-32 位用户名"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.85)',
                  border: `1px solid ${colors.warmGold}35`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '11px 14px 11px 40px',
                  fontSize: 14,
                  outline: 'none',
                }}
              />
              <User
                size={16}
                color={colors.coldSilverBlue}
                style={{ position: 'absolute', left: 14, top: 14 }}
              />
            </div>
          </div>

          {tab === 'register' && (
            <div>
              <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
                显示昵称 (选填)
              </label>
              <input
                type="text"
                placeholder="例如: CodeExplorer"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.85)',
                  border: `1px solid ${colors.warmGold}35`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '11px 14px',
                  fontSize: 14,
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
                placeholder="请输入至少 6 位密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(11, 16, 38, 0.85)',
                  border: `1px solid ${colors.warmGold}35`,
                  color: colors.moonlightSilver,
                  borderRadius: 8,
                  padding: '11px 14px 11px 40px',
                  fontSize: 14,
                  outline: 'none',
                }}
              />
              <Lock
                size={16}
                color={colors.coldSilverBlue}
                style={{ position: 'absolute', left: 14, top: 14 }}
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
              padding: '13px',
              fontWeight: 600,
              fontSize: 14,
              letterSpacing: '0.04em',
              cursor: submitting ? 'not-allowed' : 'pointer',
              opacity: submitting ? 0.7 : 1,
              boxShadow: `0 4px 20px ${colors.warmGold}35`,
              transition: 'all 0.3s ease',
            }}
          >
            {submitting ? '正在安全认证...' : tab === 'login' ? '立即登录进入创作' : '注册并开启创作之旅'}
          </button>
        </form>
      </div>
    </div>
  );
};
