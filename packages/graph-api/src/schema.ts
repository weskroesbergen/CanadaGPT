/**
 * GraphQL Schema using @neo4j/graphql
 *
 * This schema is automatically mapped to Neo4j nodes and relationships.
 * The @neo4j/graphql library generates resolvers, filters, and pagination.
 */

export const typeDefs = `#graphql
  # ============================================
  # People & Organizations
  # ============================================

  type MP @node {
    id: ID! @unique
    name: String!
    given_name: String
    family_name: String
    gender: String
    party: String
    riding: String
    current: Boolean!
    elected_date: Date
    email: String
    phone: String
    twitter: String
    wikipedia_id: String
    constituency_office: String
    ourcommons_url: String
    cabinet_position: String

    # Photo URLs - Two-tier approach for graceful fallback
    photo_url_source: String  # OpenParliament URL (auto-updated by ingestion)
    photo_url: String  # Custom high-res GCS URL (manually upgraded, takes precedence)

    # House of Commons seating information
    parl_mp_id: Int  # House of Commons PersonId (MP XML, Votes, Committee Evidence)
    hansard_db_id: Int  # Hansard Affiliation DbId (for Hansard statement linking)
    seat_row: Int  # Row number in chamber (1-12 across both sides)
    seat_column: Int  # Column position within row
    bench_section: String  # "government" | "opposition" | "speaker"
    seat_visual_x: Float  # SVG X coordinate for rendering
    seat_visual_y: Float  # SVG Y coordinate for rendering

    # Enhanced MP metadata from OurCommons XML
    honorific: String  # "Hon.", "Right Hon." (for ministers and former PMs)
    term_start_date: DateTime  # Precise swearing-in date from OurCommons XML
    term_end_date: DateTime  # Term end date (null if currently serving)
    province: String  # Province/territory directly from OurCommons XML

    updated_at: DateTime!

    # Relationships
    memberOf: Party @relationship(type: "MEMBER_OF", direction: OUT)
    represents: Riding @relationship(type: "REPRESENTS", direction: OUT)
    sponsored: [Bill!]! @relationship(type: "SPONSORED", direction: OUT)
    ballots: [Ballot!]! @relationship(type: "CAST_BY", direction: IN)
    voted: [Vote!]! @relationship(type: "VOTED", direction: OUT, properties: "VotedProperties")
    sponsoredPetitions: [Petition!]! @relationship(type: "SPONSORED", direction: OUT)
    expenses: [Expense!]! @relationship(type: "INCURRED", direction: OUT)
    metWith: [Lobbyist!]! @relationship(type: "MET_WITH", direction: IN, properties: "MetWithProperties")
    servedOn: [Committee!]! @relationship(type: "SERVES_ON", direction: OUT, properties: "ServedOnProperties")
    roles: [Role!]! @relationship(type: "HOLDS_ROLE", direction: OUT)
    speeches: [Statement!]! @relationship(type: "MADE_BY", direction: IN)
  }

  type Senator @node {
    id: ID! @unique
    name: String!
    name_with_title: String
    current: Boolean!
    updated_at: DateTime!

    # Relationships
    sponsored: [Bill!]! @relationship(type: "SPONSORED", direction: OUT)
  }

  type Party @node {
    code: ID! @unique
    name: String!
    short_name: String
    leader_name: String
    seats: Int
    updated_at: DateTime!

    # Relationships
    members: [MP!]! @relationship(type: "MEMBER_OF", direction: IN)
    receivedDonations: [Donation!]! @relationship(type: "RECEIVED", direction: OUT)
  }

  type Riding @node {
    id: ID! @unique
    name: String!
    province: String
    population: Int
    is_vacant: Boolean
    vacant_since: Date

    # Relationships
    representedBy: [MP!]! @relationship(type: "REPRESENTS", direction: IN)
  }

  type Role @node {
    id: ID! @unique
    person_id: Int!
    title: String!
    role_type: String!
    from_date: DateTime!
    to_date: DateTime
    order_of_precedence: Int
    is_current: Boolean!
    updated_at: DateTime!

    # Relationships
    heldBy: MP @relationship(type: "HOLDS_ROLE", direction: IN)
  }

  type Organization @node {
    id: ID! @unique
    name: String!
    industry: String
    ceo: String

    # Relationships
    lobbyists: [Lobbyist!]! @relationship(type: "WORKS_FOR", direction: IN)
    registrations: [LobbyRegistration!]! @relationship(type: "ON_BEHALF_OF", direction: IN)
    lobbiedOn: [Bill!]! @relationship(type: "LOBBIED_ON", direction: OUT, properties: "LobbiedOnProperties")
    receivedContracts: [Contract!]! @relationship(type: "RECEIVED", direction: OUT)
    receivedGrants: [Grant!]! @relationship(type: "RECEIVED", direction: OUT)
    donated: [Party!]! @relationship(type: "DONATED", direction: OUT, properties: "DonatedProperties")
  }

  type Lobbyist @node {
    id: ID! @unique
    name: String!
    firm: String

    # Relationships
    worksFor: Organization @relationship(type: "WORKS_FOR", direction: OUT)
    registeredFor: [LobbyRegistration!]! @relationship(type: "REGISTERED_FOR", direction: OUT)
    metWith: [MP!]! @relationship(type: "MET_WITH", direction: OUT, properties: "MetWithProperties")
  }

  # ============================================
  # Legislative Entities
  # ============================================

  # Parliament and Session - Foundational structure
  type Parliament @node {
    number: Int! @unique
    ordinal: String!  # "45th"
    election_date: Date!
    opening_date: Date
    dissolution_date: Date
    party_in_power: String
    prime_minister: String
    total_seats: Int!
    is_current: Boolean!
    updated_at: DateTime!

    # Relationships
    sessions: [Session!]! @relationship(type: "HAS_SESSION", direction: OUT)
    bills: [Bill!]! @relationship(type: "FROM_PARLIAMENT", direction: IN)
  }

  type Session @node {
    id: ID! @unique  # "45-1"
    parliament_number: Int!
    session_number: Int!
    start_date: Date!
    end_date: Date
    prorogation_date: Date
    is_current: Boolean!
    updated_at: DateTime!

    # Relationships
    parliament: Parliament! @relationship(type: "HAS_SESSION", direction: IN)
    bills: [Bill!]! @relationship(type: "FROM_SESSION", direction: IN)
    votes: [Vote!]! @relationship(type: "FROM_SESSION", direction: IN)
    documents: [Document!]! @relationship(type: "FROM_SESSION", direction: IN)
  }

  type Bill @node {
    # Basic identifiers
    number: String!
    session: String!
    parliament: Int
    session_number: Int

    # Titles
    title: String
    title_fr: String

    # Summary & description
    summary: String
    summary_fr: String
    full_summary_available: Boolean

    # Status & progress
    status: String
    status_fr: String
    stage: String
    latest_event: String

    # Bill classification
    bill_type: String
    bill_type_fr: String
    is_government_bill: Boolean
    is_private_member_bill: Boolean
    originating_chamber: String
    originating_chamber_fr: String
    is_proforma: Boolean
    bill_form: String

    # Sponsor info
    sponsor_name: String
    sponsor_mp_id: String

    # Dates - Introduction & reading stages
    introduced_date: Date
    passed_house_first_reading: Date
    passed_house_second_reading: Date
    passed_house_third_reading: Date
    passed_senate_first_reading: Date
    passed_senate_second_reading: Date
    passed_senate_third_reading: Date
    royal_assent: Date

    # Legacy date fields (for backward compatibility)
    passed_date: Date
    royal_assent_date: Date

    # Statute info (if passed into law)
    statute_year: Int
    statute_chapter: String

    # Cross-session relationships
    reinstated_from_previous: Boolean
    reinstated_from_bill: String

    # Metadata
    updated_at: DateTime!

    # Full narrative text (continuous reading format from LEGISinfo XML)
    full_text_en: String
    full_text_fr: String
    full_text_updated_at: DateTime

    # Relationships
    sponsor: MP @relationship(type: "SPONSORED", direction: IN)
    senatorSponsor: Senator @relationship(type: "SPONSORED", direction: IN)
    votes: [Vote!]! @relationship(type: "SUBJECT_OF", direction: IN)
    hansardDebates: [Statement!]! @relationship(type: "MENTIONS", direction: IN, properties: "MentionsProperties")
    debates: [Debate!]! @relationship(type: "DISCUSSED", direction: IN)
    referredTo: [Committee!]! @relationship(type: "REFERRED_TO", direction: OUT)
    lobbiedOnBy: [Organization!]! @relationship(type: "LOBBIED_ON", direction: IN, properties: "LobbiedOnProperties")
    citedIn: [Case!]! @relationship(type: "CITED_IN", direction: OUT)
    fromSession: Session @relationship(type: "FROM_SESSION", direction: OUT)
    fromParliament: Parliament @relationship(type: "FROM_PARLIAMENT", direction: OUT)

    # Bill structure (parsed from LEGISinfo XML)
    parts: [BillPart!]! @relationship(type: "HAS_PART", direction: OUT)
    sections: [BillSection!]! @relationship(type: "HAS_SECTION", direction: OUT)
    versions: [BillVersion!]! @relationship(type: "HAS_VERSION", direction: OUT)
    amendmentEvents: [BillAmendmentEvent!]! @relationship(type: "HAS_AMENDMENT_EVENT", direction: OUT)
  }

  # ============================================
  # Bill Structure (Hierarchical Text)
  # ============================================

  type BillVersion @node {
    id: ID! @unique
    bill_id: String!
    version_number: Int!
    stage: String!  # "first-reading", "committee", "third-reading", "royal-assent"
    publication_type_name: String  # "First Reading", "As amended by committee"
    publication_date: DateTime
    has_amendments: Boolean!
    xml_url: String
    pdf_url: String
    updated_at: DateTime!

    # Full narrative text (version-specific)
    full_text_en: String
    full_text_fr: String
    full_text_extracted: Boolean

    # Relationships
    bill: Bill @relationship(type: "HAS_VERSION", direction: IN)
  }

  type BillAmendmentEvent @node {
    id: ID! @unique
    bill_id: String!
    event_type: String!  # "committee_report_with_amendments", "senate_amendment"
    description_en: String!
    description_fr: String
    event_date: DateTime
    chamber: String!  # "House" or "Senate"
    stage: String!  # "Consideration in committee", "Report stage"
    committee_code: String
    committee_name: String
    report_id: Int
    report_number: Int
    number_of_amendments: Int
    updated_at: DateTime!

    # Relationships
    bill: Bill @relationship(type: "HAS_AMENDMENT_EVENT", direction: IN)
  }

  type BillPart @node {
    id: ID! @unique
    bill_id: String!
    number: Int!
    title_en: String
    title_fr: String
    anchor_id: String! @unique  # bill:45-1:c-234:part-1
    sequence: Int!
    updated_at: DateTime!

    # Relationships
    bill: Bill @relationship(type: "HAS_PART", direction: IN)
    sections: [BillSection!]! @relationship(type: "HAS_SECTION", direction: OUT)
  }

  type BillSection @node {
    id: ID! @unique
    bill_id: String!
    number: String!  # Can be "1", "2", or "2.1" for standalone subsections
    marginal_note_en: String  # Section title/description
    marginal_note_fr: String
    text_en: String  # Direct section text (not in subsections)
    text_fr: String
    anchor_id: String! @unique  # bill:45-1:c-234:s2
    sequence: Int!
    updated_at: DateTime!

    # Relationships (can be in a Part or directly in Bill)
    part: BillPart @relationship(type: "HAS_SECTION", direction: IN)
    bill: Bill @relationship(type: "HAS_SECTION", direction: IN)
    subsections: [BillSubsection!]! @relationship(type: "HAS_SUBSECTION", direction: OUT)
  }

  type BillSubsection @node {
    id: ID! @unique
    section_id: String!
    number: String!  # "(1)", "(2)" - stored without parentheses
    text_en: String
    text_fr: String
    anchor_id: String! @unique  # bill:45-1:c-234:s2.1
    sequence: Int!
    updated_at: DateTime!

    # Relationships
    section: BillSection @relationship(type: "HAS_SUBSECTION", direction: IN)
    paragraphs: [BillParagraph!]! @relationship(type: "HAS_PARAGRAPH", direction: OUT)
  }

  type BillParagraph @node {
    id: ID! @unique
    subsection_id: String!
    letter: String!  # "a", "b", "c" - stored without parentheses
    text_en: String
    text_fr: String
    anchor_id: String! @unique  # bill:45-1:c-234:s2.1.a
    sequence: Int!
    updated_at: DateTime!

    # Relationships
    subsection: BillSubsection @relationship(type: "HAS_PARAGRAPH", direction: IN)
    subparagraphs: [BillSubparagraph!]! @relationship(type: "HAS_SUBPARAGRAPH", direction: OUT)
  }

  type BillSubparagraph @node {
    id: ID! @unique
    paragraph_id: String!
    numeral: String!  # "i", "ii", "iii" - Roman numerals
    text_en: String
    text_fr: String
    anchor_id: String! @unique  # bill:45-1:c-234:s2.1.a.i
    sequence: Int!
    updated_at: DateTime!

    # Relationships
    paragraph: BillParagraph @relationship(type: "HAS_SUBPARAGRAPH", direction: IN)
  }

  type BillDefinition @node {
    id: ID! @unique
    bill_id: String!
    term_en: String!
    term_fr: String
    definition_en: String!
    definition_fr: String
    section_id: String  # Which section contains this definition
    updated_at: DateTime!

    # Relationships
    bill: Bill @relationship(type: "HAS_DEFINITION", direction: IN)
    section: BillSection @relationship(type: "DEFINES", direction: IN)
  }

  type Vote @node {
    # Primary identifiers - handle both property naming conventions
    # Some votes have vote_number (from votes_xml_import), others have id (from lightweight_update)
    id: ID! @cypher(statement: "RETURN toString(COALESCE(this.vote_number, this.id)) AS value", columnName: "value")
    vote_number: Int @cypher(statement: "RETURN COALESCE(this.vote_number, toInteger(this.id)) AS value", columnName: "value")
    number: Int! @cypher(statement: "RETURN COALESCE(this.vote_number, this.number, toInteger(this.id)) AS value", columnName: "value")

    # Session info
    parliament_number: Int
    session_number: Int

    # Vote details - handle both property naming conventions
    date: DateTime! @cypher(statement: "RETURN COALESCE(this.date_time, this.date) AS value", columnName: "value")
    result: String!
    yeas: Int! @cypher(statement: "RETURN COALESCE(this.num_yeas, this.yeas) AS value", columnName: "value")
    nays: Int! @cypher(statement: "RETURN COALESCE(this.num_nays, this.nays) AS value", columnName: "value")
    paired: Int @cypher(statement: "RETURN COALESCE(this.num_paired, this.paired) AS value", columnName: "value")
    description: String @cypher(statement: "RETURN COALESCE(this.subject, this.description) AS value", columnName: "value")

    # Additional metadata
    bill_number: String
    vote_type: String
    vote_type_id: Int
    updated_at: DateTime

    # Relationships
    ballots: [Ballot!]! @relationship(type: "CAST_IN", direction: IN)
    subjectOf: Bill @relationship(type: "SUBJECT_OF", direction: OUT)
    fromSession: Session @relationship(type: "FROM_SESSION", direction: OUT)
  }

  type Ballot @node {
    id: ID! @unique
    vote_number: Int!
    person_id: Int!
    vote_value: String!
    is_yea: Boolean!
    is_nay: Boolean!
    is_paired: Boolean!
    person_first_name: String
    person_last_name: String
    person_salutation: String
    constituency_name: String
    province_territory: String
    caucus_short_name: String
    updated_at: DateTime!

    # Relationships
    castIn: Vote! @relationship(type: "CAST_IN", direction: OUT)
    castBy: MP! @relationship(type: "CAST_BY", direction: OUT)
  }

  type Debate @node {
    id: ID! @unique
    date: Date!
    topic: String
    hansard_url: String
    parliament: Int
    session: String

    # Video information (CPAC)
    cpac_video_url: String  # CPAC stream or episode URL
    cpac_episode_id: String  # CPAC episode identifier
    video_start_time: DateTime  # When video recording started
    video_duration: Int  # Duration in seconds

    # Relationships
    speakers: [MP!]! @relationship(type: "SPOKE_AT", direction: IN, properties: "SpokeAtProperties")
    discussed: Bill @relationship(type: "DISCUSSED", direction: OUT)
  }

  # ============================================
  # Hansard Documents & Statements
  # ============================================

  type Document @node {
    id: ID! @unique
    date: Date
    number: Int
    session_id: String
    document_type: String  # "D" = Debates, "E" = Evidence (Committee)
    source_id: String
    downloaded: Boolean
    public: Boolean
    xml_source_url: String
    updated_at: DateTime

    # TF-IDF keyword extraction (JSON string arrays)
    keywords_en: String  # JSON: [{"word": "keyword", "weight": 0.95}, ...]
    keywords_fr: String  # JSON: [{"word": "mot-clé", "weight": 0.95}, ...]

    # Enhanced Hansard XML document metadata
    creation_timestamp: DateTime  # When document was created/published (MetaCreationTime)
    speaker_of_day: String  # Speaker of the House for this sitting
    hansard_document_id: String  # Official Hansard document identifier
    parliament_number: Int  # Parliament number (e.g., 45)
    session_number: Int  # Session number (e.g., 1)
    volume: String  # Hansard volume number

    # Relationships
    statements: [Statement!]! @relationship(type: "PART_OF", direction: IN)
    speakers: [MP!]! @relationship(type: "SPOKE_AT", direction: IN, properties: "SpokeAtProperties")
    presentedTo: Committee @relationship(type: "PRESENTED_TO", direction: OUT)
    fromSession: Session @relationship(type: "FROM_SESSION", direction: OUT)
  }

  type Statement @node {
    id: ID! @unique
    document_id: Int
    time: DateTime
    politician_id: Int  # OpenParliament politician ID
    member_id: Int
    who_en: String  # Speaker display name (e.g., "Pierre Poilievre (Leader of the Opposition, CPC)")
    who_fr: String
    content_en: String  # Full statement text in English
    content_fr: String  # Full statement text in French
    h1_en: String  # Top-level heading (e.g., "Government Orders")
    h1_fr: String
    h2_en: String  # Sub-heading (e.g., "Budget Implementation Act, 2024")
    h2_fr: String
    h3_en: String  # Detail heading
    h3_fr: String
    statement_type: String  # "debate", "question", "answer", "interjection", etc.
    wordcount: Int
    procedural: Boolean
    bill_debated_id: Int  # OpenParliament bill ID
    bill_debate_stage: String  # "1", "2", "3" (reading stages)
    slug: String
    updated_at: DateTime

    # Threading fields
    thread_id: String  # Conversation group identifier
    parent_statement_id: Int  # ID of statement this replies to
    sequence_in_thread: Int  # Order within conversation (0 = root)

    # Enhanced Hansard XML metadata (from direct XML ingestion)
    person_db_id: Int  # House of Commons stable person database ID (Affiliation@DbId)
    role_type_code: Int  # Parliamentary role classification (1=PM, 2=MP, 9=Opposition Leader, 15=Speaker, 60107=Presiding Officer)
    intervention_id: String  # Hansard XML Intervention ID (distinct from statement id)
    paragraph_ids: [String!]  # ParaText IDs for precise paragraph-level citations
    timestamp_hour: Int  # Structured hour from Timestamp element (0-23)
    timestamp_minute: Int  # Structured minute from Timestamp element (0-59)
    floor_language: String  # Language spoken on floor (en/fr)
    intervention_type: String  # Type attribute from Intervention element

    # Government response (for written questions)
    # Finds the matching government response by looking for a Statement with:
    # - Same h3_en (question number)
    # - Same document_id (same Hansard sitting)
    # - Liberal party member (government response) - must end with 'Lib.)'
    # Returns all answer fields in a single query (more efficient than 6 separate queries)
    answer: WrittenQuestionAnswer
      @cypher(
        statement: """
        OPTIONAL MATCH (a:Statement)
        WHERE a.h3_en = this.h3_en
          AND a.document_id = this.document_id
          AND a.who_en ENDS WITH 'Lib.)'
        WITH a
        LIMIT 1
        RETURN {
          id: toString(a.id),
          time: a.time,
          who_en: a.who_en,
          who_fr: a.who_fr,
          content_en: a.content_en,
          content_fr: a.content_fr
        } AS result
        """
        columnName: "result"
      )

    # Relationships
    madeBy: MP @relationship(type: "MADE_BY", direction: OUT)
    partOf: Document @relationship(type: "PART_OF", direction: OUT)
    mentions: Bill @relationship(type: "MENTIONS", direction: OUT, properties: "MentionsProperties")
    replyTo: Statement @relationship(type: "REPLIES_TO", direction: OUT)
    replies: [Statement!]! @relationship(type: "REPLIES_TO", direction: IN)
  }

  # Relationship properties for Statement → Bill (MENTIONS)
  type MentionsProperties @relationshipProperties {
    debate_stage: String  # Which reading stage: "1", "2", or "3"
  }

  # ============================================
  # Written Questions
  # ============================================

  # Written Questions metadata from OurCommons website
  # These are formal questions asked by MPs to ministers that require written responses
  type WrittenQuestion @node {
    id: ID! @unique  # Format: "wq-45-1-762"
    question_number: String!  # "Q-762"
    parliament_number: Int!  # 45
    session_number: Int!  # 1
    session_id: String!  # "45-1"
    date_asked: Date
    asker_name: String  # MP name who asked the question
    asker_constituency: String
    responding_department: String  # Minister/department who responds
    status: String  # "Awaiting response", "Answered", "Withdrawn"
    due_date: Date  # Response deadline
    answer_date: Date  # When answered (if answered)
    sessional_paper: String  # Sessional paper reference (e.g., "8555-451-762")
    topics: [String!]  # Topic tags
    ourcommons_url: String  # Link to OurCommons page
    updated_at: DateTime!

    # Relationships
    askedBy: MP @relationship(type: "ASKED_BY", direction: OUT)
    hansardQuestion: Statement @relationship(type: "HAS_HANSARD_QUESTION", direction: OUT)
    hansardAnswer: Statement @relationship(type: "HAS_HANSARD_ANSWER", direction: OUT)
  }

  # ============================================
  # Debate Browse/Detail Types
  # ============================================

  type DebateSummary {
    document: DocumentSummary!
    statement_count: Int!
    speaker_count: Int!
    top_topics: [String!]!
    is_question_period: Boolean
  }

  type DocumentSummary {
    id: ID!
    date: Date
    session_id: String
    document_type: String
    number: Int
    keywords_en: String
    keywords_fr: String
  }

  type DebateCalendarDay {
    date: String!
    hasHouseDebates: Boolean!
    hasQuestionPeriod: Boolean!
    hasCommittee: Boolean!
    hasScheduledMeeting: Boolean!
    scheduledMeetings: [ScheduledMeetingInfo!]!
  }

  type ScheduledMeetingInfo {
    committee_code: String!
    committee_name: String!
    number: Int!
    in_camera: Boolean!
  }

  type DebateDetail {
    document: DocumentInfo!
    statements: [StatementInfo!]!
    sections: [String!]!
    statement_count: Int!
  }

  type DocumentInfo {
    id: ID!
    date: Date
    session_id: String
    document_type: String
    number: Int
    xml_source_url: String
  }

  type MPInfo {
    id: ID!
    name: String
    party: String
    riding: String
    photo_url: String
    photo_url_source: String
  }

  # Written question with answer (for government MP pages)
  type WrittenQuestionWithAnswer {
    question: StatementInfo!
    answer: WrittenQuestionAnswer!
    partOf: DocumentInfo!
  }

  type StatementInfo {
    id: ID!
    time: DateTime
    who_en: String
    who_fr: String
    content_en: String
    content_fr: String
    h1_en: String
    h1_fr: String
    h2_en: String
    h2_fr: String
    h3_en: String
    h3_fr: String
    statement_type: String
    politician_id: Int
    thread_id: String
    parent_statement_id: Int
    sequence_in_thread: Int
    wordcount: Int
    procedural: Boolean
    madeBy: MPInfo
    partOf: DocumentInfo
  }

  type WrittenQuestionAnswer {
    id: String
    time: DateTime
    who_en: String
    who_fr: String
    content_en: String
    content_fr: String
  }

  type Committee @node {
    code: ID! @unique
    name: String  # Made nullable to handle edge cases in @neo4j/graphql query generation
    mandate: String
    chamber: String  # Nullable - historical committees may not have a specified chamber

    # Relationships
    members: [MP!]! @relationship(type: "SERVES_ON", direction: IN, properties: "ServedOnProperties")
    bills: [Bill!]! @relationship(type: "REFERRED_TO", direction: IN)
    meetings: [Meeting!]! @relationship(type: "HELD_MEETING", direction: OUT)
    evidence: [Document!]! @relationship(type: "PRESENTED_TO", direction: IN)

    # Activity tracking fields (computed)
    latestMeetingDate: Date
      @cypher(
        statement: """
        MATCH (this)-[:HELD_MEETING]->(m:Meeting)
        WHERE m.date IS NOT NULL
        WITH m
        ORDER BY m.date DESC
        LIMIT 1
        RETURN m.date AS date
        """
        columnName: "date"
      )

    latestMeetingNumber: Int
      @cypher(
        statement: """
        MATCH (this)-[:HELD_MEETING]->(m:Meeting)
        WHERE m.date IS NOT NULL
        WITH m
        ORDER BY m.date DESC
        LIMIT 1
        RETURN m.number AS number
        """
        columnName: "number"
      )

    totalMeetingsCount: Int
      @cypher(
        statement: """
        MATCH (this)-[:HELD_MEETING]->(m:Meeting)
        RETURN count(m) AS count
        """
        columnName: "count"
      )
  }

  type Meeting @node {
    id: ID
    ourcommons_meeting_id: String
    committee_code: String!
    date: Date
    time_description: String
    subject: String
    status: String
    webcast_available: Boolean
    webcast: Boolean
    televised: Boolean
    travel: Boolean
    source: String
    imported_at: String
    number: Int
    in_camera: Boolean
    has_evidence: Boolean
    meeting_url: String
    session: String
    session_id: String
    parliament: Int
    evidence_id: String
    start_time: String
    end_time: String
    updated_at: DateTime
    created_at: DateTime

    # Relationships
    heldBy: Committee @relationship(type: "HELD_MEETING", direction: IN)
    evidence: CommitteeEvidence @relationship(type: "HAS_EVIDENCE", direction: OUT)
  }

  type CommitteeEvidence @node {
    id: ID! @unique
    committee_code: String!
    meeting_number: Int!
    date: Date
    title: String
    parliament_number: Int
    session_number: Int
    publication_status: String
    source_xml_url: String
    updated_at: DateTime!

    # Relationships
    meeting: Meeting @relationship(type: "HAS_EVIDENCE", direction: IN)
    testimonies: [CommitteeTestimony!]! @relationship(type: "GIVEN_IN", direction: IN)
    speakers: [MP!]! @relationship(type: "SPOKE_AT", direction: IN, properties: "SpokeAtProperties")
    committee: Committee @relationship(type: "EVIDENCE_FOR", direction: OUT)
  }

  type CommitteeTestimony @node {
    id: ID! @unique
    intervention_id: String
    speaker_name: String
    organization: String
    role: String
    text: String!
    is_witness: Boolean!
    person_db_id: Int
    timestamp_hour: Int
    timestamp_minute: Int
    floor_language: String
    updated_at: DateTime!

    # Relationships
    evidence: CommitteeEvidence! @relationship(type: "GIVEN_IN", direction: OUT)
    speaker: MP @relationship(type: "TESTIFIED_BY", direction: OUT)
  }

  type Petition @node {
    number: ID! @unique
    title: String!
    text: String!
    signatures: Int!
    status: String!
    created_date: Date!
    closed_date: Date
    category: String

    # Relationships
    sponsor: MP @relationship(type: "SPONSORED", direction: IN)
  }

  # ============================================
  # Financial Entities
  # ============================================

  type Expense @node {
    id: ID! @unique
    mp_id: String!
    fiscal_year: Int!
    quarter: Int!
    category: String
    amount: Float!
    description: String

    # Relationships
    incurredBy: MP @relationship(type: "INCURRED", direction: IN)
  }

  type Contract @node {
    id: ID! @unique
    vendor: String!
    amount: Float!
    department: String!
    date: Date!
    delivery_date: Date
    description: String!
    owner_org: String

    # Relationships
    receivedBy: Organization @relationship(type: "RECEIVED", direction: IN)
  }

  type Grant @node {
    id: ID! @unique
    recipient: String!
    amount: Float!
    program_name: String!
    program_purpose: String
    agreement_date: Date!
    agreement_year: Int!
    start_date: Date
    end_date: Date
    owner_org: String!
    recipient_city: String
    recipient_province: String

    # Relationships
    receivedBy: Organization @relationship(type: "RECEIVED", direction: IN)
  }

  type Donation @node {
    id: ID! @unique
    donor_name: String!
    amount: Float!
    date: Date!
    contribution_year: Int!
    political_party: String!
    recipient_type: String!
    recipient_name: String!
    electoral_district: String
    donor_city: String
    donor_province: String

    # Relationships
    receivedBy: Party @relationship(type: "RECEIVED", direction: IN)
  }

  # ============================================
  # Lobbying
  # ============================================

  type LobbyRegistration @node {
    id: ID! @unique
    reg_number: String!
    client_org_name: String!
    registrant_name: String!
    effective_date: Date!
    end_date: Date
    active: Boolean!
    subject_matters: [String!]
    government_institutions: [String!]

    # Relationships
    registeredBy: Lobbyist @relationship(type: "REGISTERED_FOR", direction: IN)
    onBehalfOf: Organization @relationship(type: "ON_BEHALF_OF", direction: OUT)
  }

  type LobbyCommunication @node {
    id: ID! @unique
    client_org_name: String!
    registrant_name: String
    date: Date!
    dpoh_names: [String!]
    dpoh_titles: [String!]
    institutions: [String!]
    subject_matters: [String!]

    # Relationships
    organization: Organization @relationship(type: "COMMUNICATION_BY", direction: OUT)
    lobbyist: Lobbyist @relationship(type: "CONDUCTED_BY", direction: OUT)
    contacted: [MP!]! @relationship(type: "CONTACTED", direction: OUT)
  }

  # ============================================
  # Legal (CanLII)
  # ============================================

  type Case @node {
    id: ID! @unique
    citation: String!
    court: String!
    date: Date!
    summary: String
    canlii_url: String!

    # Relationships
    citedBills: [Bill!]! @relationship(type: "CITED_IN", direction: IN)
    citesLegislation: [Legislation!]! @relationship(type: "CITES", direction: OUT)
    citesCases: [Case!]! @relationship(type: "CITES", direction: OUT)
  }

  type Legislation @node {
    id: ID! @unique
    title: String!
    jurisdiction: String!
    type: String!
    date: Date

    # Relationships
    citedBy: [Case!]! @relationship(type: "CITES", direction: IN)
  }

  # ============================================
  # Relationship Properties
  # ============================================

  type VotedProperties @relationshipProperties {
    position: String!  # "yea", "nay", "paired"
  }

  type MetWithProperties @relationshipProperties {
    first_contact: Date!
    last_contact: Date
  }

  type ServedOnProperties @relationshipProperties {
    role: String
    start_date: Date
  }

  type SpokeAtProperties @relationshipProperties {
    timestamp: DateTime  # For Hansard statements
    statement_id: String  # Statement node ID (for Hansard)
    testimony_id: String  # CommitteeTestimony node ID (for committees)
    intervention_id: String  # XML intervention ID
    person_db_id: Int  # House of Commons person database ID
    timestamp_hour: Int  # Structured hour (0-23)
    timestamp_minute: Int  # Structured minute (0-59)
  }

  type LobbiedOnProperties @relationshipProperties {
    date: Date!
    subject: String
  }

  type DonatedProperties @relationshipProperties {
    via: String  # "individual" or "corporate"
  }

  # ============================================
  # Custom Types for Analytics
  # ============================================

  # MP Summary for Scorecard (plain object, not a Node)
  type MPSummary {
    id: ID!
    name: String!
    given_name: String
    family_name: String
    party: String
    riding: String
    current: Boolean!
    cabinet_position: String
    email: String
    phone: String
    updated_at: DateTime!
  }

  type MPScorecard {
    mp: MP!
    bills_sponsored: Int!
    bills_passed: Int!
    votes_participated: Int!
    petitions_sponsored: Int!
    total_petition_signatures: Int!
    current_year_expenses: Float!
    lobbyist_meetings: Int!
    question_period_interjections: Int!
    voting_participation_rate: Float!
    party_discipline_score: Float!
    legislative_success_rate: Float!
    committee_activity_index: Float!
  }

  type MPAverages {
    party_code: String!
    party_name: String!
    avg_voting_participation_rate: Float
    avg_party_discipline_score: Float
    avg_legislative_success_rate: Float
    avg_committee_activity_index: Float
    avg_bills_sponsored: Float
    avg_bills_passed: Float
    avg_current_year_expenses: Float
    mp_count: Int!
  }

  type MPExpenseSummary {
    mp: MP!
    total_expenses: Float!
  }

  type ParliamentStats {
    parliament: ParliamentInfo!
    bill_count: Int!
    vote_count: Int!
    document_count: Int!
    session_count: Int!
  }

  type ParliamentInfo {
    number: Int!
    ordinal: String!
    election_date: Date!
    opening_date: Date
    dissolution_date: Date
    party_in_power: String
    prime_minister: String
    total_seats: Int!
  }

  type SessionStats {
    session: SessionInfo!
    bill_count: Int!
    vote_count: Int!
    document_count: Int!
  }

  type SessionInfo {
    id: ID!
    parliament_number: Int!
    session_number: Int!
    start_date: Date!
    end_date: Date
    prorogation_date: Date
    is_current: Boolean!
  }

  # TODO: Fix MPInterjectionStats validation error
  # type MPInterjectionStats {
  #   mp: MP!
  #   interjection_count: Int!
  # }

  # TODO: Implement as custom resolver (type currently disabled)
  # type GlobalExpenseStats {
  #   average_per_quarter: Float!
  #   median_per_quarter: Float!
  #   total_quarters: Int!
  # }

  type BillLobbyingActivity {
    bill_number: String!
    bill_session: String!
    bill_title: String
    bill_status: String
    organizations_lobbying: Int!
    total_lobbying_events: Int!
    organizations: [OrganizationLobbyingSummary!]!
    communications: [LobbyingCommunicationSummary!]!
  }

  type OrganizationLobbyingSummary {
    name: String!
    industry: String
    lobbying_count: Int!
  }

  type LobbyingCommunicationSummary {
    id: ID!
    date: String!
    subject: [String!]!
    lobbyist_names: [String!]!
    government_officials: [String!]!
    organization_name: String!
    organization_industry: String
  }

  type ConflictOfInterest {
    mp: MP!
    organization: Organization!
    bill: Bill!
    suspicion_score: Int!
  }

  type PartySpendingTrend {
    quarter: Int!
    period: String!
    parties: [PartySpendingSummary!]!
    total_all_parties: Float!
  }

  type PartySpendingSummary {
    party: String!
    total_expenses: Float!
    mp_count: Int!
    average_per_mp: Float!
  }

  type CommitteeActivityMetrics {
    committee: Committee!
    total_meetings: Int!
    meetings_last_30_days: Int!
    meetings_last_90_days: Int!
    total_evidence_documents: Int!
    active_bills_count: Int!
    member_count: Int!
    avg_statements_per_meeting: Float!
  }

  type NewsArticle {
    title: String!
    url: String!
    source: String!
    published_date: String
    description: String
    image_url: String
    last_updated: String!
  }


  # ============================================
  # Custom Types for MP Counts
  # ============================================

  type MPCount {
    count: Int!
  }

  # ============================================
  # Custom Queries (Accountability Analytics)
  # ============================================

  type Query {
    # Custom query to get a single meeting by ID (workaround for @neo4j/graphql ID filtering issue)
    meeting(id: ID!): Meeting
      @cypher(
        statement: """
        MATCH (m:Meeting)
        WHERE toString(m.id) = $id OR m.ourcommons_meeting_id = $id
        RETURN m
        LIMIT 1
        """
        columnName: "m"
      )

    # MP Performance Scorecard
    # Test query to debug MPScorecard issues
    testMPScorecard(mpId: ID!): MP
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})
        RETURN mp
        """
        columnName: "mp"
      )

    mpScorecard(mpId: ID!): MPScorecard
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})
        WITH mp,
          CASE
            WHEN date().month < 4 THEN date().year
            ELSE date().year + 1
          END AS current_fiscal_year
        // Calculate each metric separately to avoid Cartesian products
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[:SPONSORED]->(bill:Bill)
          RETURN count(DISTINCT bill) AS bills_sponsored,
                 count(DISTINCT CASE WHEN bill.status = 'Passed' THEN bill END) AS bills_passed
        }
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[:VOTED]->(vote:Vote)
          RETURN count(DISTINCT vote) AS votes_participated
        }
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[:SPONSORED]->(petition:Petition)
          RETURN count(DISTINCT petition) AS petitions_sponsored,
                 sum(petition.signatures) AS total_petition_signatures
        }
        CALL {
          WITH mp, current_fiscal_year
          OPTIONAL MATCH (mp)-[:INCURRED]->(expense:Expense {fiscal_year: current_fiscal_year})
          RETURN sum(expense.amount) AS current_year_expenses
        }
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)<-[:MET_WITH]-(lobbyist:Lobbyist)
          RETURN count(DISTINCT lobbyist) AS lobbyist_meetings
        }
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)<-[:MADE_BY]-(statement:Statement {statement_type: 'interjection'})
          WHERE statement.h1_en CONTAINS 'Oral Question'
          RETURN count(DISTINCT statement) AS question_period_interjections
        }

        // Calculate voting participation rate (% of all votes participated in)
        CALL {
          WITH votes_participated
          MATCH (v:Vote)
          WITH votes_participated, count(DISTINCT v) AS total_votes
          RETURN CASE WHEN total_votes > 0
                 THEN (toFloat(votes_participated) / toFloat(total_votes)) * 100.0
                 ELSE 0.0 END AS voting_participation_rate
        }

        // Calculate party discipline score (% of votes aligned with party majority)
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[voted:VOTED]->(vote:Vote)
          WITH mp, voted, vote
          OPTIONAL MATCH (vote)<-[party_votes:VOTED]-(party_mp:MP)
          WHERE party_mp.party = mp.party
          WITH mp, vote, voted,
               count(DISTINCT CASE WHEN party_votes.position = voted.position THEN party_mp END) AS same_position_count,
               count(DISTINCT party_mp) AS total_party_votes
          WITH mp,
               count(DISTINCT vote) AS total_mp_votes,
               count(DISTINCT CASE WHEN toFloat(same_position_count) / toFloat(total_party_votes) > 0.5 THEN vote END) AS aligned_votes
          RETURN CASE WHEN total_mp_votes > 0
                 THEN (toFloat(aligned_votes) / toFloat(total_mp_votes)) * 100.0
                 ELSE 0.0 END AS party_discipline_score
        }

        // Calculate legislative success rate (% of bills that passed)
        CALL {
          WITH bills_sponsored, bills_passed
          RETURN CASE WHEN bills_sponsored > 0
                 THEN (toFloat(bills_passed) / toFloat(bills_sponsored)) * 100.0
                 ELSE 0.0 END AS legislative_success_rate
        }

        // Calculate committee activity index (weighted score)
        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[:SERVES_ON]->(committee:Committee)
          OPTIONAL MATCH (mp)<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document {document_type: 'E'})
          WITH mp, count(DISTINCT committee) AS committee_memberships, count(DISTINCT s) AS committee_statements
          // Weight: 1 point per membership + 0.1 points per statement
          RETURN (toFloat(committee_memberships) + toFloat(committee_statements) * 0.1) AS committee_activity_index
        }

        // Collect all variables for final return
        WITH mp,
             bills_sponsored,
             bills_passed,
             votes_participated,
             petitions_sponsored,
             total_petition_signatures,
             current_year_expenses,
             lobbyist_meetings,
             question_period_interjections,
             voting_participation_rate,
             party_discipline_score,
             legislative_success_rate,
             committee_activity_index

        // Return scorecard with explicitly projected MP fields
        RETURN {
          mp: {
            id: mp.id,
            name: mp.name,
            given_name: mp.given_name,
            family_name: mp.family_name,
            party: mp.party,
            riding: mp.riding,
            current: mp.current,
            cabinet_position: mp.cabinet_position,
            email: mp.email,
            phone: mp.phone,
            updated_at: mp.updated_at
          },
          bills_sponsored: bills_sponsored,
          bills_passed: bills_passed,
          votes_participated: votes_participated,
          petitions_sponsored: petitions_sponsored,
          total_petition_signatures: COALESCE(total_petition_signatures, 0),
          current_year_expenses: COALESCE(current_year_expenses, 0.0),
          lobbyist_meetings: lobbyist_meetings,
          question_period_interjections: question_period_interjections,
          voting_participation_rate: voting_participation_rate,
          party_discipline_score: party_discipline_score,
          legislative_success_rate: legislative_success_rate,
          committee_activity_index: committee_activity_index
        } AS scorecard
        """
        columnName: "scorecard"
      )

    # Case-insensitive MP search
    searchMPs(
      searchTerm: String
      party: String
      current: Boolean
      cabinetOnly: Boolean
      limit: Int = 500
    ): [MP!]!
      @cypher(
        statement: """
        MATCH (mp:MP)
        WHERE ($current IS NULL OR mp.current = $current)
          AND ($party IS NULL OR mp.party = $party)
          AND ($cabinetOnly IS NULL OR $cabinetOnly = false OR mp.cabinet_position IS NOT NULL)
          AND (
            $searchTerm IS NULL OR $searchTerm = '' OR
            toLower(mp.name) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.given_name, '')) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.family_name, '')) CONTAINS toLower($searchTerm)
          )
        RETURN mp
        ORDER BY mp.name ASC
        LIMIT $limit
        """
        columnName: "mp"
      )

    # Paginated MPs with offset-based pagination for optimal performance
    # Supports server-side party filtering (multiple parties)
    paginatedMPs(
      parties: [String!]
      current: Boolean = true
      cabinetOnly: Boolean
      searchTerm: String
      limit: Int = 24
      offset: Int = 0
    ): [MP!]!
      @cypher(
        statement: """
        MATCH (mp:MP)
        WHERE ($current IS NULL OR mp.current = $current)
          AND ($cabinetOnly IS NULL OR $cabinetOnly = false OR mp.cabinet_position IS NOT NULL)
          AND ($parties IS NULL OR size($parties) = 0 OR mp.party IN $parties)
          AND (
            $searchTerm IS NULL OR $searchTerm = '' OR
            toLower(mp.name) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.given_name, '')) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.family_name, '')) CONTAINS toLower($searchTerm)
          )
        RETURN mp
        ORDER BY mp.name ASC
        SKIP $offset
        LIMIT $limit
        """
        columnName: "mp"
      )

    # Count MPs matching filters (for pagination info)
    countMPs(
      parties: [String!]
      current: Boolean = true
      cabinetOnly: Boolean
      searchTerm: String
    ): MPCount!
      @cypher(
        statement: """
        MATCH (mp:MP)
        WHERE ($current IS NULL OR mp.current = $current)
          AND ($cabinetOnly IS NULL OR $cabinetOnly = false OR mp.cabinet_position IS NOT NULL)
          AND ($parties IS NULL OR size($parties) = 0 OR mp.party IN $parties)
          AND (
            $searchTerm IS NULL OR $searchTerm = '' OR
            toLower(mp.name) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.given_name, '')) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(mp.family_name, '')) CONTAINS toLower($searchTerm)
          )
        RETURN {count: count(mp)} AS result
        """
        columnName: "result"
      )

    # Server-side randomized MPs with optional party filtering
    randomMPs(
      parties: [String!]
      limit: Int = 8
    ): [MP!]!
      @cypher(
        statement: """
        MATCH (mp:MP)
        WHERE mp.current = true
          AND ($parties IS NULL OR size($parties) = 0 OR mp.party IN $parties)
        WITH mp, rand() AS r
        ORDER BY r
        LIMIT $limit
        RETURN mp
        """
        columnName: "mp"
      )

    # TODO: Re-enable mpInterjectionLeaderboard after fixing MPInterjectionStats validation
    # MPs ranked by Question Period interjections
    # mpInterjectionLeaderboard(
    #   party: String
    #   limit: Int = 100
    # ): [MPInterjectionStats!]!
    #   @cypher(
    #     statement: """
    #     MATCH (mp:MP)
    #     WHERE mp.current = true
    #       AND ($party IS NULL OR mp.party = $party)
    #     OPTIONAL MATCH (mp)<-[:MADE_BY]-(statement:Statement {statement_type: 'interjection'})
    #     WHERE statement.h1_en CONTAINS 'Oral Question'
    #     WITH mp, count(DISTINCT statement) AS interjection_count
    #     RETURN {
    #       mp: mp,
    #       interjection_count: interjection_count
    #     } AS result
    #     ORDER BY interjection_count DESC, mp.name ASC
    #     LIMIT $limit
    #     """
    #     columnName: "result"
    #   )

    # Case-insensitive Bill search with filters
    searchBills(
      searchTerm: String
      status: String
      session: String
      bill_type: String
      is_government_bill: Boolean
      originating_chamber: String
      limit: Int = 100
    ): [Bill!]!
      @cypher(
        statement: """
        MATCH (b:Bill)
        WHERE ($status IS NULL OR b.status = $status)
          AND ($session IS NULL OR b.session = $session)
          AND ($bill_type IS NULL OR b.bill_type = $bill_type)
          AND ($is_government_bill IS NULL OR b.is_government_bill = $is_government_bill)
          AND ($originating_chamber IS NULL OR b.originating_chamber = $originating_chamber)
          AND (
            $searchTerm IS NULL OR $searchTerm = '' OR
            toLower(COALESCE(b.title, '')) CONTAINS toLower($searchTerm) OR
            toLower(COALESCE(b.number, '')) CONTAINS toLower($searchTerm)
          )
        WITH b
        ORDER BY b.introduced_date DESC
        LIMIT $limit
        RETURN b
        """
        columnName: "b"
      )

    # Case-insensitive Lobbying search
    searchLobbyRegistrations(
      searchTerm: String
      active: Boolean
      limit: Int = 50
    ): [LobbyRegistration!]!
      @cypher(
        statement: """
        MATCH (l:LobbyRegistration)
        WHERE ($active IS NULL OR l.active = $active)
          AND (
            $searchTerm IS NULL OR $searchTerm = '' OR
            toLower(COALESCE(l.client_org_name, '')) CONTAINS toLower($searchTerm)
          )
        RETURN l
        ORDER BY l.effective_date DESC
        LIMIT $limit
        """
        columnName: "l"
      )

    # Top Spenders (MPs by expenses)
    # Custom resolver in server.ts handles this query with proper integer conversion
    topSpenders(fiscalYear: Int, limit: Int = 10): [MPExpenseSummary!]!

    # Party Spending Trends (quarterly spending by party)
    partySpendingTrends(fiscalYear: Int): [PartySpendingTrend!]!
      @cypher(
        statement: """
        MATCH (mp:MP)-[:INCURRED]->(e:Expense)
        WHERE $fiscalYear IS NULL OR e.fiscal_year = $fiscalYear
        WITH
          CASE WHEN $fiscalYear IS NULL THEN e.fiscal_year ELSE $fiscalYear END AS fy,
          e.quarter AS quarter,
          mp.party AS party,
          e.amount AS amount,
          mp
        WITH fy, quarter, party, sum(amount) AS total_expenses, count(DISTINCT mp.id) AS mp_count
        WITH fy, quarter, collect({
          party: party,
          total_expenses: total_expenses,
          mp_count: mp_count,
          average_per_mp: total_expenses / toFloat(mp_count)
        }) AS parties
        WITH fy, quarter, parties, reduce(total = 0.0, p IN parties | total + p.total_expenses) AS total_all_parties
        RETURN {
          quarter: quarter,
          period: CASE WHEN $fiscalYear IS NULL THEN 'FY' + toString(fy) + '-Q' + toString(quarter) ELSE 'Q' + toString(quarter) END,
          parties: parties,
          total_all_parties: total_all_parties
        } AS trend
        ORDER BY CASE WHEN $fiscalYear IS NULL THEN fy ELSE 0 END, quarter
        """
        columnName: "trend"
      )

    # Global Expense Statistics
    # TODO: Implement as custom resolver (currently disabled due to type validation issue)
    # globalExpenseStats: GlobalExpenseStats!
    #   @cypher(
    #     statement: """
    #     MATCH (mp:MP)-[:INCURRED]->(e:Expense)
    #     WITH e.fiscal_year AS fiscal_year, e.quarter AS quarter, mp.id AS mp_id, sum(e.amount) AS quarter_total
    #     WITH collect(quarter_total) AS all_quarter_totals
    #     RETURN {
    #       average_per_quarter: reduce(sum = 0.0, x IN all_quarter_totals | sum + x) / size(all_quarter_totals),
    #       median_per_quarter: all_quarter_totals[size(all_quarter_totals) / 2],
    #       total_quarters: size(all_quarter_totals)
    #     } AS stats
    #     """
    #     columnName: "stats"
    #   )

    # Bill Lobbying Activity
    billLobbying(billNumber: String!, session: String!): BillLobbyingActivity
      @cypher(
        statement: """
        MATCH (bill:Bill {number: $billNumber, session: $session})

        // Fetch organization summaries
        OPTIONAL MATCH (org:Organization)-[l:LOBBIED_ON]->(bill)
        WHERE org IS NOT NULL
        WITH bill, org, count(l) as lobbying_count
        WITH bill,
             count(DISTINCT org) as organizations_lobbying,
             sum(lobbying_count) as total_lobbying_events,
             collect(DISTINCT {name: org.name, industry: org.industry, lobbying_count: lobbying_count}) as organizations

        // Fetch all lobbying communications for this bill
        OPTIONAL MATCH (comm:LobbyCommunication)-[:COMMUNICATION_BY]->(org2:Organization)-[:LOBBIED_ON]->(bill)
        WITH bill, organizations_lobbying, total_lobbying_events, organizations,
             collect(DISTINCT {
               id: comm.id,
               date: toString(comm.date),
               subject: comm.subject_matters,
               lobbyist_names: COALESCE(comm.dpoh_names, []),
               government_officials: COALESCE(comm.dpoh_titles, []),
               organization_name: comm.client_org_name,
               organization_industry: org2.industry
             }) as communications

        WHERE size(organizations) > 0 OR organizations_lobbying = 0
        RETURN {
          bill_number: bill.number,
          bill_session: bill.session,
          bill_title: bill.title,
          bill_status: bill.status,
          organizations_lobbying: COALESCE(organizations_lobbying, 0),
          total_lobbying_events: COALESCE(total_lobbying_events, 0),
          organizations: CASE WHEN organizations_lobbying > 0 THEN organizations ELSE [] END,
          communications: CASE WHEN size(communications) > 0 AND communications[0].id IS NOT NULL THEN communications ELSE [] END
        } AS activity
        """
        columnName: "activity"
      )

    # Detect Conflicts of Interest
    conflictsOfInterest(limit: Int = 20): [ConflictOfInterest!]!
      @cypher(
        statement: """
        MATCH (org:Organization)-[:LOBBIED_ON]->(bill:Bill)
        MATCH (org)-[:DONATED]->(party:Party)
        MATCH (party)<-[:MEMBER_OF]-(mp:MP)-[v:VOTED]->(vote:Vote)-[:SUBJECT_OF]->(bill)
        WHERE v.position = 'yea'
          AND exists((org)-[:RECEIVED]->(:Contract))
        WITH mp, org, bill, count(*) AS suspicion_score
        RETURN {
          mp: mp,
          organization: org,
          bill: bill,
          suspicion_score: suspicion_score
        } AS conflict
        ORDER BY suspicion_score DESC
        LIMIT $limit
        """
        columnName: "conflict"
      )

    # MP News Articles
    # Note: This is implemented as a custom resolver in server.ts
    mpNews(mpName: String!, limit: Int = 10): [NewsArticle!]!

    # ============================================
    # Optimized Lobbying Search Queries
    # ============================================

    # Full-text search for lobbyists (optimized)
    searchLobbyists(
      searchTerm: String!
      limit: Int = 20
    ): [Lobbyist!]!
      @cypher(
        statement: """
        CALL db.index.fulltext.queryNodes('lobbyist_search', $searchTerm)
        YIELD node, score
        WITH node AS lobbyist, score
        WHERE score > 0.5
        RETURN lobbyist
        ORDER BY score DESC
        LIMIT $limit
        """
        columnName: "lobbyist"
      )

    # Full-text search for organizations (optimized)
    searchOrganizations(
      searchTerm: String!
      limit: Int = 20
    ): [Organization!]!
      @cypher(
        statement: """
        CALL db.index.fulltext.queryNodes('organization_search', $searchTerm)
        YIELD node, score
        WITH node AS org, score
        WHERE score > 0.5
        RETURN org
        ORDER BY score DESC
        LIMIT $limit
        """
        columnName: "org"
      )

    # Full-text search for bills (optimized)
    searchBillsFullText(
      searchTerm: String!
      status: String
      session: String
      limit: Int = 50
    ): [Bill!]!
      @cypher(
        statement: """
        CALL db.index.fulltext.queryNodes('bill_search', $searchTerm)
        YIELD node, score
        WITH node AS bill, score
        WHERE score > 0.5
          AND ($status IS NULL OR bill.status = $status)
          AND ($session IS NULL OR bill.session = $session)
        RETURN bill
        ORDER BY score DESC, bill.introduced_date DESC
        LIMIT $limit
        """
        columnName: "bill"
      )

    # ============================================
    # Hansard Queries
    # ============================================

    # Get recent speeches by an MP
    mpSpeeches(
      mpId: ID!
      limit: Int = 20
      documentType: String  # Filter by "D" (Debates) or "E" (Evidence/Committee)
    ): [Statement!]!
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})<-[:MADE_BY]-(s:Statement)
        WHERE $documentType IS NULL OR
              exists((s)-[:PART_OF]->(:Document {document_type: $documentType}))
        WITH s
        ORDER BY s.time DESC
        LIMIT $limit
        RETURN s
        """
        columnName: "s"
      )

    # Get debate statements for a specific bill
    billDebates(
      billNumber: String!
      session: String!
      limit: Int = 50
      debateStage: String  # Filter by reading stage: "1", "2", or "3"
    ): [Statement!]!
      @cypher(
        statement: """
        MATCH (b:Bill {number: $billNumber, session: $session})<-[r:MENTIONS]-(s:Statement)
        WHERE $debateStage IS NULL OR r.debate_stage = $debateStage
        WITH s, r
        ORDER BY s.id ASC
        LIMIT $limit
        RETURN s
        """
        columnName: "s"
      )

    # Full-text search across Hansard content
    searchHansard(
      query: String!
      limit: Int = 50
      language: String = "en"  # "en" or "fr"
    ): [Statement!]!
      @cypher(
        statement: """
        CALL {
          WITH $query AS query, $language AS language
          CALL db.index.fulltext.queryNodes(
            CASE WHEN language = 'fr' THEN 'statement_content_fr' ELSE 'statement_content_en' END,
            query
          ) YIELD node, score
          RETURN node, score
        }
        WITH node AS s, score
        ORDER BY score DESC, s.time DESC
        LIMIT $limit
        RETURN s
        """
        columnName: "s"
      )

    # Get written questions (Questions on the Order Paper)
    writtenQuestions(
      limit: Int = 50
      answered: Boolean  # Filter by whether question has an answer
      mpId: ID  # Filter by MP who asked
      session: String  # Filter by parliamentary session (e.g., "45-1")
    ): [Statement!]!
      @cypher(
        statement: """
        MATCH (s:Statement)-[:PART_OF]->(d:Document)
        WHERE s.h2_en CONTAINS 'Questions on the Order Paper'
          AND s.h3_en IS NOT NULL
          AND s.h3_en <> ''
          AND s.h3_en CONTAINS 'Question No'
          AND NOT s.who_en CONTAINS 'Lib.'
          AND s.who_en IS NOT NULL
          AND s.who_en <> ''
          AND ($mpId IS NULL OR EXISTS((s)<-[:MADE_BY]-(:MP {id: $mpId})))
          AND ($session IS NULL OR d.session_id = $session)

        # Filter by answered status if requested
        OPTIONAL MATCH (a:Statement)
        WHERE a.h3_en = s.h3_en
          AND a.document_id = s.document_id
          AND a.who_en CONTAINS 'Lib.'

        WITH s, a
        WHERE $answered IS NULL OR ($answered = true AND a IS NOT NULL) OR ($answered = false AND a IS NULL)

        WITH s
        ORDER BY s.time DESC
        LIMIT $limit

        RETURN s
        """
        columnName: "s"
      )

    # Get written questions asked by a specific MP
    # Optional session parameter filters to specific parliamentary session (e.g., "45-1")
    mpWrittenQuestions(
      mpId: ID!
      limit: Int = 50
      session: String
    ): [Statement!]!
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document)
        WHERE s.h2_en CONTAINS 'Questions on the Order Paper'
          AND s.h3_en IS NOT NULL
          AND s.h3_en <> ''
          AND s.h3_en CONTAINS 'Question No'
          AND ($session IS NULL OR d.session_id = $session)

        WITH s
        ORDER BY s.time DESC
        LIMIT $limit

        RETURN s
        """
        columnName: "s"
      )

    # Get list of parliamentary sessions that have written questions
    # Returns session IDs like "45-1", "44-1", etc. in descending order
    writtenQuestionSessions: [String!]!
      @cypher(
        statement: """
        MATCH (s:Statement)-[:PART_OF]->(d:Document)
        WHERE s.h2_en CONTAINS 'Questions on the Order Paper'
          AND s.h3_en CONTAINS 'Question No'
          AND d.session_id IS NOT NULL
        WITH DISTINCT d.session_id AS session_id
        ORDER BY session_id DESC
        RETURN session_id
        """
        columnName: "session_id"
      )

    # Get written questions answered by a government MP
    # Returns opposition questions with this MP's answers
    # For use on Liberal/government MP pages
    mpAnsweredQuestions(
      mpId: ID!
      limit: Int = 50
      session: String
    ): [WrittenQuestionWithAnswer!]!
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})

        // Find answers provided by this government MP
        MATCH (mp)<-[:MADE_BY]-(answer:Statement)-[:PART_OF]->(d:Document)
        WHERE answer.h2_en CONTAINS 'Questions on the Order Paper'
          AND answer.h3_en IS NOT NULL
          AND answer.h3_en <> ''
          AND answer.h3_en CONTAINS 'Question No'
          AND answer.who_en CONTAINS 'Lib.'
          AND ($session IS NULL OR d.session_id = $session)

        // Find the original opposition question for each answer
        MATCH (question:Statement)-[:PART_OF]->(d)
        WHERE question.h3_en = answer.h3_en
          AND NOT question.who_en CONTAINS 'Lib.'

        // Get the MP who made the question
        OPTIONAL MATCH (question)-[:MADE_BY]->(question_mp:MP)

        WITH question, answer, d, question_mp
        ORDER BY answer.time DESC
        LIMIT $limit

        RETURN {
          question: {
            id: toString(question.id),
            time: question.time,
            who_en: question.who_en,
            who_fr: question.who_fr,
            content_en: question.content_en,
            content_fr: question.content_fr,
            h1_en: question.h1_en,
            h1_fr: question.h1_fr,
            h2_en: question.h2_en,
            h2_fr: question.h2_fr,
            h3_en: question.h3_en,
            h3_fr: question.h3_fr,
            statement_type: question.statement_type,
            politician_id: question.politician_id,
            thread_id: question.thread_id,
            parent_statement_id: question.parent_statement_id,
            sequence_in_thread: question.sequence_in_thread,
            wordcount: question.wordcount,
            procedural: question.procedural,
            madeBy: CASE WHEN question_mp IS NOT NULL THEN {
              id: question_mp.id,
              name: question_mp.name,
              party: question_mp.party,
              riding: question_mp.riding,
              photo_url: question_mp.photo_url,
              photo_url_source: question_mp.photo_url_source
            } ELSE null END,
            partOf: {
              id: toString(d.id),
              date: d.date,
              session_id: d.session_id,
              document_type: d.document_type,
              number: d.number,
              xml_source_url: d.xml_source_url
            }
          },
          answer: {
            id: toString(answer.id),
            time: answer.time,
            who_en: answer.who_en,
            who_fr: answer.who_fr,
            content_en: answer.content_en,
            content_fr: answer.content_fr
          },
          partOf: {
            id: toString(d.id),
            date: d.date,
            session_id: d.session_id,
            document_type: d.document_type,
            number: d.number,
            xml_source_url: d.xml_source_url
          }
        } AS result
        """
        columnName: "result"
      )

    # Search written questions by keyword
    searchWrittenQuestions(
      searchTerm: String!
      limit: Int = 50
      language: String = "en"
    ): [Statement!]!
      @cypher(
        statement: """
        CALL {
          WITH $searchTerm AS query, $language AS language
          CALL db.index.fulltext.queryNodes(
            CASE WHEN language = 'fr' THEN 'statement_content_fr' ELSE 'statement_content_en' END,
            query
          ) YIELD node, score
          RETURN node, score
        }
        WITH node AS s, score
        WHERE s.h2_en CONTAINS 'Questions on the Order Paper'
          AND s.h3_en IS NOT NULL
          AND s.h3_en <> ''
          AND s.h3_en CONTAINS 'Question No'
          AND NOT s.who_en CONTAINS 'Lib.'
          AND s.who_en IS NOT NULL
          AND s.who_en <> ''

        WITH s, score
        ORDER BY score DESC, s.time DESC
        LIMIT $limit

        RETURN s
        """
        columnName: "s"
      )

    # Get a specific Hansard document with all its statements
    hansardDocument(id: ID!): Document
      @cypher(
        statement: """
        MATCH (d:Document {id: $id})
        RETURN d
        """
        columnName: "d"
      )

    # List recent debates (browse view)
    recentDebates(
      limit: Int = 20
      documentType: String  # "D" (Debates) or "E" (Evidence)
      questionPeriodOnly: Boolean = false
      startDate: String  # Filter by date range (YYYY-MM-DD)
      endDate: String    # Filter by date range (YYYY-MM-DD)
    ): [DebateSummary!]!
      @cypher(
        statement: """
        MATCH (d:Document)
        WHERE d.public = true
          AND ($documentType IS NULL OR d.document_type = $documentType)
          AND ($startDate IS NULL OR d.date >= $startDate)
          AND ($endDate IS NULL OR d.date <= $endDate)
        OPTIONAL MATCH (d)<-[:PART_OF]-(s:Statement)
        WITH d, s
        WHERE NOT $questionPeriodOnly OR s.h1_en CONTAINS 'Oral Question' OR s.h1_en CONTAINS 'Question Period'
        WITH d,
             count(DISTINCT s) AS statement_count,
             count(DISTINCT s.politician_id) AS speaker_count,
             collect(DISTINCT s.h2_en)[0..3] AS top_topics
        WHERE statement_count > 0
        RETURN {
          document: {
            id: d.id,
            date: d.date,
            session_id: d.session_id,
            document_type: d.document_type,
            number: d.number,
            keywords_en: d.keywords_en,
            keywords_fr: d.keywords_fr
          },
          statement_count: statement_count,
          speaker_count: speaker_count,
          top_topics: [topic IN top_topics WHERE topic IS NOT NULL]
        } AS summary
        ORDER BY d.date DESC
        LIMIT $limit
        """
        columnName: "summary"
      )

    # Get full debate with all statements (for debate detail page)
    debateWithStatements(
      documentId: ID!
      includeThreading: Boolean = true
    ): DebateDetail
      @cypher(
        statement: """
        MATCH (d:Document {id: toInteger($documentId)})
        MATCH (d)<-[:PART_OF]-(s:Statement)
        OPTIONAL MATCH (s)-[:MADE_BY]->(mp:MP)
        WITH d, s, mp
        ORDER BY s.id ASC
        WITH d,
             collect({
               id: s.id,
               time: s.time,
               who_en: s.who_en,
               who_fr: s.who_fr,
               content_en: s.content_en,
               content_fr: s.content_fr,
               h1_en: s.h1_en,
               h2_en: s.h2_en,
               h3_en: s.h3_en,
               statement_type: s.statement_type,
               politician_id: s.politician_id,
               thread_id: s.thread_id,
               parent_statement_id: s.parent_statement_id,
               sequence_in_thread: s.sequence_in_thread,
               wordcount: s.wordcount,
               procedural: s.procedural,
               madeBy: CASE WHEN mp IS NOT NULL THEN {
                 id: mp.id,
                 name: mp.name,
                 party: mp.party,
                 photo_url: mp.photo_url,
                photo_url_source: mp.photo_url_source
               } ELSE null END,
               partOf: {
                 id: d.id,
                 date: d.date,
                 document_type: d.document_type
               }
             }) AS statements,
             count(DISTINCT s.h1_en) AS section_count,
             collect(DISTINCT s.h1_en) AS sections
        RETURN {
          document: {
            id: d.id,
            date: d.date,
            session_id: d.session_id,
            document_type: d.document_type,
            number: d.number,
            xml_source_url: d.xml_source_url
          },
          statements: statements,
          sections: [section IN sections WHERE section IS NOT NULL],
          statement_count: size(statements)
        } AS detail
        """
        columnName: "detail"
      )

    # Get calendar data for debates (for calendar view)
    # Custom resolver in server.ts that merges Neo4j data with OpenParliament scheduled meetings
    debatesCalendarData(
      startDate: String!
      endDate: String!
    ): [DebateCalendarDay!]!

    # Question Period debates only
    questionPeriodDebates(
      limit: Int = 10
      sinceDate: Date
    ): [DebateSummary!]!
      @cypher(
        statement: """
        MATCH (d:Document)<-[:PART_OF]-(s:Statement)
        WHERE d.public = true
          AND d.document_type = 'D'
          AND (s.h1_en CONTAINS 'Oral Question' OR s.h1_en CONTAINS 'Question Period')
          AND ($sinceDate IS NULL OR d.date >= date($sinceDate))
        WITH d,
             count(DISTINCT s) AS statement_count,
             count(DISTINCT s.politician_id) AS speaker_count,
             collect(DISTINCT s.h2_en)[0..5] AS top_topics
        RETURN {
          document: {
            id: d.id,
            date: d.date,
            session_id: d.session_id,
            document_type: d.document_type,
            number: d.number,
            keywords_en: d.keywords_en,
            keywords_fr: d.keywords_fr
          },
          statement_count: statement_count,
          speaker_count: speaker_count,
          top_topics: [topic IN top_topics WHERE topic IS NOT NULL],
          is_question_period: true
        } AS summary
        ORDER BY d.date DESC
        LIMIT $limit
        """
        columnName: "summary"
      )

    # ============================================
    # Committee Queries
    # ============================================

    # Get recent testimony/evidence for a committee
    committeeTestimony(committeeCode: String!, limit: Int = 20): [Statement!]!
      @cypher(
        statement: """
        MATCH (c:Committee {code: $committeeCode})<-[:SERVES_ON]-(mp:MP)<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document {document_type: 'E'})
        WITH s, d
        ORDER BY s.time DESC
        LIMIT $limit
        RETURN s
        """
        columnName: "s"
      )

    # Committee activity metrics
    committeeActivityMetrics(committeeCode: String!): CommitteeActivityMetrics
      @cypher(
        statement: """
        MATCH (c:Committee {code: $committeeCode})
        OPTIONAL MATCH (c)-[:HELD_MEETING]->(m:Meeting)
        OPTIONAL MATCH (c)<-[:PRESENTED_TO]-(e:Document {document_type: 'E'})
        OPTIONAL MATCH (c)<-[:REFERRED_TO]-(b:Bill)

        WITH c, m, e, b,
          date() - duration({days: 30}) AS thirtyDaysAgo,
          date() - duration({days: 90}) AS ninetyDaysAgo

        WITH c,
          count(DISTINCT m) AS totalMeetings,
          count(DISTINCT CASE WHEN m.date >= thirtyDaysAgo THEN m END) AS meetings30,
          count(DISTINCT CASE WHEN m.date >= ninetyDaysAgo THEN m END) AS meetings90,
          count(DISTINCT e) AS evidenceDocs,
          count(DISTINCT CASE WHEN b.status IN ['In Committee', 'Reported'] THEN b END) AS activeBills,
          size((c)<-[:SERVES_ON]-()) AS memberCount

        OPTIONAL MATCH (c)-[:HELD_MEETING]->(allM:Meeting)
        OPTIONAL MATCH (allM)<-[:PART_OF]-(s:Statement)

        WITH c, totalMeetings, meetings30, meetings90, evidenceDocs, activeBills, memberCount,
          count(DISTINCT s) AS totalStatements,
          count(DISTINCT allM) AS meetingsWithStatements

        RETURN {
          committee: c,
          total_meetings: toInteger(totalMeetings),
          meetings_last_30_days: toInteger(meetings30),
          meetings_last_90_days: toInteger(meetings90),
          total_evidence_documents: toInteger(evidenceDocs),
          active_bills_count: toInteger(activeBills),
          member_count: toInteger(memberCount),
          avg_statements_per_meeting: CASE WHEN meetingsWithStatements > 0
            THEN toFloat(totalStatements) / toFloat(meetingsWithStatements)
            ELSE 0.0
          END
        }
        """
        columnName: "committeeActivityMetrics"
      )

    # Party performance averages for comparison
    mpPartyAverages(partyCode: String!): MPAverages
      @cypher(
        statement: """
        MATCH (party:Party {code: $partyCode})<-[:MEMBER_OF]-(mp:MP)
        WHERE mp.current = true

        WITH party, mp,
          CASE
            WHEN date().month < 4 THEN date().year
            ELSE date().year + 1
          END AS current_fiscal_year

        // Calculate total votes in the system for participation rate
        CALL {
          MATCH (v:Vote)
          RETURN count(DISTINCT v) AS total_votes
        }

        // For each MP, calculate their metrics
        CALL {
          WITH mp, current_fiscal_year
          OPTIONAL MATCH (mp)-[:SPONSORED]->(bill:Bill)
          RETURN count(DISTINCT bill) AS mp_bills_sponsored,
                 count(DISTINCT CASE WHEN bill.status = 'Passed' THEN bill END) AS mp_bills_passed
        }

        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[voted:VOTED]->(vote:Vote)
          WITH mp, voted, vote, count(DISTINCT vote) AS mp_votes_participated
          // Calculate party alignment (votes where MP voted same as majority of their party)
          OPTIONAL MATCH (vote)<-[party_votes:VOTED]-(party_mp:MP)-[:MEMBER_OF]->(mp_party:Party)
          WHERE mp_party.code = mp.party
          WITH mp, vote, voted, mp_votes_participated,
               count(DISTINCT CASE WHEN party_votes.position = voted.position THEN party_mp END) AS same_position_count,
               count(DISTINCT party_mp) AS total_party_votes
          WITH mp, mp_votes_participated,
               count(DISTINCT CASE WHEN toFloat(same_position_count) / toFloat(total_party_votes) > 0.5 THEN vote END) AS aligned_votes
          RETURN mp_votes_participated, aligned_votes
        }

        CALL {
          WITH mp, current_fiscal_year
          OPTIONAL MATCH (mp)-[:INCURRED]->(expense:Expense {fiscal_year: current_fiscal_year})
          RETURN sum(expense.amount) AS mp_current_year_expenses
        }

        CALL {
          WITH mp
          OPTIONAL MATCH (mp)-[:SERVES_ON]->(committee:Committee)
          OPTIONAL MATCH (mp)<-[:MADE_BY]-(s:Statement)-[:PART_OF]->(d:Document {document_type: 'E'})
          WITH mp, count(DISTINCT committee) AS committee_memberships, count(DISTINCT s) AS committee_statements
          // Weight: 1 point per membership + 0.1 points per statement
          RETURN (committee_memberships + committee_statements * 0.1) AS mp_committee_activity
        }

        // Calculate averages across all party MPs
        WITH party, total_votes,
             avg(mp_bills_sponsored) AS avg_bills_sponsored,
             avg(mp_bills_passed) AS avg_bills_passed,
             avg(mp_current_year_expenses) AS avg_current_year_expenses,
             avg(CASE WHEN total_votes > 0
                  THEN (toFloat(mp_votes_participated) / toFloat(total_votes)) * 100.0
                  ELSE 0.0 END) AS avg_voting_participation_rate,
             avg(CASE WHEN mp_votes_participated > 0
                  THEN (toFloat(aligned_votes) / toFloat(mp_votes_participated)) * 100.0
                  ELSE 0.0 END) AS avg_party_discipline_score,
             avg(CASE WHEN mp_bills_sponsored > 0
                  THEN (toFloat(mp_bills_passed) / toFloat(mp_bills_sponsored)) * 100.0
                  ELSE 0.0 END) AS avg_legislative_success_rate,
             avg(mp_committee_activity) AS avg_committee_activity_index,
             count(DISTINCT mp) AS mp_count

        RETURN {
          party_code: party.code,
          party_name: party.name,
          avg_voting_participation_rate: avg_voting_participation_rate,
          avg_party_discipline_score: avg_party_discipline_score,
          avg_legislative_success_rate: avg_legislative_success_rate,
          avg_committee_activity_index: avg_committee_activity_index,
          avg_bills_sponsored: avg_bills_sponsored,
          avg_bills_passed: avg_bills_passed,
          avg_current_year_expenses: avg_current_year_expenses,
          mp_count: mp_count
        } AS averages
        """
        columnName: "averages"
      )

    # ============================================
    # Parliament & Session Queries
    # ============================================

    # Get current parliament
    currentParliament: Parliament
      @cypher(
        statement: """
        MATCH (p:Parliament {is_current: true})
        RETURN p
        """
        columnName: "p"
      )

    # Get current session
    currentSession: Session
      @cypher(
        statement: """
        MATCH (s:Session {is_current: true})
        RETURN s
        """
        columnName: "s"
      )

    # Get statistics for a parliament (bills, votes, debates)
    parliamentStats(parliamentNumber: Int!): ParliamentStats
      @cypher(
        statement: """
        MATCH (p:Parliament {number: $parliamentNumber})
        WITH p.number AS number,
             p.ordinal AS ordinal,
             p.election_date AS election_date,
             p.opening_date AS opening_date,
             p.dissolution_date AS dissolution_date,
             p.party_in_power AS party_in_power,
             p.prime_minister AS prime_minister,
             p.total_seats AS total_seats,
             p
        OPTIONAL MATCH (p)<-[:FROM_PARLIAMENT]-(b:Bill)
        OPTIONAL MATCH (p)-[:HAS_SESSION]->(s:Session)
        OPTIONAL MATCH (s)<-[:FROM_SESSION]-(v:Vote)
        OPTIONAL MATCH (s)<-[:FROM_SESSION]-(d:Document)

        RETURN {
          parliament: {
            number: number,
            ordinal: ordinal,
            election_date: election_date,
            opening_date: opening_date,
            dissolution_date: dissolution_date,
            party_in_power: party_in_power,
            prime_minister: prime_minister,
            total_seats: total_seats
          },
          bill_count: count(DISTINCT b),
          vote_count: count(DISTINCT v),
          document_count: count(DISTINCT d),
          session_count: count(DISTINCT s)
        } AS stats
        """
        columnName: "stats"
      )

    # Get statistics for a session (bills, votes, debates)
    sessionStats(sessionId: ID!): SessionStats
      @cypher(
        statement: """
        MATCH (s:Session {id: $sessionId})
        WITH s.id AS id,
             s.parliament_number AS parliament_number,
             s.session_number AS session_number,
             s.start_date AS start_date,
             s.end_date AS end_date,
             s.prorogation_date AS prorogation_date,
             s.is_current AS is_current,
             s
        OPTIONAL MATCH (s)<-[:FROM_SESSION]-(b:Bill)
        OPTIONAL MATCH (s)<-[:FROM_SESSION]-(v:Vote)
        OPTIONAL MATCH (s)<-[:FROM_SESSION]-(d:Document)

        RETURN {
          session: {
            id: id,
            parliament_number: parliament_number,
            session_number: session_number,
            start_date: start_date,
            end_date: end_date,
            prorogation_date: prorogation_date,
            is_current: is_current
          },
          bill_count: count(DISTINCT b),
          vote_count: count(DISTINCT v),
          document_count: count(DISTINCT d)
        } AS stats
        """
        columnName: "stats"
      )

    # ============================================
    # Written Questions Queries
    # ============================================

    # Get written questions asked by a specific MP
    writtenQuestionsByMP(
      mpId: ID!
      session: String
      limit: Int = 50
    ): [WrittenQuestion!]!
      @cypher(
        statement: """
        MATCH (mp:MP {id: $mpId})<-[:ASKED_BY]-(wq:WrittenQuestion)
        WHERE $session IS NULL OR wq.session_id = $session
        RETURN wq
        ORDER BY wq.date_asked DESC
        LIMIT $limit
        """
        columnName: "wq"
      )

    # Get written questions by status
    writtenQuestionsByStatus(
      status: String!
      session: String
      limit: Int = 50
    ): [WrittenQuestion!]!
      @cypher(
        statement: """
        MATCH (wq:WrittenQuestion)
        WHERE toLower(wq.status) CONTAINS toLower($status)
          AND ($session IS NULL OR wq.session_id = $session)
        RETURN wq
        ORDER BY wq.date_asked DESC
        LIMIT $limit
        """
        columnName: "wq"
      )

    # Get written questions by topic
    writtenQuestionsByTopic(
      topic: String!
      session: String
      limit: Int = 50
    ): [WrittenQuestion!]!
      @cypher(
        statement: """
        MATCH (wq:WrittenQuestion)
        WHERE any(t IN wq.topics WHERE toLower(t) CONTAINS toLower($topic))
          AND ($session IS NULL OR wq.session_id = $session)
        RETURN wq
        ORDER BY wq.date_asked DESC
        LIMIT $limit
        """
        columnName: "wq"
      )

    # Get all written questions for a session with optional filters
    allWrittenQuestions(
      session: String = "45-1"
      status: String
      limit: Int = 100
      offset: Int = 0
    ): [WrittenQuestion!]!
      @cypher(
        statement: """
        MATCH (wq:WrittenQuestion)
        WHERE wq.session_id = $session
          AND ($status IS NULL OR toLower(wq.status) CONTAINS toLower($status))
        RETURN wq
        ORDER BY wq.date_asked DESC
        SKIP $offset
        LIMIT $limit
        """
        columnName: "wq"
      )

    # Count written questions by status for a session
    writtenQuestionStats(session: String = "45-1"): WrittenQuestionStats
      @cypher(
        statement: """
        MATCH (wq:WrittenQuestion {session_id: $session})
        WITH count(wq) as total,
             sum(CASE WHEN toLower(wq.status) CONTAINS 'answer' THEN 1 ELSE 0 END) as answered,
             sum(CASE WHEN toLower(wq.status) CONTAINS 'await' THEN 1 ELSE 0 END) as awaiting
        RETURN {
          total: total,
          answered: answered,
          awaiting: awaiting
        } as stats
        """
        columnName: "stats"
      )
  }

  # Written Question statistics type
  type WrittenQuestionStats {
    total: Int!
    answered: Int!
    awaiting: Int!
  }
`;
