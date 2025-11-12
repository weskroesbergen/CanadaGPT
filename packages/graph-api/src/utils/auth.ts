/**
 * Authentication and Authorization utilities for GraphQL API
 *
 * Provides API key management, JWT verification, and access control
 */

import jwt from 'jsonwebtoken';
import crypto from 'crypto';

/**
 * API Key structure
 */
export interface APIKey {
  key: string;
  name: string;
  created: Date;
  expiresAt?: Date;
  rateLimit: number; // requests per hour
  permissions: string[];
}

/**
 * User context extracted from authentication
 */
export interface AuthContext {
  apiKey?: string;
  keyName?: string;
  permissions: string[];
  authenticated: boolean;
  ip?: string;
}

/**
 * Generate a cryptographically secure API key
 *
 * @returns A 64-character hexadecimal API key
 */
export function generateAPIKey(): string {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * Hash an API key for secure storage
 *
 * @param apiKey - The API key to hash
 * @returns SHA-256 hash of the API key
 */
export function hashAPIKey(apiKey: string): string {
  return crypto.createHash('sha256').update(apiKey).digest('hex');
}

/**
 * In-memory API key store
 * In production, this should be replaced with a database or secret manager
 */
const API_KEYS: Map<string, APIKey> = new Map();

/**
 * Initialize default API keys from environment variables
 */
export function initializeAPIKeys(): void {
  // Frontend API key - full access
  const frontendKey = process.env.FRONTEND_API_KEY;
  if (frontendKey) {
    const hashedKey = hashAPIKey(frontendKey);
    API_KEYS.set(hashedKey, {
      key: hashedKey,
      name: 'frontend',
      created: new Date(),
      rateLimit: 10000, // 10k requests/hour
      permissions: ['read', 'write'],
    });
    console.log('✓ Frontend API key registered');
  }

  // Public read-only API key (optional - for public access)
  const publicKey = process.env.PUBLIC_API_KEY;
  if (publicKey) {
    const hashedKey = hashAPIKey(publicKey);
    API_KEYS.set(hashedKey, {
      key: hashedKey,
      name: 'public',
      created: new Date(),
      rateLimit: 1000, // 1k requests/hour
      permissions: ['read'],
    });
    console.log('✓ Public API key registered');
  }

  // Admin API key - for management operations
  const adminKey = process.env.ADMIN_API_KEY;
  if (adminKey) {
    const hashedKey = hashAPIKey(adminKey);
    API_KEYS.set(hashedKey, {
      key: hashedKey,
      name: 'admin',
      created: new Date(),
      rateLimit: 50000, // 50k requests/hour
      permissions: ['read', 'write', 'admin'],
    });
    console.log('✓ Admin API key registered');
  }

  if (API_KEYS.size === 0) {
    console.warn('⚠️  WARNING: No API keys configured! API will be publicly accessible.');
    console.warn('   Set FRONTEND_API_KEY, PUBLIC_API_KEY, or ADMIN_API_KEY in environment');
  }
}

/**
 * Validate an API key
 *
 * @param apiKey - The API key to validate
 * @returns The API key object if valid, null otherwise
 */
export function validateAPIKey(apiKey: string): APIKey | null {
  const hashedKey = hashAPIKey(apiKey);
  const keyData = API_KEYS.get(hashedKey);

  if (!keyData) {
    return null;
  }

  // Check if key has expired
  if (keyData.expiresAt && keyData.expiresAt < new Date()) {
    return null;
  }

  return keyData;
}

/**
 * Extract API key from request headers
 * Supports multiple authentication methods:
 * - Authorization: Bearer <api-key>
 * - X-API-Key: <api-key>
 *
 * @param request - The incoming HTTP request
 * @returns The API key if found, null otherwise
 */
export function extractAPIKey(request: any): string | null {
  // Check Authorization header (Bearer token)
  const authHeader = request.headers.get('authorization');
  if (authHeader) {
    const match = authHeader.match(/^Bearer\s+(.+)$/i);
    if (match) {
      return match[1];
    }
  }

  // Check X-API-Key header
  const apiKeyHeader = request.headers.get('x-api-key');
  if (apiKeyHeader) {
    return apiKeyHeader;
  }

  return null;
}

/**
 * Extract client IP address from request
 * Handles X-Forwarded-For header for proxied requests
 *
 * @param request - The incoming HTTP request
 * @returns The client IP address
 */
export function extractClientIP(request: any): string {
  // Check X-Forwarded-For header (Cloud Run, proxies)
  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    // Take the first IP in the list (original client)
    return forwardedFor.split(',')[0].trim();
  }

  // Check X-Real-IP header
  const realIP = request.headers.get('x-real-ip');
  if (realIP) {
    return realIP;
  }

  // Fallback to connection remote address (not available in all environments)
  return 'unknown';
}

/**
 * Authenticate a request and return auth context
 *
 * @param request - The incoming HTTP request
 * @returns Authentication context
 */
export async function authenticateRequest(request: any): Promise<AuthContext> {
  const apiKey = extractAPIKey(request);
  const ip = extractClientIP(request);

  // If no API key provided
  if (!apiKey) {
    // Check if API keys are required (if any keys are configured)
    if (API_KEYS.size > 0) {
      return {
        authenticated: false,
        permissions: [],
        ip,
      };
    } else {
      // No API keys configured - allow unauthenticated access (backward compatibility)
      console.warn('⚠️  Unauthenticated request allowed (no API keys configured)');
      return {
        authenticated: true,
        permissions: ['read', 'write'], // Full access when no keys configured
        ip,
      };
    }
  }

  // Validate API key
  const keyData = validateAPIKey(apiKey);
  if (!keyData) {
    return {
      authenticated: false,
      permissions: [],
      ip,
    };
  }

  return {
    authenticated: true,
    apiKey: keyData.key,
    keyName: keyData.name,
    permissions: keyData.permissions,
    ip,
  };
}

/**
 * Check if authenticated user has a specific permission
 *
 * @param context - Authentication context
 * @param permission - Required permission
 * @returns True if user has permission
 */
export function hasPermission(context: AuthContext, permission: string): boolean {
  if (!context.authenticated) {
    return false;
  }

  return context.permissions.includes(permission) || context.permissions.includes('admin');
}

/**
 * Require authentication middleware
 * Throws an error if user is not authenticated
 *
 * @param context - Authentication context
 */
export function requireAuth(context: AuthContext): void {
  if (!context.authenticated) {
    throw new Error('Authentication required. Provide a valid API key via Authorization header or X-API-Key header.');
  }
}

/**
 * Require specific permission middleware
 * Throws an error if user does not have required permission
 *
 * @param context - Authentication context
 * @param permission - Required permission
 */
export function requirePermission(context: AuthContext, permission: string): void {
  requireAuth(context);

  if (!hasPermission(context, permission)) {
    throw new Error(`Permission denied. Required permission: ${permission}`);
  }
}

/**
 * Generate a JWT token (optional - for session-based auth)
 *
 * @param payload - JWT payload
 * @param secret - JWT signing secret
 * @param expiresIn - Token expiration (default: 24h)
 * @returns Signed JWT token
 */
export function generateJWT(
  payload: Record<string, any>,
  secret: string,
  expiresIn: string | number = '24h'
): string {
  return jwt.sign(payload, secret, { expiresIn } as jwt.SignOptions);
}

/**
 * Verify a JWT token (optional - for session-based auth)
 *
 * @param token - JWT token to verify
 * @param secret - JWT signing secret
 * @returns Decoded token payload, or null if invalid
 */
export function verifyJWT(token: string, secret: string): Record<string, any> | null {
  try {
    return jwt.verify(token, secret) as Record<string, any>;
  } catch (error) {
    return null;
  }
}
