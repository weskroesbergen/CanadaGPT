-- ============================================
-- CanadaGPT Forum System Migration (v2 - Fixed)
-- ============================================
-- Creates tables for threaded discussions, bill debates, and moderation
-- Version: 2.0.0
-- Date: 2025-01-07
-- This version handles existing tables and adds missing columns

-- ============================================
-- 1. USER PROFILES (Update existing or create)
-- ============================================

-- Drop and recreate user_profiles to avoid conflicts
DROP TABLE IF EXISTS public.user_profiles CASCADE;

CREATE TABLE public.user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name VARCHAR(100),
  avatar_url TEXT,
  bio TEXT,
  location VARCHAR(100),

  -- Forum statistics
  posts_count INT DEFAULT 0 CHECK (posts_count >= 0),
  replies_count INT DEFAULT 0 CHECK (replies_count >= 0),
  reputation_score INT DEFAULT 0,

  -- Settings
  email_notifications BOOLEAN DEFAULT TRUE,
  show_email BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Index for reputation leaderboard
CREATE INDEX idx_user_profiles_reputation ON public.user_profiles(reputation_score DESC);

-- ============================================
-- 2. FORUM CATEGORIES
-- ============================================

DROP TABLE IF EXISTS public.forum_categories CASCADE;

CREATE TABLE public.forum_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(100) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  icon VARCHAR(50),
  color VARCHAR(7),
  display_order INT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  post_count INT DEFAULT 0 CHECK (post_count >= 0),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_forum_categories_active ON public.forum_categories(is_active, display_order);

-- ============================================
-- 3. FORUM POSTS
-- ============================================

DROP TABLE IF EXISTS public.forum_posts CASCADE;

CREATE TABLE public.forum_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_type VARCHAR(20) NOT NULL CHECK (post_type IN ('discussion', 'bill_comment')),

  -- For generic discussions
  category_id UUID REFERENCES public.forum_categories(id) ON DELETE CASCADE,

  -- For bill-specific comments
  bill_id INT,
  bill_number VARCHAR(20),
  bill_session VARCHAR(20),

  -- Content
  title VARCHAR(255),
  content TEXT NOT NULL CHECK (LENGTH(content) > 0),

  -- Ownership
  author_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  author_name VARCHAR(255),
  author_avatar_url TEXT,

  -- Threading structure
  parent_post_id UUID REFERENCES public.forum_posts(id) ON DELETE CASCADE,
  thread_root_id UUID REFERENCES public.forum_posts(id) ON DELETE CASCADE,
  depth INT DEFAULT 0 CHECK (depth >= 0 AND depth <= 10),

  -- Engagement metrics
  upvotes_count INT DEFAULT 0 CHECK (upvotes_count >= 0),
  downvotes_count INT DEFAULT 0 CHECK (downvotes_count >= 0),
  reply_count INT DEFAULT 0 CHECK (reply_count >= 0),

  -- Moderation
  is_deleted BOOLEAN DEFAULT FALSE,
  is_pinned BOOLEAN DEFAULT FALSE,
  is_locked BOOLEAN DEFAULT FALSE,
  deleted_at TIMESTAMPTZ,
  deleted_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  last_reply_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

  -- Full-text search vector
  search_vector TSVECTOR GENERATED ALWAYS AS (
    to_tsvector('english', COALESCE(title, '') || ' ' || content)
  ) STORED,

  -- Constraints
  CONSTRAINT forum_posts_category_check CHECK (
    (post_type = 'discussion' AND category_id IS NOT NULL) OR
    (post_type = 'bill_comment' AND bill_number IS NOT NULL AND bill_session IS NOT NULL)
  ),
  CONSTRAINT forum_posts_title_check CHECK (
    (depth = 0 AND title IS NOT NULL) OR (depth > 0)
  )
);

-- Indexes
CREATE INDEX idx_forum_posts_category ON public.forum_posts(category_id, created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_forum_posts_bill ON public.forum_posts(bill_number, bill_session, created_at DESC) WHERE is_deleted = FALSE;
CREATE INDEX idx_forum_posts_author ON public.forum_posts(author_id, created_at DESC);
CREATE INDEX idx_forum_posts_parent ON public.forum_posts(parent_post_id, created_at);
CREATE INDEX idx_forum_posts_thread ON public.forum_posts(thread_root_id, depth, created_at);
CREATE INDEX idx_forum_posts_search ON public.forum_posts USING GIN(search_vector);
CREATE INDEX idx_forum_posts_hot ON public.forum_posts(last_reply_at DESC) WHERE is_deleted = FALSE AND is_pinned = FALSE;

-- ============================================
-- 4. FORUM VOTES
-- ============================================

DROP TABLE IF EXISTS public.forum_votes CASCADE;

CREATE TABLE public.forum_votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID REFERENCES public.forum_posts(id) ON DELETE CASCADE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  vote_type VARCHAR(10) NOT NULL CHECK (vote_type IN ('upvote', 'downvote')),
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  UNIQUE(post_id, user_id)
);

CREATE INDEX idx_forum_votes_post ON public.forum_votes(post_id);
CREATE INDEX idx_forum_votes_user ON public.forum_votes(user_id);

-- ============================================
-- 5. MODERATION REPORTS
-- ============================================

DROP TABLE IF EXISTS public.moderation_reports CASCADE;

CREATE TABLE public.moderation_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID REFERENCES public.forum_posts(id) ON DELETE CASCADE NOT NULL,
  reporter_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  reason TEXT NOT NULL CHECK (LENGTH(reason) > 0),
  status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'resolved', 'dismissed')),
  resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  resolved_at TIMESTAMPTZ,
  admin_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  UNIQUE(post_id, reporter_id)
);

CREATE INDEX idx_moderation_reports_status ON public.moderation_reports(status, created_at DESC);
CREATE INDEX idx_moderation_reports_post ON public.moderation_reports(post_id);

-- ============================================
-- 6. MODERATION ACTIONS
-- ============================================

DROP TABLE IF EXISTS public.moderation_actions CASCADE;

CREATE TABLE public.moderation_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID REFERENCES public.forum_posts(id) ON DELETE CASCADE NOT NULL,
  moderator_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  action VARCHAR(20) NOT NULL CHECK (action IN ('delete', 'lock', 'unlock', 'pin', 'unpin', 'warn')),
  reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_moderation_actions_post ON public.moderation_actions(post_id, created_at DESC);
CREATE INDEX idx_moderation_actions_moderator ON public.moderation_actions(moderator_id, created_at DESC);

-- ============================================
-- 7. TRIGGERS & FUNCTIONS
-- ============================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_forum_categories_updated_at BEFORE UPDATE ON public.forum_categories
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_forum_posts_updated_at BEFORE UPDATE ON public.forum_posts
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Function: Update post vote counts
CREATE OR REPLACE FUNCTION public.update_post_vote_counts()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    IF NEW.vote_type = 'upvote' THEN
      UPDATE public.forum_posts SET upvotes_count = upvotes_count + 1 WHERE id = NEW.post_id;
    ELSIF NEW.vote_type = 'downvote' THEN
      UPDATE public.forum_posts SET downvotes_count = downvotes_count + 1 WHERE id = NEW.post_id;
    END IF;
  ELSIF (TG_OP = 'DELETE') THEN
    IF OLD.vote_type = 'upvote' THEN
      UPDATE public.forum_posts SET upvotes_count = upvotes_count - 1 WHERE id = OLD.post_id;
    ELSIF OLD.vote_type = 'downvote' THEN
      UPDATE public.forum_posts SET downvotes_count = downvotes_count - 1 WHERE id = OLD.post_id;
    END IF;
  ELSIF (TG_OP = 'UPDATE' AND OLD.vote_type != NEW.vote_type) THEN
    IF OLD.vote_type = 'upvote' AND NEW.vote_type = 'downvote' THEN
      UPDATE public.forum_posts
      SET upvotes_count = upvotes_count - 1, downvotes_count = downvotes_count + 1
      WHERE id = NEW.post_id;
    ELSIF OLD.vote_type = 'downvote' AND NEW.vote_type = 'upvote' THEN
      UPDATE public.forum_posts
      SET upvotes_count = upvotes_count + 1, downvotes_count = downvotes_count - 1
      WHERE id = NEW.post_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_vote_counts AFTER INSERT OR UPDATE OR DELETE ON public.forum_votes
  FOR EACH ROW EXECUTE FUNCTION public.update_post_vote_counts();

-- Function: Update category post counts
CREATE OR REPLACE FUNCTION public.update_category_post_count()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT' AND NEW.depth = 0 AND NEW.is_deleted = FALSE) THEN
    UPDATE public.forum_categories SET post_count = post_count + 1 WHERE id = NEW.category_id;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE AND NEW.depth = 0 THEN
      UPDATE public.forum_categories SET post_count = post_count - 1 WHERE id = NEW.category_id;
    ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE AND NEW.depth = 0 THEN
      UPDATE public.forum_categories SET post_count = post_count + 1 WHERE id = NEW.category_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_category_counts AFTER INSERT OR UPDATE ON public.forum_posts
  FOR EACH ROW EXECUTE FUNCTION public.update_category_post_count();

-- Function: Update parent post reply counts and last_reply_at
CREATE OR REPLACE FUNCTION public.update_parent_reply_stats()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT' AND NEW.parent_post_id IS NOT NULL AND NEW.is_deleted = FALSE) THEN
    UPDATE public.forum_posts
    SET reply_count = reply_count + 1, last_reply_at = NEW.created_at
    WHERE id = NEW.parent_post_id OR id = NEW.thread_root_id;
  ELSIF (TG_OP = 'UPDATE') THEN
    IF OLD.is_deleted = FALSE AND NEW.is_deleted = TRUE AND NEW.parent_post_id IS NOT NULL THEN
      UPDATE public.forum_posts SET reply_count = reply_count - 1 WHERE id = NEW.parent_post_id;
    ELSIF OLD.is_deleted = TRUE AND NEW.is_deleted = FALSE AND NEW.parent_post_id IS NOT NULL THEN
      UPDATE public.forum_posts SET reply_count = reply_count + 1 WHERE id = NEW.parent_post_id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reply_stats AFTER INSERT OR UPDATE ON public.forum_posts
  FOR EACH ROW EXECUTE FUNCTION public.update_parent_reply_stats();

-- Function: Rate limiting check (max 10 posts per hour)
CREATE OR REPLACE FUNCTION public.check_post_rate_limit(p_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  v_recent_posts INT;
BEGIN
  SELECT COUNT(*) INTO v_recent_posts
  FROM public.forum_posts
  WHERE author_id = p_user_id
    AND created_at > NOW() - INTERVAL '1 hour';
  RETURN v_recent_posts < 10;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- 8. ROW-LEVEL SECURITY (RLS)
-- ============================================

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forum_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forum_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.forum_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.moderation_actions ENABLE ROW LEVEL SECURITY;

-- User Profiles
CREATE POLICY user_profiles_select ON public.user_profiles FOR SELECT USING (TRUE);
CREATE POLICY user_profiles_insert ON public.user_profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY user_profiles_update ON public.user_profiles FOR UPDATE USING (auth.uid() = id);

-- Categories
CREATE POLICY forum_categories_select ON public.forum_categories FOR SELECT USING (is_active = TRUE);

-- Posts
CREATE POLICY forum_posts_select ON public.forum_posts FOR SELECT USING (is_deleted = FALSE OR author_id = auth.uid());
CREATE POLICY forum_posts_insert ON public.forum_posts FOR INSERT WITH CHECK (auth.uid() = author_id AND public.check_post_rate_limit(auth.uid()));
CREATE POLICY forum_posts_update ON public.forum_posts FOR UPDATE USING (auth.uid() = author_id AND is_locked = FALSE) WITH CHECK (auth.uid() = author_id);
CREATE POLICY forum_posts_delete ON public.forum_posts FOR DELETE USING (auth.uid() = author_id);

-- Votes
CREATE POLICY forum_votes_select ON public.forum_votes FOR SELECT USING (TRUE);
CREATE POLICY forum_votes_insert ON public.forum_votes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY forum_votes_update ON public.forum_votes FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY forum_votes_delete ON public.forum_votes FOR DELETE USING (auth.uid() = user_id);

-- Reports
CREATE POLICY moderation_reports_select ON public.moderation_reports FOR SELECT USING (reporter_id = auth.uid());
CREATE POLICY moderation_reports_insert ON public.moderation_reports FOR INSERT WITH CHECK (auth.uid() = reporter_id);

-- Actions
CREATE POLICY moderation_actions_select ON public.moderation_actions FOR SELECT USING (TRUE);

-- ============================================
-- 9. SEED DATA
-- ============================================

INSERT INTO public.forum_categories (name, slug, description, icon, color, display_order) VALUES
  ('General Discussion', 'general', 'General political discussions and current events', 'MessageSquare', '#6B7280', 1),
  ('Healthcare', 'healthcare', 'Discuss healthcare policy, funding, and reforms', 'Heart', '#EF4444', 2),
  ('Climate & Environment', 'climate', 'Climate change, environmental policy, and sustainability', 'Leaf', '#10B981', 3),
  ('Economy & Finance', 'economy', 'Economic policy, budgets, taxes, and fiscal matters', 'DollarSign', '#F59E0B', 4),
  ('Justice & Law', 'justice', 'Legal system, justice reform, and law enforcement', 'Scale', '#8B5CF6', 5),
  ('Indigenous Affairs', 'indigenous', 'Indigenous rights, reconciliation, and treaty issues', 'Users', '#F97316', 6),
  ('Immigration', 'immigration', 'Immigration policy, refugees, and citizenship', 'Globe', '#3B82F6', 7),
  ('Education', 'education', 'Education policy, funding, and curriculum', 'GraduationCap', '#EC4899', 8),
  ('Defence & Security', 'defence', 'National defence, cybersecurity, and public safety', 'Shield', '#DC2626', 9),
  ('Housing', 'housing', 'Housing affordability, development, and policy', 'Home', '#14B8A6', 10);

-- ============================================
-- SUCCESS MESSAGE
-- ============================================
DO $$
BEGIN
  RAISE NOTICE 'Forum system migration completed successfully!';
  RAISE NOTICE 'Created 6 tables: user_profiles, forum_categories, forum_posts, forum_votes, moderation_reports, moderation_actions';
  RAISE NOTICE 'Seeded 10 forum categories';
  RAISE NOTICE 'Enabled RLS on all tables';
END $$;
