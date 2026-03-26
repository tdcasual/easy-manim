import { useEffect, useState } from "react";

import { getStatusLabel, JsonBlock, MetricChip, PageIntro, SectionPanel } from "../../app/ui";
import { AgentProfile, applyProfilePatch, getProfile, getProfileScorecard, ProfileScorecard } from "../../lib/profileApi";
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
      .then(([nextProfile, nextScorecard]) => {
        if (cancelled) return;
        setProfile(nextProfile);
        setScorecard(nextScorecard);
        setStatus("idle");
        setPatchText(safeStringify({ style_hints: (nextProfile.profile_json as any)?.style_hints ?? {} }));
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

  async function refresh() {
    if (!sessionToken) return;
    setStatus("loading");
    setError(null);
    try {
      const [nextProfile, nextScorecard] = await Promise.all([getProfile(sessionToken), getProfileScorecard(sessionToken)]);
      setProfile(nextProfile);
      setScorecard(nextScorecard);
      setStatus("idle");
      setPatchText(safeStringify({ style_hints: (nextProfile.profile_json as any)?.style_hints ?? {} }));
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "profile_load_failed");
    }
  }

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
      await refresh();
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "profile_apply_failed");
    } finally {
      setApplyState("idle");
    }
  }

  if (!sessionToken) {
    return (
      <section className="page">
        <h2>画像</h2>
        <p className="muted">当前未登录。</p>
      </section>
    );
  }

  return (
    <section className="page">
      <PageIntro
        eyebrow="身份"
        title="画像"
        description="查看当前生效的智能体画像、最近表现信号，以及明确的补丁修改，而不是让风格在多轮交互中随意漂移。"
        actions={
          <button className="button buttonQuiet" type="button" onClick={() => void refresh()} disabled={status === "loading"}>
            {status === "loading" ? "正在刷新…" : "刷新"}
          </button>
        }
        aside={
          <div className="metricStrip">
            <MetricChip label="已完成" value={scorecard?.completed_count ?? 0} />
            <MetricChip label="失败数" value={scorecard?.failed_count ?? 0} />
            <MetricChip label="质量中位数" value={scorecard?.median_quality_score ?? "—"} />
          </div>
        }
      />

      {status === "error" ? (
        <p role="alert" className="alert">
          {error || "profile_load_failed"}
        </p>
      ) : null}

      <div className="pageSplit">
        <SectionPanel title="当前画像" detail="当前智能体实际生效的画像 JSON 与策略 JSON。">
          {profile ? (
            <div className="resultStack">
              <div className="profileIdentity">
                <div>
                  <span className="muted small">智能体</span>
                  <div className="identityCode identityCode--soft">{profile.name}</div>
                </div>
                <div className="metaChips">
                  <span className="metaChip">版本 {profile.profile_version}</span>
                  <span className="metaChip">{getStatusLabel(profile.status)}</span>
                </div>
              </div>

              <div className="infoBlock">
                <span className="infoLabel">画像 JSON</span>
                <JsonBlock value={profile.profile_json} />
              </div>

              <div className="infoBlock">
                <span className="infoLabel">策略 JSON</span>
                <JsonBlock value={profile.policy_json} />
              </div>
            </div>
          ) : (
            <p className="muted">{status === "loading" ? "正在加载…" : "暂时还没有画像数据。"}</p>
          )}
        </SectionPanel>

        <div className="pageStack">
          <SectionPanel title="评分卡" detail="快速查看最近画像表现、失败聚集情况和主要问题码。">
            {scorecard ? (
              <div className="resultStack">
                <dl className="factsGrid">
                  <dt className="muted">已完成</dt>
                  <dd>{scorecard.completed_count}</dd>
                  <dt className="muted">失败</dt>
                  <dd>{scorecard.failed_count}</dd>
                  <dt className="muted">近期失败</dt>
                  <dd>{scorecard.failed_count_recent}</dd>
                  <dt className="muted">质量中位数</dt>
                  <dd>{scorecard.median_quality_score}</dd>
                </dl>

                <div className="metaChips">
                  {scorecard.top_issue_codes.length ? (
                    scorecard.top_issue_codes.map((issue) => (
                      <span key={issue} className="metaChip">
                        {issue}
                      </span>
                    ))
                  ) : (
                    <span className="metaChip">近期没有问题码</span>
                  )}
                </div>
              </div>
            ) : (
              <p className="muted">{status === "loading" ? "正在加载…" : "暂时还没有评分卡。"}</p>
            )}
          </SectionPanel>

          <SectionPanel title="应用补丁" detail="允许修改的键：style_hints、output_profile、validation_profile。">
            <label className="field">
              <span className="fieldLabel">补丁 JSON</span>
              <textarea
                aria-label="补丁 JSON"
                className="textarea textarea--code"
                rows={9}
                value={patchText}
                onChange={(event) => setPatchText(event.target.value)}
                spellCheck={false}
              />
            </label>

            <div className="buttonRow">
              <button className="button buttonPrimary" type="button" onClick={onApply} disabled={applyState !== "idle"}>
                {applyState === "applying" ? "正在应用…" : "应用补丁"}
              </button>
            </div>

            {applyError ? (
              <p role="alert" className="alert">
                {applyError}
              </p>
            ) : null}
          </SectionPanel>

          <SuggestionsPanel />
        </div>
      </div>
    </section>
  );
}
