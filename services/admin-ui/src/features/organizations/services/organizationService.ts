/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Organization Service
 * 
 * This service handles all API interactions for organization management.
 * It provides a clean interface for the UI components to interact with the backend.
 */

import { apiClient } from '@/services/api/apiClient';
import { Organization, OrganizationFormData, PKIServiceRequest } from '../types';
import { AuthTokenManager } from '@/utils/auth-token-manager';

/**
 * Mock data for development
 * In production, this would come from the API
 */
const mockOrganizations: Organization[] = [
  {
    id: 'org-001',
    name: 'Acme Corporation',
    plan: 'enterprise',
    status: 'active',
    contact: {
      name: 'John Doe',
      email: 'admin@acme.com',
      phone: '+1-555-0123'
    },
    pki: {
      enabled: true,
      type: 'dedicated',
      caId: 'ca-001'
    },
    billing: {
      plan: 'Enterprise',
      price: 4999,
      billingCycle: 'monthly'
    },
    createdAt: new Date('2024-01-15'),
    expiresAt: new Date('2025-01-15'),
    usage: {
      devices: 1234,
      users: 45,
      apiCalls: 2450000,
      storage: 12.5
    },
    limits: {
      devices: -1, // unlimited
      users: -1,
      apiCalls: -1,
      storage: 100
    }
  },
  {
    id: 'org-002',
    name: 'StartupTech Inc',
    plan: 'starter',
    status: 'active',
    contact: {
      name: 'Jane Smith',
      email: 'admin@startuptech.com'
    },
    pki: {
      enabled: true,
      type: 'shared'
    },
    billing: {
      plan: 'Starter',
      price: 999,
      billingCycle: 'monthly'
    },
    createdAt: new Date('2024-03-01'),
    expiresAt: new Date('2025-03-01'),
    usage: {
      devices: 156,
      users: 8,
      apiCalls: 450000,
      storage: 2.3
    },
    limits: {
      devices: 10000,
      users: 100,
      apiCalls: 1000000,
      storage: 10
    }
  }
];

/**
 * Organization Service class
 */
class OrganizationService {
  /**
   * Wait for authentication to be ready
   */
  private async waitForAuth(maxRetries = 10, delayMs = 500): Promise<boolean> {
    for (let i = 0; i < maxRetries; i++) {
      if (AuthTokenManager.hasValidToken()) {
        console.log('[organizationService] Authentication ready');
        return true;
      }
      console.log(`[organizationService] Waiting for authentication... attempt ${i + 1}/${maxRetries}`);
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
    console.warn('[organizationService] Authentication timeout - no valid token found');
    return false;
  }

  /**
   * Handle API errors with proper logging and response parsing
   */
  private handleApiError(error: any, operation: string): never {
    console.error(`[organizationService] ${operation} failed:`, error);
    
    if (error.response) {
      const status = error.response.status;
      const contentType = error.response.headers?.['content-type'] || '';
      
      // Handle HTML error responses (usually from server error pages)
      if (contentType.includes('text/html')) {
        console.error('[organizationService] Received HTML response instead of JSON');
        if (status === 401) {
          throw new Error('Authentication required. Please log in again.');
        }
        throw new Error(`Server error (${status}). Please try again later.`);
      }
      
      // Handle JSON error responses
      console.error('[organizationService] Error details:', {
        status,
        message: error.response.data?.message || error.message,
        data: error.response.data
      });
      
      if (status === 401) {
        // Clear invalid tokens
        AuthTokenManager.clearTokens();
        throw new Error('Authentication expired. Please log in again.');
      }
    }
    
    throw error;
  }
  /**
   * Get all organizations
   */
  async getOrganizations(): Promise<Organization[]> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        console.warn('[organizationService] Proceeding without authentication');
        return [];
      }
      
      console.log('[organizationService] Fetching organizations from API...');
      // Use actual API with enhanced error handling
      let response;
      try {
        response = await apiClient.get('/api/v1/organizations');
        console.log('[organizationService] API response:', response.data);
      } catch (error: any) {
        // Check if we got an HTML response
        if (error.isHtmlResponse || error.response?.headers?.['content-type']?.includes('text/html')) {
          console.error('[organizationService] Received HTML response, API endpoint may be incorrect');
          console.log('[organizationService] Attempting without trailing slash...');
          
          // Try without trailing slash
          try {
            response = await apiClient.get('/api/v1/organizations');
            console.log('[organizationService] Success without trailing slash:', response.data);
          } catch (retryError: any) {
            console.error('[organizationService] Both attempts failed');
            throw error; // Throw original error
          }
        } else {
          throw error;
        }
      }
      
      // Map API response to match Organization interface
      const mapped = response.data.organizations.map((org: any) => ({
        id: org.id || org._id,
        name: org.name,
        plan: org.plan || org.subscription || 'starter',
        status: org.status || 'active',
        contact: {
          name: org.contact?.name || 'Admin',
          email: org.contact?.email || `admin@${org.name.toLowerCase().replace(/\s+/g, '')}.com`,
          phone: org.contact?.phone
        },
        pki: {
          enabled: true,
          type: org.plan === 'enterprise' || org.subscription === 'enterprise' ? 'dedicated' : 'shared'
        },
        billing: {
          plan: org.plan || org.subscription || 'Starter',
          price: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? 4999 : 
                 (org.plan === 'business' || org.subscription === 'business') ? 2499 : 999,
          billingCycle: 'monthly'
        },
        createdAt: new Date(org.created_at || org.createdAt || '2024-01-01'),
        expiresAt: new Date(org.expires_at || org.expiresAt || '2025-12-31'),
        usage: {
          devices: org.device_count !== undefined ? org.device_count : (org.usage?.devices || 0),
          users: org.user_count !== undefined ? org.user_count : (org.usage?.users || 0),
          // API sends api_calls_billing (cumulative), api_calls_24h (Prometheus), api_calls_total
          // Prefer billing usage as it's more accurate monthly count
          apiCalls: org.api_calls_billing || org.api_calls_24h || org.api_calls_total || org.api_calls || org.usage?.apiCalls || 0,
          storage: org.storage_bytes || org.storage || org.usage?.storage || 0
        },
        limits: {
          devices: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? -1 : 10000,
          users: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? -1 : 100,
          apiCalls: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? -1 : 1000000,
          storage: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? 100 : 10
        },
        // Preserve hierarchy fields
        parent_id: org.parent_id,
        organization_id: org.organization_id,
        type: org.type,
        depth: org.depth,
        sub_organizations_count: org.sub_organizations_count,
        // Add count fields directly
        device_count: org.device_count,
        user_count: org.user_count,
        // Storage in bytes - from API (for OrganizationCard display)
        storage_bytes: org.storage_bytes ?? 0
      }));
      console.log('[organizationService] Mapped organizations:', mapped.length, 'organizations');
      console.log('[organizationService] First 3 organizations:', mapped.slice(0, 3).map(o => ({
        id: o.id,
        name: o.name,
        parent_id: o.parent_id,
        type: o.type
      })));
      return mapped;
    } catch (error: any) {
      this.handleApiError(error, 'Failed to fetch organizations');
    }
  }

  /**
   * Get a single organization by ID
   */
  async getOrganization(id: string): Promise<Organization> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      console.log(`[organizationService] Fetching organization ${id}`);
      const response = await apiClient.get(`/api/v1/organizations/${id}`);
      console.log('[organizationService] Raw API response:', response.data);
      
      // Handle different response structures
      const org = response.data.organization || response.data;
      console.log('[organizationService] Extracted org data:', {
        id: org.id,
        name: org.name,
        device_count: org.device_count,
        user_count: org.user_count
      });
      
      // Use the mapping helper
      const mapped = this.mapApiResponseToOrganization(org);
      console.log('[organizationService] After mapping:', {
        id: mapped.id,
        name: mapped.name,
        device_count: mapped.device_count,
        user_count: mapped.user_count,
        usage: mapped.usage
      });
      return mapped;
    } catch (error: any) {
      this.handleApiError(error, `Failed to fetch organization ${id}`);
    }
  }

  /**
   * Map API response to Organization interface
   */
  private mapApiResponseToOrganization(org: any): Organization {
    console.log('[organizationService] Mapping organization:', {
      id: org.id || org._id,
      name: org.name,
      device_count: org.device_count,
      user_count: org.user_count,
      usage: org.usage
    });
    
    return {
      id: org.id || org._id,
      _id: org._id || org.id,  // Preserve both id formats
      organization_id: org.organization_id,
      name: org.name,
      description: org.description || '',
      plan: org.plan || org.subscription || 'starter',
      status: org.status || 'active',
      contact: org.contact || {
        name: 'Admin',
        email: `admin@${org.name.toLowerCase().replace(/\s+/g, '')}.com`
      },
      address: {
        street: org.address?.street || '123 Main Street',
        city: org.address?.city || 'Bangkok',
        country: org.address?.country || 'Thailand',
        postalCode: org.address?.postalCode || '10110'
      },
      pki: org.pki || {
        enabled: true,
        type: (org.plan === 'enterprise' || org.subscription === 'enterprise') ? 'dedicated' : 'shared'
      },
      billing: org.billing || {
        plan: org.billing?.plan || org.plan || org.subscription || 'Starter',
        price: org.billing?.price || ((org.plan === 'enterprise' || org.subscription === 'enterprise') ? 4999 : 
               (org.plan === 'business' || org.subscription === 'business') ? 2499 : 99),
        billingCycle: org.billing?.billingCycle || 'monthly',
        nextBillingDate: org.billing?.nextBillingDate
      },
      createdAt: new Date(org.created_at || org.createdAt || '2024-01-01'),
      expiresAt: new Date(org.expires_at || org.expiresAt || org.expiresAt || '2025-12-31'),
      usage: {
        devices: org.device_count !== undefined ? org.device_count : (org.usage?.devices || 0),
        users: org.user_count !== undefined ? org.user_count : (org.usage?.users || 0),
        certificates: org.usage?.certificates || 0,
        // API sends api_calls_billing (cumulative), api_calls_24h (Prometheus), api_calls_total
        apiCalls: org.api_calls_billing ?? org.api_calls_24h ?? org.api_calls_total ?? org.api_calls ?? org.usage?.apiCalls ?? 0,
        storage: org.storage_bytes ?? org.storage ?? org.usage?.storage ?? 0
      },
      limits: org.limits || this.getPlanLimits(org.plan || org.subscription || 'starter'),
      features: org.features,
      pkiService: org.pkiService || {
        enabled: true,
        caType: 'shared',
        validityPeriod: 365
      },
      // Preserve hierarchy fields
      parent_id: org.parent_id,
      type: org.type,
      depth: org.depth,
      sub_organizations_count: org.sub_organizations_count,
      // Preserve count fields - CRITICAL FOR DASHBOARD
      device_count: org.device_count,
      user_count: org.user_count,
      api_calls: org.api_calls_billing ?? org.api_calls_24h ?? org.api_calls_total ?? org.api_calls,
      // Storage in bytes - from API
      storage_bytes: org.storage_bytes ?? 0
    } as any;  // Use 'as any' to bypass type checking for extra fields
  }

  /**
   * Create a new organization
   */
  async createOrganization(data: OrganizationFormData): Promise<Organization> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const response = await apiClient.post('/api/v1/organizations', {
        name: data.name,
        description: data.description || '',
        plan: data.plan,
        contact: data.contact
      });
      
      const org = response.data;
      
      // Map response to Organization interface
      return {
        id: org.id || org._id,
        name: org.name,
        plan: data.plan as any,
        status: 'trial',
        contact: data.contact,
        pki: {
          enabled: false
        },
        billing: {
          plan: data.plan,
          price: data.plan === 'enterprise' ? 4999 : data.plan === 'business' ? 2499 : 999,
          billingCycle: 'monthly'
        },
        createdAt: new Date(org.created_at || Date.now()),
        expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days trial
        usage: {
          devices: 0,
          users: 0,
          apiCalls: 0,
          storage: 0
        },
        limits: this.getPlanLimits(data.plan)
      };
    } catch (error: any) {
      this.handleApiError(error, 'Failed to create organization');
    }
  }

  /**
   * Update an organization
   */
  async updateOrganization(id: string, data: Partial<Organization>): Promise<Organization> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const updateData: any = {};
      
      if (data.name) updateData.name = data.name;
      if (data.description) updateData.description = data.description;
      if (data.plan) updateData.plan = data.plan;
      if (data.status) updateData.status = data.status;
      if (data.contact) updateData.contact = data.contact;
      
      await apiClient.put(`/api/v1/organizations/${id}`, updateData);
      
      // Fetch updated organization
      return this.getOrganization(id);
    } catch (error: any) {
      this.handleApiError(error, `Failed to update organization ${id}`);
    }
  }

  /**
   * Delete an organization
   */
  async deleteOrganization(id: string): Promise<void> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      await apiClient.delete(`/api/v1/organizations/${id}`);
    } catch (error: any) {
      this.handleApiError(error, `Failed to delete organization ${id}`);
    }
  }

  /**
   * Update PKI service for an organization
   */
  async updatePKIService(orgId: string, config: PKIServiceRequest): Promise<void> {
    try {
      // await apiClient.post(`/organizations/${orgId}/pki`, config);
      
      const org = mockOrganizations.find(o => o.id === orgId);
      if (org) {
        org.pki = {
          enabled: true,
          type: config.type,
          settings: config.settings
        };
      }
    } catch (error) {
      console.error(`Failed to update PKI service for ${orgId}:`, error);
      throw error;
    }
  }

  /**
   * Get organization dashboard data
   */
  async getOrganizationDashboard(id: string): Promise<any> {
    try {
      // const response = await apiClient.get(`/organizations/${id}/dashboard`);
      // return response.data;
      
      // Mock implementation would return dashboard metrics
      return Promise.resolve({
        metrics: {},
        recentActivity: [],
        alerts: []
      });
    } catch (error) {
      console.error(`Failed to fetch dashboard for ${id}:`, error);
      throw error;
    }
  }

  /**
   * Get organization administrators
   */
  async getOrganizationAdmins(orgId: string): Promise<any[]> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        return [];
      }
      
      const response = await apiClient.get(`/api/v1/organizations/${orgId}/admins`);
      return response.data;
    } catch (error: any) {
      console.error(`Failed to fetch admins for ${orgId}:`, error);
      // Return empty array on error
      return [];
    }
  }

  /**
   * Get organization users
   */
  async getOrganizationUsers(orgId: string): Promise<any[]> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        return [];
      }
      
      const response = await apiClient.get(`/api/v1/organizations/${orgId}/users`);
      return response.data;
    } catch (error: any) {
      console.error(`Failed to fetch users for ${orgId}:`, error);
      return [];
    }
  }

  /**
   * Get organization devices
   */
  async getOrganizationDevices(orgId: string): Promise<any[]> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        return [];
      }
      
      const response = await apiClient.get(`/api/v1/devices?organization_id=${orgId}`);
      return response.data;
    } catch (error: any) {
      console.error(`Failed to fetch devices for ${orgId}:`, error);
      return [];
    }
  }

  /**
   * Create organization admin
   */
  async createOrganizationAdmin(orgId: string, adminData: any): Promise<any> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const response = await apiClient.post(`/api/v1/organizations/${orgId}/admins`, adminData);
      return response.data;
    } catch (error: any) {
      this.handleApiError(error, `Failed to create admin for ${orgId}`);
    }
  }

  /**
   * Create organization user
   */
  async createOrganizationUser(orgId: string, userData: any): Promise<any> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const response = await apiClient.post(`/api/v1/users`, {
        ...userData,
        organization_id: orgId
      });
      return response.data;
    } catch (error: any) {
      this.handleApiError(error, `Failed to create user for ${orgId}`);
    }
  }

  /**
   * Get organization tree structure
   */
  async getOrganizationTree(): Promise<any[]> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        console.warn('[organizationService] No authentication for tree fetch');
        return [];
      }
      
      console.log('[organizationService] Fetching organization tree...');
      const response = await apiClient.get('/api/v1/organizations/tree');
      console.log('[organizationService] Tree response:', response.data);
      if (response.data.tree && response.data.tree.length > 0) {
        console.log('[organizationService] First tree node:', response.data.tree[0]);
        console.log('[organizationService] First tree node children:', response.data.tree[0].children);
        console.log('[organizationService] Tree length:', response.data.tree.length);
      }
      
      // Check if we have organizations but no tree structure, build it client-side
      if (response.data.tree && response.data.tree.length === 0) {
        console.log('[organizationService] No tree data returned, fetching organizations to build tree...');
        
        // Get all organizations and build tree client-side
        const orgsResponse = await this.getOrganizations();
        const tree = this.buildTreeFromOrganizations(orgsResponse);
        console.log('[organizationService] Built tree from organizations:', tree);
        return tree;
      }
      
      return response.data.tree || [];
    } catch (error: any) {
      console.error('[organizationService] Failed to fetch organization tree:', error);
      
      // Don't try fallback if it's an auth error
      if (error.response?.status === 401) {
        return [];
      }
      
      // Try to build tree from organizations as fallback
      try {
        const orgs = await this.getOrganizations();
        const tree = this.buildTreeFromOrganizations(orgs);
        console.log('[organizationService] Built tree from organizations (fallback):', tree);
        return tree;
      } catch (fallbackError) {
        console.error('[organizationService] Fallback also failed:', fallbackError);
        return [];
      }
    }
  }

  /**
   * Build tree structure from flat organization list
   */
  private buildTreeFromOrganizations(organizations: Organization[]): any[] {
    console.log('[organizationService] Building tree from organizations:', organizations);
    
    // Create a map for quick lookup
    const orgMap = new Map<string, any>();
    const roots: any[] = [];
    
    // First pass: create all nodes
    organizations.forEach(org => {
      const node = {
        id: org.id,
        organization_id: org.organization_id,
        name: org.name,
        type: org.type || 'root',
        depth: org.depth || 0,
        device_count: org.devices?.count || 0,
        user_count: org.users?.count || 0,
        plan: org.plan,
        status: org.status,
        parent_id: org.parent_id,
        children: []
      };
      orgMap.set(org.id, node);
    });
    
    // Second pass: build tree structure
    organizations.forEach(org => {
      if (org.parent_id) {
        const parent = orgMap.get(org.parent_id);
        if (parent) {
          parent.children.push(orgMap.get(org.id));
        } else {
          // Parent not found, add as root
          roots.push(orgMap.get(org.id));
        }
      } else {
        // No parent, it's a root
        roots.push(orgMap.get(org.id));
      }
    });
    
    console.log('[organizationService] Built tree with roots:', roots);
    return roots;
  }

  /**
   * Create a sub-organization
   */
  async createSubOrganization(parentId: string, data: any): Promise<any> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const response = await apiClient.post(`/api/v1/organizations/${parentId}/sub-organizations`, data);
      return response.data.organization;
    } catch (error: any) {
      this.handleApiError(error, `Failed to create sub-organization for ${parentId}`);
    }
  }

  /**
   * Get organization hierarchy
   */
  async getOrganizationHierarchy(orgId: string): Promise<any> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }
      
      const response = await apiClient.get(`/api/v1/organizations/${orgId}/hierarchy`);
      return response.data.hierarchy;
    } catch (error: any) {
      this.handleApiError(error, `Failed to fetch hierarchy for ${orgId}`);
    }
  }

  /**
   * Get organization usage metrics (REAL DATA from Prometheus/MongoDB)
   * NO MOCK DATA - Returns actual metrics from backend
   */
  async getOrganizationUsage(orgId: string): Promise<any> {
    try {
      // Wait for authentication to be ready
      const authReady = await this.waitForAuth();
      if (!authReady) {
        throw new Error('Authentication required');
      }

      console.log(`[organizationService] Fetching REAL usage metrics for ${orgId}...`);
      const response = await apiClient.get(`/api/v1/organizations/${orgId}/usage`);
      console.log('[organizationService] Usage API response:', response.data);

      return response.data;
    } catch (error: any) {
      console.error(`[organizationService] Failed to fetch usage for ${orgId}:`, error);
      // Return null to indicate no data available (NOT mock data)
      return null;
    }
  }

  /**
   * Helper method to get plan limits
   */
  private getPlanLimits(plan: string): Organization['limits'] {
    const limits: Record<string, Organization['limits']> = {
      community: {
        devices: 100,
        users: 10,
        apiCalls: 100000,
        storage: 1
      },
      starter: {
        devices: 10000,
        users: 100,
        apiCalls: 1000000,
        storage: 10
      },
      business: {
        devices: 100000,
        users: 1000,
        apiCalls: 10000000,
        storage: 100
      },
      enterprise: {
        devices: -1,
        users: -1,
        apiCalls: -1,
        storage: -1
      }
    };
    
    return limits[plan] || limits.community;
  }
}

// Export singleton instance
export const organizationService = new OrganizationService();