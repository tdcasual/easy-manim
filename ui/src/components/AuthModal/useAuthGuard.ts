/**
 * useAuthGuard - authentication guard hook
 * Automatically shows AuthModal when auth is required.
 * Features:
 * - Does not show by default; auto-shows when needed.
 * - Supports manual and automatic triggers.
 * - Can be closed without blocking page usage.
 */
import { useState, useCallback, useEffect, useRef } from "react";
import { useSession } from "../../features/auth/useSession";

interface UseAuthGuardOptions {
  /** Whether to check auth immediately (on page load) */
  immediate?: boolean;
  /** Callback when authenticated */
  onAuthenticated?: () => void;
}

interface UseAuthGuardReturn {
  /** Whether the auth modal is visible */
  showAuthModal: boolean;
  /** Manually trigger the modal */
  requireAuth: () => boolean;
  /** Close the modal */
  closeAuthModal: () => void;
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
}

/**
 * Authentication guard hook.
 * @example
 * ```tsx
 * // Usage in a page
 * function MyPage() {
 *   const { showAuthModal, requireAuth, closeAuthModal } = useAuthGuard();
 *
 *   const handleCreateTask = () => {
 *     if (!requireAuth()) return; // auto-show modal when not authenticated
 *     // proceed to create task...
 *   };
 *
 *   return (
 *     <div>
 *       <button onClick={handleCreateTask}>Create task</button>
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

  // Immediate auth check (used on page load)
  useEffect(() => {
    if (immediate && !isAuthenticated && !hasShownRef.current) {
      // Delay slightly to avoid jarring appearance on page load
      const timer = setTimeout(() => {
        setShowAuthModal(true);
        hasShownRef.current = true;
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [immediate, isAuthenticated]);

  // Auth success callback
  useEffect(() => {
    if (isAuthenticated && showAuthModal) {
      onAuthenticated?.();
    }
  }, [isAuthenticated, showAuthModal, onAuthenticated]);

  /**
   * Require authentication.
   * Auto-shows the modal if not authenticated.
   * @returns Whether authenticated.
   */
  const requireAuth = useCallback((): boolean => {
    if (isAuthenticated) {
      return true;
    }
    setShowAuthModal(true);
    return false;
  }, [isAuthenticated]);

  /**
   * Close the modal
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
