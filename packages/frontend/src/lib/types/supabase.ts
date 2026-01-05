/**
 * Supabase Database TypeScript Types
 * Auto-generated types for database schema including GR module
 */

// ============================================================================
// ORGANIZATIONS & ENTITLEMENTS
// ============================================================================

export interface Organization {
  id: string;
  name: string;
  slug: string;
  salesforce_instance_url: string | null;
  salesforce_connected: boolean;
  settings: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMember {
  id: string;
  organization_id: string;
  user_id: string;
  role: 'admin' | 'manager' | 'member' | 'viewer';
  created_at: string;
}

export interface OrganizationEntitlement {
  id: string;
  organization_id: string;
  entitlement: string;
  enabled: boolean;
  granted_at: string;
  expires_at: string | null;
  metadata: Record<string, any>;
}

export type EntitlementType =
  | 'gov_institutions'
  | 'gr_module'
  | 'salesforce_sync'
  | 'advanced_search'
  | 'api_access';

export interface SalesforceConnection {
  id: string;
  organization_id: string;
  instance_url: string;
  access_token_encrypted: string;
  refresh_token_encrypted: string;
  token_iv: string;
  token_tag: string;
  expires_at: string | null;
  connected_by: string | null;
  connected_at: string;
  last_sync_at: string | null;
  sync_status: 'pending' | 'syncing' | 'completed' | 'error';
  sync_error: string | null;
  updated_at: string;
}

// ============================================================================
// GR EVENTS
// ============================================================================

export type EventType =
  | 'committee_hearing'
  | 'stakeholder_meeting'
  | 'ministerial_meeting'
  | 'parliamentary_session'
  | 'conference'
  | 'consultation'
  | 'other';

export type EventStatus =
  | 'draft'
  | 'scheduled'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'postponed';

export type EventPriority = 'low' | 'medium' | 'high' | 'urgent';

export type LocationType = 'in_person' | 'virtual' | 'hybrid' | 'tbd';

export interface GREvent {
  id: string;
  organization_id: string;
  title: string;
  title_fr: string | null;
  description: string | null;
  event_type: EventType;
  start_datetime: string;
  end_datetime: string | null;
  timezone: string;
  location: string | null;
  location_type: LocationType | null;
  status: EventStatus;
  priority: EventPriority;
  salesforce_id: string | null;
  salesforce_object_type: string | null;
  sync_status: 'pending' | 'synced' | 'error' | 'conflict';
  last_synced_at: string | null;
  sync_error: string | null;
  tags: string[];
  custom_fields: Record<string, any>;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export type AttendeeType =
  | 'mp'
  | 'senator'
  | 'minister'
  | 'senior_official'
  | 'stakeholder'
  | 'witness'
  | 'lobbyist'
  | 'staff'
  | 'other';

export type RSVPStatus = 'pending' | 'accepted' | 'declined' | 'tentative' | 'no_response';

export interface GREventAttendee {
  id: string;
  event_id: string;
  salesforce_contact_id: string | null;
  mp_id: string | null;  // Neo4j MP.id
  senior_official_id: string | null;  // Neo4j SeniorOfficial.id
  name: string;
  title: string | null;
  organization: string | null;
  email: string | null;
  phone: string | null;
  attendee_type: AttendeeType | null;
  priority: EventPriority;
  is_target: boolean;
  is_confirmed: boolean;
  rsvp_status: RSVPStatus | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// GR BRIEFINGS
// ============================================================================

export type BriefType = 'event' | 'contact' | 'bill' | 'issue' | 'custom';

export type BriefStatus = 'draft' | 'review' | 'approved' | 'published' | 'archived';

export interface GRBriefing {
  id: string;
  organization_id: string;
  event_id: string | null;
  brief_type: BriefType;
  contact_mp_id: string | null;
  contact_senior_official_id: string | null;
  contact_salesforce_id: string | null;
  title: string;
  content_markdown: string;
  content_html: string | null;
  include_web_search: boolean;
  context_data: Record<string, any> | null;
  template_id: string | null;
  salesforce_content_note_id: string | null;
  salesforce_linked_entity_id: string | null;
  version: number;
  is_current: boolean;
  parent_brief_id: string | null;
  status: BriefStatus;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export type TemplateTone = 'professional' | 'formal' | 'conversational' | 'executive';

export interface BriefTemplateSection {
  id: string;
  title: string;
  prompt: string;
  data_sources: string[];
  include_web_search?: boolean;
  max_words?: number;
}

export interface GRBriefTemplate {
  id: string;
  organization_id: string | null;  // NULL = system default
  template_name: string;
  description: string | null;
  salesforce_object_type: string;
  sections: BriefTemplateSection[];
  default_include_web_search: boolean;
  default_tone: TemplateTone;
  is_default: boolean;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// NOTES & SHARING
// ============================================================================

export type NoteContentType = 'full_message' | 'selection' | 'summary' | 'custom';

export interface ChatNote {
  id: string;
  user_id: string;
  organization_id: string | null;
  conversation_id: string | null;
  message_id: string | null;
  title: string;
  content: string;
  content_type: NoteContentType;
  tags: string[];
  collection_id: string | null;
  salesforce_content_note_id: string | null;
  created_at: string;
  updated_at: string;
}

export type CollectionVisibility = 'private' | 'organization' | 'public';

export interface BookmarkCollectionExtended {
  id: string;
  user_id: string;
  organization_id: string | null;
  visibility: CollectionVisibility;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export type SharePermission = 'view' | 'edit' | 'admin';

export interface CollectionShare {
  id: string;
  collection_id: string;
  shared_with_user_id: string | null;
  shared_with_org_id: string | null;
  permission: SharePermission;
  shared_by: string | null;
  created_at: string;
}

// ============================================================================
// DIGESTS & SYNC
// ============================================================================

export type DigestFrequency = 'daily' | 'weekly' | 'biweekly' | 'monthly';

export interface GRDigestPreferences {
  id: string;
  user_id: string;
  organization_id: string;
  frequency: DigestFrequency;
  send_day: number;
  send_hour: number;
  timezone: string;
  include_upcoming_events: boolean;
  include_recent_briefs: boolean;
  include_parliamentary_activity: boolean;
  custom_sections: any[];
  last_sent_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type SyncDirection = 'to_salesforce' | 'from_salesforce' | 'bidirectional';

export type SyncEntityType = 'event' | 'briefing' | 'note' | 'contact';

export type SyncStatus = 'pending' | 'processing' | 'completed' | 'error' | 'skipped';

export interface GRSyncQueueItem {
  id: string;
  organization_id: string;
  direction: SyncDirection;
  entity_type: SyncEntityType;
  entity_id: string;
  salesforce_id: string | null;
  salesforce_object_type: string | null;
  status: SyncStatus;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  scheduled_at: string;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

// ============================================================================
// DATABASE TYPES (for Supabase client)
// ============================================================================

export interface Database {
  public: {
    Tables: {
      organizations: {
        Row: Organization;
        Insert: Omit<Organization, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<Organization, 'id' | 'created_at'>>;
      };
      organization_members: {
        Row: OrganizationMember;
        Insert: Omit<OrganizationMember, 'id' | 'created_at'>;
        Update: Partial<Omit<OrganizationMember, 'id'>>;
      };
      organization_entitlements: {
        Row: OrganizationEntitlement;
        Insert: Omit<OrganizationEntitlement, 'id' | 'granted_at'>;
        Update: Partial<Omit<OrganizationEntitlement, 'id'>>;
      };
      salesforce_connections: {
        Row: SalesforceConnection;
        Insert: Omit<SalesforceConnection, 'id' | 'connected_at' | 'updated_at'>;
        Update: Partial<Omit<SalesforceConnection, 'id'>>;
      };
      gr_events: {
        Row: GREvent;
        Insert: Omit<GREvent, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<GREvent, 'id'>>;
      };
      gr_event_attendees: {
        Row: GREventAttendee;
        Insert: Omit<GREventAttendee, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<GREventAttendee, 'id'>>;
      };
      gr_briefings: {
        Row: GRBriefing;
        Insert: Omit<GRBriefing, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<GRBriefing, 'id'>>;
      };
      gr_brief_templates: {
        Row: GRBriefTemplate;
        Insert: Omit<GRBriefTemplate, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<GRBriefTemplate, 'id'>>;
      };
      chat_notes: {
        Row: ChatNote;
        Insert: Omit<ChatNote, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<ChatNote, 'id'>>;
      };
      collection_shares: {
        Row: CollectionShare;
        Insert: Omit<CollectionShare, 'id' | 'created_at'>;
        Update: Partial<Omit<CollectionShare, 'id'>>;
      };
      gr_digest_preferences: {
        Row: GRDigestPreferences;
        Insert: Omit<GRDigestPreferences, 'id' | 'created_at' | 'updated_at'>;
        Update: Partial<Omit<GRDigestPreferences, 'id'>>;
      };
      gr_sync_queue: {
        Row: GRSyncQueueItem;
        Insert: Omit<GRSyncQueueItem, 'id' | 'created_at'>;
        Update: Partial<Omit<GRSyncQueueItem, 'id'>>;
      };
    };
    Functions: {
      has_org_membership: {
        Args: { p_user_id: string; p_org_id: string };
        Returns: boolean;
      };
      has_org_role: {
        Args: { p_user_id: string; p_org_id: string; p_min_role: string };
        Returns: boolean;
      };
      org_has_entitlement: {
        Args: { p_org_id: string; p_entitlement: string };
        Returns: boolean;
      };
      user_has_entitlement: {
        Args: { p_user_id: string; p_entitlement: string };
        Returns: boolean;
      };
      can_access_collection: {
        Args: { p_user_id: string; p_collection_id: string };
        Returns: boolean;
      };
    };
  };
}
