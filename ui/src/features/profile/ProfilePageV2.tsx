import { useEffect, useState, useCallback, useMemo } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import {
  RefreshCw,
  CheckCircle,
  Loader2,
  AlertCircle,
  ChevronDown,
  Code,
  Palette,
  Save,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  Crown,
} from "lucide-react";
import { useSession } from "../auth/useSession";
import {
  AgentProfile,
  applyProfilePatch,
  getProfile,
  getProfileScorecard,
  listProfileSuggestions,
  listProfileStrategies,
  ProfileSuggestion,
  ProfileScorecard,
  StrategyProfileSummary,
} from "../../lib/profileApi";
import { getRuntimeStatus, RuntimeStatus } from "../../lib/runtimeApi";
import { SkeletonMetricCard } from "../../components/Skeleton";
import { useARIAMessage } from "../../components/useARIAMessage";
import { useToast } from "../../components/useToast";
import { useI18n } from "../../app/locale";
import { getStatusLabel } from "../../app/ui";
import { AuthModal, useAuthGuard } from "../../components/AuthModal";
import "./ProfilePageV2.css";

// 编辑器模式
type EditorMode = "visual" | "json";

// 可视化表单数据类型
interface VisualFormData {
  preferred_color: string;
  animation_speed: "slow" | "normal" | "fast";
  text_language: "zh" | "en" | "auto";
  complexity_level: "simple" | "medium" | "complex";
  auto_retry: boolean;
  confirm_before_render: boolean;
  style_notes: string;
}

// 默认表单数据
const defaultFormData: VisualFormData = {
  preferred_color: "blue",
  animation_speed: "normal",
  text_language: "auto",
  complexity_level: "medium",
  auto_retry: true,
  confirm_before_render: false,
  style_notes: "",
};

// Kawaii 颜色选项 - 使用粉彩色系
const colorOptions = [
  { value: "blue", label: "天空蓝", hex: "#7FC4DB", emoji: "☁️" },
  { value: "green", label: "薄荷绿", hex: "#7FD4B6", emoji: "🌿" },
  { value: "purple", label: "薰衣草", hex: "#DDA0DD", emoji: "🪻" },
  { value: "orange", label: "蜜桃橙", hex: "#FFB080", emoji: "🍑" },
  { value: "pink", label: "樱花粉", hex: "#FFA0B5", emoji: "🌸" },
  { value: "yellow", label: "柠檬黄", hex: "#FFF7A8", emoji: "🍋" },
];

// 速度选项 - 带 emoji
const speedOptions = [
  { value: "slow", label: "慢速", desc: "舒缓的动画节奏", emoji: "🐢" },
  { value: "normal", label: "正常", desc: "标准动画速度", emoji: "🐰" },
  { value: "fast", label: "快速", desc: "紧凑的动画节奏", emoji: "⚡" },
];

// 复杂度选项 - 带 emoji
const complexityOptions = [
  { value: "simple", label: "简洁", desc: "清晰的视觉呈现", emoji: "✨" },
  { value: "medium", label: "适中", desc: "平衡的视觉效果", emoji: "🎨" },
  { value: "complex", label: "丰富", desc: "多层次的动画", emoji: "🌈" },
];

// 趋势指示器组件
function TrendIndicator({ current, previous }: { current: number; previous?: number }) {
  if (!previous || current === previous) {
    return <Minus size={14} className="trend-neutral" />;
  }
  const isUp = current > previous;
  const percent = Math.abs(((current - previous) / previous) * 100);
  return (
    <span className={`trend ${isUp ? "up" : "down"}`}>
      {isUp ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
      <span>{percent.toFixed(0)}%</span>
    </span>
  );
}

// 可视化编辑器组件
function VisualEditor({
  data,
  onChange,
}: {
  data: VisualFormData;
  onChange: (data: VisualFormData) => void;
}) {
  const { t } = useI18n();

  const updateField = <K extends keyof VisualFormData>(key: K, value: VisualFormData[K]) => {
    onChange({ ...data, [key]: value });
  };

  return (
    <div className="visual-editor">
      {/* 颜色偏好 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">🎨</span>
          {t("profile.preferredColor")}
        </label>
        <div className="color-picker">
          {colorOptions.map((color) => (
            <button
              key={color.value}
              type="button"
              className={`color-option ${data.preferred_color === color.value ? "active" : ""}`}
              onClick={() => updateField("preferred_color", color.value)}
              style={{ backgroundColor: color.hex }}
              title={color.label}
              aria-label={color.label}
            >
              <span className="color-emoji">{color.emoji}</span>
              {data.preferred_color === color.value && (
                <CheckCircle size={14} className="color-check" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 动画速度 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">⚡</span>
          {t("profile.animationSpeed")}
        </label>
        <div className="option-cards">
          {speedOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`option-card ${data.animation_speed === option.value ? "active" : ""}`}
              onClick={() =>
                updateField("animation_speed", option.value as VisualFormData["animation_speed"])
              }
            >
              <span className="option-emoji">{option.emoji}</span>
              <span className="option-title">{option.label}</span>
              <span className="option-desc">{option.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 复杂度 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">🌟</span>
          {t("profile.complexityLevel")}
        </label>
        <div className="option-cards">
          {complexityOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              className={`option-card ${data.complexity_level === option.value ? "active" : ""}`}
              onClick={() =>
                updateField("complexity_level", option.value as VisualFormData["complexity_level"])
              }
            >
              <span className="option-emoji">{option.emoji}</span>
              <span className="option-title">{option.label}</span>
              <span className="option-desc">{option.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 文本语言 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">🌐</span>
          {t("profile.textLanguage")}
        </label>
        <div className="select-wrapper">
          <select
            className="form-select"
            value={data.text_language}
            onChange={(e) =>
              updateField("text_language", e.target.value as VisualFormData["text_language"])
            }
          >
            <option value="auto">🌍 {t("profile.langAuto")}</option>
            <option value="zh">🇨🇳 {t("profile.langZh")}</option>
            <option value="en">🇬🇧 {t("profile.langEn")}</option>
          </select>
        </div>
      </div>

      {/* 行为设置 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">⚙️</span>
          {t("profile.behaviorSettings")}
        </label>
        <div className="checkbox-group">
          <label className="checkbox-label">
            <div className="checkbox-wrapper">
              <input
                type="checkbox"
                checked={data.auto_retry}
                onChange={(e) => updateField("auto_retry", e.target.checked)}
              />
              <span className="checkbox-custom"></span>
            </div>
            <span className="checkbox-text">
              <span className="checkbox-title">🔄 {t("profile.autoRetry")}</span>
              <span className="checkbox-desc">{t("profile.autoRetryDesc")}</span>
            </span>
          </label>
          <label className="checkbox-label">
            <div className="checkbox-wrapper">
              <input
                type="checkbox"
                checked={data.confirm_before_render}
                onChange={(e) => updateField("confirm_before_render", e.target.checked)}
              />
              <span className="checkbox-custom"></span>
            </div>
            <span className="checkbox-text">
              <span className="checkbox-title">✋ {t("profile.confirmBeforeRender")}</span>
              <span className="checkbox-desc">{t("profile.confirmBeforeRenderDesc")}</span>
            </span>
          </label>
        </div>
      </div>

      {/* 风格备注 */}
      <div className="form-group">
        <label className="form-label">
          <span className="label-emoji">💭</span>
          {t("profile.styleNotes")}
        </label>
        <textarea
          className="form-textarea"
          value={data.style_notes}
          onChange={(e) => updateField("style_notes", e.target.value)}
          placeholder={t("profile.styleNotesPlaceholder")}
          rows={3}
        />
      </div>
    </div>
  );
}

// 装饰云朵组件
function FloatingClouds() {
  return (
    <div className="floating-clouds" aria-hidden="true">
      <div className="cloud cloud-1">☁️</div>
      <div className="cloud cloud-2">☁️</div>
      <div className="cloud cloud-3">✨</div>
      <div className="cloud cloud-4">🌸</div>
    </div>
  );
}

const capabilityLabels: Record<string, string> = {
  agent_learning_auto_apply_enabled: "Agent learning auto apply",
  auto_repair_enabled: "Auto repair",
  multi_agent_workflow_enabled: "Multi-agent workflow",
  multi_agent_workflow_auto_challenger_enabled: "Auto challenger",
  multi_agent_workflow_auto_arbitration_enabled: "Auto arbitration",
  multi_agent_workflow_guarded_rollout_enabled: "Guarded rollout",
  strategy_promotion_enabled: "Strategy promotion",
  strategy_promotion_guarded_auto_apply_enabled: "Guarded strategy promotion",
};

function formatCapabilityLabel(key: string) {
  return capabilityLabels[key] ?? key.replaceAll("_", " ");
}

function formatSupportSummary(counts?: Record<string, number>) {
  const entries = Object.entries(counts ?? {});
  if (!entries.length) return "No field evidence";
  return entries
    .slice(0, 3)
    .map(([field, count]) => `${field}: ${count}`)
    .join(" | ");
}

function formatCountSummary(counts?: Record<string, number>) {
  const entries = Object.entries(counts ?? {}).sort(([left], [right]) => left.localeCompare(right));
  if (!entries.length) return "none";
  return entries.map(([label, count]) => `${label} ${count}`).join(" | ");
}

function formatRoleStatusSummary(roleStatusCounts?: Record<string, Record<string, number>>) {
  const entries = Object.entries(roleStatusCounts ?? {}).sort(([left], [right]) =>
    left.localeCompare(right)
  );
  if (!entries.length) return "none";
  return entries.map(([role, counts]) => `${role} [${formatCountSummary(counts)}]`).join(" | ");
}

// 主组件
export function ProfilePageV2() {
  const { sessionToken } = useSession();
  const { locale, t } = useI18n();
  const { success: toastSuccess, error: toastError } = useToast();
  const { showAuthModal, closeAuthModal } = useAuthGuard();
  const [profile, setProfile] = useState<AgentProfile | null>(null);
  const [scorecard, setScorecard] = useState<ProfileScorecard | null>(null);
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatus | null>(null);
  const [suggestions, setSuggestions] = useState<ProfileSuggestion[]>([]);
  const [strategies, setStrategies] = useState<StrategyProfileSummary[]>([]);
  const [scorecardHistory, setScorecardHistory] = useState<ProfileScorecard[]>([]);
  const { status, startLoading, setErrorState, succeed } = useAsyncStatus();
  const [patchText, setPatchText] = useState('{"style_hints": {}}');
  const [applyState, setApplyState] = useState<"idle" | "applying">("idle");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [showExample, setShowExample] = useState(false);
  const [editorMode, setEditorMode] = useState<EditorMode>("visual");
  const [formData, setFormData] = useState<VisualFormData>(defaultFormData);
  const { ARIALiveRegion, announcePolite } = useARIAMessage();

  // JSON 示例
  const jsonExample = JSON.stringify(
    {
      style_hints: {
        preferred_color: "blue",
        animation_speed: "normal",
        text_language: locale === "zh-CN" ? "zh" : "en",
        complexity_level: "medium",
      },
      behavior: {
        auto_retry: true,
        confirm_before_render: false,
      },
    },
    null,
    2
  );

  // 从 profile_json 解析表单数据
  const parseProfileToForm = useCallback((profileJson: Record<string, unknown>): VisualFormData => {
    const styleHints = (profileJson.style_hints as Record<string, unknown>) ?? {};
    const behavior = (profileJson.behavior as Record<string, unknown>) ?? {};

    return {
      preferred_color: (styleHints.preferred_color as string) ?? "blue",
      animation_speed:
        (styleHints.animation_speed as VisualFormData["animation_speed"]) ?? "normal",
      text_language: (styleHints.text_language as VisualFormData["text_language"]) ?? "auto",
      complexity_level:
        (styleHints.complexity_level as VisualFormData["complexity_level"]) ?? "medium",
      auto_retry: (behavior.auto_retry as boolean) ?? true,
      confirm_before_render: (behavior.confirm_before_render as boolean) ?? false,
      style_notes: (styleHints.style_notes as string) ?? "",
    };
  }, []);

  // 将表单数据转换为 JSON
  const formToPatch = useCallback((data: VisualFormData): Record<string, unknown> => {
    return {
      style_hints: {
        preferred_color: data.preferred_color,
        animation_speed: data.animation_speed,
        text_language: data.text_language,
        complexity_level: data.complexity_level,
        style_notes: data.style_notes,
      },
      behavior: {
        auto_retry: data.auto_retry,
        confirm_before_render: data.confirm_before_render,
      },
    };
  }, []);

  const refresh = useCallback(async () => {
    if (!sessionToken) return;
    startLoading();
    try {
      const [nextProfile, nextScorecard, nextRuntimeStatus, nextSuggestions, nextStrategies] =
        await Promise.all([
          getProfile(sessionToken),
          getProfileScorecard(sessionToken),
          getRuntimeStatus(sessionToken),
          listProfileSuggestions(sessionToken),
          listProfileStrategies(sessionToken),
        ]);
      setProfile(nextProfile);
      setScorecard(nextScorecard);
      setRuntimeStatus(nextRuntimeStatus);
      setSuggestions(Array.isArray(nextSuggestions.items) ? nextSuggestions.items : []);
      setStrategies(Array.isArray(nextStrategies.items) ? nextStrategies.items : []);
      setScorecardHistory((prev) => [...prev.slice(-4), nextScorecard]);

      // 同步表单数据
      const parsedForm = parseProfileToForm(nextProfile.profile_json ?? {});
      setFormData(parsedForm);

      // 同步 JSON
      setPatchText(JSON.stringify(formToPatch(parsedForm), null, 2));
      succeed();
    } catch {
      setErrorState(t("profile.loadFailed"));
      toastError(t("profile.loadFailed"));
    }
  }, [
    sessionToken,
    parseProfileToForm,
    formToPatch,
    t,
    toastError,
    startLoading,
    succeed,
    setErrorState,
  ]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // 实时 JSON 验证（仅在 JSON 模式下）
  useEffect(() => {
    if (editorMode !== "json") return;
    try {
      JSON.parse(patchText);
      setJsonError(null);
    } catch {
      setJsonError(t("profile.jsonInvalid"));
    }
  }, [patchText, t, editorMode]);

  // 同步表单和 JSON
  useEffect(() => {
    if (editorMode === "visual") {
      setPatchText(JSON.stringify(formToPatch(formData), null, 2));
    }
  }, [formData, editorMode, formToPatch]);

  async function onApply() {
    if (!sessionToken) return;

    // 根据编辑器模式获取 patch
    let patch: Record<string, unknown>;
    if (editorMode === "visual") {
      patch = formToPatch(formData);
    } else {
      try {
        patch = JSON.parse(patchText) as Record<string, unknown>;
      } catch {
        setJsonError(t("profile.jsonParseFailed"));
        announcePolite(t("profile.applyFailed", { error: t("profile.jsonInvalid") }));
        return;
      }
    }

    setApplyState("applying");
    try {
      await applyProfilePatch(patch, sessionToken);
      await refresh();
      toastSuccess(t("profile.applied"));
      announcePolite(t("profile.applied"));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : t("common.applying");
      setJsonError(errorMsg);
      toastError(errorMsg);
      announcePolite(t("profile.applyFailed", { error: errorMsg }));
    } finally {
      setApplyState("idle");
    }
  }

  // 获取上一期的分数用于趋势对比
  const previousScorecard = useMemo(() => {
    if (scorecardHistory.length < 2) return undefined;
    return scorecardHistory[scorecardHistory.length - 2];
  }, [scorecardHistory]);
  const qualityPassedCount = scorecard?.quality_passed_count ?? scorecard?.completed_count ?? 0;
  const previousQualityPassedCount =
    previousScorecard?.quality_passed_count ?? previousScorecard?.completed_count;

  if (!sessionToken) {
    return (
      <div className="page-v2 page-kawaii">
        <FloatingClouds />
        <div className="empty-state-v2">
          <div className="empty-emoji">🔒</div>
          <p>{t("common.notLoggedIn")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-v2 page-kawaii">
      <FloatingClouds />
      <ARIALiveRegion />

      <div className="page-header-v2">
        <div className="page-header-content-v2">
          <div className="page-eyebrow">
            <Sparkles size={14} />
            {t("profile.page.eyebrow")}
          </div>
          <h1 className="page-title-v2">
            <span className="title-emoji">👤</span>
            {t("profile.page.title")}
          </h1>
          <p className="page-description-v2">{t("profile.page.description")}</p>
        </div>
        <button
          className="refresh-btn kawaii-btn kawaii-btn-mint"
          onClick={refresh}
          disabled={status === "loading"}
        >
          {status === "loading" ? <Loader2 size={18} className="spin" /> : <RefreshCw size={18} />}
          {t("profile.refresh")}
        </button>
      </div>

      {/* 指标卡片 */}
      {!scorecard && status === "loading" ? (
        <div className="metrics-grid-v2">
          <SkeletonMetricCard />
          <SkeletonMetricCard />
          <SkeletonMetricCard />
        </div>
      ) : scorecard ? (
        <div className="metrics-grid-v2">
          <div className="metric-card-v2 metric-card-mint">
            <div className="metric-decoration">✨</div>
            <div className="metric-icon-wrapper">
              <CheckCircle size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">{t("profile.completed")}</p>
              <h3 className="metric-value-v2">{qualityPassedCount}</h3>
              <TrendIndicator current={qualityPassedCount} previous={previousQualityPassedCount} />
            </div>
          </div>
          <div className="metric-card-v2 metric-card-pink">
            <div className="metric-decoration">🌸</div>
            <div className="metric-icon-wrapper">
              <Crown size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">{t("profile.failed")}</p>
              <h3 className="metric-value-v2">{scorecard.failed_count}</h3>
            </div>
          </div>
          <div className="metric-card-v2 metric-card-lavender">
            <div className="metric-decoration">🎨</div>
            <div className="metric-icon-wrapper">
              <Palette size={20} />
            </div>
            <div className="metric-content">
              <p className="metric-label-v2">{t("profile.medianQuality")}</p>
              <h3 className="metric-value-v2">
                {scorecard.median_quality_score?.toFixed(1) ?? "—"}
              </h3>
              {scorecard.median_quality_score && (
                <span
                  className={`quality-badge ${
                    scorecard.median_quality_score >= 8
                      ? "excellent"
                      : scorecard.median_quality_score >= 6
                        ? "good"
                        : "needs-improvement"
                  }`}
                >
                  {scorecard.median_quality_score >= 8
                    ? "🌟 " + t("profile.qualityExcellent")
                    : scorecard.median_quality_score >= 6
                      ? "✨ " + t("profile.qualityGood")
                      : "💪 " + t("profile.qualityNeedsImprovement")}
                </span>
              )}
            </div>
          </div>
        </div>
      ) : null}

      <div className="content-grid-v2">
        {/* 左侧：当前画像 */}
        <div className="main-column">
          <div className="section-card-v2 section-card-glass">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <span className="title-icon">👤</span>
                {t("profile.currentProfile")}
              </h3>
              <div className="section-decoration">✨</div>
            </div>

            {profile && (
              <div className="profile-content">
                <div className="profile-header">
                  <div className="profile-avatar">
                    <span className="avatar-emoji">🌟</span>
                    {profile.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="profile-info">
                    <h4>{profile.name}</h4>
                    <div className="profile-meta">
                      <span className="profile-badge">
                        🏷️ {t("profile.version", { version: profile.profile_version })}
                      </span>
                      <span className={`profile-status ${profile.status}`}>
                        {profile.status === "active" ? "🟢" : "⚪"}{" "}
                        {getStatusLabel(profile.status, locale)}
                      </span>
                      {runtimeStatus && (
                        <span className="profile-badge">
                          🧭 Rollout: {runtimeStatus.capabilities.rollout_profile}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {runtimeStatus && (
                  <div className="profile-json">
                    <label>
                      <span className="label-icon">🛡️</span>
                      Runtime Diagnostics
                    </label>
                    <div className="memory-meta">
                      <span>Provider: {runtimeStatus.provider.mode}</span>
                      <span>
                        MathTeX:{" "}
                        {runtimeStatus.features.mathtex?.available ? "available" : "missing"}
                      </span>
                    </div>
                    {runtimeStatus.autonomy_guard?.enabled ? (
                      <div className="memory-meta">
                        <span>
                          Guarded autonomy:{" "}
                          {runtimeStatus.autonomy_guard.allowed ? "allowed" : "blocked"}
                        </span>
                        {runtimeStatus.autonomy_guard.reasons.length ? (
                          <span>{runtimeStatus.autonomy_guard.reasons.join(", ")}</span>
                        ) : null}
                      </div>
                    ) : null}
                    {runtimeStatus.delivery_summary ? (
                      <>
                        <div className="memory-meta">
                          <span>
                            Delivery rate:{" "}
                            {(runtimeStatus.delivery_summary.delivery_rate * 100).toFixed(0)}%
                          </span>
                          <span>
                            Cases:{" "}
                            {formatCountSummary(runtimeStatus.delivery_summary.case_status_counts)}
                          </span>
                        </div>
                        <div className="memory-meta">
                          <span>
                            Agent runs:{" "}
                            {formatCountSummary(
                              runtimeStatus.delivery_summary.agent_run_status_counts
                            )}
                          </span>
                          <span>
                            Agent roles:{" "}
                            {formatRoleStatusSummary(
                              runtimeStatus.delivery_summary.agent_run_role_status_counts
                            )}
                          </span>
                        </div>
                        <div className="memory-meta">
                          <span>
                            Agent stop reasons:{" "}
                            {formatCountSummary(
                              runtimeStatus.delivery_summary.agent_run_stop_reason_counts
                            )}
                          </span>
                        </div>
                        <div className="memory-meta">
                          <span>
                            Completion modes:{" "}
                            {formatCountSummary(runtimeStatus.delivery_summary.completion_modes)}
                          </span>
                        </div>
                        <div className="memory-meta">
                          <span>
                            Arbitration success:{" "}
                            {(
                              runtimeStatus.delivery_summary.arbitration_success_rate * 100
                            ).toFixed(0)}
                            %
                          </span>
                        </div>
                      </>
                    ) : null}
                    <ul>
                      {Object.entries(runtimeStatus.capabilities.effective).map(
                        ([key, enabled]) => (
                          <li key={key}>
                            {formatCapabilityLabel(key)}: {enabled ? "enabled" : "disabled"}
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                )}

                {scorecard && (
                  <div className="profile-json">
                    <label>
                      <span className="label-icon">📉</span>
                      Top Issue Codes
                    </label>
                    {scorecard.top_issue_codes.length ? (
                      <ul>
                        {scorecard.top_issue_codes.map((item) => (
                          <li key={item.code}>
                            {item.code} ({item.count})
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p>No recent issue pressure.</p>
                    )}
                  </div>
                )}

                <div className="profile-json">
                  <label>
                    <span className="label-icon">🧪</span>
                    Suggestion Diagnostics
                  </label>
                  {suggestions.length ? (
                    <div className="memory-list">
                      {suggestions.slice(0, 3).map((suggestion) => (
                        <div key={suggestion.suggestion_id} className="memory-item">
                          <div className="memory-item-header">
                            <span className="memory-id">{suggestion.suggestion_id}</span>
                            <span className={`memory-status ${suggestion.status.toLowerCase()}`}>
                              {suggestion.status}
                            </span>
                          </div>
                          <p className="memory-text">
                            Confidence {Number(suggestion.rationale.confidence ?? 0).toFixed(2)}
                          </p>
                          <div className="memory-meta">
                            <span>
                              Evidence:{" "}
                              {formatSupportSummary(
                                suggestion.rationale.supporting_evidence_counts
                              )}
                            </span>
                            {suggestion.rationale.conflicts?.length ? (
                              <span>
                                Conflicts:{" "}
                                {suggestion.rationale.conflicts
                                  .map((item) => item.field)
                                  .join(", ")}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p>No pending profile suggestions.</p>
                  )}
                </div>

                <div className="profile-json">
                  <label>
                    <span className="label-icon">🧭</span>
                    Strategy Routing
                  </label>
                  {strategies.length ? (
                    <div className="memory-list">
                      {strategies.slice(0, 4).map((strategy) => {
                        const guardedRollout = strategy.guarded_rollout ?? {};
                        const lastEvalRun = strategy.last_eval_run ?? {};
                        const shadowPasses = Number(
                          guardedRollout["consecutive_shadow_passes"] ?? 0
                        );
                        const rollbackArmed = Boolean(guardedRollout["rollback_armed"] ?? false);
                        const promotionMode = String(lastEvalRun["promotion_mode"] ?? "shadow");
                        return (
                          <div key={strategy.strategy_id} className="memory-item">
                            <div className="memory-item-header">
                              <span className="memory-id">{strategy.strategy_id}</span>
                              <span className={`memory-status ${strategy.status.toLowerCase()}`}>
                                {strategy.status}
                              </span>
                            </div>
                            <p className="memory-text">
                              Cluster: {strategy.prompt_cluster ?? "global"} | Mode: {promotionMode}
                            </p>
                            <div className="memory-meta">
                              <span>
                                Routing keywords:{" "}
                                {strategy.routing_keywords.length
                                  ? strategy.routing_keywords.join(", ")
                                  : "none"}
                              </span>
                              <span>Shadow passes: {shadowPasses}</span>
                              <span>Rollback armed: {rollbackArmed ? "yes" : "no"}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p>No strategy routing profiles configured.</p>
                  )}
                </div>

                <div className="profile-json">
                  <label>
                    <span className="label-icon">📋</span>
                    {t("profile.jsonLabel")}
                  </label>
                  <pre>{JSON.stringify(profile.profile_json, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 右侧：编辑区 */}
        <div className="side-column">
          <div className="section-card-v2 section-card-glass">
            <div className="section-header-v2">
              <h3 className="section-title-v2">
                <span className="title-icon">⚙️</span>
                {t("profile.applyPatch")}
              </h3>
              {/* 编辑器模式切换 */}
              <div className="editor-mode-toggle">
                <button
                  type="button"
                  className={editorMode === "visual" ? "active" : ""}
                  onClick={() => setEditorMode("visual")}
                >
                  <Palette size={14} />
                  {t("profile.visualMode")}
                </button>
                <button
                  type="button"
                  className={editorMode === "json" ? "active" : ""}
                  onClick={() => setEditorMode("json")}
                >
                  <Code size={14} />
                  {t("profile.jsonMode")}
                </button>
              </div>
            </div>

            <div className="patch-form">
              {editorMode === "visual" ? (
                <VisualEditor data={formData} onChange={setFormData} />
              ) : (
                <>
                  {/* JSON 示例折叠面板 */}
                  <details
                    className="json-example-panel"
                    open={showExample}
                    onToggle={(e) => setShowExample(e.currentTarget.open)}
                  >
                    <summary className="json-example-summary">
                      <ChevronDown
                        size={16}
                        className={`json-example-icon ${showExample ? "open" : ""}`}
                      />
                      <span className="summary-emoji">📖</span>
                      {t("profile.showJsonExample")}
                    </summary>
                    <pre className="json-example-code">{jsonExample}</pre>
                  </details>

                  <div className="textarea-wrapper">
                    <textarea
                      className={`form-textarea-v2 code ${jsonError ? "error" : ""}`}
                      value={patchText}
                      onChange={(e) => setPatchText(e.target.value)}
                      rows={10}
                      spellCheck={false}
                      aria-invalid={!!jsonError}
                      aria-describedby={jsonError ? "json-error" : undefined}
                    />
                    <div className="textarea-decoration">✨</div>
                  </div>

                  {jsonError && (
                    <div id="json-error" className="form-error-v2" role="alert">
                      <AlertCircle size={16} />
                      {jsonError}
                    </div>
                  )}
                </>
              )}

              <button
                className="submit-btn-v2 kawaii-btn kawaii-btn-pink"
                onClick={onApply}
                disabled={applyState !== "idle" || (editorMode === "json" && !!jsonError)}
                aria-busy={applyState === "applying"}
              >
                {applyState === "applying" ? (
                  <>
                    <Loader2 size={18} className="spin" /> {t("profile.applying")}
                  </>
                ) : (
                  <>
                    <Save size={18} /> ✨ {t("profile.applyAction")}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 🔐 认证弹窗 */}
      {showAuthModal && <AuthModal forceShow onClose={closeAuthModal} />}
    </div>
  );
}
