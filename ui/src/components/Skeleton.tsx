import { cn } from "../lib/utils";

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  circle?: boolean;
  animation?: "pulse" | "wave" | "none";
}

export function Skeleton({
  className = "",
  width,
  height,
  circle = false,
  animation = "pulse",
}: SkeletonProps) {
  const style: React.CSSProperties = {
    width: typeof width === "number" ? `${width}px` : width,
    height: typeof height === "number" ? `${height}px` : height,
  };

  return (
    <div
      className={cn(
        "rounded-xl bg-muted",
        animation === "pulse" && "animate-pulse",
        animation === "wave" && "animate-pulse",
        circle && "rounded-full",
        className
      )}
      style={style}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-muted p-4">
      <Skeleton height={160} className="w-full rounded-xl" />
      <div className="flex flex-col gap-2">
        <Skeleton width="80%" height={20} />
        <Skeleton width="60%" height={16} />
        <Skeleton width="40%" height={16} />
      </div>
    </div>
  );
}

export function SkeletonListItem() {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-muted p-4">
      <Skeleton width={40} height={40} circle />
      <div className="flex flex-1 flex-col gap-2">
        <Skeleton width="60%" height={18} />
        <Skeleton width="40%" height={14} />
      </div>
      <Skeleton width={60} height={24} />
    </div>
  );
}

export function SkeletonMetricCard() {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-muted p-5">
      <Skeleton width={48} height={48} circle />
      <div className="flex flex-col gap-2">
        <Skeleton width={80} height={14} />
        <Skeleton width={60} height={32} />
      </div>
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="flex min-h-screen flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <Skeleton width={200} height={32} />
        <Skeleton width={120} height={24} />
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <SkeletonMetricCard />
        <SkeletonMetricCard />
        <SkeletonMetricCard />
        <SkeletonMetricCard />
      </div>
      <Skeleton height={300} className="w-full rounded-2xl" />
    </div>
  );
}
