import "./Skeleton.css";

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
    borderRadius: circle ? "50%" : undefined,
  };

  return (
    <div
      className={`skeleton skeleton--${animation} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

// 骨架屏卡片
export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <Skeleton height={160} className="skeleton-card__image" />
      <div className="skeleton-card__content">
        <Skeleton width="80%" height={20} />
        <Skeleton width="60%" height={16} />
        <Skeleton width="40%" height={16} />
      </div>
    </div>
  );
}

// 骨架屏列表项
export function SkeletonListItem() {
  return (
    <div className="skeleton-list-item">
      <Skeleton width={40} height={40} circle />
      <div className="skeleton-list-item__content">
        <Skeleton width="60%" height={18} />
        <Skeleton width="40%" height={14} />
      </div>
      <Skeleton width={60} height={24} />
    </div>
  );
}

// 骨架屏指标卡片
export function SkeletonMetricCard() {
  return (
    <div className="skeleton-metric-card">
      <Skeleton width={48} height={48} circle />
      <div className="skeleton-metric-card__content">
        <Skeleton width={80} height={14} />
        <Skeleton width={60} height={32} />
      </div>
    </div>
  );
}

// 页面加载骨架屏
export function PageSkeleton() {
  return (
    <div className="page-skeleton">
      <div className="page-skeleton__header">
        <Skeleton width={200} height={32} />
        <Skeleton width={120} height={24} />
      </div>
      <div className="page-skeleton__metrics">
        <SkeletonMetricCard />
        <SkeletonMetricCard />
        <SkeletonMetricCard />
        <SkeletonMetricCard />
      </div>
      <div className="page-skeleton__content">
        <Skeleton height={300} />
      </div>
    </div>
  );
}
