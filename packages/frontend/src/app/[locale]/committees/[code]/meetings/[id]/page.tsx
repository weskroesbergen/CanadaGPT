/**
 * Committee Meeting Detail Page
 * Shows full transcript and details of a specific committee meeting
 */

'use client';

import { use, useEffect } from 'react';
import { useQuery, gql } from '@apollo/client';
import { useLocale } from 'next-intl';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Loading } from '@/components/Loading';
import { Card } from '@canadagpt/design-system';
import Link from 'next/link';
import { Calendar, Users, ArrowLeft, ExternalLink } from 'lucide-react';
import { ShareButton } from '@/components/ShareButton';
import { BookmarkButton } from '@/components/bookmarks/BookmarkButton';
import { useCommitteeActivity } from '@/hooks/useCommitteeActivity';
import { useUserPreferences } from '@/contexts/UserPreferencesContext';

// GraphQL query for meeting details
const GET_MEETING_DETAILS = gql`
  query GetMeetingDetails($meetingId: ID!) {
    meeting(id: $meetingId) {
      id
      ourcommons_meeting_id
      date
      time_description
      subject
      status
      webcast_available
      number
      committee_code
      in_camera
      has_evidence
      meeting_url
      session
      parliament
      heldBy {
        code
        name
        chamber
      }
      evidence {
        id
        title
        testimonies(options: { limit: 500 }) {
          id
          intervention_id
          speaker_name
          organization
          role
          text
          is_witness
          person_db_id
          timestamp_hour
          timestamp_minute
          floor_language
          speaker {
            id
            name
            party
            photo_url
            photo_url_source
          }
        }
      }
    }
  }
`;

export default function MeetingDetailPage({ params }: { params: Promise<{ code: string; id: string }> }) {
  const { code, id } = use(params);
  const locale = useLocale();

  const { data, loading, error } = useQuery(GET_MEETING_DETAILS, {
    variables: { meetingId: id },
  });

  const meeting = data?.meeting;
  const committee = meeting?.heldBy;
  const testimonies = meeting?.evidence?.testimonies || [];

  // Committee activity tracking
  const { markCommitteeViewed, isTracking } = useCommitteeActivity();
  const { preferences } = useUserPreferences();

  // Mark as viewed on page load if preference is 'click_meeting'
  useEffect(() => {
    if (meeting && committee && isTracking(code) && preferences.committeeMarkReadOn === 'click_meeting') {
      // When viewing a specific meeting, mark it as viewed
      markCommitteeViewed(code, meeting.number, undefined);
    }
  }, [code, meeting, committee, isTracking, markCommitteeViewed, preferences.committeeMarkReadOn]);

  if (loading) {
    return (
      <>
        <Header />
        <Loading />
        <Footer />
      </>
    );
  }

  if (error || !meeting || !committee) {
    return (
      <>
        <Header />
        <div className="page-container">
          <Card>
            <p className="text-accent-red">Meeting not found</p>
          </Card>
        </div>
        <Footer />
      </>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 page-container">
        {/* Back Button */}
        <Link
          href={`/${locale}/committees/${code}`}
          className="inline-flex items-center gap-2 text-accent-red hover:text-accent-red-hover mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {committee.name}
        </Link>

        {/* Meeting Header */}
        <div className="mb-8 relative">
          {/* Bookmark and Share Buttons */}
          <div className="absolute top-0 right-0 flex gap-2">
            <BookmarkButton
              bookmarkData={{
                itemType: 'meeting',
                itemId: meeting.id,
                title: `${committee.name} - Meeting #${meeting.number}`,
                subtitle: new Date(meeting.date).toLocaleDateString(),
                url: `/${locale}/committees/${code}/meetings/${id}`,
                metadata: {
                  committee_code: code,
                  meeting_number: meeting.number,
                  date: meeting.date,
                  in_camera: meeting.in_camera,
                },
              }}
              size="md"
            />
            <ShareButton
              url={`/${locale}/committees/${code}/meetings/${id}`}
              title={`${committee.name} - Meeting #${meeting.number}`}
              description={`Committee meeting on ${new Date(meeting.date).toLocaleDateString()}`}
              size="md"
            />
          </div>

          <div className="pr-24">
            <h1 className="text-4xl font-bold text-text-primary mb-2">
              {meeting.number ? `Meeting #${meeting.number}` : 'Committee Meeting'}
            </h1>
            <p className="text-xl text-text-secondary mb-2">{committee.name}</p>

            {/* Meeting Subject */}
            {meeting.subject && (
              <p className="text-lg text-text-primary mb-3 font-medium">
                {meeting.subject}
              </p>
            )}

            {/* Meeting Metadata */}
            <div className="flex flex-wrap items-center gap-4 text-sm text-text-secondary mb-2">
              {meeting.date && (
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  {new Date(meeting.date).toLocaleDateString('en-CA', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </div>
              )}
              {meeting.time_description && (
                <div className="text-sm">
                  {meeting.time_description}
                </div>
              )}
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4" />
                {testimonies.length} testimonies
              </div>
            </div>

            {/* Status Badges */}
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {meeting.status && (
                <span className="px-2 py-1 rounded bg-blue-500/20 text-blue-400 text-xs">
                  {meeting.status}
                </span>
              )}
              {meeting.in_camera && (
                <span className="px-2 py-1 rounded bg-gray-500/20 text-gray-400 text-xs">
                  In Camera
                </span>
              )}
              {meeting.has_evidence && (
                <span className="px-2 py-1 rounded bg-green-500/20 text-green-400 text-xs">
                  Evidence Available
                </span>
              )}
              {meeting.webcast_available && (
                <span className="px-2 py-1 rounded bg-purple-500/20 text-purple-400 text-xs">
                  Webcast Available
                </span>
              )}
            </div>

            {meeting.meeting_url && (
              <a
                href={`https://openparliament.ca${meeting.meeting_url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-2 text-sm text-accent-red hover:text-accent-red-hover font-medium"
              >
                View on OpenParliament
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        {/* Transcript */}
        <Card>
          <h2 className="text-2xl font-bold text-text-primary mb-6">Evidence & Testimony</h2>
          {testimonies.length > 0 ? (
            <div className="space-y-6">
              {testimonies.map((testimony: any) => (
                <div key={testimony.id} className="border-l-4 border-accent-red pl-4">
                  {/* Speaker Info */}
                  <div className="flex items-start gap-3 mb-2">
                    {testimony.speaker && (
                      <img
                        src={testimony.speaker.photo_url || '/default-avatar.png'}
                        alt={testimony.speaker.name}
                        className="w-10 h-10 rounded-full"
                      />
                    )}
                    <div>
                      <div className="font-semibold text-text-primary">
                        {testimony.speaker?.name || testimony.speaker_name}
                      </div>
                      {testimony.organization && (
                        <div className="text-sm text-text-secondary">
                          {testimony.role && `${testimony.role}, `}
                          {testimony.organization}
                        </div>
                      )}
                      {testimony.is_witness && (
                        <span className="inline-block mt-1 px-2 py-0.5 text-xs rounded bg-blue-500/20 text-blue-400">
                          Witness
                        </span>
                      )}
                      {testimony.timestamp_hour !== null && (
                        <div className="text-xs text-text-secondary mt-1">
                          {String(testimony.timestamp_hour).padStart(2, '0')}:
                          {String(testimony.timestamp_minute || 0).padStart(2, '0')}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Testimony Text */}
                  <div className="text-text-primary whitespace-pre-wrap">
                    {testimony.text}
                  </div>

                  {testimony.floor_language && (
                    <div className="mt-2 text-xs text-text-secondary">
                      Language: {testimony.floor_language === 'en' ? 'English' : 'French'}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-400 mb-2">Evidence Not Yet Available</h3>
              <p className="text-text-secondary mb-4">
                Committee evidence and testimony transcripts are imported separately from meeting metadata.
                {meeting.has_evidence && (
                  <span className="block mt-2 text-green-400">
                    Evidence exists for this meeting and will be available after the next import run.
                  </span>
                )}
              </p>
              <div className="text-sm text-text-secondary">
                <p className="mb-2">Evidence includes:</p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Witness testimony and presentations</li>
                  <li>MP questions and interventions</li>
                  <li>Expert opinions and stakeholder input</li>
                </ul>
              </div>
              {meeting.meeting_url && (
                <div className="mt-4 pt-4 border-t border-blue-500/20">
                  <p className="text-sm text-text-secondary mb-2">
                    View evidence on the official House of Commons website:
                  </p>
                  <a
                    href={`https://openparliament.ca${meeting.meeting_url}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-accent-red hover:text-accent-red-hover font-medium"
                  >
                    View on OpenParliament
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              )}
            </div>
          )}
        </Card>
      </main>

      <Footer />
    </div>
  );
}
