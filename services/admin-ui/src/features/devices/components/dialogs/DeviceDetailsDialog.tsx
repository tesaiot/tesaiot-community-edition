/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Terminal, Play, Key, Shield, AlertTriangle, Database, RefreshCw, Pause, Heart, Building, Factory, Zap, Leaf, CheckCircle2, XCircle, QrCode, Package } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Device } from '../../types/device.types';
import { TelemetryChart } from '../charts/TelemetryChart';
import { AnalyticsCharts } from '../charts/AnalyticsCharts';
import { TelemetryDashboard } from '../TelemetryDashboard';
import { DeviceCredentialsSection } from '../DeviceCredentialsSection';
import { DeviceQRCode } from '../DeviceQRCode';
import { authFetch } from '@/utils/auth-fetch';
import { tesaApi } from '@/services/api/tesaApi';
import { CertificateStatusBadge, getCertificateInfo } from '@/features/certificates/components/CertificateStatusBadge';
import { toast } from 'sonner';

// Device Logs Improvement Feature (v2026.01) - Enhanced debugging components
import { CSRWorkflowWidget } from '../CSRWorkflowWidget';
import { RealtimeDebugConsole } from '../RealtimeDebugConsole';

interface DeviceDetailsDialogProps {
  device: Device | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  realTelemetryData?: any[];
  telemetryLoading?: boolean;
  onRenewCertificate?: (device: Device) => void;
  // Optional external control of the active top-level tab (overview, credentials, logs, etc.)
  activeTab?: string;
  onTabChange?: (tab: string) => void;
  // Optional: default inner tab for the Credentials section ("credentials" or "certificates")
  credentialsDefaultTab?: 'credentials' | 'certificates';
}

export function DeviceDetailsDialog({
  device,
  open,
  onOpenChange,
  realTelemetryData = [],
  telemetryLoading = false,
  onRenewCertificate,
  activeTab: activeTabProp,
  onTabChange,
  credentialsDefaultTab,
}: DeviceDetailsDialogProps) {
  // Internal state with optional external control
  const [internalTab, setInternalTab] = useState('overview');
  const activeTab = activeTabProp ?? internalTab;
  const setActiveTab = (tab: string) => {
    setInternalTab(tab);
    if (onTabChange) onTabChange(tab);
  };
  const [detailedDevice, setDetailedDevice] = useState<Device | null>(null);
  const [deviceLoading, setDeviceLoading] = useState(false);
  const [certificateData, setCertificateData] = useState<any>(null);
  const [certificateLoading, setCertificateLoading] = useState(false);
  const [deviceLogs, setDeviceLogs] = useState<any[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsAutoRefresh, setLogsAutoRefresh] = useState(false);
  const logsIntervalRef = React.useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!open) {
      setActiveTab('overview');
      setLogsAutoRefresh(false);
      setDetailedDevice(null);
    }
  }, [open]);

  // Fetch detailed device data when device or dialog opens
  useEffect(() => {
    if (device && open) {
      fetchDetailedDeviceData();
      if (activeTab === 'logs') {
        fetchDeviceLogs();
      }
    }
  }, [device, open, activeTab]);

  // Fetch certificate data when detailed device is loaded
  useEffect(() => {
    if (detailedDevice && open) {
      fetchDeviceCertificateData();
    }
  }, [detailedDevice, open]);

  // Debug certificateData state changes
  useEffect(() => {
    console.log('=== CERTIFICATE DATA STATE UPDATED ===');
    console.log('certificateData:', JSON.stringify(certificateData, null, 2));
    console.log('detailedDevice:', JSON.stringify(detailedDevice, null, 2));
    if (certificateData?.certificate) {
      console.log('Certificate validFrom:', certificateData.certificate.validFrom);
      console.log('Certificate validTo:', certificateData.certificate.validTo);
    }
  }, [certificateData]);

  // Auto-refresh logs when enabled
  useEffect(() => {
    if (logsAutoRefresh && activeTab === 'logs' && open) {
      // Start auto-refresh interval
      logsIntervalRef.current = setInterval(() => {
        fetchDeviceLogs();
      }, 5000); // Refresh every 5 seconds
    } else {
      // Clear interval when auto-refresh is disabled
      if (logsIntervalRef.current) {
        clearInterval(logsIntervalRef.current);
        logsIntervalRef.current = null;
      }
    }

    // Cleanup on unmount
    return () => {
      if (logsIntervalRef.current) {
        clearInterval(logsIntervalRef.current);
      }
    };
  }, [logsAutoRefresh, activeTab, open]);

  const fetchDetailedDeviceData = async () => {
    if (!device) return;
    
    console.log('=== FETCHING DETAILED DEVICE DATA ===');
    console.log('Device ID for detailed fetch:', device.device_id || device.id);
    
    setDeviceLoading(true);
    try {
      const deviceId = device.device_id || device.id;
      const detailedDeviceData = await tesaApi.getDevice(deviceId);
      
      console.log('Detailed device data received:', JSON.stringify(detailedDeviceData, null, 2));
      console.log('Certificate fields in detailed data:');
      console.log('- certificate_issued_at:', (detailedDeviceData as any).certificate_issued_at);
      console.log('- certificate_expires_at:', (detailedDeviceData as any).certificate_expires_at);
      console.log('- certificate:', detailedDeviceData.certificate);
      console.log('- certificate_status:', (detailedDeviceData as any).certificate_status);
      
      setDetailedDevice(detailedDeviceData);
    } catch (error) {
      console.error('Error fetching detailed device data:', error);
      // Fallback to basic device data
      setDetailedDevice(device);
    } finally {
      setDeviceLoading(false);
    }
  };

  const fetchDeviceCertificateData = async () => {
    const deviceToUse = detailedDevice || device;
    if (!deviceToUse) return;
    
    console.log('=== CERTIFICATE DATA DEBUG START ===');
    console.log('Device ID:', deviceToUse.device_id || deviceToUse.id);
    console.log('Using detailed device data:', detailedDevice ? 'YES' : 'NO');
    console.log('Full device object:', JSON.stringify(deviceToUse, null, 2));
    console.log('deviceToUse.certificate:', deviceToUse.certificate);
    console.log('deviceToUse.certificate_info:', (deviceToUse as any).certificate_info);
    console.log('All device properties:', Object.keys(deviceToUse));
    
    // Check for certificate properties at the device root level
    console.log('Checking device root level certificate properties:');
    console.log('- deviceToUse.certificate_issued_at:', (deviceToUse as any).certificate_issued_at);
    console.log('- deviceToUse.certificate_expires_at:', (deviceToUse as any).certificate_expires_at);
    console.log('- deviceToUse.certificate_status:', (deviceToUse as any).certificate_status);
    console.log('- deviceToUse.serial_number:', (deviceToUse as any).serial_number);
    console.log('- deviceToUse.validFrom:', (deviceToUse as any).validFrom);
    console.log('- deviceToUse.validTo:', (deviceToUse as any).validTo);
    console.log('- deviceToUse.issued_at:', (deviceToUse as any).issued_at);
    console.log('- deviceToUse.expires_at:', (deviceToUse as any).expires_at);
    
    setCertificateLoading(true);
    try {
      // First check if device already has certificate data
      if (deviceToUse.certificate || (deviceToUse as any).certificate_info) {
        // Use certificate_info for metadata, certificate is just the PEM string
        const cert = (deviceToUse as any).certificate_info || {};
        const pemCertificate = deviceToUse.certificate;
        console.log('Found certificate data on device object:');
        console.log('- PEM certificate exists:', !!pemCertificate);
        console.log('- Certificate info:', JSON.stringify(cert, null, 2));
        console.log('- Certificate algorithm from root:', (deviceToUse as any).certificate_algorithm);
        console.log('Certificate info properties:', Object.keys(cert));
        
        // Helper function to parse the date format from API
        const parseApiDate = (dateStr: string | undefined): string | undefined => {
          console.log('Parsing date string:', dateStr);
          if (!dateStr) {
            console.log('Date string is undefined/null');
            return undefined;
          }
          try {
            // Handle format like "Wed, 22 Jul 2026 02:52:22 GMT"
            const parsed = new Date(dateStr);
            console.log('Parsed date object:', parsed);
            console.log('Is valid date?', !isNaN(parsed.getTime()));
            if (!isNaN(parsed.getTime())) {
              const isoString = parsed.toISOString();
              console.log('Converted to ISO string:', isoString);
              return isoString;
            }
          } catch (e) {
            console.warn('Failed to parse date:', dateStr, e);
          }
          return dateStr; // Return original if parsing fails
        };
        
        // Log all possible date fields
        console.log('Checking all possible date fields in certificate:');
        console.log('- cert.validFrom:', cert.validFrom);
        console.log('- cert.issued_at:', cert.issued_at);
        console.log('- cert.issuedAt:', cert.issuedAt);
        console.log('- cert.not_before:', cert.not_before);
        console.log('- cert.notBefore:', cert.notBefore);
        console.log('- cert.validTo:', cert.validTo);
        console.log('- cert.expires_at:', cert.expires_at);
        console.log('- cert.expiresAt:', cert.expiresAt);
        console.log('- cert.not_after:', cert.not_after);
        console.log('- cert.notAfter:', cert.notAfter);
        
        const certificateData = {
          exists: true,
          certificate: {
            serial_number: cert.serialNumber || cert.serial_number || cert.serial || 
                          (deviceToUse as any).certificate_info?.serial,
            status: cert.status || 'active',
            algorithm: cert.algorithm || cert.key_algorithm || 
                      (deviceToUse as any).certificate_info?.algorithm || 
                      (deviceToUse as any).certificate_info?.key_algorithm ||
                      (deviceToUse as any).certificate_algorithm ||
                      'Unknown',
            validFrom: cert.validFrom || cert.issued_at || cert.issuedAt || 
                      cert.not_before || cert.notBefore ||
                      parseApiDate((deviceToUse as any).certificate_issued_at),
            validTo: cert.validTo || cert.expires_at || cert.expiresAt || 
                    cert.not_after || cert.notAfter ||
                    parseApiDate((deviceToUse as any).certificate_expires_at),
            issuer: cert.issuer || 'TESA IoT Platform CA',
            subject: cert.subject || `CN=${deviceToUse.device_id || deviceToUse.id}`,
            device_type: cert.type || deviceToUse.type
          }
        };
        
        console.log('Final certificate data being set:', JSON.stringify(certificateData, null, 2));
        setCertificateData(certificateData);
        return;
      }
      
      console.log('No certificate data on device object, fetching from API...');
      
      // Fallback: Try to get all certificates and find the one for this device
      const response = await authFetch('/api/v1/certificates');
      console.log('Certificates API response status:', response.status);
      
      if (response.ok) {
        const certificates = await response.json();
        console.log('All certificates:', certificates);
        
        // Find certificate for this device - check multiple field variations
        const deviceCert = certificates.find((cert: any) => {
          console.log('Checking certificate:', JSON.stringify(cert, null, 2));
          console.log('Certificate properties:', Object.keys(cert));
          const deviceId = deviceToUse.device_id || deviceToUse.id;
          console.log('Matching against device_id:', deviceId);
          console.log('- cert.deviceId === deviceId?', cert.deviceId === deviceId);
          console.log('- cert.device_id === deviceId?', cert.device_id === deviceId);
          console.log('- cert.device_name === deviceToUse.name?', cert.device_name === deviceToUse.name);
          console.log('- cert.common_name === CN match?', cert.common_name === `${deviceId}.sensor.tesa.iot`);
          
          return cert.deviceId === deviceId || 
                 cert.device_id === deviceId ||
                 cert.device_name === deviceToUse.name ||
                 cert.common_name === `${deviceId}.sensor.tesa.iot`;
        });
        
        console.log('Found device certificate:', JSON.stringify(deviceCert, null, 2));
        
        if (deviceCert) {
          // Helper function to parse the date format from API
          const parseApiDate = (dateStr: string | undefined): string | undefined => {
            if (!dateStr) return undefined;
            try {
              // Handle format like "Wed, 22 Jul 2026 02:52:22 GMT"
              const parsed = new Date(dateStr);
              if (!isNaN(parsed.getTime())) {
                return parsed.toISOString();
              }
            } catch (e) {
              console.warn('Failed to parse date:', dateStr, e);
            }
            return dateStr; // Return original if parsing fails
          };
          
          console.log('Checking all date fields in deviceCert:');
          console.log('- deviceCert.validFrom:', deviceCert.validFrom);
          console.log('- deviceCert.valid_from:', deviceCert.valid_from);
          console.log('- deviceCert.issued_at:', deviceCert.issued_at);
          console.log('- deviceCert.not_before:', deviceCert.not_before);
          console.log('- deviceCert.certificate_issued_at:', deviceCert.certificate_issued_at);
          console.log('- deviceCert.validTo:', deviceCert.validTo);
          console.log('- deviceCert.valid_to:', deviceCert.valid_to);
          console.log('- deviceCert.expires_at:', deviceCert.expires_at);
          console.log('- deviceCert.not_after:', deviceCert.not_after);
          console.log('- deviceCert.certificate_expires_at:', deviceCert.certificate_expires_at);
          
          // Transform the certificate data to match our expected structure
          const certificateData = {
            exists: true,
            certificate: {
              serial_number: deviceCert.serialNumber || deviceCert.serial_number || deviceCert.serial ||
                            (deviceToUse as any).certificate_info?.serial,
              status: deviceCert.status || 'active',
              algorithm: deviceCert.algorithm || deviceCert.key_algorithm || 
                        (deviceToUse as any).certificate_info?.algorithm || 
                        (deviceToUse as any).certificate_info?.key_algorithm ||
                        (deviceToUse as any).certificate_algorithm ||
                        'RSA 2048',
              validFrom: deviceCert.validFrom || deviceCert.valid_from || deviceCert.issued_at || deviceCert.not_before ||
                        parseApiDate(deviceCert.certificate_issued_at),
              validTo: deviceCert.validTo || deviceCert.valid_to || deviceCert.expires_at || deviceCert.not_after ||
                      parseApiDate(deviceCert.certificate_expires_at),
              issuer: deviceCert.issuer || 'CN=TESA IoT Intermediate CA',
              subject: deviceCert.subject || deviceCert.common_name || `CN=${deviceToUse.device_id || deviceToUse.id}.sensor.tesa.iot`,
              device_type: deviceCert.type || deviceToUse.type
            }
          };
          
          console.log('Transformed certificate data from API:', JSON.stringify(certificateData, null, 2));
          setCertificateData(certificateData);
        } else {
          console.log('No certificate found for device');
          setCertificateData({ exists: false });
        }
      } else {
        console.log('Certificates API failed, trying device-specific endpoint...');
        // Final fallback to device-specific endpoint if available
        const deviceId = deviceToUse.device_id || deviceToUse.id;
        const deviceResponse = await authFetch(`/api/v1/certificates/devices/${deviceId}/certificate`);
        console.log('Device-specific certificate API response status:', deviceResponse.status);
        
        if (deviceResponse.ok) {
          const data = await deviceResponse.json();
          console.log('Device-specific certificate data:', data);
          setCertificateData(data);
        } else {
          console.log('Device-specific certificate API failed');
          setCertificateData({ exists: false });
        }
      }
    } catch (error) {
      console.error('Error fetching certificate data:', error);
      setCertificateData({ exists: false });
    } finally {
      setCertificateLoading(false);
      // Note: certificateData state won't be updated yet due to React's async state updates
      console.log('=== CERTIFICATE DATA DEBUG END ===');
    }
  };

  const fetchDeviceLogs = async () => {
    const deviceToUse = detailedDevice || device;
    if (!deviceToUse) return;
    
    setLogsLoading(true);
    try {
      // Use the device-specific logs endpoint
      const deviceId = deviceToUse.device_id || deviceToUse.id;
      const response = await authFetch(`/api/v1/devices/${deviceId}/logs?limit=100&types=telemetry,connection,error,warning,info,security`);
      
      if (response.ok) {
        const data = await response.json();
        // The device logs endpoint returns logs in the correct format already
        setDeviceLogs(data.logs || []);
      } else {
        console.error('Failed to fetch device logs');
        // Fallback to general logs endpoint if device-specific fails
        try {
          const fallbackResponse = await authFetch(`/api/v1/logs?device_id=${deviceId}&limit=50`);
          if (fallbackResponse.ok) {
            const fallbackData = await fallbackResponse.json();
            // Transform logs to match expected format
            const transformedLogs = (fallbackData.logs || []).map((log: any) => ({
              _id: log.id,
              timestamp: log.time,
              level: log.level?.toUpperCase() || 'INFO',
              message: log.message,
              details: log.metadata || {},
              source: log.source,
              log_type: log.log_type
            }));
            setDeviceLogs(transformedLogs);
          } else {
            setDeviceLogs([]);
          }
        } catch (fallbackError) {
          console.error('Fallback logs fetch failed:', fallbackError);
          setDeviceLogs([]);
        }
      }
    } catch (error) {
      console.error('Error fetching device logs:', error);
      setDeviceLogs([]);
    } finally {
      setLogsLoading(false);
    }
  };

  const deviceToUse = detailedDevice || device;
  if (!deviceToUse) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-600';
      case 'offline':
        return 'text-gray-600';
      case 'error':
        return 'text-red-600';
      case 'maintenance':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  // Helper function to get industry display name
  const getIndustryDisplayName = (industry: string) => {
    const industryNames: Record<string, string> = {
      health_medical: 'Healthcare & Medical',
      industry_40: 'Industry 4.0',
      smart_city: 'Smart City',
      smart_energy: 'Smart Energy',
      smart_farm: 'Smart Agriculture'
    };
    return industryNames[industry] || industry;
  };

  // Helper function to format compliance data
  const formatComplianceData = (compliance: Record<string, boolean>) => {
    const complianceInfo: Record<string, { name: string; description: string }> = {
      hipaa: { name: 'HIPAA', description: 'Health Insurance Portability and Accountability Act' },
      gdpr: { name: 'GDPR', description: 'General Data Protection Regulation' },
      hitech: { name: 'HITECH', description: 'Health Information Technology for Economic and Clinical Health Act' },
      '21_cfr_part_11': { name: '21 CFR Part 11', description: 'FDA Electronic Records and Signatures' }
    };
    
    return Object.entries(compliance).map(([key, value]) => ({
      key,
      name: complianceInfo[key]?.name || key.toUpperCase(),
      description: complianceInfo[key]?.description || '',
      compliant: value
    }));
  };

  // Helper function to format vital signs data
  const formatVitalSignsData = (vitalSigns: Record<string, any>) => {
    const vitalSignsInfo: Record<string, { name: string; description: string }> = {
      ecg: { name: 'ECG', description: 'Electrocardiogram monitoring' },
      spo2: { name: 'SpO2', description: 'Blood oxygen saturation' },
      temperature: { name: 'Temperature', description: 'Body temperature monitoring' },
      blood_pressure: { name: 'Blood Pressure', description: 'Blood pressure monitoring' },
      heart_rate: { name: 'Heart Rate', description: 'Heart rate monitoring' },
      respiratory_rate: { name: 'Respiratory Rate', description: 'Breathing rate monitoring' }
    };
    
    return vitalSignsInfo;
  };

  const renderIndustryInformation = () => {
    const industryType = deviceToUse.metadata?.industry || (deviceToUse as any).industry;
    const industryData = deviceToUse.metadata?.industrySpecificData || (deviceToUse as any).industrySpecificData;

    if (!industryType || !industryData) {
      return null;
    }

    // Healthcare specific rendering
    if (industryType === 'health_medical') {
      return (
        <div className="space-y-6">
          {/* Basic Industry Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
              <dd className="text-sm mt-1">
                <Badge variant="outline" className="gap-1">
                  <Heart className="h-3 w-3" />
                  Healthcare & Medical
                </Badge>
              </dd>
            </div>
          </div>

          {/* Compliance Information */}
          {industryData.compliance && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Compliance Standards</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(formatComplianceData(industryData.compliance)).map(([key, info]) => (
                  <div key={key} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
                    {industryData.compliance[key] ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                    <div>
                      <p className="text-sm font-medium">{info.name}</p>
                      <p className="text-xs text-muted-foreground">{info.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Vital Signs Configuration */}
          {industryData.vitalSigns && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Vital Signs Monitoring</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(formatVitalSignsData(industryData.vitalSigns)).map(([key, info]) => (
                  <div key={key} className="p-3 rounded-lg border bg-card">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium">{info.name}</span>
                      <Badge variant={industryData.vitalSigns[key]?.enabled ? 'default' : 'secondary'}>
                        {industryData.vitalSigns[key]?.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{info.description}</p>
                    {industryData.vitalSigns[key]?.enabled && industryData.vitalSigns[key]?.config && (
                      <div className="mt-2 text-xs text-muted-foreground">
                        <p>Range: {industryData.vitalSigns[key].config.normalRange?.min} - {industryData.vitalSigns[key].config.normalRange?.max} {industryData.vitalSigns[key].config.unit}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Additional Healthcare Fields */}
          {(industryData.fdaClass || industryData.clinicalUse || industryData.patientData) && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Medical Device Information</h4>
              <div className="space-y-2">
                {industryData.fdaClass && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">FDA Classification</span>
                    <Badge>Class {industryData.fdaClass}</Badge>
                  </div>
                )}
                {industryData.clinicalUse && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Clinical Use</span>
                    <span className="text-sm">{industryData.clinicalUse}</span>
                  </div>
                )}
                {industryData.patientData && (
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Patient Data Handling</span>
                    <Badge variant="outline">{industryData.patientData}</Badge>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Smart City specific rendering
    if (industryType === 'smart_city') {
      return (
        <div className="space-y-6">
          {/* Basic Industry Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
              <dd className="text-sm mt-1">
                <Badge variant="outline" className="gap-1">
                  <Building className="h-3 w-3" />
                  Smart City & Building
                </Badge>
              </dd>
            </div>
          </div>

          {/* Building & Infrastructure */}
          {industryData.buildingAutomation && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Building Automation</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {industryData.buildingAutomation.systems && industryData.buildingAutomation.systems.map((system: string, idx: number) => (
                  <Badge key={idx} variant="secondary" className="justify-center">
                    {system.toUpperCase()}
                  </Badge>
                ))}
              </div>
              {industryData.buildingAutomation.protocol && (
                <div className="mt-2">
                  <span className="text-sm text-muted-foreground">Protocol: </span>
                  <Badge variant="outline">{industryData.buildingAutomation.protocol}</Badge>
                </div>
              )}
            </div>
          )}

          {/* City Services Integration */}
          {industryData.cityServiceIntegration && (
            <div>
              <h4 className="text-sm font-semibold mb-3">City Service Integration</h4>
              <div className="space-y-2">
                {industryData.cityServiceIntegration.publicTransit && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Public Transit Integration</span>
                  </div>
                )}
                {industryData.cityServiceIntegration.emergencyServices && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Emergency Services Connected</span>
                  </div>
                )}
                {industryData.cityServiceIntegration.utilityMetering && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Utility Metering Integrated</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Mesh Network Configuration */}
          {industryData.meshNetwork && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Mesh Network</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Network Type</span>
                  <p className="text-sm font-medium">{industryData.meshNetwork.type}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Max Hops</span>
                  <p className="text-sm font-medium">{industryData.meshNetwork.maxHops}</p>
                </div>
                {industryData.meshNetwork.selfHealing && (
                  <div className="col-span-2">
                    <Badge variant="outline" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Self-Healing Enabled
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Industry 4.0 specific rendering
    if (industryType === 'industry_40') {
      return (
        <div className="space-y-6">
          {/* Basic Industry Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
              <dd className="text-sm mt-1">
                <Badge variant="outline" className="gap-1">
                  <Factory className="h-3 w-3" />
                  Industry 4.0
                </Badge>
              </dd>
            </div>
          </div>

          {/* OEE Metrics */}
          {industryData.oeeMetrics && (
            <div>
              <h4 className="text-sm font-semibold mb-3">OEE Performance Metrics</h4>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 rounded-lg border">
                  <p className="text-2xl font-bold text-green-600">{industryData.oeeMetrics.availability || 0}%</p>
                  <p className="text-xs text-muted-foreground">Availability</p>
                </div>
                <div className="text-center p-3 rounded-lg border">
                  <p className="text-2xl font-bold text-blue-600">{industryData.oeeMetrics.performance || 0}%</p>
                  <p className="text-xs text-muted-foreground">Performance</p>
                </div>
                <div className="text-center p-3 rounded-lg border">
                  <p className="text-2xl font-bold text-purple-600">{industryData.oeeMetrics.quality || 0}%</p>
                  <p className="text-xs text-muted-foreground">Quality</p>
                </div>
              </div>
              <div className="mt-2 text-center">
                <span className="text-sm text-muted-foreground">Overall OEE: </span>
                <Badge variant={industryData.oeeMetrics.overall >= 85 ? 'default' : industryData.oeeMetrics.overall >= 65 ? 'secondary' : 'destructive'}>
                  {industryData.oeeMetrics.overall || 0}%
                </Badge>
              </div>
            </div>
          )}

          {/* ISA-95 Hierarchy */}
          {industryData.isa95Level !== undefined && (
            <div>
              <h4 className="text-sm font-semibold mb-3">ISA-95 Hierarchy</h4>
              <div className="flex items-center gap-2">
                <Badge>Level {industryData.isa95Level}</Badge>
                <span className="text-sm text-muted-foreground">
                  {industryData.isa95Level === 0 ? 'Process' :
                   industryData.isa95Level === 1 ? 'Basic Control' :
                   industryData.isa95Level === 2 ? 'Supervisory Control' :
                   industryData.isa95Level === 3 ? 'Manufacturing Operations' :
                   industryData.isa95Level === 4 ? 'Business Planning' : 'Unknown'}
                </span>
              </div>
            </div>
          )}

          {/* Security Zones */}
          {industryData.securityZones && industryData.securityZones.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Security Zones (IEC 62443)</h4>
              <div className="space-y-2">
                {industryData.securityZones.map((zone: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
                    <span className="text-sm font-medium">{zone.name}</span>
                    <Badge variant={zone.level === 'critical' ? 'destructive' : zone.level === 'high' ? 'default' : 'secondary'}>
                      {zone.level}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Smart Energy specific rendering
    if (industryType === 'smart_energy') {
      return (
        <div className="space-y-6">
          {/* Basic Industry Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
              <dd className="text-sm mt-1">
                <Badge variant="outline" className="gap-1">
                  <Zap className="h-3 w-3" />
                  Smart Energy
                </Badge>
              </dd>
            </div>
          </div>

          {/* Grid Integration */}
          {industryData.gridIntegration && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Grid Integration</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Connection Type</span>
                  <p className="text-sm font-medium">{industryData.gridIntegration.connectionType}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Voltage Level</span>
                  <p className="text-sm font-medium">{industryData.gridIntegration.voltageLevel} V</p>
                </div>
                {industryData.gridIntegration.bidirectional && (
                  <div className="col-span-2">
                    <Badge variant="outline" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Bidirectional Power Flow
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* DER Capabilities */}
          {industryData.derCapabilities && (
            <div>
              <h4 className="text-sm font-semibold mb-3">DER Capabilities</h4>
              <div className="space-y-2">
                {industryData.derCapabilities.voltageRegulation && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Voltage Regulation</span>
                  </div>
                )}
                {industryData.derCapabilities.frequencySupport && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Frequency Support</span>
                  </div>
                )}
                {industryData.derCapabilities.blackStart && (
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span className="text-sm">Black Start Capability</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Metering Information */}
          {industryData.meteringInfo && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Metering Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Meter Type</span>
                  <p className="text-sm font-medium">{industryData.meteringInfo.type}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Accuracy Class</span>
                  <Badge>{industryData.meteringInfo.accuracyClass}</Badge>
                </div>
                {industryData.meteringInfo.tariffSupport && (
                  <div className="col-span-2">
                    <span className="text-sm text-muted-foreground">Supported Tariffs: </span>
                    {industryData.meteringInfo.tariffSupport.map((tariff: string, idx: number) => (
                      <Badge key={idx} variant="secondary" className="ml-1">
                        {tariff}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Smart Farm specific rendering
    if (industryType === 'smart_farm') {
      return (
        <div className="space-y-6">
          {/* Basic Industry Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
              <dd className="text-sm mt-1">
                <Badge variant="outline" className="gap-1">
                  <Leaf className="h-3 w-3" />
                  Smart Agriculture
                </Badge>
              </dd>
            </div>
          </div>

          {/* ISOBUS Information */}
          {industryData.isobusInfo && (
            <div>
              <h4 className="text-sm font-semibold mb-3">ISOBUS Configuration</h4>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm text-muted-foreground">Function</span>
                  <p className="text-sm font-medium">{industryData.isobusInfo.function}</p>
                </div>
                <div>
                  <span className="text-sm text-muted-foreground">Version</span>
                  <Badge>{industryData.isobusInfo.version}</Badge>
                </div>
                {industryData.isobusInfo.certified && (
                  <div className="col-span-2">
                    <Badge variant="outline" className="gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      ISOBUS Certified
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Agricultural Operations */}
          {industryData.operations && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Agricultural Operations</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {industryData.operations.planting && (
                  <Badge variant="secondary" className="justify-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Planting
                  </Badge>
                )}
                {industryData.operations.irrigation && (
                  <Badge variant="secondary" className="justify-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Irrigation
                  </Badge>
                )}
                {industryData.operations.fertilization && (
                  <Badge variant="secondary" className="justify-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Fertilization
                  </Badge>
                )}
                {industryData.operations.harvesting && (
                  <Badge variant="secondary" className="justify-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Harvesting
                  </Badge>
                )}
                {industryData.operations.spraying && (
                  <Badge variant="secondary" className="justify-center gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Spraying
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Environmental Monitoring */}
          {industryData.environmentalSensors && (
            <div>
              <h4 className="text-sm font-semibold mb-3">Environmental Sensors</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {industryData.environmentalSensors.soilMoisture && (
                  <div className="p-2 rounded-lg bg-muted/50 text-center">
                    <p className="text-sm font-medium">Soil Moisture</p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                )}
                {industryData.environmentalSensors.soilPH && (
                  <div className="p-2 rounded-lg bg-muted/50 text-center">
                    <p className="text-sm font-medium">Soil pH</p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                )}
                {industryData.environmentalSensors.temperature && (
                  <div className="p-2 rounded-lg bg-muted/50 text-center">
                    <p className="text-sm font-medium">Temperature</p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                )}
                {industryData.environmentalSensors.humidity && (
                  <div className="p-2 rounded-lg bg-muted/50 text-center">
                    <p className="text-sm font-medium">Humidity</p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                )}
                {industryData.environmentalSensors.windSpeed && (
                  <div className="p-2 rounded-lg bg-muted/50 text-center">
                    <p className="text-sm font-medium">Wind Speed</p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Default rendering for unknown industries
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <dt className="text-sm font-medium text-muted-foreground">Industry Type</dt>
            <dd className="text-sm mt-1">
              <Badge variant="outline">{getIndustryDisplayName(industryType)}</Badge>
            </dd>
          </div>
        </div>
        {industryData && (
          <div>
            <dt className="text-sm font-medium text-muted-foreground mb-2">Industry Data</dt>
            <dd className="text-sm mt-1">
              <pre className="text-xs bg-muted p-2 rounded overflow-auto max-h-40">
                {JSON.stringify(industryData, null, 2)}
              </pre>
            </dd>
          </div>
        )}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className={cn(
        "transition-all duration-300 z-[100]",
        (activeTab === 'telemetry' || activeTab === 'telemetry_beta' || activeTab === 'console')
          ? "max-h-[95vh] sm:max-h-[90vh] md:max-h-[85vh] overflow-y-auto w-[95vw] sm:w-[90vw] md:w-[85vw] lg:w-[80vw] xl:w-[75vw] 2xl:w-[70vw] max-w-[1400px]"
          : "max-h-[90vh] overflow-y-auto sm:max-w-[720px] md:max-w-[840px] lg:max-w-[960px]"
      )}>
        <DialogHeader>
          <DialogTitle>Device Details</DialogTitle>
          <DialogDescription>
            Complete information about {deviceToUse.name}
            {deviceLoading && <span className="ml-2 text-muted-foreground">(Loading detailed data...)</span>}
          </DialogDescription>
        </DialogHeader>
        
        <Tabs 
          value={activeTab}
          onValueChange={setActiveTab}
          className="mt-4"
        >
          <TabsList className="inline-flex h-10 items-center justify-start rounded-md bg-muted p-1 text-muted-foreground w-full overflow-x-auto">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="telemetry">Telemetry</TabsTrigger>
            <TabsTrigger value="dataschema">Data Schema</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="credentials">Credentials</TabsTrigger>
            <TabsTrigger value="qrcode" className="gap-1.5 px-4">
              <QrCode className="h-4 w-4" />
              <span className="whitespace-nowrap">QR & Provisioning</span>
            </TabsTrigger>
            <TabsTrigger value="console" className="gap-1.5 px-4">
              <Terminal className="h-4 w-4" />
              <span className="whitespace-nowrap">Console</span>
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4">
            {/* Device Image */}
            {deviceToUse.metadata?.devicePicture && (
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <img
                    src={deviceToUse.metadata.devicePicture}
                    alt={deviceToUse.name}
                    className="h-32 w-auto rounded-lg object-contain border-2 border-gray-200 shadow-md"
                    onError={(e) => {
                      // Hide image if it fails to load
                      const target = e.target as HTMLImageElement;
                      target.parentElement?.classList.add('hidden');
                    }}
                  />
                </div>
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Device Information</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Type</span>
                      <Badge variant="secondary">{deviceToUse.type}</Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Serial Number</span>
                      <span
                        className="text-sm font-medium font-mono break-all max-w-[260px] text-right"
                        title={deviceToUse.serialNumber}
                      >
                        {deviceToUse.serialNumber}
                      </span>
                    </div>
                    {deviceToUse.metadata?.factory_uid && (
                      <div className="flex justify-between">
                        <span className="text-sm">Factory UID</span>
                        <span
                          className="text-sm font-mono break-all max-w-[260px] text-right text-muted-foreground"
                          title={deviceToUse.metadata.factory_uid}
                        >
                          {deviceToUse.metadata.factory_uid}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-sm">Firmware</span>
                      <span className="text-sm font-medium">{deviceToUse.firmwareVersion}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Protocol</span>
                      <span className="text-sm font-medium">
                        {deviceToUse.metadata.protocol
                          || (Array.isArray(deviceToUse.metadata?.protocols) ? deviceToUse.metadata.protocols.join(', ') : '')
                          || '-'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Authentication Mode</span>
                      <span className="text-sm font-medium">
                        {(() => {
                          const rawProto = deviceToUse.metadata?.protocol
                            || (Array.isArray(deviceToUse.metadata?.protocols) ? deviceToUse.metadata.protocols[0] : '');
                          const proto = (rawProto || '').toUpperCase();
                          const authMode = deviceToUse.auth_mode || '';

                          if (authMode === 'mtls') {
                            const label = proto.startsWith('MQTT') ? 'MQTTs' : (proto || 'UNKNOWN');
                            return `${label} with mTLS`;
                          } else if (authMode === 'server_tls') {
                            if (proto.startsWith('MQTT')) {
                              return `MQTTs with Username/Password`;
                            } else if (proto.startsWith('HTTP')) {
                              return `HTTPS with Server-TLS + API Key`;
                            } else {
                              return `${proto || 'UNKNOWN'} with Server-TLS`;
                            }
                          } else if (authMode === 'api_key') {
                            return `${proto || 'HTTPS'} with API Key`;
                          } else {
                            return authMode ? authMode.toUpperCase() : (proto || '-');
                          }
                        })()}
                      </span>
                    </div>
                    {(deviceToUse as any).trustm_uid && (
                      <div className="flex justify-between items-start">
                        <span className="text-sm">Trust M UID</span>
                        <span
                          className="text-xs font-mono break-all max-w-[260px] text-right text-muted-foreground"
                          title={(deviceToUse as any).trustm_uid}
                        >
                          {(deviceToUse as any).trustm_uid}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Manufacturer</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Company</span>
                      <span className="text-sm font-medium">{deviceToUse.metadata.manufacturer || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Model</span>
                      <span className="text-sm font-medium">{deviceToUse.metadata.model || '-'}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Connection Details</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Status</span>
                      <div className="flex items-center gap-2">
                        <div className={cn(
                          "h-2 w-2 rounded-full",
                          deviceToUse.status === 'online' ? 'bg-green-600' :
                          deviceToUse.status === 'offline' ? 'bg-gray-400' :
                          'bg-red-600'
                        )} />
                        <span className={cn("text-sm font-medium", getStatusColor(deviceToUse.status))}>
                          {deviceToUse.status}
                        </span>
                      </div>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Last Seen</span>
                      <span className="text-sm font-medium">
                        {(() => {
                          const ts = deviceToUse.lastSeen
                            || (deviceToUse as any).last_seen
                            || (deviceToUse as any).last_activity;
                          if (!ts) return 'Never';
                          try { return format(new Date(ts), 'MMM d, HH:mm'); } catch { return 'Never'; }
                        })()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">IP Address</span>
                      <span className="text-sm font-medium">{deviceToUse.metadata.ipAddress || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">MAC Address</span>
                      <span className="text-sm font-medium">{deviceToUse.metadata.macAddress || '-'}</span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">Location</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Name</span>
                      <span className="text-sm font-medium">{deviceToUse.location?.name || '-'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Organization</span>
                      <span className="text-sm font-medium">{deviceToUse.organizationName}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">Tags</h4>
              <div className="flex flex-wrap gap-2">
                {deviceToUse.tags && deviceToUse.tags.length > 0 ? (
                  deviceToUse.tags.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">No tags</span>
                )}
              </div>
            </div>

            {/* Industry Specific Data */}
            {deviceToUse.metadata?.industry && (
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Industry Information</h4>
                {renderIndustryInformation()}
              </div>
            )}
          </TabsContent>
          
          <TabsContent value="telemetry" className="space-y-4">
            <TelemetryDashboard
              devices={deviceToUse ? [deviceToUse] : []}
              isTabActive={activeTab === 'telemetry'}
            />
          </TabsContent>
          
          <TabsContent value="dataschema" className="space-y-4">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="h-5 w-5" />
                    Telemetry Data Schema
                  </CardTitle>
                  <CardDescription>
                    Current data structure for telemetry sent by this device
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {deviceToUse?.telemetrySchema?.schema && Object.keys(deviceToUse.telemetrySchema.schema).length > 0 ? (
                    <div className="space-y-4">
                      {/* Schema Metadata */}
                      {deviceToUse.telemetrySchema.metadata && (
                        <div className="flex items-center gap-2 mb-4">
                          {deviceToUse.telemetrySchema.metadata.templateName && (
                            <Badge variant="secondary">
                              {deviceToUse.telemetrySchema.metadata.templateName}
                            </Badge>
                          )}
                          {deviceToUse.telemetrySchema.metadata.customized && (
                            <Badge variant="outline">Customized</Badge>
                          )}
                          {deviceToUse.telemetrySchema.metadata.updatedAt && (
                            <span className="text-sm text-muted-foreground">
                              Updated: {format(new Date(deviceToUse.telemetrySchema.metadata.updatedAt), 'MMM dd, yyyy')}
                            </span>
                          )}
                        </div>
                      )}
                      
                      {/* Schema Properties Display */}
                      <div className="border rounded-lg p-4 bg-muted/30">
                        <div className="font-medium text-sm mb-3">Schema Properties:</div>
                        <div className="font-mono text-sm space-y-1">
                          {Object.entries(deviceToUse.telemetrySchema.schema.properties || {}).map(([key, prop]: [string, any]) => {
                            const isRequired = deviceToUse.telemetrySchema.schema.required?.includes(key);
                            const type = prop.type || 'any';
                            return (
                              <div key={key} className="text-muted-foreground">
                                <span className="text-foreground font-medium">{key}</span>
                                <span>:</span>
                                <span className="text-blue-600 dark:text-blue-400">{type}</span>
                                {isRequired && <span className="text-red-600 dark:text-red-400">required</span>}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                      
                      {/* JSON Schema View */}
                      <div className="space-y-2">
                        <div className="font-medium text-sm">JSON Schema:</div>
                        <div className="bg-gray-950 rounded-lg p-4 overflow-auto">
                          <pre className="text-xs text-gray-100 font-mono">
                            {JSON.stringify(deviceToUse.telemetrySchema.schema, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <Alert>
                      <Database className="h-4 w-4" />
                      <AlertTitle>No Telemetry Schema Defined</AlertTitle>
                      <AlertDescription>
                        This device does not have a telemetry data schema configured. Edit the device to define the data structure using the Schema Assistant.
                      </AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>

              {(deviceToUse?.type === 'actuator' || deviceToUse?.type === 'controller') && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Database className="h-5 w-5" />
                      Actuator Command Schema
                    </CardTitle>
                    <CardDescription>
                      Current command structure for controlling this device
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {deviceToUse?.actuatorSchema?.schema && Object.keys(deviceToUse.actuatorSchema.schema).length > 0 ? (
                      <div className="space-y-4">
                        {/* Schema Metadata */}
                        {deviceToUse.actuatorSchema.metadata && (
                          <div className="flex items-center gap-2 mb-4">
                            {deviceToUse.actuatorSchema.metadata.templateName && (
                              <Badge variant="secondary">
                                {deviceToUse.actuatorSchema.metadata.templateName}
                              </Badge>
                            )}
                            {deviceToUse.actuatorSchema.metadata.customized && (
                              <Badge variant="outline">Customized</Badge>
                            )}
                            {deviceToUse.actuatorSchema.metadata.updatedAt && (
                              <span className="text-sm text-muted-foreground">
                                Updated: {format(new Date(deviceToUse.actuatorSchema.metadata.updatedAt), 'MMM dd, yyyy')}
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Schema Properties Display */}
                        <div className="border rounded-lg p-4 bg-muted/30">
                          <div className="font-medium text-sm mb-3">Command Properties:</div>
                          <div className="font-mono text-sm space-y-1">
                            {Object.entries(deviceToUse.actuatorSchema.schema.properties || {}).map(([key, prop]: [string, any]) => {
                              const isRequired = deviceToUse.actuatorSchema.schema.required?.includes(key);
                              const type = prop.type || 'any';
                              return (
                                <div key={key} className="text-muted-foreground">
                                  <span className="text-foreground font-medium">{key}</span>
                                  <span>:</span>
                                  <span className="text-blue-600 dark:text-blue-400">{type}</span>
                                  {isRequired && <span className="text-red-600 dark:text-red-400">required</span>}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                        
                        {/* JSON Schema View */}
                        <div className="space-y-2">
                          <div className="font-medium text-sm">JSON Schema:</div>
                          <div className="bg-gray-950 rounded-lg p-4 overflow-auto">
                            <pre className="text-xs text-gray-100 font-mono">
                              {JSON.stringify(deviceToUse.actuatorSchema.schema, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <Alert>
                        <Database className="h-4 w-4" />
                        <AlertTitle>No Actuator Schema Defined</AlertTitle>
                        <AlertDescription>
                          This actuator/controller does not have a command schema configured. Edit the device to define the command structure using the Schema Assistant.
                        </AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="security" className="space-y-4">
            {(() => {
              console.log('=== SECURITY TAB RENDER DEBUG ===');
              console.log('certificateLoading:', certificateLoading);
              console.log('certificateData:', certificateData);
              console.log('deviceToUse.certificate:', deviceToUse.certificate);
              console.log('deviceToUse.certificate_status:', (deviceToUse as any).certificate_status);
              console.log('deviceToUse object:', deviceToUse);
              return null;
            })()}
            {certificateLoading ? (
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-center">
                    <div className="text-sm text-muted-foreground">Loading certificate information...</div>
                  </div>
                </CardContent>
              </Card>
            ) : certificateData?.exists || deviceToUse.certificate || (deviceToUse as any).certificate_status ? (
              <Card>
                <CardHeader>
                  <CardTitle>Device Certificate</CardTitle>
                  <CardDescription>PKI certificate details from TESA Vault</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Key className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">Certificate Status</p>
                        <p className="text-sm text-muted-foreground">
                          Serial: {certificateData?.certificate?.serial_number || deviceToUse.certificate?.serial || (deviceToUse as any).serial_number || deviceToUse.serialNumber || deviceToUse.device_id || deviceToUse.id || 'N/A'}
                        </p>
                      </div>
                    </div>
                    <Badge variant={
                      (certificateData?.certificate?.status || deviceToUse.certificate?.status || (deviceToUse as any).certificate_status) === 'active' || 
                      (certificateData?.certificate?.status || deviceToUse.certificate?.status || (deviceToUse as any).certificate_status) === 'valid' ? 'default' :
                      (certificateData?.certificate?.status || deviceToUse.certificate?.status || (deviceToUse as any).certificate_status) === 'expiring' ? 'secondary' :
                      'destructive'
                    }>
                      {certificateData?.certificate?.status || deviceToUse.certificate?.status || (deviceToUse as any).certificate_status || 'Unknown'}
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Algorithm</span>
                      <span className="text-sm font-medium">
                        {(() => {
                          console.log('=== ALGORITHM DEBUG ===');
                          console.log('certificateData?.certificate?.algorithm:', certificateData?.certificate?.algorithm);
                          console.log('deviceToUse.certificate?.algorithm:', deviceToUse.certificate?.algorithm);
                          console.log('(deviceToUse as any).certificate_info?.algorithm:', (deviceToUse as any).certificate_info?.algorithm);
                          console.log('(deviceToUse as any).certificate_info?.key_algorithm:', (deviceToUse as any).certificate_info?.key_algorithm);
                          console.log('(deviceToUse as any).certificate_algorithm:', (deviceToUse as any).certificate_algorithm);
                          console.log('Full deviceToUse:', deviceToUse);
                          console.log('Full certificateData:', certificateData);
                          console.log('All device keys:', Object.keys(deviceToUse));
                          
                          // Check all possible locations for algorithm
                          const algorithm = certificateData?.certificate?.algorithm || 
                                          deviceToUse.certificate?.algorithm || 
                                          (deviceToUse as any).certificate_info?.algorithm ||
                                          (deviceToUse as any).certificate_info?.key_algorithm ||
                                          (deviceToUse as any).certificate_algorithm ||
                                          (deviceToUse as any).algorithm ||
                                          null;
                          
                          // Check for both null/undefined AND empty string
                          if (algorithm && algorithm.trim() !== '') {
                            // Format algorithm properly
                            const algoLower = algorithm.toLowerCase();
                            if (algoLower === 'ecc-p256' || algoLower === 'ecc p-256') {
                              return 'ECC P-256';
                            } else if (algoLower === 'ecc-p384' || algoLower === 'ecc p-384') {
                              return 'ECC P-384';
                            } else if (algoLower === 'rsa-2048' || algoLower === 'rsa 2048') {
                              return 'RSA 2048';
                            } else if (algoLower === 'rsa-3072' || algoLower === 'rsa 3072') {
                              return 'RSA 3072';
                            } else if (algoLower === 'rsa-4096' || algoLower === 'rsa 4096') {
                              return 'RSA 4096';
                            } else {
                              // Return the algorithm as-is but uppercase
                              return algorithm.toUpperCase().replace(/-/g, ' ');
                            }
                          }
                          
                          return 'Not available';
                        })()}
                      </span>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Valid From</span>
                      <span className="text-sm font-medium">
                        {(() => {
                          console.log('=== VALID FROM DEBUG ===');
                          console.log('certificateData?.certificate?.validFrom:', certificateData?.certificate?.validFrom);
                          console.log('deviceToUse.certificate?.validFrom:', deviceToUse.certificate?.validFrom);
                          console.log('(deviceToUse as any).certificate_issued_at:', (deviceToUse as any).certificate_issued_at);
                          console.log('(deviceToUse as any).created_at:', (deviceToUse as any).created_at);
                          
                          if (certificateData?.certificate?.validFrom) {
                            const date = new Date(certificateData.certificate.validFrom);
                            console.log('Using certificateData validFrom, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if (deviceToUse.certificate?.validFrom) {
                            const date = new Date(deviceToUse.certificate.validFrom);
                            console.log('Using deviceToUse.certificate validFrom, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if ((deviceToUse as any).certificate_issued_at) {
                            const date = new Date((deviceToUse as any).certificate_issued_at);
                            console.log('Using deviceToUse.certificate_issued_at, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if ((deviceToUse as any).created_at) {
                            const date = new Date((deviceToUse as any).created_at);
                            console.log('Using deviceToUse.created_at as fallback, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else {
                            console.log('No valid from date found');
                            return 'Not available';
                          }
                        })()}
                      </span>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Valid Until</span>
                      <span className="text-sm font-medium">
                        {(() => {
                          console.log('=== VALID TO DEBUG ===');
                          console.log('certificateData?.certificate?.validTo:', certificateData?.certificate?.validTo);
                          console.log('deviceToUse.certificate?.validTo:', deviceToUse.certificate?.validTo);
                          console.log('deviceToUse.certificate?.expiresAt:', deviceToUse.certificate?.expiresAt);
                          console.log('(deviceToUse as any).certificate_expires_at:', (deviceToUse as any).certificate_expires_at);
                          
                          if (certificateData?.certificate?.validTo) {
                            const date = new Date(certificateData.certificate.validTo);
                            console.log('Using certificateData validTo, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if (deviceToUse.certificate?.validTo) {
                            const date = new Date(deviceToUse.certificate.validTo);
                            console.log('Using deviceToUse.certificate validTo, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if (deviceToUse.certificate?.expiresAt) {
                            const date = new Date(deviceToUse.certificate.expiresAt);
                            console.log('Using deviceToUse.certificate.expiresAt, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else if ((deviceToUse as any).certificate_expires_at) {
                            const date = new Date((deviceToUse as any).certificate_expires_at);
                            console.log('Using deviceToUse.certificate_expires_at, parsed date:', date);
                            return format(date, 'MMM dd, yyyy');
                          } else {
                            console.log('No valid to date found');
                            return 'Not available';
                          }
                        })()}
                      </span>
                    </div>
                    <div className="flex justify-between py-2 border-b">
                      <span className="text-sm text-muted-foreground">Issuer</span>
                      <span className="text-sm font-medium">
                        {certificateData?.certificate?.issuer || 
                         deviceToUse.certificate?.issuer || 
                         'TESA IoT Platform CA'}
                      </span>
                    </div>
                    {certificateData?.certificate?.subject && (
                      <div className="flex justify-between py-2 border-b">
                        <span className="text-sm text-muted-foreground">Subject</span>
                        <span className="text-sm font-medium">{certificateData.certificate.subject}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Shield className="h-4 w-4 mr-2" />
                      View Certificate
                    </Button>
                    {onRenewCertificate && deviceToUse && (
                      <Button 
                        variant="outline" 
                        size="sm"
                        onClick={() => onRenewCertificate(deviceToUse)}
                        className="text-blue-600 hover:text-blue-700"
                      >
                        <RefreshCw className="h-4 w-4 mr-2" />
                        Renew Certificate
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>No Certificate</AlertTitle>
                <AlertDescription>
                  This device does not have a security certificate. Generate one to enable secure communication.
                </AlertDescription>
              </Alert>
            )}
          </TabsContent>

          <TabsContent value="qrcode" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Package className="h-5 w-5" />
                  Device Provisioning Information
                </CardTitle>
                <CardDescription>
                  QR code and provisioning details for Trust M devices
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Provisioning Information */}
                {(deviceToUse as any).trustm_uid && (
                  <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">Trust M UID</dt>
                      <dd className="mt-1 text-sm font-mono break-all">{(deviceToUse as any).trustm_uid}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">Device ID</dt>
                      <dd className="mt-1 text-sm font-mono">{deviceToUse.device_id || deviceToUse.id}</dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">Authentication Mode</dt>
                      <dd className="mt-1 text-sm">
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          mTLS (Trust M)
                        </Badge>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-sm font-medium text-muted-foreground">Provisioning Status</dt>
                      <dd className="mt-1 text-sm">
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Provisioned
                        </Badge>
                      </dd>
                    </div>
                  </div>
                )}

                {/* QR Code Section */}
                <div className="border-t pt-4">
                  <DeviceQRCode
                    deviceId={deviceToUse.device_id || deviceToUse.id}
                    trustmUid={(deviceToUse as any).trustm_uid}
                  />
                </div>

                {/* Provisioning Instructions */}
                {(deviceToUse as any).trustm_uid && (
                  <Alert>
                    <Shield className="h-4 w-4" />
                    <AlertTitle>Trust M Provisioning</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1 text-sm mt-2">
                        <li>QR code contains both Trust M UID and Device ID</li>
                        <li>Use the QR scanner to retrieve device information</li>
                        <li>Device authenticates using hardware-backed certificate</li>
                        <li>No password or token required for mTLS authentication</li>
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="console" className="space-y-4">
            {/* Console Tab - Device Logs Improvement Feature (v2026.01) */}
            {/* Section 1: CSR Workflow Status */}
            <CSRWorkflowWidget deviceId={deviceToUse.device_id || deviceToUse.id} />

            {/* Section 2: Real-time Enhanced Debug Console */}
            <RealtimeDebugConsole
              deviceId={deviceToUse.device_id || deviceToUse.id}
              className="h-[400px]"
            />

            {/* Section 3: Traditional Logs (Legacy) */}
            <Card>
              <CardHeader>
                <CardTitle>Device Logs & Data Validation</CardTitle>
                <CardDescription>Data validation errors, connectivity warnings, and system messages</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-950 rounded-lg p-4 h-[400px] overflow-y-auto">
                  {logsLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-sm text-muted-foreground">Loading device logs...</div>
                    </div>
                  ) : deviceLogs.length > 0 ? (
                    <div className="space-y-2 font-mono text-xs">
                      {deviceLogs.map((log, index) => {
                        const logTime = log.timestamp ? new Date(log.timestamp) : new Date();
                        // Enhanced color coding for data validation and connectivity issues
                        const isDataValidationError = log.message?.toLowerCase().includes('schema') || 
                                                    log.message?.toLowerCase().includes('validation') ||
                                                    log.message?.toLowerCase().includes('invalid data') ||
                                                    log.log_type === 'telemetry' && log.level === 'ERROR';
                        const isConnectivityIssue = log.message?.toLowerCase().includes('connect') ||
                                                  log.message?.toLowerCase().includes('mqtt') ||
                                                  log.message?.toLowerCase().includes('network') ||
                                                  log.message?.toLowerCase().includes('timeout') ||
                                                  log.message?.toLowerCase().includes('certificate') ||
                                                  log.log_type === 'connection';
                        const isSecurityIssue = log.message?.toLowerCase().includes('auth') ||
                                              log.message?.toLowerCase().includes('certificate') ||
                                              log.message?.toLowerCase().includes('security') ||
                                              log.log_type === 'security';
                        
                        let levelColor = {
                          'INFO': 'text-green-400',
                          'WARNING': 'text-yellow-400',
                          'WARN': 'text-yellow-400',
                          'ERROR': 'text-red-400',
                          'DEBUG': 'text-gray-400',
                          'CRITICAL': 'text-red-600'
                        }[log.level] || 'text-blue-400';
                        
                        // Special highlighting for critical issues
                        if (isDataValidationError) levelColor = 'text-orange-400';
                        if (isConnectivityIssue) levelColor = 'text-purple-400';
                        if (isSecurityIssue && log.level === 'ERROR') levelColor = 'text-red-500';
                        
                        return (
                          <div key={log._id || index} className="flex gap-2 items-start">
                            <span className="text-gray-500">{format(logTime, 'HH:mm:ss.SSS')}</span>
                            <span className={levelColor}>[{log.level}]</span>
                            {isDataValidationError && (
                              <span className="text-orange-400 text-xs bg-orange-400/10 px-1 rounded">[DATA]</span>
                            )}
                            {isConnectivityIssue && (
                              <span className="text-purple-400 text-xs bg-purple-400/10 px-1 rounded">[CONN]</span>
                            )}
                            {isSecurityIssue && (
                              <span className="text-red-400 text-xs bg-red-400/10 px-1 rounded">[SEC]</span>
                            )}
                            {log.log_type && !isDataValidationError && !isConnectivityIssue && !isSecurityIssue && (
                              <span className="text-gray-400 text-xs bg-gray-400/10 px-1 rounded">[{log.log_type.toUpperCase()}]</span>
                            )}
                            <span className="text-gray-100 flex-1">{log.message}</span>
                            {log.details && Object.keys(log.details).length > 0 && (
                              <span className="text-gray-500 ml-2">
                                ({Object.entries(log.details)
                                  .filter(([_, v]) => v !== null && v !== undefined)
                                  .map(([k, v]) => `${k}: ${v}`)
                                  .join(', ')})
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-sm text-muted-foreground">No logs available for this device</div>
                    </div>
                  )}
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <div className="text-xs text-muted-foreground">
                    {deviceLogs.length > 0 ? `Showing ${deviceLogs.length} most recent logs` : ''}
                    {logsAutoRefresh && (
                      <span className="ml-2 text-green-400">• Auto-refreshing</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant={logsAutoRefresh ? "default" : "outline"}
                      size="sm"
                      onClick={() => setLogsAutoRefresh(!logsAutoRefresh)}
                    >
                      {logsAutoRefresh ? (
                        <>
                          <Pause className="h-4 w-4 mr-2" />
                          Pause Auto-refresh
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4 mr-2" />
                          Auto-refresh
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => fetchDeviceLogs()}
                      disabled={logsLoading || logsAutoRefresh}
                    >
                      <RefreshCw className={cn("h-4 w-4 mr-2", logsLoading && "animate-spin")} />
                      Refresh Now
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="credentials" className="space-y-4">
            <DeviceCredentialsSection 
              device={deviceToUse}
              defaultInnerTab={credentialsDefaultTab}
              onRegenerateApiKey={async () => {
                try {
                  const deviceId = deviceToUse.device_id || deviceToUse.id;
                  const response = await tesaApi.regenerateDeviceApiKey(deviceId, {
                    reason: 'API key regeneration requested by administrator'
                  });
                  
                  if (response.data.status === 'success') {
                    toast.success('API key regenerated successfully');
                    // Update the device with the new API key
                    if (response.data.api_key) {
                      const updatedDevice = {
                        ...deviceToUse,
                        https_api_key: response.data.api_key,
                        api_key: response.data.api_key
                      };
                      // Update the detailed device state to trigger re-render
                      setDetailedDevice(updatedDevice);
                    }
                  } else {
                    toast.error('Failed to regenerate API key');
                  }
                } catch (error) {
                  console.error('Error regenerating API key:', error);
                  toast.error('Failed to regenerate API key');
                }
              }}
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
