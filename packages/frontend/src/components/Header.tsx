/**
 * Global header component with navigation
 * Supports internationalization with language switching
 */

'use client';

import { Link } from '@/i18n/navigation';
import { MapleLeafIcon } from '@canadagpt/design-system';
import { Search, Menu } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { UserMenu } from './UserMenu';
import { LanguageSwitcher } from './LanguageSwitcher';

export function Header() {
  const t = useTranslations('nav');
  const tCommon = useTranslations('common');

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border-subtle bg-bg-primary/95 backdrop-blur supports-[backdrop-filter]:bg-bg-primary/60">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2 lg:space-x-3 hover:opacity-80 transition-opacity flex-shrink-0">
            <MapleLeafIcon size={32} className="h-8 w-8 text-accent-red" />
            <div className="flex flex-col">
              <span className="text-lg lg:text-xl font-bold text-text-primary">{t('siteTitle')}</span>
              <span className="text-xs text-text-tertiary hidden lg:block">{t('tagline')}</span>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-3 lg:space-x-5 flex-shrink min-w-0">
            <Link href="/dashboard" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('dashboard')}
            </Link>
            <Link href="/mps" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('mps')}
            </Link>
            <Link href="/chamber" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('chamber')}
            </Link>
            <Link href="/committees" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('committees')}
            </Link>
            <Link href="/bills" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('bills')}
            </Link>
            <Link href="/hansard" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('speeches')}
            </Link>
            <Link href="/about" className="text-text-secondary hover:text-text-primary transition-colors whitespace-nowrap text-xs lg:text-sm">
              {t('about')}
            </Link>
          </nav>

          {/* Actions */}
          <div className="flex items-center space-x-2 lg:space-x-4 flex-shrink-0">
            <button
              className="p-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
              aria-label={tCommon('search')}
            >
              <Search className="h-5 w-5" />
            </button>
            <UserMenu />
            <LanguageSwitcher />
            <button
              className="md:hidden p-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
              aria-label="Menu"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
