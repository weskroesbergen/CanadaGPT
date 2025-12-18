'use client';

import { FileText, BookOpen, MessageSquare, ThumbsUp, Award } from 'lucide-react';

interface BillProgressTimelineProps {
  introducedDate?: string;
  passedHouseFirst?: string;
  passedHouseSecond?: string;
  passedHouseThird?: string;
  passedSenateFirst?: string;
  passedSenateSecond?: string;
  passedSenateThird?: string;
  royalAssentDate?: string;
  currentStage?: string;
  locale: string;
}

interface Stage {
  key: string;
  label: string;
  shortLabel: string;
  date?: string;
  completed: boolean;
  isCurrent: boolean;
  chamber: 'house' | 'senate' | 'crown';
  icon: any;
}

export function BillProgressTimeline({
  introducedDate,
  passedHouseFirst,
  passedHouseSecond,
  passedHouseThird,
  passedSenateFirst,
  passedSenateSecond,
  passedSenateThird,
  royalAssentDate,
  currentStage,
  locale
}: BillProgressTimelineProps) {
  // Determine which stage is current based on completed stages
  const getCurrentStage = (): string => {
    if (royalAssentDate) return 'royal_assent';
    if (passedSenateThird) return 'royal_assent';
    if (passedSenateSecond) return 'senate_third';
    if (passedSenateFirst) return 'senate_second';
    if (passedHouseThird) return 'senate_first';
    if (passedHouseSecond) return 'house_third';
    if (passedHouseFirst) return 'house_second';
    if (introducedDate) return 'house_first';
    return 'introduced';
  };

  const current = currentStage || getCurrentStage();

  const stages: Stage[] = [
    {
      key: 'introduced',
      label: locale === 'fr' ? 'Introduction' : 'Introduction',
      shortLabel: locale === 'fr' ? 'Intro' : 'Intro',
      date: introducedDate,
      completed: true, // All bills in the database have been introduced
      isCurrent: current === 'introduced',
      chamber: 'house',
      icon: FileText
    },
    {
      key: 'house_first',
      label: locale === 'fr' ? 'Chambre 1re lecture' : 'House 1st Reading',
      shortLabel: locale === 'fr' ? 'C-1re' : 'H-1st',
      date: passedHouseFirst,
      completed: !!passedHouseFirst,
      isCurrent: current === 'house_first',
      chamber: 'house',
      icon: BookOpen
    },
    {
      key: 'house_second',
      label: locale === 'fr' ? 'Chambre 2e lecture' : 'House 2nd Reading',
      shortLabel: locale === 'fr' ? 'C-2e' : 'H-2nd',
      date: passedHouseSecond,
      completed: !!passedHouseSecond,
      isCurrent: current === 'house_second',
      chamber: 'house',
      icon: MessageSquare
    },
    {
      key: 'house_third',
      label: locale === 'fr' ? 'Chambre 3e lecture' : 'House 3rd Reading',
      shortLabel: locale === 'fr' ? 'C-3e' : 'H-3rd',
      date: passedHouseThird,
      completed: !!passedHouseThird,
      isCurrent: current === 'house_third',
      chamber: 'house',
      icon: ThumbsUp
    },
    {
      key: 'senate_first',
      label: locale === 'fr' ? 'Sénat 1re lecture' : 'Senate 1st Reading',
      shortLabel: locale === 'fr' ? 'S-1re' : 'S-1st',
      date: passedSenateFirst,
      completed: !!passedSenateFirst,
      isCurrent: current === 'senate_first',
      chamber: 'senate',
      icon: BookOpen
    },
    {
      key: 'senate_second',
      label: locale === 'fr' ? 'Sénat 2e lecture' : 'Senate 2nd Reading',
      shortLabel: locale === 'fr' ? 'S-2e' : 'S-2nd',
      date: passedSenateSecond,
      completed: !!passedSenateSecond,
      isCurrent: current === 'senate_second',
      chamber: 'senate',
      icon: MessageSquare
    },
    {
      key: 'senate_third',
      label: locale === 'fr' ? 'Sénat 3e lecture' : 'Senate 3rd Reading',
      shortLabel: locale === 'fr' ? 'S-3e' : 'S-3rd',
      date: passedSenateThird,
      completed: !!passedSenateThird,
      isCurrent: current === 'senate_third',
      chamber: 'senate',
      icon: ThumbsUp
    },
    {
      key: 'royal_assent',
      label: locale === 'fr' ? 'Sanction royale' : 'Royal Assent',
      shortLabel: locale === 'fr' ? 'Sanction' : 'Assent',
      date: royalAssentDate,
      completed: !!royalAssentDate,
      isCurrent: current === 'royal_assent',
      chamber: 'crown',
      icon: Award
    }
  ];

  const getStageStyle = (stage: Stage): string => {
    if (stage.completed) {
      return 'bg-green-500/20 text-green-400 border-green-500';
    }
    if (stage.isCurrent) {
      return 'bg-accent-red/20 text-accent-red border-accent-red';
    }
    return 'bg-gray-500/10 text-gray-500 border-gray-600';
  };

  const getConnectorStyle = (index: number): string => {
    if (index < stages.length - 1) {
      const thisStage = stages[index];
      if (thisStage.completed) {
        return 'bg-green-500';
      }
    }
    return 'bg-border-subtle';
  };

  return (
    <div className="mb-4">
      <div className="flex items-center justify-start flex-wrap gap-1">
        {stages.map((stage, index) => {
          const Icon = stage.icon;
          return (
            <div key={stage.key} className="flex items-center">
              {/* Stage indicator */}
              <div className="flex items-center gap-1">
                <div
                  className={`flex items-center gap-1 px-2 py-1 rounded border ${getStageStyle(stage)} transition-colors`}
                  title={stage.label}
                >
                  <Icon className="h-3 w-3 flex-shrink-0" />
                  <span className="text-xs font-medium whitespace-nowrap hidden sm:inline">
                    {stage.shortLabel}
                  </span>
                </div>
              </div>

              {/* Connector */}
              {index < stages.length - 1 && (
                <div className={`h-px w-2 ${getConnectorStyle(index)}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
