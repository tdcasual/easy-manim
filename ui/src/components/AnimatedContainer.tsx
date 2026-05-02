import { useState, useEffect, useRef, type ReactNode } from "react";
import { cn } from "../lib/utils";

export type AnimationType = "fade" | "slide-up" | "slide-down" | "slide-left" | "slide-right";

interface AnimatedContainerProps {
  children: ReactNode;
  animation?: AnimationType;
  delay?: number;
  duration?: number;
  className?: string;
  trigger?: "mount" | "in-view" | "manual";
  onAnimationEnd?: () => void;
}

const animationClassMap: Record<AnimationType, string> = {
  fade: "animate-fade-in",
  "slide-up": "animate-slide-up",
  "slide-down": "animate-slide-down",
  "slide-left": "animate-slide-left",
  "slide-right": "animate-slide-right",
};

export function AnimatedContainer({
  children,
  animation = "fade",
  delay = 0,
  duration = 500,
  className = "",
  trigger = "mount",
  onAnimationEnd,
}: AnimatedContainerProps) {
  const [isVisible, setIsVisible] = useState(trigger === "manual");
  const [hasAnimated, setHasAnimated] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    if (trigger === "mount") {
      timeoutId = setTimeout(() => {
        setIsVisible(true);
      }, delay);
      return () => {
        if (timeoutId) clearTimeout(timeoutId);
      };
    }

    if (trigger === "in-view" && ref.current) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting && !hasAnimated) {
              timeoutId = setTimeout(() => {
                setIsVisible(true);
                setHasAnimated(true);
              }, delay);
            }
          });
        },
        { threshold: 0.1 }
      );

      observer.observe(ref.current);
      return () => {
        observer.disconnect();
        if (timeoutId) clearTimeout(timeoutId);
      };
    }
  }, [trigger, delay, hasAnimated]);

  return (
    <div
      ref={ref}
      className={cn(
        "will-change-transform opacity-0",
        isVisible && ["visible", animationClassMap[animation]],
        className
      )}
      style={{
        animationDuration: `${duration}ms`,
        animationDelay: `${delay}ms`,
      }}
      onAnimationEnd={onAnimationEnd}
    >
      {children}
    </div>
  );
}

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
    <div className={cn("flex flex-col gap-3", className)}>
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

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export function PageTransition({ children, className = "" }: PageTransitionProps) {
  return (
    <div className={cn("relative", className)}>
      <AnimatedContainer animation="fade" duration={300}>
        {children}
      </AnimatedContainer>
    </div>
  );
}

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
    <div className={cn("hover-animate", className)} style={style}>
      {children}
    </div>
  );
}

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
      className={cn("relative", pulse && "", className)}
      style={
        {
          "--glow-color": color,
          "--glow-intensity": intensityMap[intensity],
        } as React.CSSProperties
      }
    >
      <span
        className="pointer-events-none absolute -inset-1 -z-10 rounded-[inherit] opacity-0 transition-opacity duration-300"
        style={{
          background: `var(--glow-color, currentColor)`,
          filter: "blur(12px)",
        }}
        aria-hidden="true"
      />
      {children}
    </div>
  );
}

interface SparkleProps {
  children: ReactNode;
  active?: boolean;
  className?: string;
}

export function Sparkle({ children, active = true, className = "" }: SparkleProps) {
  if (!active) return <>{children}</>;

  return (
    <div className={cn("relative inline-block", className)}>
      {children}
      <span className="pointer-events-none absolute inset-0" aria-hidden="true">
        <span className="absolute -right-2 -top-2 text-lg">✨</span>
        <span className="absolute -bottom-1 -left-1 text-base">✨</span>
      </span>
    </div>
  );
}
