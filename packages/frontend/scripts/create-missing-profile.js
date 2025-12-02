/**
 * Create missing user profile
 * Run with: NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/create-missing-profile.js
 */

const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing environment variables');
  console.error('Please set NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

const userId = '6b5e16ed-6c48-4237-b79b-7e3b808216da';

async function createProfile() {
  console.log('Checking auth.users...');
  const { data: authUser, error: authError } = await supabase.auth.admin.getUserById(userId);

  if (authError) {
    console.error('Error fetching auth user:', authError);
    return;
  }

  console.log('Auth user:', authUser.user.email, 'created:', authUser.user.created_at);

  console.log('\nChecking user_profiles...');
  const { data: profile, error: profileError } = await supabase
    .from('user_profiles')
    .select('*')
    .eq('id', userId)
    .single();

  if (profile) {
    console.log('Profile already exists:', profile.email);
    return;
  }

  console.log('Profile does not exist, creating...');

  const { data: newProfile, error: createError } = await supabase
    .from('user_profiles')
    .insert({
      id: userId,
      email: authUser.user.email,
      full_name: authUser.user.user_metadata?.full_name || authUser.user.email,
      subscription_tier: 'FREE',
      monthly_usage: 0,
      usage_reset_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: authUser.user.created_at,
      updated_at: new Date().toISOString()
    })
    .select()
    .single();

  if (createError) {
    console.error('Error creating profile:', createError);
    return;
  }

  console.log('Profile created successfully!');
  console.log('  Email:', newProfile.email);
  console.log('  Tier:', newProfile.subscription_tier);
  console.log('  Created:', newProfile.created_at);
}

createProfile()
  .then(() => {
    console.log('\nDone!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Error:', error);
    process.exit(1);
  });
