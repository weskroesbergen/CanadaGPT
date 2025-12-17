/**
 * FollowButton Component
 *
 * Button to follow/unfollow a user with optimistic UI updates
 * Follows the same pattern as bookmark button
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { UserPlus, UserMinus, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface FollowButtonProps {
  targetUserId: string;
  targetUsername: string;
  initialIsFollowing: boolean;
  onFollowChange?: (isFollowing: boolean) => void;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'sm' | 'default' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export function FollowButton({
  targetUserId,
  targetUsername,
  initialIsFollowing,
  onFollowChange,
  variant = 'default',
  size = 'default',
  showIcon = true,
  className,
}: FollowButtonProps) {
  const { user } = useAuth();
  const router = useRouter();
  const [isFollowing, setIsFollowing] = useState(initialIsFollowing);
  const [isLoading, setIsLoading] = useState(false);

  const handleToggleFollow = async () => {
    // Require authentication
    if (!user) {
      toast.error('Please sign in to follow users');
      router.push('/auth/signin');
      return;
    }

    // Prevent self-follow
    if (user.id === targetUserId) {
      toast.error('You cannot follow yourself');
      return;
    }

    setIsLoading(true);

    // Optimistic update
    const previousState = isFollowing;
    setIsFollowing(!isFollowing);

    try {
      const response = await fetch(`/api/users/${targetUsername}/follow`, {
        method: isFollowing ? 'DELETE' : 'POST',
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Failed to toggle follow');
      }

      // Success toast
      toast.success(
        isFollowing
          ? `Unfollowed @${targetUsername}`
          : `Now following @${targetUsername}`
      );

      // Notify parent component
      onFollowChange?.(!isFollowing);
    } catch (error) {
      console.error('Error toggling follow:', error);

      // Revert optimistic update
      setIsFollowing(previousState);

      toast.error(
        error instanceof Error
          ? error.message
          : 'Failed to update follow status'
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button
      variant={isFollowing ? 'outline' : variant}
      size={size}
      onClick={handleToggleFollow}
      disabled={isLoading}
      className={className}
    >
      {isLoading ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          {isFollowing ? 'Unfollowing' : 'Following'}...
        </>
      ) : (
        <>
          {showIcon && (
            <>
              {isFollowing ? (
                <UserMinus className="mr-2 h-4 w-4" />
              ) : (
                <UserPlus className="mr-2 h-4 w-4" />
              )}
            </>
          )}
          {isFollowing ? 'Following' : 'Follow'}
        </>
      )}
    </Button>
  );
}
