'use client';

import { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { reportPost } from '@/actions/moderation';
import type { ReportReason } from '@/types/forum';

interface ReportModalProps {
  postId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const REPORT_REASONS: { value: ReportReason; label: string; description: string }[] = [
  {
    value: 'spam',
    label: 'Spam or advertising',
    description: 'Unwanted promotional content or repetitive posts',
  },
  {
    value: 'harassment',
    label: 'Harassment or hate speech',
    description: 'Targeting individuals or groups with abuse',
  },
  {
    value: 'misinformation',
    label: 'Misinformation',
    description: 'Deliberately false or misleading information',
  },
  {
    value: 'off_topic',
    label: 'Off-topic',
    description: 'Not relevant to the discussion or category',
  },
  {
    value: 'other',
    label: 'Other',
    description: 'Other rule violation (explain below)',
  },
];

export function ReportModal({ postId, isOpen, onClose, onSuccess }: ReportModalProps) {
  const [selectedReason, setSelectedReason] = useState<ReportReason | ''>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedReason) {
      setError('Please select a reason for reporting');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await reportPost({
        post_id: postId,
        reason: selectedReason,
      });

      if (result.success) {
        onSuccess?.();
        onClose();
        // Reset form
        setSelectedReason('');
      } else {
        setError(result.error || 'Failed to submit report');
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
      console.error('Report submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setSelectedReason('');
      setError(null);
      onClose();
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="
            bg-background-secondary border-2 border-border-primary rounded-lg
            max-w-md w-full max-h-[90vh] overflow-y-auto
            shadow-2xl
          "
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-primary">
            <div className="flex items-center gap-3">
              <AlertTriangle className="text-accent-red" size={24} />
              <h2 className="text-xl font-bold text-text-primary">Report Post</h2>
            </div>
            <button
              onClick={handleClose}
              disabled={isSubmitting}
              className="text-text-tertiary hover:text-text-primary transition-colors disabled:opacity-50"
              aria-label="Close"
            >
              <X size={24} />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6">
            <p className="text-text-secondary mb-6">
              Please select the reason you're reporting this post. Our moderation team will
              review your report.
            </p>

            {/* Reason selection */}
            <div className="space-y-3 mb-6">
              {REPORT_REASONS.map((reason) => (
                <label
                  key={reason.value}
                  className={`
                    block p-4 rounded-lg border-2 cursor-pointer transition-all
                    ${
                      selectedReason === reason.value
                        ? 'border-accent-red bg-accent-red/10'
                        : 'border-border-primary hover:border-border-hover'
                    }
                  `}
                >
                  <input
                    type="radio"
                    name="reason"
                    value={reason.value}
                    checked={selectedReason === reason.value}
                    onChange={(e) => setSelectedReason(e.target.value as ReportReason)}
                    className="sr-only"
                    disabled={isSubmitting}
                  />
                  <div className="flex items-start gap-3">
                    <div
                      className={`
                        w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5
                        ${
                          selectedReason === reason.value
                            ? 'border-accent-red'
                            : 'border-border-primary'
                        }
                      `}
                    >
                      {selectedReason === reason.value && (
                        <div className="w-3 h-3 rounded-full bg-accent-red" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-text-primary mb-1">
                        {reason.label}
                      </div>
                      <div className="text-sm text-text-tertiary">
                        {reason.description}
                      </div>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {/* Error message */}
            {error && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500 rounded-lg">
                <p className="text-red-500 text-sm">{error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleClose}
                disabled={isSubmitting}
                className="
                  flex-1 px-4 py-2 rounded-lg
                  bg-background-primary border-2 border-border-primary
                  text-text-primary font-medium
                  hover:border-border-hover
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !selectedReason}
                className="
                  flex-1 px-4 py-2 rounded-lg
                  bg-accent-red text-white font-medium
                  hover:bg-red-700
                  transition-all
                  disabled:opacity-50 disabled:cursor-not-allowed
                "
              >
                {isSubmitting ? 'Submitting...' : 'Submit Report'}
              </button>
            </div>

            <p className="text-xs text-text-tertiary mt-4 text-center">
              False reports may result in account restrictions
            </p>
          </form>
        </div>
      </div>
    </>
  );
}
