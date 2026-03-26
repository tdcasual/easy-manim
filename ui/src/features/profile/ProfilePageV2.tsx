import { useEffect, useState, useCallback } from "react";
import { UserCircle, RefreshCw, CheckCircle, Loader2, AlertCircle, ChevronDown } from "lucide-react";
import { useSession } from "../auth/useSession";
import { 
  AgentProfile, 
  applyProfilePatch, 
  getProfile, 
  getProfileScorecard, 
  ProfileScorecard 
} from "../../lib/profileApi";
import { SkeletonMetricCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/ARIALiveRegion";
import { getStatusLabel } from "../../app/ui";
import "./ProfilePageV2.css";

export function ProfilePageV2() {
  const { sessionToken } = useSession();
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [scorecard, setScorecard] = useState<ProfileScorecard | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [patchText, setPatchText] = useState('{"style_hints": {}}');
  const [applyState, setApplyState] = useState<"idle" | "applying">("idle");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [showExample, setShowExample] = useState(false);
  const { ARIALiveRegion, announcePolite } = useARIAMessage();
  
  // JSON 示例
  const jsonExample = JSON.stringify({
    style_hints: {
      preferred_color: "blue",
      animation_speed: "normal",
      text_language: "zh",
      complexity_level: "medium"
    },
    behavior: {
      auto_retry: true,
      confirm_before_render: false
    }
  }, null, 2);
  
  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    setStatus("loading");
    try {
      const [nextProfile, nextScorecard] = await Promise.all([
        getProfile(sessionToken),
        getProfileScorecard(sessionToken)
      ]);
      setProfile(nextProfile);
      setScorecard(nextScorecard);
      setPatchText(JSON.stringify({ 
        style_hints: (nextProfile.profile_json as any)?.style_hints || {} 
      }, null, 2));
      setStatus("idle");
    } catch {
      setStatus("error");
    }
  }, [sessionToken]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  // 实时 JSON 验证
  useEffect(() => {
    try {
      JSON.parse(patchText);
      setJsonError(null);
    } catch (e) {
      setJsonError("JSON 格式错误，请检查语法");
    }
  }, [patchText]);
  
  async function onApply() {
    if (!sessionToken) return;
    
    // 验证 JSON
    let patch: Record<string, unknown> = {};
    try {
      patch = JSON.parse(patchText);
    } catch {
      setJsonError("无效的 JSON 格式，请检查语法");
      announcePolite("应用失败：JSON 格式错误");
      return;
    }
    
    setApplyState("applying");
    try {
      await applyProfilePatch(patch, sessionToken);
      await refresh();
      announcePolite("画像补丁已应用");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "应用失败";
      setJsonError(errorMsg);
      announcePolite(`应用失败: ${errorMsg}`);
    } finally {
      setApplyState("idle");
    }
  }
  
  if (!sessionToken) {
    return (
      <div className="page-v2">
        <div className="empty-state-v2">当前未登录</div>
      </div>
    );
  }
  
  return (
    <div className="page-v2">
      {/* ARIA Live 区域 */}
      <ARIALiveRegion />
      
      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">身份</div>
          <h1 className="page-title-v2">画像</h1>
          <p className="page-description-v2">
            查看当前生效的智能体画像、最近表现信号，以及明确的补丁修改
          </p>
        </div>
        <button 
          className="refresh-btn"
          onClick={refresh}
          disabled={status === "loading"}
        >
          {status === "loading" ? (
            <Loader2 size={18} className="spin" />
          ) : (
            <RefreshCw size={18} />
          )}
          刷新
        </button>
      </div>
      
      {!scorecard && status === "loading" ? (
        <div className="metrics-grid-v2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : scorecard ? (
        <div className="metrics-grid-v2">
          <div className="metric-card-v2" style={{ '--card-color': 'var(--success)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' }}>
              <CheckCircle size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">已完成</p>
              <h3 className="metric-value-v2">{scorecard.completed_count}</h3>
            </div>
          </div>
          <div className="metric-card-v2" style={{ '--card-color': 'var(--error)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(239, 68, 68, 0.15)', color: 'var(--error)' }}>
              <UserCircle size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">失败数</p>
              <h3 className="metric-value-v2">{scorecard.failed_count}</h3>
            </div>
          </div>
          <div className="metric-card-v2" style={{ '--card-color': 'var(--accent-purple)' } as React.CSSProperties}>
            <div className="metric-icon-wrapper" style={{ background: 'rgba(139, 92, 246, 0.15)', color: 'var(--accent-purple)' }}>
              <UserCircle size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">质量中位数</p>
              <h3 className="metric-value-v2">{scorecard.median_quality_score ?? "—"}</h3>
            </div>
          </div>
        </div>
      ) : null}
      
      <div className="content-grid-v2">
        <div className="main-column">
          <div className="section-card-v2">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <UserCircle size={20} />
                当前画像
              </h3>
            </div>
            
            {profile && (
              <div className="profile-content">
                <div className="profile-header">
                  <div className="profile-avatar">
                    {profile.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="profile-info">
                    <h4>{profile.name}</h4>
                    <div className="profile-meta">
                      <span className="profile-badge">版本 {profile.profile_version}</span>
                      <span className={`profile-status ${profile.status}`}>{getStatusLabel(profile.status)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="profile-json">
                  <label>画像 JSON</label>
                  <pre>{JSON.stringify(profile.profile_json, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="side-column">
          <div className="section-card-v2">
            <div className="section-header-v2">
              <h3 className="section-title-v2">应用补丁</h3>
            </div>
            <div className="patch-form">
              {/* JSON 示例折叠面板 */}
              <details 
                className="json-example-panel"
                open={showExample}
                onToggle={(e) => setShowExample(e.currentTarget.open)}
              >
                <summary className="json-example-summary">
                  <ChevronDown size={16} className={`json-example-icon ${showExample ? 'open' : ''}`} />
                  查看 JSON 示例
                </summary>
                <pre className="json-example-code">{jsonExample}</pre>
              </details>
              
              <textarea
                className={`form-textarea-v2 code ${jsonError ? 'error' : ''}`}
                value={patchText}
                onChange={(e) => setPatchText(e.target.value)}
                rows={10}
                spellCheck={false}
                aria-invalid={!!jsonError}
                aria-describedby={jsonError ? "json-error" : undefined}
              />
              
              {jsonError && (
                <div id="json-error" className="form-error-v2" role="alert">
                  <AlertCircle size={16} />
                  {jsonError}
                </div>
              )}
              
              <button 
                className="submit-btn-v2"
                onClick={onApply}
                disabled={applyState !== "idle" || !!jsonError}
                aria-busy={applyState === "applying"}
              >
                {applyState === "applying" ? (
                  <><Loader2 size={18} className="spin" /> 应用中...</>
                ) : (
                  "应用补丁"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
