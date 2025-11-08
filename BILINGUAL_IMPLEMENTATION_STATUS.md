# Bilingual Implementation Status (English/Quebec French)

**Last Updated:** 2025-11-07
**Progress:** ~60% Complete

## Overview

Comprehensive bilingualization of FedMCP frontend using `next-intl` with `/en/` and `/fr/` URL structure, browser auto-detection, and AI-generated Quebec French translations.

---

## ✅ COMPLETED (Phases 1-3)

### Phase 1: Core Infrastructure ✅

**1. Dependencies & Configuration**
- ✅ Installed `next-intl` (v4.4.0) and `date-fns` (v3.6.0)
- ✅ Created i18n config (`src/i18n/config.ts`) with EN/FR locales
- ✅ Created request handler (`src/i18n/request.ts`)
- ✅ Updated `next.config.mjs` with next-intl plugin

**2. Middleware & Routing**
- ✅ Updated middleware to combine i18n + authentication
- ✅ Configured locale detection from Accept-Language header
- ✅ Set up `/en/` and `/fr/` URL prefixes with `localePrefix: 'always'`
- ✅ Created locale-aware navigation utilities (`src/i18n/navigation.ts`)

**3. App Directory Restructuring**
- ✅ Created `[locale]` folder structure
- ✅ Moved all routes under `/app/[locale]/`
- ✅ Updated root layout to handle locale parameter
- ✅ Implemented `generateStaticParams()` for both locales

### Phase 2: Translation System ✅

**4. Translation Files**
- ✅ Created `messages/en.json` (555+ strings organized by namespace)
- ✅ Created `messages/fr.json` (complete Quebec French translations)
- ✅ Organized by namespaces: `metadata`, `common`, `nav`, `footer`, `home`, `mps`, `bills`, `bill`, `hansard`, `chamber`, `committees`, `lobbying`, `spending`, `chat`, `parties`, `provinces`, `errors`

**5. Core Components**
- ✅ Created `LanguageSwitcher` component (EN/FR toggle in header)
- ✅ Translated `Header` component with i18n navigation
- ✅ Translated `Footer` component with bilingual links
- ✅ Updated locale-specific layout with metadata generation

### Phase 3: GraphQL & Data Layer ✅

**6. GraphQL Query Updates**
- ✅ Updated `BILL_BASIC_FRAGMENT` to fetch all `_fr` fields:
  - `title_fr`, `summary_fr`, `status_fr`, `bill_type_fr`, `originating_chamber_fr`
- ✅ Updated `STATEMENT_FRAGMENT` to fetch all `_fr` fields:
  - `who_fr`, `content_fr`, `h1_fr`, `h2_fr`, `h3_fr`
- ✅ Both fragments now return bilingual data for automatic selection

**7. Bilingual Hooks**
Created comprehensive hooks in `src/hooks/useBilingual.ts`:
- ✅ `useBilingualField(enField, frField)` - Select field based on locale
- ✅ `useBilingualContent(content)` - Transform objects with `_en/_fr` suffixes
- ✅ `useLocaleSuffix()` - Get `_en` or `_fr` for dynamic queries
- ✅ `usePartyName(partyCode)` - Localized party name mapping
- ✅ `useChamberName(chamber)` - Localized chamber names

**8. Pages Translated**
- ✅ **Landing Page** (`app/[locale]/page.tsx`):
  - Hero section, features, stats, CTA - all fully bilingual
  - Uses `useTranslations('home')` hook
  - Locale-aware Link components

---

## 🚧 IN PROGRESS / REMAINING WORK

### Phase 4-6: Page & Component Translation (50% Remaining)

**Pages to Translate:**
- 🔲 MPs page (`app/[locale]/mps/page.tsx`)
- 🔲 Bills page (`app/[locale]/bills/page.tsx`)
- 🔲 Bill detail page (`app/[locale]/bills/[session]/[number]/page.tsx`)
- 🔲 Hansard search page (`app/[locale]/hansard/page.tsx`)
- 🔲 Chamber page (`app/[locale]/chamber/page.tsx`)
- 🔲 Committees page (`app/[locale]/committees/page.tsx`)
- 🔲 Dashboard page
- 🔲 MP profile pages
- 🔲 Lobbying page
- 🔲 Spending page
- 🔲 About page
- 🔲 Forum pages (if applicable)

**Shared Components to Translate:**
- 🔲 `MPCard` component
- 🔲 `BillCard` component
- 🔲 `SearchBar` component
- 🔲 Filter components (party, province, status dropdowns)
- 🔲 `ChatWidget` component
- 🔲 Modal components (MPModal, etc.)
- 🔲 Empty state components
- 🔲 Error boundary components
- 🔲 Loading components

### Phase 7: Data Display Logic

- 🔲 Update all components using bills to use `useBilingualContent()`
- 🔲 Update all components using Hansard to use bilingual fields
- 🔲 Update date formatting with French locale from `date-fns`
- 🔲 Update number formatting (Quebec uses space as thousands separator)
- 🔲 Ensure party names use `usePartyName()` hook
- 🔲 Ensure chamber names use `useChamberName()` hook

### Phase 8: Hansard Search Language Parameter

- 🔲 Update Hansard search page to pass `language` param based on current locale
- 🔲 Currently hardcoded to `'en'` in `hansard/page.tsx:72`
- 🔲 Should use: `const locale = useLocale(); language: locale`

### Phase 9: SEO & Metadata

- 🔲 Add `<link rel="alternate" hreflang="en" />` and `hreflang="fr"` tags
- 🔲 Generate bilingual sitemap with /en/ and /fr/ URLs
- 🔲 Add Open Graph locale tags (`og:locale`, `og:locale:alternate`)
- 🔲 Test locale detection across browsers
- 🔲 Verify metadata is correctly set per locale

### Phase 10: Testing & QA

- 🔲 Test all routes in both /en/ and /fr/
- 🔲 Test language switcher preserves current page/filters
- 🔲 Verify bilingual data displays correctly (bills, Hansard)
- 🔲 Test fallback behavior (French data missing → shows English)
- 🔲 Cross-browser testing for locale detection
- 🔲 Performance check (ensure translation files don't bloat bundle)
- 🔲 Accessibility testing (lang attribute updates, screen readers)

---

## 📁 Key Files Modified/Created

### Created Files:
- `/src/i18n/config.ts` - Locale configuration
- `/src/i18n/request.ts` - Request handler for next-intl
- `/src/i18n/navigation.ts` - Locale-aware navigation utilities
- `/src/hooks/useBilingual.ts` - Bilingual data selection hooks
- `/src/components/LanguageSwitcher.tsx` - Language toggle component
- `/messages/en.json` - English translations (555+ strings)
- `/messages/fr.json` - Quebec French translations (555+ strings)
- `/migrate-to-locale.sh` - Migration script (can be deleted)

### Modified Files:
- `/src/middleware.ts` - Combined i18n + auth middleware
- `/next.config.mjs` - Added next-intl plugin
- `/src/app/[locale]/layout.tsx` - Locale-aware layout
- `/src/components/Header.tsx` - Translated with i18n
- `/src/components/Footer.tsx` - Translated with i18n
- `/src/lib/queries.ts` - Updated fragments for bilingual fields
- `/src/app/[locale]/page.tsx` - Translated landing page

### App Directory Structure:
```
src/app/
├── api/ (unchanged, not localized)
└── [locale]/
    ├── layout.tsx (locale-aware)
    ├── page.tsx (landing page - ✅ translated)
    ├── mps/
    ├── bills/
    ├── hansard/
    ├── chamber/
    ├── committees/
    ├── dashboard/
    ├── lobbying/
    ├── spending/
    ├── about/
    ├── profile/
    ├── account/
    ├── auth/
    └── forum/
```

---

## 🔍 How to Use Bilingual Features

### For Developers:

**1. Using translations in components:**
```tsx
'use client';
import { useTranslations } from 'next-intl';

export function MyComponent() {
  const t = useTranslations('namespace');
  return <h1>{t('key')}</h1>;
}
```

**2. Using bilingual data from GraphQL:**
```tsx
import { useBilingualContent } from '@/hooks/useBilingual';

const bill = { title_en: "Act", title_fr: "Loi", ... };
const { title } = useBilingualContent(bill);
// Auto-selects based on current locale
```

**3. Using locale-aware navigation:**
```tsx
import { Link } from '@/i18n/navigation';

<Link href="/bills">Bills</Link>
// Automatically generates /en/bills or /fr/bills
```

**4. Party name localization:**
```tsx
import { usePartyName } from '@/hooks/useBilingual';

const partyName = usePartyName('Conservative');
// Returns "Conservative" in EN, "Conservateur" in FR
```

### For Users:

- Visit `/en/` for English or `/fr/` for French
- Use the **EN / FR** toggle in the header to switch languages
- Browser language auto-detection on first visit
- Language preference persists across pages

---

## 🎯 Estimated Remaining Work

**Time Estimate:** 10-15 hours

**Breakdown:**
- Pages translation: 5-7 hours (10 pages × 30-40 min each)
- Component translation: 3-4 hours (20+ components)
- Data display logic: 1-2 hours
- SEO & metadata: 1 hour
- Testing & QA: 2-3 hours

**Priority Order:**
1. **High Priority:** MPs page, Bills page, Hansard page (most-used features)
2. **Medium Priority:** Bill detail page, Chamber page, shared components
3. **Low Priority:** Lobbying, Spending, Forum pages, SEO optimization

---

## ✨ Key Features Implemented

✅ **Full URL Localization:** `/en/bills` and `/fr/bills`
✅ **Auto-Detection:** Uses Accept-Language header
✅ **Language Switcher:** Prominent EN/FR toggle in header
✅ **Bilingual Data:** GraphQL queries fetch both _en and _fr fields
✅ **Smart Fallbacks:** Falls back to English if French missing
✅ **Party Translation:** Automatic party name localization
✅ **Type-Safe Routing:** Locale-aware Link and useRouter
✅ **SSR Compatible:** Works with Next.js 15 server components

---

## 🐛 Known Issues / Notes

1. **Hansard Language Parameter:** Currently hardcoded to 'en' - needs to be dynamic
2. **MP/Committee Names:** Not bilingual in data (only in Canada's official records)
3. **Date Formatting:** Need to add French locale support from date-fns
4. **Number Formatting:** Quebec uses spaces (e.g., "1 000 000" not "1,000,000")

---

## 📚 Resources

- [next-intl Documentation](https://next-intl-docs.vercel.app/)
- [Quebec French Translation Guidelines](https://www.oqlf.gouv.qc.ca/)
- [Federal Government Bilingual Guidelines](https://www.noslangues-ourlanguages.gc.ca/)

---

## 🚀 Next Steps

To continue implementation, the recommended order is:

1. **Translate MPs page** - High traffic, straightforward
2. **Translate Bills page** - Core functionality
3. **Translate shared components** (MPCard, BillCard) - Used everywhere
4. **Translate Hansard search** - Critical feature
5. **Update data display logic** - Apply bilingual hooks
6. **Test and QA** - Ensure everything works
7. **SEO optimization** - hreflang tags and sitemaps

Run `pnpm dev` and visit `http://localhost:3000/en` or `http://localhost:3000/fr` to see the bilingual site!
