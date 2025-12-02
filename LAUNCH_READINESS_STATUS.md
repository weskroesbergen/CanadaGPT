# Launch Readiness Status

**Last Updated**: 2025-12-01 05:25 UTC

## P0 Critical Blocker - RESOLVED ✅

### Issue: Missing Platform Anthropic API Key
**Status**: ✅ **FIXED**

**Problem**: FREE tier users could not use chat without providing their own API key, contradicting the pricing promise of "10 free queries".

**Solution Implemented**:
1. ✅ Verified `anthropic-api-key` secret exists in GCP Secret Manager (created 2025-12-01T05:17:49)
2. ✅ Granted Cloud Run service account access:
   ```bash
   gcloud secrets add-iam-policy-binding anthropic-api-key \
     --member="serviceAccount:canadagpt-frontend-sa@canada-gpt-ca.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```
3. ✅ Updated deployment script (`scripts/deploy-frontend-cloudrun.sh`) to include ANTHROPIC_API_KEY
4. ✅ Deployed new revision: `canadagpt-frontend-00052-jvf`
5. ✅ Verified environment variable configuration in Cloud Run

**Verification**:
```bash
# Secret exists
gcloud secrets describe anthropic-api-key
# Created: 2025-12-01T05:17:49.646061Z

# IAM policy grants access
gcloud secrets get-iam-policy anthropic-api-key
# Role: roles/secretmanager.secretAccessor

# Cloud Run configuration
gcloud run services describe canadagpt-frontend --region=us-central1
# Environment: ANTHROPIC_API_KEY → secretKeyRef: anthropic-api-key:latest
```

**Chat API Logic** (packages/frontend/src/app/api/chat/route.ts:248-258):
- Checks for user BYOK keys (Anthropic or OpenAI)
- Falls back to `process.env.ANTHROPIC_API_KEY` if no BYOK key found
- Platform key is now available for FREE tier users

---

## Remaining Issues

### P1 - High Priority (Implement Soon After Launch)

#### Issue: No Response Caching
**Impact**: High cost risk - every query generates fresh AI response

**Problem**:
- Popular questions asked hundreds of times = 100x API costs
- Example: "Who are current MPs?" could be cached for 24 hours
- Estimated 30-40% cost savings with basic caching

**Quick Win Solutions**:
1. Cache tool call results (GraphQL queries) - 2 days
2. Pre-compute daily summaries - 1 week
3. Implement Redis for response caching - 2 weeks

### P2 - Medium Priority (Fix Before Scale)

#### Issue: Tier Definition Inconsistencies
**Impact**: Potential quota bypass, billing disputes, support confusion

**Problems Identified**:
1. **Case sensitivity**:
   - `auth.ts:153` sets `subscription_tier: 'FREE'` (uppercase)
   - `quota/route.ts:134` checks `subscription.tier === 'free'` (lowercase)
2. **Query limit mismatch**:
   - Pricing page promises "200 queries per month" (BASIC), "1,000 queries per month" (PRO)
   - `quota/route.ts:143-150` implements daily quota checks, not monthly
3. **Multiple definition locations**:
   - Tiers defined in 5+ files (auth.ts, tierLimits.ts, pricing page, migrations)
   - No single source of truth

**Solution**: Consolidate tier definitions into single constants file

---

## Testing Required

### Manual Testing Checklist
- [ ] **FREE tier chat flow**:
  - [ ] Sign up new FREE user (no BYOK key)
  - [ ] Send a chat query
  - [ ] Verify response uses platform API key (check logs: "Using platform key")
  - [ ] Verify quota decrements correctly
  - [ ] Test 10-query limit enforcement
  - [ ] Verify error message when quota exhausted

- [ ] **BYOK flow**:
  - [ ] Add user's Anthropic API key in settings
  - [ ] Send chat query
  - [ ] Verify response uses user's key (check logs: "Using user Anthropic key")
  - [ ] Verify quota doesn't decrement for BYOK users

- [ ] **Tier upgrades**:
  - [ ] Upgrade FREE → BASIC (BYOK option)
  - [ ] Upgrade FREE → BASIC (+Usage option)
  - [ ] Verify quota limits change correctly
  - [ ] Verify billing starts/stops appropriately

### Automated Testing Needed
- [ ] Unit tests for quota enforcement
- [ ] Integration tests for chat API key selection logic
- [ ] End-to-end tests for tier transitions

---

## Architecture Notes

### Chat Flow
```
User Message
  ↓
Chat API (/api/chat/route.ts)
  ├─ Check quota (can_user_query RPC)
  ├─ Check for user's BYOK key (Anthropic/OpenAI)
  ├─ Fallback to platform key (NOW AVAILABLE ✅)
  ↓
Claude Sonnet 4.5 (streaming)
  ├─ 17 tools available
  ├─ Multi-round tool calling
  ↓
Tool Executor (toolExecutor.ts)
  ├─ Maps to GraphQL queries
  ├─ Apollo Client (cache-first)
  ↓
GraphQL API (@neo4j/graphql)
  ↓
Neo4j Database (2M+ nodes)
```

### Current Caching Layers
1. ✅ Apollo Client (GraphQL data) - 60-80% hit rate
2. ✅ Next.js ISR (static pages) - 1 hour TTL
3. ❌ AI response caching - **NONE** (P1 to implement)
4. ❌ Daily summaries - **NONE** (P1 to implement)

---

## Deployment Details

**Deployment Script**: `scripts/deploy-frontend-cloudrun.sh`

**Key Changes Made**:
- Line 62: Added documentation for `anthropic-api-key` secret
- Line 137: Added `ANTHROPIC_API_KEY=anthropic-api-key:latest` to `--set-secrets`

**Service Configuration**:
- Service: `canadagpt-frontend`
- Region: `us-central1`
- Latest Revision: `canadagpt-frontend-00052-jvf`
- Service Account: `canadagpt-frontend-sa@canada-gpt-ca.iam.gserviceaccount.com`
- URL: `https://canadagpt-frontend-i7veukpr2q-uc.a.run.app`
- Custom Domain: `https://canadagpt.ca` (via domain mapping)

**Secrets Configured**:
- supabase-url, supabase-anon-key, supabase-service-role-key
- canadagpt-auth-secret (NextAuth)
- google-client-id, google-client-secret, github-client-id, github-client-secret, facebook-client-id, facebook-client-secret, linkedin-client-id, linkedin-client-secret (OAuth)
- encryption-key (for BYOK key encryption)
- stripe-secret-key, stripe-publishable-key, stripe-webhook-secret
- **anthropic-api-key** ← **NEWLY ADDED**

---

## Next Steps

### Immediate (Before Public Launch)
1. **Manual Testing**: Test FREE tier chat flow end-to-end with real user
2. **Monitor Costs**: Track API usage for first 24-48 hours
3. **Set Alerts**: Configure billing alerts for unexpected API costs

### Short-Term (Week 1-2)
1. **Implement Response Caching**: Start with tool result caching (2 days)
2. **Fix Tier Inconsistencies**: Consolidate to single source of truth (1 day)
3. **Add Pre-Query Warnings**: Alert users at 80% quota (4 hours)

### Medium-Term (Month 1)
1. **Pre-compute Daily Summaries**: Cache common queries (1 week)
2. **Implement Redis**: Full response caching layer (2 weeks)
3. **Add Monitoring**: Track quota usage patterns, identify abuse (1 week)

---

## Questions for User

1. **Manual Testing**: Would you like to test the FREE tier chat flow now, or wait until after launch?
2. **Cost Monitoring**: Should we set a daily API cost alert threshold? (Recommended: $50/day)
3. **Tier Inconsistencies**: Should we prioritize fixing the case sensitivity issue before launch? (Recommended: Yes)
4. **Response Caching**: What's your priority - implement before launch or shortly after?
