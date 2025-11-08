-- User Preferences System
-- Stores user-specific settings and preferences

CREATE TABLE IF NOT EXISTS user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Threading preferences
  threaded_view_enabled BOOLEAN DEFAULT true,
  threaded_view_default_collapsed BOOLEAN DEFAULT false,

  -- Display preferences
  language VARCHAR(10) DEFAULT 'en',
  theme VARCHAR(20) DEFAULT 'system', -- 'light', 'dark', 'system'
  density VARCHAR(20) DEFAULT 'comfortable', -- 'compact', 'comfortable', 'spacious'

  -- Content preferences
  show_procedural_statements BOOLEAN DEFAULT false,
  default_hansard_filter VARCHAR(50), -- 'all', 'debates', 'committees'
  statements_per_page INT DEFAULT 20,

  -- Notification preferences (for future use)
  email_notifications BOOLEAN DEFAULT true,
  push_notifications BOOLEAN DEFAULT false,

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Ensure one preferences record per user
  UNIQUE(user_id)
);

-- Index for faster user lookups
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);

-- Enable Row Level Security
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only read/write their own preferences
CREATE POLICY "Users can view own preferences"
  ON user_preferences
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own preferences"
  ON user_preferences
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own preferences"
  ON user_preferences
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own preferences"
  ON user_preferences
  FOR DELETE
  USING (auth.uid() = user_id);

-- Function to auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER user_preferences_updated_at
  BEFORE UPDATE ON user_preferences
  FOR EACH ROW
  EXECUTE FUNCTION update_user_preferences_updated_at();

-- Function to create default preferences for new users
CREATE OR REPLACE FUNCTION create_default_user_preferences()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_preferences (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create preferences when a new user signs up
CREATE TRIGGER create_user_preferences_on_signup
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION create_default_user_preferences();

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO authenticated;
GRANT USAGE ON SEQUENCE user_preferences_id_seq TO authenticated;

-- Comments for documentation
COMMENT ON TABLE user_preferences IS 'User-specific settings and preferences stored server-side';
COMMENT ON COLUMN user_preferences.threaded_view_enabled IS 'Default setting for threaded conversation view';
COMMENT ON COLUMN user_preferences.threaded_view_default_collapsed IS 'Whether thread replies should be collapsed by default';
COMMENT ON COLUMN user_preferences.theme IS 'UI theme preference: light, dark, or system';
COMMENT ON COLUMN user_preferences.language IS 'Preferred language: en or fr';
