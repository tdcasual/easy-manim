/**
 * AuthModal - Kawaii 风格认证弹窗
 * 特点：
 * - 默认折叠，需要时自动弹出
 * - 可关闭，保持未认证状态
 * - 固定在右下角
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { X, LogOut, Sparkles } from "lucide-react";
import { postSession } from "../../lib/api";
import { writeSessionToken, clearSessionToken } from "../../lib/session";
import { useSession } from "../../features/auth/useSession";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { useI18n } from "../../app/locale";
import { useDialogA11y } from "../useDialogA11y";
import styles from "./AuthModal.module.css";

export interface AuthModalProps {
  /** 强制显示（用于需要认证时自动弹出） */
  forceShow?: boolean;
  /** 当弹窗关闭时的回调 */
  onClose?: () => void;
}

export function AuthModal({ forceShow = false, onClose }: AuthModalProps) {
  const { isAuthenticated } = useSession();
  const { t } = useI18n();
  const { status, error, startLoading, setErrorState, succeed, reset } = useAsyncStatus();

  // 弹窗状态：默认折叠
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(true);
  const [token, setToken] = useState("");
  const modalRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 自动弹出逻辑
  useEffect(() => {
    if (forceShow && !isAuthenticated) {
      setIsOpen(true);
      setIsMinimized(false);
    }
  }, [forceShow, isAuthenticated]);

  // 认证成功后自动关闭
  useEffect(() => {
    if (isAuthenticated && isOpen) {
      // 延迟关闭，让用户看到成功状态
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

  useDialogA11y({
    isOpen,
    onClose: handleClose,
    dialogRef: modalRef,
    initialFocusRef: inputRef,
    restoreFocusRef: triggerRef,
  });

  // 渲染折叠状态（迷你按钮）
  if (!isOpen && isMinimized) {
    const miniTriggerLabel = isAuthenticated
      ? t("authModal.signedIn")
      : t("authModal.openLogin");

    return (
      <div className={styles.collapsed}>
        <button
          ref={triggerRef}
          type="button"
          className={styles.miniButton}
          onClick={handleOpen}
          aria-label={miniTriggerLabel}
          title={miniTriggerLabel}
        >
          {isAuthenticated ? "✨" : "🔒"}
        </button>
      </div>
    );
  }

  // 渲染展开的弹窗
  return (
    <>
      {/* 遮罩层 */}
      <div className={styles.overlay} onClick={handleClose} aria-hidden="true" />

      {/* 弹窗 */}
      <div
        ref={modalRef}
        className={styles.modal}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-title"
      >
        <div className={styles.content}>
          {/* 头部 */}
          <div className={styles.header}>
            <h2 id="auth-title" className={styles.headerTitle}>
              <span className={styles.headerEmoji}>{isAuthenticated ? "✨" : "🔐"}</span>
              <span>{isAuthenticated ? t("login.welcome") : t("authModal.titleLogin")}</span>
            </h2>
            <button
              type="button"
              className={styles.closeButton}
              onClick={handleClose}
              aria-label={t("common.close")}
            >
              <X size={18} />
            </button>
          </div>

          {/* 身体 */}
          <div className={styles.body}>
            {isAuthenticated ? (
              /* 已登录状态 */
              <div className={styles.authenticated}>
                <div className={styles.successIcon}>🎉</div>
                <p className={styles.authenticatedText}>{t("authModal.successTitle")}</p>
                <p className={styles.authenticatedSubtext}>{t("authModal.successSubtitle")}</p>
                <button type="button" className={styles.logoutButton} onClick={handleLogout}>
                  <LogOut size={16} />
                  <span>{t("sidebar.logout")}</span>
                </button>
              </div>
            ) : (
              /* 登录表单 */
              <>
                {/* 欢迎区 */}
                <div className={styles.welcome}>
                  <div className={styles.welcomeIcon}>🌟</div>
                  <h3 className={styles.welcomeTitle}>{t("login.welcome")}</h3>
                  <p className={styles.welcomeText}>{t("login.subtitle")}</p>
                </div>

                {/* 错误提示 */}
                {error && (
                  <div className={styles.error} role="alert">
                    <span className={styles.errorEmoji}>💔</span>
                    <span>{error}</span>
                  </div>
                )}

                {/* 表单 */}
                <form className={styles.form} onSubmit={handleSubmit}>
                  <div className={styles.inputGroup}>
                    <label htmlFor="auth-token" className={styles.label}>
                      <span className={styles.labelEmoji}>🔑</span>
                      <span>{t("login.tokenLabel")}</span>
                    </label>
                    <input
                      ref={inputRef}
                      id="auth-token"
                      type="text"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder={t("login.tokenPlaceholder")}
                      className={styles.input}
                      disabled={isLoading}
                      autoFocus
                    />
                  </div>

                  <button
                    type="submit"
                    className={`${styles.submitButton} ${isLoading ? styles.loading : ""}`}
                    disabled={!token.trim() || isLoading}
                  >
                    {isLoading ? (
                      <>
                        <span className={styles.spinner} />
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

                {/* 帮助链接 */}
                <div className={styles.help}>
                  <span>💡</span>
                  <span>{t("authModal.noToken")}</span>
                  <span>{t("login.tokenHint")}</span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

export default AuthModal;
