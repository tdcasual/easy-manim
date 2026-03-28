/**
 * Studio - 宫崎骏风格创作工作室主容器
 * 重构后版本 - 使用 Hooks + Zustand
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

// Hooks
import { useTaskManager, useHistory, useKeyboardShortcuts, useResponsive } from "./hooks";
import { useTheme } from "./hooks/useTheme";
import { useSession } from "../features/auth/useSession";

// Store
import { useStudioStore } from "./store";

// Components
import { SkyBackground } from "./components/SkyBackground";
import { VideoStage } from "./components/VideoStage";
import { ChatInput, type ChatInputRef } from "./components/ChatInput";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { SettingsPanel } from "./components/SettingsPanel";
import { HelpPanel } from "./components/HelpPanel";
import { ThemeToggle } from "./components/ThemeToggle";
import { AuthModal, useAuthGuard } from "../components/AuthModal";

// Styles
import styles from "./styles/Studio.module.css";

// Loading Screen
function LoadingScreen() {
  return (
    <div className={styles.loadingScreen}>
      <div className={styles.loadingIcon}>
        <Sparkles size={48} color="var(--accent-primary)" />
      </div>
      <p className={styles.loadingText}>正在加载创作室...</p>
    </div>
  );
}

export function Studio() {
  const { isNight, toggleTheme } = useTheme();
  const { sessionToken } = useSession();
  const { isMobile } = useResponsive();
  const { showAuthModal, closeAuthModal } = useAuthGuard();

  // Store - 使用 selector 模式获取状态
  const {
    prompt,
    setPrompt,
    currentTask,
    isGenerating,
    error,
    isHistoryOpen,
    isSettingsOpen,
    isHelpOpen,
    generationParams,
    toggleHistory,
    closeHistory,
    toggleSettings,
    closeSettings,
    toggleHelp,
    closeHelp,
    clearError,
    setCurrentTask,
    updateGenerationParams,
  } = useStudioStore();

  // Refs
  const textareaRef = useRef<ChatInputRef>(null);
  const [isReady, setIsReady] = useState(false);

  // History
  const { historyItems, loadHistory } = useHistory({ sessionToken });

  // Task Manager
  const { submitTask, startPolling, cancelCurrentTask } = useTaskManager({
    sessionToken,
    onTaskComplete: loadHistory,
  });

  // Keyboard shortcuts
  useKeyboardShortcuts({
    isSettingsOpen,
    isHistoryOpen,
    isHelpOpen,
    onToggleSettings: toggleSettings,
    onToggleHistory: toggleHistory,
    onToggleHelp: toggleHelp,
    onToggleTheme: toggleTheme,
    onFocusInput: () => textareaRef.current?.focus(),
  });

  // Initialize
  useEffect(() => {
    setIsReady(true);
    if (sessionToken) {
      loadHistory();
    }
  }, [sessionToken, loadHistory]);

  // Handle submit
  const handleSubmit = useCallback(async () => {
    if (!sessionToken || !prompt.trim()) return;

    try {
      const { success, taskId } = await submitTask({
        prompt: prompt.trim(),
        ...generationParams,
      });

      if (success && taskId) {
        setPrompt("");
        startPolling(taskId);
      }
    } catch (err) {
      // submitTask 内部已处理错误，这里只是防止意外异常
      console.error("Submit task failed:", err);
    }
  }, [sessionToken, prompt, generationParams, submitTask, startPolling, setPrompt]);

  // Handle cancel
  const handleCancel = useCallback(async () => {
    try {
      await cancelCurrentTask();
    } catch (err) {
      // cancelCurrentTask 内部已处理错误
      console.error("Cancel task failed:", err);
    }
  }, [cancelCurrentTask]);

  // Handle history selection
  const handleSelectHistory = useCallback(
    (id: string) => {
      const item = historyItems.find((h) => h.id === id);
      if (item) {
        setCurrentTask({
          id: item.id,
          videoUrl: item.thumbnailUrl,
          title: item.title,
          status: item.status,
        });
      }
      closeHistory();
    },
    [historyItems, setCurrentTask, closeHistory]
  );

  // Loading state
  if (!isReady) {
    return <LoadingScreen />;
  }

  // Auth check
  if (!sessionToken) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className={styles.studio}>
      <SkyBackground isNight={isNight} />

      <main className={styles.main}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.logoSection}>
            <div className={styles.logo}>
              <Sparkles size={22} />
            </div>
            <div className={styles.brand}>
              <h1 className={styles.brandTitle}>easy-manim</h1>
              {!isMobile && <p className={styles.brandSubtitle}>AI 动画创作室</p>}
            </div>
          </div>

          <div className={styles.toolbar}>
            <button
              type="button"
              onClick={toggleHistory}
              className={styles.toolbarButton}
              aria-label="打开历史记录"
              title="历史 (H)"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
              <span>历史</span>
            </button>
            <button
              type="button"
              onClick={toggleHelp}
              className={styles.toolbarButton}
              aria-label="打开帮助"
              title="帮助 (?)"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span>帮助</span>
            </button>
            <button
              type="button"
              onClick={toggleSettings}
              className={styles.toolbarButton}
              aria-label="打开设置"
              title="设置 (S)"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 6.34L2.1 2.1m17.8 17.8l-4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1" />
              </svg>
              <span>设置</span>
            </button>
            <div className={styles.toolbarDivider} />
            <div className={styles.spacer} />
            <ThemeToggle isNight={isNight} onToggle={toggleTheme} />
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div
            role="alert"
            className={`${styles.errorBanner} ${error.type === "network" ? styles.errorBannerNetwork : styles.errorBannerOther}`}
          >
            <div
              className={`${styles.errorIcon} ${error.type === "network" ? styles.errorIconNetwork : styles.errorIconOther}`}
            >
              {error.type === "network" ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0119 12.55M5 12.55a10.94 10.94 0 011.88-1.49m12.14-.22a9 9 0 11-12.73 0M8.53 16.11a6 6 0 016.95 0M12 20h.01" />
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              )}
            </div>

            <div className={styles.errorContent}>
              <div
                className={`${styles.errorTitle} ${error.type === "network" ? styles.errorTitleNetwork : styles.errorTitleOther}`}
              >
                {error.type === "network" && "网络错误"}
                {error.type === "timeout" && "请求超时"}
                {error.type === "generation" && "生成失败"}
                {error.type === "unknown" && "出错了"}
              </div>
              <div className={styles.errorMessage}>{error.message}</div>
            </div>

            <div className={styles.errorActions}>
              {error.retryable && (
                <button type="button" onClick={handleSubmit} className={styles.retryButton}>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
                  </svg>
                  重试
                </button>
              )}
              <button
                type="button"
                onClick={clearError}
                aria-label="关闭错误提示"
                className={styles.closeButton}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Video Stage */}
        <section className={styles.videoSection}>
          <VideoStage
            videoUrl={currentTask?.videoUrl}
            isGenerating={isGenerating}
            title={currentTask?.title}
            onCancel={isGenerating ? handleCancel : undefined}
          />
        </section>

        {/* Chat Input */}
        <section className={styles.inputSection}>
          <ChatInput
            ref={textareaRef}
            value={prompt}
            onChange={setPrompt}
            onSubmit={handleSubmit}
            isLoading={isGenerating}
          />
        </section>
      </main>

      {/* Overlays */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={closeHistory}
        items={historyItems}
        onItemClick={handleSelectHistory}
        activeId={currentTask?.id}
      />

      <SettingsPanel
        isOpen={isSettingsOpen}
        onClose={closeSettings}
        params={generationParams}
        onParamsChange={updateGenerationParams}
      />

      <HelpPanel isOpen={isHelpOpen} onClose={closeHelp} />

      {/* 🔐 认证弹窗 - 默认折叠，需要时自动弹出 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
