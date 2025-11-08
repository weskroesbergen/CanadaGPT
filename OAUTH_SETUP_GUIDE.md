# OAuth Provider Setup Guide

This guide walks you through setting up OAuth authentication providers (Google, GitHub, Facebook, LinkedIn) for your FedMCP application.

## Prerequisites

- Supabase project created (you already have: `pbxyhcdzdovsdlsyixsk.supabase.co`)
- Access to Supabase Dashboard: https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk

## Overview

Your application supports 4 OAuth providers:
- Google OAuth
- GitHub OAuth
- Facebook OAuth
- LinkedIn OAuth

Each provider requires:
1. Creating an OAuth application on the provider's platform
2. Configuring redirect URLs
3. Obtaining Client ID and Client Secret
4. Adding credentials to Supabase Dashboard

## Supabase OAuth Callback URL

All OAuth providers must redirect to this URL:
```
https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback
```

## Step-by-Step Setup

### 1. Google OAuth Setup

#### Step 1: Create OAuth Client
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. If prompted, configure the OAuth consent screen:
   - **Application type**: External
   - **Application name**: CanadaGPT (or your app name)
   - **User support email**: Your email
   - **Developer contact email**: Your email
   - **Scopes**: Add `email` and `profile` (default)
   - **Test users**: Add your email for testing

#### Step 2: Configure OAuth Client
1. **Application type**: Web application
2. **Name**: CanadaGPT Web Client
3. **Authorized JavaScript origins**:
   - `http://localhost:3000` (development)
   - Your production domain when deployed
4. **Authorized redirect URIs**:
   - `https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback`
5. Click **Create**

#### Step 3: Copy Credentials
- Save the **Client ID** (looks like: `123456789-abc.apps.googleusercontent.com`)
- Save the **Client Secret** (looks like: `GOCSPX-abc123...`)

#### Step 4: Add to Supabase
1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk)
2. Navigate to **Authentication** → **Providers**
3. Find **Google** and toggle it on
4. Paste:
   - **Client ID**: Your Google Client ID
   - **Client Secret**: Your Google Client Secret
5. Click **Save**

---

### 2. GitHub OAuth Setup

#### Step 1: Create OAuth App
1. Go to [GitHub Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** → **New OAuth App**
3. Fill in the details:
   - **Application name**: CanadaGPT
   - **Homepage URL**: `http://localhost:3000` (for development)
   - **Application description**: Federal parliamentary data and AI chat
   - **Authorization callback URL**: `https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback`
4. Click **Register application**

#### Step 2: Generate Client Secret
1. On your OAuth app page, click **Generate a new client secret**
2. Save the **Client ID** (visible at top)
3. Save the **Client Secret** (shown once - copy immediately!)

#### Step 3: Add to Supabase
1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk)
2. Navigate to **Authentication** → **Providers**
3. Find **GitHub** and toggle it on
4. Paste:
   - **Client ID**: Your GitHub Client ID
   - **Client Secret**: Your GitHub Client Secret
5. Click **Save**

---

### 3. Facebook OAuth Setup

#### Step 1: Create Facebook App
1. Go to [Facebook Developers](https://developers.facebook.com)
2. Click **My Apps** → **Create App**
3. Select **Consumer** as app type
4. Fill in app details:
   - **App Name**: CanadaGPT
   - **App Contact Email**: Your email
5. Click **Create App**

#### Step 2: Add Facebook Login
1. In the app dashboard, find **Facebook Login**
2. Click **Set Up**
3. Select **Web** platform
4. Enter Site URL: `http://localhost:3000`
5. Click **Save** and **Continue**

#### Step 3: Configure OAuth Settings
1. Go to **Facebook Login** → **Settings**
2. Under **Valid OAuth Redirect URIs**, add:
   ```
   https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback
   ```
3. Click **Save Changes**

#### Step 4: Get App Credentials
1. Go to **Settings** → **Basic**
2. Copy the **App ID** (this is your Client ID)
3. Click **Show** next to **App Secret** and copy it (this is your Client Secret)

#### Step 5: Add to Supabase
1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk)
2. Navigate to **Authentication** → **Providers**
3. Find **Facebook** and toggle it on
4. Paste:
   - **Client ID**: Your Facebook App ID
   - **Client Secret**: Your Facebook App Secret
5. Click **Save**

---

### 4. LinkedIn OAuth Setup

#### Step 1: Create LinkedIn App
1. Go to [LinkedIn Developers](https://www.linkedin.com/developers)
2. Click **Create app**
3. Fill in the details:
   - **App name**: CanadaGPT
   - **LinkedIn Page**: Select or create a LinkedIn page for your app
   - **App logo**: Upload a logo (optional)
   - **Legal agreement**: Check the box
4. Click **Create app**

#### Step 2: Request OAuth 2.0 Scopes
1. In the **Auth** tab, ensure you have:
   - **OpenID** scope
   - **Profile** scope (for name, profile picture)
   - **Email** scope
2. Add **Authorized redirect URLs**:
   ```
   https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback
   ```

#### Step 3: Get Credentials
1. Go to the **Auth** tab
2. Copy the **Client ID**
3. Copy the **Client Secret**

#### Step 4: Add to Supabase
1. Go to [Supabase Dashboard](https://supabase.com/dashboard/project/pbxyhcdzdovsdlsyixsk)
2. Navigate to **Authentication** → **Providers**
3. Find **LinkedIn** and toggle it on
4. Paste:
   - **Client ID**: Your LinkedIn Client ID
   - **Client Secret**: Your LinkedIn Client Secret
5. Click **Save**

---

## Additional Supabase Configuration

### 1. Configure Site URL and Redirect URLs

1. Go to **Authentication** → **URL Configuration**
2. Set **Site URL**:
   - Development: `http://localhost:3000`
   - Production: Your production domain
3. Add **Redirect URLs**:
   - `http://localhost:3000/auth/callback`
   - `http://localhost:3000/*` (for wildcard matching)
   - Add production URLs when deployed

### 2. Email Template Configuration (Optional)

1. Go to **Authentication** → **Email Templates**
2. Customize:
   - **Confirm signup** template
   - **Invite user** template
   - **Magic link** template
   - **Change email address** template
   - **Reset password** template

### 3. Test Authentication

After configuring providers:

1. Start your development server:
   ```bash
   cd packages/frontend
   pnpm dev
   ```

2. Navigate to `http://localhost:3000/auth/login`

3. Test each OAuth provider:
   - Click the Google button → should redirect to Google login
   - Click the GitHub button → should redirect to GitHub login
   - Click the Facebook button → should redirect to Facebook login
   - Click the LinkedIn button → should redirect to LinkedIn login

4. After successful authentication, you should be redirected back to your app

---

## Environment Variables

Your `.env.local` file already has Supabase credentials configured. You need to add:

### Required: Anthropic API Key (for AI Chat)

1. Go to [Anthropic Console](https://console.anthropic.com/settings/keys)
2. Click **Create Key**
3. Copy the API key (starts with `sk-ant-`)
4. Add to `.env.local`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

### Optional: OpenAI API Key (Alternative AI Provider)

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click **Create new secret key**
3. Copy the API key (starts with `sk-`)
4. Add to `.env.local`:
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   ```

### Optional: Encryption Key (for BYOK Feature)

Generate a secure encryption key:
```bash
openssl rand -hex 32
```

Add to `.env.local`:
```bash
ENCRYPTION_KEY=your-generated-64-character-hex-string
```

---

## Troubleshooting

### OAuth Provider Issues

**"Redirect URI mismatch" error**:
- Verify the redirect URI in the provider settings exactly matches:
  ```
  https://pbxyhcdzdovsdlsyixsk.supabase.co/auth/v1/callback
  ```
- Check for trailing slashes or typos

**"Invalid client" error**:
- Verify Client ID and Client Secret are correct in Supabase
- Ensure the OAuth app is not in a restricted or pending state
- For Google: Check that OAuth consent screen is configured

**User not redirected after login**:
- Check Supabase URL Configuration has correct Site URL
- Verify redirect URLs include your callback route
- Check browser console for JavaScript errors

### Supabase Connection Issues

**"Invalid API key" error**:
- Verify `NEXT_PUBLIC_SUPABASE_URL` matches your project URL
- Verify `NEXT_PUBLIC_SUPABASE_ANON_KEY` is the **anon** key, not service role
- Check for spaces or quotes in `.env.local`

**Can't see providers in login page**:
- Verify providers are enabled in Supabase Dashboard
- Check that `OAuthProviders` component is imported in login page
- Restart Next.js dev server after adding environment variables

---

## Security Best Practices

1. **Never commit `.env.local`** to git (already in `.gitignore`)
2. **Use different OAuth apps** for development and production
3. **Restrict OAuth app domains** to your actual domains
4. **Rotate secrets** if they're accidentally exposed
5. **Use Supabase RLS policies** to protect user data
6. **Enable MFA** on your Supabase account

---

## Production Deployment Checklist

When deploying to production:

- [ ] Create production OAuth apps for each provider
- [ ] Update OAuth redirect URIs to production domain
- [ ] Add production domain to Supabase URL Configuration
- [ ] Set production environment variables in hosting platform
- [ ] Test OAuth flow in production environment
- [ ] Submit OAuth apps for review if required (Google, Facebook)
- [ ] Enable rate limiting and abuse prevention
- [ ] Set up monitoring and error tracking

---

## Need Help?

- **Supabase Documentation**: https://supabase.com/docs/guides/auth
- **OAuth 2.0 Spec**: https://oauth.net/2/
- **Provider-specific docs**:
  - [Google OAuth](https://developers.google.com/identity/protocols/oauth2)
  - [GitHub OAuth](https://docs.github.com/en/apps/oauth-apps)
  - [Facebook Login](https://developers.facebook.com/docs/facebook-login)
  - [LinkedIn OAuth](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)

---

## Summary

You now have:
- ✅ Supabase project configured
- ✅ `.env.local` file set up with Supabase credentials
- 📋 Step-by-step instructions for each OAuth provider
- 📋 Testing and troubleshooting guidance

**Next Steps**:
1. Choose which OAuth providers you want to enable
2. Follow the setup instructions for each provider
3. Add provider credentials to Supabase Dashboard
4. Add Anthropic API key to `.env.local`
5. Test authentication in your local environment
