/**
 * SkyBackground - sky background component.
 * Includes drifting clouds, stars, moon/sun decorations.
 */
import { useMemo } from "react";

// Cloud SVG component
function CloudSVG({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg
      className={className}
      style={style}
      viewBox="0 0 200 100"
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path d="M40 70c-11 0-20-9-20-20s9-20 20-20c2 0 4 0 6 1 4-12 15-21 29-21 14 0 25 9 29 21 2-1 4-1 6-1 11 0 20 9 20 20s-9 20-20 20H40z" />
    </svg>
  );
}

// Single cloud component
interface CloudProps {
  size: number;
  top: string;
  duration: number;
  delay: number;
  opacity: number;
  layer: number;
}

function Cloud({ size, top, duration, delay, opacity, layer }: CloudProps) {
  const style: React.CSSProperties = {
    position: "absolute",
    top,
    left: "-200px",
    width: `${size}px`,
    height: `${size * 0.5}px`,
    opacity,
    color: "var(--cloud)",
    filter: `drop-shadow(0 ${4 * layer}px ${8 * layer}px var(--cloud-shadow))`,
    animation: `drift ${duration}s linear infinite`,
    animationDelay: `${delay}s`,
    zIndex: layer,
  };

  return <CloudSVG style={style} />;
}

// Star component
interface StarProps {
  size: number;
  left: string;
  top: string;
  delay: number;
  duration: number;
}

function Star({ size, left, top, delay, duration }: StarProps) {
  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        width: `${size}px`,
        height: `${size}px`,
        background: "var(--star)",
        borderRadius: "50%",
        boxShadow: `0 0 ${size * 2}px var(--star)`,
        animation: `twinkle ${duration}s ease-in-out infinite`,
        animationDelay: `${delay}s`,
      }}
    />
  );
}

// Moon component
function Moon() {
  return (
    <div
      className="moon"
      style={{
        position: "absolute",
        top: "10%",
        right: "10%",
        width: "80px",
        height: "80px",
        borderRadius: "50%",
        background: "var(--moon)",
        boxShadow: `
          0 0 60px var(--moon-glow),
          0 0 100px var(--moon-glow),
          inset -10px -10px 20px rgba(0,0,0,0.1)
        `,
        animation: "breathe 8s ease-in-out infinite",
      }}
    >
      {/* Moon surface texture */}
      <div
        style={{
          position: "absolute",
          top: "20%",
          left: "30%",
          width: "15px",
          height: "15px",
          borderRadius: "50%",
          background: "rgba(0,0,0,0.05)",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "60%",
          width: "10px",
          height: "10px",
          borderRadius: "50%",
          background: "rgba(0,0,0,0.05)",
        }}
      />
    </div>
  );
}

// Sun component
function Sun() {
  return (
    <div
      className="sun"
      style={{
        position: "absolute",
        top: "8%",
        right: "12%",
        width: "70px",
        height: "70px",
        borderRadius: "50%",
        background:
          "linear-gradient(135deg, var(--color-lemon-100) 0%, var(--color-lemon-200) 100%)",
        boxShadow: `
          0 0 40px rgba(255, 236, 179, 0.6),
          0 0 80px rgba(255, 236, 179, 0.3)
        `,
        opacity: 0.9,
      }}
    >
      {/* Sun glow */}
      <div
        style={{
          position: "absolute",
          inset: "-20px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,247,168,0.25) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}

// Grass tuft component
function GrassTuft({
  left,
  scale = 1,
  delay = 0,
}: {
  left: string;
  scale?: number;
  delay?: number;
}) {
  return (
    <svg
      style={{
        position: "absolute",
        bottom: "0",
        left,
        width: `${40 * scale}px`,
        height: `${60 * scale}px`,
        transformOrigin: "bottom center",
        animation: `sway ${3 + delay}s ease-in-out infinite`,
        animationDelay: `${delay}s`,
      }}
      viewBox="0 0 40 60"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M20 60c0-20-5-40-15-55M20 60c0-15 3-35 10-50M20 60c0-25 8-40 12-48"
        stroke="var(--grass-mid)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d="M20 60c-2-18-8-32-12-42M20 60c2-20 6-35 8-45"
        stroke="var(--grass-light)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Falling petals
function FallingPetal({
  left,
  delay,
  duration,
  color,
}: {
  left: string;
  delay: number;
  duration: number;
  color: string;
}) {
  return (
    <div
      style={{
        position: "absolute",
        left,
        top: "-20px",
        width: "12px",
        height: "8px",
        background: color,
        borderRadius: "50% 50% 50% 50% / 60% 60% 40% 40%",
        opacity: 0.7,
        animation: `petal-fall ${duration}s linear infinite`,
        animationDelay: `${delay}s`,
      }}
    />
  );
}

// Main component
interface SkyBackgroundProps {
  isNight?: boolean;
}

// Use a fixed seed for pseudo-random numbers to avoid SSR hydration mismatch
function seededRandom(seed: number): number {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

// Pre-generated configs to avoid recomputing on every render
const CLOUD_CONFIGS = Array.from({ length: 6 }, (_, i) => ({
  size: 120 + seededRandom(i * 100) * 100,
  top: `${5 + seededRandom(i * 100 + 1) * 35}%`,
  duration: 40 + seededRandom(i * 100 + 2) * 30,
  delay: seededRandom(i * 100 + 3) * -50,
  opacity: 0.6 + seededRandom(i * 100 + 4) * 0.3,
  layer: Math.floor(seededRandom(i * 100 + 5) * 3) + 1,
}));

const STAR_CONFIGS = Array.from({ length: 30 }, (_, i) => ({
  size: 2 + seededRandom(i * 200) * 3,
  left: `${seededRandom(i * 200 + 1) * 100}%`,
  top: `${seededRandom(i * 200 + 2) * 50}%`,
  delay: seededRandom(i * 200 + 3) * 5,
  duration: 2 + seededRandom(i * 200 + 4) * 3,
}));

const GRASS_CONFIGS = Array.from({ length: 15 }, (_, i) => ({
  left: `${seededRandom(i * 300) * 100}%`,
  scale: 0.6 + seededRandom(i * 300 + 1) * 0.6,
  delay: seededRandom(i * 300 + 2) * 2,
}));

const PETAL_COLORS = ["var(--flower-pink)", "var(--flower-yellow)", "var(--flower-blue)"];
const PETAL_CONFIGS = Array.from({ length: 5 }, (_, i) => ({
  left: `${10 + seededRandom(i * 400) * 80}%`,
  delay: seededRandom(i * 400 + 1) * 20,
  duration: 15 + seededRandom(i * 400 + 2) * 10,
  color: PETAL_COLORS[Math.floor(seededRandom(i * 400 + 3) * PETAL_COLORS.length)],
}));

export function SkyBackground({ isNight = false }: SkyBackgroundProps) {
  // Use pre-generated configs
  const clouds = useMemo(() => CLOUD_CONFIGS, []);
  const stars = useMemo(() => (isNight ? STAR_CONFIGS : []), [isNight]);
  const grassTufts = useMemo(() => GRASS_CONFIGS, []);
  const petals = useMemo(() => PETAL_CONFIGS, []);

  return (
    <div
      className="sky-background"
      style={{
        position: "fixed",
        inset: 0,
        pointerEvents: "none",
        overflow: "hidden",
        zIndex: 0,
      }}
    >
      {/* Stars (night only) */}
      {isNight && stars.map((star, i) => <Star key={`star-${i}`} {...star} />)}

      {/* Moon or sun */}
      {isNight ? <Moon /> : <Sun />}

      {/* Clouds */}
      {clouds.map((cloud, i) => (
        <Cloud key={`cloud-${i}`} {...cloud} />
      ))}

      {/* Falling petals */}
      {petals.map((petal, i) => (
        <FallingPetal key={`petal-${i}`} {...petal} />
      ))}

      {/* Bottom grass */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "60px",
          pointerEvents: "none",
        }}
      >
        {grassTufts.map((tuft, i) => (
          <GrassTuft key={`grass-${i}`} {...tuft} />
        ))}
      </div>
    </div>
  );
}
