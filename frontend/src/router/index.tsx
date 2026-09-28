import React from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { HomePage } from '../pages/Home/HomePage';
import { WorkspacePage } from '../pages/Workspace/WorkspacePage';
import { ChatPage } from '../pages/Chat/ChatPage';
import { LoginPage } from '../pages/Auth/LoginPage';
import { NotFoundPage } from '../pages/NotFound/NotFoundPage';
import { colors } from '../styles/theme';

// Protected Route Guard: requires authenticated user to access workspace and chat
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: colors.midnightDeep,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: colors.warmGold,
          fontSize: 14,
        }}
      >
        <span>正在安全验证 Mangata 身份凭证...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to={`/login?redirect=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }

  return <>{children}</>;
};

// Main Layout with minimalist Navbar & Footer
const Layout: React.FC = () => {
  return (
    <>
      <Navbar />
      <main style={{ minHeight: 'calc(100vh - 64px)' }}>
        <Outlet />
      </main>
      <Footer />
    </>
  );
};

// Chat Layout (full height)
const ChatLayout: React.FC = () => {
  return (
    <div style={{ height: '100vh', overflow: 'hidden' }}>
      <Outlet />
    </div>
  );
};

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Public home page */}
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <WorkspacePage />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Protected Chat / Multi-Agent Workspace */}
        <Route element={<ChatLayout />}>
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};
