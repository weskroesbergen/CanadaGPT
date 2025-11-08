-- ============================================
-- Add Admin Role to User Profiles
-- ============================================
-- Adds is_admin and is_moderator flags to user_profiles table
-- Date: 2025-01-07

-- Add admin and moderator flags
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_moderator BOOLEAN DEFAULT FALSE;

-- Create index for admin lookups
CREATE INDEX IF NOT EXISTS idx_user_profiles_is_admin ON public.user_profiles(is_admin) WHERE is_admin = TRUE;
CREATE INDEX IF NOT EXISTS idx_user_profiles_is_moderator ON public.user_profiles(is_moderator) WHERE is_moderator = TRUE;

-- Add comment
COMMENT ON COLUMN public.user_profiles.is_admin IS 'Full admin access to moderation dashboard and all features';
COMMENT ON COLUMN public.user_profiles.is_moderator IS 'Moderator access to content moderation only';

-- Optional: Create a function to promote users to admin (run manually)
CREATE OR REPLACE FUNCTION promote_to_admin(user_email TEXT)
RETURNS VOID AS $$
BEGIN
  UPDATE public.user_profiles
  SET is_admin = TRUE, is_moderator = TRUE
  WHERE id = (SELECT id FROM auth.users WHERE email = user_email);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Optional: Create a function to promote users to moderator (run manually)
CREATE OR REPLACE FUNCTION promote_to_moderator(user_email TEXT)
RETURNS VOID AS $$
BEGIN
  UPDATE public.user_profiles
  SET is_moderator = TRUE
  WHERE id = (SELECT id FROM auth.users WHERE email = user_email);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Example usage (uncomment and replace with actual admin email):
-- SELECT promote_to_admin('admin@example.com');
-- SELECT promote_to_moderator('moderator@example.com');
