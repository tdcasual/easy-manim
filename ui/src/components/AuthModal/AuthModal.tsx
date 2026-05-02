import { useState, useEffect, useCallback, useRef } from "react";
import { LogOut, Sparkles } from "lucide-react";
import { postSession } from "../../lib/api";
import { writeSessionToken, clearSessionToken } from "../../lib/session";
import { useSession } from "../../features/auth/useSession";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { useI18n } from "../../app/locale";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import { cn } from "../../lib/utils";

export interface AuthModalProps {
  forceShow?: boolean;
  onClose?: () => void;
}

export function AuthModal({ forceShow = false, onClose }: AuthModalProps) {
  const { isAuthenticated } = useSession();
  const { t } = useI18n();
  const { status, error, startLoading, setErrorState, succeed, reset } = useAsyncStatus();

  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(true);
  const [token, setToken] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (forceShow && !isAuthenticated) {
      setIsOpen(true);
      setIsMinimized(false);
    }
  }, [forceShow, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated && isOpen) {
      const timer = setTimeout(() => {
        setIsOpen(false);
        onClose?.();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated, isOpen, onClose]);

  const handleOpen = useCallback(() => {
    setIsOpen(true);
    setIsMinimized(false);
    reset();
  }, [reset]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
    setIsMinimized(true);
    onClose?.();
    setTimeout(() => {
      triggerRef.current?.focus();
    }, 0);
  }, [onClose]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!token.trim()) return;

      startLoading();
      try {
        const result = await postSession(token.trim());
        writeSessionToken(result.session_token);
        succeed();
        setToken("");
      } catch (err) {
        setErrorState(err instanceof Error ? err.message : t("login.errorFallback"));
      }
    },
    [token, startLoading, succeed, setErrorState, t]
  );

  const handleLogout = useCallback(() => {
    clearSessionToken();
    setIsOpen(false);
    setIsMinimized(true);
  }, []);

  const isLoading = status === "loading";

  if (!isOpen && isMinimized) {
    const miniTriggerLabel = isAuthenticated ? t("authModal.signedIn") : t("authModal.openLogin");

    return (
      <div className="fixed bottom-6 right-6 z-40">
        <button
          ref={triggerRef}
          type="button"
          onClick={handleOpen}
          aria-label={miniTriggerLabel}
          title={miniTriggerLabel}
          className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-pink-400 to-lavender-400 text-lg text-white shadow-lg transition-transform hover:scale-110"
        >
          {isAuthenticated ? "✨" : "🔒"}
        </button>
      </div>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="gap-4 rounded-3xl border-cloud-200 bg-white p-0 shadow-xl dark:border-cloud-800 dark:bg-cloud-900 sm:max-w-md">
        <DialogHeader className="border-b border-cloud-200 p-5 dark:border-cloud-800">
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-lg font-semibold text-foreground">
              <span>{isAuthenticated ? "✨" : "🔐"}</span>
              <span>{isAuthenticated ? t("login.welcome") : t("authModal.titleLogin")}</span>
            </DialogTitle>
          </div>
          <DialogDescription className="sr-only">
            {isAuthenticated ? t("authModal.successSubtitle") : t("login.subtitle")}
          </DialogDescription>
        </DialogHeader>

        <div className="px-5 pb-6">
          {isAuthenticated ? (
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="text-4xl">🎉</div>
              <p className="text-base font-medium text-foreground">{t("authModal.successTitle")}</p>
              <p className="text-sm text-muted-foreground">{t("authModal.successSubtitle")}</p>
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 rounded-xl bg-destructive/10 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
              >
                <LogOut size={16} />
                <span>{t("sidebar.logout")}</span>
              </button>
            </div>
          ) : (
            <>
              <div className="flex flex-col items-center gap-2 py-3 text-center">
                <div className="text-3xl">🌟</div>
                <h3 className="text-base font-semibold text-foreground">{t("login.welcome")}</h3>
                <p className="text-sm text-muted-foreground">{t("login.subtitle")}</p>
              </div>

              {error && (
                <div
                  className="my-3 flex items-center gap-2 rounded-xl bg-destructive/10 px-3 py-2 text-sm text-destructive"
                  role="alert"
                >
                  <span>💔</span>
                  <span>{error}</span>
                </div>
              )}

              <form className="flex flex-col gap-3" onSubmit={handleSubmit}>
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="auth-token"
                    className="flex items-center gap-1 text-sm font-medium text-foreground"
                  >
                    <span>🔑</span>
                    <span>{t("login.tokenLabel")}</span>
                  </label>
                  <input
                    id="auth-token"
                    type="text"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder={t("login.tokenPlaceholder")}
                    disabled={isLoading}
                    autoFocus
                    className="flex h-10 w-full rounded-xl border border-border bg-card px-3 py-2 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!token.trim() || isLoading}
                  className={cn(
                    "flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors transition-transform",
                    !token.trim() || isLoading
                      ? "bg-cloud-300"
                      : "bg-gradient-to-br from-pink-400 to-lavender-400 hover:-translate-y-0.5 hover:shadow-md"
                  )}
                >
                  {isLoading ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                      <span>{t("login.loggingIn")}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles size={18} />
                      <span>{t("login.submit")}</span>
                    </>
                  )}
                </button>
              </form>

              <div className="mt-3 flex flex-wrap items-center justify-center gap-1 text-xs text-muted-foreground">
                <span>💡</span>
                <span>{t("authModal.noToken")}</span>
                <span>{t("login.tokenHint")}</span>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default AuthModal;
