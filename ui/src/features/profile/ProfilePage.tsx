import { useEffect, useState } from "react";

import { applyProfilePatch, getProfile, getProfileScorecard, AgentProfile, ProfileScorecard } from "../../lib/profileApi";
import { useSession } from "../auth/useSession";
import { SuggestionsPanel } from "./SuggestionsPanel";

function safeStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

export function ProfilePage() {
  const { sessionToken } = useSession();
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [scorecard, setScorecard] = useState<ProfileScorecard | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const [patchText, setPatchText] = useState<string>('{\n  "style_hints": {}\n}');
  const [applyState, setApplyState] = useState<"idle" | "applying">("idle");
  const [applyError, setApplyError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionToken) return;
    let cancelled = false;
    setStatus("loading");
    setError(null);
    Promise.all([getProfile(sessionToken), getProfileScorecard(sessionToken)])
      .then(([p, s]) => {
        if (cancelled) return;
        setProfile(p);
        setScorecard(s);
        setStatus("idle");
        setPatchText(safeStringify({ style_hints: (p.profile_json as any)?.style_hints ?? {} }));
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setError(err instanceof Error ? err.message : "profile_load_failed");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionToken]);

  async function onApply() {
    if (!sessionToken) return;
    setApplyError(null);
    let patch: Record<string, unknown> = {};
    try {
      const parsed = JSON.parse(patchText);
      patch = typeof parsed === "object" && parsed !== null ? (parsed as Record<string, unknown>) : {};
    } catch {
      setApplyError("patch_must_be_valid_json");
      return;
    }

    setApplyState("applying");
    try {
      await applyProfilePatch(patch, sessionToken);
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "profile_apply_failed");
    } finally {
      setApplyState("idle");
    }
  }

  if (!sessionToken) {
    return (
      <section>
        <h2>Profile</h2>
        <p className="muted">Not authenticated.</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Profile</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        Inspect the current resolved profile and apply small patches.
      </p>

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "profile_load_failed"}
        </p>
      ) : null}

      <div className="tasksGrid" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="cardTitle">Current</div>
          {profile ? (
            <div style={{ display: "grid", gap: 10 }}>
              <div>
                <div className="muted small">Agent</div>
                <div style={{ fontWeight: 600, letterSpacing: "-0.01em" }}>{profile.name}</div>
              </div>
              <div>
                <div className="muted small">Profile JSON</div>
                <pre
                  style={{
                    margin: 0,
                    padding: 12,
                    borderRadius: 12,
                    border: "1px solid color-mix(in oklab, var(--hairline), transparent 22%)",
                    background: "color-mix(in oklab, var(--surface), transparent 4%)",
                    overflow: "auto",
                    maxHeight: 260,
                    lineHeight: 1.35,
                    fontSize: 12
                  }}
                >
                  {safeStringify(profile.profile_json)}
                </pre>
              </div>
            </div>
          ) : (
            <p className="muted">{status === "loading" ? "Loading…" : "No profile yet."}</p>
          )}
        </div>

        <div className="card">
          <div className="cardTitle">Scorecard</div>
          {scorecard ? (
            <dl style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "8px 12px", margin: "12px 0 0" }}>
              <dt className="muted">Completed</dt>
              <dd style={{ margin: 0 }}>{scorecard.completed_count}</dd>
              <dt className="muted">Failed</dt>
              <dd style={{ margin: 0 }}>{scorecard.failed_count}</dd>
              <dt className="muted">Median quality</dt>
              <dd style={{ margin: 0 }}>{scorecard.median_quality_score}</dd>
            </dl>
          ) : (
            <p className="muted">{status === "loading" ? "Loading…" : "No scorecard yet."}</p>
          )}

          <div style={{ marginTop: 16 }}>
            <div className="cardTitle">Apply patch</div>
            <div className="muted small">JSON patch. Allowed keys: style_hints, output_profile, validation_profile.</div>

            <label className="field">
              <span className="fieldLabel">Patch</span>
              <textarea
                aria-label="Patch"
                className="textarea"
                rows={6}
                value={patchText}
                onChange={(e) => setPatchText(e.target.value)}
                spellCheck={false}
              />
            </label>

            <div className="buttonRow">
              <button className="button buttonPrimary" type="button" onClick={onApply} disabled={applyState !== "idle"}>
                {applyState === "applying" ? "Applying…" : "Apply patch"}
              </button>
            </div>

            {applyError ? (
              <p role="alert" className="alert">
                {applyError}
              </p>
            ) : null}
          </div>

          <SuggestionsPanel />
        </div>
      </div>
    </section>
  );
}
