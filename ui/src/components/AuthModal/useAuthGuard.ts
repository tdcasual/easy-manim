/**
 * useAuthGuard - 认证守卫 Hook
 * 在需要认证时自动显示 AuthModal
 * 特点：
 * - 默认不弹窗，需要时自动弹出
 * - 支持手动触发和自动触发
 * - 可关闭，不影响页面使用
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { useSession } from "../../features/auth/useSession";

interface UseAuthGuardOptions {
  /** 是否立即检查认证（用于页面加载时） */
  immediate?: boolean;
  /** 认证成功回调 */
  onAuthenticated?: () => void;
}

interface UseAuthGuardReturn {
  /** 是否显示认证弹窗 */
  showAuthModal: boolean;
  /** 手动触发显示弹窗 */
  requireAuth: () => boolean;
  /** 关闭弹窗 */
  closeAuthModal: () => void;
  /** 是否已认证 */
  isAuthenticated: boolean;
}

/**
 * 认证守卫 Hook
 * @example
 * ```tsx
 * // 在页面中使用
 * function MyPage() {
 *   const { showAuthModal, requireAuth, closeAuthModal } = useAuthGuard();
 *
 *   const handleCreateTask = () => {
 *     if (!requireAuth()) return; // 未认证时自动弹窗
 *     // 执行创建任务...
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={handleCreateTask}>创建任务</button>
 *       {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuthGuard(options: UseAuthGuardOptions = {}): UseAuthGuardReturn {
  const { immediate = false, onAuthenticated } = options;
  const { isAuthenticated } = useSession();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const hasShownRef = useRef(false);

  // 立即检查认证（用于页面加载时）
  useEffect(() => {
    if (immediate && !isAuthenticated && !hasShownRef.current) {
      // 延迟一点显示，避免页面加载时的突兀感
      const timer = setTimeout(() => {
        setShowAuthModal(true);
        hasShownRef.current = true;
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [immediate, isAuthenticated]);

  // 认证成功回调
  useEffect(() => {
    if (isAuthenticated && showAuthModal) {
      onAuthenticated?.();
    }
  }, [isAuthenticated, showAuthModal, onAuthenticated]);

  /**
   * 要求认证
   * 如果未认证，自动显示弹窗
   * @returns 是否已认证
   */
  const requireAuth = useCallback((): boolean => {
    if (isAuthenticated) {
      return true;
    }
    setShowAuthModal(true);
    return false;
  }, [isAuthenticated]);

  /**
   * 关闭弹窗
   */
  const closeAuthModal = useCallback(() => {
    setShowAuthModal(false);
  }, []);

  return {
    showAuthModal,
    requireAuth,
    closeAuthModal,
    isAuthenticated,
  };
}

export default useAuthGuard;
