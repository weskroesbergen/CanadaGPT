'use client';

import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { locales } from '@/i18n/config';
import { useTransition } from 'react';

export function LanguageSwitcher() {
  const t = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const handleLanguageChange = (newLocale: string) => {
    startTransition(() => {
      router.replace(pathname, { locale: newLocale });
    });
  };

  return (
    <div className="flex items-center gap-0.5 rounded-md border border-border-subtle bg-bg-secondary p-0.5">
      {locales.map((loc) => (
        <button
          key={loc}
          onClick={() => handleLanguageChange(loc)}
          disabled={isPending}
          className={`
            px-2 py-1 text-xs font-medium rounded transition-colors
            ${
              locale === loc
                ? 'bg-accent-red text-white'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
            }
            ${isPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
          aria-label={loc === 'en' ? t('english') : t('french')}
          aria-current={locale === loc ? 'true' : 'false'}
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
