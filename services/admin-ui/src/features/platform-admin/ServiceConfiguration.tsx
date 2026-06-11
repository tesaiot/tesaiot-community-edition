/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Settings, 
  Building2, 
  ToggleLeft, 
  ToggleRight,
  Save,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Shield,
  Zap,
  Database,
  Activity,
  Users,
  Key,
  FileText,
  BarChart3,
  Bell,
  Package,
  ArrowLeft
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/hooks/useAuth';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import axios from 'axios';

// Service categories and their features
const serviceCategories = {
  'Core Features': {
    icon: <Zap className="h-4 w-4" />,
    features: [
      { id: 'device_management', name: 'Device Management', description: 'Device provisioning and control' },
      { id: 'user_management', name: 'User Management', description: 'User accounts and permissions' },
      { id: 'certificates', name: 'Certificates', description: 'PKI certificate management' },
      { id: 'organizations', name: 'Organizations', description: 'Multi-tenant support' },
    ]
  },
  'Dashboard Cards': {
    icon: <Activity className="h-4 w-4" />,
    features: [
      { id: 'system_health_card', name: 'System Health Card', description: 'Real-time health monitoring' },
      { id: 'device_stats_card', name: 'Device Statistics', description: 'Device count and status' },
      { id: 'user_activity_card', name: 'User Activity', description: 'Recent user actions' },
      { id: 'compliance_card', name: 'Compliance Status', description: 'ETSI compliance tracking' },
    ]
  },
  'Menu Items': {
    icon: <Package className="h-4 w-4" />,
    features: [
      { id: 'menu_dashboard', name: 'Dashboard', description: 'Main dashboard' },
      { id: 'menu_devices', name: 'Devices & Identity', description: 'Device management menu' },
      { id: 'menu_users', name: 'Users', description: 'User management menu' },
      { id: 'menu_certificates', name: 'Certificates', description: 'Certificate menu' },
      { id: 'menu_system_health', name: 'System Health', description: 'System health monitoring' },
      { id: 'menu_activity_logs', name: 'Activity Logs', description: 'System and user activity logs' },
      { id: 'menu_analytics', name: 'Analytics', description: 'Analytics menu' },
      { id: 'menu_compliance', name: 'Compliance', description: 'Compliance menu' },
      { id: 'menu_organizations', name: 'Organizations', description: 'Organization management menu' },
      { id: 'menu_api_keys', name: 'API Keys', description: 'API key management menu' },
      { id: 'menu_settings', name: 'Settings', description: 'System settings menu' },
      { id: 'menu_security', name: 'Security', description: 'Security settings menu' },
    ]
  },
  'Feature Buttons': {
    icon: <Zap className="h-4 w-4" />,
    features: [
      { id: 'device_data_dashboard', name: 'Device Data Dashboard', description: 'Advanced device dashboard button' },
      { id: 'ai_assistant', name: 'AI Assistant', description: 'AI-powered assistant button' },
      { id: 'bulk_operations', name: 'Bulk Operations', description: 'Bulk device actions' },
      { id: 'export_data', name: 'Export Data', description: 'Data export functionality' },
      { id: 'import_devices', name: 'Import Devices', description: 'Bulk device import' },
      { id: 'generate_reports', name: 'Generate Reports', description: 'Report generation' },
    ]
  },
  'Analytics': {
    icon: <BarChart3 className="h-4 w-4" />,
    features: [
      { id: 'basic_analytics', name: 'Basic Analytics', description: 'Simple charts and graphs' },
      { id: 'advanced_analytics', name: 'Advanced Analytics', description: 'Complex data analysis' },
      { id: 'ai_analytics', name: 'AI Analytics', description: 'ML-powered insights' },
      { id: 'custom_dashboards', name: 'Custom Dashboards', description: 'Customizable analytics' },
    ]
  },
  'Security': {
    icon: <Shield className="h-4 w-4" />,
    features: [
      { id: 'security_monitoring', name: 'Security Monitoring', description: 'Threat detection' },
      { id: 'audit_logs', name: 'Audit Logs', description: 'Complete audit trail' },
      { id: 'compliance_tools', name: 'Compliance Tools', description: 'Compliance automation' },
      { id: 'vulnerability_scanning', name: 'Vulnerability Scanning', description: 'Security scanning' },
    ]
  }
};

// Organization interface
interface Organization {
  _id: string;
  id?: string;
  name: string;
  tier?: string;
  type?: 'root' | 'internal' | 'external' | 'platform';
  parent?: string;
  email?: string;
  devices?: number;
  users?: number;
  description?: string;
}

export const ServiceConfiguration: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [selectedOrg, setSelectedOrg] = useState<string>('');
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loadingOrgs, setLoadingOrgs] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['Core Features']);
  const [featureStates, setFeatureStates] = useState<Record<string, boolean>>({});
  const [originalStates, setOriginalStates] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Check platform admin access via RBAC role claim (never a hardcoded account)
  useEffect(() => {
    if (user?.role !== 'platform_admin' && user?.role !== 'super_admin') {
      navigate('/dashboard');
      toast({
        title: 'Unauthorized',
        description: 'Platform Admin access required',
        variant: 'destructive'
      });
    }
  }, [user, navigate, toast]);

  // Fetch real organizations from API
  useEffect(() => {
    const fetchOrganizations = async () => {
      try {
        setLoadingOrgs(true);
        
        // Try multiple token sources
        let token = localStorage.getItem('token') || 
                   localStorage.getItem('authToken') || 
                   sessionStorage.getItem('token') ||
                   sessionStorage.getItem('authToken');
        
        // Check if we have a token in axios defaults
        if (!token && axios.defaults.headers.common['Authorization']) {
          const authHeader = axios.defaults.headers.common['Authorization'] as string;
          if (authHeader && authHeader.startsWith('Bearer ')) {
            token = authHeader.substring(7);
          }
        }
        
        console.log('Fetching organizations with token:', token ? 'Token exists' : 'No token');
        
        if (!token) {
          console.warn('No auth token found. Using demo data for preview.');
          // Use demo data when no token is available
          const demoOrgs = [
            { _id: 'tesa-1', name: 'Thai Embedded Systems Association', type: 'root', devices: 9, users: 2 },
            { _id: 'infineon-1', name: 'Infineon Technology', type: 'root', devices: 0, users: 0 },
            { _id: 'bdh-1', name: 'BDH Corporation', type: 'root', devices: 8, users: 5 },
            { _id: 'infineon-2', name: 'Infineon Technologies', type: 'root', devices: 5, users: 1 },
            { _id: 'tesa-beta', name: 'TESA Beta Team', type: 'internal', devices: 0, users: 2 },
            { _id: 'early-adopters', name: 'Early Adopters', type: 'external', devices: 0, users: 2 },
            { _id: 'tesa-platform', name: 'TESA Platform Infrastructure', type: 'platform', devices: 0, users: 3 }
          ];
          setOrganizations(demoOrgs);
          setLoadingOrgs(false);
          toast({
            title: 'Demo Mode',
            description: 'Using demo organizations. Login for real data.',
          });
          return;
        }
        
        const response = await axios.get('/api/v1/organizations', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        console.log('Organizations response:', response.data);
        
        // Handle both array response and object with organizations property
        let orgData = response.data;
        if (response.data && response.data.organizations) {
          orgData = response.data.organizations;
        }
        
        if (orgData && Array.isArray(orgData)) {
          // Map the organizations to add tier based on type
          const orgs = orgData.map((org: any) => ({
            ...org,
            id: org._id || org.id,
            tier: org.type === 'root' ? 'enterprise' : 
                  org.type === 'internal' ? 'business' : 
                  org.type === 'platform' ? 'platform' : 'startup',
            devices: org.device_count || org.devices || 0,
            users: org.user_count || org.users || 0
          }));
          console.log('Processed organizations:', orgs);
          setOrganizations(orgs);
        } else {
          console.warn('Unexpected organizations data format:', orgData);
          setOrganizations([]);
        }
      } catch (error: any) {
        console.error('Failed to fetch organizations:', error);
        console.error('Error details:', error.response?.data);
        toast({
          title: 'Error',
          description: error.response?.data?.error || 'Failed to load organizations',
          variant: 'destructive'
        });
        setOrganizations([]);
      } finally {
        setLoadingOrgs(false);
      }
    };

    fetchOrganizations();
  }, [toast]);

  // Load organization features when selected
  useEffect(() => {
    if (selectedOrg) {
      loadOrganizationConfiguration(selectedOrg);
    }
  }, [selectedOrg]);
  
  const loadOrganizationConfiguration = async (orgId: string) => {
    try {
      // Try to get saved configuration from API
      const token = localStorage.getItem('token') || 
                   sessionStorage.getItem('token') ||
                   axios.defaults.headers.common['Authorization']?.replace('Bearer ', '');
      
      if (token) {
        const response = await axios.get(
          `/api/v1/platform-admin/organizations/${orgId}/configuration`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        if (response.data?.data?.features) {
          // Use saved configuration
          setFeatureStates(response.data.data.features);
          setOriginalStates(response.data.data.features);
          setHasChanges(false);
          return;
        }
      }
    } catch (error) {
      console.log('No saved configuration found, using defaults');
    }
    
    // Fallback to default configuration
    const defaultFeatures: Record<string, boolean> = {};
    
    // ALL organizations get ALL features enabled by default
    Object.values(serviceCategories).forEach(category => {
      category.features.forEach(feature => {
        defaultFeatures[feature.id] = true;
      });
    });
    
    setFeatureStates(defaultFeatures);
    setOriginalStates(defaultFeatures);
    setHasChanges(false);
  };

  // Check for changes
  useEffect(() => {
    const changed = Object.keys(featureStates).some(
      key => featureStates[key] !== originalStates[key]
    );
    setHasChanges(changed);
  }, [featureStates, originalStates]);

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const toggleFeature = (featureId: string) => {
    setFeatureStates(prev => ({
      ...prev,
      [featureId]: !prev[featureId]
    }));
  };

  const saveConfiguration = async () => {
    if (!selectedOrg) {
      toast({
        title: 'Error',
        description: 'Please select an organization first',
        variant: 'destructive'
      });
      return;
    }
    
    try {
      const token = localStorage.getItem('token') || 
                   sessionStorage.getItem('token') ||
                   axios.defaults.headers.common['Authorization']?.replace('Bearer ', '');
      
      if (!token) {
        toast({
          title: 'Error',
          description: 'Authentication required',
          variant: 'destructive'
        });
        return;
      }
      
      // Save configuration to API
      await axios.put(
        `/api/v1/platform-admin/organizations/${selectedOrg}/configuration`,
        {
          features: featureStates
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );
      
      setOriginalStates(featureStates);
      setHasChanges(false);
      toast({
        title: 'Success',
        description: 'Service configuration saved successfully'
      });
    } catch (error: any) {
      console.error('Error saving configuration:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.message || 'Failed to save configuration',
        variant: 'destructive'
      });
    }
  };

  const discardChanges = () => {
    setFeatureStates(originalStates);
    setHasChanges(false);
    toast({
      title: 'Changes discarded',
      description: 'All unsaved changes have been reverted'
    });
  };

  const getTierBadgeColor = (tier: string) => {
    switch (tier) {
      case 'enterprise': 
      case 'root': 
        return 'bg-purple-100 text-purple-800';
      case 'platform': 
        return 'bg-indigo-100 text-indigo-800';
      case 'business':
      case 'internal': 
        return 'bg-blue-100 text-blue-800';
      case 'startup':
      case 'external': 
        return 'bg-green-100 text-green-800';
      default: 
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getOrgTypeLabel = (type?: string) => {
    switch (type) {
      case 'root': return 'ROOT';
      case 'internal': return 'INTERNAL';
      case 'external': return 'EXTERNAL';
      case 'platform': return 'PLATFORM';
      default: return type?.toUpperCase() || 'UNKNOWN';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/platform-admin')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Settings className="h-8 w-8 text-purple-600" />
              Service Configuration
            </h1>
            <p className="text-gray-600 mt-1">
              Customize service features and UI elements per organization
            </p>
          </div>
        </div>
        
        {hasChanges && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={discardChanges}>
              Discard Changes
            </Button>
            <Button onClick={saveConfiguration}>
              <Save className="h-4 w-4 mr-2" />
              Save Configuration
            </Button>
          </div>
        )}
      </div>

      {/* Organization Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Select Organization</CardTitle>
          <CardDescription>
            Choose an organization to configure its service features
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedOrg} onValueChange={setSelectedOrg} disabled={loadingOrgs}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder={loadingOrgs ? "Loading organizations..." : "Select an organization..."} />
            </SelectTrigger>
            <SelectContent>
              {organizations.map(org => (
                <SelectItem key={org._id || org.id} value={org._id || org.id || ''}>
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-4 w-4" />
                      <span>{org.name}</span>
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      {org.type && (
                        <Badge className={cn('text-xs', getTierBadgeColor(org.tier || org.type || ''))}>
                          {getOrgTypeLabel(org.type)}
                        </Badge>
                      )}
                      <span className="text-xs text-gray-500">
                        {org.devices || 0} devices • {org.users || 0} users
                      </span>
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Feature Configuration */}
      {selectedOrg && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Feature Categories */}
          <div className="lg:col-span-2 space-y-4">
            {Object.entries(serviceCategories).map(([category, config]) => (
              <Card key={category}>
                <CardHeader 
                  className="cursor-pointer"
                  onClick={() => toggleCategory(category)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {config.icon}
                      <CardTitle className="text-lg">{category}</CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">
                        {config.features.filter(f => featureStates[f.id]).length} / {config.features.length}
                      </Badge>
                      {expandedCategories.includes(category) ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </div>
                  </div>
                </CardHeader>
                
                {expandedCategories.includes(category) && (
                  <CardContent className="space-y-4">
                    {config.features.map(feature => (
                      <div key={feature.id} className="flex items-center justify-between">
                        <div className="space-y-1">
                          <Label htmlFor={feature.id} className="text-base">
                            {feature.name}
                          </Label>
                          <p className="text-sm text-gray-500">
                            {feature.description}
                          </p>
                        </div>
                        <Switch
                          id={feature.id}
                          checked={featureStates[feature.id] || false}
                          onCheckedChange={() => toggleFeature(feature.id)}
                        />
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            ))}
          </div>

          {/* Preview Panel */}
          <div className="space-y-4">
            <Card className="sticky top-4">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="h-5 w-5" />
                  Preview
                </CardTitle>
                <CardDescription>
                  How the UI will appear for this organization
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Menu Items Preview */}
                <div>
                  <h4 className="font-medium mb-2">Visible Menu Items</h4>
                  <div className="space-y-1">
                    {serviceCategories['Menu Items'].features
                      .filter(f => featureStates[f.id])
                      .map(feature => (
                        <div key={feature.id} className="flex items-center gap-2 text-sm">
                          <ChevronRight className="h-3 w-3" />
                          {feature.name}
                        </div>
                      ))
                    }
                  </div>
                </div>

                {/* Dashboard Cards Preview */}
                <div>
                  <h4 className="font-medium mb-2">Dashboard Cards</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {serviceCategories['Dashboard Cards'].features
                      .filter(f => featureStates[f.id])
                      .map(feature => (
                        <div key={feature.id} className="border rounded p-2 text-xs">
                          {feature.name.replace(' Card', '')}
                        </div>
                      ))
                    }
                  </div>
                </div>

                {/* Feature Summary */}
                <div>
                  <h4 className="font-medium mb-2">Feature Summary</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span>Total Features</span>
                      <span className="font-medium">
                        {Object.values(featureStates).filter(v => v).length}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Analytics</span>
                      <span className="font-medium">
                        {serviceCategories['Analytics'].features
                          .filter(f => featureStates[f.id]).length > 0 ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Security</span>
                      <span className="font-medium">
                        {serviceCategories['Security'].features
                          .filter(f => featureStates[f.id]).length > 0 ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServiceConfiguration;