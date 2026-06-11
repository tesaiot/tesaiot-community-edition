/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef, Suspense, lazy } from 'react';
import { useSearchParams } from 'react-router-dom';
import { DeviceDialog } from './components/DeviceDialog';
import { DeviceTable } from './components/table/DeviceTable';
import { DeviceDetailsDialog } from './components/dialogs/DeviceDetailsDialog';
import { QRCodeDialog } from './components/dialogs/QRCodeDialog';
import { ProvisioningTab } from './components/ProvisioningTab';
import { organizationService } from '../organizations/services/organizationService';
import { SmartTelemetryDashboard } from './components/SmartTelemetryDashboard';
import { SmartTelemetryDashboardBeta } from './components/SmartTelemetryDashboardBeta';
import { getFeatureFlags } from '@/config/features.config';
import { PerformanceMonitor } from '@/components/PerformanceMonitor';
import { RefreshRateSettings } from '@/components/RefreshRateSettings';
import { AutoRefreshStatusBar } from '@/components/AutoRefreshIndicators';
// AI Assistant and Edge AI Telemetry dashboard are out of scope for the Community Edition.
import { useAuth } from '@/hooks/useAuth';
import { useServiceConfiguration } from '@/features/platform-admin/hooks/useServiceConfiguration';
/**
 * COMPLETE DEVICE MANAGEMENT WITH VAULT PKI INTEGRATION - v2.4.0-beta.20250106
 * Professional Modular Implementation
 * - Uses modular components for better maintainability
 * - DeviceDialog component for Add/Edit operations
 * ✅ THREE-DOT MENU: View Details, Edit Device, QR Code, Certificate Downloads
 * ✅ Download CA Chain, Certificate, Private Key, Bundle (ZIP) from VAULT ONLY
 * ✅ QR CODE DOWNLOAD FUNCTIONALITY 
 * ✅ COMPREHENSIVE ADD DEVICE FORM with tabs and advanced settings 
 * ✅ RICH VIEW DETAILS DIALOG with 4 tabs (Overview, Telemetry, Security, Logs)
 * ✅ COMPREHENSIVE EDIT DEVICE DIALOG with 3 tabs and device actions
 * ✅ BULK OPERATIONS with device selection
 * ✅ EXPORT FUNCTIONALITY and filtering
 * ✅ TOAST SYSTEM FIXED - NO MORE React #31 ERRORS
 * ✅ ALL DIALOGS WORKING (Add Device, Edit Device, View Details, QR Code)
 * ✅ REAL API DEVICE LOADING - No more mock device IDs causing 404s
 * ✅ VAULT PKI CERTIFICATE GENERATION - Real certificates from Vault
 * ✅ ORGANIZATION NAME MAPPING - Displays correct organization names
 * Build: 2025-01-06 Enhanced with DeviceCreationWithCertificate
 * Status: STABLE - ENHANCED WITH COMPREHENSIVE ADD DEVICE DIALOG
 * Last Fix: Fixed organization name display for BDH Corporation devices
 */
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
// Dialog components removed - using extracted dialog components
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
// Table components removed - using extracted DeviceTable component
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Server,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  MoreVertical,
  Edit,
  Trash2,
  Key,
  Shield,
  Wifi,
  WifiOff,
  Activity,
  Package,
  AlertTriangle,
  CheckCircle,
  Sparkles,
  Clock,
  Zap,
  Settings,
  RefreshCw,
  Copy,
  QrCode,
  Terminal,
  Smartphone,
  Router,
  Cpu,
  Info,
  MapPin,
  Calendar,
  BarChart3,
  Play,
  CheckCircle2,
  X
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { LicenseService } from '@/services/license/LicenseService';
import authFetch from '@/utils/auth-fetch';
import { 
  LineChart, 
  Line, 
  BarChart, 
  Bar, 
  AreaChart,
  Area,
  PieChart,
  Pie,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts';
import QRCode from 'qrcode'; // QR code functionality for device provisioning
import { CertificateGenerationDialog } from './components/CertificateGenerationDialog';
import { CertificateRenewalDialog } from '@/features/certificates/components/CertificateRenewalDialog';
import { Device, DeviceGroup, FirmwareUpdate } from './types/device.types';
import { DEVICE_STATUS_COLORS, DEVICE_TYPE_COLORS, DEFAULT_NEW_DEVICE, TOAST_MESSAGES, DEVICE_API_ENDPOINTS, TELEMETRY_CHART_DATA } from './constants/device.constants';
import { createFetchRealTelemetryData, generateFallbackData, getSmartChartDomain, generateSignalData, getStatusColor, getDeviceIcon } from './utils/deviceUtils';
import { deviceService } from './services/deviceService';
import { DeviceFilterForm } from './components/forms/DeviceFilterForm';
import { useDeviceData } from './hooks/useDeviceData';
import { useDeviceFilters } from './hooks/useDeviceFilters';
import { useDeviceState } from './hooks/useDeviceState';
import { useDeviceHandlers } from './hooks/useDeviceHandlers';
import { DeviceStatsCards } from './components/cards/DeviceStatsCards';
import { Container } from '@/components/common/container';

export default function CompleteDeviceManagement() {
  const { user: currentUser } = useAuth();
  const isPlatformAdmin = currentUser?.role === 'platform_admin';
  const organizationId = currentUser?.organization_id || currentUser?.organization || 'default';
  const { config: serviceConfig } = useServiceConfiguration(organizationId);
  const [searchParams, setSearchParams] = useSearchParams();
  const deviceParam = searchParams.get('device');
  const certTabParam = searchParams.get('certTab');
  const handledCertificateRedirect = useRef<string | null>(null);
  
  // Tab management with URL parameter support
  const [activeTab, setActiveTab] = useState(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'provisioning') return 'provisioning';
    return 'devices';
  });

  // Update URL when tab changes
  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    const newSearchParams = new URLSearchParams(searchParams);
    if (tab === 'provisioning') {
      newSearchParams.set('tab', 'provisioning');
    } else {
      newSearchParams.delete('tab');
    }
    setSearchParams(newSearchParams);
  };
  
  // Using toast from sonner import above
  const licenseService = LicenseService.getInstance();
  const isCommercial = licenseService.isCommercialEdition();
  
  // Using custom hooks for state management
  const { devices, setDevices, organizationMap, loading, reloadDevices } = useDeviceData();
  
  // ✅ EXTRACTED: Device filtering to useDeviceFilters hook
  const {
    searchTerm,
    setSearchTerm,
    filterType,
    setFilterType,
    filterStatus,
    setFilterStatus,
    filterOrg,
    setFilterOrg,
    filteredDevices
  } = useDeviceFilters(devices);
  
  // ✅ EXTRACTED: Device state management to useDeviceState hook
  const {
    // Dialog visibility states
    selectedDevices,
    setSelectedDevices,
    showAddDialog,
    setShowAddDialog,
    showEditDialog,
    setShowEditDialog,
    showDetailsDialog,
    setShowDetailsDialog,
    showBulkDialog,
    setShowBulkDialog,
    showQRDialog,
    setShowQRDialog,
    showTelemetryDashboard,
    setShowTelemetryDashboard,
    showAIAssistant,
    setShowAIAssistant,
    showCertificateDialog,
    setShowCertificateDialog,
    
    // Selected device and UI states
    selectedDevice,
    setSelectedDevice,
    qrCodeData,
    setQrCodeData,
    activeDetailTab,
    setActiveDetailTab,
    
    // Telemetry states
    realTelemetryData,
    setRealTelemetryData,
    telemetryLoading,
    setTelemetryLoading,
    
    // Form states
    newDevice,
    setNewDevice,
    editDevice,
    setEditDevice,
    
    // Enhanced dialog states
    currentAddTab,
    setCurrentAddTab,
    isCreating,
    setIsCreating,
    creationStep,
    setCreationStep,
    certificateDetails,
    setCertificateDetails,
    certificateBundle,
    setCertificateBundle,
    createdDeviceId,
    setCreatedDeviceId,
    creationSteps,
    setCreationSteps,
    
    // Helper functions
    resetNewDevice,
    populateEditDevice,
    // beta telemetry
    showTelemetryDashboardBeta,
    setShowTelemetryDashboardBeta,
    // Edge AI telemetry
    showEdgeAITelemetry,
    setShowEdgeAITelemetry
  } = useDeviceState(currentUser?.organizationId);
  
  // ✅ EXTRACTED: loading state moved to useDeviceData hook
  const [setLoading] = useState<any>(() => () => {}); // Temporary for backward compatibility
  
  // Certificate renewal state
  const [showRenewalDialog, setShowRenewalDialog] = useState(false);
  const [selectedCertificateDevice, setSelectedCertificateDevice] = useState<Device | null>(null);

  // Create telemetry fetch function
  const fetchRealTelemetryData = createFetchRealTelemetryData(setRealTelemetryData, setTelemetryLoading);
  
  // ✅ EXTRACTED: Device handlers to useDeviceHandlers hook
  const {
    handleAddDeviceOriginal,
    handleEnhancedAddDevice,
    handleDeleteDevice,
    handleBulkAction,
    downloadCertificateFile,
    generateQRCode,
    exportDevices
  } = useDeviceHandlers({
    devices,
    setDevices,
    filteredDevices,
    selectedDevices,
    setSelectedDevices,
    reloadDevices,
    setLoading,
    setShowBulkDialog,
    setQrCodeData,
    setSelectedDevice,
    setShowQRDialog,
    newDevice,
    resetNewDevice,
    setShowAddDialog,
    currentUser,
    setCreationSteps,
    setIsCreating,
    setCurrentAddTab,
    setCreationStep,
    setCreatedDeviceId,
    setCertificateDetails,
  setCertificateBundle
  });
 
  // Default tab for Certificate dialog: 'overview' for Manage, 'lifecycle' for Renew
  const [certificateDialogDefaultTab, setCertificateDialogDefaultTab] = useState<'overview' | 'lifecycle'>('overview');
  
  // Certificate renewal handlers
  const handleRenewCertificate = (device: Device) => {
    // Server-TLS devices don't need certificate renewal
    if (device.auth_mode === 'server_tls') {
      toast.info('Server-TLS devices do not require client certificates');
      return;
    }
    console.log('Device selected for certificate renewal:', device);
    setSelectedDevice(device);
    // Open the unified Enterprise Certificate dialog on Lifecycle tab (Auto | CSR)
    setCertificateDialogDefaultTab('lifecycle');
    setShowCertificateDialog(true);
    // Optional: close legacy renewal dialog if it was open
    setShowRenewalDialog(false);
  };

  useEffect(() => {
    if (!deviceParam || devices.length === 0) {
      return;
    }

    const redirectKey = `${deviceParam}:${certTabParam ?? ''}`;
    if (handledCertificateRedirect.current === redirectKey) {
      return;
    }

    const matchedDevice = devices.find((device) => {
      const primaryId = (device as any).device_id || device.id || (device as any)._id || (device as any).uuid;
      return primaryId === deviceParam;
    });

    if (!matchedDevice) {
      return;
    }

    handledCertificateRedirect.current = redirectKey;
    setSelectedDevice(matchedDevice);

    const authMode = String((matchedDevice as any).auth_mode || (matchedDevice as any).authentication_mode || '').toLowerCase();
    const dialogTab = certTabParam === 'lifecycle' ? 'lifecycle' : 'overview';

    if (authMode === 'server_tls') {
      setShowCertificateDialog(false);
      setActiveDetailTab('credentials');
      setShowDetailsDialog(true);
    } else {
      setCertificateDialogDefaultTab(dialogTab);
      setShowDetailsDialog(false);
      setShowCertificateDialog(true);
    }

    const newParams = new URLSearchParams(searchParams);
    newParams.delete('device');
    newParams.delete('certTab');
    setSearchParams(newParams, { replace: true });
  }, [deviceParam, certTabParam, devices, searchParams, setActiveDetailTab, setSearchParams, setSelectedDevice, setShowCertificateDialog, setShowDetailsDialog, setCertificateDialogDefaultTab]);

  useEffect(() => {
    if (!deviceParam) {
      handledCertificateRedirect.current = null;
    }
  }, [deviceParam]);

  const handleRenewalComplete = (certificate: any, newCertificate: any) => {
    toast.success(`Certificate for ${selectedCertificateDevice?.name} has been renewed successfully`);
    setShowRenewalDialog(false);
    setSelectedCertificateDevice(null);
    // Reload devices to get updated certificate info
    reloadDevices();
  };

  // ✅ EXTRACTED: loadOrganizations moved to useDeviceData hook
  
  // Fetch telemetry when a device is selected for details
  useEffect(() => {
    if (selectedDevice && showDetailsDialog) {
      console.log('Selected device for telemetry:', selectedDevice);
      console.log('Using device_id:', (selectedDevice as any).device_id);
      fetchRealTelemetryData((selectedDevice as any).device_id || selectedDevice.id);
      
      // Set up auto-refresh for real-time data
      const interval = setInterval(() => {
        fetchRealTelemetryData((selectedDevice as any).device_id || selectedDevice.id);
      }, 30000); // Refresh every 30 seconds
      
      return () => clearInterval(interval);
    }
  }, [selectedDevice, showDetailsDialog]);

  // ✅ EXTRACTED: Device loading moved to useDeviceData hook
  
  // ✅ EXTRACTED: Device filtering logic moved to useDeviceFilters hook
  // filteredDevices is now provided by the hook

  // Platform admins cannot access device management
  if (isPlatformAdmin) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Access Restricted
            </CardTitle>
            <CardDescription>
              Platform Administrator Access
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="space-y-2">
                <p>
                  As a platform administrator, you have access to infrastructure management only.
                  Device management is restricted to organization administrators.
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  Platform administrators can manage:
                </p>
                <ul className="list-disc list-inside text-sm text-muted-foreground ml-4">
                  <li>System infrastructure and monitoring</li>
                  <li>Platform-wide settings and configuration</li>
                  <li>Service health and performance metrics</li>
                </ul>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <Container>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Device Management</h1>
          <p className="text-muted-foreground">
            Monitor and manage all IoT devices with provisioning capabilities
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isCommercial && (
            <>
              <Button variant="outline" onClick={exportDevices}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button variant="outline">
                <Upload className="mr-2 h-4 w-4" />
                Import
              </Button>
            </>
          )}
          {/* Legacy real-time telemetry dashboard is temporarily hidden while the new experience is validated.
              Keep the button code for potential rollback. */}
          {/*
          <Button
            variant="outline"
            onClick={() => setShowTelemetryDashboard(true)}
            className="bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:from-blue-600 hover:to-purple-600"
          >
            <Activity className="mr-2 h-4 w-4" />
            Real-time Telemetry
          </Button>
          */}
          {/* Real-time Telemetry button - Disabled in favor of Edge AI Telemetry Dashboard (v2025.12-rc.6) */}
          {/* {getFeatureFlags().SHOW_PREVIEW_FEATURES && (
            <Button
              variant="outline"
              onClick={() => setShowTelemetryDashboardBeta(true)}
              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600"
            >
              <Activity className="mr-2 h-4 w-4" />
              Real-time Telemetry
            </Button>
          )} */}
          {/* Edge AI Telemetry Dashboard removed in the Community Edition (out of scope: AI inference). */}
          {/* Device Data Dashboard Button - temporarily disabled (incomplete implementation) */}
          {/* {serviceConfig?.features?.device_data_dashboard !== false && (
            <Button
              variant="outline"
              onClick={() => window.location.href = '/device-data-dashboard'}
              className="bg-gradient-to-r from-indigo-500 to-cyan-500 text-white hover:from-indigo-600 hover:to-cyan-600"
            >
              <BarChart3 className="mr-2 h-4 w-4" />
              Device Data Dashboard
            </Button>
          )} */}
          {/* AI Assistant Button - temporarily disabled (incomplete implementation) */}
          {/* {serviceConfig?.features?.ai_assistant !== false && (
            <Button
              variant="outline"
              onClick={() => setShowAIAssistant(true)}
              className="bg-gradient-to-r from-green-500 to-emerald-500 text-white hover:from-green-600 hover:to-emerald-600"
            >
              <Sparkles className="mr-2 h-4 w-4" />
              AI Assistant
            </Button>
          )} */}
          <Button onClick={() => setShowAddDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Device
          </Button>
        </div>
      </div>

      {/* Stats */}
      {/* ✅ EXTRACTED: DeviceStatsCards component */}
      <DeviceStatsCards devices={devices} />

      {/* Main Content with Tabs */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="devices" className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            Devices
          </TabsTrigger>
          <TabsTrigger value="provisioning" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Provisioning
          </TabsTrigger>
        </TabsList>

        <TabsContent value="devices" className="mt-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>All Devices</CardTitle>
                  <CardDescription>
                    Manage and monitor your IoT device fleet
                  </CardDescription>
                </div>
            {selectedDevices.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  {selectedDevices.length} selected
                </span>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleBulkAction('restart')}
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Restart
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleBulkAction('update')}
                >
                  <Package className="mr-2 h-4 w-4" />
                  Update
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  className="text-red-600"
                  onClick={() => handleBulkAction('delete')}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          {/* ✅ EXTRACTED: DeviceFilterForm component */}
          <DeviceFilterForm
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            filterType={filterType}
            onFilterTypeChange={setFilterType}
            filterStatus={filterStatus}
            onFilterStatusChange={setFilterStatus}
            filterOrg={filterOrg}
            onFilterOrgChange={setFilterOrg}
            showOrgFilter={currentUser?.role === 'super_admin'}
          />

          {/* Devices Table */}
          {/* ✅ EXTRACTED: Device table moved to DeviceTable component */}
  <DeviceTable
            devices={filteredDevices}
            selectedDevices={selectedDevices}
            onSelectionChange={setSelectedDevices}
            onViewDetails={(device) => {
              console.log('Device selected for details:', device);
              console.log('Device has device_id:', (device as any).device_id);
              setSelectedDevice(device);
              setShowDetailsDialog(true);
            }}
            onEdit={(device) => {
              console.log('DeviceManagement: Edit device selected:', device);
              setSelectedDevice(device);
              setShowEditDialog(true);
            }}
            onDelete={handleDeleteDevice}
            onGenerateQRCode={generateQRCode}
            onManageCertificates={(device) => {
              // Behavior tweak: For Server‑TLS devices, open Device Details at Credentials → CA Certificate
              const authMode = (device as any).auth_mode || (device as any).authentication_mode || '';
              setSelectedDevice(device);
              if (authMode === 'server_tls') {
                setActiveDetailTab('credentials');
                setShowDetailsDialog(true);
              } else {
                // mTLS devices keep the existing certificate management dialog
                setCertificateDialogDefaultTab('overview');
                setShowCertificateDialog(true);
              }
            }}
            onRenewCertificate={handleRenewCertificate}
          />
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="provisioning" className="mt-6">
          <ProvisioningTab onDevicesImported={reloadDevices} />
        </TabsContent>
      </Tabs>

      {/* Enhanced Add Device Dialog using modular component */}
      <DeviceDialog 
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        mode="create"
        enhancedMode={true}
        onSuccess={() => {
          reloadDevices();
          toast.success('Device created successfully!');
        }}
      />

      {/* QR Code Dialog */}
      <QRCodeDialog
        device={selectedDevice}
        open={showQRDialog}
        onOpenChange={setShowQRDialog}
        qrCodeData={qrCodeData}
      />

      {/* Edit Device Dialog - Enhanced with Data Schema Tab */}
      <DeviceDialog 
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        mode="edit"
        enhancedMode={true}
        device={selectedDevice}
        onSave={async (updatedDevice) => {
          setLoading(true);
          try {
            // Log the selected device and its ID
            console.log('DeviceManagement: Updating device:', selectedDevice);
            console.log('Device ID to update:', selectedDevice?.device_id || selectedDevice?.id);
            console.log('Update payload:', updatedDevice);
            
            // Ensure name is preserved in the update payload
            if (!updatedDevice.name && selectedDevice?.name) {
              updatedDevice.name = selectedDevice.name;
            }
            
            // Use device service for update
            const updatedDeviceData = await deviceService.updateDevice(
              selectedDevice?.device_id || selectedDevice?.id || '',
              updatedDevice
            );
            
            // If the API returns the updated device, update it in the local state immediately
            if (updatedDeviceData && updatedDeviceData.device_id) {
              setDevices(prevDevices => 
                prevDevices.map(dev => 
                  (dev.device_id === updatedDeviceData.device_id || dev.id === updatedDeviceData._id) 
                    ? { ...dev, ...updatedDeviceData, name: updatedDeviceData.name || dev.name }
                    : dev
                )
              );
            }
            
            // Reload devices to ensure consistency
            await reloadDevices();
            // Success is now handled in the dialog itself
            // Don't close the dialog here
          } catch (error) {
            console.error('Error updating device:', error);
            toast.error('Failed to update device');
            throw error; // Re-throw to let dialog handle the error state
          } finally {
            setLoading(false);
          }
        }}
      />

      {/* Legacy Smart Telemetry Dashboard (hidden, retained for rollback) */}
      {false && showTelemetryDashboard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Smart Telemetry Dashboard</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowTelemetryDashboard(false)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <SmartTelemetryDashboard
                devices={devices}
                className="w-full"
                isTabActive={showTelemetryDashboard}
                showTitle={false}
              />
            </div>
          </div>
        </div>
      )}

      {/* Smart Telemetry Dashboard (new default) */}
      {showTelemetryDashboardBeta && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg shadow-xl max-w-7xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold">Smart Telemetry Dashboard</h2>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowTelemetryDashboardBeta(false)}
                  className="h-8 w-8 p-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <SmartTelemetryDashboardBeta
                devices={devices}
                className="w-full"
                isTabActive={showTelemetryDashboardBeta}
                showTitle={false}
              />
            </div>
          </div>
        </div>
      )}

      {/* Edge AI Telemetry Dashboard removed in the Community Edition (out of scope). */}

      {/* AI Assistant Dialog - temporarily disabled (incomplete implementation) */}
      {/* {showAIAssistant && (
        <AIAssistant
          devices={devices}
          onClose={() => setShowAIAssistant(false)}
        />
      )} */}

      {/* Device Details Dialog */}
      <DeviceDetailsDialog
        device={selectedDevice}
        open={showDetailsDialog}
        onOpenChange={setShowDetailsDialog}
        credentialsDefaultTab={(selectedDevice as any)?.auth_mode === 'server_tls' ? 'certificates' : undefined}
        activeTab={activeDetailTab}
        onTabChange={setActiveDetailTab}
        realTelemetryData={realTelemetryData}
        telemetryLoading={telemetryLoading}
        onRefreshTelemetry={() => selectedDevice && fetchRealTelemetryData((selectedDevice as any).device_id || selectedDevice.id)}
        onRenewCertificate={handleRenewCertificate}
      />

      {/* Certificate Management Dialog */}
      <CertificateGenerationDialog
        isOpen={showCertificateDialog}
        onClose={() => setShowCertificateDialog(false)}
        device={selectedDevice}
        defaultTab={certificateDialogDefaultTab}
        onSuccess={() => {
          reloadDevices();
          toast.success('Certificate generated successfully!');
          setShowCertificateDialog(false);
        }}
      />

      {/* Certificate Renewal Dialog */}
      <CertificateRenewalDialog
        open={showRenewalDialog}
        onOpenChange={setShowRenewalDialog}
        certificate={selectedCertificateDevice ? {
          id: selectedCertificateDevice.id,
          deviceId: (selectedCertificateDevice as any).device_id || selectedCertificateDevice.id,
          deviceName: selectedCertificateDevice.name,
          deviceType: selectedCertificateDevice.type,
          status: selectedCertificateDevice.certificate?.status === 'revoked' ? 'revoked' :
                  selectedCertificateDevice.certificate_info?.status === 'revoked' ? 'revoked' :
                  (selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at) ? 
                    (new Date(selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at) < new Date() ? 'expired' :
                     (Math.floor((new Date(selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)) <= 30 ? 'expiring' : 'active'))
                    : 'expired',
          issuedAt: selectedCertificateDevice.certificate?.issuedAt || selectedCertificateDevice.certificate?.issued_at || selectedCertificateDevice.certificate_info?.issued_at || selectedCertificateDevice.certificate_issued_at || '',
          expiresAt: selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at || '',
          daysUntilExpiry: (selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at) ? 
            Math.floor((new Date(selectedCertificateDevice.certificate?.expiresAt || selectedCertificateDevice.certificate?.expires_at || selectedCertificateDevice.certificate_info?.expires_at || selectedCertificateDevice.certificate_expires_at).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24)) : 0,
          serialNumber: selectedCertificateDevice.certificate?.serialNumber || selectedCertificateDevice.certificate?.serial_number || selectedCertificateDevice.certificate_info?.serial || selectedCertificateDevice.certificate_serial || '',
          algorithm: selectedCertificateDevice.certificate?.algorithm || 'RSA-2048',
          organization: selectedCertificateDevice.organizationName
        } : null}
        onRenewalComplete={handleRenewalComplete}
      />
      </div>
    </Container>
  );
}
