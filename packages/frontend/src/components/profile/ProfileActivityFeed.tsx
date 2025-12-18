/**
 * ProfileActivityFeed Component
 *
 * Displays user's activity timeline (posts, bookmarks, follows, etc.)
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import {
  MessageSquare,
  MessageCircle,
  Bookmark,
  BookmarkPlus,
  FolderPlus,
  UserPlus,
  FileText,
  ThumbsUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface ActivityEvent {
  id: string;
  event_type: string;
  title: string;
  description: string | null;
  reference_url: string | null;
  created_at: string;
  metadata: Record<string, any>;
}

interface ProfileActivityFeedProps {
  username: string;
  initialEvents?: ActivityEvent[];
  limit?: number;
}

export function ProfileActivityFeed({
  username,
  initialEvents = [],
  limit = 20,
}: ProfileActivityFeedProps) {
  const [events, setEvents] = useState<ActivityEvent[]>(initialEvents);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(initialEvents.length);

  const loadMore = async () => {
    setLoading(true);

    try {
      const response = await fetch(
        `/api/users/${username}/feed?limit=${limit}&offset=${offset}`
      );

      if (!response.ok) {
        throw new Error('Failed to load activity feed');
      }

      const data = await response.json();

      setEvents((prev) => [...prev, ...data.events]);
      setHasMore(data.hasMore);
      setOffset((prev) => prev + data.events.length);
    } catch (error) {
      console.error('Error loading activity feed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (events.length === 0 && !loading) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
        <p>No activity yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {events.map((event) => (
        <ActivityEventCard key={event.id} event={event} />
      ))}

      {hasMore && (
        <div className="flex justify-center py-4">
          <Button
            variant="outline"
            onClick={loadMore}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              'Load more'
            )}
          </Button>
        </div>
      )}
    </div>
  );
}

function ActivityEventCard({ event }: { event: ActivityEvent }) {
  const icon = getEventIcon(event.event_type);
  const timeAgo = formatDistanceToNow(new Date(event.created_at), {
    addSuffix: true,
  });

  return (
    <div className="flex gap-4 rounded-lg border bg-card p-4 transition-colors hover:bg-muted/50">
      <div className="flex-shrink-0">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
          {icon}
        </div>
      </div>

      <div className="flex-1 space-y-1">
        <p className="font-medium">{event.title}</p>
        {event.description && (
          <p className="text-sm text-muted-foreground">{event.description}</p>
        )}
        <p className="text-xs text-muted-foreground">{timeAgo}</p>
      </div>

      {event.reference_url && (
        <div className="flex-shrink-0">
          <Link href={event.reference_url}>
            <Button variant="ghost" size="sm">
              View
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}

function getEventIcon(eventType: string) {
  const iconClass = 'h-5 w-5';

  switch (eventType) {
    case 'post_created':
      return <MessageSquare className={iconClass} />;
    case 'reply_created':
      return <MessageCircle className={iconClass} />;
    case 'post_voted':
      return <ThumbsUp className={iconClass} />;
    case 'bill_bookmarked':
    case 'mp_bookmarked':
    case 'statement_bookmarked':
      return <Bookmark className={iconClass} />;
    case 'collection_created':
      return <FolderPlus className={iconClass} />;
    case 'followed_user':
      return <UserPlus className={iconClass} />;
    case 'substack_article':
      return <FileText className={iconClass} />;
    default:
      return <BookmarkPlus className={iconClass} />;
  }
}
