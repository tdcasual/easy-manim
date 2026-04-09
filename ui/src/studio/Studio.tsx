/**
 * Studio - 宫崎骏风格创作工作室主容器
 * 重构后版本 - 使用 Hooks + Zustand + Tailwind CSS
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Sparkles } from "lucide-react";

// Hooks
import { useTaskManager, useHistory, useKeyboardShortcuts, useResponsive } from "./hooks";
import { useTheme } from "./hooks/useTheme";
import { useSession } from "../features/auth/useSession";
import { useI18n } from "../app/locale";

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
import { LocaleToggle } from "../components/LocaleToggle";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "../components/ui/sheet";
import { cn } from "../lib/utils";

// Loading Screen
function LoadingScreen() {
  const { t } = useI18n();

  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-4"
      style={{ background: "var(--gradient-day)" }}
    >
      <div className="animate-pop-in text-5xl">🎨</div>
      <p className="m-0 text-lg text-cloud-700 animate-fade-in">{t("studio.loading")} ✨</p>
    </div>
  );
}

function HistoryIcon() {
  return (
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
  );
}

function HelpIcon() {
  return (
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
  );
}

function SettingsIcon() {
  return (
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
  );
}

interface ToolbarAction {
  id: "history" | "help" | "settings";
  label: string;
  ariaLabel: string;
  title: string;
  icon: ReactNode;
  onClick: () => void;
}

export function Studio() {
  const { t } = useI18n();
  const { isNight, toggleTheme } = useTheme();
  const { sessionToken } = useSession();
  const { isMobile } = useResponsive();
  const { showAuthModal, closeAuthModal } = useAuthGuard();

  // Store - use selectors to avoid re-rendering on unrelated state changes
  const prompt = useStudioStore((s) => s.prompt);
  const setPrompt = useStudioStore((s) => s.setPrompt);
  const currentTask = useStudioStore((s) => s.currentTask);
  const isGenerating = useStudioStore((s) => s.isGenerating);
  const error = useStudioStore((s) => s.error);
  const isHistoryOpen = useStudioStore((s) => s.isHistoryOpen);
  const isSettingsOpen = useStudioStore((s) => s.isSettingsOpen);
  const isHelpOpen = useStudioStore((s) => s.isHelpOpen);
  const generationParams = useStudioStore((s) => s.generationParams);
  const toggleHistory = useStudioStore((s) => s.toggleHistory);
  const closeHistory = useStudioStore((s) => s.closeHistory);
  const toggleSettings = useStudioStore((s) => s.toggleSettings);
  const closeSettings = useStudioStore((s) => s.closeSettings);
  const toggleHelp = useStudioStore((s) => s.toggleHelp);
  const closeHelp = useStudioStore((s) => s.closeHelp);
  const clearError = useStudioStore((s) => s.clearError);
  const setCurrentTask = useStudioStore((s) => s.setCurrentTask);
  const updateGenerationParams = useStudioStore((s) => s.updateGenerationParams);

  // Refs
  const textareaRef = useRef<ChatInputRef>(null);
  const [isReady, setIsReady] = useState(false);
  const [isMobileActionsOpen, setIsMobileActionsOpen] = useState(false);

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
    } catch {
      // error is surfaced via store state
    }
  }, [sessionToken, prompt, generationParams, submitTask, startPolling, setPrompt]);

  // Handle cancel
  const handleCancel = useCallback(async () => {
    try {
      await cancelCurrentTask();
    } catch {
      // error is surfaced via store state
    }
  }, [cancelCurrentTask]);

  // Handle history selection
  const handleSelectHistory = useCallback(
    (id: string) => {
      const item = historyItems.find((h) => h.id === id);
      if (item) {
        setCurrentTask({
          id: item.id,
          videoUrl: item.videoUrl,
          title: item.title,
          status: item.status,
        });
      }
      closeHistory();
    },
    [historyItems, setCurrentTask, closeHistory]
  );

  if (!isReady) {
    return <LoadingScreen />;
  }

  if (!sessionToken) {
    return <Navigate to="/login" replace />;
  }

  const isNetworkError = error?.type === "network";
  const toolbarActions: ToolbarAction[] = [
    {
      id: "history",
      label: t("studio.toolbar.history"),
      ariaLabel: t("studio.toolbar.historyAria"),
      title: t("studio.toolbar.historyTitle"),
      icon: <HistoryIcon />,
      onClick: toggleHistory,
    },
    {
      id: "help",
      label: t("studio.toolbar.help"),
      ariaLabel: t("studio.toolbar.helpAria"),
      title: t("studio.toolbar.helpTitle"),
      icon: <HelpIcon />,
      onClick: toggleHelp,
    },
    {
      id: "settings",
      label: t("studio.toolbar.settings"),
      ariaLabel: t("studio.toolbar.settingsAria"),
      title: t("studio.toolbar.settingsTitle"),
      icon: <SettingsIcon />,
      onClick: toggleSettings,
    },
  ];
  const toolbarButtonClass =
    "flex items-center gap-1 rounded-full border-none bg-[var(--glass-white)] px-3 py-2 text-sm font-medium text-cloud-700 shadow-xs transition-all hover:-translate-y-0.5 hover:bg-gradient-to-br hover:from-pink-100 hover:to-lavender-100 hover:text-pink-600 hover:shadow-md active:scale-95";

  return (
    <div
      className="relative flex min-h-screen flex-col overflow-hidden"
      style={{ background: "var(--gradient-day)" }}
    >
      <SkyBackground isNight={isNight} />

      <main className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 overflow-y-auto p-4 min-h-0 sm:gap-6 sm:p-6">
        {/* Header */}
        <header className="mb-2 flex items-center justify-between rounded-2xl border border-[var(--glass-border)] bg-[var(--glass-white)] p-3 px-3 shadow-md backdrop-blur-xl transition-all duration-300 hover:shadow-lg sm:px-4">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full text-white shadow-lg animate-float transition-transform duration-300 hover:scale-110 hover:rotate-[5deg] sm:h-12 sm:w-12"
              style={{
                background:
                  "linear-gradient(135deg, var(--color-pink-300) 0%, var(--color-peach-300) 100%)",
                boxShadow: "var(--shadow-glow-pink)",
              }}
            >
              <Sparkles size={isMobile ? 18 : 22} />
            </div>
            <div className="flex flex-col">
              <h1 className="m-0 bg-gradient-to-br from-pink-500 to-lavender-500 bg-clip-text text-xl font-bold text-transparent sm:text-2xl">
                easy-manim
              </h1>
              {!isMobile && (
                <p className="m-0 flex items-center gap-1 text-xs text-cloud-700">
                  <span>✨</span>
                  {t("studio.brandSubtitle")}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <LocaleToggle />
            {isMobile ? (
              <Sheet open={isMobileActionsOpen} onOpenChange={setIsMobileActionsOpen}>
                <SheetTrigger asChild>
                  <button
                    type="button"
                    className="flex h-10 w-10 items-center justify-center rounded-full border border-[var(--glass-border)] bg-[var(--glass-white)] text-cloud-700 shadow-xs transition-all hover:-translate-y-0.5 hover:bg-gradient-to-br hover:from-pink-100 hover:to-lavender-100 hover:text-pink-600 hover:shadow-md"
                    aria-label={t("studio.toolbar.moreActionsAria")}
                    title={t("studio.toolbar.moreActionsTitle")}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <circle cx="12" cy="5" r="1.5" />
                      <circle cx="12" cy="12" r="1.5" />
                      <circle cx="12" cy="19" r="1.5" />
                    </svg>
                  </button>
                </SheetTrigger>
                <SheetContent side="right" closeLabel={t("studio.toolbar.moreActionsTitle")}>
                  <SheetHeader>
                    <SheetTitle>{t("studio.toolbar.moreActions")}</SheetTitle>
                    <SheetDescription>{t("studio.toolbar.moreActionsHint")}</SheetDescription>
                  </SheetHeader>
                  <div className="mt-4 flex flex-col gap-3">
                    {toolbarActions.map((action) => (
                      <button
                        key={action.id}
                        type="button"
                        onClick={() => {
                          action.onClick();
                          setIsMobileActionsOpen(false);
                        }}
                        className="flex items-center gap-3 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-white)] px-4 py-3 text-left text-sm font-medium text-cloud-700 transition-all hover:bg-pink-50 hover:text-pink-600"
                        aria-label={action.ariaLabel}
                        title={action.title}
                      >
                        <span className="text-cloud-600">{action.icon}</span>
                        <span>{action.label}</span>
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={() => {
                        toggleTheme();
                        setIsMobileActionsOpen(false);
                      }}
                      className="flex items-center gap-3 rounded-xl border border-[var(--glass-border)] bg-[var(--glass-white)] px-4 py-3 text-left text-sm font-medium text-cloud-700 transition-all hover:bg-pink-50 hover:text-pink-600"
                      aria-label={isNight ? t("studio.theme.toDay") : t("studio.theme.toNight")}
                    >
                      <span className="text-lg" aria-hidden="true">
                        {isNight ? "🌙" : "☀️"}
                      </span>
                      <span>{isNight ? t("studio.theme.toDay") : t("studio.theme.toNight")}</span>
                    </button>
                  </div>
                </SheetContent>
              </Sheet>
            ) : (
              <>
                {toolbarActions.map((action) => (
                  <button
                    key={action.id}
                    type="button"
                    onClick={action.onClick}
                    className={toolbarButtonClass}
                    aria-label={action.ariaLabel}
                    title={action.title}
                  >
                    {action.icon}
                    <span className="hidden sm:inline">{action.label}</span>
                  </button>
                ))}
                <div className="h-6 w-px bg-pink-200/50" />
                <div className="w-1" />
                <ThemeToggle isNight={isNight} onToggle={toggleTheme} />
              </>
            )}
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div
            role="alert"
            className={cn(
              "animate-slide-up flex items-start gap-3 rounded-2xl border-2 p-4 px-5",
              isNetworkError
                ? "border-pink-300 bg-[var(--glass-pink)] shadow-[var(--shadow-glow-pink)]"
                : "border-mint-300 bg-[var(--glass-mint)] shadow-[var(--shadow-glow-mint)]"
            )}
          >
            <div
              className={cn(
                "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-xl",
                isNetworkError ? "bg-pink-100 text-pink-600" : "bg-mint-100 text-mint-600"
              )}
            >
              {isNetworkError ? (
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

            <div className="min-w-0 flex-1">
              <div
                className={cn(
                  "mb-1 font-semibold",
                  isNetworkError ? "text-pink-600" : "text-mint-600"
                )}
              >
                {error.type === "network" && t("studio.error.network")}
                {error.type === "timeout" && t("studio.error.timeout")}
                {error.type === "generation" && t("studio.error.generation")}
                {error.type === "unknown" && t("studio.error.unknown")}
              </div>
              <div className="text-sm text-cloud-800">{error.message}</div>
            </div>

            <div className="flex items-center gap-2">
              {error.retryable && (
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="flex items-center gap-1 rounded-xl border-none bg-gradient-to-br from-mint-400 to-sky-400 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
                >
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
                  🔄 {t("studio.error.retry")}
                </button>
              )}
              <button
                type="button"
                onClick={clearError}
                aria-label={t("studio.error.close")}
                className="flex h-11 w-11 items-center justify-center rounded-full border-none bg-transparent text-cloud-700 transition-all hover:rotate-90 hover:bg-pink-100 hover:text-pink-600"
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
        <section
          className={cn("py-1 sm:py-4", !isMobile && "flex flex-1 items-center justify-center")}
        >
          <VideoStage
            videoUrl={currentTask?.videoUrl}
            isGenerating={isGenerating}
            title={currentTask?.title}
            onCancel={isGenerating ? handleCancel : undefined}
            compact={isMobile}
          />
        </section>

        {/* Chat Input */}
        <section className="pb-3 sm:pb-5">
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

      {/* Auth Modal */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
