/**
 * ProfileHeader Component
 *
 * Header section of user profile with cover image, avatar, bio, and action buttons
 */

'use client';

import { useState } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { FollowButton } from './FollowButton';
import {
  MapPin,
  Link as LinkIcon,
  Calendar,
  MessageCircle,
  Settings,
  Camera
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';

interface ProfileHeaderProps {
  profile: {
    id: string;
    username: string | null;
    display_name: string | null;
    avatar_url: string | null;
    bio: string | null;
    location: string | null;
    website_url: string | null;
    cover_image_url: string | null;
    created_at: string;
  };
  isFollowing: boolean;
  isOwnProfile: boolean;
  onFollowChange?: (isFollowing: boolean) => void;
}

export function ProfileHeader({
  profile,
  isFollowing,
  isOwnProfile,
  onFollowChange,
}: ProfileHeaderProps) {
  const { user } = useAuth();
  const [localIsFollowing, setLocalIsFollowing] = useState(isFollowing);

  const handleFollowChange = (newIsFollowing: boolean) => {
    setLocalIsFollowing(newIsFollowing);
    onFollowChange?.(newIsFollowing);
  };

  const joinedDate = formatDistanceToNow(new Date(profile.created_at), {
    addSuffix: true,
  });

  return (
    <div className="w-full">
      {/* Cover Image */}
      <div className="relative h-48 bg-gradient-to-r from-blue-500 to-purple-600 md:h-64">
        {profile.cover_image_url ? (
          <Image
            src={profile.cover_image_url}
            alt="Cover"
            fill
            className="object-cover"
          />
        ) : null}

        {/* Edit cover button (own profile only) */}
        {isOwnProfile && (
          <Button
            variant="secondary"
            size="sm"
            className="absolute bottom-4 right-4"
          >
            <Camera className="mr-2 h-4 w-4" />
            Edit cover
          </Button>
        )}
      </div>

      {/* Profile Info */}
      <div className="px-4 md:px-6">
        <div className="relative flex flex-col gap-4 pb-4 md:flex-row md:items-end md:justify-between">
          {/* Avatar */}
          <div className="relative -mt-16 md:-mt-20">
            <div className="relative h-32 w-32 rounded-full border-4 border-background bg-muted md:h-40 md:w-40">
              {profile.avatar_url ? (
                <Image
                  src={profile.avatar_url}
                  alt={profile.display_name || 'User'}
                  fill
                  className="rounded-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-4xl font-bold text-white md:text-5xl">
                  {profile.display_name?.[0]?.toUpperCase() || '?'}
                </div>
              )}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {isOwnProfile ? (
              <Link href="/settings">
                <Button variant="outline">
                  <Settings className="mr-2 h-4 w-4" />
                  Edit profile
                </Button>
              </Link>
            ) : (
              <>
                <FollowButton
                  targetUserId={profile.id}
                  targetUsername={profile.username || profile.id}
                  initialIsFollowing={localIsFollowing}
                  onFollowChange={handleFollowChange}
                />
                <Link href={`/messages?user=${profile.username || profile.id}`}>
                  <Button variant="outline">
                    <MessageCircle className="mr-2 h-4 w-4" />
                    Message
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Name and Username */}
        <div className="mt-2">
          <h1 className="text-2xl font-bold md:text-3xl">
            {profile.display_name || 'Anonymous User'}
          </h1>
          {profile.username && (
            <p className="text-sm text-muted-foreground md:text-base">
              @{profile.username}
            </p>
          )}
        </div>

        {/* Bio */}
        {profile.bio && (
          <p className="mt-3 whitespace-pre-wrap text-sm md:text-base">
            {profile.bio}
          </p>
        )}

        {/* Metadata */}
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-muted-foreground">
          {profile.location && (
            <div className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              <span>{profile.location}</span>
            </div>
          )}
          {profile.website_url && (
            <div className="flex items-center gap-1">
              <LinkIcon className="h-4 w-4" />
              <a
                href={profile.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline dark:text-blue-400"
              >
                {new URL(profile.website_url).hostname}
              </a>
            </div>
          )}
          <div className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            <span>Joined {joinedDate}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
