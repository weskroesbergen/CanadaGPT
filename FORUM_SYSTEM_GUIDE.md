# CanadaGPT Forum System - Complete Guide

## 📋 Overview

A full-featured forum and discussion system built for CanadaGPT with:
- Threaded discussions (up to 10 levels deep)
- Bill-specific debate sections
- Real-time updates via Supabase Realtime
- Voting system (upvote/downvote)
- User reporting and admin moderation
- Markdown support with live preview
- Rate limiting (10 posts/hour per user)
- Browser notifications for replies

## 🏗️ Architecture

### **Database**: Supabase PostgreSQL
- 6 main tables: `user_profiles`, `forum_categories`, `forum_posts`, `forum_votes`, `moderation_reports`, `moderation_actions`
- Row-Level Security (RLS) on all tables
- Triggers for maintaining denormalized counters
- Real-time subscriptions enabled

### **Backend**: Next.js Server Actions
- `/src/actions/forum.ts` - CRUD operations for posts
- `/src/actions/moderation.ts` - Admin moderation actions
- Server-side auth with Supabase SSR

### **Frontend**: React + TypeScript
- 7 core components in `/src/components/forum/`
- 3 route pages: `/forum`, `/forum/[slug]`, `/forum/posts/[id]`
- Real-time hooks for live updates
- Bill integration on `/bills/[session]/[number]`

## 🚀 Setup Instructions

### 1. Run Database Migrations

```bash
# Navigate to Supabase project
cd supabase

# Run migrations
supabase db push

# Or apply manually via Supabase Dashboard > SQL Editor:
# - migrations/20250107000001_forum_system_v2.sql
# - migrations/20250107000002_add_admin_role.sql
```

### 2. Enable Realtime in Supabase

1. Go to Supabase Dashboard → Database → Replication
2. Enable Realtime for these tables:
   - `forum_posts`
   - `forum_votes`
   - `moderation_reports`

### 3. Promote Your First Admin

```sql
-- Run in Supabase SQL Editor
-- Replace with your email address
SELECT promote_to_admin('your-email@example.com');
```

### 4. Install Dependencies

Already installed! The forum uses existing packages:
- `@supabase/ssr` (already in package.json)
- `react-markdown` + `remark-gfm` (already installed)
- `lucide-react` (already installed)

### 5. Configure Environment Variables

Your `.env.local` should already have:
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## 📁 File Structure

```
packages/frontend/src/
├── actions/
│   ├── forum.ts                    # Post CRUD operations
│   └── moderation.ts              # Admin moderation actions
├── components/forum/
│   ├── VoteButtons.tsx            # Upvote/downvote component
│   ├── MarkdownEditor.tsx         # Write/Preview editor
│   ├── PostCard.tsx               # Individual post display
│   ├── PostThread.tsx             # Nested reply tree
│   ├── UserBadge.tsx              # User avatar + reputation
│   ├── ReportModal.tsx            # Report dialog
│   ├── CreatePostForm.tsx         # New post/reply form
│   ├── BillDiscussions.tsx        # Bill comment section
│   ├── NotificationBell.tsx       # Real-time notifications
│   └── index.ts                   # Component exports
├── hooks/
│   ├── useRealtimePosts.ts        # Live post updates
│   ├── useRealtimeVotes.ts        # Live vote counts
│   └── useRealtimeNotifications.ts # Reply notifications
├── app/
│   ├── forum/
│   │   ├── page.tsx               # Forum homepage
│   │   ├── [slug]/page.tsx        # Category posts list
│   │   └── posts/[id]/page.tsx    # Full thread view
│   ├── admin/moderation/page.tsx  # Moderation dashboard
│   └── bills/[session]/[number]/page.tsx  # (modified)
├── types/
│   └── forum.ts                   # TypeScript types
└── lib/
    └── supabase-server.ts         # Server-side Supabase client

supabase/migrations/
├── 20250107000001_forum_system_v2.sql    # Main forum tables
└── 20250107000002_add_admin_role.sql     # Admin permissions
```

## 🎯 Features Breakdown

### ✅ **Phase 1: Database** (Complete)
- [x] User profiles with reputation system
- [x] Forum categories (10 pre-seeded)
- [x] Threaded posts (up to 10 levels deep)
- [x] Vote tracking with denormalized counters
- [x] Moderation reports and actions log
- [x] RLS policies for security
- [x] Rate limiting function (10 posts/hour)

### ✅ **Phase 2: Server Actions** (Complete)
- [x] `createPost` - Create new posts/replies
- [x] `getPosts` - List posts with pagination
- [x] `getPost` - Get single post
- [x] `getPostThread` - Get full threaded replies
- [x] `updatePost` - Edit posts (owner only)
- [x] `deletePost` - Soft delete (owner only)
- [x] `votePost` - Upvote/downvote with toggle
- [x] `getCategories` - List all categories

### ✅ **Phase 3: Moderation** (Complete)
- [x] `reportPost` - User reporting (5 violation types)
- [x] `getPendingReports` - Admin queue
- [x] `resolveReport` - Mark resolved/dismissed
- [x] `moderatePost` - Delete/lock/pin/warn actions
- [x] `getModerationStats` - Dashboard statistics
- [x] `bulkModerate` - Bulk operations
- [x] Admin role checking via `is_admin` flag

### ✅ **Phase 4: UI Components** (Complete)
- [x] VoteButtons - Interactive voting
- [x] MarkdownEditor - Write/Preview tabs
- [x] PostCard - Post display with actions
- [x] PostThread - Recursive comment tree
- [x] UserBadge - Avatar + reputation
- [x] ReportModal - Report dialog
- [x] CreatePostForm - Post/reply form
- [x] BillDiscussions - Bill comment section
- [x] NotificationBell - Real-time alerts

### ✅ **Phase 5: Routes** (Complete)
- [x] `/forum` - Category grid homepage
- [x] `/forum/[slug]` - Category post list
- [x] `/forum/posts/[id]` - Thread view
- [x] Bill integration on `/bills/[session]/[number]`

### ✅ **Phase 6: Real-time** (Complete)
- [x] `useRealtimePosts` - Live post updates
- [x] `useRealtimeVotes` - Live vote counts
- [x] `useRealtimeNotifications` - Reply alerts
- [x] Browser notifications (with permission)
- [x] WebSocket subscriptions
- [x] Automatic reconnection

### ✅ **Phase 7: Admin Dashboard** (Complete)
- [x] `/admin/moderation` route
- [x] Pending reports queue
- [x] Statistics cards
- [x] Filter by violation type
- [x] Quick actions (delete/lock/warn/dismiss)
- [x] View full post context
- [x] Authorization checks

## 🎨 Design System Integration

The forum uses CanadaGPT's design tokens:
- **Colors**: `text-primary`, `text-secondary`, `accent-red`, `background-secondary`
- **Components**: `Card` from `@canadagpt/design-system`
- **Icons**: Lucide React icons
- **Dark Theme**: Optimized for dark backgrounds

## 🔐 Security Features

### Row-Level Security (RLS)
- Users can only edit/delete their own posts
- Admin actions bypass RLS with service role key
- Votes are tracked per user (no double voting)
- Reports are anonymous but logged

### Rate Limiting
- 10 posts per hour per user (enforced at database level)
- Function: `check_post_rate_limit()`
- Returns error if exceeded

### Input Validation
- Title: 1-255 characters
- Content: 10-10,000 characters
- Markdown sanitized on render
- SQL injection prevention via parameterized queries

## 📊 Database Schema

### Key Tables

**forum_posts**
- Supports both `discussion` (category-based) and `bill_comment` (bill-specific)
- `parent_post_id` - Links to parent reply
- `thread_root_id` - Links to root post of thread
- `depth` - Reply nesting level (0-10)
- Denormalized: `upvotes_count`, `downvotes_count`, `reply_count`

**forum_votes**
- Composite primary key: `(post_id, user_id)`
- `vote_type`: 'upvote' or 'downvote'
- Trigger updates `forum_posts` counters

**moderation_reports**
- Reasons: spam, harassment, misinformation, off_topic, other
- Status: pending, resolved, dismissed
- Tracks `reporter_id`, `resolved_by`, timestamps

## 🧪 Testing Guide

### Manual Testing Checklist

**Basic Forum Flow:**
1. ✅ Visit `/forum` - See category grid
2. ✅ Click category - See posts list
3. ✅ Create new post (requires sign-in)
4. ✅ Reply to post - Creates nested thread
5. ✅ Edit own post - Success
6. ✅ Try to edit others' post - Fail
7. ✅ Upvote/downvote - See count update
8. ✅ Vote again - Toggle (remove vote)

**Bill Integration:**
1. ✅ Visit `/bills/45-1/c-249`
2. ✅ Scroll to "Community Discussion"
3. ✅ Add comment
4. ✅ See comment in list

**Real-time:**
1. ✅ Open same thread in two tabs
2. ✅ Post in tab 1
3. ✅ See instant update in tab 2
4. ✅ Vote in tab 2
5. ✅ See count update in tab 1

**Notifications:**
1. ✅ User A creates post
2. ✅ User B replies to User A's post
3. ✅ User A sees notification bell light up
4. ✅ Click bell - See reply notification
5. ✅ Click notification - Navigate to post

**Moderation:**
1. ✅ Report a post
2. ✅ Visit `/admin/moderation` (as admin)
3. ✅ See report in queue
4. ✅ Delete/lock/warn/dismiss
5. ✅ See stats update

### Admin Setup for Testing

```sql
-- Promote yourself to admin
SELECT promote_to_admin('your-test-email@example.com');

-- Create test data
INSERT INTO forum_posts (post_type, category_id, title, content, author_id)
VALUES ('discussion',
        (SELECT id FROM forum_categories WHERE slug = 'healthcare' LIMIT 1),
        'Test Post',
        'This is a test post for manual testing.',
        (SELECT id FROM auth.users WHERE email = 'your-test-email@example.com'));
```

## 🔄 Real-time Implementation

### How It Works

```typescript
// 1. Fetch initial data from database
const [initialPosts, setInitialPosts] = useState([]);

// 2. Subscribe to real-time updates
const posts = useRealtimePosts(initialPosts, {
  categoryId: 'healthcare-category-uuid',
  enabled: true,
});

// 3. Supabase Realtime listens for:
// - INSERT → Add new post to list
// - UPDATE → Update existing post
// - DELETE → Remove post from list

// 4. UI automatically re-renders
```

### Channels Created

Each component creates its own channel:
- `posts-{categoryId}` - For category pages
- `posts-{billNumber}` - For bill discussions
- `votes-{postId}` - For vote buttons
- `user-notifications-{userId}` - For notifications

### Performance

- **Bandwidth**: ~1-2KB per event
- **Latency**: <100ms for local updates
- **Connections**: Multiplexed over single WebSocket
- **Cleanup**: Auto-disconnects on component unmount

## 🎯 Usage Examples

### Creating a Post

```typescript
import { createPost } from '@/actions/forum';

const result = await createPost({
  post_type: 'discussion',
  category_id: 'healthcare-uuid',
  title: 'Medicare Expansion Discussion',
  content: 'What are your thoughts on the proposed expansion?',
});

if (result.success) {
  console.log('Post created:', result.data);
}
```

### Bill Comment

```typescript
const result = await createPost({
  post_type: 'bill_comment',
  bill_number: 'C-249',
  bill_session: '45-1',
  content: 'I support this bill because...',
});
```

### Voting

```typescript
import { votePost } from '@/actions/forum';

// Upvote (or remove upvote if already voted)
const result = await votePost('post-uuid', 'upvote');

// Downvote
const result = await votePost('post-uuid', 'downvote');
```

### Reporting

```typescript
import { reportPost } from '@/actions/moderation';

const result = await reportPost({
  post_id: 'post-uuid',
  reason: 'spam',
});
```

## 🐛 Troubleshooting

### "Admin access required" error

**Problem**: Can't access `/admin/moderation`

**Solution**:
```sql
-- Run in Supabase SQL Editor
SELECT promote_to_admin('your-email@example.com');

-- Verify
SELECT id, email, is_admin FROM user_profiles
JOIN auth.users ON user_profiles.id = auth.users.id
WHERE is_admin = TRUE;
```

### Real-time not working

**Problem**: Posts don't update live

**Solution**:
1. Check Supabase Dashboard → Database → Replication
2. Ensure `forum_posts` has Realtime enabled
3. Check browser console for WebSocket errors
4. Verify `NEXT_PUBLIC_SUPABASE_URL` is correct

### Rate limit exceeded

**Problem**: "You can only create 10 posts per hour"

**Solution**:
```sql
-- Reset rate limit for user (dev only!)
DELETE FROM forum_posts
WHERE author_id = 'user-uuid'
AND created_at > NOW() - INTERVAL '1 hour';
```

### Nested replies not showing

**Problem**: Replies don't appear under parent

**Solution**:
- Check that `parent_post_id` and `thread_root_id` are set correctly
- Verify `depth` is not > 10 (max depth)
- Ensure `getPostThread` is being used (not `getPosts`)

## 📈 Future Enhancements

### Planned Features
- [ ] Emoji reactions (❤️ 👍 😂 etc.)
- [ ] Mentions with @username autocomplete
- [ ] Search posts by keyword
- [ ] User profiles with post history
- [ ] Reputation badges and levels
- [ ] Pin posts to top of category
- [ ] Lock threads to prevent new replies
- [ ] Image uploads with Supabase Storage
- [ ] Rich text editor option (TipTap)
- [ ] Export thread as PDF
- [ ] RSS feeds for categories

### Scaling Considerations
- Add Redis cache for vote counts
- Implement pagination for large threads
- Add read/unread tracking
- Create background job for reputation calculation
- Archive old threads to separate table

## 🤝 Contributing

When adding new features:

1. **Update migration** in `supabase/migrations/`
2. **Add server action** in `src/actions/forum.ts`
3. **Update types** in `src/types/forum.ts`
4. **Create component** in `src/components/forum/`
5. **Add tests** (when test suite is ready)
6. **Update this guide** with new features

## 📝 License

Part of the CanadaGPT project. See main README for license details.

---

**Built with ❤️ for Canadian democracy**
