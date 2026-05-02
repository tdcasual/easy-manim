/**
 * useResponsive - responsive breakpoint detection hook.
 */
import { useState, useEffect, useCallback } from "react";

type Breakpoint = "xs" | "sm" | "md" | "lg" | "xl";

const breakpoints = {
  xs: 0,
  sm: 480,
  md: 768,
  lg: 1024,
  xl: 1440,
};

export function useResponsive() {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>("lg");
  const [width, setWidth] = useState<number>(
    typeof window !== "undefined" ? window.innerWidth : 1024
  );

  const getBreakpoint = useCallback((w: number): Breakpoint => {
    if (w >= breakpoints.xl) return "xl";
    if (w >= breakpoints.lg) return "lg";
    if (w >= breakpoints.md) return "md";
    if (w >= breakpoints.sm) return "sm";
    return "xs";
  }, []);

  useEffect(() => {
    const handleResize = () => {
      const w = window.innerWidth;
      setWidth(w);
      setBreakpoint(getBreakpoint(w));
    };

    // Initialize
    handleResize();

    // Throttle with requestAnimationFrame
    let ticking = false;
    const throttledResize = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          handleResize();
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener("resize", throttledResize);
    return () => window.removeEventListener("resize", throttledResize);
  }, [getBreakpoint]);

  return {
    breakpoint,
    width,
    isXs: breakpoint === "xs",
    isSm: breakpoint === "sm",
    isMd: breakpoint === "md",
    isLg: breakpoint === "lg",
    isXl: breakpoint === "xl",
    isMobile: breakpoint === "xs" || breakpoint === "sm",
    isTablet: breakpoint === "md",
    isDesktop: breakpoint === "lg" || breakpoint === "xl",
  };
}
