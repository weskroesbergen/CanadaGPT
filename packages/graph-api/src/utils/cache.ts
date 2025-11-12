/**
 * Simple in-memory cache with TTL support
 *
 * Provides efficient caching for expensive queries like randomMPs and topSpenders.
 * Cache entries automatically expire based on TTL.
 * Includes size limits to prevent memory exhaustion from DoS attacks.
 */

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
  sizeBytes: number;
}

/**
 * Configuration for cache limits
 */
const CACHE_LIMITS = {
  MAX_ENTRIES: 1000, // Maximum number of cache entries
  MAX_TOTAL_SIZE_MB: 100, // Maximum total cache size in MB
  MAX_ENTRY_SIZE_MB: 10, // Maximum size of a single entry in MB
};

class QueryCache {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private totalSizeBytes: number = 0;

  /**
   * Get cached value if it exists and hasn't expired
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // Check if expired
    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  /**
   * Estimate the size of data in bytes (rough approximation)
   */
  private estimateSize(data: any): number {
    const jsonString = JSON.stringify(data);
    // UTF-8 encoding: most characters are 1 byte, some are more
    // This is a rough estimate
    return new Blob([jsonString]).size;
  }

  /**
   * Evict oldest entries if cache is too full
   */
  private evictIfNeeded(newEntrySize: number): void {
    const maxTotalBytes = CACHE_LIMITS.MAX_TOTAL_SIZE_MB * 1024 * 1024;

    // Check if adding new entry would exceed total size limit
    while (
      this.totalSizeBytes + newEntrySize > maxTotalBytes ||
      this.cache.size >= CACHE_LIMITS.MAX_ENTRIES
    ) {
      // Evict the oldest entry (first entry in the Map)
      const firstKey = this.cache.keys().next().value;
      if (firstKey) {
        const entry = this.cache.get(firstKey);
        if (entry) {
          this.totalSizeBytes -= entry.sizeBytes;
        }
        this.cache.delete(firstKey);
      } else {
        break; // No more entries to evict
      }
    }
  }

  /**
   * Set cache value with TTL in seconds
   * Enforces size limits to prevent memory exhaustion
   */
  set<T>(key: string, data: T, ttlSeconds: number): void {
    const sizeBytes = this.estimateSize(data);
    const maxEntryBytes = CACHE_LIMITS.MAX_ENTRY_SIZE_MB * 1024 * 1024;

    // Reject entries that are too large
    if (sizeBytes > maxEntryBytes) {
      console.warn(
        `Cache entry "${key}" rejected: size ${(sizeBytes / 1024 / 1024).toFixed(2)}MB exceeds maximum ${CACHE_LIMITS.MAX_ENTRY_SIZE_MB}MB`
      );
      return;
    }

    // Remove old entry if updating existing key
    const existingEntry = this.cache.get(key);
    if (existingEntry) {
      this.totalSizeBytes -= existingEntry.sizeBytes;
    }

    // Evict old entries if needed to make room
    this.evictIfNeeded(sizeBytes);

    // Add new entry
    const expiresAt = Date.now() + (ttlSeconds * 1000);
    this.cache.set(key, { data, expiresAt, sizeBytes });
    this.totalSizeBytes += sizeBytes;
  }

  /**
   * Clear a specific cache entry
   */
  delete(key: string): void {
    const entry = this.cache.get(key);
    if (entry) {
      this.totalSizeBytes -= entry.sizeBytes;
    }
    this.cache.delete(key);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.totalSizeBytes = 0;
  }

  /**
   * Get cache statistics including size information
   */
  getStats() {
    const now = Date.now();
    const entries = Array.from(this.cache.entries());
    const activeEntries = entries.filter(([_, entry]) => entry.expiresAt > now);

    return {
      totalEntries: this.cache.size,
      activeEntries: activeEntries.length,
      expiredEntries: this.cache.size - activeEntries.length,
      totalSizeMB: (this.totalSizeBytes / 1024 / 1024).toFixed(2),
      maxEntriesLimit: CACHE_LIMITS.MAX_ENTRIES,
      maxTotalSizeMB: CACHE_LIMITS.MAX_TOTAL_SIZE_MB,
      maxEntrySizeMB: CACHE_LIMITS.MAX_ENTRY_SIZE_MB,
    };
  }

  /**
   * Remove expired entries (garbage collection)
   */
  cleanExpired(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    for (const [key, entry] of this.cache.entries()) {
      if (entry.expiresAt <= now) {
        expiredKeys.push(key);
        this.totalSizeBytes -= entry.sizeBytes;
      }
    }

    expiredKeys.forEach(key => this.cache.delete(key));
  }
}

// Singleton instance
export const queryCache = new QueryCache();

// Run garbage collection every 5 minutes
setInterval(() => {
  queryCache.cleanExpired();
}, 5 * 60 * 1000);

// Helper function to create cache keys
export function createCacheKey(queryName: string, args: Record<string, any>): string {
  const sortedArgs = Object.keys(args)
    .sort()
    .map(key => `${key}:${JSON.stringify(args[key])}`)
    .join('|');

  return `${queryName}:${sortedArgs}`;
}
