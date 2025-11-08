# Supabase Database Setup - AI Chat System

This directory contains database migrations for the CanadaGPT AI chat system.

## Overview

The AI chat system uses Supabase PostgreSQL with the following features:
- **Hybrid pricing model**: Free tier, paid subscriptions, BYOK, usage-based billing
- **Row-level security (RLS)**: Ensures users only see their own data
- **Automated quota tracking**: Real-time usage monitoring and enforcement
- **Encrypted API key storage**: AES-256-GCM encryption for BYOK keys
- **Conversation history**: Tiered retention (0/30/90 days)

## Database Schema

### Tables

1. **user_subscriptions** - User subscription tiers and billing settings
   - Tracks tier (free/basic/pro/usage_only)
   - Daily and lifetime quotas
   - Overage limits and charges
   - BYOK flag

2. **user_api_keys** - Encrypted user API keys (BYOK)
   - Stores encrypted Anthropic/OpenAI keys
   - AES-256-GCM encryption with IV and auth tag
   - Validation status tracking

3. **conversations** - Chat conversation threads
   - Context awareness (MP, Bill, Dashboard, etc.)
   - Token tracking
   - Expiration dates based on tier

4. **messages** - Individual messages in conversations
   - Role (user/assistant/system)
   - Token and cost tracking
   - Function calling support

5. **usage_logs** - Detailed query usage logs
   - Daily usage tracking
   - Overage billing records
   - BYOK vs. paid query tracking

6. **credit_packs** - Pre-purchased query credits
   - For usage-only tier
   - Never expire (unless specified)

### Functions

1. **can_user_query(user_id)** - Check if user can make a query
   - Validates subscription status
   - Checks quotas (lifetime for free, daily for paid)
   - Returns: can_query, reason, requires_payment

2. **track_query_usage(...)** - Record query usage
   - Logs usage to usage_logs
   - Calculates overage charges
   - Updates conversation stats

3. **reset_monthly_overages()** - Reset monthly overage charges
   - Run via cron on billing cycle
   - Resets current_overage_amount to 0

4. **cleanup_expired_conversations()** - Delete expired conversations
   - Run daily via cron
   - Deletes non-pinned expired conversations

### Views

- **daily_quota_usage** - Real-time daily usage per user

## Running Migrations

### Option 1: Supabase CLI (Recommended)

```bash
# Install Supabase CLI
npm install -g supabase

# Initialize Supabase (if not already done)
supabase init

# Link to your Supabase project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push

# Or run a specific migration
supabase db push --file supabase/migrations/20250104000000_ai_chat_system.sql
```

### Option 2: Supabase Dashboard

1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `migrations/20250104000000_ai_chat_system.sql`
4. Paste and execute

### Option 3: psql (Direct Connection)

```bash
psql postgresql://postgres:password@db.yourproject.supabase.co:5432/postgres \
  -f supabase/migrations/20250104000000_ai_chat_system.sql
```

## Environment Variables

Add these to your `.env.local`:

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://yourproject.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# AI Providers (for server-side)
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Encryption (generate with: openssl rand -hex 32)
ENCRYPTION_KEY=your-32-byte-hex-key

# Stripe (for billing)
STRIPE_SECRET_KEY=your-stripe-secret-key
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your-stripe-publishable-key
STRIPE_WEBHOOK_SECRET=your-webhook-secret
```

## Testing the Setup

After running the migration, test the setup:

```sql
-- Check tables created
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'user_subscriptions',
    'user_api_keys',
    'conversations',
    'messages',
    'usage_logs',
    'credit_packs'
  );

-- Check functions created
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'can_user_query',
    'track_query_usage',
    'reset_monthly_overages',
    'cleanup_expired_conversations'
  );

-- Test quota checking (will fail until you have a user)
SELECT * FROM can_user_query('00000000-0000-0000-0000-000000000000');
```

## Row-Level Security (RLS)

All tables have RLS enabled. Users can only access their own data:
- Authenticated users see only their own subscriptions, keys, conversations
- Messages are accessible only if the conversation belongs to the user
- Service role can bypass RLS for admin operations

## Pricing Tiers

### Free Tier
- Tier: `free`
- Quota: 10 lifetime queries
- Overages: Not allowed
- BYOK: Not available
- History: No persistent storage

### Basic Tier ($9.99/mo)
- Tier: `basic`
- Quota: 15 queries/day (450/month)
- Overages: $0.025/query (default $10 limit)
- BYOK: Available for unlimited queries
- History: 30 days

### Pro Tier ($29.99/mo)
- Tier: `pro`
- Quota: 40 queries/day (1200/month)
- Overages: $0.025/query (default $10 limit)
- BYOK: Available for unlimited queries
- History: 90 days

### Usage-Only Tier
- Tier: `usage_only`
- Quota: 0 included
- Pay-per-use: $0.025/query
- BYOK: Available for unlimited queries
- History: None

## Automated Tasks (Cron Jobs)

Set up these cron jobs in Supabase:

### Reset Monthly Overages
```sql
-- Run on 1st of each month at midnight UTC
SELECT cron.schedule(
  'reset-monthly-overages',
  '0 0 1 * *',
  'SELECT reset_monthly_overages();'
);
```

### Cleanup Expired Conversations
```sql
-- Run daily at 2 AM UTC
SELECT cron.schedule(
  'cleanup-expired-conversations',
  '0 2 * * *',
  'SELECT cleanup_expired_conversations();'
);
```

## Troubleshooting

### Migration Fails
- Check PostgreSQL version (requires 12+)
- Ensure `auth.users` table exists (Supabase Auth enabled)
- Check for conflicting table names

### RLS Blocks Queries
- Verify you're using `auth.uid()` for authenticated requests
- Check RLS policies are enabled
- Use service role key for admin operations

### Quota Not Enforcing
- Verify `can_user_query()` is called before each query
- Check `usage_logs` are being written
- Ensure `counted_against_quota` is set correctly

## Next Steps

After running this migration:
1. Install frontend dependencies (Vercel AI SDK, Anthropic SDK, etc.)
2. Create Supabase client configuration
3. Build chat context and state management
4. Implement quota checking middleware
5. Create chat API routes
6. Build UI components

See `/AI_CHAT_IMPLEMENTATION_PLAN.md` for the complete implementation roadmap.
