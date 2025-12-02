# Tool Result Caching Implementation

**Implemented**: 2025-12-01
**Priority**: P1 - High Priority for Cost Savings

## Overview

Implemented an in-memory LRU (Least Recently Used) cache for tool execution results to reduce redundant GraphQL queries and AI API costs. Expected **30-40% cost savings** based on typical query patterns.

## Architecture

### Cache Location
- **File**: `packages/frontend/src/lib/toolCache.ts`
- **Integration**: `packages/frontend/src/lib/toolExecutor.ts`
- **Type**: In-memory, per-instance cache
- **Strategy**: LRU eviction with TTL (Time-To-Live)

### How It Works

```
User Query → Chat API → Tool Call
                         ↓
                  Check Cache (toolCache.get)
                         ↓
            ┌────────────┴────────────┐
            │                         │
         Cache HIT              Cache MISS
            │                         │
     Return cached result    Execute GraphQL query
            │                         │
            └─────────────┬───────────┘
                          ↓
                  Cache result (toolCache.set)
                          ↓
                   Return to Claude
```

## TTL Configuration

Different tool types have different TTLs based on data freshness requirements:

| Tool Category | TTL | Rationale |
|--------------|-----|-----------|
| **MPs, Committees** | 24 hours | Mostly static data |
| **Bills** | 6 hours | Static once passed |
| **Hansard Search** | 30 minutes | Search results vary |
| **Recent Debates** | 1 hour | Semi-static, updated daily |
| **Lobby Data** | 6 hours | Rarely changes |
| **Scorecards/Aggregations** | 1 hour | Computed data |
| **Navigation** | No cache | Just URL building |

### TTL Examples

```typescript
const TOOL_TTL_CONFIG: Record<string, number> = {
  'search_mps': 24 * 60 * 60,    // 24 hours
  'get_mp': 24 * 60 * 60,         // 24 hours
  'search_hansard': 30 * 60,      // 30 minutes
  'get_recent_debates': 60 * 60,  // 1 hour
  'get_bill': 6 * 60 * 60,        // 6 hours
  // ... see toolCache.ts for complete list
};
```

## Cache Key Generation

Cache keys are generated using SHA-256 hash of `toolName` + sorted parameters:

```typescript
// Example:
toolName = "search_hansard"
params = { searchTerm: "climate change", limit: 10 }

// Keys are order-independent:
{ searchTerm: "climate", limit: 10 } === { limit: 10, searchTerm: "climate" }
```

This ensures consistent cache hits regardless of parameter order.

## Cache Configuration

- **Max Size**: 1,000 entries before LRU eviction
- **Eviction**: Least Recently Used (LRU) policy
- **Cleanup**: Automatic expired entry cleanup every 100 requests
- **Persistence**: In-memory only (cleared on service restart)

## Statistics & Monitoring

### API Endpoint

**GET** `/api/chat/cache-stats` - Returns cache statistics

```json
{
  "success": true,
  "stats": {
    "hits": 234,
    "misses": 156,
    "evictions": 3,
    "size": 87,
    "hitRate": 60.0
  },
  "timestamp": "2025-12-01T05:30:00Z"
}
```

**DELETE** `/api/chat/cache-stats` - Clears the cache

### Logging

Cache operations are logged to console:

```
[ToolCache] MISS: search_hansard { params: { searchTerm: "climate" } }
[ToolCache] SET: search_hansard (TTL: 1800s) { params: ... }
[ToolCache] HIT: search_hansard (age: 45s) { params: ... }
[ToolCache] Cleaned 12 expired entries
```

## Cost Savings Calculation

### Without Caching
- Popular query asked 100 times/day
- Each query = 1 tool call = 1 GraphQL query
- Total: 100 GraphQL queries

### With Caching (30-min TTL)
- First query: Cache MISS → GraphQL query
- Next 99 queries within 30 minutes: Cache HIT → No GraphQL query
- Total: ~3-4 GraphQL queries (assuming 24-hour spread)
- **Savings: 96%+ for popular queries**

### Realistic Estimates
- Assuming 30% of queries are repeats within TTL window
- **Expected savings: 30-40% reduction in GraphQL queries**
- **Cost impact**: $X/month reduction in API costs (TBD after monitoring)

## Files Modified

1. **packages/frontend/src/lib/toolCache.ts** (NEW)
   - Cache implementation with LRU and TTL

2. **packages/frontend/src/lib/toolExecutor.ts** (MODIFIED)
   - Added cache check before tool execution (line 44-47)
   - Added cache storage after successful execution (line 356-358)
   - Changed all tool cases to use `result` variable + `break` pattern

3. **packages/frontend/src/app/api/chat/cache-stats/route.ts** (NEW)
   - Cache statistics API endpoint

## Testing

### Local Testing

Test script: `/tmp/test-cache.ts`

```bash
npx tsx /tmp/test-cache.ts
```

**Results**:
- ✅ Cache miss detection works
- ✅ Cache hit detection works
- ✅ Parameter order independence works
- ✅ Statistics tracking works
- ✅ Hit rate calculation correct

### Production Testing

After deployment, monitor via:

```bash
# Check cache stats
curl -H "Authorization: Bearer $TOKEN" \
  https://canadagpt.ca/api/chat/cache-stats

# Clear cache if needed
curl -X DELETE -H "Authorization: Bearer $TOKEN" \
  https://canadagpt.ca/api/chat/cache-stats
```

## Deployment

### Build & Deploy

```bash
cd packages/frontend
./scripts/deploy-frontend-cloudrun.sh
```

**Deployment includes**:
1. New `toolCache.ts` module
2. Modified `toolExecutor.ts` with caching
3. New cache stats API endpoint

### Verification Steps

1. ✅ TypeScript compilation passes
2. ✅ Local test passes
3. 🔄 Deploy to Cloud Run
4. ⏳ Monitor cache hit rate in production logs
5. ⏳ Verify cost reduction after 7 days

## Future Enhancements

### Short-Term (Week 1-2)
1. **Add Redis caching**: Share cache across Cloud Run instances
2. **Pre-compute daily summaries**: Cache "What happened today?" queries
3. **Cache warming**: Pre-populate cache with popular queries on startup

### Medium-Term (Month 1)
1. **Intelligent TTL**: Adjust TTLs based on query patterns
2. **Cache invalidation**: Smart cache clearing when new data ingested
3. **A/B testing**: Measure exact cost savings vs non-cached baseline

### Long-Term (Month 2+)
1. **Distributed caching**: Redis cluster for high availability
2. **Cache analytics**: Dashboard for cache performance monitoring
3. **ML-based caching**: Predict and pre-cache likely queries

## Known Limitations

1. **Instance-local**: Each Cloud Run instance has its own cache (no sharing)
   - **Impact**: Lower hit rate with multiple instances
   - **Solution**: Implement Redis in future

2. **Cold starts**: Cache cleared on instance restart
   - **Impact**: Temporary hit rate drop after deployment
   - **Solution**: Implement cache warming

3. **Memory usage**: 1,000 entries ≈ 5-10MB RAM
   - **Impact**: Minimal on 512Mi instances
   - **Solution**: Monitor and adjust MAX_CACHE_SIZE if needed

## Monitoring Checklist

After deployment, monitor for 7 days:

- [ ] **Cache hit rate**: Target ≥ 40% after 24 hours
- [ ] **Memory usage**: Ensure < 300Mi (well under 512Mi limit)
- [ ] **Response times**: Verify cached responses are faster
- [ ] **Cost reduction**: Track GraphQL query count vs baseline
- [ ] **Error rate**: Ensure no increase in errors

## Questions & Decisions

### Q: Why in-memory instead of Redis?
**A**: Quick win for immediate cost savings. Redis adds complexity and latency. We can migrate to Redis later if needed.

### Q: What if cache hit rate is low?
**A**: Analyze logs to identify:
1. Are TTLs too short? Increase for static data.
2. Are queries too varied? Add query normalization.
3. Is traffic spread across many instances? Implement Redis.

### Q: How to handle cache invalidation?
**A**: Currently: TTL-based expiration only. Future: Add manual invalidation via DELETE endpoint or ingestion pipeline triggers.

## References

- Original pre-launch review: `/Users/matthewdufresne/.claude/plans/floofy-greeting-spring.md`
- Launch readiness status: `/Users/matthewdufresne/CanadaGPT/LAUNCH_READINESS_STATUS.md`
- Tool executor: `packages/frontend/src/lib/toolExecutor.ts`
- Cache implementation: `packages/frontend/src/lib/toolCache.ts`
