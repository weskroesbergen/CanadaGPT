'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Plus, Filter, TrendingUp, Clock, MessageSquare } from 'lucide-react';
import { PostCard, CreatePostForm } from '@/components/forum';
import { getPosts, getCategories } from '@/actions/forum';
import type { ForumPost, ForumCategory } from '@/types/forum';
import { useAuth } from '@/contexts/AuthContext';

type SortOption = 'recent' | 'top' | 'active';

export default function CategoryPage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const slug = params.slug as string;

  const [category, setCategory] = useState<ForumCategory | null>(null);
  const [posts, setPosts] = useState<ForumPost[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortOption>('recent');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const limit = 20;

  // Fetch category details
  useEffect(() => {
    const fetchCategory = async () => {
      const result = await getCategories();
      if (result.success && result.data) {
        const cat = result.data.find((c) => c.slug === slug);
        if (cat) {
          setCategory(cat);
        } else {
          router.push('/forum');
        }
      }
    };
    fetchCategory();
  }, [slug, router]);

  // Fetch posts
  useEffect(() => {
    const fetchPosts = async () => {
      if (!category) return;

      setIsLoading(true);
      const result = await getPosts({
        category_id: category.id,
        post_type: 'discussion',
        sort_by: sortBy,
        limit,
        offset,
      });

      if (result.success && result.data) {
        setPosts(offset === 0 ? result.data.data : [...posts, ...result.data.data]);
        setHasMore(result.data.has_more);
      }
      setIsLoading(false);
    };

    fetchPosts();
  }, [category, sortBy, offset]);

  const handleSortChange = (newSort: SortOption) => {
    setSortBy(newSort);
    setOffset(0);
  };

  const handleLoadMore = () => {
    setOffset(offset + limit);
  };

  const handlePostCreated = () => {
    // Refresh posts
    setOffset(0);
    setSortBy('recent');
  };

  if (!category) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="text-center py-12">
          <p className="text-text-secondary">Loading category...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-text-tertiary mb-2">
          <a href="/forum" className="hover:text-accent-red transition-colors">
            Forum
          </a>
          <span>/</span>
          <span className="text-text-primary">{category.name}</span>
        </div>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold text-text-primary mb-2">
              {category.name}
            </h1>
            {category.description && (
              <p className="text-text-secondary">{category.description}</p>
            )}
          </div>

          {user && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="
                flex items-center gap-2 px-4 py-2 rounded-lg
                bg-accent-red text-white font-medium
                hover:bg-red-700 transition-all
                whitespace-nowrap
              "
            >
              <Plus size={20} />
              New Post
            </button>
          )}
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        <Filter size={18} className="text-text-tertiary flex-shrink-0" />
        <div className="flex gap-2">
          <button
            onClick={() => handleSortChange('recent')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
              ${
                sortBy === 'recent'
                  ? 'bg-accent-red text-white'
                  : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
              }
            `}
          >
            <Clock size={16} />
            Recent
          </button>
          <button
            onClick={() => handleSortChange('top')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
              ${
                sortBy === 'top'
                  ? 'bg-accent-red text-white'
                  : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
              }
            `}
          >
            <TrendingUp size={16} />
            Top
          </button>
          <button
            onClick={() => handleSortChange('active')}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all
              ${
                sortBy === 'active'
                  ? 'bg-accent-red text-white'
                  : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
              }
            `}
          >
            <MessageSquare size={16} />
            Active
          </button>
        </div>
      </div>

      {/* Posts list */}
      {isLoading && offset === 0 ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="bg-background-secondary border-2 border-border-primary rounded-lg p-6 animate-pulse"
            >
              <div className="h-6 bg-background-primary rounded mb-3 w-3/4" />
              <div className="h-4 bg-background-primary rounded mb-2 w-full" />
              <div className="h-4 bg-background-primary rounded w-5/6" />
            </div>
          ))}
        </div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 bg-background-secondary border-2 border-border-primary rounded-lg">
          <MessageSquare size={48} className="mx-auto text-text-tertiary mb-4" />
          <p className="text-text-secondary mb-4">No posts yet in this category</p>
          {user && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-4 py-2 bg-accent-red text-white rounded-lg hover:bg-red-700 transition-all"
            >
              Be the first to post
            </button>
          )}
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {posts.map((post) => (
              <a key={post.id} href={`/forum/posts/${post.id}`} className="block">
                <PostCard
                  post={post}
                  showReplyButton={false}
                  variant="compact"
                />
              </a>
            ))}
          </div>

          {/* Load more button */}
          {hasMore && (
            <div className="mt-6 text-center">
              <button
                onClick={handleLoadMore}
                disabled={isLoading}
                className="
                  px-6 py-3 bg-background-secondary border-2 border-border-primary
                  text-text-primary font-medium rounded-lg
                  hover:border-accent-red transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                {isLoading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </>
      )}

      {/* Create post modal */}
      <CreatePostForm
        postType="discussion"
        categoryId={category.id}
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={handlePostCreated}
      />
    </div>
  );
}
