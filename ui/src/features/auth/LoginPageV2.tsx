import { useState } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
import { postSession } from "../../lib/api";
import { writeSessionToken } from "../../lib/session";
import { useI18n } from "../../app/locale";
import { LocaleToggle } from "../../components/LocaleToggle";
import { KawaiiIcon, EmojiIcon } from "../../components";
import "./LoginPage.css";

// ☁️ 云朵装饰组件
function CloudDecorations() {
  return (
    <>
      <div className="cloud-decoration cloud-1">
        <EmojiIcon emoji="☁️" color="pink" size="lg" bounce />
      </div>
      <div className="cloud-decoration cloud-2">
        <EmojiIcon emoji="☁️" color="mint" size="md" bounce />
      </div>
      <div className="cloud-decoration cloud-3">
        <EmojiIcon emoji="☁️" color="sky" size="xl" bounce />
      </div>
      <div className="cloud-decoration cloud-4">
        <EmojiIcon emoji="☁️" color="lavender" size="sm" bounce />
      </div>
    </>
  );
}

// ✨ 星星装饰组件
function StarDecorations() {
  return (
    <>
      <div className="star-decoration star-1">
        <EmojiIcon emoji="⭐" color="lemon" size="sm" pulse />
      </div>
      <div className="star-decoration star-2">
        <EmojiIcon emoji="✨" color="pink" size="xs" pulse />
      </div>
      <div className="star-decoration star-3">
        <EmojiIcon emoji="🌟" color="mint" size="md" pulse />
      </div>
      <div className="star-decoration star-4">
        <EmojiIcon emoji="✨" color="lavender" size="sm" pulse />
      </div>
      <div className="star-decoration star-5">
        <EmojiIcon emoji="⭐" color="peach" size="xs" pulse />
      </div>
    </>
  );
}

// 🌸 花瓣飘落组件
function PetalDecorations() {
  return (
    <>
      <div className="petal">🌸</div>
      <div className="petal">🌺</div>
      <div className="petal">🌸</div>
      <div className="petal">💮</div>
      <div className="petal">🌸</div>
    </>
  );
}

export function LoginPageV2() {
  const [agentToken, setAgentToken] = useState("");
  const { status, error, startLoading, setErrorState, succeed } = useAsyncStatus();
  const navigate = useNavigate();
  const { t } = useI18n();

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    startLoading();

    try {
      const created = await postSession(agentToken.trim());
      writeSessionToken(created.session_token);
      succeed();
      navigate("/tasks", { replace: true });
    } catch (err) {
      setErrorState(err instanceof Error ? err.message : t("login.errorFallback"));
    }
  }

  return (
    <div className="login-page">
      {/* 装饰元素 */}
      <CloudDecorations />
      <StarDecorations />
      <PetalDecorations />

      {/* 工具栏 */}
      <div className="login-page-toolbar">
        <LocaleToggle />
      </div>

      {/* 主内容 */}
      <div className="login-container">
        {/* 左侧品牌区 */}
        <div className="login-brand">
          <div className="brand-content">
            <div className="brand-logo-large">
              <KawaiiIcon icon={Sparkles} color="gradient" size="xl" pulse />
            </div>
            <h1 className="brand-title-large">easy-manim</h1>
            <p className="brand-tagline">{t("login.brand.tagline")}</p>
            <div className="brand-features">
              <div className="feature-item">
                <EmojiIcon emoji="🎨" color="mint" size="sm" />
                <span>{t("login.brand.workflow")}</span>
              </div>
              <div className="feature-item">
                <EmojiIcon emoji="🛡️" color="sky" size="sm" />
                <span>{t("login.brand.localFirst")}</span>
              </div>
            </div>
          </div>

          {/* 装饰性元素 */}
          <div className="brand-decoration">
            <div className="decoration-ring" />
            <div className="decoration-ring" />
            <div className="decoration-ring" />
          </div>
        </div>

        {/* 右侧登录表单 */}
        <div className="login-form-wrapper">
          <div className="login-form-card">
            <div className="form-header">
              <div className="form-icon">
                <EmojiIcon emoji="🌟" color="peach" size="lg" bounce />
              </div>
              <h2 className="form-title">{t("login.welcome")}</h2>
              <p className="form-subtitle">{t("login.subtitle")}</p>
            </div>

            <form onSubmit={onSubmit} className="login-form">
              <div className="form-field">
                <label className="form-label" htmlFor="token">
                  {t("login.tokenLabel")}
                </label>
                <div className="input-wrapper">
                  <input
                    id="token"
                    type="text"
                    className="form-input"
                    value={agentToken}
                    onChange={(e) => setAgentToken(e.target.value)}
                    placeholder={t("login.tokenPlaceholder")}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={status === "loading"}
                  />
                  <div className="input-glow" />
                </div>
                <p className="form-hint">{t("login.tokenHint")}</p>
              </div>

              {error && <div className="form-error animate-slide-up">{error}</div>}

              <button
                type="submit"
                className="submit-btn"
                disabled={status === "loading" || !agentToken.trim()}
              >
                {status === "loading" ? (
                  <>
                    <span className="spinner" />
                    {t("login.loggingIn")}
                  </>
                ) : (
                  <>
                    {t("login.submit")}
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>

            <div className="form-footer">
              <p>{t("login.footer")}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
