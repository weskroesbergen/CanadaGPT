'use client';

import { Card } from '@canadagpt/design-system';
import { ThumbsUp, MessageSquare, Building, UserCheck, TrendingUp, MessagesSquare, Users } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface BillActivityStatsProps {
  voteCount: number;
  debateCount: number;
  lobbyingOrgCount: number;
  committeeCount: number;
  discussionCount: number;
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
  onStatClick: (tab: 'votes' | 'debates' | 'lobbying' | 'committees' | 'fulltext') => void;
  locale: string;
}

export function BillActivityStats({
  voteCount,
  debateCount,
  lobbyingOrgCount,
  committeeCount,
  discussionCount,
  debates = [],
  onStatClick,
  locale
}: BillActivityStatsProps) {
  // Calculate MPs Mentioned
  const uniqueMPs = new Set(debates.map(d => d.madeBy?.id).filter(Boolean));
  const mpsMentionedCount = uniqueMPs.size;

  // Calculate Committee Discussions (mentions during committee stage)
  const committeeDiscussionsCount = debates.filter(debate =>
    debate.mentionsConnection?.edges?.[0]?.properties?.debate_stage === 'Committee'
  ).length;

  // Group by debate stage for breakdown
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
  const stats = [
    {
      icon: ThumbsUp,
      count: voteCount,
      label: locale === 'fr' ? 'Votes' : 'Votes',
      tab: 'votes' as const,
      color: 'text-blue-400',
      key: 'votes'
    },
    {
      icon: MessageSquare,
      count: debateCount,
      label: locale === 'fr' ? 'Mentions débats' : 'Debate Mentions',
      tab: 'debates' as const,
      color: 'text-green-400',
      key: 'debate-mentions'
    },
    {
      icon: Building,
      count: lobbyingOrgCount,
      label: locale === 'fr' ? 'Organisations de lobbying' : 'Lobbying Orgs',
      tab: 'lobbying' as const,
      color: 'text-purple-400',
      key: 'lobbying'
    },
    {
      icon: UserCheck,
      count: committeeCount,
      label: locale === 'fr' ? 'Comités' : 'Committees',
      tab: 'committees' as const,
      color: 'text-orange-400',
      key: 'committees'
    },
    {
      icon: MessagesSquare,
      count: discussionCount,
      label: locale === 'fr' ? 'Discussions' : 'Discussions',
      tab: 'fulltext' as const,
      color: 'text-pink-400',
      key: 'discussions'
    },
    {
      icon: Users,
      count: mpsMentionedCount,
      label: locale === 'fr' ? 'Députés' : 'MPs Mentioned',
      tab: 'debates' as const,
      color: 'text-cyan-400',
      key: 'mps-mentioned'
    },
    {
      icon: Building,
      count: committeeDiscussionsCount,
      label: locale === 'fr' ? 'Discussions en comité' : 'Committee Discussions',
      tab: 'committees' as const,
      color: 'text-indigo-400',
      key: 'committee-discussions'
    }
  ];

  return (
    <Card className="mb-6">
      <div className="flex items-center mb-4">
        <TrendingUp className="h-5 w-5 mr-2 text-accent-red" />
        <h3 className="text-xl font-bold text-text-primary">
          {locale === 'fr' ? 'Activité du projet de loi' : 'Bill Activity'}
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <button
              key={stat.key}
              onClick={() => onStatClick(stat.tab)}
              className="p-4 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-red/30 transition-all group text-left"
            >
              <div className="flex items-center justify-between mb-2">
                <Icon className={`h-5 w-5 ${stat.color} group-hover:text-accent-red transition-colors`} />
                <span className="text-xs text-text-tertiary">
                  {locale === 'fr' ? 'Voir détails →' : 'View details →'}
                </span>
              </div>
              <div className="text-3xl font-bold text-text-primary mb-1">
                {stat.count.toLocaleString(locale)}
              </div>
              <div className="text-sm text-text-secondary">
                {stat.label}
              </div>
            </button>
          );
        })}
      </div>

      {/* Legislative Stage Breakdown */}
      {Object.keys(stageBreakdown).length > 0 && (
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
      )}

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
