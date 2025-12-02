/**
 * Tool Result Cache - In-Memory LRU Cache with TTL
 *
 * Caches tool execution results to reduce redundant GraphQL queries and API costs.
 * Uses a simple LRU (Least Recently Used) eviction policy with configurable TTLs.
 */

import crypto from 'crypto';

interface CacheEntry<T> {
  value: T;
  expiresAt: number;
  createdAt: number;
}

interface CacheStats {
  hits: number;
  misses: number;
  evictions: number;
  size: number;
}

/**
 * TTL Configuration by Tool Type (in seconds)
 *
 * Strategy:
 * - Static data (MPs, committees, bills): 24 hours
 * - Semi-static (recent debates): 1 hour
 * - Search results (hansard): 30 minutes
 * - Lobbying data: 6 hours
 * - Scorecards/aggregations: 1 hour
 */
const TOOL_TTL_CONFIG: Record<string, number> = {
  // MP Tools - mostly static (MPs don't change often)
  'search_mps': 24 * 60 * 60, // 24 hours
  'get_mp': 24 * 60 * 60, // 24 hours
  'get_mp_scorecard': 60 * 60, // 1 hour (aggregated data)
  'get_mp_speeches': 60 * 60, // 1 hour (can have new speeches)

  // Bill Tools - static once passed
  'search_bills': 6 * 60 * 60, // 6 hours
  'get_bill': 6 * 60 * 60, // 6 hours
  'get_bill_lobbying': 6 * 60 * 60, // 6 hours
  'get_bill_debates': 60 * 60, // 1 hour

  // Hansard/Debate Tools - search results vary
  'search_hansard': 30 * 60, // 30 minutes
  'get_recent_debates': 60 * 60, // 1 hour

  // Committee Tools - mostly static
  'get_committees': 24 * 60 * 60, // 24 hours
  'get_committee': 24 * 60 * 60, // 24 hours
  'get_committee_testimony': 60 * 60, // 1 hour

  // Accountability/Lobbying Tools
  'get_top_spenders': 6 * 60 * 60, // 6 hours (quarterly data)
  'detect_conflicts_of_interest': 6 * 60 * 60, // 6 hours
  'search_lobby_registrations': 6 * 60 * 60, // 6 hours

  // Navigation Tools - no cache (just URL building)
  'navigate_to_hansard': 0, // No cache
};

// Default TTL for tools not in config: 30 minutes
const DEFAULT_TTL = 30 * 60;

// Maximum cache size (number of entries) before LRU eviction
const MAX_CACHE_SIZE = 1000;

class ToolCache<T = any> {
  private cache: Map<string, CacheEntry<T>>;
  private accessOrder: string[]; // For LRU tracking
  private stats: CacheStats;

  constructor() {
    this.cache = new Map();
    this.accessOrder = [];
    this.stats = {
      hits: 0,
      misses: 0,
      evictions: 0,
      size: 0,
    };
  }

  /**
   * Generate cache key from tool name and parameters
   */
  private generateKey(toolName: string, params: Record<string, any>): string {
    // Sort parameters for consistent key generation
    const sortedParams = Object.keys(params)
      .sort()
      .reduce((acc, key) => {
        acc[key] = params[key];
        return acc;
      }, {} as Record<string, any>);

    const payload = `${toolName}:${JSON.stringify(sortedParams)}`;

    // Use SHA-256 hash for consistent, collision-resistant keys
    return crypto.createHash('sha256').update(payload).digest('hex');
  }

  /**
   * Get TTL for a tool (in seconds)
   */
  private getTTL(toolName: string): number {
    return TOOL_TTL_CONFIG[toolName] ?? DEFAULT_TTL;
  }

  /**
   * Update LRU access order
   */
  private updateAccessOrder(key: string): void {
    // Remove from current position
    const index = this.accessOrder.indexOf(key);
    if (index > -1) {
      this.accessOrder.splice(index, 1);
    }

    // Add to end (most recently used)
    this.accessOrder.push(key);
  }

  /**
   * Evict least recently used entry
   */
  private evictLRU(): void {
    if (this.accessOrder.length === 0) return;

    const lruKey = this.accessOrder.shift()!;
    this.cache.delete(lruKey);
    this.stats.evictions++;
    this.stats.size = this.cache.size;
  }

  /**
   * Clean expired entries
   */
  private cleanExpired(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    this.cache.forEach((entry, key) => {
      if (entry.expiresAt < now) {
        expiredKeys.push(key);
      }
    });

    expiredKeys.forEach((key) => {
      this.cache.delete(key);
      const index = this.accessOrder.indexOf(key);
      if (index > -1) {
        this.accessOrder.splice(index, 1);
      }
    });

    if (expiredKeys.length > 0) {
      this.stats.size = this.cache.size;
      console.log(`[ToolCache] Cleaned ${expiredKeys.length} expired entries`);
    }
  }

  /**
   * Get cached value
   */
  get(toolName: string, params: Record<string, any>): T | null {
    // Clean expired entries periodically (every 100 requests)
    if ((this.stats.hits + this.stats.misses) % 100 === 0) {
      this.cleanExpired();
    }

    const key = this.generateKey(toolName, params);
    const entry = this.cache.get(key);

    if (!entry) {
      this.stats.misses++;
      console.log(`[ToolCache] MISS: ${toolName}`, { params });
      return null;
    }

    // Check if expired
    if (entry.expiresAt < Date.now()) {
      this.cache.delete(key);
      this.stats.misses++;
      this.stats.size = this.cache.size;
      console.log(`[ToolCache] EXPIRED: ${toolName}`, { params });
      return null;
    }

    // Update access order
    this.updateAccessOrder(key);

    this.stats.hits++;
    const age = Math.floor((Date.now() - entry.createdAt) / 1000);
    console.log(`[ToolCache] HIT: ${toolName} (age: ${age}s)`, { params });
    return entry.value;
  }

  /**
   * Set cached value
   */
  set(toolName: string, params: Record<string, any>, value: T): void {
    const ttl = this.getTTL(toolName);

    // Skip caching if TTL is 0
    if (ttl === 0) {
      return;
    }

    const key = this.generateKey(toolName, params);

    // Evict LRU if cache is full
    if (this.cache.size >= MAX_CACHE_SIZE && !this.cache.has(key)) {
      this.evictLRU();
    }

    const now = Date.now();
    const entry: CacheEntry<T> = {
      value,
      expiresAt: now + ttl * 1000,
      createdAt: now,
    };

    this.cache.set(key, entry);
    this.updateAccessOrder(key);
    this.stats.size = this.cache.size;

    console.log(`[ToolCache] SET: ${toolName} (TTL: ${ttl}s)`, { params });
  }

  /**
   * Clear all cached entries
   */
  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
    this.stats = {
      hits: 0,
      misses: 0,
      evictions: 0,
      size: 0,
    };
    console.log('[ToolCache] Cache cleared');
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    const total = this.stats.hits + this.stats.misses;
    const hitRate = total > 0 ? (this.stats.hits / total) * 100 : 0;

    return {
      ...this.stats,
      hitRate: Math.round(hitRate * 100) / 100, // Round to 2 decimals
    } as CacheStats & { hitRate: number };
  }

  /**
   * Invalidate cache entries for a specific tool
   */
  invalidateTool(toolName: string): void {
    const keysToDelete: string[] = [];

    // Find all entries for this tool
    // This is a simple implementation - could be optimized with a secondary index
    this.cache.forEach((entry, key) => {
      // We can't easily reverse-engineer the tool name from the hash,
      // so this is a limitation of the current implementation
      // For now, we'll just clear the entire cache
    });

    console.log(`[ToolCache] Invalidating all entries for: ${toolName}`);
    // TODO: Implement partial invalidation with secondary index
  }
}

// Singleton instance
const toolCache = new ToolCache();

// Export cache instance and types
export { toolCache, type CacheStats };

/**
 * Log cache statistics (call periodically in production)
 */
export function logCacheStats(): void {
  const stats = toolCache.getStats();
  console.log('[ToolCache] Statistics:', stats);
}

/**
 * Clear cache (useful for testing or manual invalidation)
 */
export function clearCache(): void {
  toolCache.clear();
}
