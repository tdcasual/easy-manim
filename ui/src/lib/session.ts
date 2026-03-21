const TOKEN_KEY = "easy_manim_session_token";
const listeners = new Set<() => void>();

function emit() {
  for (const listener of Array.from(listeners)) listener();
}

export function readSessionToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeSessionToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  emit();
}

export function clearSessionToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  emit();
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
