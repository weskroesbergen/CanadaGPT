/**
 * Loading skeleton components for better perceived performance
 */

'use client';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-md bg-bg-elevated ${className}`}
    />
  );
}

/**
 * Skeleton for MP Card
 */
export function MPCardSkeleton() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-primary p-4">
      <div className="flex items-start space-x-4">
        {/* Photo skeleton */}
        <Skeleton className="w-[60px] h-24 rounded-lg flex-shrink-0" />

        {/* Info skeleton */}
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton for Compact MP Card (Chamber view)
 */
export function CompactMPCardSkeleton() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-primary p-2">
      {/* Photo skeleton */}
      <Skeleton className="w-full h-96 rounded-md mb-2" />

      {/* Info skeleton */}
      <div className="space-y-1">
        <Skeleton className="h-3 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  );
}

/**
 * Skeleton for News Article
 */
export function NewsArticleSkeleton() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-elevated overflow-hidden">
      <div className="flex gap-4">
        {/* Image skeleton */}
        <Skeleton className="flex-shrink-0 w-48 h-32" />

        {/* Content skeleton */}
        <div className="flex-1 p-4 space-y-3">
          <Skeleton className="h-5 w-full" />
          <Skeleton className="h-4 w-4/5" />
          <div className="flex gap-4">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton for Bill Card
 */
export function BillCardSkeleton() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-primary p-4 space-y-3">
      <div className="flex items-start justify-between">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-5 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <div className="flex gap-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

/**
 * Skeleton for Committee Card
 */
export function CommitteeCardSkeleton() {
  return (
    <div className="rounded-lg border border-border-subtle bg-bg-primary p-4 space-y-3">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
      <div className="flex gap-2 mt-4">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

/**
 * Generic grid of skeleton cards
 */
interface SkeletonGridProps {
  count?: number;
  component?: React.ComponentType;
}

export function SkeletonGrid({ count = 6, component: Component = MPCardSkeleton }: SkeletonGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <Component key={i} />
      ))}
    </div>
  );
}

/**
 * Generic list of skeleton items
 */
interface SkeletonListProps {
  count?: number;
  component?: React.ComponentType;
}

export function SkeletonList({ count = 5, component: Component = NewsArticleSkeleton }: SkeletonListProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <Component key={i} />
      ))}
    </div>
  );
}
