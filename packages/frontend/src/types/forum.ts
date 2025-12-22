/**
 * Forum System Types
 * TypeScript definitions for forum entities matching Supabase schema
 */

// ============================================
// Database Types (matching Supabase tables)
// ============================================

export interface UserProfile {
  id: string; // UUID
  display_name: string | null;
  avatar_url: string | null;
  bio: string | null;
  location: string | null;
  posts_count: number;
  replies_count: number;
  reputation_score: number;
  email_notifications: boolean;
  show_email: boolean;
  created_at: string;
  updated_at: string;
}

export interface ForumCategory {
  id: string; // UUID
  name: string;
  slug: string;
  description: string | null;
  icon: string | null; // Lucide icon name
  color: string | null; // Hex color
  display_order: number;
  is_active: boolean;
  post_count: number;
  last_post_at: string | null;
  created_at: string;
  updated_at: string;
}

export type PostType = 'discussion' | 'bill_comment';

export interface ForumPost {
  id: string; // UUID
  post_type: PostType;

  // For discussions
  category_id: string | null;
  category?: ForumCategory; // Joined data

  // For bill comments
  bill_id: number | null;
  bill_number: string | null;
  bill_session: string | null;

  // Additional entity metadata (e.g., section_ref for bill section discussions)
  entity_metadata: Record<string, unknown> | null;

  // Content
  title: string | null;
  content: string;

  // Author
  author_id: string;
  author_name: string | null;
  author_avatar_url: string | null;
  author?: UserProfile; // Joined data

  // Threading
  parent_post_id: string | null;
  thread_root_id: string | null;
  depth: number;

  // Engagement
  upvotes_count: number;
  downvotes_count: number;
  reply_count: number;

  // Moderation
  is_deleted: boolean;
  is_pinned: boolean;
  is_locked: boolean;
  deleted_at: string | null;
  deleted_by: string | null;

  // Timestamps
  created_at: string;
  updated_at: string;
  edited_at: string | null;
  last_reply_at: string;

  // User's vote on this post (if authenticated)
  user_vote?: 'upvote' | 'downvote' | null;

  // Replies (for threaded display)
  replies?: ForumPost[];
}

export type VoteType = 'upvote' | 'downvote';

export interface ForumVote {
  id: string;
  post_id: string;
  user_id: string;
  vote_type: VoteType;
  created_at: string;
}

export type ReportReason = 'spam' | 'harassment' | 'misinformation' | 'off_topic' | 'other';
export type ReportStatus = 'pending' | 'resolved' | 'dismissed';

export interface ModerationReport {
  id: string;
  post_id: string;
  post?: ForumPost;
  reporter_id: string;
  reporter?: UserProfile;
  reason: string;
  status: ReportStatus;
  resolved_by: string | null;
  resolved_at: string | null;
  admin_notes: string | null;
  created_at: string;
}

export type ModerationActionType = 'delete' | 'lock' | 'unlock' | 'pin' | 'unpin' | 'warn';

export interface ModerationAction {
  id: string;
  post_id: string;
  post?: ForumPost;
  moderator_id: string;
  moderator?: UserProfile;
  action: ModerationActionType;
  reason: string | null;
  created_at: string;
}

// ============================================
// Input Types (for creating/updating)
// ============================================

export interface CreatePostInput {
  post_type: PostType;
  category_id?: string;
  bill_number?: string;
  bill_session?: string;
  title?: string; // Required for top-level posts
  content: string;
  parent_post_id?: string; // For replies
  thread_root_id?: string; // For threading
  depth?: number; // Thread depth
  entity_metadata?: Record<string, unknown>; // Additional metadata (e.g., section_ref)
}

export interface UpdatePostInput {
  title?: string;
  content?: string;
}

export interface CreateReportInput {
  post_id: string;
  reason: string;
}

export interface ResolveReportInput {
  report_id: string;
  status: 'resolved' | 'dismissed';
  admin_notes?: string;
}

export interface ModeratePostInput {
  post_id: string;
  action: ModerationActionType;
  reason?: string;
}

// ============================================
// Query Parameters
// ============================================

export interface GetPostsParams {
  post_type?: PostType;
  category_id?: string;
  bill_number?: string;
  bill_session?: string;
  author_id?: string;
  limit?: number;
  offset?: number;
  sort?: 'recent' | 'hot' | 'top' | 'controversial';
  sort_by?: string; // Alternative sorting field
}

export interface GetThreadParams {
  post_id: string;
  max_depth?: number;
}

// ============================================
// API Response Types
// ============================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ApiResponse<T = void> {
  success: boolean;
  data?: T;
  error?: string;
}

// ============================================
// UI Component Props
// ============================================

export interface PostCardProps {
  post: ForumPost;
  onReply?: (postId: string) => void;
  onEdit?: (postId: string) => void;
  onDelete?: (postId: string) => void;
  onReport?: (postId: string) => void;
  showReplies?: boolean;
}

export interface VoteButtonsProps {
  postId: string;
  upvotes: number;
  downvotes: number;
  userVote?: VoteType | null;
  onVote: (voteType: VoteType) => Promise<void>;
}

export interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
}

// ============================================
// Utility Types
// ============================================

export type SortOption = 'recent' | 'hot' | 'top' | 'controversial';

export interface ThreadNode extends ForumPost {
  children: ThreadNode[];
}

// Helper type for nested thread building
export type PostWithReplies = ForumPost & {
  replies: PostWithReplies[];
};
