/**
 * KawaiiDecorations - 全局二次元装饰组件
 * 提供云朵、星星、花瓣等装饰元素
 */

import { Cloud, Star, Sparkles } from "lucide-react";
import "./KawaiiDecorations.css";

// ☁️ 浮动云朵
export function FloatingClouds() {
  return (
    <div className="floating-clouds" aria-hidden="true">
      <div className="cloud cloud-1">
        <Cloud size={80} strokeWidth={1} />
      </div>
      <div className="cloud cloud-2">
        <Cloud size={60} strokeWidth={1} />
      </div>
      <div className="cloud cloud-3">
        <Cloud size={100} strokeWidth={1} />
      </div>
      <div className="cloud cloud-4">
        <Cloud size={50} strokeWidth={1} />
      </div>
      <div className="cloud cloud-5">
        <Cloud size={70} strokeWidth={1} />
      </div>
    </div>
  );
}

// ⭐ 闪烁星星
export function TwinklingStars() {
  return (
    <div className="twinkling-stars" aria-hidden="true">
      <div className="star star-1">
        <Star size={16} fill="#FFD700" color="#FFD700" />
      </div>
      <div className="star star-2">
        <Star size={12} fill="#FF6B8A" color="#FF6B8A" />
      </div>
      <div className="star star-3">
        <Star size={20} fill="#A8E6CF" color="#A8E6CF" />
      </div>
      <div className="star star-4">
        <Star size={14} fill="#DDA0DD" color="#DDA0DD" />
      </div>
      <div className="star star-5">
        <Star size={18} fill="#FFCBA4" color="#FFCBA4" />
      </div>
      <div className="star star-6">
        <Star size={10} fill="#FFD700" color="#FFD700" />
      </div>
      <div className="star star-7">
        <Sparkles size={16} color="#FFD700" />
      </div>
      <div className="star star-8">
        <Sparkles size={14} color="#FF6B8A" />
      </div>
    </div>
  );
}

// 🌸 飘落花瓣
export function FallingPetals() {
  return (
    <div className="falling-petals" aria-hidden="true">
      <span className="petal petal-1">🌸</span>
      <span className="petal petal-2">🌺</span>
      <span className="petal petal-3">🌸</span>
      <span className="petal petal-4">💮</span>
      <span className="petal petal-5">🌸</span>
      <span className="petal petal-6">🌼</span>
    </div>
  );
}

// 🎈 装饰性气泡
export function FloatingBubbles() {
  return (
    <div className="floating-bubbles" aria-hidden="true">
      <div className="bubble bubble-1" />
      <div className="bubble bubble-2" />
      <div className="bubble bubble-3" />
      <div className="bubble bubble-4" />
      <div className="bubble bubble-5" />
    </div>
  );
}

// 🌈 渐变背景装饰
export function GradientOrbs() {
  return (
    <div className="gradient-orbs" aria-hidden="true">
      <div className="orb orb-pink" />
      <div className="orb orb-mint" />
      <div className="orb orb-sky" />
      <div className="orb orb-lavender" />
    </div>
  );
}

// 🎀 完整的 Kawaii 背景装饰
export function KawaiiBackground() {
  return (
    <>
      <GradientOrbs />
      <FloatingClouds />
      <TwinklingStars />
    </>
  );
}

// 🎨 页面装饰包装器
interface KawaiiPageWrapperProps {
  children: React.ReactNode;
  showClouds?: boolean;
  showStars?: boolean;
  showPetals?: boolean;
  showBubbles?: boolean;
  className?: string;
}

export function KawaiiPageWrapper({
  children,
  showClouds = true,
  showStars = true,
  showPetals = false,
  showBubbles = false,
  className = "",
}: KawaiiPageWrapperProps) {
  return (
    <div className={`kawaii-page-wrapper ${className}`}>
      {showClouds && <FloatingClouds />}
      {showStars && <TwinklingStars />}
      {showPetals && <FallingPetals />}
      {showBubbles && <FloatingBubbles />}
      {children}
    </div>
  );
}
