# Architecture Cleanup Status

**Last Updated**: 2025-11-08 05:20 UTC

## Overview

Cleaning up the FedMCP architecture to clearly separate concerns:
- **Supabase**: User auth, profiles, and forum (user-generated content ONLY)
- **Neo4j**: All parliamentary data (MPs, bills, Hansard, votes, lobbying)
- **Ingestion VM**: Bulk data processing with local PostgreSQL mirror

## Completed ✅

### 1. Architecture Documentation
- ✅ Created `PRODUCTION_ARCHITECTURE.md` - comprehensive system architecture
- ✅ Created `PRODUCTION_OAUTH_SETUP.md` - OAuth provider setup guide
- ✅ Documented actual architecture (Cloud Run + Neo4j VM, not "Production VM")
- ✅ Clarified data separation (Supabase = auth/users/forums, Neo4j = parliamentary)

### 2. Hansard Data Import
- ✅ Confirmed 3.67M statements in Ingestion VM PostgreSQL
- ✅ Started import from Ingestion VM → Neo4j (3.37M missing statements)
- ✅ Running in tmux session: `hansard_import` on canadagpt-ingestion VM
- ✅ ETA: 2-3 hours from 04:43 UTC
- ✅ Removed local Mac PostgreSQL (freed 7.4GB)

### 3. Supabase Cleanup Migration
- ✅ Created migration: `supabase/migrations/20251108050000_cleanup_parliamentary_tables.sql`
- ✅ Migration committed to git and pushed to remote
- ✅ Migration will drop:
  - `hansards_statement` (3.67M records - redundant with Ingestion VM)
  - `hansards_document` (~25K records - redundant)
  - `bills_bill` (1.2K records - now in Neo4j)
  - `mps_mp`, `mps_party`, `mps_riding` (MP data - now in Neo4j)
- ✅ Adds schema comment documenting architecture

### 4. Frontend Deployment
- ✅ Fixed GitHub Actions workflow (added NEXT_PUBLIC_GRAPHQL_URL)
- ✅ Triggered automated deployment for parliament-buildings.jpg image
- ✅ Deployment running via GitHub Actions

### 5. Hansard UI Improvements
- ✅ Fixed threaded speech cards (party colors, readability)
- ✅ Fixed MP photo display and cropping
- ✅ Improved text contrast on colored backgrounds

## Pending ⏳

### 1. Apply Supabase Cleanup Migration
**Status**: Migration created and committed, pending application

**Why Pending**: Supabase CLI connection issues (pooler refusing connections)

**Options to Complete**:

#### Option A: Wait and Retry CLI
```bash
cd /Users/matthewdufresne/FedMCP
supabase db push
```

#### Option B: Apply via Supabase Dashboard (Manual)
1. Go to https://supabase.com/dashboard/project/lbyqmjcqbwfeglfkiqpd/editor
2. Click **SQL Editor**
3. Run this SQL:
```sql
-- Drop hansards tables (now in Ingestion VM → Neo4j)
DROP TABLE IF EXISTS public.hansards_statement CASCADE;
DROP TABLE IF EXISTS public.hansards_document CASCADE;

-- Drop bills tables (now in Neo4j only)
DROP TABLE IF EXISTS public.bills_bill CASCADE;

-- Drop MPs tables (now in Neo4j only)
DROP TABLE IF EXISTS public.mps_mp CASCADE;
DROP TABLE IF EXISTS public.mps_party CASCADE;
DROP TABLE IF EXISTS public.mps_riding CASCADE;

-- Add comment to document architecture
COMMENT ON SCHEMA public IS 'User-generated content only. Parliamentary data stored in Neo4j graph database.';
```
4. Then mark migration as applied:
```bash
supabase migration repair --status applied 20251108050000
```

**Storage Freed**: ~3-5 GB after cleanup (3.67M+ records removed)

### 2. OAuth Provider Setup
**Status**: Documentation created, providers not yet configured

**Required**: Set up OAuth applications for production at https://canadagpt.ca

**Providers to Configure**:
- [ ] Google OAuth (via Google Cloud Console)
- [ ] GitHub OAuth (via GitHub Developer Settings)
- [ ] Facebook OAuth (via Facebook Developers)
- [ ] LinkedIn OAuth (via LinkedIn Developers)

**Callback URL** (for all providers):
```
https://lbyqmjcqbwfeglfkiqpd.supabase.co/auth/v1/callback
```

**Guide**: See `PRODUCTION_OAUTH_SETUP.md` for step-by-step instructions

### 3. Monitor Hansard Import Completion
**Status**: Running on ingestion VM

**Check Progress**:
```bash
# SSH to ingestion VM
gcloud compute ssh canadagpt-ingestion --zone=us-central1-a

# Attach to tmux session
tmux attach -t hansard_import
```

**When Complete**:
1. Verify statement count in Neo4j: `MATCH (s:Statement) RETURN count(s)`
2. Should be ~3.67M statements
3. Stop ingestion VM to save costs ($100/mo → $5/mo storage only)

### 4. Verify Frontend Deployment
**Status**: GitHub Actions running

**Check**:
- Visit https://canadagpt.ca and verify parliament-buildings.jpg displays
- Check https://github.com/northernvariables/FedMCP/actions for deployment status

## Data Architecture Summary

### Before Cleanup
```
Supabase:
├── auth.* (users, sessions)
├── public.profiles
├── public.forums*
├── hansards_statement (3.67M) ❌ REDUNDANT
├── hansards_document (25K) ❌ REDUNDANT
├── bills_bill (1.2K) ❌ REDUNDANT
└── mps_* (338) ❌ REDUNDANT

Neo4j:
├── Statement (297K) ⚠️ INCOMPLETE (missing 3.37M)
├── Document (25K) ✅
├── Bill (1.2K) ✅
├── MP (338) ✅
└── Other nodes ✅

Ingestion VM:
└── PostgreSQL: openparliament_temp (3.67M statements) ✅
```

### After Cleanup (Target State)
```
Supabase:
├── auth.* (users, sessions) ✅
├── public.profiles ✅
└── public.forums* ✅

Neo4j:
├── Statement (3.67M) ✅ COMPLETE
├── Document (25K) ✅
├── Bill (1.2K) ✅
├── MP (338) ✅
└── Other nodes ✅

Ingestion VM:
└── PostgreSQL: openparliament_temp (staging mirror)
    Can be stopped when idle to save $95/month
```

## Cost Impact

**Current Monthly Costs**:
- Cloud Run (Frontend): $0-5 (scale-to-zero)
- Cloud Run (GraphQL): $0-10 (scale-to-zero)
- Neo4j VM: ~$50
- Ingestion VM (running): ~$100
- Supabase (Free tier): $0
- **Total: ~$150-165/month**

**After Cleanup**:
- Cloud Run (Frontend): $0-5
- Cloud Run (GraphQL): $0-10
- Neo4j VM: ~$50
- Ingestion VM (stopped): ~$5 (storage only)
- Supabase (Free tier): $0
- **Total: ~$55-70/month**

**Savings**: ~$95/month by stopping ingestion VM when idle

## Next Steps

1. **Immediate**: Monitor Hansard import completion (2-3 hours from 04:43 UTC)
2. **Short-term**: Apply Supabase cleanup migration (via dashboard or CLI retry)
3. **Short-term**: Set up OAuth providers using guide (see PRODUCTION_OAUTH_SETUP.md)
4. **After import**: Stop ingestion VM to save costs
5. **Ongoing**: Monitor Neo4j storage and consider upgrade if needed

## Files Modified

- `PRODUCTION_ARCHITECTURE.md` - Created comprehensive architecture docs
- `PRODUCTION_OAUTH_SETUP.md` - Created OAuth setup guide
- `supabase/migrations/20251108050000_cleanup_parliamentary_tables.sql` - Created cleanup migration
- `.github/workflows/deploy-frontend.yml` - Fixed missing NEXT_PUBLIC_GRAPHQL_URL
- `packages/frontend/src/components/hansard/ThreadedSpeechCard.tsx` - UI improvements
- `ARCHITECTURE_CLEANUP_STATUS.md` - This status document

---

**Maintained By**: Claude Code
**Session Date**: 2025-11-08
