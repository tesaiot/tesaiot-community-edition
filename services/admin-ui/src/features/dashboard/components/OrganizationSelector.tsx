/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import authFetch from '@/utils/auth-fetch';
import { useAuth } from '@/hooks/useAuth';
import { Building2, Users, Shield } from 'lucide-react';

interface Organization {
  id: string;
  name: string;
}

interface OrganizationSelectorProps {
  organizations?: Organization[];
  selectedOrgId?: string;
  onSelect?: (orgId: string) => void;
  // Alternative props for backward compatibility
  value?: string;
  onChange?: (value: string) => void;
}

export const OrganizationSelector: React.FC<OrganizationSelectorProps> = ({
  organizations,
  selectedOrgId,
  onSelect,
  value,
  onChange
}) => {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const { user: currentUser } = useAuth();
  
  // Use either prop pattern
  const currentValue = selectedOrgId || value || '';
  const handleChange = (newValue: string | string[]) => {
    const value = Array.isArray(newValue) ? newValue[0] : newValue;
    if (onSelect) onSelect(value);
    if (onChange) onChange(value);
  };
  
  // Fetch organizations from API with user filtering
  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        // First, try to get user details with organization info
        const userResponse = await authFetch('/api/v1/users/me');
        let userOrgId = null;
        let userOrgName = null;
        let isAdmin = false;
        
        if (userResponse.ok) {
          const userData = await userResponse.json();
          console.log('Current user data:', userData);
          userOrgId = userData.organization_id || userData.organization;
          userOrgName = userData.organization_name;
          isAdmin = userData.is_admin || userData.role === 'admin' || userData.role === 'system_admin';
        }
        
        // If user is not admin and has an organization, only show their organization
        if (!isAdmin && userOrgId) {
          setOrgs([{
            id: userOrgId,
            name: userOrgName || 'My Organization'
          }]);
          // Auto-select the user's organization
          handleChange(userOrgId);
        } else {
          // Admin users or users without organization: fetch all organizations
          const response = await authFetch('/api/v1/organizations');
          if (response.ok) {
            const data = await response.json();
            console.log('All organizations from API:', data);
            
            // Add "All Organizations" option for admins
            const allOrgsOption = isAdmin ? [{ id: 'all', name: 'All Organizations' }] : [];
            
            // Map the API response to our format
            const orgsArray = Array.isArray(data) ? data : (data.organizations || []);
            const mappedOrgs = orgsArray.map((org: any) => ({
              id: org._id || org.id || org.organization_id,
              name: org.name || org.organization_name || 'Unnamed Organization'
            }));
            
            setOrgs([...allOrgsOption, ...mappedOrgs]);
          } else {
            // Fallback for specific user
            if (userOrgId) {
              setOrgs([{
                id: userOrgId,
                name: userOrgName || 'BDH Corporation'
              }]);
              handleChange(userOrgId);
            } else {
              setOrgs([
                { id: 'all', name: 'All Organizations' },
                { id: 'bdh-corp', name: 'BDH Corporation' }
              ]);
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch organizations:', error);
        // Fallback when the organizations API is unreachable
        setOrgs([
          { id: 'all', name: 'All Organizations' }
        ]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchOrganizations();
  }, [organizations, currentUser]);

  // Convert organizations to SelectOption format
  const selectOptions: SelectOption[] = orgs.map(org => ({
    value: org.id,
    label: org.name,
    description: org.id === 'all' ? 'View data from all organizations' : 
                 org.id === 'bdh-corp' ? 'BDH Corporation - Thailand' : 
                 `Organization ID: ${org.id}`,
    icon: org.id === 'all' ? <Shield className="h-4 w-4 text-blue-500" /> :
          org.id === 'bdh-corp' ? <Building2 className="h-4 w-4 text-purple-500" /> :
          <Users className="h-4 w-4 text-gray-500" />
  }));

  // Async search handler for organizations
  const handleSearch = async (query: string) => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      // Search organizations by name
      const response = await authFetch(`/api/v1/organizations?search=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        const orgsArray = Array.isArray(data) ? data : (data.organizations || []);
        const searchedOrgs = orgsArray
          .filter((org: any) => 
            (org.name || org.organization_name || '').toLowerCase().includes(query.toLowerCase())
          )
          .map((org: any) => ({
            id: org._id || org.id || org.organization_id,
            name: org.name || org.organization_name || 'Unnamed Organization'
          }));
        
        setOrgs(searchedOrgs);
      }
    } catch (error) {
      console.error('Failed to search organizations:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SearchableSelect
      options={selectOptions}
      value={currentValue}
      onValueChange={handleChange}
      onSearch={handleSearch}
      loading={loading}
      placeholder="Select organization..."
      searchPlaceholder="Search organizations by name..."
      emptyMessage="No organizations found"
      loadingMessage="Loading organizations..."
      searchable={true}
      clearable={false}
      size="md"
      className="w-[250px]"
      aria-label="Organization Selector"
    />
  );
};
