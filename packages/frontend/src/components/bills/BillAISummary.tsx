'use client';

import { useState, useEffect } from 'react';
import { Card } from '@canadagpt/design-system';
import { Sparkles } from 'lucide-react';
import { Loading } from '../Loading';
import { useAuth } from '@/contexts/AuthContext';
import { useChatStore } from '@/lib/stores/chatStore';

interface BillAISummaryProps {
  billNumber: string;
  session: string;
  billTitle: string;
  billType?: string;
  sponsor?: {
    name: string;
    party?: string;
  };
  votes?: any[];
  debates?: any[];
  lobbying?: {
    organizations_lobbying: number;
  };
  locale: string;
}

export function BillAISummary({
  billNumber,
  session,
  billTitle,
  billType,
  sponsor,
  votes,
  debates,
  lobbying,
  locale
}: BillAISummaryProps) {
  const { user } = useAuth();
  const isOpen = useChatStore((state) => state.isOpen);
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Helper function to convert markdown to HTML
  const formatSummary = (text: string) => {
    return text
      .replace(/^## (.+)$/gm, '<h3 class="text-lg font-bold text-text-primary mt-4 mb-2">$1</h3>') // ## Heading -> <h3>
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>') // **bold** -> <strong>bold</strong>
      .replace(/\n/g, '<br />'); // newlines to <br />
  };

  // Fetch existing summary on mount
  useEffect(() => {
    if (typeof window === 'undefined') return; // Only run on client side

    const fetchExistingSummary = async () => {
      try {
        const response = await fetch(`/api/bills/${session}/${billNumber}/summary`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.summary) {
            setSummary(data.summary);
          }
        } else if (response.status === 404) {
          // No summary exists yet - that's expected
          setSummary(null);
        }
      } catch (err) {
        // Network error or other issue - just log it, don't show to user
        console.log('Could not fetch summary:', err);
        setSummary(null);
      }
    };

    fetchExistingSummary();
  }, [session, billNumber]);

  const generateSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/bills/${session}/${billNumber}/summary`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          billTitle,
          billType,
          sponsor,
          votes,
          debates,
          lobbying
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate summary');
      }

      const data = await response.json();
      setSummary(data.summary);
    } catch (err) {
      console.error('Error generating summary:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate summary');
    } finally {
      setLoading(false);
    }
  };

  // Hide this card when chatbot is open (summary will be shown in chat instead)
  if (isOpen) {
    return null;
  }

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold text-text-primary flex items-center">
          <Sparkles className="h-5 w-5 mr-2 text-accent-red" />
          {locale === 'fr' ? 'Résumé généré par IA' : 'AI-Generated Summary'}
        </h3>
        <span className="text-xs px-2 py-1 rounded bg-accent-red/10 text-accent-red">
          {locale === 'fr' ? 'IA' : 'AI'}
        </span>
      </div>

      {!summary && !loading && !error && (
        <div className="space-y-3">
          <p className="text-sm text-text-secondary">
            {locale === 'fr'
              ? 'Aucun résumé officiel disponible pour ce projet de loi. Générez un résumé à l\'aide de l\'IA.'
              : 'No official summary available for this bill. Generate an AI summary to get an overview.'}
          </p>
          <button
            onClick={generateSummary}
            className="px-4 py-2 bg-accent-red text-white rounded-lg hover:bg-accent-red/90 transition-colors flex items-center gap-2"
          >
            <Sparkles className="h-4 w-4" />
            {locale === 'fr' ? 'Générer le résumé' : 'Generate Summary'}
          </button>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-8 space-y-3">
          <Loading size="md" />
          <p className="text-sm text-text-secondary">
            {locale === 'fr' ? 'Génération du résumé...' : 'Generating summary...'}
          </p>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <p className="text-sm text-red-400">{error}</p>
          <button
            onClick={generateSummary}
            className="mt-3 text-sm text-accent-red hover:underline"
          >
            {locale === 'fr' ? 'Réessayer' : 'Try again'}
          </button>
        </div>
      )}

      {summary && !loading && (
        <div className="space-y-3">
          <div
            className="text-text-secondary leading-relaxed"
            dangerouslySetInnerHTML={{ __html: formatSummary(summary) }}
          />
          {user && (
            <button
              onClick={generateSummary}
              className="text-sm text-text-tertiary hover:text-accent-red transition-colors"
            >
              {locale === 'fr' ? 'Regénérer' : 'Regenerate'}
            </button>
          )}
        </div>
      )}
    </Card>
  );
}
