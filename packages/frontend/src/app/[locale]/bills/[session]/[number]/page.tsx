/**
 * Individual bill detail page
 * Fully bilingual with Quebec French support
 * @version 2.0.2 - Fixed .dockerignore to prevent env override
 */

'use client';

import { use, useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from '@apollo/client';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { Loading } from '@/components/Loading';
import { Card } from '@canadagpt/design-system';
import { GET_BILL, GET_BILL_LOBBYING, GET_BILL_DEBATES, GET_BILL_COMMITTEE_EVIDENCE } from '@/lib/queries';
import { Link } from '@/i18n/navigation';
import NextLink from 'next/link';
import { getMPPhotoUrl } from '@/lib/utils/mpPhotoUrl';
import { format } from 'date-fns';
import { fr, enUS } from 'date-fns/locale';
import { FileText, Users, ThumbsUp, ThumbsDown, Building, Calendar, CheckCircle, UserCheck, MessageSquare, BookOpen, LayoutGrid, ExternalLink, ChevronRight } from 'lucide-react';
import { useBilingualContent } from '@/hooks/useBilingual';
import { useBillChatSummary } from '@/hooks/useBillChatSummary';
import { usePageThreading } from '@/contexts/UserPreferencesContext';
import { ThreadToggle, ConversationThread } from '@/components/hansard';
import { ShareButton } from '@/components/ShareButton';
import { BookmarkButton } from '@/components/bookmarks/BookmarkButton';
import { EntityVoteButtons } from '@/components/votes/EntityVoteButtons';
import { BillSplitView, BillDiscussionPanel, BillAISummary, BillProgressTimeline, BillActivityStats, BillTopComments, BillActiveDiscussions, BillLobbyingTimeline, CommentButton } from '@/components/bills';
import { parseHighlightParam } from '@/lib/highlights';
import { getPosts } from '@/actions/forum';
import { useEntityVotes } from '@/hooks/useEntityVotes';

type ViewTab = 'overview' | 'votes' | 'lobbying' | 'debates' | 'committees' | 'fulltext';

export default function BillDetailPage({
  params,
}: {
  params: Promise<{ session: string; number: string }>;
}) {
  const resolvedParams = use(params);
  const t = useTranslations('bill');
  const locale = useLocale();
  const dateLocale = locale === 'fr' ? fr : enUS;
  const searchParams = useSearchParams();

  // View tab state (overview vs full text)
  const [activeTab, setActiveTab] = useState<ViewTab>('overview');

  // Section discussion state
  const [selectedSection, setSelectedSection] = useState<string | null>(null);

  // Create modal opener function from BillDiscussionPanel
  const [openCreateModal, setOpenCreateModal] = useState<(() => void) | null>(null);

  // Stable callback for create modal trigger (prevents infinite re-render loop)
  const handleCreateModalTrigger = useCallback((opener: () => void) => {
    setOpenCreateModal(() => opener);
  }, []);

  // Parse highlight from URL (memoized to prevent re-render loops)
  const highlightParam = searchParams.get('hl');
  const highlight = useMemo(
    () => highlightParam ? parseHighlightParam(highlightParam) : null,
    [highlightParam]
  );

  // If URL has highlight, switch to fulltext tab
  useEffect(() => {
    if (highlight) {
      setActiveTab('fulltext');
      if (highlight.section) {
        setSelectedSection(highlight.section);
      }
    }
  }, [highlight]);

  const { data, loading, error } = useQuery(GET_BILL, {
    variables: {
      number: resolvedParams.number,
      session: resolvedParams.session,
    },
  });

  const { data: lobbyingData, loading: lobbyingLoading } = useQuery(GET_BILL_LOBBYING, {
    variables: {
      billNumber: resolvedParams.number,
      session: resolvedParams.session,
    },
  });

  const { data: debatesData, loading: debatesLoading } = useQuery(GET_BILL_DEBATES, {
    variables: {
      billNumber: resolvedParams.number,
      session: resolvedParams.session,
      limit: 50,
    },
  });

  const { data: committeeEvidenceData, loading: committeeEvidenceLoading } = useQuery(GET_BILL_COMMITTEE_EVIDENCE, {
    variables: {
      billNumber: resolvedParams.number,
      session: resolvedParams.session,
    },
  });

  // Fetch vote data for this bill
  const billId = `${resolvedParams.session}-${resolvedParams.number}`;
  const { getVoteData } = useEntityVotes('bill', [billId]);
  const voteData = getVoteData(billId);

  // Threading state
  const { enabled: threadedViewEnabled, setEnabled: setThreadedViewEnabled } = usePageThreading();

  // Lobbying display state
  const [showAllLobbying, setShowAllLobbying] = useState(false);

  // Discussion count state
  const [discussionCount, setDiscussionCount] = useState(0);

  const bill = data?.bills?.[0];
  const bilingualBill = useBilingualContent(bill || {});
  const lobbying = lobbyingData?.billLobbying;
  const debates = debatesData?.billDebates || [];

  // Fetch discussion count
  useEffect(() => {
    const fetchDiscussionCount = async () => {
      if (!bill) return;

      const result = await getPosts({
        post_type: 'bill_comment',
        bill_number: bill.number,
        bill_session: bill.session,
        limit: 1,
        offset: 0,
      });

      if (result.success && result.data) {
        setDiscussionCount(result.data.total || 0);
      }
    };

    fetchDiscussionCount();
  }, [bill]);

  // Auto-load/generate AI summary when chat is open (only when bill data is loaded)
  useBillChatSummary({
    billNumber: bill?.number || '',
    session: bill?.session || '',
    billTitle: bilingualBill.title || '',
    billType: bill?.code,
    sponsor: bill?.sponsor ? {
      name: bill.sponsor.name,
      party: bill.sponsor.party?.name,
    } : undefined,
    votes: bill?.votes || [],
    debates: debates,
    lobbying: lobbying,
  });

  if (loading) {
    return (
      <>
        <Header />
        <Loading />
        <Footer />
      </>
    );
  }

  if (error || !bill) {
    return (
      <>
        <Header />
        <div className="page-container">
          <Card>
            <p className="text-accent-red">{t('notFound')}</p>
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
        {/* Bill Header */}
        <div className="mb-8">
          {/* Header with buttons */}
          <div className="flex items-start gap-4 mb-3">
            {/* Content area - wraps when needed */}
            <div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
              <h1 className="text-4xl font-bold text-text-primary">{t('billNumber')} {bill.number}</h1>
              <span className="text-sm text-text-tertiary">{t('session')} {bill.session}</span>
              {bilingualBill.bill_type && (
                <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                  bill.is_government_bill
                    ? 'bg-blue-500/20 text-blue-400'
                    : bilingualBill.bill_type?.includes('Senate') || bilingualBill.bill_type?.includes('Sénat')
                    ? 'bg-purple-500/20 text-purple-400'
                    : 'bg-green-500/20 text-green-400'
                }`}>
                  {bilingualBill.bill_type}
                </span>
              )}
              {bilingualBill.originating_chamber && (
                <span className="text-sm px-3 py-1 rounded-full bg-gray-500/20 text-gray-400 font-medium">
                  {bilingualBill.originating_chamber}
                </span>
              )}
              <span className={`text-sm px-4 py-2 rounded-full font-semibold ${
                bilingualBill.status === 'Passed' || bilingualBill.status === 'Royal Assent' ||
                bilingualBill.status === 'Adopté' || bilingualBill.status === 'Sanction royale'
                  ? 'bg-green-500/20 text-green-400'
                  : bilingualBill.status?.includes('Reading') || bilingualBill.status?.includes('lecture')
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {bilingualBill.status}
              </span>
              {/* Committee badge - show when bill is referred to a committee */}
              {bill.referredTo && bill.referredTo.length > 0 && (
                <NextLink
                  href={`/${locale}/committees/${bill.referredTo[0].code}`}
                  className="text-sm px-3 py-1 rounded-full bg-purple-500/20 text-purple-400 font-medium flex items-center gap-1 hover:bg-purple-500/30 transition-colors"
                >
                  <Users className="h-3 w-3" />
                  {bill.referredTo[0].name}
                </NextLink>
              )}
            </div>

            {/* Voting, Bookmark and Share Buttons - Right side, non-shrinkable */}
            <div className="flex gap-2 flex-shrink-0">
              <EntityVoteButtons
                entityType="bill"
                entityId={`${bill.session}-${bill.number}`}
                initialUpvotes={voteData.initialUpvotes}
                initialDownvotes={voteData.initialDownvotes}
                initialUserVote={voteData.initialUserVote}
                size="md"
                showVotersList={true}
              />
              <BookmarkButton
                bookmarkData={{
                  itemType: 'bill',
                  itemId: `${bill.session}-${bill.number}`,
                  title: `${t('billNumber')} ${bill.number}`,
                  subtitle: bilingualBill.title,
                  url: `/${locale}/bills/${bill.session}/${bill.number}`,
                  metadata: {
                    session: bill.session,
                    number: bill.number,
                    status: bilingualBill.status,
                    is_government_bill: bill.is_government_bill,
                    bill_type: bilingualBill.bill_type,
                  },
                }}
                size="md"
              />
              <ShareButton
                url={`/${locale}/bills/${bill.session}/${bill.number}`}
                title={`${t('billNumber')} ${bill.number} - ${bilingualBill.title}`}
                description={bilingualBill.summary || bilingualBill.title}
                size="md"
              />
            </div>
          </div>

          <h2 className="text-2xl text-text-secondary mb-4">{bilingualBill.title}</h2>

          {/* External References */}
          <div className="mb-4 flex items-center gap-3">
            <a
              href={`https://www.parl.ca/legisinfo/${locale}/bill/${bill.session}/${bill.number.toLowerCase()}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-accent-red hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              {locale === 'fr' ? 'Voir sur LEGISinfo' : 'View on LEGISinfo'}
            </a>
          </div>

          {bill.statute_year && (
            <div className="mb-4 text-sm text-green-400 flex items-center">
              <CheckCircle className="h-4 w-4 mr-2" />
              {t('enactedAs')} {bill.statute_year}{bill.statute_chapter && `, ${t('chapter')} ${bill.statute_chapter}`}
            </div>
          )}

          <div className="flex flex-wrap gap-6 text-sm text-text-secondary">
            {bill.sponsor && (
              <Link
                href={`/mps/${bill.sponsor.id}` as any}
                className="flex items-center hover:text-accent-red transition-colors"
              >
                <Users className="h-4 w-4 mr-2" />
                {t('sponsoredBy')} {bill.sponsor.name} ({bill.sponsor.party})
              </Link>
            )}
            {bill.introduced_date && (
              <div className="flex items-center">
                <Calendar className="h-4 w-4 mr-2" />
                {t('introduced')} {format(new Date(bill.introduced_date), 'MMMM d, yyyy', { locale: dateLocale })}
              </div>
            )}
            {bill.passed_date && (
              <div className="flex items-center text-green-400">
                <CheckCircle className="h-4 w-4 mr-2" />
                {t('passed')} {format(new Date(bill.passed_date), 'MMMM d, yyyy', { locale: dateLocale })}
              </div>
            )}
          </div>
        </div>

        {/* Legislative Progress Timeline */}
        <BillProgressTimeline
          introducedDate={bill.introduced_date}
          passedHouseFirst={bill.passed_house_first_reading}
          passedHouseSecond={bill.passed_house_second_reading}
          passedHouseThird={bill.passed_house_third_reading}
          passedSenateFirst={bill.passed_senate_first_reading}
          passedSenateSecond={bill.passed_senate_second_reading}
          passedSenateThird={bill.passed_senate_third_reading}
          royalAssentDate={bill.royal_assent_date || bill.passed_date}
          currentStage={bilingualBill.status}
          locale={locale}
        />

        {/* View Tabs */}
        <div className="mb-6 flex gap-2 border-b border-border-subtle overflow-x-auto">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'overview'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <LayoutGrid className="h-4 w-4" />
            {locale === 'fr' ? 'Aperçu' : 'Overview'}
          </button>
          <button
            onClick={() => setActiveTab('votes')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'votes'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <ThumbsUp className="h-4 w-4" />
            {locale === 'fr' ? 'Votes' : 'Votes'}
          </button>
          <button
            onClick={() => setActiveTab('lobbying')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'lobbying'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <Building className="h-4 w-4" />
            {locale === 'fr' ? 'Lobbying' : 'Lobbying'}
          </button>
          <button
            onClick={() => setActiveTab('debates')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'debates'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            {locale === 'fr' ? 'Débats' : 'Debates'}
          </button>
          <button
            onClick={() => setActiveTab('committees')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'committees'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <UserCheck className="h-4 w-4" />
            {locale === 'fr' ? 'Comités' : 'Committees'}
          </button>
          <button
            onClick={() => setActiveTab('fulltext')}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === 'fulltext'
                ? 'border-accent-red text-accent-red'
                : 'border-transparent text-text-secondary hover:text-text-primary'
            }`}
          >
            <BookOpen className="h-4 w-4" />
            {locale === 'fr' ? 'Texte intégral / Discussion' : 'Full Text / Discussion'}
          </button>
        </div>

        {/* Full Text View with Split Panel */}
        {activeTab === 'fulltext' && (
          <div className="mb-6 min-h-screen">
            {/* Narrative Text View (if available) */}
            {(bill.full_text_en || bill.full_text_fr) ? (
              <div className="max-w-4xl mx-auto">
                <Card className="p-8">
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap font-serif leading-relaxed text-text-primary">
                      {locale === 'fr' && bill.full_text_fr ? bill.full_text_fr : bill.full_text_en}
                    </div>
                  </div>
                </Card>
                {/* Link to official PDF as fallback */}
                <div className="mt-4 text-center text-sm text-text-secondary">
                  <a
                    href={`https://www.parl.ca/DocumentViewer/en/${bill.session}/bill/${bill.number}/third-reading`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 hover:text-accent-red transition-colors"
                  >
                    <ExternalLink className="h-3 w-3" />
                    {locale === 'fr' ? 'Voir le PDF officiel' : 'View official PDF'}
                  </a>
                </div>
              </div>
            ) : (
              /* Fallback to structured view if narrative text not available */
              <BillSplitView
                billNumber={bill.number}
                session={bill.session}
                locale={locale}
                initialSection={selectedSection || undefined}
                discussionsEnabled={true}
                onSectionSelect={(sectionAnchorId) => setSelectedSection(sectionAnchorId)}
                discussionHeaderAction={
                  openCreateModal ? (
                    <CommentButton onClick={openCreateModal} locale={locale} />
                  ) : null
                }
                discussionPanel={
                  <BillDiscussionPanel
                    billNumber={bill.number}
                    session={bill.session}
                    billTitle={bilingualBill.title}
                    locale={locale}
                    selectedSection={selectedSection ? {
                      anchorId: `bill:${bill.session}:${bill.number}:${selectedSection}`,
                      sectionRef: selectedSection,
                    } : null}
                    onClearSection={() => setSelectedSection(null)}
                    onSectionMention={(sectionRef) => setSelectedSection(sectionRef)}
                    onCreateModalTrigger={handleCreateModalTrigger}
                  />
                }
              />
            )}
          </div>
        )}

        {/* Overview Tab Content */}
        {activeTab === 'overview' && (
          <>
            {/* Summary - Official or AI-generated */}
            {bilingualBill.summary ? (
              <Card className="mb-6">
                <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
                  <FileText className="h-5 w-5 mr-2 text-accent-red" />
                  {t('summary')}
                </h3>
                <div
                  className="text-text-secondary leading-relaxed prose prose-invert max-w-none"
                  dangerouslySetInnerHTML={{ __html: bilingualBill.summary }}
                />
              </Card>
            ) : (
              <BillAISummary
                billNumber={bill.number}
                session={bill.session}
                billTitle={bilingualBill.title}
                billType={bilingualBill.bill_type}
                sponsor={bill.sponsor ? {
                  name: bill.sponsor.name,
                  party: bill.sponsor.party
                } : undefined}
                votes={bill.votes}
                debates={debates}
                lobbying={lobbying}
                locale={locale}
              />
            )}

            {/* Community Highlights - Top & Controversial Comments */}
            <BillTopComments
              billNumber={bill.number}
              session={bill.session}
              locale={locale}
            />

            {/* Activity Stats Grid */}
            <BillActivityStats
              voteCount={bill.votes?.length || 0}
              debateCount={debates.length}
              lobbyingOrgCount={lobbying?.organizations_lobbying || 0}
              committeeCount={bill.referredTo?.length || 0}
              discussionCount={discussionCount}
              debates={debates}
              onStatClick={(tab) => setActiveTab(tab)}
              locale={locale}
            />


            {/* Recent Votes */}
            {bill.votes && bill.votes.length > 0 && (
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold text-text-primary flex items-center">
                    <ThumbsUp className="h-5 w-5 mr-2 text-accent-red" />
                    {locale === 'fr' ? 'Votes récents' : 'Recent Votes'}
                  </h3>
                  {bill.votes.length > 3 && (
                    <button
                      onClick={() => setActiveTab('votes')}
                      className="text-sm text-accent-red hover:underline"
                    >
                      {locale === 'fr' ? 'Voir tout' : 'View all'} ({bill.votes.length})
                    </button>
                  )}
                </div>
                <div className="space-y-2">
                  {bill.votes.slice(0, 3).map((vote: any) => {
                    const resultLower = vote.result?.toLowerCase() || '';
                    const isPassed = resultLower.includes('agree') || resultLower === 'y';
                    const isFailed = resultLower.includes('negative') || resultLower === 'n';

                    return (
                      <div key={vote.id} className="p-3 rounded-lg bg-bg-elevated text-sm">
                        <div className="flex items-center justify-between mb-2">
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                            isPassed
                              ? 'bg-green-500/20 text-green-400'
                              : isFailed
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {isPassed ? (locale === 'fr' ? 'Adopté' : 'Passed') : isFailed ? (locale === 'fr' ? 'Rejeté' : 'Failed') : vote.result}
                          </span>
                          <span className="text-xs text-text-tertiary">
                            {format(new Date(vote.date), 'MMM d, yyyy', { locale: dateLocale })}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs">
                          <span className="text-green-400">{vote.yeas} {locale === 'fr' ? 'pour' : 'yea'}</span>
                          <span className="text-red-400">{vote.nays} {locale === 'fr' ? 'contre' : 'nay'}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}
          </>
        )}

        {/* Votes Tab Content */}
        {activeTab === 'votes' && (
          <Card>
            <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
              <ThumbsUp className="h-5 w-5 mr-2 text-accent-red" />
              {t('votes')}
            </h3>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loading />
              </div>
            ) : bill?.votes && Array.isArray(bill.votes) && bill.votes.length > 0 ? (
              <div className="space-y-3">
                {bill.votes.map((vote: any) => {
                  const resultLower = vote.result?.toLowerCase() || '';
                  const isPassed = resultLower.includes('agree') || resultLower === 'y';
                  const isFailed = resultLower.includes('negative') || resultLower === 'n';
                  const resultDisplay = isPassed ? t('voteResult.passed') : isFailed ? t('voteResult.failed') : vote.result;

                  return (
                    <div key={vote.id} className="p-3 rounded-lg bg-bg-elevated">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-text-primary">
                          {vote.description || vote.result}
                        </span>
                        <div className="flex flex-col items-center gap-1">
                          <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                            isPassed
                              ? 'bg-green-500/20 text-green-400'
                              : isFailed
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {resultDisplay}
                          </span>
                          <span className="text-sm text-text-secondary whitespace-nowrap">
                            {format(new Date(vote.date), 'MMM d, yyyy', { locale: dateLocale })}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-6 text-sm">
                        <span className="flex items-center text-green-400">
                          <ThumbsUp className="h-4 w-4 mr-1" />
                          {vote.yeas} {t('voteResult.yea')}
                        </span>
                        <span className="flex items-center text-red-400">
                          <ThumbsDown className="h-4 w-4 mr-1" />
                          {vote.nays} {t('voteResult.nay')}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div>
                {bilingualBill.status?.toLowerCase().includes('second reading') ||
                 bilingualBill.status?.toLowerCase().includes('deuxième lecture') ? (
                  <div className="space-y-2">
                    <div className="flex items-center">
                      <Calendar className="h-5 w-5 mr-2 text-blue-400" />
                      <span className="font-semibold text-text-primary">{t('awaitingSecondReading')}</span>
                    </div>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {t('awaitingDescription')}
                      {bill.is_private_member_bill && (
                        <span className="block mt-2">
                          {t('privateMemberNote')}
                        </span>
                      )}
                    </p>
                  </div>
                ) : (
                  <p className="text-text-secondary">{t('noVotes')}</p>
                )}
              </div>
            )}
          </Card>
        )}

        {/* Lobbying Tab Content */}
        {activeTab === 'lobbying' && (
          <Card>
            <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
              <Building className="h-5 w-5 mr-2 text-accent-red" />
              {t('lobbying')}
            </h3>

            {lobbyingLoading ? (
              <Loading size="sm" />
            ) : lobbying?.organizations_lobbying > 0 ? (
              <div className="space-y-6">
                {/* Stats header */}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-lg font-semibold text-text-primary">
                      {lobbying.organizations_lobbying} {lobbying.organizations_lobbying === 1 ? (locale === 'fr' ? 'organisation' : 'organization') : (locale === 'fr' ? 'organisations' : 'organizations')}
                    </p>
                    <p className="text-sm text-text-tertiary">
                      {lobbying.total_lobbying_events} {lobbying.total_lobbying_events === 1 ? (locale === 'fr' ? 'communication' : 'communication') : (locale === 'fr' ? 'communications' : 'communications')}
                    </p>
                  </div>
                </div>

                {/* Top Organizations */}
                <div>
                  <h4 className="text-md font-semibold text-text-primary mb-3">
                    {locale === 'fr' ? 'Principales organisations' : 'Top Lobbying Organizations'}
                  </h4>
                  <div className="space-y-2">
                    {(showAllLobbying ? lobbying.organizations : lobbying.organizations.slice(0, 10))
                      .sort((a: any, b: any) => b.lobbying_count - a.lobbying_count)
                      .map((org: any, index: number) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-3 bg-bg-elevated rounded-lg"
                        >
                          <div>
                            <p className="font-medium text-text-primary">{org.name}</p>
                            {org.industry && (
                              <p className="text-sm text-text-tertiary">{org.industry}</p>
                            )}
                          </div>
                          <span className="text-accent-red font-semibold">
                            {org.lobbying_count} {org.lobbying_count === 1 ? (locale === 'fr' ? 'événement' : 'event') : (locale === 'fr' ? 'événements' : 'events')}
                          </span>
                        </div>
                      ))}
                  </div>

                  {lobbying.organizations.length > 10 && !showAllLobbying && (
                    <button
                      onClick={() => setShowAllLobbying(true)}
                      className="mt-3 text-sm text-accent-red hover:underline"
                    >
                      {t('viewAll')} ({lobbying.organizations.length} {t('total')})
                    </button>
                  )}
                  {showAllLobbying && lobbying.organizations.length > 10 && (
                    <button
                      onClick={() => setShowAllLobbying(false)}
                      className="mt-3 text-sm text-accent-red hover:underline"
                    >
                      {t('showLess')}
                    </button>
                  )}
                </div>

                {/* Communications Timeline */}
                {lobbying.communications && lobbying.communications.length > 0 && (
                  <div>
                    <h4 className="text-md font-semibold text-text-primary mb-3">
                      {locale === 'fr' ? 'Historique des communications' : 'Lobbying Activity Timeline'}
                    </h4>
                    <BillLobbyingTimeline
                      communications={lobbying.communications}
                      locale={locale}
                    />
                  </div>
                )}
              </div>
            ) : (
              <p className="text-text-secondary">{t('noLobbying')}</p>
            )}
          </Card>
        )}

        {/* Committees Tab Content */}
        {activeTab === 'committees' && (
          <>
            {bill.referredTo && bill.referredTo.length > 0 ? (
              <Card>
              <h3 className="text-xl font-bold text-text-primary mb-4 flex items-center">
                <UserCheck className="h-5 w-5 mr-2 text-accent-red" />
                {t('committees')}
              </h3>

              <div className="space-y-6">
                {/* Committee Cards */}
                <div>
                  <h4 className="text-md font-semibold text-text-primary mb-3">
                    {locale === 'fr' ? 'Comités' : 'Committees'}
                  </h4>
                  <div className="space-y-2">
                    {bill.referredTo.map((committee: any, index: number) => (
                      <NextLink
                        key={index}
                        href={`/${locale}/committees/${committee.code}?bill=${bill.session}/${bill.number}`}
                        className="block p-4 bg-bg-elevated rounded-lg border border-border-subtle hover:border-accent-red hover:shadow-md transition-all"
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-semibold text-text-primary">{committee.name}</h4>
                            {committee.code && (
                              <p className="text-sm text-text-tertiary mt-1">Code: {committee.code}</p>
                            )}
                          </div>
                          <ChevronRight className="h-5 w-5 text-text-tertiary" />
                        </div>
                      </NextLink>
                    ))}
                  </div>
                </div>

                {/* Committee Evidence & Testimony */}
                {committeeEvidenceLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loading size="sm" />
                  </div>
                ) : committeeEvidenceData?.bills?.[0]?.referredTo?.some((c: any) =>
                    c.meetings?.some((m: any) =>
                      m.evidence?.testimonies?.some((t: any) =>
                        t.text?.toLowerCase().includes(resolvedParams.number.toLowerCase())
                      )
                    )
                  ) ? (
                  <div>
                    <h4 className="text-md font-semibold text-text-primary mb-3">
                      {locale === 'fr' ? 'Témoignages en comité' : 'Committee Testimony'}
                    </h4>
                    {committeeEvidenceData.bills[0].referredTo.map((committee: any) => {
                      // Filter meetings that have testimonies mentioning the bill
                      const relevantMeetings = committee.meetings?.filter((meeting: any) =>
                        meeting.evidence?.testimonies?.some((testimony: any) =>
                          testimony.text?.toLowerCase().includes(resolvedParams.number.toLowerCase())
                        )
                      ) || [];

                      if (relevantMeetings.length === 0) return null;

                      return (
                        <div key={committee.code} className="mb-6">
                          <h5 className="text-sm font-semibold text-text-secondary mb-3">
                            {committee.name}
                          </h5>
                          <div className="space-y-4">
                            {relevantMeetings.map((meeting: any) => (
                              <div key={meeting.id} className="border border-border-subtle rounded-lg p-4 bg-bg-elevated">
                                {/* Meeting header */}
                                <div className="flex items-start justify-between mb-3">
                                  <div>
                                    <p className="font-semibold text-text-primary">
                                      {locale === 'fr' ? 'Réunion' : 'Meeting'} #{meeting.number}
                                    </p>
                                    <p className="text-sm text-text-tertiary">
                                      {format(new Date(meeting.date), 'PPP', { locale: dateLocale })}
                                    </p>
                                    {meeting.subject && (
                                      <p className="text-sm text-text-secondary mt-1">{meeting.subject}</p>
                                    )}
                                  </div>
                                  {meeting.status && (
                                    <span className="text-xs px-2 py-1 bg-bg-overlay rounded text-text-tertiary">
                                      {meeting.status}
                                    </span>
                                  )}
                                </div>

                                {/* Testimony excerpts */}
                                {meeting.evidence && (() => {
                                  const evidence = meeting.evidence;
                                  const relevantTestimonies = evidence.testimonies?.filter((t: any) =>
                                    t.text?.toLowerCase().includes(resolvedParams.number.toLowerCase())
                                  ) || [];

                                  if (relevantTestimonies.length === 0) return null;

                                  return (
                                    <div className="mt-3 space-y-3">
                                      <p className="text-sm font-semibold text-text-secondary">
                                        {locale === 'fr'
                                          ? `Témoignages mentionnant ${resolvedParams.number}:`
                                          : `Testimony mentioning ${resolvedParams.number}:`}
                                      </p>
                                      {relevantTestimonies.slice(0, 3).map((testimony: any) => (
                                        <div key={testimony.id} className="p-3 bg-bg-overlay rounded-lg">
                                          <div className="flex items-start justify-between mb-2">
                                            <div>
                                              <p className="font-medium text-sm text-text-primary">
                                                {testimony.speaker_name}
                                              </p>
                                              {testimony.organization && (
                                                <p className="text-xs text-text-tertiary">
                                                  {testimony.organization}
                                                </p>
                                              )}
                                              {testimony.role && (
                                                <p className="text-xs text-text-tertiary">
                                                  {testimony.role}
                                                </p>
                                              )}
                                            </div>
                                            {testimony.is_witness && (
                                              <span className="text-xs px-2 py-1 bg-accent-red/10 text-accent-red rounded">
                                                {locale === 'fr' ? 'Témoin' : 'Witness'}
                                              </span>
                                            )}
                                          </div>
                                          <p className="text-sm text-text-secondary line-clamp-4">
                                            {testimony.text}
                                          </p>
                                        </div>
                                      ))}
                                      {relevantTestimonies.length > 3 && (
                                        <p className="text-xs text-text-tertiary">
                                          + {relevantTestimonies.length - 3} {locale === 'fr' ? 'autres témoignages' : 'more testimonies'}
                                        </p>
                                      )}
                                      {evidence.source_xml_url && (
                                        <a
                                          href={evidence.source_xml_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-sm text-accent-red hover:underline inline-flex items-center gap-1"
                                        >
                                          {locale === 'fr' ? 'Voir le témoignage complet' : 'View full evidence'}
                                          <ExternalLink className="h-3 w-3" />
                                        </a>
                                      )}
                                    </div>
                                  );
                                })()}
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : null}
              </div>
              </Card>
            ) : (
              <Card>
                <p className="text-text-secondary">{t('noCommittees')}</p>
              </Card>
            )}
          </>
        )}

        {/* Debates Tab Content */}
        {activeTab === 'debates' && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-text-primary flex items-center">
                <MessageSquare className="h-5 w-5 mr-2 text-accent-red" />
                {t('debates')}
              </h3>
              <ThreadToggle
                enabled={threadedViewEnabled}
                onChange={setThreadedViewEnabled}
                size="sm"
                showLabels={false}
              />
            </div>

            {debatesLoading ? (
              <Loading size="sm" />
            ) : debates && debates.length > 0 ? (
              threadedViewEnabled ? (
                <ConversationThread
                  statements={debates}
                  defaultExpanded={false}
                />
              ) : (
                <div className="space-y-4">
                  {debates.map((speech: any) => (
                    <div
                      key={speech.id}
                      className="p-4 rounded-lg bg-bg-elevated border border-border-subtle hover:border-accent-red/30 transition-colors"
                    >
                      {/* Topic Headers */}
                      {(speech.h1_en || speech.h2_en || speech.h3_en) && (
                        <div className="mb-3 pb-3 border-b border-border-subtle">
                          {speech.h1_en && (
                            <div className="text-xs font-semibold text-accent-red uppercase mb-1">
                              {speech.h1_en}
                            </div>
                          )}
                          {speech.h2_en && (
                            <div className="font-bold text-lg text-text-primary">
                              {speech.h2_en}
                            </div>
                          )}
                          {speech.h3_en && (
                            <div className="text-sm text-text-secondary mt-1">
                              {speech.h3_en}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Speaker */}
                      {speech.madeBy && (() => {
                        const photoUrl = getMPPhotoUrl(speech.madeBy);

                        return (
                          <div className="flex items-center gap-3 mb-3">
                            {photoUrl && (
                              <img
                                src={photoUrl}
                                alt={speech.madeBy.name}
                                className="w-10 h-10 rounded-full object-cover"
                              />
                            )}
                            <div>
                              <Link
                                href={`/mps/${speech.madeBy.id}` as any}
                                className="font-semibold text-text-primary hover:text-accent-red transition-colors"
                              >
                                {speech.madeBy.name}
                              </Link>
                              <div className="text-sm text-text-secondary">
                                {speech.madeBy.party}
                              </div>
                            </div>
                          </div>
                        );
                      })()}

                      {/* Content */}
                      <p className="text-text-primary mb-3 whitespace-pre-line">
                        {speech.content_en}
                      </p>

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-text-secondary">
                        {speech.time && (
                          <span>{speech.time}</span>
                        )}
                        {speech.wordcount && (
                          <span>{speech.wordcount} words</span>
                        )}
                        {speech.statement_type && (
                          <span className="px-2 py-0.5 bg-bg-overlay rounded">
                            {speech.statement_type}
                          </span>
                        )}
                        {speech.mentionsConnection?.edges?.[0]?.properties?.debate_stage && (
                          <span className="px-2 py-0.5 bg-accent-red/20 text-accent-red rounded">
                            {speech.mentionsConnection.edges[0].properties.debate_stage}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <p className="text-text-secondary">{t('noDebates')}</p>
            )}
          </Card>
        )}
      </main>

      <Footer />
    </div>
  );
}
