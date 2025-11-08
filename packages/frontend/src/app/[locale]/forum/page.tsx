import { Suspense } from 'react';
import { MessageSquare, TrendingUp, Users } from 'lucide-react';
import { getCategories } from '@/actions/forum';

// Force dynamic rendering due to cookies usage in server actions
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Forum - CanadaGPT',
  description: 'Discuss Canadian politics, bills, and parliamentary affairs',
};

async function ForumCategories() {
  const result = await getCategories();
  const categories = result.success ? result.data || [] : [];

  if (categories.length === 0) {
    return (
      <div className="text-center py-12">
        <MessageSquare size={48} className="mx-auto text-text-tertiary mb-4" />
        <p className="text-text-secondary">No categories available</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {categories.map((category) => (
        <a
          key={category.id}
          href={`/forum/${category.slug}`}
          className="
            bg-background-secondary border-2 border-border-primary
            rounded-lg p-6 hover:border-accent-red
            transition-all group
          "
        >
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-text-primary group-hover:text-accent-red transition-colors">
              {category.name}
            </h3>
            <MessageSquare
              size={24}
              className="text-text-tertiary group-hover:text-accent-red transition-colors"
            />
          </div>

          {category.description && (
            <p className="text-text-secondary text-sm mb-4 line-clamp-2">
              {category.description}
            </p>
          )}

          <div className="flex items-center gap-4 text-sm text-text-tertiary">
            <div className="flex items-center gap-1">
              <MessageSquare size={14} />
              <span>{category.post_count || 0} posts</span>
            </div>
            {category.post_count > 0 && category.last_post_at && (
              <div className="text-xs">
                Last: {new Date(category.last_post_at).toLocaleDateString()}
              </div>
            )}
          </div>
        </a>
      ))}
    </div>
  );
}

function CategoriesLoading() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="bg-background-secondary border-2 border-border-primary rounded-lg p-6 animate-pulse"
        >
          <div className="h-6 bg-background-primary rounded mb-3 w-3/4" />
          <div className="h-4 bg-background-primary rounded mb-2 w-full" />
          <div className="h-4 bg-background-primary rounded mb-4 w-5/6" />
          <div className="h-4 bg-background-primary rounded w-1/2" />
        </div>
      ))}
    </div>
  );
}

export default function ForumPage() {
  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-text-primary mb-3">
          Community Forum
        </h1>
        <p className="text-text-secondary text-lg">
          Discuss Canadian politics, bills, and parliamentary affairs with the community
        </p>
      </div>

      {/* Stats banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-4">
          <div className="flex items-center gap-3">
            <MessageSquare size={24} className="text-accent-red" />
            <div>
              <div className="text-2xl font-bold text-text-primary">
                {/* TODO: Fetch from API */}
                ---
              </div>
              <div className="text-sm text-text-tertiary">Total Posts</div>
            </div>
          </div>
        </div>

        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-4">
          <div className="flex items-center gap-3">
            <Users size={24} className="text-accent-red" />
            <div>
              <div className="text-2xl font-bold text-text-primary">
                {/* TODO: Fetch from API */}
                ---
              </div>
              <div className="text-sm text-text-tertiary">Active Members</div>
            </div>
          </div>
        </div>

        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-4">
          <div className="flex items-center gap-3">
            <TrendingUp size={24} className="text-accent-red" />
            <div>
              <div className="text-2xl font-bold text-text-primary">
                {/* TODO: Fetch from API */}
                ---
              </div>
              <div className="text-sm text-text-tertiary">Posts Today</div>
            </div>
          </div>
        </div>
      </div>

      {/* Categories */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-text-primary mb-4">Categories</h2>
        <Suspense fallback={<CategoriesLoading />}>
          <ForumCategories />
        </Suspense>
      </div>

      {/* Guidelines */}
      <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6">
        <h3 className="text-lg font-bold text-text-primary mb-3">
          Community Guidelines
        </h3>
        <ul className="text-text-secondary space-y-2 text-sm">
          <li>• Be respectful and constructive in all discussions</li>
          <li>• Stay on topic and provide evidence for claims</li>
          <li>• No spam, harassment, or misinformation</li>
          <li>• Follow Canadian parliamentary decorum standards</li>
          <li>• Report inappropriate content to moderators</li>
        </ul>
      </div>
    </div>
  );
}
