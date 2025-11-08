# Supabase Setup Guide for CanadaGPT

This guide walks through setting up Supabase authentication for the CanadaGPT platform.

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/log in
2. Click "New Project"
3. Fill in project details:
   - **Name**: canadagpt
   - **Database Password**: (generate a strong password - save this!)
   - **Region**: North America (closest to Canada)
   - **Pricing Plan**: Free (upgrade later as needed)
4. Click "Create new project" (takes ~2 minutes to provision)

## 2. Get API Keys

Once your project is ready:

1. Go to **Settings** (gear icon) → **API**
2. Copy these values (you'll need them later):
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon/public key**: `eyJhbGc...` (public, safe for frontend)
   - **service_role key**: `eyJhbGc...` (secret, backend only)

## 3. Configure Authentication Providers

### Enable Email/Password Authentication

1. Go to **Authentication** → **Providers**
2. **Email** should be enabled by default
3. Under **Email Auth** settings:
   - ✅ Enable email confirmations
   - Set "Confirm email" template as needed
   - Site URL: `http://localhost:3000` (development)
   - Redirect URLs: Add `http://localhost:3000/auth/callback`

### Enable OAuth Providers

#### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Application type: **Web application**
6. Add authorized redirect URIs:
   ```
   https://xxxxx.supabase.co/auth/v1/callback
   ```
7. Copy **Client ID** and **Client Secret**
8. Back in Supabase:
   - Go to **Authentication** → **Providers** → **Google**
   - Enable Google provider
   - Paste Client ID and Client Secret
   - Save

#### GitHub OAuth

1. Go to [GitHub Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: CanadaGPT
   - **Homepage URL**: `https://canadagpt.ca` (or your domain)
   - **Authorization callback URL**: `https://xxxxx.supabase.co/auth/v1/callback`
4. Click **Register application**
5. Copy **Client ID** and generate a **Client Secret**
6. Back in Supabase:
   - Go to **Authentication** → **Providers** → **GitHub**
   - Enable GitHub provider
   - Paste Client ID and Client Secret
   - Save

### Enable Magic Link (Passwordless)

Magic links are enabled by default with email auth. No additional configuration needed.

## 4. Create User Profiles Table

1. Go to **SQL Editor** in Supabase dashboard
2. Run this SQL to create profiles table:

```sql
-- User profiles table
CREATE TABLE public.user_profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  email TEXT,
  full_name TEXT,
  subscription_tier TEXT DEFAULT 'FREE' CHECK (subscription_tier IN ('FREE', 'BASIC', 'PRO')),
  monthly_usage INTEGER DEFAULT 0,
  usage_reset_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  api_key TEXT UNIQUE,
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own profile
CREATE POLICY "Users can view own profile" ON public.user_profiles
  FOR SELECT USING (auth.uid() = id);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update own profile" ON public.user_profiles
  FOR UPDATE USING (auth.uid() = id);

-- Function to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, full_name)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on new user signup
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Index for faster lookups
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX idx_user_profiles_api_key ON public.user_profiles(api_key);
CREATE INDEX idx_user_profiles_stripe ON public.user_profiles(stripe_customer_id);
```

## 5. Configure Email Templates (Optional)

1. Go to **Authentication** → **Email Templates**
2. Customize templates for:
   - Confirm signup
   - Magic Link
   - Change Email Address
   - Reset Password

Use your branding and add `{.ConfirmationURL}` placeholder for links.

## 6. Production Configuration (Later)

When deploying to production:

1. Update **Site URL** to `https://canadagpt.ca`
2. Update **Redirect URLs** to include:
   ```
   https://canadagpt.ca/auth/callback
   https://www.canadagpt.ca/auth/callback
   ```
3. Update OAuth provider redirect URIs to production URLs
4. Enable **Email rate limiting** to prevent abuse
5. Consider enabling **CAPTCHA** for signups

## 7. Add Environment Variables

Add these to your `.env.local` file in `packages/frontend/`:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...  # Server-side only, never expose to frontend
```

## 8. Test Authentication

Once configured:

1. Start the dev server: `pnpm dev`
2. Navigate to `/auth/signup`
3. Test each provider:
   - Email/password signup
   - Google OAuth
   - GitHub OAuth
   - Magic link (check your email)
4. Verify profile creation in Supabase dashboard

## Next Steps

After completing this setup:
- Install Supabase dependencies: `@supabase/supabase-js` and `@supabase/auth-helpers-nextjs`
- Create Supabase client utility
- Build authentication UI components
- Implement auth middleware for protected routes

## Troubleshooting

**OAuth redirect errors**: Double-check callback URLs match exactly
**Email not sending**: Check Supabase email settings and rate limits
**Profile not created**: Check SQL trigger in database logs
**CORS errors**: Ensure site URL is configured correctly

## Useful Links

- [Supabase Docs](https://supabase.com/docs)
- [Supabase Auth Helpers](https://supabase.com/docs/guides/auth/auth-helpers/nextjs)
- [Next.js Authentication](https://nextjs.org/docs/authentication)
