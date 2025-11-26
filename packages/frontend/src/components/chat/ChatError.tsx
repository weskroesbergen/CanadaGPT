/**
 * ChatError Component
 *
 * Displays error messages from the chat store with:
 * - Error icon and message
 * - Dismiss button
 * - Auto-dismiss after 5 seconds
 * - Different styles for different error types
 */

'use client';

import React from 'react';
import { AlertCircle, X } from 'lucide-react';
import { useChatStore } from '@/lib/stores/chatStore';

export function ChatError() {
  const error = useChatStore((state) => state.error);
  const setError = useChatStore((state) => state.setError);
  const [isVisible, setIsVisible] = React.useState(false);

  // Show/hide error with animation
  React.useEffect(() => {
    if (error) {
      setIsVisible(true);

      // Auto-dismiss after 5 seconds
      const timer = setTimeout(() => {
        handleDismiss();
      }, 5000);

      return () => clearTimeout(timer);
    } else {
      setIsVisible(false);
    }
  }, [error]);

  const handleDismiss = () => {
    setIsVisible(false);
    // Wait for animation to complete before clearing error
    setTimeout(() => {
      setError(null);
    }, 300);
  };

  if (!error) return null;

  // Determine error type and styling
  const isQuotaError = error.toLowerCase().includes('quota') || error.toLowerCase().includes('limit');
  const isAuthError = error.toLowerCase().includes('authentication') || error.toLowerCase().includes('not authenticated');

  return (
    <div
      className={`
        fixed top-4 left-1/2 transform -translate-x-1/2 z-50
        max-w-md w-full mx-4
        transition-all duration-300 ease-in-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2 pointer-events-none'}
      `}
    >
      <div className="bg-red-900/90 backdrop-blur-sm border border-red-700 rounded-lg shadow-lg">
        <div className="flex items-start gap-3 p-4">
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            <AlertCircle className="w-5 h-5 text-red-400" />
          </div>

          {/* Error Message */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-red-100">
              {isQuotaError && 'Quota Exceeded'}
              {isAuthError && 'Authentication Error'}
              {!isQuotaError && !isAuthError && 'Error'}
            </p>
            <p className="mt-1 text-sm text-red-200">
              {error}
            </p>
          </div>

          {/* Dismiss Button */}
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 p-1 hover:bg-red-800 rounded transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4 text-red-300" />
          </button>
        </div>
      </div>
    </div>
  );
}
