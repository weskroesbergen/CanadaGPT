/**
 * useMobileDetect Hook
 * Detects mobile devices and provides responsive utilities
 */

'use client';

import { useState, useEffect } from 'react';

interface MobileDetection {
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isTouchDevice: boolean;
  isIOS: boolean;
  isAndroid: boolean;
  screenWidth: number;
  screenHeight: number;
  orientation: 'portrait' | 'landscape';
}

export function useMobileDetect(): MobileDetection {
  const [detection, setDetection] = useState<MobileDetection>({
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    isTouchDevice: false,
    isIOS: false,
    isAndroid: false,
    screenWidth: typeof window !== 'undefined' ? window.innerWidth : 1024,
    screenHeight: typeof window !== 'undefined' ? window.innerHeight : 768,
    orientation: 'landscape',
  });

  useEffect(() => {
    const detectDevice = () => {
      if (typeof window === 'undefined') return;

      const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
      const screenWidth = window.innerWidth;
      const screenHeight = window.innerHeight;

      // Detect mobile devices
      const isMobileUA =
        /android|webos|iphone|ipod|blackberry|iemobile|opera mini/i.test(userAgent);
      const isMobileWidth = screenWidth < 768;
      const isMobile = isMobileUA || isMobileWidth;

      // Detect tablet
      const isTabletUA = /ipad|tablet|(android(?!.*mobile))/i.test(userAgent);
      const isTabletWidth = screenWidth >= 768 && screenWidth < 1024;
      const isTablet = isTabletUA || isTabletWidth;

      // Detect desktop
      const isDesktop = !isMobile && !isTablet;

      // Detect touch device
      const isTouchDevice =
        'ontouchstart' in window ||
        navigator.maxTouchPoints > 0 ||
        (navigator as any).msMaxTouchPoints > 0;

      // Detect OS
      const isIOS = /iPad|iPhone|iPod/.test(userAgent) && !(window as any).MSStream;
      const isAndroid = /android/i.test(userAgent);

      // Detect orientation
      const orientation = screenWidth > screenHeight ? 'landscape' : 'portrait';

      setDetection({
        isMobile,
        isTablet,
        isDesktop,
        isTouchDevice,
        isIOS,
        isAndroid,
        screenWidth,
        screenHeight,
        orientation,
      });
    };

    // Initial detection
    detectDevice();

    // Re-detect on resize
    window.addEventListener('resize', detectDevice);
    window.addEventListener('orientationchange', detectDevice);

    return () => {
      window.removeEventListener('resize', detectDevice);
      window.removeEventListener('orientationchange', detectDevice);
    };
  }, []);

  return detection;
}
