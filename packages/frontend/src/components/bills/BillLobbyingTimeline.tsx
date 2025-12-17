'use client';

import { Calendar, Building2, Users, Briefcase } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { enUS, fr } from 'date-fns/locale';

interface LobbyingCommunication {
  id: string;
  date: string;
  subject: string[];
  lobbyist_names: string[];
  government_officials: string[];
  organization_name: string;
  organization_industry?: string;
}

interface BillLobbyingTimelineProps {
  communications: LobbyingCommunication[];
  locale?: string;
}

export function BillLobbyingTimeline({ communications, locale = 'en' }: BillLobbyingTimelineProps) {
  // Sort communications by date descending (most recent first)
  const sortedCommunications = [...communications].sort((a, b) => {
    return new Date(b.date).getTime() - new Date(a.date).getTime();
  });

  if (communications.length === 0) {
    return (
      <div className="text-center py-8 text-text-tertiary">
        <Building2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">
          {locale === 'fr'
            ? 'Aucune communication de lobbying enregistrée'
            : 'No lobbying communications recorded'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {sortedCommunications.map((comm, index) => (
        <div
          key={comm.id || index}
          className="relative border border-border-subtle rounded-lg p-4 bg-bg-elevated hover:border-accent-red/30 transition-colors"
        >
          {/* Timeline connector */}
          {index < sortedCommunications.length - 1 && (
            <div className="absolute left-[23px] top-[60px] bottom-[-16px] w-px bg-border-subtle" />
          )}

          {/* Communication content */}
          <div className="flex gap-4">
            {/* Date badge */}
            <div className="flex-shrink-0">
              <div className="w-12 h-12 rounded-full bg-accent-red/10 border-2 border-accent-red flex items-center justify-center relative z-10">
                <Calendar className="h-5 w-5 text-accent-red" />
              </div>
            </div>

            {/* Details */}
            <div className="flex-1 min-w-0">
              {/* Date and Organization */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    {comm.organization_name}
                  </p>
                  {comm.organization_industry && (
                    <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-bg-overlay text-text-tertiary rounded">
                      {comm.organization_industry}
                    </span>
                  )}
                </div>
                <time className="text-sm text-text-tertiary whitespace-nowrap">
                  {format(parseISO(comm.date), 'PPP', {
                    locale: locale === 'fr' ? fr : enUS
                  })}
                </time>
              </div>

              {/* Subject matters */}
              {comm.subject && comm.subject.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Briefcase className="h-4 w-4 text-text-tertiary" />
                    <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                      {locale === 'fr' ? 'Sujets' : 'Subject Matters'}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {comm.subject.map((topic, i) => (
                      <span
                        key={i}
                        className="text-xs px-2 py-1 bg-accent-red/10 text-text-primary rounded border border-accent-red/20"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Lobbyists */}
              {comm.lobbyist_names && comm.lobbyist_names.length > 0 && (
                <div className="mb-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Users className="h-4 w-4 text-text-tertiary" />
                    <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                      {locale === 'fr' ? 'Lobbyistes' : 'Lobbyists'}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary">
                    {comm.lobbyist_names.join(', ')}
                  </p>
                </div>
              )}

              {/* Government Officials Contacted */}
              {comm.government_officials && comm.government_officials.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Briefcase className="h-4 w-4 text-text-tertiary" />
                    <span className="text-xs font-medium text-text-secondary uppercase tracking-wide">
                      {locale === 'fr' ? 'Fonctionnaires contactés' : 'Officials Contacted'}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary">
                    {comm.government_officials.join(', ')}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
