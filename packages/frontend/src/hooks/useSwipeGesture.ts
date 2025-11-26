/**
 * useSwipeGesture Hook
 * Provides swipe gesture detection for mobile UI
 */

'use client';

import { useGesture } from '@use-gesture/react';
import { useRef } from 'react';

interface SwipeConfig {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  threshold?: number; // Minimum distance in pixels
  velocityThreshold?: number; // Minimum velocity
}

export function useSwipeGesture(config: SwipeConfig) {
  const {
    onSwipeLeft,
    onSwipeRight,
    onSwipeUp,
    onSwipeDown,
    threshold = 50,
    velocityThreshold = 0.3,
  } = config;

  const bind = useGesture({
    onDrag: ({ direction: [xDir, yDir], distance, velocity, cancel }) => {
      const [xVelocity, yVelocity] = velocity;
      const [xDistance, yDistance] = distance;

      // Horizontal swipe
      if (Math.abs(xDir) > Math.abs(yDir)) {
        if (xDistance > threshold && xVelocity > velocityThreshold) {
          if (xDir > 0 && onSwipeRight) {
            onSwipeRight();
            cancel();
          } else if (xDir < 0 && onSwipeLeft) {
            onSwipeLeft();
            cancel();
          }
        }
      }
      // Vertical swipe
      else {
        if (yDistance > threshold && yVelocity > velocityThreshold) {
          if (yDir > 0 && onSwipeDown) {
            onSwipeDown();
            cancel();
          } else if (yDir < 0 && onSwipeUp) {
            onSwipeUp();
            cancel();
          }
        }
      }
    },
  });

  return bind;
}

/**
 * Simple touch-based swipe detection (no dependencies)
 */
export function useSimpleSwipe(config: SwipeConfig) {
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(null);

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;

    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    const deltaTime = Date.now() - touchStartRef.current.time;

    const threshold = config.threshold || 50;
    const velocityThreshold = config.velocityThreshold || 0.3;

    // Calculate velocity (pixels per millisecond)
    const velocity = Math.sqrt(deltaX ** 2 + deltaY ** 2) / deltaTime;

    // Determine direction
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      // Horizontal swipe
      if (Math.abs(deltaX) > threshold && velocity > velocityThreshold) {
        if (deltaX > 0 && config.onSwipeRight) {
          config.onSwipeRight();
        } else if (deltaX < 0 && config.onSwipeLeft) {
          config.onSwipeLeft();
        }
      }
    } else {
      // Vertical swipe
      if (Math.abs(deltaY) > threshold && velocity > velocityThreshold) {
        if (deltaY > 0 && config.onSwipeDown) {
          config.onSwipeDown();
        } else if (deltaY < 0 && config.onSwipeUp) {
          config.onSwipeUp();
        }
      }
    }

    touchStartRef.current = null;
  };

  return {
    onTouchStart: handleTouchStart,
    onTouchEnd: handleTouchEnd,
  };
}
