/**
 * AnimatedContainer - 动画容器组件
 * 为子元素提供进入/退出动画效果
 */
import { useState, useEffect, useRef, type ReactNode } from "react";
import "./AnimatedContainer.css";

export type AnimationType =
  | "fade"
  | "slide-up"
  | "slide-down"
  | "slide-left"
  | "slide-right"
  | "scale"
  | "bounce"
  | "flip"
  | "rotate";

interface AnimatedContainerProps {
  children: ReactNode;
  animation?: AnimationType;
  delay?: number;
  duration?: number;
  className?: string;
  trigger?: "mount" | "in-view" | "manual";
  onAnimationEnd?: () => void;
}

export function AnimatedContainer({
  children,
  animation = "fade",
  delay = 0,
  duration = 500,
  className = "",
  trigger = "mount",
  onAnimationEnd,
}: AnimatedContainerProps) {
  const [isVisible, setIsVisible] = useState(trigger === "mount" ? false : true);
  const [hasAnimated, setHasAnimated] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (trigger === "mount") {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, delay);
      return () => clearTimeout(timer);
    }

    if (trigger === "in-view" && ref.current) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting && !hasAnimated) {
              setTimeout(() => {
                setIsVisible(true);
                setHasAnimated(true);
              }, delay);
            }
          });
        },
        { threshold: 0.1 }
      );

      observer.observe(ref.current);
      return () => observer.disconnect();
    }
  }, [trigger, delay, hasAnimated]);

  const handleAnimationEnd = () => {
    onAnimationEnd?.();
  };

  return (
    <div
      ref={ref}
      className={`animated-container ${animation} ${isVisible ? "visible" : ""} ${className}`}
      style={{
        animationDuration: `${duration}ms`,
        animationDelay: `${delay}ms`,
      }}
      onAnimationEnd={handleAnimationEnd}
    >
      {children}
    </div>
  );
}

// 交错动画列表
interface StaggeredListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => ReactNode;
  keyExtractor: (item: T, index: number) => string;
  animation?: AnimationType;
  staggerDelay?: number;
  className?: string;
}

export function StaggeredList<T>({
  items,
  renderItem,
  keyExtractor,
  animation = "slide-up",
  staggerDelay = 50,
  className = "",
}: StaggeredListProps<T>) {
  return (
    <div className={`staggered-list ${className}`}>
      {items.map((item, index) => (
        <AnimatedContainer
          key={keyExtractor(item, index)}
          animation={animation}
          delay={index * staggerDelay}
          trigger="in-view"
        >
          {renderItem(item, index)}
        </AnimatedContainer>
      ))}
    </div>
  );
}

// 页面过渡包装器
interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export function PageTransition({ children, className = "" }: PageTransitionProps) {
  return (
    <div className={`page-transition ${className}`}>
      <AnimatedContainer animation="fade" duration={300}>
        {children}
      </AnimatedContainer>
    </div>
  );
}

// 悬停动画包装器
interface HoverAnimationProps {
  children: ReactNode;
  scale?: number;
  rotate?: number;
  lift?: boolean;
  className?: string;
}

export function HoverAnimation({
  children,
  scale = 1.05,
  rotate = 0,
  lift = true,
  className = "",
}: HoverAnimationProps) {
  const style = {
    "--hover-scale": scale,
    "--hover-rotate": `${rotate}deg`,
    "--hover-lift": lift ? "-4px" : "0px",
  } as React.CSSProperties;

  return (
    <div className={`hover-animation ${className}`} style={style}>
      {children}
    </div>
  );
}

// 浮动动画装饰
interface FloatingElementProps {
  children: ReactNode;
  amplitude?: number;
  duration?: number;
  delay?: number;
  className?: string;
}

export function FloatingElement({
  children,
  amplitude = 10,
  duration = 3,
  delay = 0,
  className = "",
}: FloatingElementProps) {
  return (
    <div
      className={`floating-element ${className}`}
      style={
        {
          "--float-amplitude": `${amplitude}px`,
          "--float-duration": `${duration}s`,
          "--float-delay": `${delay}s`,
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  );
}

// 发光效果装饰
interface GlowEffectProps {
  children: ReactNode;
  color?: string;
  intensity?: "low" | "medium" | "high";
  pulse?: boolean;
  className?: string;
}

export function GlowEffect({
  children,
  color = "var(--accent-primary)",
  intensity = "medium",
  pulse = false,
  className = "",
}: GlowEffectProps) {
  const intensityMap = {
    low: "0.3",
    medium: "0.5",
    high: "0.8",
  };

  return (
    <div
      className={`glow-effect ${pulse ? "pulse" : ""} ${className}`}
      style={
        {
          "--glow-color": color,
          "--glow-intensity": intensityMap[intensity],
        } as React.CSSProperties
      }
    >
      {children}
    </div>
  );
}

// 闪光效果
interface SparkleProps {
  children: ReactNode;
  active?: boolean;
  className?: string;
}

export function Sparkle({ children, active = true, className = "" }: SparkleProps) {
  if (!active) return <>{children}</>;

  return (
    <div className={`sparkle-container ${className}`}>
      {children}
      <div className="sparkle-effect" aria-hidden="true" />
    </div>
  );
}
