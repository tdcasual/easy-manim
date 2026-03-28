/**
 * GradientBackground - 渐变背景装饰组件
 * 二次元风格的柔和渐变背景，增强视觉层次
 */
import { useEffect, useState } from "react";
import "./GradientBackground.css";

interface OrbConfig {
  id: number;
  size: number;
  color: string;
  initialX: number;
  initialY: number;
  duration: number;
  delay: number;
}

// 预定义的渐变配色方案
const colorSchemes = {
  // 梦幻森林 - 绿紫粉
  dreamy: [
    "linear-gradient(135deg, #7cb342 0%, #4caf50 50%, #81c784 100%)",
    "linear-gradient(135deg, #e040fb 0%, #9c27b0 50%, #ce93d8 100%)",
    "linear-gradient(135deg, #ff80ab 0%, #f50057 50%, #ff4081 100%)",
  ],
  // 日落海滩 - 橙黄红
  sunset: [
    "linear-gradient(135deg, #ff9100 0%, #ff6d00 50%, #ffab40 100%)",
    "linear-gradient(135deg, #ffeb3b 0%, #ffc107 50%, #ff9800 100%)",
    "linear-gradient(135deg, #f44336 0%, #e91e63 50%, #ff5722 100%)",
  ],
  // 海洋天空 - 蓝青紫
  ocean: [
    "linear-gradient(135deg, #448aff 0%, #2979ff 50%, #82b1ff 100%)",
    "linear-gradient(135deg, #00bcd4 0%, #0097a7 50%, #4dd0e1 100%)",
    "linear-gradient(135deg, #7c4dff 0%, #651fff 50%, #b388ff 100%)",
  ],
  // 极简黑白 - 灰白银
  minimal: [
    "linear-gradient(135deg, #e0e0e0 0%, #bdbdbd 50%, #f5f5f5 100%)",
    "linear-gradient(135deg, #9e9e9e 0%, #757575 50%, #e0e0e0 100%)",
    "linear-gradient(135deg, #f5f5f5 0%, #ffffff 50%, #eeeeee 100%)",
  ],
};

interface GradientBackgroundProps {
  scheme?: keyof typeof colorSchemes;
  intensity?: "low" | "medium" | "high";
  animated?: boolean;
  orbCount?: number;
}

export function GradientBackground({
  scheme = "dreamy",
  intensity = "medium",
  animated = true,
  orbCount = 3,
}: GradientBackgroundProps) {
  const [orbs, setOrbs] = useState<OrbConfig[]>([]);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // 检测用户是否偏好减少动画
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // 生成随机渐变球体配置
  useEffect(() => {
    const colors = colorSchemes[scheme];
    const newOrbs: OrbConfig[] = [];

    for (let i = 0; i < orbCount; i++) {
      newOrbs.push({
        id: i,
        size: 300 + Math.random() * 400,
        color: colors[i % colors.length],
        initialX: Math.random() * 100,
        initialY: Math.random() * 100,
        duration: 15 + Math.random() * 10,
        delay: i * -5,
      });
    }

    setOrbs(newOrbs);
  }, [scheme, orbCount]);

  // 根据强度调整透明度
  const opacityMap = {
    low: 0.08,
    medium: 0.15,
    high: 0.25,
  };

  const baseOpacity = opacityMap[intensity];

  if (prefersReducedMotion) {
    // 减少动画模式：静态渐变
    return (
      <div
        className="gradient-background-static"
        aria-hidden="true"
        style={{
          background: `radial-gradient(ellipse at 20% 30%, ${colorSchemes[scheme][0]} 0%, transparent 50%),
                       radial-gradient(ellipse at 80% 70%, ${colorSchemes[scheme][1]} 0%, transparent 50%),
                       radial-gradient(ellipse at 50% 50%, ${colorSchemes[scheme][2]} 0%, transparent 70%)`,
          opacity: baseOpacity,
        }}
      />
    );
  }

  return (
    <div className="gradient-background" aria-hidden="true">
      {orbs.map((orb) => (
        <div
          key={orb.id}
          className={`gradient-orb ${animated ? "animated" : ""}`}
          style={{
            width: orb.size,
            height: orb.size,
            background: orb.color,
            left: `${orb.initialX}%`,
            top: `${orb.initialY}%`,
            opacity: baseOpacity,
            animationDuration: `${orb.duration}s`,
            animationDelay: `${orb.delay}s`,
          }}
        />
      ))}
      {/* 噪点纹理叠加 */}
      <div className="noise-overlay" />
    </div>
  );
}

// 页面特定的渐变背景预设
export function DreamyBackground() {
  return <GradientBackground scheme="dreamy" intensity="medium" />;
}

export function SunsetBackground() {
  return <GradientBackground scheme="sunset" intensity="medium" />;
}

export function OceanBackground() {
  return <GradientBackground scheme="ocean" intensity="low" />;
}

export function MinimalBackground() {
  return <GradientBackground scheme="minimal" intensity="low" />;
}
