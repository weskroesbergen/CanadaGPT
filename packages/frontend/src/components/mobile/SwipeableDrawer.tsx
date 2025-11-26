/**
 * SwipeableDrawer - Bottom Sheet Drawer with Swipe Gestures
 * Used for filters, options, and voice chat
 */

'use client';

import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import { useSimpleSwipe } from '@/hooks/useSwipeGesture';

interface SwipeableDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  height?: 'half' | 'full' | 'auto';
}

export function SwipeableDrawer({
  isOpen,
  onClose,
  title,
  children,
  height = 'half',
}: SwipeableDrawerProps) {
  const swipeHandlers = useSimpleSwipe({
    onSwipeDown: onClose,
    threshold: 75,
  });

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const getHeightClass = () => {
    switch (height) {
      case 'full':
        return 'swipeable-drawer-full';
      case 'auto':
        return 'swipeable-drawer-auto';
      default:
        return 'swipeable-drawer-half';
    }
  };

  return (
    <>
      {/* Overlay */}
      <div className="swipeable-drawer-overlay" onClick={onClose} />

      {/* Drawer */}
      <div className={`swipeable-drawer ${getHeightClass()}`}>
        {/* Drag Handle */}
        <div className="swipeable-drawer-handle" {...swipeHandlers}>
          <div className="swipeable-drawer-handle-bar" />
        </div>

        {/* Header */}
        {title && (
          <div className="swipeable-drawer-header">
            <h2 className="swipeable-drawer-title">{title}</h2>
            <button
              onClick={onClose}
              className="swipeable-drawer-close"
              aria-label="Close"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        )}

        {/* Content */}
        <div className="swipeable-drawer-content">
          {children}
        </div>
      </div>
    </>
  );
}
