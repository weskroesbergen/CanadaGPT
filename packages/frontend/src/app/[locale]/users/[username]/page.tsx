/**
 * User Profile Page
 *
 * Public profile page displaying user info, stats, and activity feed
 * Route: /users/[username]
 */

import { notFound } from 'next/navigation';
import { ProfileHeader } from '@/components/profile/ProfileHeader';
import { ProfileStats } from '@/components/profile/ProfileStats';
import { ProfileActivityFeed } from '@/components/profile/ProfileActivityFeed';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { SubstackFeaturedArticles, SubstackArticlesList } from '@/components/substack';

interface UserProfilePageProps {
  params: Promise<{
    username: string;
    locale: string;
  }>;
  searchParams: Promise<{
    tab?: string;
  }>;
}

async function fetchUserProfile(username: string) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
    const response = await fetch(`${baseUrl}/api/users/${username}`, {
      cache: 'no-store', // Always fetch fresh data
    });

    if (!response.ok) {
      return null;
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching user profile:', error);
    return null;
  }
}

async function fetchActivityFeed(username: string, limit: number = 20) {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
    const response = await fetch(
      `${baseUrl}/api/users/${username}/feed?limit=${limit}`,
      {
        cache: 'no-store',
      }
    );

    if (!response.ok) {
      return { events: [], count: 0, hasMore: false };
    }

    return response.json();
  } catch (error) {
    console.error('Error fetching activity feed:', error);
    return { events: [], count: 0, hasMore: false };
  }
}

export default async function UserProfilePage({
  params,
  searchParams,
}: UserProfilePageProps) {
  const { username } = await params;
  const resolvedSearchParams = await searchParams;
  const currentTab = resolvedSearchParams.tab || 'overview';

  // Fetch user profile data
  const data = await fetchUserProfile(username);

  if (!data || !data.profile) {
    notFound();
  }

  const { profile, isFollowing, mutualFollowers, isOwnProfile } = data;

  // Fetch activity feed for overview tab
  const feedData = await fetchActivityFeed(username);

  return (
    <div className="min-h-screen">
      {/* Profile Header */}
      <ProfileHeader
        profile={profile}
        isFollowing={isFollowing}
        isOwnProfile={isOwnProfile}
      />

      {/* Profile Stats */}
      <ProfileStats
        username={username}
        stats={{
          posts_count: profile.posts_count,
          replies_count: profile.replies_count,
          followers_count: profile.followers_count,
          following_count: profile.following_count,
          reputation_score: profile.reputation_score,
        }}
      />

      {/* Tabs */}
      <div className="mx-auto max-w-5xl px-4 py-6 md:px-6">
        <Tabs defaultValue={currentTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="articles">Articles</TabsTrigger>
            <TabsTrigger value="posts">Posts</TabsTrigger>
            <TabsTrigger value="bookmarks">Bookmarks</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="space-y-6">
              {/* Mutual Followers (if applicable) */}
              {!isOwnProfile && mutualFollowers > 0 && (
                <div className="rounded-lg border bg-muted/50 p-4">
                  <p className="text-sm text-muted-foreground">
                    Followed by {mutualFollowers} user
                    {mutualFollowers !== 1 ? 's' : ''} you follow
                  </p>
                </div>
              )}

              {/* Featured Substack Articles */}
              <SubstackFeaturedArticles username={username} />

              {/* Activity Feed */}
              <div>
                <h2 className="mb-4 text-xl font-semibold">Recent Activity</h2>
                <ProfileActivityFeed
                  username={username}
                  initialEvents={feedData.events}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="articles" className="mt-6">
            <SubstackArticlesList username={username} />
          </TabsContent>

          <TabsContent value="posts" className="mt-6">
            <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
              <p>Posts view coming soon...</p>
              <p className="mt-2 text-sm">
                This will show all forum posts and replies by {profile.display_name}
              </p>
            </div>
          </TabsContent>

          <TabsContent value="bookmarks" className="mt-6">
            <div className="rounded-lg border bg-card p-8 text-center text-muted-foreground">
              {isOwnProfile ? (
                <>
                  <p>Your bookmarks</p>
                  <p className="mt-2 text-sm">
                    View and manage your saved MPs, bills, and debates
                  </p>
                </>
              ) : (
                <>
                  <p>Public bookmarks</p>
                  <p className="mt-2 text-sm">
                    Public bookmarks will be displayed here
                  </p>
                </>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// Generate metadata for SEO
export async function generateMetadata({ params }: UserProfilePageProps) {
  const { username } = await params;
  const data = await fetchUserProfile(username);

  if (!data || !data.profile) {
    return {
      title: 'User not found',
    };
  }

  const { profile } = data;

  return {
    title: `${profile.display_name || username} (@${username}) | CanadaGPT`,
    description: profile.bio || `View ${profile.display_name || username}'s profile on CanadaGPT`,
  };
}
