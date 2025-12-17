/**
 * ProfileStats Component
 *
 * Displays user statistics (posts, followers, following, reputation)
 */

'use client';

import Link from 'next/link';
import { MessageSquare, Users, UserPlus, Award } from 'lucide-react';

interface ProfileStatsProps {
  username: string;
  stats: {
    posts_count: number;
    replies_count: number;
    followers_count: number;
    following_count: number;
    reputation_score: number;
  };
}

export function ProfileStats({ username, stats }: ProfileStatsProps) {
  const statItems = [
    {
      label: 'Posts',
      value: stats.posts_count + stats.replies_count,
      icon: MessageSquare,
      href: `/users/${username}?tab=posts`,
    },
    {
      label: 'Followers',
      value: stats.followers_count,
      icon: Users,
      href: `/users/${username}/followers`,
    },
    {
      label: 'Following',
      value: stats.following_count,
      icon: UserPlus,
      href: `/users/${username}/following`,
    },
    {
      label: 'Reputation',
      value: stats.reputation_score,
      icon: Award,
      href: null, // Not clickable
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 border-y bg-muted/50 px-4 py-4 md:grid-cols-4 md:px-6">
      {statItems.map((item) => {
        const content = (
          <div className="flex flex-col items-center gap-2 text-center">
            <div className="flex items-center gap-2">
              <item.icon className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold md:text-3xl">
                {item.value.toLocaleString()}
              </span>
            </div>
            <span className="text-sm text-muted-foreground">{item.label}</span>
          </div>
        );

        return item.href ? (
          <Link
            key={item.label}
            href={item.href}
            className="transition-colors hover:bg-muted/80 rounded-lg p-2"
          >
            {content}
          </Link>
        ) : (
          <div key={item.label} className="p-2">
            {content}
          </div>
        );
      })}
    </div>
  );
}
