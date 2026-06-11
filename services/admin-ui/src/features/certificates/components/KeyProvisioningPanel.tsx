/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { useToast } from '@/hooks/use-toast';
import {
  Key,
  Shield,
  Lock,
  Unlock,
  FileKey,
  Settings,
  Activity,
  AlertCircle,
  Info,
  Zap,
  CheckCircle2,
  Clock,
  Globe,
  Server,
  Loader2,
  Wifi,
  WifiOff,
  Plus,
  RefreshCw,
  Calendar,
  Bell,
  X
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
import { useProvisioningWebSocket } from '@/hooks/useProvisioningWebSocket';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { tesaApi } from '@/services/api/tesaApi';
import { Device } from '@/services/api/tesaApi';

interface KeyProvisioningPanelProps {
  className?: string;
}

interface KeyGenerationRequest {
  device_ids: string[];
  key_type: string;
  algorithm: string;
  key_size?: number;
  purpose?: string;
}

interface RotationPolicy {
  id: string;
  name: string;
  rotation_interval_days: number;
  key_types: string[];
  auto_rotate: boolean;
  notify_before_days: number;
  created_at: string;
  updated_at: string;
}

export const KeyProvisioningPanel: React.FC<KeyProvisioningPanelProps> = ({ className }) => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('overview');
  const [isGenerating, setIsGenerating] = useState(false);
  const [showKeyGenDialog, setShowKeyGenDialog] = useState(false);
  const [showRotationDialog, setShowRotationDialog] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [rotationPolicies, setRotationPolicies] = useState<RotationPolicy[]>([]);
  const [selectedDevices, setSelectedDevices] = useState<string[]>([]);
  const [keyGenConfig, setKeyGenConfig] = useState<KeyGenerationRequest>({
    device_ids: [],
    key_type: 'device_certificate',
    algorithm: 'RSA',
    key_size: 3072,
    purpose: 'device_identity'
  });
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    rotation_interval_days: 90,
    key_types: ['device_certificate'],
    auto_rotate: true,
    notify_before_days: 14
  });
  
  // Check if user has access to key provisioning features
  const hasKeyProvisioningAccess = user?.role !== 'platform_admin';
  const isOrgAdmin = user?.role === 'organization_admin' || user?.role === 'super_admin';
  
  // WebSocket connection for real-time updates
  const wsUrl = process.env.NODE_ENV === 'development' 
    ? 'ws://localhost:8000/ws/provisioning'
    : `wss://${window.location.host}/ws/provisioning`;
    
  const {
    isConnected,
    error: wsError,
    latestKeyStatus,
    latestNotification,
    keyStatusHistory,
    reconnect
  } = useProvisioningWebSocket(wsUrl);
  
  // Handle key generation notifications
  useEffect(() => {
    if (latestNotification && latestNotification.subtype.includes('key_generation')) {
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
        description: 'Lost connection to key provisioning updates. Attempting to reconnect...',
        variant: 'destructive',
      });
    }
  }, [wsError, toast]);

  // Load devices and rotation policies
  useEffect(() => {
    loadDevices();
    loadRotationPolicies();
  }, []);

  const loadDevices = async () => {
    try {
      const deviceList = await tesaApi.getDevices();
      setDevices(deviceList);
    } catch (error) {
      console.error('Failed to load devices:', error);
      toast({
        title: 'Error',
        description: 'Failed to load devices',
        variant: 'destructive',
      });
    }
  };

  const loadRotationPolicies = async () => {
    try {
      const response = await tesaApi.getRotationPolicies();
      setRotationPolicies(response);
    } catch (error) {
      console.error('Failed to load rotation policies:', error);
    }
  };

  const handleKeyGeneration = async () => {
    if (selectedDevices.length === 0) {
      toast({
        title: 'Error',
        description: 'Please select at least one device',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    try {
      const response = await tesaApi.generateKeys({
        ...keyGenConfig,
        device_ids: selectedDevices
      });
      
      toast({
        title: 'Success',
        description: `Key generation initiated for ${selectedDevices.length} device(s)`,
      });
      
      setShowKeyGenDialog(false);
      setSelectedDevices([]);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to generate keys',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreateRotationPolicy = async () => {
    if (!newPolicy.name) {
      toast({
        title: 'Error',
        description: 'Please provide a policy name',
        variant: 'destructive',
      });
      return;
    }

    try {
      const response = await tesaApi.createRotationPolicy(newPolicy);
      
      toast({
        title: 'Success',
        description: 'Rotation policy created successfully',
      });
      
      setShowRotationDialog(false);
      setNewPolicy({
        name: '',
        rotation_interval_days: 90,
        key_types: ['device_certificate'],
        auto_rotate: true,
        notify_before_days: 14
      });
      
      loadRotationPolicies();
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create rotation policy',
        variant: 'destructive',
      });
    }
  };

  const toggleDeviceSelection = (deviceId: string) => {
    setSelectedDevices(prev => 
      prev.includes(deviceId) 
        ? prev.filter(id => id !== deviceId)
        : [...prev, deviceId]
    );
  };

  const keyTypes = [
    {
      id: 'device-identity',
      name: 'Device Identity Keys',
      icon: Key,
      description: 'Unique cryptographic identity for each device',
      status: 'available',
      algorithm: 'RSA 3072 / ECC P-256',
      badge: 'Core'
    },
    {
      id: 'encryption',
      name: 'Data Encryption Keys',
      icon: Lock,
      description: 'Keys for secure data transmission',
      status: 'available',
      algorithm: 'AES-256-GCM',
      badge: 'Security'
    },
    {
      id: 'signing',
      name: 'Digital Signing Keys',
      icon: FileKey,
      description: 'Keys for message authentication and integrity',
      status: 'available',
      algorithm: 'ECDSA P-256',
      badge: 'Integrity'
    },
    {
      id: 'root-ca',
      name: 'Root CA Keys',
      icon: Shield,
      description: 'Certificate authority root keys',
      status: 'restricted',
      algorithm: 'RSA 4096 / ECC P-384',
      badge: 'Critical'
    }
  ];

  const provisioningMethods = [
    {
      id: 'secure-channel',
      name: 'Secure Channel Provisioning',
      description: 'Keys delivered through encrypted channels',
      icon: Zap,
      status: 'recommended'
    },
    {
      id: 'out-of-band',
      name: 'Out-of-Band Provisioning',
      description: 'Keys delivered via separate secure medium',
      icon: Globe,
      status: 'high-security'
    },
    {
      id: 'hsm-direct',
      name: 'HSM Direct Provisioning',
      description: 'Keys generated and stored in HSM',
      icon: Server,
      status: 'enterprise'
    }
  ];

  const securityFeatures = [
    'Hardware Security Module (HSM) integration',
    'Key escrow and recovery capabilities',
    'Cryptographic key lifecycle management',
    'Secure key distribution protocols',
    'Key rotation and renewal automation',
    'Tamper-evident key storage'
  ];

  return (
    <div className={className}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Key Provisioning</h2>
            <p className="text-muted-foreground">
              Secure cryptographic key management and distribution
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <Shield className="h-3 w-3" />
              FIPS 140-2 Level 3
            </Badge>
            <Badge variant="outline" className="gap-1">
              <Lock className="h-3 w-3" />
              HSM Protected
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
            <TabsTrigger value="key-types" className="flex items-center gap-2">
              <Key className="h-4 w-4" />
              Key Types
            </TabsTrigger>
            <TabsTrigger value="provisioning" className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Provisioning
            </TabsTrigger>
            <TabsTrigger value="monitoring" className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Monitoring
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <div className="grid gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="h-5 w-5" />
                    Key Provisioning Overview
                  </CardTitle>
                  <CardDescription>
                    Enterprise-grade cryptographic key management for IoT devices
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <h4 className="font-semibold">Key Management Features</h4>
                      <ul className="space-y-2 text-sm">
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Automated key generation
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Secure key distribution
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Key lifecycle management
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                          Hardware security module integration
                        </li>
                      </ul>
                    </div>
                    <div className="space-y-3">
                      <h4 className="font-semibold">Cryptographic Standards</h4>
                      <ul className="space-y-2 text-sm">
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          NIST approved algorithms
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Post-quantum cryptography ready
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          FIPS 140-2 compliance
                        </li>
                        <li className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-blue-500" />
                          Common Criteria certification
                        </li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Active Keys</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {keyStatusHistory.filter(k => k.status === 'completed').length}
                    </div>
                    <p className="text-xs text-muted-foreground">Across all devices</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Rotation Policies</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{rotationPolicies.length}</div>
                    <p className="text-xs text-muted-foreground">
                      {rotationPolicies.filter(p => p.auto_rotate).length} automated
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium">Next Rotation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">14</div>
                    <p className="text-xs text-muted-foreground">Days remaining</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="key-types" className="mt-6">
            <div className="grid gap-4">
              {keyTypes.map((keyType) => (
                <Card key={keyType.id} className="relative">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <keyType.icon className="h-6 w-6" />
                        <div>
                          <CardTitle className="text-lg">{keyType.name}</CardTitle>
                          <CardDescription>{keyType.description}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{keyType.badge}</Badge>
                        <Badge 
                          variant="outline" 
                          className={keyType.status === 'restricted' ? 'text-red-600' : 'text-green-600'}
                        >
                          {keyType.status}
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <div className="text-sm text-muted-foreground">
                        Algorithm: <span className="font-medium">{keyType.algorithm}</span>
                      </div>
                      <Button 
                        variant="outline" 
                        disabled={keyType.status === 'restricted'}
                        size="sm"
                        onClick={() => {
                          if (keyType.status !== 'restricted') {
                            setKeyGenConfig(prev => ({ 
                              ...prev, 
                              key_type: keyType.id,
                              algorithm: keyType.algorithm.split(' ')[0] // Extract primary algorithm
                            }));
                            setShowKeyGenDialog(true);
                          }
                        }}
                      >
                        {keyType.status === 'restricted' ? 'Restricted Access' : 'Generate Keys'}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="provisioning" className="mt-6">
            <div className="space-y-6">
              {/* Key Generation Section */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="h-5 w-5" />
                    Key Generation
                  </CardTitle>
                  <CardDescription>
                    Generate cryptographic keys for your devices
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">
                        Generate device identity keys, encryption keys, or signing keys for selected devices.
                      </p>
                    </div>
                    <Button onClick={() => setShowKeyGenDialog(true)}>
                      <Plus className="h-4 w-4 mr-2" />
                      Generate Keys
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Rotation Policies */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <RefreshCw className="h-5 w-5" />
                    Key Rotation Policies
                  </CardTitle>
                  <CardDescription>
                    Automated key lifecycle management
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-4">
                      <p className="text-sm text-muted-foreground">
                        Define policies for automatic key rotation based on age or compliance requirements.
                      </p>
                      <Button variant="outline" onClick={() => setShowRotationDialog(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Policy
                      </Button>
                    </div>
                    
                    {rotationPolicies.length > 0 ? (
                      <div className="space-y-3">
                        {rotationPolicies.map((policy) => (
                          <div key={policy.id} className="flex items-center justify-between p-4 border rounded-lg">
                            <div>
                              <h4 className="font-semibold">{policy.name}</h4>
                              <div className="flex gap-4 mt-1">
                                <span className="text-sm text-muted-foreground">
                                  <Calendar className="h-3 w-3 inline mr-1" />
                                  Rotate every {policy.rotation_interval_days} days
                                </span>
                                <span className="text-sm text-muted-foreground">
                                  <Bell className="h-3 w-3 inline mr-1" />
                                  Notify {policy.notify_before_days} days before
                                </span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant={policy.auto_rotate ? "default" : "outline"}>
                                {policy.auto_rotate ? 'Auto-Rotate' : 'Manual'}
                              </Badge>
                              <Button variant="outline" size="sm">
                                Edit
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-muted-foreground">
                        No rotation policies defined. Create one to get started.
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5" />
                    Provisioning Methods
                  </CardTitle>
                  <CardDescription>
                    Secure key delivery mechanisms for different security requirements
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4">
                    {provisioningMethods.map((method) => (
                      <div key={method.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <method.icon className="h-5 w-5" />
                          <div>
                            <h4 className="font-semibold">{method.name}</h4>
                            <p className="text-sm text-muted-foreground">{method.description}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{method.status}</Badge>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => {
                              toast({
                                title: 'Info',
                                description: `${method.name} configuration will be available in the next release`,
                              });
                            }}
                          >
                            Configure
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5" />
                    Security Features
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <ul className="space-y-2">
                      {securityFeatures.map((feature, index) => (
                        <li key={index} className="flex items-center gap-2 text-sm">
                          <Lock className="h-4 w-4 text-blue-500" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="monitoring" className="mt-6">
            <div className="space-y-6">
              {/* Key Status Overview */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Activity className="h-5 w-5" />
                    Key Provisioning Status
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
                    Real-time key management activity and statistics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {keyStatusHistory.filter(k => k.status === 'completed').length}
                      </div>
                      <div className="text-sm text-muted-foreground">Generated Keys</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {keyStatusHistory.filter(k => k.status === 'started').length}
                      </div>
                      <div className="text-sm text-muted-foreground">Pending Requests</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {keyStatusHistory.filter(k => k.key_type === 'device_certificate').length}
                      </div>
                      <div className="text-sm text-muted-foreground">Device Certificates</div>
                    </div>
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-red-600">
                        {keyStatusHistory.filter(k => k.status === 'failed').length}
                      </div>
                      <div className="text-sm text-muted-foreground">Failed Operations</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Current Key Generation */}
              {latestKeyStatus && latestKeyStatus.status === 'started' && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Active Key Generation
                    </CardTitle>
                    <CardDescription>
                      Operation: {latestKeyStatus.operation_id}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium">{latestKeyStatus.device_id}</div>
                          <div className="text-sm text-muted-foreground">
                            {latestKeyStatus.key_type.replace('_', ' ').toUpperCase()}
                          </div>
                        </div>
                        <Badge variant="outline">
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          Generating
                        </Badge>
                      </div>
                      
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Progress</span>
                          <span>{latestKeyStatus.progress}%</span>
                        </div>
                        <Progress value={latestKeyStatus.progress} className="h-3" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Recent Key Operations */}
              {keyStatusHistory.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Clock className="h-5 w-5" />
                      Recent Key Operations
                    </CardTitle>
                    <CardDescription>
                      Latest key generation and distribution activities
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {keyStatusHistory.slice(-10).reverse().map((keyOp, index) => (
                        <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className={`h-2 w-2 rounded-full ${
                              keyOp.status === 'completed' ? 'bg-green-500' :
                              keyOp.status === 'failed' ? 'bg-red-500' :
                              'bg-blue-500 animate-pulse'
                            }`}></div>
                            <div>
                              <div className="font-medium">{keyOp.device_id}</div>
                              <div className="text-sm text-muted-foreground">
                                {keyOp.key_type.replace('_', ' ')} • {keyOp.status}
                                {keyOp.serial_number && ` • ${keyOp.serial_number}`}
                              </div>
                              {keyOp.error_message && (
                                <div className="text-sm text-red-600">
                                  {keyOp.error_message}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge variant={
                              keyOp.status === 'completed' ? 'default' :
                              keyOp.status === 'failed' ? 'destructive' :
                              'secondary'
                            }>
                              {keyOp.status}
                            </Badge>
                            <div className="text-sm text-muted-foreground mt-1">
                              {keyOp.progress}%
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Key Lifecycle Progress */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Key Lifecycle Progress
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Key Generation</span>
                        <span>{keyStatusHistory.length > 0 ? 
                          Math.round((keyStatusHistory.filter(k => k.status === 'completed').length / keyStatusHistory.length) * 100) : 0}%</span>
                      </div>
                      <Progress value={keyStatusHistory.length > 0 ? 
                        (keyStatusHistory.filter(k => k.status === 'completed').length / keyStatusHistory.length) * 100 : 0} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Key Distribution</span>
                        <span>{keyStatusHistory.length > 0 ? 
                          Math.round((keyStatusHistory.filter(k => k.status === 'completed' && k.serial_number).length / keyStatusHistory.length) * 100) : 0}%</span>
                      </div>
                      <Progress value={keyStatusHistory.length > 0 ? 
                        (keyStatusHistory.filter(k => k.status === 'completed' && k.serial_number).length / keyStatusHistory.length) * 100 : 0} className="h-2" />
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Success Rate</span>
                        <span>{keyStatusHistory.length > 0 ? 
                          Math.round(((keyStatusHistory.length - keyStatusHistory.filter(k => k.status === 'failed').length) / keyStatusHistory.length) * 100) : 100}%</span>
                      </div>
                      <Progress value={keyStatusHistory.length > 0 ? 
                        ((keyStatusHistory.length - keyStatusHistory.filter(k => k.status === 'failed').length) / keyStatusHistory.length) * 100 : 100} className="h-2" />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Connection Status Alert */}
              {!isConnected && (
                <Alert variant="destructive">
                  <WifiOff className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Connection Lost:</strong> Real-time key provisioning updates are currently unavailable. 
                    Click reconnect to restore live monitoring capabilities.
                  </AlertDescription>
                </Alert>
              )}

              {/* No Activity Alert - Commented out as requested */}
              {/* {isConnected && keyStatusHistory.length === 0 && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Ready for Key Operations:</strong> No key generation activity detected. 
                    Real-time progress will appear here when key provisioning operations begin.
                  </AlertDescription>
                </Alert>
              )} */}
            </div>
          </TabsContent>
        </Tabs>

        {/* Key Generation Dialog */}
        <Dialog open={showKeyGenDialog} onOpenChange={setShowKeyGenDialog}>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Generate Cryptographic Keys</DialogTitle>
              <DialogDescription>
                Select devices and configure key generation parameters
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Device Selection */}
              <div>
                <Label>Select Devices</Label>
                <div className="mt-2 border rounded-lg p-4 max-h-48 overflow-y-auto">
                  {devices.length > 0 ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-muted-foreground">
                          {selectedDevices.length} of {devices.length} selected
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (selectedDevices.length === devices.length) {
                              setSelectedDevices([]);
                            } else {
                              setSelectedDevices(devices.map(d => d.id));
                            }
                          }}
                        >
                          {selectedDevices.length === devices.length ? 'Clear All' : 'Select All'}
                        </Button>
                      </div>
                      {devices.map((device) => (
                        <div key={device.id} className="flex items-center space-x-2">
                          <Checkbox
                            id={device.id}
                            checked={selectedDevices.includes(device.id)}
                            onCheckedChange={() => toggleDeviceSelection(device.id)}
                          />
                          <label
                            htmlFor={device.id}
                            className="flex-1 cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            {device.name}
                            <span className="text-xs text-muted-foreground ml-2">
                              ({device.type} - {device.status})
                            </span>
                          </label>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No devices available. Please add devices first.
                    </p>
                  )}
                </div>
              </div>

              {/* Key Type */}
              <div>
                <Label htmlFor="key-type">Key Type</Label>
                <Select
                  value={keyGenConfig.key_type}
                  onValueChange={(value) => setKeyGenConfig(prev => ({ ...prev, key_type: value }))}
                >
                  <SelectTrigger id="key-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="device_certificate">Device Identity Certificate</SelectItem>
                    <SelectItem value="encryption">Data Encryption Key</SelectItem>
                    <SelectItem value="signing">Digital Signing Key</SelectItem>
                    <SelectItem value="tls">TLS Client Certificate</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Algorithm Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="algorithm">Algorithm</Label>
                  <Select
                    value={keyGenConfig.algorithm}
                    onValueChange={(value) => setKeyGenConfig(prev => ({ ...prev, algorithm: value }))}
                  >
                    <SelectTrigger id="algorithm">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="RSA">RSA</SelectItem>
                      <SelectItem value="ECC">ECC (Elliptic Curve)</SelectItem>
                      <SelectItem value="ECDSA">ECDSA</SelectItem>
                      <SelectItem value="EdDSA">EdDSA</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="key-size">Key Size</Label>
                  <Select
                    value={keyGenConfig.key_size?.toString()}
                    onValueChange={(value) => setKeyGenConfig(prev => ({ ...prev, key_size: parseInt(value) }))}
                  >
                    <SelectTrigger id="key-size">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {keyGenConfig.algorithm === 'RSA' ? (
                        <>
                          <SelectItem value="2048">2048 bits</SelectItem>
                          <SelectItem value="3072">3072 bits (recommended)</SelectItem>
                          <SelectItem value="4096">4096 bits</SelectItem>
                        </>
                      ) : (
                        <>
                          <SelectItem value="256">P-256</SelectItem>
                          <SelectItem value="384">P-384</SelectItem>
                          <SelectItem value="521">P-521</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Purpose */}
              <div>
                <Label htmlFor="purpose">Purpose (Optional)</Label>
                <Input
                  id="purpose"
                  placeholder="e.g., Production device authentication"
                  value={keyGenConfig.purpose || ''}
                  onChange={(e) => setKeyGenConfig(prev => ({ ...prev, purpose: e.target.value }))}
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowKeyGenDialog(false)}>
                Cancel
              </Button>
              <Button 
                onClick={handleKeyGeneration} 
                disabled={isGenerating || selectedDevices.length === 0}
              >
                {isGenerating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Generate Keys for {selectedDevices.length} Device(s)
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Rotation Policy Dialog */}
        <Dialog open={showRotationDialog} onOpenChange={setShowRotationDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Key Rotation Policy</DialogTitle>
              <DialogDescription>
                Define automated key rotation rules for enhanced security
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <Label htmlFor="policy-name">Policy Name</Label>
                <Input
                  id="policy-name"
                  placeholder="e.g., Quarterly Device Key Rotation"
                  value={newPolicy.name}
                  onChange={(e) => setNewPolicy(prev => ({ ...prev, name: e.target.value }))}
                />
              </div>

              <div>
                <Label htmlFor="rotation-interval">Rotation Interval (days)</Label>
                <Input
                  id="rotation-interval"
                  type="number"
                  min="1"
                  max="365"
                  value={newPolicy.rotation_interval_days}
                  onChange={(e) => setNewPolicy(prev => ({ 
                    ...prev, 
                    rotation_interval_days: parseInt(e.target.value) || 90 
                  }))}
                />
              </div>

              <div>
                <Label htmlFor="notify-before">Notify Before Rotation (days)</Label>
                <Input
                  id="notify-before"
                  type="number"
                  min="1"
                  max="30"
                  value={newPolicy.notify_before_days}
                  onChange={(e) => setNewPolicy(prev => ({ 
                    ...prev, 
                    notify_before_days: parseInt(e.target.value) || 14 
                  }))}
                />
              </div>

              <div>
                <Label>Key Types</Label>
                <div className="space-y-2 mt-2">
                  {['device_certificate', 'encryption', 'signing', 'tls'].map((keyType) => (
                    <div key={keyType} className="flex items-center space-x-2">
                      <Checkbox
                        id={`policy-${keyType}`}
                        checked={newPolicy.key_types.includes(keyType)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setNewPolicy(prev => ({ 
                              ...prev, 
                              key_types: [...prev.key_types, keyType] 
                            }));
                          } else {
                            setNewPolicy(prev => ({ 
                              ...prev, 
                              key_types: prev.key_types.filter(t => t !== keyType) 
                            }));
                          }
                        }}
                      />
                      <label
                        htmlFor={`policy-${keyType}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        {keyType.replace('_', ' ').charAt(0).toUpperCase() + keyType.slice(1).replace('_', ' ')}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="auto-rotate"
                  checked={newPolicy.auto_rotate}
                  onCheckedChange={(checked) => 
                    setNewPolicy(prev => ({ ...prev, auto_rotate: checked as boolean }))
                  }
                />
                <label
                  htmlFor="auto-rotate"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                >
                  Enable automatic rotation
                </label>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowRotationDialog(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateRotationPolicy}>
                Create Policy
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};