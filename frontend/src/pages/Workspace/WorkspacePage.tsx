import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useWorkspace } from '../../context/WorkspaceContext';
import { workspaceApi, WorkspaceTreeItem } from '../../api';
import { colors, fonts } from '../../styles/theme';
import {
  FolderGit2,
  UploadCloud,
  FileCode,
  Folder,
  FolderOpen,
  RefreshCw,
  Trash2,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  GitBranch,
  HardDrive,
  Layers,
} from 'lucide-react';

export const WorkspacePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { workspaceId, setWorkspaceId, status, tree, loading, refresh } = useWorkspace();

  const [activeTab, setActiveTab] = useState<'git' | 'upload'>('git');
  const [targetWsInput, setTargetWsInput] = useState<string>(workspaceId);

  useEffect(() => {
    const wsParam = searchParams.get('workspace_id');
    if (wsParam && wsParam !== 'default' && wsParam !== workspaceId) {
      setWorkspaceId(wsParam);
      setTargetWsInput(wsParam);
    }
  }, [searchParams]);

  useEffect(() => {
    setTargetWsInput(workspaceId);
  }, [workspaceId]);

  // Git clone form state
  const [repoUrl, setRepoUrl] = useState<string>('');
  const [branch, setBranch] = useState<string>('');
  const [authToken, setAuthToken] = useState<string>('');
  const [cleanExistingGit, setCleanExistingGit] = useState<boolean>(false);

  // File upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [cleanExistingUpload, setCleanExistingUpload] = useState<boolean>(false);

  // Operation state
  const [opLoading, setOpLoading] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleSwitchWorkspace = (e: React.FormEvent) => {
    e.preventDefault();
    if (targetWsInput.trim()) {
      setWorkspaceId(targetWsInput.trim());
      setMessage({ type: 'success', text: `已切换至工作空间: ${targetWsInput.trim()}` });
    }
  };

  const handleGitClone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setOpLoading(true);
    setMessage(null);
    try {
      const res = await workspaceApi.gitClone({
        repo_url: repoUrl.trim(),
        workspace_id: workspaceId,
        branch: branch.trim() || undefined,
        auth_token: authToken.trim() || undefined,
        clean_existing: cleanExistingGit,
      });
      setMessage({
        type: 'success',
        text: `Git ${res.action === 'clone' ? '克隆' : '拉取'}成功！已导入 ${res.file_count} 个文件 (${(res.total_size_bytes / 1024).toFixed(1)} KB)，当前分支: ${res.branch || 'HEAD'}`,
      });
      setRepoUrl('');
      await refresh();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.detail || err?.message || 'Git 操作失败' });
    } finally {
      setOpLoading(false);
    }
  };

  const handleArchiveUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setOpLoading(true);
    setMessage(null);
    try {
      const res = await workspaceApi.uploadArchive(
        uploadFile,
        workspaceId,
        cleanExistingUpload,
        true
      );
      setMessage({
        type: 'success',
        text: `压缩包上传并解压成功！共保存 ${res.file_count} 个文件到云端工作空间`,
      });
      setUploadFile(null);
      await refresh();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.detail || err?.message || '上传解压失败' });
    } finally {
      setOpLoading(false);
    }
  };

  const handleDeleteWorkspace = async () => {
    if (!window.confirm(`确定要彻底清空工作空间 [${workspaceId}] 吗？`)) return;
    setOpLoading(true);
    try {
      await workspaceApi.deleteWorkspace(workspaceId);
      setMessage({ type: 'success', text: `工作空间 [${workspaceId}] 已清理` });
      await refresh();
    } catch (err: any) {
      setMessage({ type: 'error', text: err?.detail || err?.message || '清理失败' });
    } finally {
      setOpLoading(false);
    }
  };

  // Render tree node recursively
  const renderTreeNode = (node: WorkspaceTreeItem, depth: number = 0) => {
    return (
      <div key={node.path || node.name} style={{ marginLeft: depth * 16, marginTop: 4 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            color: node.is_dir ? colors.warmGold : colors.moonlightSilver,
            padding: '3px 8px',
            borderRadius: 4,
            background: 'rgba(255, 255, 255, 0.02)',
          }}
        >
          {node.is_dir ? (
            <Folder size={14} color={colors.warmGold} />
          ) : (
            <FileCode size={14} color={colors.coldSilverBlue} />
          )}
          <span style={{ fontWeight: node.is_dir ? 500 : 300 }}>{node.name}</span>
          {!node.is_dir && node.size !== undefined && (
            <span style={{ fontSize: 11, color: colors.coldSilverBlue, marginLeft: 'auto', opacity: 0.7 }}>
              {(node.size / 1024).toFixed(1)} KB
            </span>
          )}
        </div>
        {node.children && node.children.map((child) => renderTreeNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: colors.midnightDeep,
        padding: '100px 32px 64px',
        maxWidth: 1280,
        margin: '0 auto',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 36,
          flexWrap: 'wrap',
          gap: 20,
        }}
      >
        <div>
          <h1
            style={{
              fontFamily: fonts.heading,
              fontSize: 32,
              color: colors.moonlightSilver,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              marginBottom: 8,
            }}
          >
            <FolderGit2 color={colors.warmGold} size={28} />
            云端工作空间管理 (Workspace)
          </h1>
          <p style={{ fontFamily: fonts.body, color: colors.coldSilverBlue, fontSize: 14 }}>
            从 Git 仓库拉取或上传本地项目文件夹，代码将在云服务器多租户隔离目录下就绪，供智能体协同开发。
          </p>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <button
            onClick={() => refresh()}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'rgba(27, 42, 74, 0.5)',
              border: `1px solid ${colors.warmGold}40`,
              color: colors.moonlightSilver,
              borderRadius: 8,
              padding: '8px 16px',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            刷新
          </button>

          <button
            onClick={() => navigate(`/chat?workspace_id=${encodeURIComponent(workspaceId)}`)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
              border: 'none',
              color: colors.midnightDeep,
              borderRadius: 8,
              padding: '8px 20px',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: `0 4px 16px ${colors.warmGold}30`,
            }}
          >
            进入智能体协同开发 <ExternalLink size={14} />
          </button>
        </div>
      </div>

      {/* Feedback Alert */}
      {message && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '12px 18px',
            borderRadius: 8,
            marginBottom: 24,
            fontSize: 14,
            background: message.type === 'success' ? 'rgba(74, 222, 128, 0.1)' : 'rgba(248, 113, 113, 0.1)',
            border: `1px solid ${message.type === 'success' ? '#4ade8050' : '#f8717150'}`,
            color: message.type === 'success' ? '#4ade80' : '#f87171',
          }}
        >
          {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Workspace Switcher Bar */}
      <div
        style={{
          background: 'rgba(27, 42, 74, 0.3)',
          border: `1px solid ${colors.warmGold}20`,
          borderRadius: 12,
          padding: '16px 24px',
          marginBottom: 32,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}
      >
        <form onSubmit={handleSwitchWorkspace} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: colors.coldSilverBlue, fontSize: 14, fontWeight: 500 }}>
            当前工作空间 ID:
          </span>
          <input
            type="text"
            value={targetWsInput}
            onChange={(e) => setTargetWsInput(e.target.value)}
            placeholder="例如: project_alpha, my-proj"
            style={{
              background: 'rgba(11, 16, 38, 0.8)',
              border: `1px solid ${colors.warmGold}40`,
              color: colors.moonlightSilver,
              borderRadius: 6,
              padding: '6px 12px',
              fontSize: 13,
              outline: 'none',
              width: 180,
            }}
          />
          <button
            type="submit"
            style={{
              background: 'transparent',
              border: `1px solid ${colors.warmGold}60`,
              color: colors.warmGold,
              borderRadius: 6,
              padding: '6px 14px',
              fontSize: 13,
              cursor: 'pointer',
            }}
          >
            切换
          </button>
        </form>

        {/* Stats Badges */}
        <div style={{ display: 'flex', gap: 20, alignItems: 'center', fontSize: 13, color: colors.coldSilverBlue }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Layers size={14} color={colors.warmGold} />
            <span>文件数: <strong style={{ color: colors.moonlightSilver }}>{status?.file_count || 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <HardDrive size={14} color={colors.warmGold} />
            <span>
              总体积:{' '}
              <strong style={{ color: colors.moonlightSilver }}>
                {status ? (status.total_size_bytes / 1024).toFixed(1) : 0} KB
              </strong>
            </span>
          </div>
          {status?.is_git_repo && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <GitBranch size={14} color="#60a5fa" />
              <span>分支: <strong style={{ color: '#93c5fd' }}>{status.git_branch || 'main'}</strong></span>
            </div>
          )}
          <button
            onClick={handleDeleteWorkspace}
            title="清空工作空间"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#f87171',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 12,
              opacity: 0.8,
            }}
          >
            <Trash2 size={14} /> 清理
          </button>
        </div>
      </div>

      {/* Main Grid: Left = Import Forms, Right = Cloud File Tree */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(360px, 1fr) minmax(360px, 1.2fr)',
          gap: 32,
        }}
      >
        {/* Left Column: Import Action Card */}
        <div
          style={{
            background: 'rgba(27, 42, 74, 0.25)',
            border: `1px solid ${colors.warmGold}20`,
            borderRadius: 16,
            padding: 24,
            backdropFilter: 'blur(12px)',
          }}
        >
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: `1px solid ${colors.warmGold}20`, marginBottom: 20 }}>
            <button
              onClick={() => setActiveTab('git')}
              style={{
                flex: 1,
                padding: '10px 16px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'git' ? `2px solid ${colors.warmGold}` : 'none',
                color: activeTab === 'git' ? colors.warmGold : colors.coldSilverBlue,
                fontSize: 14,
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <FolderGit2 size={16} /> 从 Git 仓库拉取
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              style={{
                flex: 1,
                padding: '10px 16px',
                background: 'transparent',
                border: 'none',
                borderBottom: activeTab === 'upload' ? `2px solid ${colors.warmGold}` : 'none',
                color: activeTab === 'upload' ? colors.warmGold : colors.coldSilverBlue,
                fontSize: 14,
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              <UploadCloud size={16} /> 上传本地项目包
            </button>
          </div>

          {/* Tab 1: Git Clone Form */}
          {activeTab === 'git' && (
            <form onSubmit={handleGitClone} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
                  Git 仓库 URL <span style={{ color: colors.warmGold }}>*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="https://github.com/owner/repository.git"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
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

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
                    分支 / Tag (选填)
                  </label>
                  <input
                    type="text"
                    placeholder="main 或 master"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'rgba(11, 16, 38, 0.8)',
                      border: `1px solid ${colors.warmGold}30`,
                      color: colors.moonlightSilver,
                      borderRadius: 8,
                      padding: '8px 12px',
                      fontSize: 13,
                      outline: 'none',
                    }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 6 }}>
                    访问令牌 (私有仓库)
                  </label>
                  <input
                    type="password"
                    placeholder="GitHub PAT / Token"
                    value={authToken}
                    onChange={(e) => setAuthToken(e.target.value)}
                    style={{
                      width: '100%',
                      background: 'rgba(11, 16, 38, 0.8)',
                      border: `1px solid ${colors.warmGold}30`,
                      color: colors.moonlightSilver,
                      borderRadius: 8,
                      padding: '8px 12px',
                      fontSize: 13,
                      outline: 'none',
                    }}
                  />
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: colors.coldSilverBlue, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={cleanExistingGit}
                  onChange={(e) => setCleanExistingGit(e.target.checked)}
                />
                若目标工作空间已有文件，克隆前先清空
              </label>

              <button
                type="submit"
                disabled={opLoading}
                style={{
                  marginTop: 8,
                  background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
                  border: 'none',
                  color: colors.midnightDeep,
                  borderRadius: 8,
                  padding: '12px',
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: opLoading ? 'not-allowed' : 'pointer',
                  opacity: opLoading ? 0.7 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                {opLoading ? '正在拉取代码中...' : '开始克隆到云端工作空间'}
              </button>
            </form>
          )}

          {/* Tab 2: Upload Archive Form */}
          {activeTab === 'upload' && (
            <form onSubmit={handleArchiveUpload} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, color: colors.moonlightSilver, marginBottom: 8 }}>
                  选择项目压缩包 (.zip, .tar.gz, .tgz)
                </label>
                <div
                  style={{
                    border: `2px dashed ${colors.warmGold}40`,
                    borderRadius: 12,
                    padding: '32px 20px',
                    textAlign: 'center',
                    background: 'rgba(11, 16, 38, 0.4)',
                    cursor: 'pointer',
                  }}
                  onClick={() => document.getElementById('archive-file-input')?.click()}
                >
                  <UploadCloud size={36} color={colors.warmGold} style={{ marginBottom: 12 }} />
                  <p style={{ fontSize: 14, color: colors.moonlightSilver, marginBottom: 4 }}>
                    {uploadFile ? uploadFile.name : '点击选择或拖拽本地项目压缩包'}
                  </p>
                  <span style={{ fontSize: 12, color: colors.coldSilverBlue }}>
                    系统会自动进行安全防护检测并剥离外层单目录解压
                  </span>
                  <input
                    id="archive-file-input"
                    type="file"
                    accept=".zip,.tar,.tar.gz,.tgz"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                      }
                    }}
                  />
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: colors.coldSilverBlue, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={cleanExistingUpload}
                  onChange={(e) => setCleanExistingUpload(e.target.checked)}
                />
                上传解压前先清空当前工作空间现有文件
              </label>

              <button
                type="submit"
                disabled={opLoading || !uploadFile}
                style={{
                  marginTop: 8,
                  background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
                  border: 'none',
                  color: colors.midnightDeep,
                  borderRadius: 8,
                  padding: '12px',
                  fontWeight: 600,
                  fontSize: 14,
                  cursor: opLoading || !uploadFile ? 'not-allowed' : 'pointer',
                  opacity: opLoading || !uploadFile ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                {opLoading ? '正在上传解压中...' : '上传并解压到云端'}
              </button>
            </form>
          )}
        </div>

        {/* Right Column: Cloud File Tree Preview */}
        <div
          style={{
            background: 'rgba(27, 42, 74, 0.25)',
            border: `1px solid ${colors.warmGold}20`,
            borderRadius: 16,
            padding: 24,
            display: 'flex',
            flexDirection: 'column',
            maxHeight: 600,
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: `1px solid ${colors.warmGold}15`,
              paddingBottom: 12,
              marginBottom: 16,
            }}
          >
            <h3
              style={{
                fontFamily: fonts.heading,
                fontSize: 18,
                color: colors.moonlightSilver,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <FolderOpen size={18} color={colors.warmGold} />
              云端文件目录树预览
            </h3>
            <span style={{ fontSize: 12, color: colors.coldSilverBlue }}>
              磁盘位置: <code style={{ color: colors.warmGold }}>project/.../{workspaceId}</code>
            </span>
          </div>

          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              paddingRight: 8,
            }}
          >
            {tree && tree.children && tree.children.length > 0 ? (
              renderTreeNode(tree)
            ) : (
              <div
                style={{
                  height: 240,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.coldSilverBlue,
                  fontSize: 14,
                  gap: 12,
                }}
              >
                <Folder size={40} strokeWidth={1.2} opacity={0.4} />
                <span>当前工作空间为空，请在左侧从 Git 拉取或上传项目包</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
