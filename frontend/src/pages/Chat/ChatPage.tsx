import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../context/WorkspaceContext';
import { useAuth } from '../../context/AuthContext';
import {
  conversationApi,
  ConversationResponse,
  MessageItemResponse,
  TurnResponse,
  getUserId,
} from '../../api';
import { colors, fonts } from '../../styles/theme';
import {
  Bot,
  Send,
  Plus,
  MessageSquare,
  Sparkles,
  Terminal,
  CheckCircle,
  Clock,
  Layers,
  Code2,
  Home,
  FolderGit2,
  User,
  LogOut,
} from 'lucide-react';

export const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { workspaceId, setWorkspaceId } = useWorkspace();
  const { user, logout } = useAuth();

  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItemResponse[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>('');
  const [sending, setSending] = useState<boolean>(false);
  const [latestTurn, setLatestTurn] = useState<TurnResponse | null>(null);
  const [progressText, setProgressText] = useState<string>('');
  const [streamingAnswer, setStreamingAnswer] = useState<string>('');
  const [agentFeedback, setAgentFeedback] = useState<string[]>([]);
  const [streamingConvId, setStreamingConvId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvRef = useRef<string | null>(null);
  const pendingConvRef = useRef<string | null>(null);

  useEffect(() => {
    activeConvRef.current = activeConvId;
  }, [activeConvId]);

  const getEffectiveUserId = () => {
    return user?.user_id || getUserId() || 'user';
  };

  const getConversationWorkspace = (convId: string | null) => {
    const uid = getEffectiveUserId();
    return convId ? `${uid}_${convId}` : `${uid}_workspace`;
  };

  // Synchronize workspaceId: prefer query param if set, otherwise default to userId + conversationId
  useEffect(() => {
    const wsParam = searchParams.get('workspace_id');
    if (wsParam && wsParam !== 'default') {
      setWorkspaceId(wsParam);
    } else if (activeConvId) {
      setWorkspaceId(getConversationWorkspace(activeConvId));
    } else {
      setWorkspaceId(getConversationWorkspace(null));
    }
  }, [searchParams, activeConvId, user?.user_id]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // When active conversation changes, load messages
  useEffect(() => {
    if (activeConvId) {
      loadMessages(activeConvId);
    }
  }, [activeConvId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending, progressText, streamingAnswer, agentFeedback]);

  const loadConversations = async () => {
    try {
      const res = await conversationApi.listConversations();
      setConversations(res.items);
      if (res.items.length > 0 && !activeConvId) {
        const firstId = res.items[0].conversation_id;
        setActiveConvId(firstId);
        const wsParam = searchParams.get('workspace_id');
        if (!wsParam || wsParam === 'default') {
          setWorkspaceId(getConversationWorkspace(firstId));
        }
      }
    } catch (err) {
      console.error('加载会话列表失败', err);
    }
  };

  const handleCreateConversation = async () => {
    try {
      const newConv = await conversationApi.createConversation();
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.conversation_id);
      activeConvRef.current = newConv.conversation_id;
      const wsParam = searchParams.get('workspace_id');
      if (!wsParam || wsParam === 'default') {
        setWorkspaceId(getConversationWorkspace(newConv.conversation_id));
      }
      setMessages([]);
      setLatestTurn(null);
      setProgressText('');
      setStreamingAnswer('');
      setAgentFeedback([]);
    } catch (err) {
      console.error('创建新会话失败', err);
    }
  };

  const loadMessages = async (convId: string) => {
    try {
      const items: MessageItemResponse[] = [];
      let afterSequence = 0;
      while (true) {
        const res = await conversationApi.listMessages(convId, afterSequence, 100);
        items.push(...res.items);
        const lastSequence = res.items[res.items.length - 1]?.sequence;
        if (res.items.length < 100 || !lastSequence || lastSequence <= afterSequence) break;
        afterSequence = lastSequence;
      }
      if (activeConvRef.current === convId && pendingConvRef.current !== convId) {
        setMessages(items);
      }
    } catch (err) {
      console.error('加载历史消息失败', err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputPrompt.trim() || sending) return;

    let convId = activeConvId;
    try {
      if (!convId) {
        const newConv = await conversationApi.createConversation();
        setConversations((prev) => [newConv, ...prev]);
        convId = newConv.conversation_id;
        activeConvRef.current = convId;
        setActiveConvId(convId);
      }
    } catch (err) {
      console.error('创建新会话失败', err);
      return;
    }

    const wsParam = searchParams.get('workspace_id');
    const effectiveWs = (wsParam && wsParam !== 'default')
      ? wsParam
      : getConversationWorkspace(convId);

    if (workspaceId !== effectiveWs) {
      setWorkspaceId(effectiveWs);
    }

    const currentText = inputPrompt;
    pendingConvRef.current = convId;
    setStreamingConvId(convId);
    setProgressText('正在连接智能体');
    setStreamingAnswer('');
    setAgentFeedback([]);
    setInputPrompt('');
    setSending(true);

    // Optimistically append user message
    const tempUserMsg: MessageItemResponse = {
      message_id: 'temp-' + Date.now(),
      role: 'user',
      content: currentText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      await conversationApi.streamMessage(convId, {
        content: currentText,
        workspace_id: effectiveWs,
      }, (event) => {
        if (event.type === 'progress' && activeConvRef.current === convId) {
          setProgressText(event.message);
        } else if (event.type === 'delta' && activeConvRef.current === convId) {
          setStreamingAnswer((prev) => prev + event.content);
        } else if (event.type === 'agent_result' && activeConvRef.current === convId) {
          setAgentFeedback((prev) => [...prev,
            `${event.agent_type}：${event.success ? '完成' : '失败'}\n${event.response}`]);
        } else if (event.type === 'answer') {
          setLatestTurn(event.data);
          if (activeConvRef.current === convId) {
            setStreamingAnswer(event.data.answer || '');
          }
        }
      });
      pendingConvRef.current = null;
      await loadMessages(convId);
    } catch (err: any) {
      const errorMsg: MessageItemResponse = {
        message_id: 'err-' + Date.now(),
        role: 'assistant',
        content: `❌ 请求处理失败: ${err?.detail || err?.message || '智能体执行异常'}`,
        created_at: new Date().toISOString(),
      };
      pendingConvRef.current = null;
      await loadMessages(convId);
      if (activeConvRef.current === convId) {
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      pendingConvRef.current = null;
      setProgressText('');
      setStreamingAnswer('');
      setAgentFeedback([]);
      setStreamingConvId(null);
      setSending(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        background: colors.midnightDeep,
        paddingTop: 64, // below navbar
      }}
    >
      {/* Sidebar: Conversations */}
      <div
        style={{
          width: 280,
          background: 'rgba(27, 42, 74, 0.3)',
          borderRight: `1px solid ${colors.warmGold}15`,
          display: 'flex',
          flexDirection: 'column',
          padding: '20px 16px',
        }}
      >
        <button
          onClick={handleCreateConversation}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
            border: 'none',
            color: colors.midnightDeep,
            borderRadius: 8,
            padding: '10px 16px',
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            marginBottom: 20,
          }}
        >
          <Plus size={16} /> 新建协同会话
        </button>

        <div style={{ fontSize: 12, color: colors.coldSilverBlue, marginBottom: 8, paddingLeft: 6 }}>
          历史会话列表
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {conversations.map((c) => (
            <div
              key={c.conversation_id}
              onClick={() => {
                activeConvRef.current = c.conversation_id;
                setActiveConvId(c.conversation_id);
                setProgressText('');
                setStreamingAnswer('');
                setAgentFeedback([]);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 12px',
                borderRadius: 6,
                background: activeConvId === c.conversation_id ? 'rgba(212, 175, 122, 0.15)' : 'transparent',
                border: activeConvId === c.conversation_id ? `1px solid ${colors.warmGold}40` : '1px solid transparent',
                color: activeConvId === c.conversation_id ? colors.warmGold : colors.moonlightSilver,
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              <MessageSquare size={14} />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                会话 {c.conversation_id.slice(0, 8)}...
              </span>
            </div>
          ))}
        </div>

        {/* Bottom Controls moved from top right */}
        <div
          style={{
            marginTop: 'auto',
            paddingTop: 16,
            borderTop: `1px solid ${colors.warmGold}15`,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          {/* Quick Navigation Buttons */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <button
              onClick={() => navigate('/workspace')}
              title="管理云端项目与文件"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                background: 'rgba(212, 175, 122, 0.1)',
                border: `1px solid ${colors.warmGold}35`,
                color: colors.warmGold,
                borderRadius: 8,
                padding: '8px 10px',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <FolderGit2 size={14} />
              <span>工作空间</span>
            </button>

            <button
              onClick={() => navigate('/')}
              title="返回品牌首页"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                background: 'rgba(255, 255, 255, 0.04)',
                border: `1px solid ${colors.warmGold}20`,
                color: colors.coldSilverBlue,
                borderRadius: 8,
                padding: '8px 10px',
                fontSize: 12,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
            >
              <Home size={14} />
              <span>返回首页</span>
            </button>
          </div>

          {/* Bound Workspace Tag */}
          <div
            onClick={() => navigate(`/workspace?workspace_id=${encodeURIComponent(workspaceId && workspaceId !== 'default' ? workspaceId : getConversationWorkspace(activeConvId))}`)}
            title="点击前往工作空间文件管理器"
            style={{
              padding: '8px 12px',
              borderRadius: 6,
              background: 'rgba(11, 16, 38, 0.7)',
              border: `1px solid ${colors.warmGold}15`,
              fontSize: 11,
              color: colors.coldSilverBlue,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
            }}
          >
            <span style={{ flexShrink: 0 }}>工作空间:</span>
            <strong
              style={{
                color: colors.warmGold,
                fontFamily: 'monospace',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                textAlign: 'right',
                maxWidth: 130,
              }}
              title={workspaceId && workspaceId !== 'default' ? workspaceId : getConversationWorkspace(activeConvId)}
            >
              {workspaceId && workspaceId !== 'default' ? workspaceId : getConversationWorkspace(activeConvId)}
            </strong>
          </div>

          {/* User Account & Logout */}
          {user && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                borderRadius: 8,
                background: 'rgba(27, 42, 74, 0.5)',
                border: `1px solid ${colors.warmGold}25`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: 'rgba(212, 175, 122, 0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <User size={13} color={colors.warmGold} />
                </div>
                <span
                  style={{
                    fontSize: 12,
                    color: colors.moonlightSilver,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {user.display_name || user.username}
                </span>
              </div>

              <button
                onClick={async () => {
                  await logout();
                  navigate('/login');
                }}
                title="退出登录"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#f87171',
                  cursor: 'pointer',
                  padding: 4,
                  display: 'flex',
                  alignItems: 'center',
                  opacity: 0.8,
                }}
              >
                <LogOut size={14} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        {/* Messages Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '32px 48px', display: 'flex', flexDirection: 'column', gap: 24 }}>
          {messages.length === 0 && (
            <div
              style={{
                margin: 'auto',
                textAlign: 'center',
                maxWidth: 500,
                color: colors.coldSilverBlue,
              }}
            >
              <Bot size={48} color={colors.warmGold} style={{ marginBottom: 16 }} />
              <h2 style={{ fontFamily: fonts.heading, fontSize: 24, color: colors.moonlightSilver, marginBottom: 8 }}>
                MangataAgent 多智能体协同工作台
              </h2>
              <p style={{ fontSize: 14, lineHeight: 1.6 }}>
                当前绑定工作空间: <code style={{ color: colors.warmGold, wordBreak: 'break-all' }}>{workspaceId && workspaceId !== 'default' ? workspaceId : getConversationWorkspace(activeConvId)}</code>
                <br />
                输入您的开发需求，HostAgent 将调度技术侦察规划、精准施工与质量质检全流水线。
              </p>
            </div>
          )}

          {messages.map((m) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={m.message_id}
                style={{
                  display: 'flex',
                  gap: 16,
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                }}
              >
                {!isUser && (
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: '50%',
                      background: 'rgba(212, 175, 122, 0.2)',
                      border: `1px solid ${colors.warmGold}50`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Bot size={18} color={colors.warmGold} />
                  </div>
                )}

                <div
                  style={{
                    background: isUser ? 'rgba(212, 175, 122, 0.15)' : 'rgba(27, 42, 74, 0.4)',
                    border: `1px solid ${isUser ? colors.warmGold + '40' : colors.warmGold + '20'}`,
                    borderRadius: 12,
                    padding: '14px 18px',
                    color: colors.moonlightSilver,
                    fontSize: 14,
                    lineHeight: 1.7,
                    whiteSpace: 'pre-wrap',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)',
                  }}
                >
                  {m.content}
                </div>
              </div>
            );
          })}

          {sending && streamingConvId === activeConvId && (
            <div style={{ display: 'flex', gap: 16, alignSelf: 'flex-start', maxWidth: '85%' }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: '50%',
                  background: 'rgba(212, 175, 122, 0.2)',
                  border: `1px solid ${colors.warmGold}50`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Sparkles size={18} color={colors.warmGold} className="pulse" />
              </div>
              <div
                style={{
                  background: 'rgba(27, 42, 74, 0.4)',
                  border: `1px solid ${colors.warmGold}20`,
                  borderRadius: 12,
                  padding: '14px 18px',
                  color: colors.warmGold,
                  fontSize: 14,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  whiteSpace: 'pre-wrap',
                  maxHeight: '55vh',
                  overflowY: 'auto',
                }}
              >
                <span>{progressText || '正在处理'}{agentFeedback.length ? `\n\n${agentFeedback.join('\n\n')}` : ''}{streamingAnswer ? `\n\n${streamingAnswer}` : ''}</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Area */}
        <div
          style={{
            padding: '20px 48px 32px',
            background: 'rgba(11, 16, 38, 0.9)',
            borderTop: `1px solid ${colors.warmGold}15`,
          }}
        >
          <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: 12 }}>
            <input
              type="text"
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              placeholder="输入给智能体的开发或重构需求，例如: 帮我为工作空间新增一个健康检查 API 并编写测试..."
              disabled={sending}
              style={{
                flex: 1,
                background: 'rgba(27, 42, 74, 0.5)',
                border: `1px solid ${colors.warmGold}40`,
                color: colors.moonlightSilver,
                borderRadius: 24,
                padding: '12px 24px',
                fontSize: 14,
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={sending || !inputPrompt.trim()}
              style={{
                background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
                border: 'none',
                color: colors.midnightDeep,
                borderRadius: 24,
                padding: '0 28px',
                fontWeight: 600,
                fontSize: 14,
                cursor: sending || !inputPrompt.trim() ? 'not-allowed' : 'pointer',
                opacity: sending || !inputPrompt.trim() ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <Send size={16} /> 发送
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
