import { useEffect, useState } from "react";
import { cn } from "../lib/utils";

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

const colorSchemes: Record<string, ColorScheme> = {
  dreamy: {
    gradients: [
      "linear-gradient(135deg, var(--color-mint-300) 0%, var(--color-mint-500) 50%, var(--color-mint-200) 100%)",
      "linear-gradient(135deg, var(--color-lavender-300) 0%, var(--color-lavender-500) 50%, var(--color-lavender-200) 100%)",
      "linear-gradient(135deg, var(--color-pink-300) 0%, var(--color-pink-500) 50%, var(--color-pink-400) 100%)",
    ],
    staticColors: ["var(--color-mint-300)", "var(--color-lavender-300)", "var(--color-pink-300)"],
  },
  sunset: {
    gradients: [
      "linear-gradient(135deg, var(--color-peach-500) 0%, var(--color-peach-200) 50%, var(--color-peach-100) 100%)",
      "linear-gradient(135deg, var(--color-lemon-500) 0%, var(--color-lemon-100) 50%, var(--color-peach-500) 100%)",
      "linear-gradient(135deg, var(--color-pink-400) 0%, var(--color-pink-500) 50%, var(--color-peach-200) 100%)",
    ],
    staticColors: ["var(--color-peach-500)", "var(--color-lemon-500)", "var(--color-pink-400)"],
  },
  ocean: {
    gradients: [
      "linear-gradient(135deg, var(--color-sky-400) 0%, var(--color-sky-500) 50%, var(--color-sky-200) 100%)",
      "linear-gradient(135deg, var(--color-mint-300) 0%, var(--color-sky-500) 50%, var(--color-sky-400) 100%)",
      "linear-gradient(135deg, var(--color-lavender-300) 0%, var(--color-lavender-500) 50%, var(--color-lavender-200) 100%)",
    ],
    staticColors: ["var(--color-sky-400)", "var(--color-mint-300)", "var(--color-lavender-300)"],
  },
  minimal: {
    gradients: [
      "linear-gradient(135deg, var(--color-cloud-400) 0%, var(--color-cloud-500) 50%, var(--color-cloud-300) 100%)",
      "linear-gradient(135deg, var(--color-cloud-600) 0%, var(--color-cloud-700) 50%, var(--color-cloud-400) 100%)",
      "linear-gradient(135deg, var(--color-cloud-300) 0%, var(--color-cloud-100) 50%, var(--color-cloud-200) 100%)",
    ],
    staticColors: ["var(--color-cloud-400)", "var(--color-cloud-600)", "var(--color-cloud-300)"],
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

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);
    const handleChange = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

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

  const opacityMap = { low: 0.08, medium: 0.15, high: 0.25 };
  const baseOpacity = opacityMap[intensity];

  if (prefersReducedMotion) {
    const [primaryColor, secondaryColor, tertiaryColor] = colorSchemes[scheme].staticColors;
    return (
      <div
        className="pointer-events-none fixed inset-0 -z-10"
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
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {orbs.map((orb) => (
        <div
          key={orb.id}
          className={cn(
            "absolute -translate-x-1/2 -translate-y-1/2 rounded-full blur-[80px] will-change-transform",
            animated && "animate-orb-float"
          )}
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
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}

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
