# Forum System Setup Instructions

This guide walks you through setting up the forum/discussion system for CanadaGPT.

## Step 1: Apply Database Migration

The forum system requires new database tables in Supabase. You have two options:

### Option A: Using Supabase Dashboard (Recommended - Easiest)

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk)
2. Click **SQL Editor** in the left sidebar
3. Click **New Query**
4. Open the file `/supabase/migrations/20250107000000_forum_system.sql`
5. Copy and paste the entire contents into the SQL editor
6. Click **Run** button
7. Wait for confirmation message: "Success. No rows returned"

### Option B: Using Supabase CLI

```bash
# Link your Supabase project (first time only)
cd /Users/matthewdufresne/FedMCP
supabase link --project-ref pbxyhcdzdovsdlsyixsk

# Push the migration
supabase db push
```

## Step 2: Verify Migration

After running the migration, verify the tables were created:

1. In Supabase Dashboard, go to **Table Editor**
2. You should see these new tables:
   - `user_profiles`
   - `forum_categories` (with 10 pre-seeded categories)
   - `forum_posts`
   - `forum_votes`
   - `moderation_reports`
   - `moderation_actions`

## Step 3: Install Additional Dependencies (if needed)

The forum system uses existing dependencies, but for enhanced Markdown support:

```bash
cd packages/frontend
pnpm install remark-gfm rehype-sanitize  # For safe Markdown rendering
```

## Step 4: Development Server

The dev servers should already be running. If not:

```bash
# Terminal 1: GraphQL API
cd packages/graph-api
pnpm dev

# Terminal 2: Frontend
cd packages/frontend
pnpm dev
```

## Step 5: Test the Forum

Once the implementation is complete, you'll be able to:

1. Visit `http://localhost:3000/forum` - Forum homepage
2. Click a category (e.g., "Healthcare") - View discussions
3. Create a post - Test authentication + post creation
4. Reply to a post - Test threaded replies
5. Upvote/downvote - Test voting system
6. Visit a bill page → "Discussions" tab - Bill-specific comments

## What Was Created

### Database Tables

1. **user_profiles** - User display names, avatars, reputation
2. **forum_categories** - Discussion categories (Healthcare, Climate, etc.)
3. **forum_posts** - Posts and threaded replies
4. **forum_votes** - Upvote/downvote tracking
5. **moderation_reports** - User-flagged content
6. **moderation_actions** - Admin moderation log

### Security Features

- **Row-Level Security (RLS)** on all tables
- **Rate limiting**: Max 10 posts per hour per user
- **Soft deletes**: Posts never actually deleted (for moderation records)
- **Vote uniqueness**: One vote per user per post
- **Report uniqueness**: One report per user per post

### Seeded Data

10 initial forum categories:
- General Discussion
- Healthcare
- Climate & Environment
- Economy & Finance
- Justice & Law
- Indigenous Affairs
- Immigration
- Education
- Defence & Security
- Housing

## Troubleshooting

### Migration Errors

If you see errors about existing tables:

```sql
-- In Supabase SQL Editor, drop existing tables first:
DROP TABLE IF EXISTS public.moderation_actions CASCADE;
DROP TABLE IF EXISTS public.moderation_reports CASCADE;
DROP TABLE IF EXISTS public.forum_votes CASCADE;
DROP TABLE IF EXISTS public.forum_posts CASCADE;
DROP TABLE IF EXISTS public.forum_categories CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;

-- Then re-run the migration
```

### RLS Errors

If you get "permission denied" errors, ensure RLS policies were created:

```sql
-- Check RLS is enabled:
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'forum%' OR tablename = 'user_profiles';

-- Should show rowsecurity = true for all tables
```

### Connection Errors

If the app can't connect to Supabase, verify your `.env.local`:

```bash
cat packages/frontend/.env.local | grep SUPABASE
```

Should show:
- `NEXT_PUBLIC_SUPABASE_URL=https://pbxyhcdzdovsdlsyixsk.supabase.co`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJI...`

## Next Steps

The migration is complete! The development will continue with:

1. ✅ **Phase 1: Database** (DONE)
2. **Phase 2: Server Actions** (creating CRUD API)
3. **Phase 3: UI Components** (building React components)
4. **Phase 4: Routes** (creating /forum pages)
5. **Phase 5: Real-Time** (WebSocket subscriptions)
6. **Phase 6: Moderation Dashboard** (admin tools)

## Support

If you encounter any issues:

1. Check the Supabase Dashboard → Logs for errors
2. Check browser console (F12) for frontend errors
3. Verify authentication is working (try logging in)
4. Check that the migration ran successfully (tables exist)
