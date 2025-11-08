/**
 * Hooks for handling bilingual content from GraphQL queries
 * Automatically selects the correct field based on current locale
 */

import { useLocale } from 'next-intl';

/**
 * Select the correct bilingual field based on current locale
 * @param enField - English field value
 * @param frField - French field value
 * @returns The appropriate field value for the current locale
 */
export function useBilingualField(
  enField: string | null | undefined,
  frField: string | null | undefined
): string {
  const locale = useLocale();

  if (locale === 'fr') {
    // Return French if available, fallback to English
    return frField || enField || '';
  }

  // Return English (default)
  return enField || '';
}

/**
 * Utility function for selecting bilingual content from objects with _en and _fr suffixes
 * This is a non-hook version that can be used inside loops and conditionals
 * @param content - Object with bilingual fields (e.g., { title_en, title_fr, summary_en, summary_fr })
 * @param locale - Current locale ('en' or 'fr')
 * @returns Object with selected fields based on locale
 *
 * @example
 * const bill = { title_en: "Climate Act", title_fr: "Loi sur le climat" }
 * const { title } = getBilingualContent(bill, 'fr')
 * // Returns: { title: "Loi sur le climat", ... }
 */
export function getBilingualContent<T extends Record<string, any>>(
  content: T,
  locale: string
): Record<string, any> {
  const isFrench = locale === 'fr';

  const result: Record<string, any> = {};

  // Find all English fields (ending with _en)
  Object.keys(content).forEach((key) => {
    if (key.endsWith('_en')) {
      const baseKey = key.replace('_en', '');
      const frKey = `${baseKey}_fr`;

      if (isFrench && frKey in content) {
        // Use French field if available in French locale
        result[baseKey] = content[frKey] || content[key];
      } else {
        // Use English field
        result[baseKey] = content[key];
      }

      // Also keep original _en and _fr fields for reference
      result[key] = content[key];
      if (frKey in content) {
        result[frKey] = content[frKey];
      }
    } else if (!key.endsWith('_fr')) {
      // Keep non-bilingual fields as-is
      result[key] = content[key];
    }
  });

  // Add any _fr fields that weren't processed
  Object.keys(content).forEach((key) => {
    if (key.endsWith('_fr') && !(key in result)) {
      result[key] = content[key];
    }
  });

  return result;
}

/**
 * Hook for selecting bilingual content from objects with _en and _fr suffixes
 * For use at the top level of components. For use inside loops, use getBilingualContent() instead.
 * @param content - Object with bilingual fields (e.g., { title_en, title_fr, summary_en, summary_fr })
 * @returns Object with selected fields based on locale
 *
 * @example
 * const bill = { title_en: "Climate Act", title_fr: "Loi sur le climat" }
 * const { title } = useBilingualContent(bill)
 * // In French locale: title = "Loi sur le climat"
 * // In English locale: title = "Climate Act"
 */
export function useBilingualContent<T extends Record<string, any>>(
  content: T
): Record<string, any> {
  const locale = useLocale();
  return getBilingualContent(content, locale);
}

/**
 * Get the appropriate field name suffix for the current locale
 * Useful for dynamic field selection in queries
 */
export function useLocaleSuffix(): '_en' | '_fr' {
  const locale = useLocale();
  return locale === 'fr' ? '_fr' : '_en';
}

/**
 * Map party names to localized versions
 */
export function usePartyName(partyCode: string | null | undefined): string {
  const locale = useLocale();

  if (!partyCode) return '';

  const partyMap: Record<string, { en: string; fr: string }> = {
    'Liberal': { en: 'Liberal', fr: 'Libéral' },
    'Conservative': { en: 'Conservative', fr: 'Conservateur' },
    'NDP': { en: 'NDP', fr: 'NPD' },
    'NDP-New Democratic Party': { en: 'NDP', fr: 'NPD' },
    'Bloc Québécois': { en: 'Bloc Québécois', fr: 'Bloc Québécois' },
    'Green Party': { en: 'Green', fr: 'Vert' },
    'Green': { en: 'Green', fr: 'Vert' },
    'Independent': { en: 'Independent', fr: 'Indépendant' },
    "People's Party": { en: "People's Party", fr: 'Parti populaire' },
  };

  const party = partyMap[partyCode];
  if (party) {
    return locale === 'fr' ? party.fr : party.en;
  }

  return partyCode;
}

/**
 * Map chamber names to localized versions
 */
export function useChamberName(chamber: string | null | undefined): string {
  const locale = useLocale();

  if (!chamber) return '';

  const chamberMap: Record<string, { en: string; fr: string }> = {
    'House': { en: 'House of Commons', fr: 'Chambre des communes' },
    'Senate': { en: 'Senate', fr: 'Sénat' },
    'C': { en: 'House of Commons', fr: 'Chambre des communes' },
    'S': { en: 'Senate', fr: 'Sénat' },
  };

  const chamberTranslation = chamberMap[chamber];
  if (chamberTranslation) {
    return locale === 'fr' ? chamberTranslation.fr : chamberTranslation.en;
  }

  return chamber;
}
