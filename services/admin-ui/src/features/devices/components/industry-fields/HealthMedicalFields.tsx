/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Shield, AlertTriangle, Info, Heart, Activity, FileCheck, Globe } from 'lucide-react';
import { IndustrySchema } from '@/services/api/industrySchemaService';

interface HealthMedicalFieldsProps {
  data: any;
  onChange: (data: any) => void;
  errors?: Record<string, string>;
  mode?: 'create' | 'edit';
  schema?: IndustrySchema | null;
}

const HealthMedicalFields: React.FC<HealthMedicalFieldsProps> = ({
  data,
  onChange,
  errors = {},
  mode = 'create',
  schema
}) => {
  const [deviceClass, setDeviceClass] = useState(data.fdaClass || '');

  const handleFieldChange = (field: string, value: any) => {
    onChange({
      ...data,
      [field]: value
    });
  };

  return (
    <div className="space-y-6">
      {/* Regulatory Compliance Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Regulatory Compliance
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="fda-class">FDA Device Classification *</Label>
              <SearchableSelect
                value={deviceClass}
                onValueChange={(value) => {
                  setDeviceClass(value as string);
                  handleFieldChange('fdaClass', value);
                }}
                options={[
                  {
                    value: 'I',
                    label: 'Class I - Low Risk',
                    description: 'General controls, minimal potential for harm',
                    icon: <Shield className="h-4 w-4 text-green-500" />
                  },
                  {
                    value: 'II',
                    label: 'Class II - Moderate Risk',
                    description: 'Special controls, moderate risk to patient',
                    icon: <Shield className="h-4 w-4 text-yellow-500" />
                  },
                  {
                    value: 'III',
                    label: 'Class III - High Risk',
                    description: 'Premarket approval required, high risk',
                    icon: <Shield className="h-4 w-4 text-red-500" />
                  }
                ]}
                placeholder="Select FDA class"
                searchable={false}
                size="md"
              />
              {errors.fdaClass && (
                <p className="text-sm text-red-500 mt-1">{errors.fdaClass}</p>
              )}
            </div>

            <div>
              <Label htmlFor="ce-mark">CE Mark Compliance</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Switch
                  id="ce-mark"
                  checked={data.ceMark || false}
                  onCheckedChange={(checked) => handleFieldChange('ceMark', checked)}
                />
                <Label htmlFor="ce-mark" className="font-normal">
                  Device has CE marking
                </Label>
              </div>
            </div>
          </div>

          {(deviceClass === 'II' || deviceClass === 'III') && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                Class {deviceClass} devices require UDI (Unique Device Identifier) registration
              </AlertDescription>
            </Alert>
          )}

          <div>
            <Label htmlFor="udi">UDI Device Identifier</Label>
            <Input
              id="udi"
              placeholder="(01)00123456789012(11)210312(17)230312(10)ABC123"
              value={data.udi || ''}
              onChange={(e) => handleFieldChange('udi', e.target.value)}
              disabled={deviceClass === 'I'}
            />
            <p className="text-sm text-muted-foreground mt-1">
              Format: (01)GTIN(11)ProductionDate(17)ExpirationDate(10)LotNumber
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="gmdn-code">GMDN Code</Label>
              <Input
                id="gmdn-code"
                placeholder="e.g., 12345"
                value={data.gmdnCode || ''}
                onChange={(e) => handleFieldChange('gmdnCode', e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="intended-use">Intended Use</Label>
              <SearchableSelect
                value={data.intendedUse || ''}
                onValueChange={(value) => handleFieldChange('intendedUse', value)}
                options={[
                  {
                    value: 'diagnostic',
                    label: 'Diagnostic',
                    description: 'Disease detection and diagnosis',
                    icon: <FileCheck className="h-4 w-4" />
                  },
                  {
                    value: 'therapeutic',
                    label: 'Therapeutic',
                    description: 'Treatment and therapy delivery',
                    icon: <Heart className="h-4 w-4" />
                  },
                  {
                    value: 'monitoring',
                    label: 'Monitoring',
                    description: 'Continuous patient monitoring',
                    icon: <Activity className="h-4 w-4" />
                  },
                  {
                    value: 'life-support',
                    label: 'Life Support',
                    description: 'Critical life-sustaining functions',
                    icon: <AlertTriangle className="h-4 w-4 text-red-500" />
                  }
                ]}
                placeholder="Select intended use"
                searchable={false}
                size="md"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Clinical Parameters Section */}
      <Card>
        <CardHeader>
          <CardTitle>Clinical Parameters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Vital Signs Monitoring</Label>
            <div className="grid grid-cols-2 gap-4 mt-2">
              {[
                { id: 'ecg', label: 'ECG', placeholder: 'Leads (e.g., 12)' },
                { id: 'spo2', label: 'SpO2', placeholder: 'Accuracy %' },
                { id: 'bloodPressure', label: 'Blood Pressure', placeholder: 'Range mmHg' },
                { id: 'temperature', label: 'Temperature', placeholder: 'Accuracy °C' }
              ].map((param) => (
                <div key={param.id} className="flex items-center space-x-2">
                  <Switch
                    id={param.id}
                    checked={data.vitalSigns?.[param.id]?.enabled || false}
                    onCheckedChange={(checked) => 
                      handleFieldChange('vitalSigns', {
                        ...data.vitalSigns,
                        [param.id]: { 
                          ...data.vitalSigns?.[param.id],
                          enabled: checked 
                        }
                      })
                    }
                  />
                  <Label htmlFor={param.id} className="flex-1">
                    {param.label}
                  </Label>
                  {data.vitalSigns?.[param.id]?.enabled && (
                    <Input
                      placeholder={param.placeholder}
                      className="w-32"
                      value={data.vitalSigns?.[param.id]?.spec || ''}
                      onChange={(e) => 
                        handleFieldChange('vitalSigns', {
                          ...data.vitalSigns,
                          [param.id]: { 
                            ...data.vitalSigns?.[param.id],
                            spec: e.target.value 
                          }
                        })
                      }
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Security & Privacy */}
      <Card>
        <CardHeader>
          <CardTitle>Data Security & Privacy</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Compliance Standards</Label>
            <div className="space-y-2 mt-2">
              {[
                { id: 'hipaa', label: 'HIPAA Compliant', desc: 'US Healthcare Privacy' },
                { id: 'gdpr', label: 'GDPR Compliant', desc: 'EU Data Protection' },
                { id: 'hitech', label: 'HITECH Act', desc: 'Health IT Security' },
                { id: 'cfr21', label: '21 CFR Part 11', desc: 'FDA Electronic Records' }
              ].map((standard) => (
                <div key={standard.id} className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Switch
                      id={standard.id}
                      checked={data.compliance?.[standard.id] || false}
                      onCheckedChange={(checked) => 
                        handleFieldChange('compliance', {
                          ...data.compliance,
                          [standard.id]: checked
                        })
                      }
                    />
                    <Label htmlFor={standard.id} className="font-normal">
                      <div>{standard.label}</div>
                      <div className="text-sm text-muted-foreground">{standard.desc}</div>
                    </Label>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Maintenance & Calibration */}
      <Card>
        <CardHeader>
          <CardTitle>Maintenance & Calibration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="calibration-interval">Calibration Interval (days) *</Label>
              <Input
                id="calibration-interval"
                type="number"
                min="1"
                max="365"
                value={data.calibrationInterval || ''}
                onChange={(e) => handleFieldChange('calibrationInterval', parseInt(e.target.value))}
              />
              {errors.calibrationInterval && (
                <p className="text-sm text-red-500 mt-1">{errors.calibrationInterval}</p>
              )}
            </div>
            <div>
              <Label htmlFor="biomedical-cert">Biomedical Certification</Label>
              <div className="flex items-center space-x-2 mt-2">
                <Switch
                  id="biomedical-cert"
                  checked={data.biomedicalCertified || false}
                  onCheckedChange={(checked) => handleFieldChange('biomedicalCertified', checked)}
                />
                <Label htmlFor="biomedical-cert" className="font-normal">
                  Requires Certified Technician
                </Label>
              </div>
            </div>
          </div>

          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Medical devices require regular calibration and maintenance to ensure accuracy
              and compliance with regulatory standards.
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
};

export default HealthMedicalFields;