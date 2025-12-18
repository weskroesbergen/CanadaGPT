'use client';

import { Card } from '@canadagpt/design-system';
import { MessageSquare, Users, Building, BookOpen } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface BillMentionsProps {
  debates: Array<{
    id: string;
    madeBy?: {
      id: string;
      name: string;
      party?: string;
    };
    mentionsConnection?: {
      edges: Array<{
        properties: {
          debate_stage?: string;
        };
      }>;
    };
  }>;
  locale: string;
}

export function BillMentions({ debates, locale }: BillMentionsProps) {
  // Derive statistics
  const uniqueMPs = new Set(debates.map(d => d.madeBy?.id).filter(Boolean));
  const totalSpeeches = debates.length;

  // Group by debate stage
  const stageBreakdown = debates.reduce((acc, debate) => {
    const stage = debate.mentionsConnection?.edges?.[0]?.properties?.debate_stage || 'Unknown';
    acc[stage] = (acc[stage] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Top MPs by mention count
  const mpCounts = debates.reduce((acc, debate) => {
    if (debate.madeBy) {
      const key = debate.madeBy.id;
      if (!acc[key]) {
        acc[key] = { mp: debate.madeBy, count: 0 };
      }
      acc[key].count++;
    }
    return acc;
  }, {} as Record<string, { mp: { id: string; name: string; party?: string }; count: number }>);

  const topMPs = Object.values(mpCounts)
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);

  // Handle empty state
  if (debates.length === 0) {
    return (
      <Card className="mb-6">
        <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
          <MessageSquare className="h-5 w-5 mr-2 text-accent-red" />
          {locale === 'fr' ? 'Mentions du projet de loi' : 'Bill Mentions'}
        </h3>
        <p className="text-text-tertiary text-center py-8">
          {locale === 'fr' ? 'Aucune mention pour le moment' : 'No mentions yet'}
        </p>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
        <MessageSquare className="h-5 w-5 mr-2 text-accent-red" />
        {locale === 'fr' ? 'Mentions du projet de loi' : 'Bill Mentions'}
      </h3>

      {/* Stats Grid - 2 columns on desktop */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* MPs stat */}
        <div className="bg-background-secondary rounded-lg p-4">
          <Users className="h-5 w-5 text-blue-400 mb-2" />
          <div className="text-2xl font-bold text-text-primary">{uniqueMPs.size}</div>
          <div className="text-sm text-text-tertiary">
            {locale === 'fr' ? 'Députés' : 'MPs Mentioned'}
          </div>
        </div>

        {/* Speeches stat */}
        <div className="bg-background-secondary rounded-lg p-4">
          <MessageSquare className="h-5 w-5 text-green-400 mb-2" />
          <div className="text-2xl font-bold text-text-primary">{totalSpeeches}</div>
          <div className="text-sm text-text-tertiary">
            {locale === 'fr' ? 'Discours totaux' : 'Total Speeches'}
          </div>
        </div>

        {/* Committee stat */}
        <div className="bg-background-secondary rounded-lg p-4">
          <Building className="h-5 w-5 text-purple-400 mb-2" />
          <div className="text-2xl font-bold text-text-primary">
            {stageBreakdown['Committee'] || 0}
          </div>
          <div className="text-sm text-text-tertiary">
            {locale === 'fr' ? 'Discussions en comité' : 'Committee Discussions'}
          </div>
        </div>

        {/* Debate stages stat */}
        <div className="bg-background-secondary rounded-lg p-4">
          <BookOpen className="h-5 w-5 text-yellow-400 mb-2" />
          <div className="text-2xl font-bold text-text-primary">
            {Object.keys(stageBreakdown).length}
          </div>
          <div className="text-sm text-text-tertiary">
            {locale === 'fr' ? 'Étapes législatives' : 'Debate Stages'}
          </div>
        </div>
      </div>

      {/* Debate Stage Breakdown */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-text-primary mb-3">
          {locale === 'fr' ? 'Par étape législative' : 'By Legislative Stage'}
        </h4>
        <div className="space-y-2">
          {Object.entries(stageBreakdown)
            .sort(([, a], [, b]) => b - a)
            .map(([stage, count]) => (
              <div key={stage} className="flex items-center justify-between text-sm">
                <span className="text-text-secondary">{stage}</span>
                <span className="text-text-primary font-medium">
                  {count} {locale === 'fr' ? 'mentions' : 'mentions'}
                </span>
              </div>
            ))}
        </div>
      </div>

      {/* Top MPs */}
      {topMPs.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-text-primary mb-3">
            {locale === 'fr' ? 'Députés les plus actifs' : 'Most Active MPs'}
          </h4>
          <div className="space-y-2">
            {topMPs.map(({ mp, count }) => (
              <div key={mp.id} className="flex items-center justify-between text-sm">
                <Link
                  href={`/mps/${mp.id}` as any}
                  className="text-accent-red hover:underline"
                >
                  {mp.name} {mp.party && `(${mp.party})`}
                </Link>
                <span className="text-text-tertiary">
                  {count} {locale === 'fr' ? 'discours' : 'speeches'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
