# AI Chat Interface Implementation Plan

**Status:** Planning Complete ✅ | Ready for Implementation
**Target:** CanadaGPT - Canadian Government Accountability Platform
**Feature:** AI-powered chat interface with hybrid pricing model

---

## Executive Summary

We're implementing an AI chat assistant that allows users to query Canadian government data through natural language. The system will feature:

- **Floating chat widget** accessible from any page
- **Context-aware prompts** on individual pages (MPs, Bills, etc.)
- **Hybrid pricing model**: Profitable quotas + BYOK + usage-based billing
- **Multi-provider support**: Anthropic Claude (primary) + OpenAI GPT
- **Smart quota management**: Free trial → Paid tiers → BYO Key for unlimited

---

## Pricing Structure (Final)

| Tier | Price | Our Infrastructure | BYOK | Overage |
|------|-------|-------------------|------|---------|
| **Free** | $0 | 10 lifetime queries | ❌ | ❌ |
| **Basic** | $9.99/mo | 15/day (450/mo) | ✅ Unlimited | $0.025/query |
| **Pro** | $29.99/mo | 40/day (1200/mo) | ✅ Unlimited | $0.025/query |
| **Usage-Only** | Pay-per-use | 0 included | ✅ Optional | $0.025/query |

**Economics:**
- Cost per query: $0.016 (Claude Sonnet 3.5)
- Revenue per query: $0.025 (56% profit margin)
- All tiers profitable at full utilization
- BYOK adoption drives 90%+ margins

---

## Implementation Phases

### Phase 1: Foundation & Database (Day 1-2)
- [ ] Set up Supabase and database migrations
- [ ] Install required dependencies
- [ ] Create database schema for:
  - User subscriptions
  - API key management (BYOK)
  - Conversations and messages
  - Usage tracking and billing
  - Credit packs (pay-as-you-go)

### Phase 2: Core Chat Infrastructure (Day 3-4)
- [ ] Create chat context and state management
- [ ] Build quota checking system
- [ ] Implement usage tracking middleware
- [ ] Create API encryption for BYOK keys

### Phase 3: Chat UI Components (Day 5-6)
- [ ] Build core chat UI components:
  - ChatMessage
  - ChatInput
  - ChatHistory
  - ChatSuggestions
- [ ] Create floating chat widget
- [ ] Add animations and UX polish

### Phase 4: AI Integration (Day 7-8)
- [ ] Create chat API route with streaming
- [ ] Implement context injection system
- [ ] Add function calling for data queries
- [ ] Connect to GraphQL backend

### Phase 5: BYOK & Billing (Day 9-10)
- [ ] Build API key management UI
- [ ] Implement secure key storage
- [ ] Create usage billing system
- [ ] Add Stripe integration

### Phase 6: Context-Aware Features (Day 11-12)
- [ ] Add context-aware prompts to individual pages:
  - MP detail pages
  - Bill detail pages
  - Dashboard
  - Lobbying page
- [ ] Implement smart suggestions
- [ ] Add citation linking

### Phase 7: Advanced Features (Day 13-14)
- [ ] Conversation history and search
- [ ] Export functionality (CSV/JSON/PDF)
- [ ] Share conversation links (Pro)
- [ ] Usage analytics dashboard

### Phase 8: Testing & Polish (Day 15)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation
- [ ] Launch preparation

---

## Technical Stack

**Frontend:**
- Next.js 15 (App Router)
- React 18
- TailwindCSS
- Framer Motion (animations)

**AI & Streaming:**
- Vercel AI SDK (`ai` package)
- Anthropic SDK (`@anthropic-ai/sdk`)
- OpenAI SDK (`openai`)

**Backend:**
- Supabase (auth, database, realtime)
- PostgreSQL (data storage)
- GraphQL (data queries)

**Billing:**
- Stripe (subscriptions & invoices)
- Supabase functions (quota enforcement)

---

## Database Schema Overview

```
user_subscriptions
├── tier (free/basic/pro)
├── status (active/canceled)
├── allow_overages
└── overage_limit

user_api_keys
├── provider (anthropic/openai)
├── encrypted_key
└── is_active

conversations
├── title
├── context_type (mp/bill/general)
├── context_id
└── expires_at (tier-based TTL)

messages
├── role (user/assistant/system)
├── content
├── tokens_used
└── provider

usage_logs
├── query_date
├── tokens_input/output
├── cost_usd
└── provider

credit_packs (PAYG)
├── credits_purchased
├── credits_remaining
└── expires_at (never)
```

---

## Key Features Breakdown

### 1. Floating Chat Widget

**Behavior:**
- Fixed position bottom-right corner
- Keyboard shortcut: `Cmd/Ctrl + K`
- Minimizes to button, expands to panel
- Shows quota status badge
- Persists across page navigation

**States:**
- Collapsed: Small button with unread indicator
- Expanded: Full chat interface (400px width)
- Loading: Skeleton UI with pulse animation
- Error: Retry button with error message

### 2. Context-Aware Prompts

**MP Detail Page:**
```
Context: Current MP's data (name, party, votes, bills, expenses)
Suggestions:
- "What bills has this MP sponsored?"
- "How does their spending compare to party average?"
- "Show me their voting record on climate bills"
```

**Bill Detail Page:**
```
Context: Bill data (number, title, status, votes, sponsor)
Suggestions:
- "Summarize this bill in simple terms"
- "Who is lobbying on this bill?"
- "What's the voting record?"
```

### 3. BYOK (Bring Your Own Key)

**Flow:**
1. User goes to Settings → API Keys
2. Clicks "Connect Anthropic Claude" or "Connect OpenAI"
3. Enters API key (validated with test query)
4. Key encrypted and stored in database
5. All future queries use their key (unlimited)

**Benefits:**
- Unlimited queries for $9.99-29.99/mo subscription
- User pays their API provider directly (~$0.015/query)
- We profit from subscription without AI costs
- User maintains full control of their API usage

### 4. Usage-Based Billing

**Overage Handling:**
```
User hits daily quota → Show modal:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Daily quota reached (15/15)

Continue chatting?
✓ Additional queries: $0.025 each
✓ Billed at end of month
✓ $10 default limit (adjustable)

OR get unlimited:
• Connect your API key 🚀
• Upgrade to Pro ($29.99/mo)

[Continue with overage] [Connect API]
```

**Monthly Bill Example:**
```
Basic Plan                     $9.99
40 overage queries @ $0.025    $1.00
────────────────────────────
Total                          $10.99

💡 Save: Connect API key for unlimited
```

---

## AI Provider Configuration

### Anthropic Claude (Primary)

**Model:** Claude Sonnet 3.5 (`claude-sonnet-3-5-20241022`)
**Pricing:** $3/M input tokens, $15/M output tokens
**Features:**
- Excellent for complex queries
- Strong reasoning capabilities
- Good with Canadian context
- Function calling support

### OpenAI GPT (Alternative)

**Model:** GPT-4 Turbo (`gpt-4-turbo-preview`)
**Pricing:** $10/M input tokens, $30/M output tokens
**Features:**
- Alternative for BYOK users
- Strong general knowledge
- Good function calling
- Faster response times

---

## System Prompts

### Base System Prompt

```
You are an AI assistant for CanadaGPT, a Canadian government accountability platform.

You help users understand Canadian parliamentary data including:
- Members of Parliament (MPs), their voting records, expenses, and activities
- Federal bills and legislation through Parliament
- Parliamentary votes and debates
- Lobbying activity and corporate influence
- Government spending and transparency

Guidelines:
- Be accurate and cite sources with links when possible
- Provide balanced, non-partisan analysis
- Explain complex legislative processes in simple terms
- Highlight accountability issues when relevant
- Use Canadian spelling and terminology
- Format responses with markdown for readability

When you mention specific entities (MPs, bills, etc.), include links:
- MP: [MP Name](/mps/mp-id)
- Bill: [Bill C-123](/bills/45-1/C-123)
- Vote: [Vote on Bill C-123](/votes/vote-id)
```

### Context Templates

**MP Context:**
```
Current page context: MP {name} ({party}, {riding})
Recent votes: {recent_votes}
Sponsored bills: {sponsored_bills}
Quarterly expenses: ${total_expenses}

The user is viewing this MP's profile page.
```

**Bill Context:**
```
Current page context: Bill {number} ({session})
Title: {title}
Status: {status}
Sponsor: {sponsor_name} ({party})
Recent votes: {vote_summary}

The user is viewing this bill's detail page.
```

---

## Function Calling / Tools

The AI will have access to these functions to query data:

```typescript
{
  name: "searchMPs",
  description: "Search for Members of Parliament by name, party, or riding",
  parameters: { searchTerm, party, current, limit }
}

{
  name: "getMPDetails",
  description: "Get detailed information about a specific MP",
  parameters: { mpId }
}

{
  name: "searchBills",
  description: "Search for federal bills by number, title, or keywords",
  parameters: { searchTerm, status, session, limit }
}

{
  name: "getBillDetails",
  description: "Get detailed information about a specific bill",
  parameters: { billNumber, session }
}

{
  name: "searchLobbyingActivity",
  description: "Search lobbying registrations and communications",
  parameters: { clientName, subjectMatter, limit }
}

{
  name: "getMPExpenses",
  description: "Get quarterly expense data for an MP",
  parameters: { mpId, fiscalYear, quarter }
}
```

---

## Security Considerations

### API Key Encryption

```typescript
// Encrypt before storing
const encryptApiKey = (key: string): string => {
  const cipher = crypto.createCipheriv(
    'aes-256-gcm',
    process.env.ENCRYPTION_KEY,
    iv
  );
  return cipher.update(key, 'utf8', 'hex');
};

// Decrypt when using
const decryptApiKey = (encrypted: string): string => {
  const decipher = crypto.createDecipheriv(
    'aes-256-gcm',
    process.env.ENCRYPTION_KEY,
    iv
  );
  return decipher.update(encrypted, 'hex', 'utf8');
};
```

### Rate Limiting

- Per-user quota checks before each query
- IP-based rate limiting (100 requests/hour for anonymous)
- Exponential backoff for retries
- Abuse detection (unusual usage patterns)

### Data Privacy

- Conversation history expires based on tier
- BYOK queries never logged by us
- Personal data never sent to AI providers
- Row-level security on all tables

---

## Success Metrics

**Adoption:**
- [ ] 30% of authenticated users try chat
- [ ] 15% become regular users (5+ queries/week)
- [ ] 10% convert to paid tiers

**Revenue:**
- [ ] BYOK adoption: 40-60% of paid users
- [ ] Average overage: $2-5/mo per Basic user
- [ ] Pro tier upgrade rate: 5% of Basic users

**Quality:**
- [ ] 85%+ query accuracy
- [ ] <2s average response time
- [ ] <5% error rate

---

## Next Steps

1. **Review & Approve**: Confirm pricing model and feature set
2. **Environment Setup**: Configure Supabase project
3. **Start Phase 1**: Database migrations and schema
4. **Iterative Development**: Build and test each phase
5. **Beta Launch**: Limited rollout to test users
6. **Full Launch**: Public release with marketing

---

## Resources Required

**Development Time:** 15 days (full-time)
**Infrastructure Costs:**
- Supabase: Free tier initially, $25/mo at scale
- AI costs: $0.016/query (pass-through with BYOK)
- Hosting: Vercel (existing)

**External Services:**
- Anthropic API (primary)
- OpenAI API (alternative)
- Stripe (billing)

---

## Questions & Decisions

- [ ] Which AI model should be default? (Claude Sonnet 3.5 ✅)
- [ ] Allow anonymous chat for Free tier? (Yes, 10 lifetime queries ✅)
- [ ] Enable voice input? (Phase 2 feature, not MVP)
- [ ] Support conversation sharing? (Pro tier only ✅)
- [ ] Should we support fine-tuned models? (Future consideration)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-04
**Status:** Ready for Implementation ✅
