/**
 * Entitlements Utility Library
 *
 * Provides client-side and server-side entitlement checking for GR module features.
 * Integrates with Supabase RLS policies and functions.
 */

import { createClient } from '@/lib/supabase/client';
import { createServerClient } from '@/lib/supabase/server';
import type { EntitlementType, OrganizationMember } from './types/supabase';

// ============================================================================
// TYPES
// ============================================================================

export interface EntitlementCheck {
  hasAccess: boolean;
  reason?: string;
  requiredTier?: 'free' | 'pro' | 'enterprise';
  requiredEntitlement?: EntitlementType;
}

export interface UserEntitlements {
  subscriptionTier: 'free' | 'pro' | 'enterprise';
  organizationEntitlements: EntitlementType[];
  hasGRModule: boolean;
  hasGovInstitutions: boolean;
  hasSalesforceSync: boolean;
  hasAdvancedSearch: boolean;
  hasAPIAccess: boolean;
}

// ============================================================================
// CLIENT-SIDE FUNCTIONS
// ============================================================================

/**
 * Check if current user has specific entitlement
 * Client-side function using Supabase RPC
 */
export async function hasEntitlement(
  entitlement: EntitlementType
): Promise<boolean> {
  const supabase = createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return false;

  const { data, error } = await supabase.rpc('user_has_entitlement', {
    p_user_id: user.id,
    p_entitlement: entitlement
  });

  if (error) {
    console.error('Error checking entitlement:', error);
    return false;
  }

  return data || false;
}

/**
 * Check if user has organization membership
 */
export async function hasOrgMembership(orgId: string): Promise<boolean> {
  const supabase = createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return false;

  const { data, error } = await supabase.rpc('has_org_membership', {
    p_user_id: user.id,
    p_org_id: orgId
  });

  if (error) {
    console.error('Error checking org membership:', error);
    return false;
  }

  return data || false;
}

/**
 * Check if user has minimum role in organization
 */
export async function hasOrgRole(
  orgId: string,
  minRole: 'viewer' | 'member' | 'manager' | 'admin'
): Promise<boolean> {
  const supabase = createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return false;

  const { data, error } = await supabase.rpc('has_org_role', {
    p_user_id: user.id,
    p_org_id: orgId,
    p_min_role: minRole
  });

  if (error) {
    console.error('Error checking org role:', error);
    return false;
  }

  return data || false;
}

/**
 * Get all entitlements for current user
 */
export async function getUserEntitlements(): Promise<UserEntitlements> {
  const supabase = createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) {
    return {
      subscriptionTier: 'free',
      organizationEntitlements: [],
      hasGRModule: false,
      hasGovInstitutions: false,
      hasSalesforceSync: false,
      hasAdvancedSearch: false,
      hasAPIAccess: false,
    };
  }

  // Get user's subscription tier
  const { data: profile } = await supabase
    .from('user_profiles')
    .select('subscription_tier')
    .eq('id', user.id)
    .single();

  const subscriptionTier = profile?.subscription_tier || 'free';

  // Get organization entitlements
  const { data: orgMemberships } = await supabase
    .from('organization_members')
    .select(`
      organization_id,
      organizations!inner(
        organization_entitlements(entitlement, enabled)
      )
    `)
    .eq('user_id', user.id);

  // Flatten entitlements from all organizations
  const entitlements = new Set<EntitlementType>();

  if (orgMemberships) {
    for (const membership of orgMemberships) {
      const org = (membership as any).organizations;
      if (org?.organization_entitlements) {
        for (const ent of org.organization_entitlements) {
          if (ent.enabled) {
            entitlements.add(ent.entitlement as EntitlementType);
          }
        }
      }
    }
  }

  const organizationEntitlements = Array.from(entitlements);

  return {
    subscriptionTier,
    organizationEntitlements,
    hasGRModule: entitlements.has('gr_module'),
    hasGovInstitutions: entitlements.has('gov_institutions'),
    hasSalesforceSync: entitlements.has('salesforce_sync'),
    hasAdvancedSearch: entitlements.has('advanced_search'),
    hasAPIAccess: entitlements.has('api_access'),
  };
}

/**
 * Check access to GR module features
 */
export async function checkGRModuleAccess(): Promise<EntitlementCheck> {
  const entitlements = await getUserEntitlements();

  // Enterprise tier gets full access
  if (entitlements.subscriptionTier === 'enterprise') {
    return { hasAccess: true };
  }

  // Pro/Free can purchase as organization add-on
  if (entitlements.hasGRModule) {
    return { hasAccess: true };
  }

  return {
    hasAccess: false,
    reason: 'GR Module requires Enterprise tier or organization add-on',
    requiredTier: 'enterprise',
    requiredEntitlement: 'gr_module'
  };
}

/**
 * Check access to government institutions data
 */
export async function checkGovInstitutionsAccess(): Promise<EntitlementCheck> {
  const entitlements = await getUserEntitlements();

  // Enterprise tier gets full access
  if (entitlements.subscriptionTier === 'enterprise') {
    return { hasAccess: true };
  }

  // Pro/Free can purchase as organization add-on
  if (entitlements.hasGovInstitutions) {
    return { hasAccess: true };
  }

  return {
    hasAccess: false,
    reason: 'Government Institutions data requires Enterprise tier or organization add-on',
    requiredTier: 'enterprise',
    requiredEntitlement: 'gov_institutions'
  };
}

// ============================================================================
// SERVER-SIDE FUNCTIONS
// ============================================================================

/**
 * Server-side entitlement check
 * Use in API routes and server components
 */
export async function hasEntitlementServer(
  userId: string,
  entitlement: EntitlementType
): Promise<boolean> {
  const supabase = createServerClient();

  const { data, error } = await supabase.rpc('user_has_entitlement', {
    p_user_id: userId,
    p_entitlement: entitlement
  });

  if (error) {
    console.error('Error checking entitlement:', error);
    return false;
  }

  return data || false;
}

/**
 * Get user's organizations
 */
export async function getUserOrganizations(
  userId: string
): Promise<OrganizationMember[]> {
  const supabase = createServerClient();

  const { data, error } = await supabase
    .from('organization_members')
    .select('*')
    .eq('user_id', userId);

  if (error) {
    console.error('Error fetching organizations:', error);
    return [];
  }

  return data || [];
}

/**
 * Middleware helper for API route protection
 */
export async function requireEntitlement(
  userId: string,
  entitlement: EntitlementType
): Promise<{ allowed: boolean; error?: string }> {
  const hasAccess = await hasEntitlementServer(userId, entitlement);

  if (!hasAccess) {
    return {
      allowed: false,
      error: `Access denied: ${entitlement} entitlement required`
    };
  }

  return { allowed: true };
}

/**
 * Middleware helper for organization membership check
 */
export async function requireOrgMembership(
  userId: string,
  orgId: string
): Promise<{ allowed: boolean; error?: string }> {
  const supabase = createServerClient();

  const { data } = await supabase.rpc('has_org_membership', {
    p_user_id: userId,
    p_org_id: orgId
  });

  if (!data) {
    return {
      allowed: false,
      error: 'Access denied: organization membership required'
    };
  }

  return { allowed: true };
}

/**
 * Middleware helper for organization role check
 */
export async function requireOrgRole(
  userId: string,
  orgId: string,
  minRole: 'viewer' | 'member' | 'manager' | 'admin'
): Promise<{ allowed: boolean; error?: string }> {
  const supabase = createServerClient();

  const { data } = await supabase.rpc('has_org_role', {
    p_user_id: userId,
    p_org_id: orgId,
    p_min_role: minRole
  });

  if (!data) {
    return {
      allowed: false,
      error: `Access denied: ${minRole} role required`
    };
  }

  return { allowed: true };
}

// ============================================================================
// REACT HOOKS (for client components)
// ============================================================================

/**
 * Hook for checking entitlements in React components
 * Usage: const { hasAccess, loading } = useEntitlement('gr_module');
 */
export function useEntitlement(entitlement: EntitlementType) {
  // Note: This would need to be implemented as a React hook
  // Left as placeholder for Phase 3 implementation
  throw new Error('useEntitlement hook not yet implemented - use in Phase 3');
}

/**
 * Hook for getting all user entitlements
 * Usage: const { entitlements, loading } = useUserEntitlements();
 */
export function useUserEntitlements() {
  // Note: This would need to be implemented as a React hook
  // Left as placeholder for Phase 3 implementation
  throw new Error('useUserEntitlements hook not yet implemented - use in Phase 3');
}
