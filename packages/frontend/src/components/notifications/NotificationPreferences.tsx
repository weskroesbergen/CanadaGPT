/**
 * NotificationPreferences Component
 *
 * Settings panel for managing notification preferences
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface NotificationPrefs {
  email_enabled: boolean;
  push_enabled: boolean;
  in_app_enabled: boolean;
  notify_new_messages: boolean;
  notify_new_followers: boolean;
  notify_mentions: boolean;
  notify_replies: boolean;
  notify_likes: boolean;
  notify_comments: boolean;
  email_digest_frequency: 'never' | 'daily' | 'weekly';
}

export function NotificationPreferences() {
  const [preferences, setPreferences] = useState<NotificationPrefs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Fetch preferences
  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/notifications/preferences');
      if (!response.ok) throw new Error('Failed to fetch preferences');

      const data = await response.json();
      setPreferences(data.preferences);
    } catch (error) {
      console.error('Error fetching preferences:', error);
      toast.error('Failed to load notification preferences');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!preferences) return;

    setSaving(true);
    try {
      const response = await fetch('/api/notifications/preferences', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      });

      if (!response.ok) throw new Error('Failed to save preferences');

      toast.success('Notification preferences saved');
    } catch (error) {
      console.error('Error saving preferences:', error);
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const updatePref = <K extends keyof NotificationPrefs>(
    key: K,
    value: NotificationPrefs[K]
  ) => {
    setPreferences((prev) => (prev ? { ...prev, [key]: value } : null));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!preferences) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Failed to load preferences
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Notification Preferences</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage how you receive notifications
        </p>
      </div>

      {/* Channels */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Notification Channels</h3>

        <label className="flex items-center justify-between">
          <div>
            <p className="font-medium">In-App Notifications</p>
            <p className="text-sm text-muted-foreground">
              Show notifications in the app
            </p>
          </div>
          <input
            type="checkbox"
            checked={preferences.in_app_enabled}
            onChange={(e) => updatePref('in_app_enabled', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <div>
            <p className="font-medium">Email Notifications</p>
            <p className="text-sm text-muted-foreground">
              Receive notifications via email
            </p>
          </div>
          <input
            type="checkbox"
            checked={preferences.email_enabled}
            onChange={(e) => updatePref('email_enabled', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <div>
            <p className="font-medium">Push Notifications</p>
            <p className="text-sm text-muted-foreground">
              Receive browser push notifications
            </p>
          </div>
          <input
            type="checkbox"
            checked={preferences.push_enabled}
            onChange={(e) => updatePref('push_enabled', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>
      </div>

      {/* Notification Types */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Notification Types</h3>

        <label className="flex items-center justify-between">
          <span>New Messages</span>
          <input
            type="checkbox"
            checked={preferences.notify_new_messages}
            onChange={(e) => updatePref('notify_new_messages', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <span>New Followers</span>
          <input
            type="checkbox"
            checked={preferences.notify_new_followers}
            onChange={(e) => updatePref('notify_new_followers', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <span>Mentions (@username)</span>
          <input
            type="checkbox"
            checked={preferences.notify_mentions}
            onChange={(e) => updatePref('notify_mentions', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <span>Replies to your posts</span>
          <input
            type="checkbox"
            checked={preferences.notify_replies}
            onChange={(e) => updatePref('notify_replies', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <span>Likes on your content</span>
          <input
            type="checkbox"
            checked={preferences.notify_likes}
            onChange={(e) => updatePref('notify_likes', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>

        <label className="flex items-center justify-between">
          <span>Comments on your content</span>
          <input
            type="checkbox"
            checked={preferences.notify_comments}
            onChange={(e) => updatePref('notify_comments', e.target.checked)}
            className="h-4 w-4 rounded"
          />
        </label>
      </div>

      {/* Email Digest */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Email Digest</h3>
        <p className="text-sm text-muted-foreground">
          Receive a summary of notifications via email
        </p>

        <select
          value={preferences.email_digest_frequency}
          onChange={(e) =>
            updatePref('email_digest_frequency', e.target.value as 'never' | 'daily' | 'weekly')
          }
          className="w-full rounded-md border border-input bg-background px-3 py-2"
        >
          <option value="never">Never</option>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
        </select>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Save Preferences'
          )}
        </Button>
      </div>
    </div>
  );
}
