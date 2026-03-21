import { useSyncExternalStore } from "react";

import { clearSessionToken, readSessionToken, subscribeSession, writeSessionToken } from "../../lib/session";

export function useSession() {
  const token = useSyncExternalStore(subscribeSession, readSessionToken, () => null);
  return {
    sessionToken: token,
    isAuthenticated: Boolean(token),
    setSessionToken: writeSessionToken,
    clearSessionToken
  };
}

