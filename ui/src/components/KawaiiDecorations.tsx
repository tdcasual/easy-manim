import { Cloud, Star, Sparkles } from "lucide-react";
import { cn } from "../lib/utils";

export function FloatingClouds() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <div
        className="absolute top-[10%] -left-[10%] animate-cloud text-pink-200/60 [animation-duration:25s]"
        style={{ filter: "drop-shadow(0 4px 8px rgba(255,167,196,0.3))" }}
      >
        <Cloud size={80} strokeWidth={1} />
      </div>
      <div
        className="absolute top-[25%] -right-[5%] animate-cloud text-mint-200/50 [animation-duration:30s] [animation-direction:reverse]"
        style={{ filter: "drop-shadow(0 4px 8px rgba(127,212,182,0.3))" }}
      >
        <Cloud size={60} strokeWidth={1} />
      </div>
      <div
        className="absolute top-[60%] -left-[15%] animate-cloud text-sky-200/50 [animation-duration:35s]"
        style={{ filter: "drop-shadow(0 4px 8px rgba(90,180,209,0.3))" }}
      >
        <Cloud size={100} strokeWidth={1} />
      </div>
      <div
        className="absolute top-[75%] -right-[10%] animate-cloud text-lavender-200/40 [animation-duration:28s] [animation-direction:reverse]"
        style={{ filter: "drop-shadow(0 4px 8px rgba(212,158,212,0.3))" }}
      >
        <Cloud size={50} strokeWidth={1} />
      </div>
      <div
        className="absolute top-[40%] -left-[5%] animate-cloud text-peach-200/50 [animation-duration:32s]"
        style={{ filter: "drop-shadow(0 4px 8px rgba(244,140,75,0.3))" }}
      >
        <Cloud size={70} strokeWidth={1} />
      </div>
    </div>
  );
}

export function TwinklingStars() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <div className="absolute top-[15%] left-[10%] animate-twinkle [animation-duration:2s]">
        <Star size={16} fill="var(--color-lemon-500)" color="var(--color-lemon-500)" />
      </div>
      <div className="absolute top-[20%] right-[15%] animate-twinkle [animation-duration:2.5s] [animation-delay:0.5s]">
        <Star size={12} fill="var(--color-pink-400)" color="var(--color-pink-400)" />
      </div>
      <div className="absolute top-[35%] left-[20%] animate-twinkle [animation-duration:3s] [animation-delay:1s]">
        <Star size={20} fill="var(--color-mint-200)" color="var(--color-mint-200)" />
      </div>
      <div className="absolute top-[50%] right-[10%] animate-twinkle [animation-duration:2.2s] [animation-delay:0.3s]">
        <Star size={14} fill="var(--color-lavender-200)" color="var(--color-lavender-200)" />
      </div>
      <div className="absolute top-[65%] left-[15%] animate-twinkle [animation-duration:2.8s] [animation-delay:0.8s]">
        <Star size={18} fill="var(--color-peach-100)" color="var(--color-peach-100)" />
      </div>
      <div className="absolute top-[80%] right-[20%] animate-twinkle [animation-duration:2.3s] [animation-delay:1.2s]">
        <Star size={10} fill="var(--color-lemon-500)" color="var(--color-lemon-500)" />
      </div>
      <div className="absolute top-[25%] left-[5%] animate-twinkle [animation-duration:2.6s] [animation-delay:0.2s]">
        <Sparkles size={16} color="var(--color-lemon-500)" />
      </div>
      <div className="absolute top-[70%] right-[5%] animate-twinkle [animation-duration:2.1s] [animation-delay:1.5s]">
        <Sparkles size={14} color="var(--color-pink-400)" />
      </div>
    </div>
  );
}

export function FallingPetals() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <span className="absolute left-[10%] animate-petal-fall text-2xl [animation-duration:8s]">
        🌸
      </span>
      <span className="absolute left-[30%] animate-petal-fall text-2xl [animation-duration:10s] [animation-delay:2s]">
        🌺
      </span>
      <span className="absolute left-[50%] animate-petal-fall text-2xl [animation-duration:9s] [animation-delay:4s]">
        🌸
      </span>
      <span className="absolute left-[70%] animate-petal-fall text-2xl [animation-duration:11s] [animation-delay:1s]">
        💮
      </span>
      <span className="absolute left-[85%] animate-petal-fall text-2xl [animation-duration:8.5s] [animation-delay:3s]">
        🌸
      </span>
      <span className="absolute left-[20%] animate-petal-fall text-2xl [animation-duration:10.5s] [animation-delay:5s]">
        🌼
      </span>
    </div>
  );
}

export function FloatingBubbles() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden="true">
      <div
        className="absolute -bottom-[50px] left-[10%] h-[40px] w-[40px] animate-float-in [animation-duration:12s] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(255,167,196,0.3))",
        }}
      />
      <div
        className="absolute -bottom-[50px] left-[30%] h-[25px] w-[25px] animate-float-in [animation-duration:15s] [animation-delay:2s] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(255,167,196,0.3))",
        }}
      />
      <div
        className="absolute -bottom-[50px] left-[60%] h-[35px] w-[35px] animate-float-in [animation-duration:13s] [animation-delay:4s] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(255,167,196,0.3))",
        }}
      />
      <div
        className="absolute -bottom-[50px] left-[80%] h-[20px] w-[20px] animate-float-in [animation-duration:16s] [animation-delay:1s] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(255,167,196,0.3))",
        }}
      />
      <div
        className="absolute -bottom-[50px] left-[45%] h-[30px] w-[30px] animate-float-in [animation-duration:14s] [animation-delay:3s] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.8), rgba(255,167,196,0.3))",
        }}
      />
    </div>
  );
}

export function GradientOrbs() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="absolute -top-[100px] -left-[100px] h-[400px] w-[400px] rounded-full bg-pink-300/50 blur-[80px] animate-orb-float [animation-duration:8s]" />
      <div className="absolute top-[30%] -right-[100px] h-[350px] w-[350px] rounded-full bg-mint-300/50 blur-[80px] animate-orb-float [animation-duration:10s] [animation-delay:2s]" />
      <div className="absolute -bottom-[50px] left-[20%] h-[300px] w-[300px] rounded-full bg-sky-300/50 blur-[80px] animate-orb-float [animation-duration:9s] [animation-delay:4s]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[250px] w-[250px] rounded-full bg-lavender-300/50 blur-[80px] animate-orb-float [animation-duration:11s] [animation-delay:1s]" />
    </div>
  );
}

export function KawaiiBackground() {
  return (
    <>
      <GradientOrbs />
      <FloatingClouds />
      <TwinklingStars />
    </>
  );
}

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
    <div className={cn("relative min-h-screen", className)}>
      {showClouds && <FloatingClouds />}
      {showStars && <TwinklingStars />}
      {showPetals && <FallingPetals />}
      {showBubbles && <FloatingBubbles />}
      {children}
    </div>
  );
}
