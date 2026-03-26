import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, Command, ArrowRight, Shield } from "lucide-react";
import { postSession } from "../../lib/api";
import { writeSessionToken } from "../../lib/session";
import "./LoginPage.css";

// 背景粒子组件
function ParticleBackground() {
  useEffect(() => {
    // 检查用户是否偏好减少动画
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return; // 如果用户偏好减少动画，不启动粒子效果
    
    const canvas = document.getElementById('particle-canvas') as HTMLCanvasElement;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);
    
    const particles: Array<{
      x: number;
      y: number;
      vx: number;
      vy: number;
      radius: number;
      opacity: number;
    }> = [];
    
    // 创建粒子（减少数量以优化性能）
    const particleCount = window.matchMedia('(pointer: coarse)').matches ? 20 : 35;
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        radius: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.4 + 0.2
      });
    }
    
    let animationId: number;
    let isVisible = true;
    let frameCount = 0;
    
    // 使用 Page Visibility API 优化性能
    const handleVisibility = () => {
      isVisible = document.visibilityState === 'visible';
    };
    document.addEventListener('visibilitychange', handleVisibility);
    
    const animate = () => {
      // 页面不可见时跳过渲染
      if (!isVisible) {
        animationId = requestAnimationFrame(animate);
        return;
      }
      
      // 每 2 帧渲染一次以优化性能（30fps）
      frameCount++;
      if (frameCount % 2 !== 0) {
        animationId = requestAnimationFrame(animate);
        return;
      }
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // 批量绘制粒子
      ctx.fillStyle = 'rgba(0, 212, 255, 0.4)';
      particles.forEach((particle) => {
        particle.x += particle.vx;
        particle.y += particle.vy;
        
        // 边界反弹
        if (particle.x < 0 || particle.x > canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > canvas.height) particle.vy *= -1;
        
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        ctx.fill();
      });
      
      // 绘制连线（限制每个粒子的连接数以优化性能）
      ctx.lineWidth = 0.5;
      particles.forEach((particle, i) => {
        let connections = 0;
        const maxConnections = 3;
        
        for (let j = i + 1; j < particles.length && connections < maxConnections; j++) {
          const other = particles[j];
          const dx = particle.x - other.x;
          const dy = particle.y - other.y;
          const distanceSq = dx * dx + dy * dy;
          
          // 使用平方距离避免开方运算
          if (distanceSq < 22500) { // 150^2
            const distance = Math.sqrt(distanceSq);
            ctx.beginPath();
            ctx.moveTo(particle.x, particle.y);
            ctx.lineTo(other.x, other.y);
            ctx.strokeStyle = `rgba(0, 212, 255, ${0.1 * (1 - distance / 150)})`;
            ctx.stroke();
            connections++;
          }
        }
      });
      
      animationId = requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => {
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', handleVisibility);
      cancelAnimationFrame(animationId);
    };
  }, []);
  
  return (
    <canvas 
      id="particle-canvas" 
      className="particle-canvas"
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 0
      }}
    />
  );
}

export function LoginPageV2() {
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
      setError(err instanceof Error ? err.message : "登录失败");
    }
  }
  
  return (
    <div className="login-page">
      <ParticleBackground />
      
      {/* Aurora 背景 */}
      <div className="login-aurora" />
      
      {/* 主内容 */}
      <div className="login-container">
        {/* 左侧品牌区 */}
        <div className="login-brand">
          <div className="brand-content">
            <div className="brand-logo-large">
              <Sparkles size={48} />
            </div>
            <h1 className="brand-title-large">
              easy-manim
            </h1>
            <p className="brand-tagline">
              AI 驱动的数学动画创作平台
            </p>
            <div className="brand-features">
              <div className="feature-item">
                <Command size={18} />
                <span>智能体工作流</span>
              </div>
              <div className="feature-item">
                <Shield size={18} />
                <span>本地优先架构</span>
              </div>
            </div>
          </div>
          
          {/* 装饰性元素 */}
          <div className="brand-decoration">
            <div className="decoration-ring" />
            <div className="decoration-ring" style={{ animationDelay: '2s' }} />
            <div className="decoration-ring" style={{ animationDelay: '4s' }} />
          </div>
        </div>
        
        {/* 右侧登录表单 */}
        <div className="login-form-wrapper">
          <div className="login-form-card">
            <div className="form-header">
              <div className="form-icon">
                <Command size={24} />
              </div>
              <h2 className="form-title">欢迎回来</h2>
              <p className="form-subtitle">
                使用 Agent Token 登录以继续
              </p>
            </div>
            
            <form onSubmit={onSubmit} className="login-form">
              <div className="form-field">
                <label className="form-label" htmlFor="token">
                  Agent Token
                </label>
                <div className="input-wrapper">
                  <input
                    id="token"
                    type="text"
                    className="form-input"
                    value={agentToken}
                    onChange={(e) => setAgentToken(e.target.value)}
                    placeholder="输入您的 Agent Token..."
                    autoComplete="off"
                    spellCheck={false}
                    disabled={status === "loading"}
                  />
                  <div className="input-glow" />
                </div>
                <p className="form-hint">
                  在管理员 CLI 中执行 issue-token 命令获取
                </p>
              </div>
              
              {error && (
                <div className="form-error animate-slide-up">
                  {error}
                </div>
              )}
              
              <button
                type="submit"
                className="submit-btn"
                disabled={status === "loading" || !agentToken.trim()}
              >
                {status === "loading" ? (
                  <>
                    <span className="spinner" />
                    登录中...
                  </>
                ) : (
                  <>
                    登录
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>
            
            <div className="form-footer">
              <p>
                easy-manim console v2.0
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
