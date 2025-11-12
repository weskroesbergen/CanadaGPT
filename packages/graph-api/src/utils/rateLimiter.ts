/**
 * Rate limiting middleware for GraphQL API
 *
 * Implements per-API-key rate limiting to prevent abuse
 */

import type { AuthContext } from './auth.js';

/**
 * Rate limit configuration
 */
const RATE_LIMIT_WINDOW_MS = 60 * 60 * 1000; // 1 hour in milliseconds

/**
 * Default rate limits by authentication level
 */
export const DEFAULT_RATE_LIMITS = {
  unauthenticated: 100, // 100 requests/hour for unauthenticated
  authenticated: 1000, // 1000 requests/hour for authenticated
  admin: 10000, // 10000 requests/hour for admin
};

/**
 * In-memory rate limit store
 * Maps API key/IP -> { count, resetTime }
 */
interface RateLimitEntry {
  count: number;
  resetTime: number;
}

const rateLimitStore = new Map<string, RateLimitEntry>();

/**
 * Get rate limit key for a request
 * Uses API key if authenticated, otherwise falls back to IP
 *
 * @param authContext - Authentication context
 * @returns Unique key for rate limiting
 */
export function getRateLimitKey(authContext: AuthContext): string {
  if (authContext.authenticated && authContext.apiKey) {
    return `api:${authContext.apiKey}`;
  }
  return `ip:${authContext.ip || 'unknown'}`;
}

/**
 * Get rate limit for authentication context
 *
 * @param authContext - Authentication context
 * @returns Maximum requests allowed per window
 */
export function getRateLimit(authContext: AuthContext): number {
  if (!authContext.authenticated) {
    return DEFAULT_RATE_LIMITS.unauthenticated;
  }

  if (authContext.permissions.includes('admin')) {
    return DEFAULT_RATE_LIMITS.admin;
  }

  return DEFAULT_RATE_LIMITS.authenticated;
}

/**
 * Check if request is within rate limit
 *
 * @param authContext - Authentication context
 * @returns Object with allowed status and remaining requests
 */
export function checkRateLimit(authContext: AuthContext): {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetTime: number;
} {
  const key = getRateLimitKey(authContext);
  const limit = getRateLimit(authContext);
  const now = Date.now();

  // Get or create rate limit entry
  let entry = rateLimitStore.get(key);

  // Reset if window has expired
  if (!entry || entry.resetTime <= now) {
    entry = {
      count: 0,
      resetTime: now + RATE_LIMIT_WINDOW_MS,
    };
    rateLimitStore.set(key, entry);
  }

  // Check if limit exceeded
  if (entry.count >= limit) {
    return {
      allowed: false,
      limit,
      remaining: 0,
      resetTime: entry.resetTime,
    };
  }

  // Increment counter
  entry.count++;
  rateLimitStore.set(key, entry);

  return {
    allowed: true,
    limit,
    remaining: limit - entry.count,
    resetTime: entry.resetTime,
  };
}

/**
 * Clean up expired rate limit entries (garbage collection)
 * Should be called periodically to prevent memory leaks
 */
export function cleanupRateLimitStore(): void {
  const now = Date.now();
  const keysToDelete: string[] = [];

  for (const [key, entry] of rateLimitStore.entries()) {
    if (entry.resetTime <= now) {
      keysToDelete.push(key);
    }
  }

  keysToDelete.forEach(key => rateLimitStore.delete(key));

  if (keysToDelete.length > 0) {
    console.log(`🧹 Cleaned up ${keysToDelete.length} expired rate limit entries`);
  }
}

/**
 * Get rate limit statistics
 *
 * @returns Statistics about current rate limits
 */
export function getRateLimitStats() {
  const now = Date.now();
  let activeEntries = 0;
  let expiredEntries = 0;

  for (const [_, entry] of rateLimitStore.entries()) {
    if (entry.resetTime > now) {
      activeEntries++;
    } else {
      expiredEntries++;
    }
  }

  return {
    totalEntries: rateLimitStore.size,
    activeEntries,
    expiredEntries,
  };
}

/**
 * Format remaining time until rate limit reset
 *
 * @param resetTime - Unix timestamp when limit resets
 * @returns Human-readable time string
 */
export function formatResetTime(resetTime: number): string {
  const now = Date.now();
  const diff = resetTime - now;

  if (diff <= 0) {
    return 'now';
  }

  const minutes = Math.floor(diff / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }

  return `${seconds}s`;
}

// Run cleanup every 5 minutes
setInterval(() => {
  cleanupRateLimitStore();
}, 5 * 60 * 1000);
