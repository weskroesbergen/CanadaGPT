/**
 * NextAuth v5 API Route Handler
 *
 * Handles all authentication requests:
 * - OAuth callbacks (Google, GitHub, Facebook)
 * - Credentials signin
 * - Session management
 */

import { handlers } from '@/auth';

export const { GET, POST } = handlers;
