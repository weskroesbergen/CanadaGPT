/**
 * MobileBottomNav - Bottom Navigation Bar for Mobile
 * Sticky bottom navigation with icon-based tabs
 */

'use client';

import React from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Home, Search, Bookmark, User } from 'lucide-react';

interface NavItem {
  id: string;
  icon: React.ReactNode;
  label: string;
  path: string;
}

interface MobileBottomNavProps {
  locale?: string;
}

export function MobileBottomNav({ locale = 'en' }: MobileBottomNavProps) {
  const router = useRouter();
  const pathname = usePathname();

  const navItems: NavItem[] = [
    {
      id: 'home',
      icon: <Home className="h-6 w-6" />,
      label: 'Home',
      path: `/${locale}`,
    },
    {
      id: 'search',
      icon: <Search className="h-6 w-6" />,
      label: 'Search',
      path: `/${locale}/search`,
    },
    {
      id: 'bookmarks',
      icon: <Bookmark className="h-6 w-6" />,
      label: 'Saved',
      path: `/${locale}/bookmarks`,
    },
    {
      id: 'profile',
      icon: <User className="h-6 w-6" />,
      label: 'Profile',
      path: `/${locale}/dashboard`,
    },
  ];

  const isActive = (path: string) => {
    if (path === `/${locale}`) {
      return pathname === path;
    }
    return pathname?.startsWith(path);
  };

  const handleNavClick = (path: string) => {
    router.push(path);
    // Haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate(10);
    }
  };

  return (
    <nav className="mobile-bottom-nav">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => handleNavClick(item.path)}
          className={`mobile-bottom-nav-item ${isActive(item.path) ? 'active' : ''}`}
          aria-label={item.label}
        >
          <div className="mobile-bottom-nav-icon">{item.icon}</div>
          <span className="mobile-bottom-nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
