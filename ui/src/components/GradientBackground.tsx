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

interface ColorScheme {
  gradients: [string, string, string];
  staticColors: [string, string, string];
}

// 预定义的渐变配色方案（使用设计系统语义 token）
const colorSchemes: Record<string, ColorScheme> = {
  // 梦幻森林 - 绿紫粉
  dreamy: {
    gradients: [
      "linear-gradient(135deg, var(--color-mint-400) 0%, var(--color-mint-500) 50%, var(--color-mint-300) 100%)",
      "linear-gradient(135deg, var(--color-lavender-400) 0%, var(--color-lavender-500) 50%, var(--color-lavender-300) 100%)",
      "linear-gradient(135deg, var(--color-pink-300) 0%, var(--color-pink-500) 50%, var(--color-pink-400) 100%)",
    ],
    staticColors: ["var(--color-mint-400)", "var(--color-lavender-400)", "var(--color-pink-400)"],
  },
  // 日落海滩 - 橙黄红
  sunset: {
    gradients: [
      "linear-gradient(135deg, var(--color-peach-400) 0%, var(--color-peach-500) 50%, var(--color-peach-300) 100%)",
      "linear-gradient(135deg, var(--color-lemon-400) 0%, var(--color-lemon-500) 50%, var(--color-peach-400) 100%)",
      "linear-gradient(135deg, var(--color-pink-400) 0%, var(--color-pink-500) 50%, var(--color-peach-500) 100%)",
    ],
    staticColors: ["var(--color-peach-400)", "var(--color-lemon-400)", "var(--color-pink-400)"],
  },
  // 海洋天空 - 蓝青紫
  ocean: {
    gradients: [
      "linear-gradient(135deg, var(--color-sky-400) 0%, var(--color-sky-500) 50%, var(--color-sky-300) 100%)",
      "linear-gradient(135deg, var(--color-mint-400) 0%, var(--color-sky-500) 50%, var(--color-sky-400) 100%)",
      "linear-gradient(135deg, var(--color-lavender-400) 0%, var(--color-lavender-500) 50%, var(--color-lavender-300) 100%)",
    ],
    staticColors: ["var(--color-sky-400)", "var(--color-mint-400)", "var(--color-lavender-400)"],
  },
  // 极简黑白 - 灰白银
  minimal: {
    gradients: [
      "linear-gradient(135deg, var(--color-cloud-300) 0%, var(--color-cloud-400) 50%, var(--color-cloud-200) 100%)",
      "linear-gradient(135deg, var(--color-cloud-500) 0%, var(--color-cloud-600) 50%, var(--color-cloud-300) 100%)",
      "linear-gradient(135deg, var(--color-cloud-200) 0%, var(--color-cloud-50) 50%, var(--color-cloud-100) 100%)",
    ],
    staticColors: ["var(--color-cloud-300)", "var(--color-cloud-500)", "var(--color-cloud-200)"],
  },
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
    const colors = colorSchemes[scheme].gradients;
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
    const [primaryColor, secondaryColor, tertiaryColor] = colorSchemes[scheme].staticColors;

    // 减少动画模式：静态渐变
    return (
      <div
        className="gradient-background-static"
        aria-hidden="true"
        style={{
          background: `radial-gradient(ellipse at 20% 30%, ${primaryColor} 0%, transparent 50%),
                       radial-gradient(ellipse at 80% 70%, ${secondaryColor} 0%, transparent 50%),
                       radial-gradient(ellipse at 50% 50%, ${tertiaryColor} 0%, transparent 70%)`,
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
