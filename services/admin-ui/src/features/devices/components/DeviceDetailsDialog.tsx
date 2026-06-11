/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Device } from '../types/device.types';
import { Shield, MapPin, Cpu, Clock, Building, Wifi, Activity, QrCode, Download, Share2, Heart, CheckCircle, AlertCircle, Zap, Factory, Leaf, FileCheck, ShieldCheck, XCircle, CheckCircle2, Gauge } from 'lucide-react';
import QRCode from 'qrcode';
import { DeviceCredentialsSection } from './DeviceCredentialsSection';
import { formatLocalDateTime } from '@/utils/dateFormatting';

interface DeviceDetailsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  device: Device | null;
}

// Helper function to get industry icon
const getIndustryIcon = (industry: string) => {
  switch (industry) {
    case 'health_medical':
      return <Heart className="h-5 w-5 text-red-500" />;
    case 'industry_40':
      return <Factory className="h-5 w-5 text-blue-500" />;
    case 'smart_city':
      return <Building className="h-5 w-5 text-purple-500" />;
    case 'smart_energy':
      return <Zap className="h-5 w-5 text-yellow-500" />;
    case 'smart_farm':
      return <Leaf className="h-5 w-5 text-green-500" />;
    default:
      return <FileCheck className="h-5 w-5 text-gray-500" />;
  }
};

// Helper function to get industry display name
const getIndustryDisplayName = (industry: string) => {
  const industryNames: Record<string, string> = {
    health_medical: 'Health & Medical',
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

export const DeviceDetailsDialog: React.FC<DeviceDetailsDialogProps> = ({
  open,
  onOpenChange,
  device,
}) => {
  const [qrCodeUrl, setQrCodeUrl] = React.useState<string>('');
  const [showQrCode, setShowQrCode] = React.useState(false);

  React.useEffect(() => {
    if (device && open) {
      // Generate QR code for device
      const deviceData = {
        id: device.device_id || device.id,
        name: device.name,
        type: device.type,
        org: device.organization_id
      };
      
      QRCode.toDataURL(JSON.stringify(deviceData), {
        width: 200,
        margin: 2,
        color: {
          dark: '#000000',
          light: '#FFFFFF'
        }
      }).then(url => {
        setQrCodeUrl(url);
      }).catch(err => {
        console.error('QR Code generation failed:', err);
      });
    }
  }, [device, open]);

  if (!device) return null;

  const getStatusColor = (status: Device['status']) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'default';
    }
  };

  const renderIndustrySection = () => {
    const industryType = device.metadata?.industry || device.industry;
    const industryData = device.metadata?.industrySpecificData || device.industrySpecificData;

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
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Device Details</span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowQrCode(!showQrCode)}
              >
                <QrCode className="h-4 w-4 mr-1" />
                {showQrCode ? 'Hide' : 'Show'} QR
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  // Export device data
                  const dataStr = JSON.stringify(device, null, 2);
                  const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
                  const exportName = `device-${device.device_id || device.id}.json`;
                  const linkElement = document.createElement('a');
                  linkElement.setAttribute('href', dataUri);
                  linkElement.setAttribute('download', exportName);
                  linkElement.click();
                }}
              >
                <Download className="h-4 w-4 mr-1" />
                Export
              </Button>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-6">
          {/* QR Code Section */}
          {showQrCode && qrCodeUrl && (
            <div className="flex justify-center p-4 border rounded-lg bg-white">
              <div className="text-center">
                <img src={qrCodeUrl} alt="Device QR Code" className="mb-2" />
                <p className="text-sm text-muted-foreground">Scan to get device info</p>
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={() => {
                    const link = document.createElement('a');
                    link.download = `device-qr-${device.device_id || device.id}.png`;
                    link.href = qrCodeUrl;
                    link.click();
                  }}
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download QR
                </Button>
              </div>
            </div>
          )}
          
          {/* Basic Information */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Basic Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 flex items-start gap-4">
                {device.metadata?.devicePicture && (
                  <div className="flex-shrink-0">
                    <img
                      src={device.metadata.devicePicture}
                      alt={device.name}
                      className="h-32 w-auto rounded-lg object-contain border border-gray-200"
                      onError={(e) => {
                        // Hide image if it fails to load
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                      }}
                    />
                  </div>
                )}
                <div className="flex-grow grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Device Name</p>
                    <p className="font-medium">{device.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Device ID</p>
                    <p className="font-mono text-sm">{device.device_id || device.id}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Type</p>
                    <Badge variant="outline">{device.type}</Badge>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <Badge variant={getStatusColor(device.status)}>
                      <Activity className="mr-1 h-3 w-3" />
                      {device.status}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Location & Organization */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Location & Organization</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">
                  <MapPin className="inline-block h-4 w-4 mr-1" />
                  Location
                </p>
                <p className="font-medium">{device.location || 'Not specified'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  <Building className="inline-block h-4 w-4 mr-1" />
                  Organization
                </p>
                <p className="font-medium">{device.organization_id || 'Not assigned'}</p>
              </div>
            </div>
          </div>

          {/* Technical Details */}
          <div>
            <h3 className="text-lg font-semibold mb-3">Technical Details</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">
                  <Cpu className="inline-block h-4 w-4 mr-1" />
                  Firmware Version
                </p>
                <p className="font-medium">{device.firmware_version || device.firmware || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  <Shield className="inline-block h-4 w-4 mr-1" />
                  Certificate Status
                </p>
                <Badge variant={device.certificate_status === 'valid' ? 'success' : 'warning'}>
                  {device.certificate_status || 'None'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  <Clock className="inline-block h-4 w-4 mr-1" />
                  Last Seen
                </p>
                <p className="font-medium">
                  {formatLocalDateTime(device.last_seen || device.lastSeen)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  <Wifi className="inline-block h-4 w-4 mr-1" />
                  Protocol
                </p>
                <p className="font-medium">{device.protocol || 'MQTT'}</p>
              </div>
            </div>
          </div>

          {/* Industry Specific Information */}
          {(device.metadata?.industry || device.industry || device.industrySpecificData) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {getIndustryIcon(device.metadata?.industry || device.industry)}
                  <span>Industry Information</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {renderIndustrySection()}
              </CardContent>
            </Card>
          )}

          {/* Additional Metadata */}
          {device.metadata && Object.keys(device.metadata).filter(key => 
            !['manufacturer', 'model', 'protocol', 'serialNumber', 'ipAddress', 'macAddress', 
             'industry', 'industrySpecificData', 'devicePicture', 'certificateType', 
             'certificate_algorithm'].includes(key)
          ).length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-3">Additional Metadata</h3>
              <div className="bg-muted/50 p-4 rounded-lg">
                <pre className="text-sm">{JSON.stringify(
                  Object.fromEntries(
                    Object.entries(device.metadata).filter(([key]) => 
                      !['manufacturer', 'model', 'protocol', 'serialNumber', 'ipAddress', 'macAddress', 
                       'industry', 'industrySpecificData', 'devicePicture', 'certificateType', 
                       'certificate_algorithm'].includes(key)
                    )
                  ), null, 2
                )}</pre>
              </div>
            </div>
          )}

          {/* Device Credentials Section */}
          <DeviceCredentialsSection 
            device={device}
            onRegenerateApiKey={async () => {
              // TODO: Implement API call to regenerate device API key
              console.log('Regenerating API key for device:', device.device_id);
            }}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
};