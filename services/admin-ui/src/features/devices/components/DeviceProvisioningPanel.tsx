/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import {
  Wifi,
  Shield,
  Key,
  QrCode,
  Upload,
  Settings,
  Activity,
  AlertCircle,
  Info,
  Zap,
  Lock,
  CheckCircle2,
  Clock,
  Loader2,
  WifiOff,
  Download
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useProvisioningWebSocket } from '@/hooks/useProvisioningWebSocket';

interface DeviceProvisioningPanelProps {
  className?: string;
}

interface ProvisioningMethod {
  id: string;
  name: string;
  icon: React.FC<{ className?: string }>;
  description: string;
  status: string;
  badge: string;
}

interface ZeroTouchConfig {
  template_id?: string;
  discovery_method: 'dhcp' | 'mdns' | 'scan';
  network_range: string;
  device_filters?: {
    manufacturer?: string;
    model?: string;
    mac_prefixes?: string[];
  };
  auto_provision: boolean;
  require_approval: boolean;
}

interface BulkImportData {
  devices: Array<{
    device_id: string;
    name: string;
    type: string;
    organization_id?: string;
    location?: string;
    tags?: string[];
    metadata?: Record<string, any>;
  }>;
  template_id?: string;
  auto_activate: boolean;
  generate_certificates: boolean;
}

export const DeviceProvisioningPanel: React.FC<DeviceProvisioningPanelProps> = ({ className }) => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('overview');
  const [isLoading, setIsLoading] = useState<Record<string, boolean>>({});
  const [dialogOpen, setDialogOpen] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Zero-touch provisioning state
  const [zeroTouchConfig, setZeroTouchConfig] = useState<ZeroTouchConfig>({
    discovery_method: 'dhcp',
    network_range: '192.168.1.0/24',
    auto_provision: true,
    require_approval: false
  });
  
  // QR Code state
  const [qrCodeData, setQrCodeData] = useState<{
    qr_code?: string;
    provisioning_url?: string;
    expires_at?: string;
  }>({});
  
  // Manual provisioning state
  const [manualDevice, setManualDevice] = useState({
    device_id: '',
    name: '',
    type: 'sensor',
    location: '',
    tags: ''
  });
  
  // Check if user has access to provisioning features
  const hasProvisioningAccess = user?.role !== 'platform_admin';
  const isOrgAdmin = user?.role === 'organization_admin' || user?.role === 'super_admin';
  
  // WebSocket connection for real-time updates
  const wsUrl = process.env.NODE_ENV === 'development' 
    ? 'ws://localhost:8000/ws/provisioning'
    : `wss://${window.location.host}/ws/provisioning`;
    
  const {
    isConnected,
    error: wsError,
    latestProgress,
    latestDiscovery,
    latestNotification,
    progressHistory,
    discoveryHistory,
    notificationHistory,
    reconnect
  } = useProvisioningWebSocket(wsUrl);
  
  // Handle WebSocket notifications
  useEffect(() => {
    if (latestNotification) {
      toast({
        title: latestNotification.title,
        description: latestNotification.message,
        variant: latestNotification.priority === 'high' ? 'destructive' : 'default',
      });
    }
  }, [latestNotification, toast]);
  
  // Show WebSocket error toast
  useEffect(() => {
    if (wsError) {
      toast({
        title: 'Connection Error',
        description: 'Lost connection to real-time updates. Attempting to reconnect...',
        variant: 'destructive',
      });
    }
  }, [wsError, toast]);

  const provisioningMethods: ProvisioningMethod[] = [
    {
      id: 'zero-touch',
      name: 'Zero-Touch Provisioning',
      icon: Wifi,
      description: 'Automated device discovery and secure enrollment',
      status: 'available',
      badge: 'Recommended'
    },
    {
      id: 'qr-code',
      name: 'QR Code Provisioning',
      icon: QrCode,
      description: 'Quick setup using secure QR codes',
      status: 'available',
      badge: 'Quick Setup'
    },
    {
      id: 'bulk-import',
      name: 'Bulk Import',
      icon: Upload,
      description: 'Import multiple devices via CSV',
      status: 'available',
      badge: 'Enterprise'
    },
    {
      id: 'manual',
      name: 'Manual Provisioning',
      icon: Settings,
      description: 'Traditional step-by-step device setup',
      status: 'available',
      badge: 'Standard'
    }
  ];
  
  // Handler functions for provisioning methods
  const handleZeroTouchProvisioning = async () => {
    setIsLoading({ ...isLoading, 'zero-touch': true });
    try {
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('/api/v1/devices/provision/zero-touch', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(zeroTouchConfig)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start zero-touch provisioning');
      }
      
      const data = await response.json();
      toast({
        title: 'Zero-Touch Provisioning Started',
        description: `Session ID: ${data.session_id}. Discovery method: ${data.discovery_method}`,
      });
      setDialogOpen({ ...dialogOpen, 'zero-touch': false });
      // Switch to status tab to monitor progress
      setActiveTab('status');
    } catch (error: any) {
      toast({
        title: 'Provisioning Failed',
        description: error.message || 'Failed to start zero-touch provisioning',
        variant: 'destructive',
      });
    } finally {
      setIsLoading({ ...isLoading, 'zero-touch': false });
    }
  };
  
  const handleQrCodeGeneration = async () => {
    setIsLoading({ ...isLoading, 'qr-code': true });
    try {
      const token = localStorage.getItem('jwt_token');
      // For now, we'll generate a QR code client-side since the endpoint doesn't exist yet
      // In production, this would call: POST /api/v1/provisioning/qr-code/generate
      const provisioningData = {
        device_type: 'iot-device',
        organization_id: user?.organizationId,
        provisioning_method: 'qr-code',
        timestamp: new Date().toISOString(),
        expires_at: new Date(Date.now() + 3600000).toISOString()
      };
      
      // Create a provisioning URL with encoded data
      const provisioningUrl = `https://${window.location.host}/provision?data=${btoa(JSON.stringify(provisioningData))}`;
      
      // Generate QR code using a placeholder (in production, use a QR library)
      const qrData = {
        qr_code: `data:image/svg+xml;base64,${btoa(`
          <svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
            <rect width="200" height="200" fill="white"/>
            <text x="100" y="100" text-anchor="middle" font-family="monospace" font-size="10">
              QR Code Placeholder
            </text>
            <text x="100" y="120" text-anchor="middle" font-family="monospace" font-size="8">
              ${provisioningData.device_type}
            </text>
          </svg>
        `)}`,
        provisioning_url: provisioningUrl,
        expires_at: provisioningData.expires_at
      };
      
      setQrCodeData(qrData);
      toast({
        title: 'QR Code Generated',
        description: 'QR code has been generated successfully. Valid for 1 hour.',
      });
    } catch (error: any) {
      toast({
        title: 'QR Code Generation Failed',
        description: error.message || 'Failed to generate QR code',
        variant: 'destructive',
      });
    } finally {
      setIsLoading({ ...isLoading, 'qr-code': false });
    }
  };
  
  const handleBulkImport = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsLoading({ ...isLoading, 'bulk-import': true });
    
    try {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        throw new Error('File size exceeds 10MB limit');
      }
      
      // Parse CSV file
      const text = await file.text();
      const lines = text.split('\n').filter(line => line.trim());
      
      if (lines.length < 2) {
        throw new Error('CSV file must contain headers and at least one device');
      }
      
      // Parse headers
      const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
      
      // Validate required headers
      const requiredHeaders = ['device_id', 'name', 'type'];
      const missingHeaders = requiredHeaders.filter(h => !headers.includes(h));
      if (missingHeaders.length > 0) {
        throw new Error(`Missing required headers: ${missingHeaders.join(', ')}`);
      }
      
      // Parse devices with better CSV handling
      const devices = [];
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        
        // Simple CSV parsing (handles basic quoted values)
        const values = [];
        let current = '';
        let inQuotes = false;
        
        for (let j = 0; j < line.length; j++) {
          const char = line[j];
          if (char === '"') {
            inQuotes = !inQuotes;
          } else if (char === ',' && !inQuotes) {
            values.push(current.trim());
            current = '';
          } else {
            current += char;
          }
        }
        values.push(current.trim());
        
        // Create device object
        const device: any = {};
        headers.forEach((header, index) => {
          const value = values[index] || '';
          if (header === 'tags' && value) {
            // Parse tags as array
            device[header] = value.split(';').map(t => t.trim()).filter(t => t);
          } else {
            device[header] = value;
          }
        });
        
        // Validate device data
        if (!device.device_id || !device.name || !device.type) {
          toast({
            title: 'Warning',
            description: `Skipping row ${i + 1}: Missing required fields`,
            variant: 'destructive',
          });
          continue;
        }
        
        devices.push(device);
      }
      
      if (devices.length === 0) {
        throw new Error('No valid devices found in CSV file');
      }
      
      const bulkData: BulkImportData = {
        devices,
        auto_activate: true,
        generate_certificates: true
      };
      
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('/api/v1/devices/bulk-import', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(bulkData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to import devices');
      }
      
      const data = await response.json();
      toast({
        title: 'Bulk Import Started',
        description: `Importing ${data.total_devices} devices. Session ID: ${data.session_id}`,
      });
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
      // Switch to status tab to monitor progress
      setActiveTab('status');
    } catch (error: any) {
      toast({
        title: 'Bulk Import Failed',
        description: error.response?.data?.error || 'Failed to import devices',
        variant: 'destructive',
      });
    } finally {
      setIsLoading({ ...isLoading, 'bulk-import': false });
    }
  };
  
  const handleManualProvisioning = async () => {
    setIsLoading({ ...isLoading, 'manual': true });
    try {
      const deviceData = {
        ...manualDevice,
        tags: manualDevice.tags ? manualDevice.tags.split(',').map(t => t.trim()) : [],
        metadata: {
          provisioning_method: 'manual',
          provisioned_by: user?.email
        }
      };
      
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('/api/v1/devices/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(deviceData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create device');
      }
      
      const data = await response.json();
      toast({
        title: 'Device Created Successfully',
        description: `Device ${data.device_id} has been provisioned`,
      });
      
      // Reset form
      setManualDevice({
        device_id: '',
        name: '',
        type: 'sensor',
        location: '',
        tags: ''
      });
      setDialogOpen({ ...dialogOpen, 'manual': false });
    } catch (error: any) {
      toast({
        title: 'Device Provisioning Failed',
        description: error.response?.data?.error || 'Failed to create device',
        variant: 'destructive',
      });
    } finally {
      setIsLoading({ ...isLoading, 'manual': false });
    }
  };
  
  const openProvisioningDialog = (methodId: string) => {
    setDialogOpen({ ...dialogOpen, [methodId]: true });
  };

  const securityFeatures = [
    'Hardware Security Module (HSM) integration',
    'Mutual TLS authentication',
    'Certificate-based device identity',
    'Secure key exchange protocols',
    'Device attestation verification',
    'Zero-knowledge provisioning'
  ];

  return (
    <div className={className}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Device Provisioning</h2>
            <p className="text-muted-foreground">
              Secure device onboarding and lifecycle management
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <Shield className="h-3 w-3" />
              Enterprise Security
            </Badge>
            <Badge variant="outline" className="gap-1">
              <Lock className="h-3 w-3" />
              ETSI EN 303 645
            </Badge>
            <Badge 
              variant={isConnected ? "default" : "destructive"} 
              className="gap-1"
            >
              {isConnected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
              {isConnected ? 'Live Updates' : 'Disconnected'}
            </Badge>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <Info className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="methods" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Methods
            </TabsTrigger>
            <TabsTrigger value="security" className="flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Security
            </TabsTrigger>
            <TabsTrigger value="status" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Status
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Wifi className="h-5 w-5" />
                    Provisioning Overview
                  </CardTitle>
                  <CardDescription>
                    Streamlined device onboarding with enterprise-grade security
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <h4 className="font-semibold">Key Features</h4>
                      <ul className="space-y-2 text-sm">
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Automated device discovery
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Secure certificate generation
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Zero-touch deployment
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Bulk device management
                        </li>
                      </ul>
                    </div>
                    <div className="space-y-3">
                      <h4 className="font-semibold">Supported Devices</h4>
                      <ul className="space-y-2 text-sm">
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Infineon PSOC™ 6, PSoC™ 6 AI, PSoC™ Edge, AURIX™
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Arduino modules
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          ESP32/ESP8266 modules
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Microchip/STM32/Nordic modules
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Raspberry Pi devices
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          RISC-V-based IoT modules
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          FPGA-based IoT modules
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Industrial IoT gateways
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Custom embedded devices
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="methods" className="mt-6">
            <div className="grid gap-4">
              {provisioningMethods.map((method) => (
                <Card key={method.id} className="relative">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <method.icon className="h-6 w-6" />
                        <div>
                          <CardTitle className="text-lg">{method.name}</CardTitle>
                          <CardDescription>{method.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{method.badge}</Badge>
                        <Badge variant="outline" className="text-green-600">
                          {method.status}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex justify-end">
                      <Button 
                        variant="outline" 
                        onClick={() => openProvisioningDialog(method.id)}
                        disabled={isLoading[method.id]}
                      >
                        {isLoading[method.id] ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Configuring...
                          </>
                        ) : (
                          'Configure'
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="security" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Security Features
                </CardTitle>
                <CardDescription>
                  Enterprise-grade security for device provisioning
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4">
                  <div className="space-y-3">
                    <h4 className="font-semibold">Security Capabilities</h4>
                    <ul className="space-y-2">
                      {securityFeatures.map((feature, index) => (
                        <li key={index} className="flex items-center gap-2 text-sm">
                          <Key className="h-4 w-4 text-blue-500" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  <div className="border-t pt-4">
                    <h4 className="font-semibold mb-3">Compliance Standards</h4>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">ETSI EN 303 645</Badge>
                      <Badge variant="outline">ISO/IEC 27001</Badge>
                      <Badge variant="outline">NIST Cybersecurity Framework</Badge>
                      <Badge variant="outline">IEC 62443</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="status" className="mt-6">
            <div className="space-y-6">
              {/* Current Status */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Provisioning Status
                    {!isConnected && (
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={reconnect}
                        className="ml-auto"
                      >
                        <Loader2 className="h-4 w-4 mr-2" />
                        Reconnect
                      </Button>
                    )}
                  </CardTitle>
                  <CardDescription>
                    Current provisioning activity and real-time statistics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {latestProgress?.status === 'processing' ? 1 : 0}
                      </div>
                      <div className="text-sm text-muted-foreground">Active Provisioning</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {discoveryHistory.length}
                      </div>
                      <div className="text-sm text-muted-foreground">Discovered Devices</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {latestProgress?.failed || 0}
                      </div>
                      <div className="text-sm text-muted-foreground">Failed Attempts</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Current Progress */}
              {latestProgress && latestProgress.status === 'processing' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Bulk Import Progress
                    </CardTitle>
                    <CardDescription>
                      Session: {latestProgress.session_id}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Overall Progress</span>
                          <span>{latestProgress.progress}%</span>
                        </div>
                        <Progress value={latestProgress.progress} className="h-3" />
                      </div>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="text-center">
                          <div className="text-lg font-semibold text-blue-600">
                            {latestProgress.current_device}
                          </div>
                          <div className="text-muted-foreground">Current Device</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold text-green-600">
                            {latestProgress.successful}
                          </div>
                          <div className="text-muted-foreground">Successful</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold text-red-600">
                            {latestProgress.failed}
                          </div>
                          <div className="text-muted-foreground">Failed</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold text-gray-600">
                            {latestProgress.skipped}
                          </div>
                          <div className="text-muted-foreground">Skipped</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Recent Discoveries */}
              {discoveryHistory.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Zap className="h-5 w-5" />
                      Recent Discoveries
                    </CardTitle>
                    <CardDescription>
                      Zero-touch provisioning device discoveries
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {discoveryHistory.slice(-5).reverse().map((discovery, index) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
                            <div>
                              <div className="font-medium">{discovery.device_id}</div>
                              <div className="text-sm text-muted-foreground">
                                {discovery.device_type || 'Unknown Type'} • {discovery.discovery_method}
                              </div>
                            </div>
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {new Date(discovery.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Connection Status Alert */}
              {!isConnected && (
                <Alert variant="destructive">
                  <WifiOff className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Connection Lost:</strong> Real-time updates are currently unavailable. 
                    Click reconnect to restore live monitoring capabilities.
                  </AlertDescription>
                </Alert>
              )}

              {/* No Activity Alert */}
              {isConnected && !latestProgress && discoveryHistory.length === 0 && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Ready for Provisioning:</strong> No active provisioning sessions detected. 
                    Real-time updates will appear here when provisioning activities begin.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </TabsContent>
        </Tabs>
        
        {/* Provisioning Dialogs */}
        
        {/* Zero-Touch Provisioning Dialog */}
        <Dialog open={dialogOpen['zero-touch']} onOpenChange={(open) => setDialogOpen({ ...dialogOpen, 'zero-touch': open })}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Wifi className="h-5 w-5" />
                Zero-Touch Provisioning Configuration
              </DialogTitle>
              <DialogDescription>
                Configure automated device discovery and enrollment settings
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="discovery-method" className="text-right">
                  Discovery Method
                </Label>
                <Select
                  value={zeroTouchConfig.discovery_method}
                  onValueChange={(value: any) => setZeroTouchConfig({ ...zeroTouchConfig, discovery_method: value })}
                >
                  <SelectTrigger className="col-span-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dhcp">DHCP Discovery</SelectItem>
                    <SelectItem value="mdns">mDNS Discovery</SelectItem>
                    <SelectItem value="scan">Network Scan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="network-range" className="text-right">
                  Network Range
                </Label>
                <Input
                  id="network-range"
                  value={zeroTouchConfig.network_range}
                  onChange={(e) => setZeroTouchConfig({ ...zeroTouchConfig, network_range: e.target.value })}
                  className="col-span-3"
                  placeholder="192.168.1.0/24"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label className="text-right">Options</Label>
                <div className="col-span-3 space-y-2">
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={zeroTouchConfig.auto_provision}
                      onChange={(e) => setZeroTouchConfig({ ...zeroTouchConfig, auto_provision: e.target.checked })}
                      className="rounded"
                    />
                    Auto-provision discovered devices
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={zeroTouchConfig.require_approval}
                      onChange={(e) => setZeroTouchConfig({ ...zeroTouchConfig, require_approval: e.target.checked })}
                      className="rounded"
                    />
                    Require manual approval
                  </label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen({ ...dialogOpen, 'zero-touch': false })}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleZeroTouchProvisioning}
                disabled={isLoading['zero-touch']}
              >
                {isLoading['zero-touch'] ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  'Start Discovery'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* QR Code Provisioning Dialog */}
        <Dialog 
          open={dialogOpen['qr-code']} 
          onOpenChange={(open) => {
            setDialogOpen({ ...dialogOpen, 'qr-code': open });
            if (!open) {
              setQrCodeData({});
            }
          }}
        >
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <QrCode className="h-5 w-5" />
                QR Code Provisioning
              </DialogTitle>
              <DialogDescription>
                Generate a secure QR code for device provisioning
              </DialogDescription>
            </DialogHeader>
            <div className="py-4">
              {qrCodeData.qr_code ? (
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <img src={qrCodeData.qr_code} alt="Provisioning QR Code" className="w-64 h-64" />
                  </div>
                  <div className="text-center space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Scan this QR code with your device to begin provisioning
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Expires: {new Date(qrCodeData.expires_at!).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex justify-center gap-2">
                    <Button
                      variant="outline"
                      onClick={() => {
                        // Download QR code
                        const link = document.createElement('a');
                        link.download = 'provisioning-qr.png';
                        link.href = qrCodeData.qr_code!;
                        link.click();
                      }}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Download QR
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(qrCodeData.provisioning_url!);
                        toast({
                          title: 'URL Copied',
                          description: 'Provisioning URL has been copied to clipboard',
                        });
                      }}
                    >
                      Copy URL
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <QrCode className="mx-auto h-16 w-16 text-muted-foreground mb-4" />
                  <p className="text-muted-foreground mb-4">
                    Click generate to create a new provisioning QR code
                  </p>
                  <Button onClick={handleQrCodeGeneration} disabled={isLoading['qr-code']}>
                    {isLoading['qr-code'] ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      'Generate QR Code'
                    )}
                  </Button>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDialogOpen({ ...dialogOpen, 'qr-code': false });
                  setQrCodeData({});
                }}
              >
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Bulk Import Dialog */}
        <Dialog open={dialogOpen['bulk-import']} onOpenChange={(open) => setDialogOpen({ ...dialogOpen, 'bulk-import': open })}>
          <DialogContent className="sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Bulk Import Devices
              </DialogTitle>
              <DialogDescription>
                Import multiple devices from a CSV file
              </DialogDescription>
            </DialogHeader>
            <div className="py-4 space-y-4">
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  CSV format: device_id, name, type, location, tags (comma-separated)
                </AlertDescription>
              </Alert>
              <div className="space-y-4">
                <div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // Download sample CSV template
                      const csvContent = `device_id,name,type,location,tags
DEV-001,Temperature Sensor 1,sensor,Building A - Room 101,"temperature,environmental"
DEV-002,Motion Detector 1,sensor,Building A - Entrance,"motion,security"
DEV-003,Smart Light Controller,actuator,Building A - Room 101,"lighting,control"
DEV-004,HVAC Controller,controller,Building A - Server Room,"hvac,environmental"`;
                      
                      const blob = new Blob([csvContent], { type: 'text/csv' });
                      const url = window.URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = 'device-import-template.csv';
                      link.click();
                      window.URL.revokeObjectURL(url);
                      
                      toast({
                        title: 'Template Downloaded',
                        description: 'Sample CSV template has been downloaded',
                      });
                    }}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download CSV Template
                  </Button>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="csv-file">Select CSV File</Label>
                  <Input
                    id="csv-file"
                    type="file"
                    accept=".csv"
                    ref={fileInputRef}
                    onChange={handleBulkImport}
                    disabled={isLoading['bulk-import']}
                  />
                </div>
              </div>
              {isLoading['bulk-import'] && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-8 w-8 animate-spin" />
                  <span className="ml-2">Processing file...</span>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen({ ...dialogOpen, 'bulk-import': false })}
              >
                Cancel
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Manual Provisioning Dialog */}
        <Dialog open={dialogOpen['manual']} onOpenChange={(open) => setDialogOpen({ ...dialogOpen, 'manual': open })}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Manual Device Provisioning
              </DialogTitle>
              <DialogDescription>
                Create a new device with manual configuration
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="device-id" className="text-right">
                  Device ID
                </Label>
                <Input
                  id="device-id"
                  value={manualDevice.device_id}
                  onChange={(e) => setManualDevice({ ...manualDevice, device_id: e.target.value })}
                  className="col-span-3"
                  placeholder="unique-device-id"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="device-name" className="text-right">
                  Name
                </Label>
                <Input
                  id="device-name"
                  value={manualDevice.name}
                  onChange={(e) => setManualDevice({ ...manualDevice, name: e.target.value })}
                  className="col-span-3"
                  placeholder="Device Name"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="device-type" className="text-right">
                  Type
                </Label>
                <Select
                  value={manualDevice.type}
                  onValueChange={(value) => setManualDevice({ ...manualDevice, type: value })}
                >
                  <SelectTrigger className="col-span-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sensor">Sensor</SelectItem>
                    <SelectItem value="actuator">Actuator</SelectItem>
                    <SelectItem value="gateway">Gateway</SelectItem>
                    <SelectItem value="controller">Controller</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="device-location" className="text-right">
                  Location
                </Label>
                <Input
                  id="device-location"
                  value={manualDevice.location}
                  onChange={(e) => setManualDevice({ ...manualDevice, location: e.target.value })}
                  className="col-span-3"
                  placeholder="Building A, Floor 2"
                />
              </div>
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="device-tags" className="text-right">
                  Tags
                </Label>
                <Input
                  id="device-tags"
                  value={manualDevice.tags}
                  onChange={(e) => setManualDevice({ ...manualDevice, tags: e.target.value })}
                  className="col-span-3"
                  placeholder="tag1, tag2, tag3"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setDialogOpen({ ...dialogOpen, 'manual': false })}
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleManualProvisioning}
                disabled={isLoading['manual'] || !manualDevice.device_id || !manualDevice.name}
              >
                {isLoading['manual'] ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create Device'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};