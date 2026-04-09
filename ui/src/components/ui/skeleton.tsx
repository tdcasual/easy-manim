import { cn } from "../../lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-xl bg-muted", className)} {...props} />;
}

function PageSkeleton() {
  return (
    <div className="flex min-h-screen flex-col gap-6 p-6">
      <Skeleton className="h-10 w-64" />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card/60 p-4">
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-3 w-3/4" />
    </div>
  );
}

function SkeletonMetricCard() {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card/60 p-5">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-10 w-24" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

export { PageSkeleton, Skeleton, SkeletonCard, SkeletonMetricCard };
