-- AI Chat System Database Migration
-- CanadaGPT - Comprehensive AI chat interface with hybrid pricing
-- Created: 2025-01-04

-- ============================================
-- SUBSCRIPTIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('free', 'basic', 'pro', 'usage_only')),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'canceled', 'suspended', 'past_due')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),

    -- Quota settings
    daily_quota INTEGER NOT NULL DEFAULT 0,
    lifetime_quota INTEGER, -- Only for free tier

    -- Overage settings
    allow_overages BOOLEAN DEFAULT TRUE,
    overage_limit DECIMAL(10,2) DEFAULT 10.00,
    current_overage_amount DECIMAL(10,2) DEFAULT 0.00,

    -- BYOK flags
    uses_byo_key BOOLEAN DEFAULT FALSE,

    -- Billing period
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    canceled_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(user_id)
);

-- Index for faster subscription lookups
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);

COMMENT ON TABLE user_subscriptions IS 'User subscription tiers and billing settings';
COMMENT ON COLUMN user_subscriptions.lifetime_quota IS 'Total queries allowed for free tier (e.g., 10)';
COMMENT ON COLUMN user_subscriptions.daily_quota IS 'Queries per day: Free=0, Basic=15, Pro=40';
COMMENT ON COLUMN user_subscriptions.uses_byo_key IS 'True if user has connected their own API key for unlimited queries';

-- ============================================
-- API KEYS TABLE (BYOK)
-- ============================================

CREATE TABLE IF NOT EXISTS user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('anthropic', 'openai')),
    encrypted_key TEXT NOT NULL,
    encryption_iv TEXT NOT NULL, -- Initialization vector for AES-GCM
    encryption_tag TEXT NOT NULL, -- Auth tag for AES-GCM
    is_active BOOLEAN DEFAULT TRUE,
    last_validated_at TIMESTAMP WITH TIME ZONE,
    validation_error TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, provider)
);

CREATE INDEX idx_user_api_keys_user_id ON user_api_keys(user_id);
CREATE INDEX idx_user_api_keys_active ON user_api_keys(user_id, is_active);

COMMENT ON TABLE user_api_keys IS 'Encrypted user API keys for BYOK (Bring Your Own Key)';
COMMENT ON COLUMN user_api_keys.encrypted_key IS 'API key encrypted with AES-256-GCM';
COMMENT ON COLUMN user_api_keys.encryption_iv IS 'Initialization vector for decryption';
COMMENT ON COLUMN user_api_keys.encryption_tag IS 'Authentication tag for GCM mode';

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New conversation',

    -- Context awareness
    context_type VARCHAR(50) CHECK (context_type IN ('general', 'mp', 'bill', 'dashboard', 'lobbying', 'spending')),
    context_id TEXT, -- MP ID, Bill number, etc.
    context_data JSONB, -- Additional context (MP name, bill title, etc.)

    -- Conversation state
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    is_pinned BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,

    -- Expiration (tier-based TTL)
    expires_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(user_id, updated_at DESC);
CREATE INDEX idx_conversations_context ON conversations(context_type, context_id);
CREATE INDEX idx_conversations_expires ON conversations(expires_at);

COMMENT ON TABLE conversations IS 'Chat conversation threads with context awareness';
COMMENT ON COLUMN conversations.context_type IS 'Page context: mp, bill, dashboard, etc.';
COMMENT ON COLUMN conversations.expires_at IS 'Free=immediate, Basic=30 days, Pro=90 days';

-- ============================================
-- MESSAGES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'function')),
    content TEXT NOT NULL,

    -- Token tracking
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_total INTEGER,

    -- AI provider info
    provider VARCHAR(20), -- 'anthropic' or 'openai'
    model VARCHAR(100), -- 'claude-sonnet-3-5-20241022', etc.
    used_byo_key BOOLEAN DEFAULT FALSE,

    -- Function calling
    function_calls JSONB, -- Array of function calls made
    function_results JSONB, -- Results from function calls

    -- Cost tracking
    cost_usd DECIMAL(10,6),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

COMMENT ON TABLE messages IS 'Individual messages in conversations with token and cost tracking';
COMMENT ON COLUMN messages.used_byo_key IS 'True if user API key was used (no cost to us)';

-- ============================================
-- USAGE LOGS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    message_id UUID REFERENCES messages(id) ON DELETE SET NULL,

    -- Date tracking
    query_date DATE NOT NULL DEFAULT CURRENT_DATE,
    query_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Token usage
    tokens_input INTEGER NOT NULL,
    tokens_output INTEGER NOT NULL,
    tokens_total INTEGER NOT NULL,

    -- Cost tracking
    cost_usd DECIMAL(10,6) NOT NULL,
    provider VARCHAR(20) NOT NULL,
    model VARCHAR(100),
    used_byo_key BOOLEAN DEFAULT FALSE,

    -- Quota tracking
    counted_against_quota BOOLEAN DEFAULT TRUE,
    was_overage BOOLEAN DEFAULT FALSE,
    overage_charge DECIMAL(10,6) DEFAULT 0.00,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_usage_logs_user_date ON usage_logs(user_id, query_date DESC);
CREATE INDEX idx_usage_logs_user_timestamp ON usage_logs(user_id, query_timestamp DESC);
CREATE INDEX idx_usage_logs_billing ON usage_logs(user_id, was_overage, query_date);

COMMENT ON TABLE usage_logs IS 'Detailed query usage logs for billing and analytics';
COMMENT ON COLUMN usage_logs.counted_against_quota IS 'False for BYOK queries';
COMMENT ON COLUMN usage_logs.was_overage IS 'True if query exceeded daily quota and was charged';

-- ============================================
-- CREDIT PACKS TABLE (Pay-as-you-go)
-- ============================================

CREATE TABLE IF NOT EXISTS credit_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,

    -- Credits
    credits_purchased INTEGER NOT NULL,
    credits_remaining INTEGER NOT NULL,
    credits_used INTEGER DEFAULT 0,

    -- Pricing
    price_paid DECIMAL(10,2) NOT NULL,
    price_per_credit DECIMAL(10,6) NOT NULL,

    -- Stripe info
    stripe_payment_intent_id VARCHAR(255),

    -- Expiration (optional - credits never expire by default)
    expires_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    depleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_credit_packs_user ON credit_packs(user_id);
CREATE INDEX idx_credit_packs_active ON credit_packs(user_id, depleted_at) WHERE depleted_at IS NULL;

COMMENT ON TABLE credit_packs IS 'Pre-purchased query credits for usage-only tier';
COMMENT ON COLUMN credit_packs.credits_remaining IS 'Must be >= 0';

-- ============================================
-- QUOTA TRACKING VIEW
-- ============================================

CREATE OR REPLACE VIEW daily_quota_usage AS
SELECT
    ul.user_id,
    ul.query_date,
    COUNT(*) as queries_today,
    SUM(ul.tokens_total) as tokens_today,
    SUM(ul.cost_usd) as cost_today,
    SUM(CASE WHEN ul.was_overage THEN 1 ELSE 0 END) as overage_queries,
    SUM(ul.overage_charge) as overage_charges,
    us.tier,
    us.daily_quota,
    us.uses_byo_key
FROM usage_logs ul
JOIN user_subscriptions us ON ul.user_id = us.user_id
WHERE ul.counted_against_quota = TRUE
GROUP BY ul.user_id, ul.query_date, us.tier, us.daily_quota, us.uses_byo_key;

COMMENT ON VIEW daily_quota_usage IS 'Real-time view of daily quota consumption per user';

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function: Check if user can make a query
CREATE OR REPLACE FUNCTION can_user_query(p_user_id UUID, OUT can_query BOOLEAN, OUT reason TEXT, OUT requires_payment BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_subscription RECORD;
    v_queries_today INTEGER;
    v_lifetime_queries INTEGER;
    v_active_key_count INTEGER;
BEGIN
    -- Get user subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- No subscription found
    IF NOT FOUND THEN
        can_query := FALSE;
        reason := 'No subscription found';
        requires_payment := TRUE;
        RETURN;
    END IF;

    -- Check subscription status
    IF v_subscription.status != 'active' THEN
        can_query := FALSE;
        reason := 'Subscription not active: ' || v_subscription.status;
        requires_payment := TRUE;
        RETURN;
    END IF;

    -- Check if user has BYOK enabled
    SELECT COUNT(*) INTO v_active_key_count
    FROM user_api_keys
    WHERE user_id = p_user_id AND is_active = TRUE;

    IF v_active_key_count > 0 THEN
        v_subscription.uses_byo_key := TRUE;
    END IF;

    -- BYOK users have unlimited queries
    IF v_subscription.uses_byo_key THEN
        can_query := TRUE;
        reason := 'Unlimited (BYOK)';
        requires_payment := FALSE;
        RETURN;
    END IF;

    -- Free tier: Check lifetime quota
    IF v_subscription.tier = 'free' THEN
        SELECT COUNT(*) INTO v_lifetime_queries
        FROM usage_logs
        WHERE user_id = p_user_id AND counted_against_quota = TRUE;

        IF v_lifetime_queries >= COALESCE(v_subscription.lifetime_quota, 10) THEN
            can_query := FALSE;
            reason := 'Free tier quota exhausted';
            requires_payment := TRUE;
            RETURN;
        END IF;

        can_query := TRUE;
        reason := 'Within free tier quota';
        requires_payment := FALSE;
        RETURN;
    END IF;

    -- Paid tiers: Check daily quota
    SELECT COUNT(*) INTO v_queries_today
    FROM usage_logs
    WHERE user_id = p_user_id
        AND query_date = CURRENT_DATE
        AND counted_against_quota = TRUE;

    -- Within daily quota
    IF v_queries_today < v_subscription.daily_quota THEN
        can_query := TRUE;
        reason := 'Within daily quota';
        requires_payment := FALSE;
        RETURN;
    END IF;

    -- Exceeded daily quota - check if overages allowed
    IF v_subscription.allow_overages THEN
        -- Check if overage limit reached
        IF v_subscription.current_overage_amount >= v_subscription.overage_limit THEN
            can_query := FALSE;
            reason := 'Overage limit reached';
            requires_payment := FALSE; -- They've hit their limit
            RETURN;
        END IF;

        can_query := TRUE;
        reason := 'Overage allowed';
        requires_payment := TRUE; -- Will be charged for overage
        RETURN;
    END IF;

    -- No overages allowed
    can_query := FALSE;
    reason := 'Daily quota exceeded';
    requires_payment := FALSE;
    RETURN;
END;
$$;

COMMENT ON FUNCTION can_user_query IS 'Check if user can make a query considering quota, BYOK, and overages';

-- Function: Track query usage
CREATE OR REPLACE FUNCTION track_query_usage(
    p_user_id UUID,
    p_conversation_id UUID,
    p_message_id UUID,
    p_tokens_input INTEGER,
    p_tokens_output INTEGER,
    p_provider VARCHAR(20),
    p_model VARCHAR(100),
    p_used_byo_key BOOLEAN,
    p_cost_usd DECIMAL(10,6)
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_subscription RECORD;
    v_queries_today INTEGER;
    v_is_overage BOOLEAN := FALSE;
    v_overage_charge DECIMAL(10,6) := 0.00;
    v_counted_against_quota BOOLEAN := TRUE;
BEGIN
    -- Get subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id;

    -- BYOK queries don't count against quota or cost
    IF p_used_byo_key THEN
        v_counted_against_quota := FALSE;
        p_cost_usd := 0.00;
    ELSE
        -- Check if this is an overage query
        SELECT COUNT(*) INTO v_queries_today
        FROM usage_logs
        WHERE user_id = p_user_id
            AND query_date = CURRENT_DATE
            AND counted_against_quota = TRUE;

        -- Free tier has no overages (shouldn't reach here)
        IF v_subscription.tier != 'free' AND v_queries_today >= v_subscription.daily_quota THEN
            v_is_overage := TRUE;
            v_overage_charge := 0.025; -- $0.025 per query

            -- Update current overage amount
            UPDATE user_subscriptions
            SET current_overage_amount = current_overage_amount + v_overage_charge,
                updated_at = NOW()
            WHERE user_id = p_user_id;
        END IF;
    END IF;

    -- Insert usage log
    INSERT INTO usage_logs (
        user_id,
        conversation_id,
        message_id,
        query_date,
        tokens_input,
        tokens_output,
        tokens_total,
        cost_usd,
        provider,
        model,
        used_byo_key,
        counted_against_quota,
        was_overage,
        overage_charge
    ) VALUES (
        p_user_id,
        p_conversation_id,
        p_message_id,
        CURRENT_DATE,
        p_tokens_input,
        p_tokens_output,
        p_tokens_input + p_tokens_output,
        p_cost_usd,
        p_provider,
        p_model,
        p_used_byo_key,
        v_counted_against_quota,
        v_is_overage,
        v_overage_charge
    );

    -- Update conversation stats
    UPDATE conversations
    SET message_count = message_count + 1,
        total_tokens = total_tokens + p_tokens_input + p_tokens_output,
        updated_at = NOW(),
        last_message_at = NOW()
    WHERE id = p_conversation_id;
END;
$$;

COMMENT ON FUNCTION track_query_usage IS 'Record query usage and handle overage billing';

-- Function: Reset monthly overage charges
CREATE OR REPLACE FUNCTION reset_monthly_overages()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_reset_count INTEGER;
BEGIN
    -- Reset overage amounts for all subscriptions
    UPDATE user_subscriptions
    SET current_overage_amount = 0.00,
        updated_at = NOW()
    WHERE current_overage_amount > 0;

    GET DIAGNOSTICS v_reset_count = ROW_COUNT;
    RETURN v_reset_count;
END;
$$;

COMMENT ON FUNCTION reset_monthly_overages IS 'Reset monthly overage charges (run via cron on billing cycle)';

-- Function: Cleanup expired conversations
CREATE OR REPLACE FUNCTION cleanup_expired_conversations()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted_count INTEGER;
BEGIN
    -- Delete expired conversations and their messages (CASCADE)
    DELETE FROM conversations
    WHERE expires_at IS NOT NULL
        AND expires_at < NOW()
        AND is_pinned = FALSE;

    GET DIAGNOSTICS v_deleted_count = ROW_COUNT;
    RETURN v_deleted_count;
END;
$$;

COMMENT ON FUNCTION cleanup_expired_conversations IS 'Delete expired conversations (run daily via cron)';

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_packs ENABLE ROW LEVEL SECURITY;

-- Subscriptions: Users can only see their own
CREATE POLICY user_subscriptions_select ON user_subscriptions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY user_subscriptions_update ON user_subscriptions
    FOR UPDATE USING (auth.uid() = user_id);

-- API Keys: Users can only see/manage their own
CREATE POLICY user_api_keys_select ON user_api_keys
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY user_api_keys_insert ON user_api_keys
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_api_keys_update ON user_api_keys
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY user_api_keys_delete ON user_api_keys
    FOR DELETE USING (auth.uid() = user_id);

-- Conversations: Users can only see their own
CREATE POLICY conversations_select ON conversations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY conversations_insert ON conversations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY conversations_update ON conversations
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY conversations_delete ON conversations
    FOR DELETE USING (auth.uid() = user_id);

-- Messages: Users can only see messages in their conversations
CREATE POLICY messages_select ON messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

CREATE POLICY messages_insert ON messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations
            WHERE conversations.id = messages.conversation_id
            AND conversations.user_id = auth.uid()
        )
    );

-- Usage Logs: Users can only see their own
CREATE POLICY usage_logs_select ON usage_logs
    FOR SELECT USING (auth.uid() = user_id);

-- Credit Packs: Users can only see their own
CREATE POLICY credit_packs_select ON credit_packs
    FOR SELECT USING (auth.uid() = user_id);

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER user_subscriptions_updated_at
    BEFORE UPDATE ON user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER user_api_keys_updated_at
    BEFORE UPDATE ON user_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- DEFAULT DATA
-- ============================================

-- Insert default free subscription for new users (via trigger)
CREATE OR REPLACE FUNCTION create_default_subscription()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO user_subscriptions (
        user_id,
        tier,
        status,
        daily_quota,
        lifetime_quota,
        allow_overages
    ) VALUES (
        NEW.id,
        'free',
        'active',
        0, -- No daily quota for free
        10, -- 10 lifetime queries
        FALSE -- No overages on free tier
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_subscription();

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Additional composite indexes
CREATE INDEX idx_usage_logs_quota_check ON usage_logs(user_id, query_date, counted_against_quota);
CREATE INDEX idx_messages_tokens ON messages(conversation_id, tokens_total);
CREATE INDEX idx_conversations_context_lookup ON conversations(user_id, context_type, context_id);

-- ============================================
-- MIGRATION COMPLETE
-- ============================================

-- Verify tables created
DO $$
DECLARE
    v_tables TEXT[] := ARRAY[
        'user_subscriptions',
        'user_api_keys',
        'conversations',
        'messages',
        'usage_logs',
        'credit_packs'
    ];
    v_table TEXT;
BEGIN
    FOREACH v_table IN ARRAY v_tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = v_table
        ) THEN
            RAISE EXCEPTION 'Table % was not created', v_table;
        END IF;
    END LOOP;

    RAISE NOTICE 'AI Chat System migration completed successfully';
    RAISE NOTICE 'Created: 6 tables, 4 functions, 1 view, RLS policies, and triggers';
END;
$$;
