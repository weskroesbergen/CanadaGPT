/**
 * Global footer component with internationalization support
 */

'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { MapleLeafIcon } from '@canadagpt/design-system';

export function Footer() {
  const t = useTranslations('footer');
  const tNav = useTranslations('nav');

  const currentYear = new Date().getFullYear();

  return (
    <footer className="mt-auto border-t border-border-subtle bg-bg-secondary">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center space-x-3 mb-4">
              <MapleLeafIcon size={24} className="h-6 w-6 text-accent-red" />
              <span className="text-lg font-bold text-text-primary">{tNav('siteTitle')}</span>
            </div>
            <p className="text-sm text-text-secondary max-w-md">
              {t('description')}
            </p>
            <p className="text-xs text-text-tertiary mt-2">
              {t('openSource')}
            </p>
          </div>

          {/* Navigation */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-4">{t('navigation')}</h3>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li>
                <Link href="/dashboard" className="hover:text-text-primary transition-colors">
                  {tNav('dashboard')}
                </Link>
              </li>
              <li>
                <Link href="/mps" className="hover:text-text-primary transition-colors">
                  {tNav('mps')}
                </Link>
              </li>
              <li>
                <Link href="/bills" className="hover:text-text-primary transition-colors">
                  {tNav('bills')}
                </Link>
              </li>
              <li>
                <Link href="/lobbying" className="hover:text-text-primary transition-colors">
                  {tNav('lobbying')}
                </Link>
              </li>
            </ul>
          </div>

          {/* About */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-4">{t('about')}</h3>
            <ul className="space-y-2 text-sm text-text-secondary">
              <li>
                <Link href="/about" className="hover:text-text-primary transition-colors">
                  {tNav('about')}
                </Link>
              </li>
              <li>
                <Link href="/contact" className="hover:text-text-primary transition-colors">
                  {t('contact')}
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-text-primary transition-colors">
                  {t('privacy')}
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/matthewdufresne/FedMCP"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-text-primary transition-colors"
                >
                  GitHub
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-8 pt-8 border-t border-border-subtle">
          <p className="text-xs text-text-tertiary text-center">
            {t('copyright', { year: currentYear })}
          </p>
        </div>
      </div>
    </footer>
  );
}
