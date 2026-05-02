import { useState } from "react";
import { useAsyncStatus } from "../../hooks/useAsyncStatus";
import { useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
import { postSession } from "../../lib/api";
import { writeSessionToken } from "../../lib/session";
import { useI18n } from "../../app/locale";
import { LocaleToggle } from "../../components/LocaleToggle";
import { KawaiiIcon, EmojiIcon } from "../../components";
import { cn } from "../../lib/utils";

function CloudDecorations() {
  return (
    <>
      <div className="cloud-decoration cloud-1">
        <EmojiIcon emoji="☁️" color="pink" size="lg" />
      </div>
      <div className="cloud-decoration cloud-2">
        <EmojiIcon emoji="☁️" color="mint" size="md" />
      </div>
      <div className="cloud-decoration cloud-3">
        <EmojiIcon emoji="☁️" color="sky" size="xl" />
      </div>
      <div className="cloud-decoration cloud-4">
        <EmojiIcon emoji="☁️" color="lavender" size="sm" />
      </div>
    </>
  );
}

function StarDecorations() {
  return (
    <>
      <div className="star-decoration star-1">
        <EmojiIcon emoji="⭐" color="lemon" size="sm" />
      </div>
      <div className="star-decoration star-2">
        <EmojiIcon emoji="✨" color="pink" size="xs" />
      </div>
      <div className="star-decoration star-3">
        <EmojiIcon emoji="🌟" color="mint" size="md" />
      </div>
      <div className="star-decoration star-4">
        <EmojiIcon emoji="✨" color="lavender" size="sm" />
      </div>
      <div className="star-decoration star-5">
        <EmojiIcon emoji="⭐" color="peach" size="xs" />
      </div>
    </>
  );
}

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
    <div
      className="login-page relative flex min-h-screen items-center justify-center overflow-x-hidden overflow-y-auto px-4 py-8"
      style={{ background: "var(--gradient-page-login)" }}
    >
      {/* Background orbs */}
      <div
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          animationDuration: "20s",
          background:
            "radial-gradient(circle at 20% 30%, rgba(255,160,181,0.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(127,212,182,0.4) 0%, transparent 40%), radial-gradient(circle at 50% 50%, rgba(90,180,209,0.3) 0%, transparent 50%)",
        }}
      />

      <CloudDecorations />
      <StarDecorations />
      <PetalDecorations />

      <div className="absolute right-5 top-5 z-20">
        <LocaleToggle />
      </div>

      <div className="relative z-10 grid w-full max-w-6xl grid-cols-1 gap-8 p-4 lg:grid-cols-[1fr_minmax(0,26rem)] lg:gap-16 lg:p-8">
        {/* Left brand */}
        <div className="relative flex flex-col justify-center lg:p-10">
          <div className="relative z-10 text-center lg:text-left">
            <div className="mx-auto mb-6 flex items-center justify-center lg:mx-0 lg:mb-8">
              <KawaiiIcon icon={Sparkles} color="gradient" size="xl" />
            </div>
            <h1 className="mb-4 text-4xl font-extrabold tracking-tight text-pink-500 dark:text-pink-400 lg:text-6xl">
              easy-manim
            </h1>
            <p className="mb-8 text-lg font-medium text-cloud-700 dark:text-cloud-200 lg:text-xl">
              {t("login.brand.tagline")}
            </p>
            <div className="flex flex-col items-center gap-3 lg:items-start">
              <div className="flex w-fit items-center gap-3 rounded-xl border border-cloud-200 bg-cloud-50 px-3 py-2 text-sm text-cloud-700 dark:border-cloud-800 dark:bg-cloud-900/60 dark:text-cloud-300">
                <EmojiIcon emoji="🎨" color="mint" size="sm" />
                <span>{t("login.brand.workflow")}</span>
              </div>
              <div className="flex w-fit items-center gap-3 rounded-xl border border-cloud-200 bg-cloud-50 px-3 py-2 text-sm text-cloud-700 dark:border-cloud-800 dark:bg-cloud-900/60 dark:text-cloud-300">
                <EmojiIcon emoji="🛡️" color="sky" size="sm" />
                <span>{t("login.brand.localFirst")}</span>
              </div>
            </div>
          </div>

          {/* Decorative rings */}
          <div className="pointer-events-none absolute left-1/2 top-1/2 hidden h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 lg:block">
            <div
              className="decoration-ring absolute inset-0 rounded-full border-2 border-transparent border-b-pink-200"
              style={{ animationDuration: "6s" }}
            />
            <div
              className="decoration-ring absolute inset-0 rounded-full border-2 border-transparent border-r-mint-200"
              style={{ animationDuration: "6s", animationDelay: "2s" }}
            />
            <div
              className="decoration-ring absolute inset-0 rounded-full border-2 border-transparent border-t-lavender-200"
              style={{ animationDuration: "6s", animationDelay: "4s" }}
            />
          </div>
        </div>

        {/* Right form */}
        <div className="flex items-center justify-center">
          <div className="w-full max-w-md rounded-[32px] border border-cloud-200 bg-white p-6 shadow-xl dark:border-cloud-800 dark:bg-cloud-900 sm:p-8">
            <div className="mb-8 text-center">
              <div className="mx-auto mb-4 flex items-center justify-center">
                <EmojiIcon emoji="🌟" color="peach" size="lg" />
              </div>
              <h2 className="mb-2 text-2xl font-bold text-cloud-800 dark:text-cloud-100">
                {t("login.welcome")}
              </h2>
              <p className="text-sm text-cloud-600 dark:text-cloud-400">{t("login.subtitle")}</p>
            </div>

            <form onSubmit={onSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <label
                  className="flex items-center gap-1 text-xs font-semibold text-cloud-700 dark:text-cloud-300"
                  htmlFor="token"
                >
                  <span>🌸</span>
                  {t("login.tokenLabel")}
                </label>
                <div className="relative">
                  <input
                    id="token"
                    type="text"
                    className={cn(
                      "w-full rounded-2xl border-2 border-transparent bg-cloud-100 px-4 py-3 text-sm text-cloud-800 outline-none transition-colors transition-shadow",
                      "placeholder:text-cloud-500",
                      "focus:border-pink-300 focus:bg-white focus:shadow-md dark:bg-cloud-800 dark:text-cloud-100"
                    )}
                    value={agentToken}
                    onChange={(e) => setAgentToken(e.target.value)}
                    placeholder={t("login.tokenPlaceholder")}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={status === "loading"}
                  />
                  <div className="pointer-events-none absolute -inset-[2px] -z-10 rounded-[18px] bg-gradient-to-br from-pink-300 to-mint-300 opacity-0 blur-[8px] transition-opacity duration-300 peer-focus:opacity-60" />
                </div>
                <p className="flex items-center gap-1 text-xs text-cloud-600 dark:text-cloud-400">
                  <span>💡</span>
                  {t("login.tokenHint")}
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-900/30 dark:bg-red-900/20 dark:text-red-400">
                  <span>⚠️</span>
                  {error}
                </div>
              )}

              <button
                type="submit"
                className={cn(
                  "group relative mt-2 flex items-center justify-center gap-2 overflow-hidden rounded-2xl px-6 py-3.5 text-base font-semibold text-white transition-transform transition-shadow transition-opacity",
                  "bg-gradient-to-r from-pink-400 to-peach-400 shadow-lg shadow-pink-200/40",
                  "hover:-translate-y-0.5 hover:shadow-xl hover:shadow-pink-200/50",
                  "disabled:cursor-not-allowed disabled:opacity-60 disabled:translate-y-0 disabled:shadow-none"
                )}
                disabled={status === "loading" || !agentToken.trim()}
              >
                <span className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/30 to-transparent transition-transform duration-700 group-hover:translate-x-full" />
                {status === "loading" ? (
                  <>
                    <span className="h-5 w-5 animate-spin rounded-full border-[3px] border-white/30 border-t-white" />
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

            <div className="mt-6 text-center">
              <p className="flex items-center justify-center gap-1 text-xs text-cloud-600 dark:text-cloud-400">
                <span>🌟</span>
                {t("login.footer")}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
