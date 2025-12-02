/**
 * Check for users without profiles
 * Run with: NEXT_PUBLIC_SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... node scripts/check-missing-profiles.js
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

async function checkMissingProfiles() {
  console.log('Fetching all auth users...');

  const { data: { users }, error: usersError } = await supabase.auth.admin.listUsers();

  if (usersError) {
    console.error('Error fetching users:', usersError);
    return;
  }

  console.log(`Found ${users.length} users in auth.users`);

  console.log('\nChecking for missing profiles...');
  const missingProfiles = [];

  for (const user of users) {
    const { data: profile, error } = await supabase
      .from('user_profiles')
      .select('id')
      .eq('id', user.id)
      .single();

    if (!profile && error?.code === 'PGRST116') {
      // Profile doesn't exist
      missingProfiles.push({
        id: user.id,
        email: user.email,
        created_at: user.created_at
      });
    }
  }

  if (missingProfiles.length === 0) {
    console.log('✓ All users have profiles!');
  } else {
    console.log(`✗ Found ${missingProfiles.length} users without profiles:\n`);
    missingProfiles.forEach(u => {
      console.log(`  - ${u.email} (created ${u.created_at})`);
      console.log(`    ID: ${u.id}`);
    });

    console.log('\nTo fix, run:');
    console.log('  node scripts/create-all-missing-profiles.js');
  }
}

checkMissingProfiles()
  .then(() => {
    console.log('\nDone!');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Error:', error);
    process.exit(1);
  });
