import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { postSession } from "../../lib/api";
import { writeSessionToken } from "../../lib/session";

const LOGIN_STEPS = [
  "在管理员 CLI 或 Docker Compose 部署里签发一个 Agent Token。",
  "把 Token 粘贴到这里，换取当前浏览器里的工作会话。",
  "进入任务、视频回看、记忆、画像与评测，不必重复登录。"
] as const;

export function LoginPage() {
  const [agentToken, setAgentToken] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setStatus("loading");
    setError(null);
    try {
      const created = await postSession(agentToken.trim());
      writeSessionToken(created.session_token);
      setStatus("idle");
      navigate("/tasks", { replace: true });
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "login_failed");
    }
  }

  return (
    <div className="loginShell">
      <div className="loginBackdrop" aria-hidden="true" />
      <div className="loginLayout">
        <section className="loginShowcase">
          <p className="pageEyebrow">控制台入口</p>
          <h1>easy-manim console</h1>
          <h2>登录工作台</h2>
          <p className="loginLead">
            面向中文创作与运营场景的智能体视频控制台。使用一次 Agent Token 建立会话，然后在同一工作上下文里持续创建、
            回看、修订与评估视频结果。
          </p>

          <div className="loginStatement">
            <span className="loginStatementLabel">这个控制台能做什么</span>
            <p>创建视频任务，直接回看最近生成的视频，排查失败原因，沉淀有效记忆，并调整画像来指导后续生成。</p>
          </div>

          <ol className="loginSteps">
            {LOGIN_STEPS.map((step, index) => (
              <li key={step}>
                <span className="loginStepIndex">{String(index + 1).padStart(2, "0")}</span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="loginPanel">
          <div className="loginPanelHeader">
            <span className="pill">需要工作会话</span>
            <p className="muted">输入已签发的 Agent Token，开始当前浏览器中的专属会话。</p>
          </div>

          <form onSubmit={onSubmit} aria-label="login form" className="stackForm">
            <label className="field">
              <span className="fieldLabel">Agent Token</span>
              <input
                aria-label="Agent token"
                className="input input--hero"
                value={agentToken}
                onChange={(event) => setAgentToken(event.target.value)}
                placeholder="easy-manim.agent-a.…"
                autoComplete="off"
                spellCheck={false}
              />
            </label>

            <div className="buttonRow buttonRow--stacked">
              <button
                className="button buttonPrimary buttonWide"
                type="submit"
                disabled={status === "loading" || agentToken.trim().length === 0}
              >
                {status === "loading" ? "正在登录…" : "登录"}
              </button>
              <p className="muted small">明文 Token 仅用于换取 Session Token，不会保存在前端页面中。</p>
            </div>

            {error ? (
              <p role="alert" className="alert">
                {error}
              </p>
            ) : null}
          </form>
        </section>
      </div>
    </div>
  );
}
