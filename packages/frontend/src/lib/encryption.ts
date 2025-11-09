/**
 * Token Encryption/Decryption Utilities
 * Uses AES-256-GCM for secure token storage
 *
 * Based on working frontend implementation
 */

import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;
const AUTH_TAG_LENGTH = 16;

/**
 * Get encryption key from environment
 * Should be a 32-byte hex string (64 characters)
 */
function getEncryptionKey(): Buffer {
  const key = process.env.ENCRYPTION_KEY;

  if (!key) {
    throw new Error('ENCRYPTION_KEY environment variable is required');
  }

  // Convert hex string to buffer
  if (key.length !== 64) {
    throw new Error('ENCRYPTION_KEY must be a 64-character hex string (32 bytes)');
  }

  return Buffer.from(key, 'hex');
}

/**
 * Encrypt a token using AES-256-GCM
 * @param token - Plain text token to encrypt
 * @returns Encrypted token as base64 string (format: iv:authTag:encryptedData)
 */
export function encryptToken(token: string): string {
  try {
    const key = getEncryptionKey();
    const iv = crypto.randomBytes(IV_LENGTH);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

    let encrypted = cipher.update(token, 'utf8', 'hex');
    encrypted += cipher.final('hex');

    const authTag = cipher.getAuthTag();

    // Combine IV, auth tag, and encrypted data
    const combined = `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;

    // Return as base64 for storage
    return Buffer.from(combined).toString('base64');
  } catch (error) {
    console.error('Token encryption failed:', error);
    throw new Error('Failed to encrypt token');
  }
}

/**
 * Decrypt a token using AES-256-GCM
 * @param encryptedToken - Encrypted token as base64 string
 * @returns Decrypted plain text token
 */
export function decryptToken(encryptedToken: string): string {
  try {
    const key = getEncryptionKey();

    // Decode from base64
    const combined = Buffer.from(encryptedToken, 'base64').toString('utf8');

    // Split into components
    const parts = combined.split(':');
    if (parts.length !== 3) {
      throw new Error('Invalid encrypted token format');
    }

    const [ivHex, authTagHex, encryptedHex] = parts;

    const iv = Buffer.from(ivHex, 'hex');
    const authTag = Buffer.from(authTagHex, 'hex');
    const encrypted = encryptedHex;

    // Create decipher
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');

    return decrypted;
  } catch (error) {
    console.error('Token decryption failed:', error);
    throw new Error('Failed to decrypt token');
  }
}

/**
 * Generate a new encryption key
 * Use this to generate the ENCRYPTION_KEY environment variable
 * @returns 32-byte hex string
 */
export function generateEncryptionKey(): string {
  return crypto.randomBytes(32).toString('hex');
}

/**
 * Hash a sensitive value for comparison (one-way)
 * Useful for storing hashed values
 * @param value - Value to hash
 * @returns SHA-256 hash as hex string
 */
export function hashValue(value: string): string {
  return crypto.createHash('sha256').update(value).digest('hex');
}

/**
 * Verify if a value matches a hash
 * @param value - Plain text value
 * @param hash - Hash to compare against
 */
export function verifyHash(value: string, hash: string): boolean {
  const valueHash = hashValue(value);
  return crypto.timingSafeEqual(Buffer.from(valueHash), Buffer.from(hash));
}
