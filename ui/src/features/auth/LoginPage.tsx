import { useState } from "react";

import { postSession } from "../../lib/api";
import { writeSessionToken } from "../../lib/session";

export function LoginPage() {
  const [agentToken, setAgentToken] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      const created = await postSession(agentToken.trim());
      writeSessionToken(created.session_token);
      setStatus("idle");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "login_failed");
    }
  }

  return (
    <div style={{ maxWidth: 520, margin: "40px auto", padding: 20 }}>
      <h2 style={{ marginBottom: 8 }}>Log In</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Paste an issued agent token to start a session.
      </p>

      <form onSubmit={onSubmit} aria-label="login form">
        <label style={{ display: "grid", gap: 8 }}>
          <span style={{ fontSize: 13 }}>Agent token</span>
          <input
            aria-label="Agent token"
            value={agentToken}
            onChange={(e) => setAgentToken(e.target.value)}
            placeholder="easy-manim.agent-a.…"
            autoComplete="off"
            spellCheck={false}
            style={{
              padding: "10px 12px",
              borderRadius: 12,
              border: "1px solid var(--hairline)",
              background: "color-mix(in oklab, var(--surface), transparent 0%)"
            }}
          />
        </label>

        <button
          type="submit"
          disabled={status === "loading" || agentToken.trim().length === 0}
          style={{
            marginTop: 14,
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid color-mix(in oklab, var(--accent), transparent 65%)",
            background: "color-mix(in oklab, var(--accent), transparent 86%)",
            cursor: status === "loading" ? "progress" : "pointer"
          }}
        >
          {status === "loading" ? "Logging in…" : "Log in"}
        </button>

        {error ? (
          <p role="alert" style={{ marginTop: 12, color: "color-mix(in oklab, var(--accent), black 18%)" }}>
            {error}
          </p>
        ) : null}
      </form>
    </div>
  );
}

