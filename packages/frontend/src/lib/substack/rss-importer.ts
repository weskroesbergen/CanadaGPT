/**
 * Substack RSS Importer
 *
 * Fetches and imports articles from Substack RSS feeds
 */

import { createClient } from '@supabase/supabase-js';
import Parser from 'rss-parser';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const parser = new Parser({
  customFields: {
    item: [
      ['content:encoded', 'contentEncoded'],
      ['media:content', 'mediaContent'],
    ],
  },
});

interface ImportResult {
  success: boolean;
  error?: string;
  imported_count: number;
  updated_count: number;
  skipped_count: number;
}

/**
 * Import articles from user's Substack RSS feed
 */
export async function importSubstackRSS(userId: string): Promise<ImportResult> {
  try {
    // Get user's Substack profile
    const { data: profile, error: profileError } = await supabase
      .from('user_substack_profiles')
      .select('*')
      .eq('user_id', userId)
      .single();

    if (profileError || !profile) {
      return {
        success: false,
        error: 'Substack profile not found',
        imported_count: 0,
        updated_count: 0,
        skipped_count: 0,
      };
    }

    // Fetch RSS feed
    let feed;
    try {
      feed = await parser.parseURL(profile.rss_feed_url);
    } catch (error) {
      console.error('Error fetching RSS feed:', error);
      return {
        success: false,
        error: 'Failed to fetch RSS feed',
        imported_count: 0,
        updated_count: 0,
        skipped_count: 0,
      };
    }

    let imported_count = 0;
    let updated_count = 0;
    let skipped_count = 0;

    // Process each article
    for (const item of feed.items) {
      try {
        const articleUrl = item.link || item.guid || '';
        if (!articleUrl) {
          skipped_count++;
          continue;
        }

        // Extract data from RSS item
        const title = item.title || 'Untitled';
        const author = item.creator || (item as any)['dc:creator'] || feed.title || '';
        const published_at = item.pubDate ? new Date(item.pubDate).toISOString() : new Date().toISOString();
        const excerpt = item.contentSnippet?.substring(0, 500) || item.summary || '';
        const content_html = (item as any).contentEncoded || item.content || '';

        // Extract cover image
        let cover_image_url = null;
        if (item.enclosure?.url) {
          cover_image_url = item.enclosure.url;
        } else if ((item as any).mediaContent?.$ ?.url) {
          cover_image_url = (item as any).mediaContent.$.url;
        } else if (item['media:content']?.$ ?.url) {
          cover_image_url = item['media:content'].$.url;
        }

        // Calculate reading time (rough estimate: 200 words per minute)
        const word_count = content_html.split(/\s+/).length;
        const read_time_minutes = Math.max(1, Math.round(word_count / 200));

        // Check if article already exists
        const { data: existing } = await supabase
          .from('substack_articles')
          .select('id')
          .eq('user_id', userId)
          .eq('article_url', articleUrl)
          .maybeSingle();

        if (existing) {
          // Update existing article
          const { error: updateError } = await supabase
            .from('substack_articles')
            .update({
              title,
              author,
              published_at,
              excerpt,
              content_html,
              cover_image_url,
              word_count,
              read_time_minutes,
              guid: item.guid || null,
            })
            .eq('id', existing.id);

          if (!updateError) {
            updated_count++;
          } else {
            console.error('Error updating article:', updateError);
            skipped_count++;
          }
        } else {
          // Insert new article
          const { error: insertError } = await supabase
            .from('substack_articles')
            .insert({
              user_id: userId,
              title,
              author,
              article_url: articleUrl,
              published_at,
              excerpt,
              content_html,
              cover_image_url,
              word_count,
              read_time_minutes,
              guid: item.guid || null,
            });

          if (!insertError) {
            imported_count++;
          } else {
            console.error('Error inserting article:', insertError);
            skipped_count++;
          }
        }
      } catch (error) {
        console.error('Error processing article:', error);
        skipped_count++;
      }
    }

    // Update last_imported_at
    await supabase
      .from('user_substack_profiles')
      .update({ last_imported_at: new Date().toISOString() })
      .eq('user_id', userId);

    // Update author name if available
    if (feed.title && !profile.author_name) {
      await supabase
        .from('user_substack_profiles')
        .update({ author_name: feed.title })
        .eq('user_id', userId);
    }

    return {
      success: true,
      imported_count,
      updated_count,
      skipped_count,
    };
  } catch (error) {
    console.error('Error in importSubstackRSS:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
      imported_count: 0,
      updated_count: 0,
      skipped_count: 0,
    };
  }
}

/**
 * Import articles for all users that need it (based on auto_import schedule)
 */
export async function importAllScheduled(): Promise<{
  success: number;
  failed: number;
}> {
  try {
    // Get users needing import
    const { data: users, error } = await supabase.rpc('get_users_needing_import');

    if (error) {
      console.error('Error fetching users needing import:', error);
      return { success: 0, failed: 0 };
    }

    if (!users || users.length === 0) {
      return { success: 0, failed: 0 };
    }

    let success = 0;
    let failed = 0;

    // Import for each user
    for (const user of users) {
      const result = await importSubstackRSS(user.user_id);
      if (result.success) {
        success++;
      } else {
        failed++;
      }

      // Rate limit: wait 1 second between imports to be respectful
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return { success, failed };
  } catch (error) {
    console.error('Error in importAllScheduled:', error);
    return { success: 0, failed: 0 };
  }
}
