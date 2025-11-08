'use client';

import { useState, useEffect } from 'react';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Ban,
  Lock,
  Unlock,
  Pin,
  Trash2,
  Eye,
  Filter
} from 'lucide-react';
import {
  getPendingReports,
  resolveReport,
  moderatePost,
  getModerationStats,
} from '@/actions/moderation';
import type { ModerationReport } from '@/types/forum';
import { useRouter } from 'next/navigation';

type FilterOption = 'all' | 'spam' | 'harassment' | 'misinformation' | 'off_topic' | 'other';

export default function ModerationDashboard() {
  const router = useRouter();
  const [reports, setReports] = useState<ModerationReport[]>([]);
  const [stats, setStats] = useState({
    pending_reports: 0,
    resolved_today: 0,
    total_actions: 0,
    deleted_posts: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<FilterOption>('all');
  const [selectedReport, setSelectedReport] = useState<ModerationReport | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Fetch reports and stats
  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);

    const [reportsResult, statsResult] = await Promise.all([
      getPendingReports(50, 0),
      getModerationStats(),
    ]);

    if (reportsResult.success && reportsResult.data) {
      setReports(reportsResult.data.data);
    } else {
      // If unauthorized, redirect to home
      if (reportsResult.error?.includes('Admin access required')) {
        alert('Admin access required');
        router.push('/');
        return;
      }
    }

    if (statsResult.success && statsResult.data) {
      setStats(statsResult.data);
    }

    setIsLoading(false);
  };

  const handleResolve = async (reportId: string, status: 'resolved' | 'dismissed', notes?: string) => {
    setIsProcessing(true);

    const result = await resolveReport({
      report_id: reportId,
      status,
      admin_notes: notes,
    });

    if (result.success) {
      // Remove from list
      setReports(reports.filter((r) => r.id !== reportId));
      setStats((prev) => ({
        ...prev,
        pending_reports: prev.pending_reports - 1,
        resolved_today: prev.resolved_today + 1,
      }));
      setSelectedReport(null);
    } else {
      alert(result.error || 'Failed to resolve report');
    }

    setIsProcessing(false);
  };

  const handleModeratePost = async (
    postId: string,
    action: 'delete' | 'lock' | 'unlock' | 'pin' | 'unpin' | 'warn',
    reason?: string
  ) => {
    setIsProcessing(true);

    const result = await moderatePost({
      post_id: postId,
      action,
      reason,
    });

    if (result.success) {
      setStats((prev) => ({
        ...prev,
        total_actions: prev.total_actions + 1,
        deleted_posts: action === 'delete' ? prev.deleted_posts + 1 : prev.deleted_posts,
      }));
    } else {
      alert(result.error || 'Failed to moderate post');
    }

    setIsProcessing(false);
  };

  const filteredReports = reports.filter((report) => {
    if (filter === 'all') return true;
    return report.reason === filter;
  });

  const getReasonBadgeColor = (reason: string) => {
    switch (reason) {
      case 'spam':
        return 'bg-yellow-500/20 text-yellow-400';
      case 'harassment':
        return 'bg-red-500/20 text-red-400';
      case 'misinformation':
        return 'bg-orange-500/20 text-orange-400';
      case 'off_topic':
        return 'bg-blue-500/20 text-blue-400';
      default:
        return 'bg-gray-500/20 text-gray-400';
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="text-center py-12">
          <p className="text-text-secondary">Loading moderation dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Shield size={32} className="text-accent-red" />
          <h1 className="text-4xl font-bold text-text-primary">Moderation Dashboard</h1>
        </div>
        <p className="text-text-secondary">Manage community reports and content moderation</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle size={24} className="text-yellow-500" />
            <div>
              <div className="text-3xl font-bold text-text-primary">{stats.pending_reports}</div>
              <div className="text-sm text-text-tertiary">Pending Reports</div>
            </div>
          </div>
        </div>

        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <CheckCircle size={24} className="text-green-500" />
            <div>
              <div className="text-3xl font-bold text-text-primary">{stats.resolved_today}</div>
              <div className="text-sm text-text-tertiary">Resolved Today</div>
            </div>
          </div>
        </div>

        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <Shield size={24} className="text-blue-500" />
            <div>
              <div className="text-3xl font-bold text-text-primary">{stats.total_actions}</div>
              <div className="text-sm text-text-tertiary">Total Actions</div>
            </div>
          </div>
        </div>

        <div className="bg-background-secondary border-2 border-border-primary rounded-lg p-6">
          <div className="flex items-center gap-3 mb-2">
            <Trash2 size={24} className="text-red-500" />
            <div>
              <div className="text-3xl font-bold text-text-primary">{stats.deleted_posts}</div>
              <div className="text-sm text-text-tertiary">Deleted Posts</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        <Filter size={18} className="text-text-tertiary flex-shrink-0" />
        <div className="flex gap-2">
          {(['all', 'spam', 'harassment', 'misinformation', 'off_topic', 'other'] as FilterOption[]).map((option) => (
            <button
              key={option}
              onClick={() => setFilter(option)}
              className={`
                px-4 py-2 rounded-lg font-medium text-sm transition-all whitespace-nowrap
                ${
                  filter === option
                    ? 'bg-accent-red text-white'
                    : 'bg-background-secondary text-text-secondary hover:bg-background-primary'
                }
              `}
            >
              {option === 'all' ? 'All Reports' : option.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Reports List */}
      {filteredReports.length === 0 ? (
        <div className="text-center py-12 bg-background-secondary border-2 border-border-primary rounded-lg">
          <CheckCircle size={48} className="mx-auto text-green-500 mb-4" />
          <p className="text-text-secondary mb-2">No pending reports</p>
          <p className="text-text-tertiary text-sm">All caught up! 🎉</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredReports.map((report) => (
            <div
              key={report.id}
              className="bg-background-secondary border-2 border-border-primary rounded-lg p-6"
            >
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getReasonBadgeColor(report.reason)}`}>
                      {report.reason.replace('_', ' ')}
                    </span>
                    <span className="text-xs text-text-tertiary">
                      Reported {new Date(report.created_at).toLocaleString()}
                    </span>
                  </div>

                  {report.post && (
                    <div className="bg-background-primary border border-border-primary rounded-lg p-4 mb-4">
                      {report.post.title && (
                        <h4 className="font-semibold text-text-primary mb-2">{report.post.title}</h4>
                      )}
                      <p className="text-text-secondary text-sm line-clamp-3">{report.post.content}</p>
                      <div className="flex items-center gap-4 mt-3 text-xs text-text-tertiary">
                        <span>Post ID: {report.post.id.slice(0, 8)}</span>
                        <span>•</span>
                        <span>Author: {report.post.author?.display_name || 'Unknown'}</span>
                      </div>
                    </div>
                  )}

                  <div className="text-sm text-text-tertiary">
                    Reported by: {report.reporter?.display_name || 'Anonymous'}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  <button
                    onClick={() => setSelectedReport(selectedReport?.id === report.id ? null : report)}
                    className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-all flex items-center gap-2"
                  >
                    <Eye size={16} />
                    {selectedReport?.id === report.id ? 'Hide' : 'Review'}
                  </button>
                </div>
              </div>

              {/* Action Panel (expanded) */}
              {selectedReport?.id === report.id && (
                <div className="border-t border-border-primary pt-4 mt-4">
                  <h4 className="font-semibold text-text-primary mb-3">Moderation Actions</h4>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
                    <button
                      onClick={() => {
                        if (confirm('Delete this post?')) {
                          handleModeratePost(report.post_id, 'delete', `Violated rule: ${report.reason}`);
                          handleResolve(report.id, 'resolved', 'Post deleted');
                        }
                      }}
                      disabled={isProcessing}
                      className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all disabled:opacity-50"
                    >
                      <Trash2 size={16} />
                      Delete
                    </button>

                    <button
                      onClick={() => {
                        handleModeratePost(report.post_id, 'lock', 'Locked due to report');
                        handleResolve(report.id, 'resolved', 'Post locked');
                      }}
                      disabled={isProcessing}
                      className="flex items-center gap-2 px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-all disabled:opacity-50"
                    >
                      <Lock size={16} />
                      Lock
                    </button>

                    <button
                      onClick={() => {
                        handleModeratePost(report.post_id, 'warn', 'Warning issued');
                        handleResolve(report.id, 'resolved', 'Warning issued to author');
                      }}
                      disabled={isProcessing}
                      className="flex items-center gap-2 px-3 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all disabled:opacity-50"
                    >
                      <AlertTriangle size={16} />
                      Warn
                    </button>

                    <button
                      onClick={() => handleResolve(report.id, 'dismissed', 'No violation found')}
                      disabled={isProcessing}
                      className="flex items-center gap-2 px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-all disabled:opacity-50"
                    >
                      <XCircle size={16} />
                      Dismiss
                    </button>
                  </div>

                  <a
                    href={`/forum/posts/${report.post_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent-red hover:underline text-sm flex items-center gap-1"
                  >
                    <Eye size={14} />
                    View full post in new tab
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
