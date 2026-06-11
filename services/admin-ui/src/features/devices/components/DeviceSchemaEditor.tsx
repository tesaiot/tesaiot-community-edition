/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Form from '@rjsf/core';
import { RJSFSchema, UiSchema } from '@rjsf/utils';
import validator from '@rjsf/validator-ajv8';
// Note: Using core theme for now, will switch to @rjsf/shadcn when theme integration is ready
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { 
  Database as Schema, 
  Code, 
  Eye, 
  Save, 
  RotateCcw,
  FileText,
  Cpu,
  Thermometer,
  Zap,
  Radio,
  Factory,
  Sparkles,
  X,
  Info
} from 'lucide-react';
import '@/css/schema-form.css';
import { SchemaAssistant } from './SchemaAssistant';

interface DeviceSchemaEditorProps {
  deviceType: 'sensor' | 'actuator' | 'gateway' | 'controller';
  industry?: string; // Industry filter for templates
  initialSchema?: {
    schema: RJSFSchema;
    uiSchema?: UiSchema;
    formData?: Record<string, any>;
    metadata?: {
      templateId?: string;
      templateName?: string;
      customized?: boolean;
      createdAt?: string;
      updatedAt?: string;
    };
  };
  onSchemaChange: (schema: {
    schema: RJSFSchema;
    uiSchema: UiSchema;
    formData: Record<string, any>;
    metadata?: {
      templateId?: string;
      templateName?: string;
      customized?: boolean;
      createdAt?: string;
      updatedAt?: string;
    };
  }) => void;
  onHasUnsavedChanges?: (hasChanges: boolean) => void; // Callback to notify parent of unsaved changes
  disabled?: boolean;
}

export const DeviceSchemaEditor: React.FC<DeviceSchemaEditorProps> = ({
  deviceType,
  industry,
  initialSchema,
  onSchemaChange,
  onHasUnsavedChanges,
  disabled = false
}) => {
  const [currentTab, setCurrentTab] = useState<'template' | 'schema' | 'preview'>('template');
  const [schema, setSchema] = useState<RJSFSchema>(initialSchema?.schema || {});
  const [uiSchema, setUiSchema] = useState<UiSchema>(initialSchema?.uiSchema || {});
  const [formData, setFormData] = useState<Record<string, any>>(initialSchema?.formData || {});
  const [selectedTemplate, setSelectedTemplate] = useState<string>(initialSchema?.metadata?.templateId || '');
  const [schemaAssistantOpen, setSchemaAssistantOpen] = useState(false);
  const [schemaMetadata, setSchemaMetadata] = useState(initialSchema?.metadata || {});
  const [showCurrentSchema, setShowCurrentSchema] = useState(true);
  const [savedTemplates, setSavedTemplates] = useState<any[]>([]);
  const [showAllTemplates, setShowAllTemplates] = useState(false); // Show all templates regardless of industry

  // Track unsaved changes - ref stores the last saved state for comparison
  const lastSavedSchemaRef = useRef<string>(JSON.stringify({
    schema: initialSchema?.schema || {},
    uiSchema: initialSchema?.uiSchema || {},
    formData: initialSchema?.formData || {}
  }));
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Industry to Template Mapping - defines which templates are relevant for each industry
  const industryTemplateMapping: Record<string, string[]> = {
    health_medical: ['patientMonitor', 'vitalSigns', 'medicalDevice', 'wearableHealth', 'environmental'],
    industry_40: ['industrial', 'plcData', 'machineStatus', 'predictiveMaintenance', 'vibrationAnalysis'],
    smart_city: ['environmental', 'airQuality', 'trafficMonitor', 'streetLight', 'parkingSensor', 'wasteManagement'],
    smart_energy: ['smartMeter', 'solarInverter', 'batteryStorage', 'gridMonitor', 'evCharger'],
    smart_farm: ['agricultural', 'soilMonitor', 'weatherStation', 'irrigationController', 'livestockTracker', 'greenhouseMonitor']
  };

  // IoT Device Schema Templates - Extended with Industry-specific templates
  const getSchemaTemplates = () => {
    const allTemplates: Record<string, Record<string, any>> = {
      sensor: {
        // === GENERAL TEMPLATES ===
        environmental: {
          name: 'Environmental Sensor',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_city', 'health_medical'],
          schema: {
            type: 'object',
            title: 'Environmental Sensor Telemetry',
            properties: {
              temperature: { type: 'number', title: 'Temperature (°C)', minimum: -50, maximum: 100 },
              humidity: { type: 'number', title: 'Humidity (%)', minimum: 0, maximum: 100 },
              pressure: { type: 'number', title: 'Pressure (hPa)', minimum: 800, maximum: 1200 },
              airQuality: {
                type: 'object', title: 'Air Quality',
                properties: {
                  pm25: { type: 'number', title: 'PM2.5 (µg/m³)' },
                  pm10: { type: 'number', title: 'PM10 (µg/m³)' },
                  co2: { type: 'number', title: 'CO2 (ppm)' }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['temperature', 'humidity', 'timestamp']
          },
          uiSchema: { temperature: { 'ui:widget': 'updown' }, humidity: { 'ui:widget': 'range' } },
          formData: { temperature: 23.5, humidity: 45, pressure: 1013.25, timestamp: new Date().toISOString() }
        },

        // === HEALTH & MEDICAL TEMPLATES ===
        patientMonitor: {
          name: 'Patient Monitor',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Patient Vital Signs Monitor',
            properties: {
              patientId: { type: 'string', title: 'Patient ID' },
              heartRate: { type: 'number', title: 'Heart Rate (bpm)', minimum: 30, maximum: 250 },
              bloodPressure: {
                type: 'object', title: 'Blood Pressure',
                properties: {
                  systolic: { type: 'number', title: 'Systolic (mmHg)', minimum: 60, maximum: 250 },
                  diastolic: { type: 'number', title: 'Diastolic (mmHg)', minimum: 40, maximum: 150 }
                }
              },
              oxygenSaturation: { type: 'number', title: 'SpO2 (%)', minimum: 70, maximum: 100 },
              respiratoryRate: { type: 'number', title: 'Respiratory Rate (breaths/min)', minimum: 5, maximum: 60 },
              bodyTemperature: { type: 'number', title: 'Body Temperature (°C)', minimum: 32, maximum: 43 },
              alertLevel: { type: 'string', enum: ['normal', 'warning', 'critical'], title: 'Alert Level' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['patientId', 'heartRate', 'oxygenSaturation', 'timestamp']
          },
          uiSchema: { alertLevel: { 'ui:widget': 'select' } },
          formData: { heartRate: 72, oxygenSaturation: 98, bodyTemperature: 36.6, alertLevel: 'normal', timestamp: new Date().toISOString() }
        },
        vitalSigns: {
          name: 'Vital Signs Sensor',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Continuous Vital Signs',
            properties: {
              ecg: { type: 'object', title: 'ECG Data', properties: { lead1: { type: 'number' }, lead2: { type: 'number' }, heartRateVariability: { type: 'number' } } },
              bloodGlucose: { type: 'number', title: 'Blood Glucose (mg/dL)', minimum: 20, maximum: 600 },
              bloodOxygen: { type: 'number', title: 'Blood Oxygen (%)', minimum: 70, maximum: 100 },
              skinTemperature: { type: 'number', title: 'Skin Temperature (°C)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['bloodOxygen', 'timestamp']
          },
          uiSchema: {},
          formData: { bloodOxygen: 98, skinTemperature: 32.5, timestamp: new Date().toISOString() }
        },
        medicalDevice: {
          name: 'Medical Device Status',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Medical Device Telemetry',
            properties: {
              deviceStatus: { type: 'string', enum: ['operational', 'standby', 'maintenance', 'error'], title: 'Device Status' },
              calibrationStatus: { type: 'string', enum: ['calibrated', 'needs_calibration', 'expired'], title: 'Calibration' },
              lastCalibration: { type: 'string', format: 'date', title: 'Last Calibration Date' },
              batteryLevel: { type: 'number', title: 'Battery (%)', minimum: 0, maximum: 100 },
              errorCodes: { type: 'array', items: { type: 'string' }, title: 'Error Codes' },
              usageHours: { type: 'number', title: 'Total Usage Hours' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['deviceStatus', 'timestamp']
          },
          uiSchema: { deviceStatus: { 'ui:widget': 'select' } },
          formData: { deviceStatus: 'operational', calibrationStatus: 'calibrated', batteryLevel: 85, timestamp: new Date().toISOString() }
        },
        wearableHealth: {
          name: 'Wearable Health Device',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Wearable Health Telemetry',
            properties: {
              steps: { type: 'integer', title: 'Steps Count', minimum: 0 },
              caloriesBurned: { type: 'number', title: 'Calories Burned (kcal)' },
              activeMinutes: { type: 'integer', title: 'Active Minutes' },
              sleepData: {
                type: 'object', title: 'Sleep Data',
                properties: {
                  duration: { type: 'number', title: 'Sleep Duration (hours)' },
                  quality: { type: 'string', enum: ['poor', 'fair', 'good', 'excellent'], title: 'Sleep Quality' },
                  deepSleep: { type: 'number', title: 'Deep Sleep (hours)' }
                }
              },
              heartRate: { type: 'number', title: 'Heart Rate (bpm)' },
              stressLevel: { type: 'number', title: 'Stress Level (1-100)', minimum: 1, maximum: 100 },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['steps', 'heartRate', 'timestamp']
          },
          uiSchema: {},
          formData: { steps: 8500, heartRate: 72, caloriesBurned: 320, timestamp: new Date().toISOString() }
        },

        // === INDUSTRY 4.0 TEMPLATES ===
        industrial: {
          name: 'Industrial Monitor',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Industrial Sensor Telemetry',
            properties: {
              temperature: { type: 'number', title: 'Temperature (°C)' },
              vibration: {
                type: 'object', title: 'Vibration',
                properties: {
                  x: { type: 'number', title: 'X-axis (m/s²)' },
                  y: { type: 'number', title: 'Y-axis (m/s²)' },
                  z: { type: 'number', title: 'Z-axis (m/s²)' }
                }
              },
              flow: { type: 'number', title: 'Flow Rate (L/min)', minimum: 0 },
              voltage: { type: 'number', title: 'Voltage (V)' },
              current: { type: 'number', title: 'Current (A)' },
              power: { type: 'number', title: 'Power (W)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['temperature', 'timestamp']
          },
          uiSchema: {},
          formData: { temperature: 85.2, voltage: 230.5, current: 2.1, power: 483.05, timestamp: new Date().toISOString() }
        },
        plcData: {
          name: 'PLC Data Interface',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'PLC Data Telemetry',
            properties: {
              plcId: { type: 'string', title: 'PLC ID' },
              registers: { type: 'object', title: 'Register Values', additionalProperties: { type: 'number' } },
              digitalInputs: { type: 'array', items: { type: 'boolean' }, title: 'Digital Inputs' },
              digitalOutputs: { type: 'array', items: { type: 'boolean' }, title: 'Digital Outputs' },
              analogInputs: { type: 'array', items: { type: 'number' }, title: 'Analog Inputs' },
              programStatus: { type: 'string', enum: ['running', 'stopped', 'fault'], title: 'Program Status' },
              scanTime: { type: 'number', title: 'Scan Time (ms)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['plcId', 'programStatus', 'timestamp']
          },
          uiSchema: { programStatus: { 'ui:widget': 'select' } },
          formData: { plcId: 'PLC-001', programStatus: 'running', scanTime: 10, timestamp: new Date().toISOString() }
        },
        machineStatus: {
          name: 'Machine Status Monitor',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Machine Status Telemetry',
            properties: {
              machineId: { type: 'string', title: 'Machine ID' },
              status: { type: 'string', enum: ['running', 'idle', 'maintenance', 'fault', 'offline'], title: 'Status' },
              productionCount: { type: 'integer', title: 'Production Count', minimum: 0 },
              rejectCount: { type: 'integer', title: 'Reject Count', minimum: 0 },
              oee: { type: 'number', title: 'OEE (%)', minimum: 0, maximum: 100 },
              cycleTime: { type: 'number', title: 'Cycle Time (seconds)' },
              runtime: { type: 'number', title: 'Runtime (hours)' },
              alarms: { type: 'array', items: { type: 'string' }, title: 'Active Alarms' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['machineId', 'status', 'timestamp']
          },
          uiSchema: { status: { 'ui:widget': 'select' } },
          formData: { machineId: 'MCH-001', status: 'running', productionCount: 1250, oee: 85.5, timestamp: new Date().toISOString() }
        },
        predictiveMaintenance: {
          name: 'Predictive Maintenance',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Predictive Maintenance Data',
            properties: {
              equipmentId: { type: 'string', title: 'Equipment ID' },
              healthScore: { type: 'number', title: 'Health Score (0-100)', minimum: 0, maximum: 100 },
              remainingUsefulLife: { type: 'number', title: 'Remaining Useful Life (hours)' },
              anomalyScore: { type: 'number', title: 'Anomaly Score', minimum: 0, maximum: 1 },
              predictedFailureDate: { type: 'string', format: 'date', title: 'Predicted Failure Date' },
              maintenanceRecommendation: { type: 'string', title: 'Recommendation' },
              sensorReadings: {
                type: 'object', title: 'Sensor Readings',
                properties: {
                  temperature: { type: 'number' },
                  vibration: { type: 'number' },
                  pressure: { type: 'number' },
                  current: { type: 'number' }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['equipmentId', 'healthScore', 'timestamp']
          },
          uiSchema: {},
          formData: { equipmentId: 'EQ-001', healthScore: 87, remainingUsefulLife: 2500, anomalyScore: 0.12, timestamp: new Date().toISOString() }
        },
        vibrationAnalysis: {
          name: 'Vibration Analysis',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Vibration Analysis Data',
            properties: {
              sensorId: { type: 'string', title: 'Sensor ID' },
              rmsVelocity: { type: 'number', title: 'RMS Velocity (mm/s)' },
              peakAcceleration: { type: 'number', title: 'Peak Acceleration (g)' },
              dominantFrequency: { type: 'number', title: 'Dominant Frequency (Hz)' },
              temperature: { type: 'number', title: 'Bearing Temperature (°C)' },
              spectrumData: { type: 'array', items: { type: 'number' }, title: 'FFT Spectrum' },
              severity: { type: 'string', enum: ['good', 'satisfactory', 'unsatisfactory', 'unacceptable'], title: 'Severity' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['sensorId', 'rmsVelocity', 'severity', 'timestamp']
          },
          uiSchema: { severity: { 'ui:widget': 'select' } },
          formData: { sensorId: 'VIB-001', rmsVelocity: 2.5, peakAcceleration: 0.8, dominantFrequency: 120, severity: 'good', timestamp: new Date().toISOString() }
        },

        // === SMART CITY TEMPLATES ===
        airQuality: {
          name: 'Air Quality Monitor',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Air Quality Telemetry',
            properties: {
              aqi: { type: 'integer', title: 'Air Quality Index (AQI)', minimum: 0, maximum: 500 },
              pm25: { type: 'number', title: 'PM2.5 (µg/m³)' },
              pm10: { type: 'number', title: 'PM10 (µg/m³)' },
              co: { type: 'number', title: 'CO (ppm)' },
              no2: { type: 'number', title: 'NO2 (ppb)' },
              o3: { type: 'number', title: 'O3 (ppb)' },
              so2: { type: 'number', title: 'SO2 (ppb)' },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              humidity: { type: 'number', title: 'Humidity (%)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['aqi', 'pm25', 'timestamp']
          },
          uiSchema: {},
          formData: { aqi: 52, pm25: 12.5, pm10: 25, co: 0.4, temperature: 28, humidity: 65, timestamp: new Date().toISOString() }
        },
        trafficMonitor: {
          name: 'Traffic Monitor',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Traffic Monitoring Data',
            properties: {
              locationId: { type: 'string', title: 'Location ID' },
              vehicleCount: { type: 'integer', title: 'Vehicle Count', minimum: 0 },
              averageSpeed: { type: 'number', title: 'Average Speed (km/h)' },
              occupancy: { type: 'number', title: 'Lane Occupancy (%)', minimum: 0, maximum: 100 },
              congestionLevel: { type: 'string', enum: ['free', 'light', 'moderate', 'heavy', 'severe'], title: 'Congestion Level' },
              incidentDetected: { type: 'boolean', title: 'Incident Detected' },
              vehicleTypes: {
                type: 'object', title: 'Vehicle Classification',
                properties: {
                  cars: { type: 'integer' },
                  trucks: { type: 'integer' },
                  motorcycles: { type: 'integer' },
                  buses: { type: 'integer' }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['locationId', 'vehicleCount', 'timestamp']
          },
          uiSchema: { congestionLevel: { 'ui:widget': 'select' } },
          formData: { locationId: 'TRF-001', vehicleCount: 245, averageSpeed: 42, congestionLevel: 'light', timestamp: new Date().toISOString() }
        },
        streetLight: {
          name: 'Smart Street Light',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Street Light Telemetry',
            properties: {
              lightId: { type: 'string', title: 'Light ID' },
              status: { type: 'string', enum: ['on', 'off', 'dimmed', 'fault'], title: 'Status' },
              brightness: { type: 'number', title: 'Brightness (%)', minimum: 0, maximum: 100 },
              powerConsumption: { type: 'number', title: 'Power (W)' },
              ambientLight: { type: 'number', title: 'Ambient Light (lux)' },
              motionDetected: { type: 'boolean', title: 'Motion Detected' },
              operatingHours: { type: 'number', title: 'Operating Hours' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['lightId', 'status', 'timestamp']
          },
          uiSchema: { status: { 'ui:widget': 'select' } },
          formData: { lightId: 'SL-001', status: 'on', brightness: 80, powerConsumption: 45, timestamp: new Date().toISOString() }
        },
        parkingSensor: {
          name: 'Parking Sensor',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Parking Spot Telemetry',
            properties: {
              spotId: { type: 'string', title: 'Spot ID' },
              occupied: { type: 'boolean', title: 'Occupied' },
              vehicleDetectedAt: { type: 'string', format: 'date-time', title: 'Vehicle Detected At' },
              duration: { type: 'number', title: 'Duration (minutes)' },
              zoneId: { type: 'string', title: 'Zone ID' },
              batteryLevel: { type: 'number', title: 'Battery (%)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['spotId', 'occupied', 'timestamp']
          },
          uiSchema: {},
          formData: { spotId: 'P-A001', occupied: true, duration: 45, batteryLevel: 92, timestamp: new Date().toISOString() }
        },
        wasteManagement: {
          name: 'Waste Bin Sensor',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Waste Bin Telemetry',
            properties: {
              binId: { type: 'string', title: 'Bin ID' },
              fillLevel: { type: 'number', title: 'Fill Level (%)', minimum: 0, maximum: 100 },
              temperature: { type: 'number', title: 'Internal Temperature (°C)' },
              tiltAngle: { type: 'number', title: 'Tilt Angle (°)' },
              lastEmptied: { type: 'string', format: 'date-time', title: 'Last Emptied' },
              batteryLevel: { type: 'number', title: 'Battery (%)' },
              wasteType: { type: 'string', enum: ['general', 'recyclable', 'organic', 'hazardous'], title: 'Waste Type' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['binId', 'fillLevel', 'timestamp']
          },
          uiSchema: { wasteType: { 'ui:widget': 'select' } },
          formData: { binId: 'BIN-001', fillLevel: 65, wasteType: 'general', batteryLevel: 88, timestamp: new Date().toISOString() }
        },

        // === SMART ENERGY TEMPLATES ===
        smartMeter: {
          name: 'Smart Energy Meter',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Energy Consumption',
            properties: {
              meterId: { type: 'string', title: 'Meter ID' },
              energy: {
                type: 'object', title: 'Energy Metrics',
                properties: {
                  voltage: { type: 'number', title: 'Voltage (V)', minimum: 0, maximum: 500 },
                  current: { type: 'number', title: 'Current (A)', minimum: 0 },
                  power: { type: 'number', title: 'Power (W)', minimum: 0 },
                  powerFactor: { type: 'number', title: 'Power Factor', minimum: 0, maximum: 1 },
                  frequency: { type: 'number', title: 'Frequency (Hz)', minimum: 45, maximum: 65 },
                  totalEnergy: { type: 'number', title: 'Total Energy (kWh)', minimum: 0 }
                }
              },
              tariffPeriod: { type: 'string', enum: ['peak', 'off-peak', 'shoulder'], title: 'Tariff Period' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['meterId', 'energy', 'timestamp']
          },
          uiSchema: { tariffPeriod: { 'ui:widget': 'select' } },
          formData: { meterId: 'MTR-001', energy: { voltage: 230, current: 10.5, power: 2415, powerFactor: 0.95, frequency: 50, totalEnergy: 1250.5 }, tariffPeriod: 'peak', timestamp: new Date().toISOString() }
        },
        solarInverter: {
          name: 'Solar Inverter',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Solar Inverter Telemetry',
            properties: {
              inverterId: { type: 'string', title: 'Inverter ID' },
              dcPower: { type: 'number', title: 'DC Power (W)' },
              acPower: { type: 'number', title: 'AC Power (W)' },
              efficiency: { type: 'number', title: 'Efficiency (%)', minimum: 0, maximum: 100 },
              dcVoltage: { type: 'number', title: 'DC Voltage (V)' },
              acVoltage: { type: 'number', title: 'AC Voltage (V)' },
              frequency: { type: 'number', title: 'Frequency (Hz)' },
              energyToday: { type: 'number', title: 'Energy Today (kWh)' },
              totalEnergy: { type: 'number', title: 'Total Energy (kWh)' },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              status: { type: 'string', enum: ['generating', 'standby', 'fault', 'offline'], title: 'Status' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['inverterId', 'acPower', 'status', 'timestamp']
          },
          uiSchema: { status: { 'ui:widget': 'select' } },
          formData: { inverterId: 'INV-001', dcPower: 5200, acPower: 5000, efficiency: 96.2, status: 'generating', timestamp: new Date().toISOString() }
        },
        batteryStorage: {
          name: 'Battery Storage System',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Battery Storage Telemetry',
            properties: {
              batteryId: { type: 'string', title: 'Battery ID' },
              stateOfCharge: { type: 'number', title: 'State of Charge (%)', minimum: 0, maximum: 100 },
              stateOfHealth: { type: 'number', title: 'State of Health (%)', minimum: 0, maximum: 100 },
              voltage: { type: 'number', title: 'Voltage (V)' },
              current: { type: 'number', title: 'Current (A)' },
              power: { type: 'number', title: 'Power (W)' },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              cycleCount: { type: 'integer', title: 'Cycle Count' },
              mode: { type: 'string', enum: ['charging', 'discharging', 'idle', 'standby'], title: 'Mode' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['batteryId', 'stateOfCharge', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' } },
          formData: { batteryId: 'BAT-001', stateOfCharge: 75, stateOfHealth: 98, mode: 'discharging', timestamp: new Date().toISOString() }
        },
        gridMonitor: {
          name: 'Grid Monitor',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Grid Monitoring Data',
            properties: {
              nodeId: { type: 'string', title: 'Node ID' },
              voltage: { type: 'number', title: 'Voltage (V)' },
              frequency: { type: 'number', title: 'Frequency (Hz)' },
              activePower: { type: 'number', title: 'Active Power (kW)' },
              reactivePower: { type: 'number', title: 'Reactive Power (kVAR)' },
              powerFactor: { type: 'number', title: 'Power Factor' },
              thd: { type: 'number', title: 'THD (%)', description: 'Total Harmonic Distortion' },
              gridStatus: { type: 'string', enum: ['normal', 'undervoltage', 'overvoltage', 'fault'], title: 'Grid Status' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['nodeId', 'voltage', 'frequency', 'timestamp']
          },
          uiSchema: { gridStatus: { 'ui:widget': 'select' } },
          formData: { nodeId: 'GRD-001', voltage: 230, frequency: 50, activePower: 150, gridStatus: 'normal', timestamp: new Date().toISOString() }
        },
        evCharger: {
          name: 'EV Charger',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'EV Charger Telemetry',
            properties: {
              chargerId: { type: 'string', title: 'Charger ID' },
              status: { type: 'string', enum: ['available', 'charging', 'finishing', 'fault', 'offline'], title: 'Status' },
              connectorType: { type: 'string', enum: ['Type1', 'Type2', 'CCS', 'CHAdeMO'], title: 'Connector Type' },
              power: { type: 'number', title: 'Power (kW)' },
              energyDelivered: { type: 'number', title: 'Energy Delivered (kWh)' },
              sessionDuration: { type: 'number', title: 'Session Duration (min)' },
              vehicleSoC: { type: 'number', title: 'Vehicle SoC (%)', minimum: 0, maximum: 100 },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['chargerId', 'status', 'timestamp']
          },
          uiSchema: { status: { 'ui:widget': 'select' }, connectorType: { 'ui:widget': 'select' } },
          formData: { chargerId: 'EVC-001', status: 'charging', connectorType: 'Type2', power: 22, timestamp: new Date().toISOString() }
        },

        // === SMART FARM TEMPLATES ===
        agricultural: {
          name: 'Agricultural Sensor',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Agricultural Monitoring',
            properties: {
              soil: {
                type: 'object', title: 'Soil Conditions',
                properties: {
                  moisture: { type: 'number', title: 'Moisture (%)', minimum: 0, maximum: 100 },
                  temperature: { type: 'number', title: 'Temperature (°C)', minimum: -10, maximum: 50 },
                  ph: { type: 'number', title: 'pH Level', minimum: 0, maximum: 14 },
                  nitrogen: { type: 'number', title: 'Nitrogen (mg/kg)' },
                  phosphorus: { type: 'number', title: 'Phosphorus (mg/kg)' },
                  potassium: { type: 'number', title: 'Potassium (mg/kg)' }
                }
              },
              weather: {
                type: 'object', title: 'Weather Conditions',
                properties: {
                  temperature: { type: 'number', title: 'Air Temperature (°C)' },
                  humidity: { type: 'number', title: 'Humidity (%)', minimum: 0, maximum: 100 },
                  rainfall: { type: 'number', title: 'Rainfall (mm)', minimum: 0 },
                  windSpeed: { type: 'number', title: 'Wind Speed (km/h)', minimum: 0 },
                  solarRadiation: { type: 'number', title: 'Solar Radiation (W/m²)', minimum: 0 }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['soil', 'timestamp']
          },
          uiSchema: {},
          formData: { soil: { moisture: 65, temperature: 22, ph: 6.5 }, weather: { temperature: 25, humidity: 70 }, timestamp: new Date().toISOString() }
        },
        soilMonitor: {
          name: 'Soil Monitor',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Soil Monitoring Data',
            properties: {
              sensorId: { type: 'string', title: 'Sensor ID' },
              depth: { type: 'number', title: 'Sensor Depth (cm)' },
              moisture: { type: 'number', title: 'Moisture (%)', minimum: 0, maximum: 100 },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              ec: { type: 'number', title: 'Electrical Conductivity (dS/m)' },
              ph: { type: 'number', title: 'pH', minimum: 0, maximum: 14 },
              npk: {
                type: 'object', title: 'NPK Levels',
                properties: {
                  nitrogen: { type: 'number', title: 'N (mg/kg)' },
                  phosphorus: { type: 'number', title: 'P (mg/kg)' },
                  potassium: { type: 'number', title: 'K (mg/kg)' }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['sensorId', 'moisture', 'timestamp']
          },
          uiSchema: {},
          formData: { sensorId: 'SOIL-001', depth: 30, moisture: 45, temperature: 22, ph: 6.8, timestamp: new Date().toISOString() }
        },
        weatherStation: {
          name: 'Weather Station',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Weather Station Data',
            properties: {
              stationId: { type: 'string', title: 'Station ID' },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              humidity: { type: 'number', title: 'Humidity (%)', minimum: 0, maximum: 100 },
              pressure: { type: 'number', title: 'Barometric Pressure (hPa)' },
              windSpeed: { type: 'number', title: 'Wind Speed (km/h)' },
              windDirection: { type: 'number', title: 'Wind Direction (°)', minimum: 0, maximum: 360 },
              rainfall: { type: 'number', title: 'Rainfall (mm)' },
              solarRadiation: { type: 'number', title: 'Solar Radiation (W/m²)' },
              uvIndex: { type: 'number', title: 'UV Index', minimum: 0, maximum: 15 },
              dewPoint: { type: 'number', title: 'Dew Point (°C)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['stationId', 'temperature', 'humidity', 'timestamp']
          },
          uiSchema: {},
          formData: { stationId: 'WS-001', temperature: 28, humidity: 65, pressure: 1013, windSpeed: 12, timestamp: new Date().toISOString() }
        },
        irrigationController: {
          name: 'Irrigation Monitor',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Irrigation System Telemetry',
            properties: {
              zoneId: { type: 'string', title: 'Zone ID' },
              status: { type: 'string', enum: ['active', 'idle', 'scheduled', 'fault'], title: 'Status' },
              flowRate: { type: 'number', title: 'Flow Rate (L/min)' },
              totalVolume: { type: 'number', title: 'Total Volume (L)' },
              pressure: { type: 'number', title: 'Pressure (bar)' },
              soilMoisture: { type: 'number', title: 'Soil Moisture (%)', minimum: 0, maximum: 100 },
              valvePosition: { type: 'number', title: 'Valve Position (%)', minimum: 0, maximum: 100 },
              nextSchedule: { type: 'string', format: 'date-time', title: 'Next Schedule' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['zoneId', 'status', 'timestamp']
          },
          uiSchema: { status: { 'ui:widget': 'select' } },
          formData: { zoneId: 'IRR-001', status: 'idle', flowRate: 0, soilMoisture: 55, timestamp: new Date().toISOString() }
        },
        livestockTracker: {
          name: 'Livestock Tracker',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Livestock Tracking Data',
            properties: {
              animalId: { type: 'string', title: 'Animal ID' },
              species: { type: 'string', enum: ['cattle', 'sheep', 'goat', 'pig', 'poultry'], title: 'Species' },
              location: {
                type: 'object', title: 'GPS Location',
                properties: {
                  latitude: { type: 'number' },
                  longitude: { type: 'number' }
                }
              },
              bodyTemperature: { type: 'number', title: 'Body Temperature (°C)' },
              activityLevel: { type: 'string', enum: ['resting', 'grazing', 'walking', 'running'], title: 'Activity' },
              heartRate: { type: 'number', title: 'Heart Rate (bpm)' },
              healthStatus: { type: 'string', enum: ['healthy', 'monitoring', 'sick', 'critical'], title: 'Health Status' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['animalId', 'species', 'timestamp']
          },
          uiSchema: { species: { 'ui:widget': 'select' }, activityLevel: { 'ui:widget': 'select' }, healthStatus: { 'ui:widget': 'select' } },
          formData: { animalId: 'COW-001', species: 'cattle', bodyTemperature: 38.5, activityLevel: 'grazing', healthStatus: 'healthy', timestamp: new Date().toISOString() }
        },
        greenhouseMonitor: {
          name: 'Greenhouse Monitor',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Greenhouse Telemetry',
            properties: {
              greenhouseId: { type: 'string', title: 'Greenhouse ID' },
              temperature: { type: 'number', title: 'Temperature (°C)' },
              humidity: { type: 'number', title: 'Humidity (%)', minimum: 0, maximum: 100 },
              co2Level: { type: 'number', title: 'CO2 (ppm)' },
              lightIntensity: { type: 'number', title: 'Light Intensity (lux)' },
              soilMoisture: { type: 'number', title: 'Soil Moisture (%)', minimum: 0, maximum: 100 },
              ventilationStatus: { type: 'string', enum: ['open', 'closed', 'auto'], title: 'Ventilation' },
              heatingStatus: { type: 'boolean', title: 'Heating Active' },
              coolingStatus: { type: 'boolean', title: 'Cooling Active' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['greenhouseId', 'temperature', 'humidity', 'timestamp']
          },
          uiSchema: { ventilationStatus: { 'ui:widget': 'select' } },
          formData: { greenhouseId: 'GH-001', temperature: 26, humidity: 75, co2Level: 800, ventilationStatus: 'auto', timestamp: new Date().toISOString() }
        },

        // === GENERAL (VEHICLE) ===
        vehicleTracker: {
          name: 'Vehicle Tracker',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'industry_40'],
          schema: {
            type: 'object',
            title: 'Vehicle Telemetry',
            properties: {
              location: {
                type: 'object', title: 'GPS Location',
                properties: {
                  latitude: { type: 'number', minimum: -90, maximum: 90 },
                  longitude: { type: 'number', minimum: -180, maximum: 180 },
                  altitude: { type: 'number', title: 'Altitude (m)' },
                  speed: { type: 'number', title: 'Speed (km/h)', minimum: 0 },
                  heading: { type: 'number', title: 'Heading (°)', minimum: 0, maximum: 360 }
                }
              },
              vehicle: {
                type: 'object', title: 'Vehicle Status',
                properties: {
                  engineRunning: { type: 'boolean', title: 'Engine Running' },
                  fuel: { type: 'number', title: 'Fuel Level (%)', minimum: 0, maximum: 100 },
                  odometer: { type: 'number', title: 'Odometer (km)', minimum: 0 }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['location', 'timestamp']
          },
          uiSchema: {},
          formData: { location: { latitude: 13.7563, longitude: 100.5018, speed: 60 }, vehicle: { engineRunning: true, fuel: 75 }, timestamp: new Date().toISOString() }
        }
      },
      actuator: {
        relay: {
          name: 'Relay Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_city', 'industry_40', 'smart_farm'],
          schema: {
            type: 'object',
            title: 'Relay Command',
            properties: {
              action: { type: 'string', enum: ['on', 'off', 'toggle'], title: 'Action' },
              relay_id: { type: 'string', title: 'Relay ID' },
              duration: { type: 'number', title: 'Duration (seconds)', minimum: 0 },
              timestamp: { type: 'string', format: 'date-time', title: 'Command Timestamp' }
            },
            required: ['action', 'relay_id']
          },
          uiSchema: { action: { 'ui:widget': 'radio' } },
          formData: { action: 'on', relay_id: 'relay_001', duration: 30, timestamp: new Date().toISOString() }
        },
        motorController: {
          name: 'Motor Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Motor Control Commands',
            properties: {
              command: { type: 'string', title: 'Command', enum: ['start', 'stop', 'emergency_stop', 'reset'], default: 'stop' },
              speed: { type: 'number', title: 'Speed Setpoint (RPM)', minimum: 0, maximum: 3600 },
              direction: { type: 'string', title: 'Direction', enum: ['forward', 'reverse'], default: 'forward' },
              rampTime: { type: 'number', title: 'Ramp Time (seconds)', minimum: 0, maximum: 60, default: 5 },
              timestamp: { type: 'string', format: 'date-time', title: 'Command Timestamp' }
            },
            required: ['command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, direction: { 'ui:widget': 'radio' } },
          formData: { command: 'stop', speed: 1500, direction: 'forward', rampTime: 5, timestamp: new Date().toISOString() }
        },
        valveController: {
          name: 'Valve Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['industry_40', 'smart_farm', 'smart_energy'],
          schema: {
            type: 'object',
            title: 'Valve Control',
            properties: {
              valveId: { type: 'string', title: 'Valve ID' },
              position: { type: 'number', title: 'Position (%)', minimum: 0, maximum: 100, description: '0 = Fully Closed, 100 = Fully Open' },
              mode: { type: 'string', title: 'Control Mode', enum: ['manual', 'automatic', 'maintenance'], default: 'manual' },
              flowSetpoint: { type: 'number', title: 'Flow Setpoint (L/min)', minimum: 0, description: 'Only used in automatic mode' },
              timestamp: { type: 'string', format: 'date-time', title: 'Command Timestamp' }
            },
            required: ['valveId', 'position', 'timestamp']
          },
          uiSchema: { position: { 'ui:widget': 'range' }, mode: { 'ui:widget': 'select' } },
          formData: { valveId: 'valve_001', position: 50, mode: 'manual', flowSetpoint: 100, timestamp: new Date().toISOString() }
        },
        pumpController: {
          name: 'Pump Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_farm', 'industry_40'],
          schema: {
            type: 'object',
            title: 'Pump Control Command',
            properties: {
              pumpId: { type: 'string', title: 'Pump ID' },
              command: { type: 'string', enum: ['start', 'stop', 'auto'], title: 'Command' },
              flowRate: { type: 'number', title: 'Target Flow Rate (L/min)' },
              pressure: { type: 'number', title: 'Target Pressure (bar)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['pumpId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' } },
          formData: { pumpId: 'PUMP-001', command: 'stop', timestamp: new Date().toISOString() }
        },
        medicalInfusionPump: {
          name: 'Medical Infusion Pump',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Infusion Pump Actuator Command',
            properties: {
              pumpId: { type: 'string', title: 'Pump ID' },
              patientId: { type: 'string', title: 'Patient ID' },
              action: { type: 'string', enum: ['start', 'pause', 'stop', 'bolus', 'prime'], title: 'Action' },
              rate: { type: 'number', title: 'Infusion Rate (mL/hr)', minimum: 0.1, maximum: 999 },
              volume: { type: 'number', title: 'Volume to Infuse (mL)' },
              bolusVolume: { type: 'number', title: 'Bolus Volume (mL)', minimum: 0.1 },
              occlusion: { type: 'object', title: 'Occlusion Settings', properties: { enabled: { type: 'boolean' }, threshold: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['pumpId', 'action', 'timestamp']
          },
          uiSchema: { action: { 'ui:widget': 'select' } },
          formData: { pumpId: 'INF-001', action: 'start', rate: 50, volume: 500, timestamp: new Date().toISOString() }
        },
        ventilatorActuator: {
          name: 'Medical Ventilator',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Ventilator Actuator Command',
            properties: {
              ventilatorId: { type: 'string', title: 'Ventilator ID' },
              mode: { type: 'string', enum: ['VC-CMV', 'PC-CMV', 'SIMV', 'PSV', 'CPAP', 'BiPAP', 'standby'], title: 'Ventilation Mode' },
              tidalVolume: { type: 'number', title: 'Tidal Volume (mL)', minimum: 100, maximum: 1000 },
              respiratoryRate: { type: 'number', title: 'Respiratory Rate (/min)', minimum: 4, maximum: 40 },
              peep: { type: 'number', title: 'PEEP (cmH2O)', minimum: 0, maximum: 25 },
              fio2: { type: 'number', title: 'FiO2 (%)', minimum: 21, maximum: 100 },
              inspiratoryTime: { type: 'number', title: 'I:E Ratio I-time (sec)' },
              pressureSupport: { type: 'number', title: 'Pressure Support (cmH2O)' },
              alarmLimits: { type: 'object', title: 'Alarm Limits', properties: { highPressure: { type: 'number' }, lowPressure: { type: 'number' }, lowVolume: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['ventilatorId', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' } },
          formData: { ventilatorId: 'VENT-001', mode: 'VC-CMV', tidalVolume: 500, respiratoryRate: 14, peep: 5, fio2: 40, timestamp: new Date().toISOString() }
        },
        hospitalBed: {
          name: 'Smart Hospital Bed',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Hospital Bed Actuator Command',
            properties: {
              bedId: { type: 'string', title: 'Bed ID' },
              headPosition: { type: 'number', title: 'Head Position (°)', minimum: 0, maximum: 80 },
              footPosition: { type: 'number', title: 'Foot Position (°)', minimum: 0, maximum: 40 },
              height: { type: 'number', title: 'Bed Height (cm)', minimum: 30, maximum: 90 },
              trendelenburg: { type: 'number', title: 'Trendelenburg (°)', minimum: -15, maximum: 15 },
              sideRails: { type: 'string', enum: ['up', 'down', 'half'], title: 'Side Rails' },
              brakeStatus: { type: 'string', enum: ['locked', 'unlocked'], title: 'Brake Status' },
              scale: { type: 'boolean', title: 'Enable Bed Scale' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['bedId', 'timestamp']
          },
          uiSchema: { sideRails: { 'ui:widget': 'radio' }, brakeStatus: { 'ui:widget': 'radio' } },
          formData: { bedId: 'BED-001', headPosition: 30, height: 60, sideRails: 'up', brakeStatus: 'locked', timestamp: new Date().toISOString() }
        },
        inverterActuator: {
          name: 'Solar Inverter Actuator',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Inverter Actuator Command',
            properties: {
              inverterId: { type: 'string', title: 'Inverter ID' },
              command: { type: 'string', enum: ['start', 'stop', 'curtail', 'reactive_power'], title: 'Command' },
              activePowerLimit: { type: 'number', title: 'Active Power Limit (%)', minimum: 0, maximum: 100 },
              reactivePowerSetpoint: { type: 'number', title: 'Reactive Power (kVAR)' },
              powerFactor: { type: 'number', title: 'Power Factor', minimum: -1, maximum: 1 },
              gridCode: { type: 'string', enum: ['normal', 'lvrt', 'frequency_response'], title: 'Grid Code Mode' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['inverterId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, gridCode: { 'ui:widget': 'select' } },
          formData: { inverterId: 'INV-001', command: 'start', activePowerLimit: 100, powerFactor: 1.0, gridCode: 'normal', timestamp: new Date().toISOString() }
        },
        batteryActuator: {
          name: 'Battery Storage Actuator',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Battery Actuator Command',
            properties: {
              batteryId: { type: 'string', title: 'Battery ID' },
              command: { type: 'string', enum: ['charge', 'discharge', 'standby', 'balance', 'emergency_discharge'], title: 'Command' },
              powerSetpoint: { type: 'number', title: 'Power Setpoint (kW)' },
              socLimit: { type: 'object', title: 'SoC Limits', properties: { min: { type: 'number' }, max: { type: 'number' } } },
              chargingStrategy: { type: 'string', enum: ['fast', 'normal', 'trickle', 'scheduled'], title: 'Charging Strategy' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['batteryId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, chargingStrategy: { 'ui:widget': 'select' } },
          formData: { batteryId: 'BESS-001', command: 'standby', powerSetpoint: 0, socLimit: { min: 20, max: 90 }, chargingStrategy: 'normal', timestamp: new Date().toISOString() }
        },
        sprinklerActuator: {
          name: 'Irrigation Sprinkler',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Sprinkler Actuator Command',
            properties: {
              sprinklerId: { type: 'string', title: 'Sprinkler ID' },
              zoneId: { type: 'string', title: 'Zone ID' },
              command: { type: 'string', enum: ['on', 'off', 'pulse', 'schedule'], title: 'Command' },
              duration: { type: 'number', title: 'Duration (minutes)', minimum: 1, maximum: 120 },
              waterVolume: { type: 'number', title: 'Target Water Volume (L)' },
              pressure: { type: 'number', title: 'Pressure Setpoint (bar)' },
              pattern: { type: 'string', enum: ['full_circle', 'half_circle', 'sector', 'oscillate'], title: 'Spray Pattern' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['sprinklerId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, pattern: { 'ui:widget': 'select' } },
          formData: { sprinklerId: 'SPR-001', zoneId: 'ZONE-A', command: 'off', duration: 30, pattern: 'full_circle', timestamp: new Date().toISOString() }
        },
        fertigationActuator: {
          name: 'Fertigation Injector',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Fertigation Actuator Command',
            properties: {
              injectorId: { type: 'string', title: 'Injector ID' },
              command: { type: 'string', enum: ['inject', 'stop', 'flush', 'calibrate'], title: 'Command' },
              nutrientMix: {
                type: 'object', title: 'Nutrient Mix',
                properties: {
                  nitrogen: { type: 'number', title: 'N (ppm)' },
                  phosphorus: { type: 'number', title: 'P (ppm)' },
                  potassium: { type: 'number', title: 'K (ppm)' },
                  micronutrients: { type: 'boolean', title: 'Include Micronutrients' }
                }
              },
              ec: { type: 'number', title: 'Target EC (mS/cm)', minimum: 0, maximum: 10 },
              ph: { type: 'number', title: 'Target pH', minimum: 4, maximum: 9 },
              injectionRate: { type: 'number', title: 'Injection Rate (L/hr)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['injectorId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' } },
          formData: { injectorId: 'FERT-001', command: 'stop', ec: 2.0, ph: 6.0, injectionRate: 5, timestamp: new Date().toISOString() }
        },
        conveyorActuator: {
          name: 'Conveyor Belt Actuator',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Conveyor Actuator Command',
            properties: {
              conveyorId: { type: 'string', title: 'Conveyor ID' },
              command: { type: 'string', enum: ['start', 'stop', 'reverse', 'jog', 'emergency_stop'], title: 'Command' },
              speed: { type: 'number', title: 'Speed (m/min)', minimum: 0, maximum: 100 },
              acceleration: { type: 'number', title: 'Acceleration (m/s²)', minimum: 0.1, maximum: 5 },
              direction: { type: 'string', enum: ['forward', 'reverse'], title: 'Direction' },
              tensionControl: { type: 'boolean', title: 'Auto Tension Control' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['conveyorId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, direction: { 'ui:widget': 'radio' } },
          formData: { conveyorId: 'CONV-001', command: 'stop', speed: 10, direction: 'forward', tensionControl: true, timestamp: new Date().toISOString() }
        },
        industrialRobot: {
          name: 'Industrial Robot Actuator',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Robot Actuator Command',
            properties: {
              robotId: { type: 'string', title: 'Robot ID' },
              command: { type: 'string', enum: ['run', 'pause', 'home', 'jog', 'emergency_stop', 'reset_fault'], title: 'Command' },
              program: { type: 'string', title: 'Program Name' },
              cycleMode: { type: 'string', enum: ['continuous', 'single_cycle', 'step'], title: 'Cycle Mode' },
              speedOverride: { type: 'number', title: 'Speed Override (%)', minimum: 0, maximum: 100 },
              toolCommand: { type: 'object', title: 'Tool Command', properties: { toolId: { type: 'integer' }, action: { type: 'string', enum: ['activate', 'deactivate', 'pulse'] } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['robotId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, cycleMode: { 'ui:widget': 'select' } },
          formData: { robotId: 'ROB-001', command: 'run', cycleMode: 'continuous', speedOverride: 100, timestamp: new Date().toISOString() }
        },
        trafficSignal: {
          name: 'Traffic Signal Actuator',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city'],
          schema: {
            type: 'object',
            title: 'Traffic Signal Command',
            properties: {
              signalId: { type: 'string', title: 'Signal ID' },
              intersection: { type: 'string', title: 'Intersection ID' },
              phase: { type: 'string', enum: ['red', 'yellow', 'green', 'flashing_red', 'flashing_yellow', 'off'], title: 'Phase' },
              duration: { type: 'number', title: 'Phase Duration (sec)' },
              mode: { type: 'string', enum: ['normal', 'manual', 'emergency', 'pedestrian_priority'], title: 'Operation Mode' },
              preemption: { type: 'boolean', title: 'Emergency Preemption' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['signalId', 'phase', 'timestamp']
          },
          uiSchema: { phase: { 'ui:widget': 'select' }, mode: { 'ui:widget': 'select' } },
          formData: { signalId: 'TRF-SIG-001', phase: 'green', duration: 45, mode: 'normal', preemption: false, timestamp: new Date().toISOString() }
        },
        doorActuator: {
          name: 'Automatic Door/Gate',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'health_medical', 'industry_40'],
          schema: {
            type: 'object',
            title: 'Door/Gate Actuator Command',
            properties: {
              doorId: { type: 'string', title: 'Door/Gate ID' },
              command: { type: 'string', enum: ['open', 'close', 'stop', 'hold_open', 'lock', 'unlock'], title: 'Command' },
              openPercentage: { type: 'number', title: 'Open Percentage (%)', minimum: 0, maximum: 100 },
              holdDuration: { type: 'number', title: 'Hold Duration (sec)' },
              speed: { type: 'string', enum: ['slow', 'normal', 'fast'], title: 'Operation Speed' },
              safetyBypass: { type: 'boolean', title: 'Safety Sensor Bypass (Admin)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['doorId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, speed: { 'ui:widget': 'select' } },
          formData: { doorId: 'DOOR-001', command: 'close', speed: 'normal', safetyBypass: false, timestamp: new Date().toISOString() }
        },
        sirenActuator: {
          name: 'Alarm/Siren Actuator',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'health_medical', 'industry_40'],
          schema: {
            type: 'object',
            title: 'Siren/Alarm Actuator Command',
            properties: {
              sirenId: { type: 'string', title: 'Siren ID' },
              command: { type: 'string', enum: ['activate', 'deactivate', 'test', 'acknowledge'], title: 'Command' },
              pattern: { type: 'string', enum: ['continuous', 'pulsing', 'wail', 'chirp', 'voice'], title: 'Sound Pattern' },
              volume: { type: 'number', title: 'Volume (%)', minimum: 0, maximum: 100 },
              duration: { type: 'number', title: 'Duration (sec)', minimum: 1 },
              visualAlert: { type: 'boolean', title: 'Visual Alert (Strobe)' },
              message: { type: 'string', title: 'Voice Message ID' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['sirenId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' }, pattern: { 'ui:widget': 'select' } },
          formData: { sirenId: 'SIREN-001', command: 'deactivate', pattern: 'continuous', volume: 80, visualAlert: true, timestamp: new Date().toISOString() }
        }
      },
      gateway: {
        smart: {
          name: 'Smart Gateway',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'industry_40', 'smart_farm', 'smart_energy', 'health_medical'],
          schema: {
            type: 'object',
            title: 'Gateway Status',
            properties: {
              systemInfo: {
                type: 'object', title: 'System Information',
                properties: {
                  cpuUsage: { type: 'number', title: 'CPU Usage (%)', minimum: 0, maximum: 100 },
                  memoryUsage: { type: 'number', title: 'Memory Usage (%)', minimum: 0, maximum: 100 },
                  diskUsage: { type: 'number', title: 'Disk Usage (%)' },
                  temperature: { type: 'number', title: 'CPU Temperature (°C)' }
                }
              },
              networkInfo: {
                type: 'object', title: 'Network Information',
                properties: {
                  connectedDevices: { type: 'number', title: 'Connected Devices' },
                  dataRate: { type: 'number', title: 'Data Rate (kbps)' },
                  signalStrength: { type: 'number', title: 'Signal Strength (dBm)' }
                }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['timestamp']
          },
          uiSchema: {},
          formData: { systemInfo: { cpuUsage: 25, memoryUsage: 60, diskUsage: 40, temperature: 45 }, networkInfo: { connectedDevices: 12, dataRate: 1024, signalStrength: -65 }, timestamp: new Date().toISOString() }
        },
        edgeComputing: {
          name: 'Edge Computing Gateway',
          icon: <Radio className="h-4 w-4" />,
          industries: ['industry_40', 'smart_city'],
          schema: {
            type: 'object',
            title: 'Edge Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway ID' },
              processingLoad: { type: 'number', title: 'Processing Load (%)', minimum: 0, maximum: 100 },
              modelInference: { type: 'object', title: 'ML Model Stats', properties: { modelsLoaded: { type: 'integer' }, inferencePerSec: { type: 'number' }, accuracy: { type: 'number' } } },
              dataBuffered: { type: 'number', title: 'Data Buffered (MB)' },
              cloudSync: { type: 'string', enum: ['synced', 'syncing', 'offline'], title: 'Cloud Sync Status' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'timestamp']
          },
          uiSchema: { cloudSync: { 'ui:widget': 'select' } },
          formData: { gatewayId: 'EDGE-001', processingLoad: 45, cloudSync: 'synced', timestamp: new Date().toISOString() }
        },
        healthcareGateway: {
          name: 'Healthcare Data Gateway',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Healthcare Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway ID' },
              connectedDevices: { type: 'integer', title: 'Connected Medical Devices', minimum: 0 },
              hl7MessagesPerMin: { type: 'number', title: 'HL7 Messages/min' },
              fhirTransactions: { type: 'number', title: 'FHIR Transactions/min' },
              dataIntegrity: { type: 'string', enum: ['verified', 'pending', 'error'], title: 'Data Integrity' },
              hipaaCompliant: { type: 'boolean', title: 'HIPAA Compliant' },
              encryptionStatus: { type: 'string', enum: ['aes256', 'tls13', 'none'], title: 'Encryption' },
              batteryBackup: { type: 'number', title: 'Battery Backup (%)', minimum: 0, maximum: 100 },
              lastAuditLog: { type: 'string', format: 'date-time', title: 'Last Audit Log' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'connectedDevices', 'timestamp']
          },
          uiSchema: { dataIntegrity: { 'ui:widget': 'select' }, encryptionStatus: { 'ui:widget': 'select' } },
          formData: { gatewayId: 'HCG-001', connectedDevices: 15, hl7MessagesPerMin: 120, hipaaCompliant: true, encryptionStatus: 'aes256', dataIntegrity: 'verified', timestamp: new Date().toISOString() }
        },
        industrialGateway: {
          name: 'Industrial Protocol Gateway',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Industrial Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway ID' },
              protocols: { type: 'array', items: { type: 'string', enum: ['modbus', 'opcua', 'profinet', 'ethernet_ip', 'mqtt'] }, title: 'Active Protocols' },
              plcConnections: { type: 'integer', title: 'PLC Connections', minimum: 0 },
              dataPointsScanned: { type: 'integer', title: 'Data Points Scanned' },
              scanCycleTime: { type: 'number', title: 'Scan Cycle (ms)' },
              bufferUtilization: { type: 'number', title: 'Buffer Utilization (%)', minimum: 0, maximum: 100 },
              redundancyStatus: { type: 'string', enum: ['primary', 'secondary', 'standalone'], title: 'Redundancy Status' },
              opcuaSubscriptions: { type: 'integer', title: 'OPC UA Subscriptions' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'plcConnections', 'timestamp']
          },
          uiSchema: { redundancyStatus: { 'ui:widget': 'select' } },
          formData: { gatewayId: 'IND-GW-001', plcConnections: 8, dataPointsScanned: 5000, scanCycleTime: 100, bufferUtilization: 35, redundancyStatus: 'primary', timestamp: new Date().toISOString() }
        },
        farmGateway: {
          name: 'Agricultural Data Gateway',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Farm Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway ID' },
              fieldSensors: { type: 'integer', title: 'Field Sensors Connected', minimum: 0 },
              irrigationZones: { type: 'integer', title: 'Irrigation Zones Managed' },
              weatherDataAge: { type: 'number', title: 'Weather Data Age (min)' },
              solarPower: { type: 'number', title: 'Solar Power Available (W)' },
              batteryLevel: { type: 'number', title: 'Battery Level (%)', minimum: 0, maximum: 100 },
              cellularSignal: { type: 'number', title: 'Cellular Signal (dBm)' },
              loraDevices: { type: 'integer', title: 'LoRa Devices Connected' },
              lastDataSync: { type: 'string', format: 'date-time', title: 'Last Cloud Sync' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'fieldSensors', 'timestamp']
          },
          uiSchema: {},
          formData: { gatewayId: 'FARM-GW-001', fieldSensors: 25, irrigationZones: 4, batteryLevel: 85, loraDevices: 12, timestamp: new Date().toISOString() }
        },
        energyGateway: {
          name: 'Smart Grid Gateway',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Energy Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway ID' },
              metersConnected: { type: 'integer', title: 'Smart Meters Connected', minimum: 0 },
              totalEnergyFlow: { type: 'number', title: 'Total Energy Flow (kW)' },
              gridFrequency: { type: 'number', title: 'Grid Frequency (Hz)', minimum: 45, maximum: 65 },
              voltageStability: { type: 'string', enum: ['stable', 'fluctuating', 'critical'], title: 'Voltage Stability' },
              derConnections: { type: 'integer', title: 'DER Connections', description: 'Distributed Energy Resources' },
              demandResponse: { type: 'boolean', title: 'Demand Response Active' },
              loadShedding: { type: 'boolean', title: 'Load Shedding Active' },
              peakDemand: { type: 'number', title: 'Peak Demand (kW)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'metersConnected', 'timestamp']
          },
          uiSchema: { voltageStability: { 'ui:widget': 'select' } },
          formData: { gatewayId: 'ENG-GW-001', metersConnected: 500, totalEnergyFlow: 2500, gridFrequency: 50, voltageStability: 'stable', derConnections: 15, timestamp: new Date().toISOString() }
        },
        loraGateway: {
          name: 'LoRaWAN Gateway',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'smart_farm', 'smart_energy'],
          schema: {
            type: 'object',
            title: 'LoRaWAN Gateway Telemetry',
            properties: {
              gatewayId: { type: 'string', title: 'Gateway EUI' },
              devicesJoined: { type: 'integer', title: 'Devices Joined', minimum: 0 },
              uplinkMessages: { type: 'integer', title: 'Uplink Messages/hour' },
              downlinkMessages: { type: 'integer', title: 'Downlink Messages/hour' },
              spreadingFactors: { type: 'object', title: 'SF Distribution', properties: { sf7: { type: 'integer' }, sf8: { type: 'integer' }, sf9: { type: 'integer' }, sf10: { type: 'integer' }, sf11: { type: 'integer' }, sf12: { type: 'integer' } } },
              rssiAverage: { type: 'number', title: 'Average RSSI (dBm)' },
              snrAverage: { type: 'number', title: 'Average SNR (dB)' },
              networkServer: { type: 'string', enum: ['connected', 'disconnected', 'reconnecting'], title: 'Network Server' },
              gpsLocation: { type: 'object', title: 'GPS', properties: { latitude: { type: 'number' }, longitude: { type: 'number' }, altitude: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['gatewayId', 'devicesJoined', 'timestamp']
          },
          uiSchema: { networkServer: { 'ui:widget': 'select' } },
          formData: { gatewayId: 'LORA-GW-001', devicesJoined: 85, uplinkMessages: 2500, downlinkMessages: 150, rssiAverage: -95, snrAverage: 8.5, networkServer: 'connected', timestamp: new Date().toISOString() }
        },
        protocolBridge: {
          name: 'Protocol Bridge Gateway',
          icon: <Radio className="h-4 w-4" />,
          industries: ['industry_40', 'smart_city', 'smart_energy', 'health_medical', 'smart_farm'],
          schema: {
            type: 'object',
            title: 'Protocol Bridge Telemetry',
            properties: {
              bridgeId: { type: 'string', title: 'Bridge ID' },
              sourceProtocol: { type: 'string', enum: ['modbus', 'bacnet', 'knx', 'zigbee', 'zwave', 'bluetooth', 'canbus'], title: 'Source Protocol' },
              targetProtocol: { type: 'string', enum: ['mqtt', 'http', 'coap', 'opcua', 'amqp'], title: 'Target Protocol' },
              messagesTranslated: { type: 'integer', title: 'Messages Translated/min' },
              translationErrors: { type: 'integer', title: 'Translation Errors' },
              queueDepth: { type: 'integer', title: 'Queue Depth' },
              latencyMs: { type: 'number', title: 'Translation Latency (ms)' },
              devicesMapped: { type: 'integer', title: 'Devices Mapped' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['bridgeId', 'sourceProtocol', 'targetProtocol', 'timestamp']
          },
          uiSchema: { sourceProtocol: { 'ui:widget': 'select' }, targetProtocol: { 'ui:widget': 'select' } },
          formData: { bridgeId: 'BRIDGE-001', sourceProtocol: 'modbus', targetProtocol: 'mqtt', messagesTranslated: 500, translationErrors: 0, latencyMs: 5, devicesMapped: 20, timestamp: new Date().toISOString() }
        }
      },
      controller: {
        hvac: {
          name: 'HVAC Controller',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['smart_city', 'health_medical'],
          schema: {
            type: 'object',
            title: 'HVAC Control Command',
            properties: {
              mode: { type: 'string', enum: ['heating', 'cooling', 'auto', 'off'], title: 'Operation Mode' },
              targetTemperature: { type: 'number', title: 'Target Temperature (°C)', minimum: 16, maximum: 30 },
              fanSpeed: { type: 'string', enum: ['low', 'medium', 'high', 'auto'], title: 'Fan Speed' },
              schedule: {
                type: 'object', title: 'Schedule',
                properties: { enabled: { type: 'boolean', title: 'Schedule Enabled' }, startTime: { type: 'string', title: 'Start Time' }, endTime: { type: 'string', title: 'End Time' } }
              },
              timestamp: { type: 'string', format: 'date-time', title: 'Command Timestamp' }
            },
            required: ['mode', 'targetTemperature']
          },
          uiSchema: { mode: { 'ui:widget': 'select' }, fanSpeed: { 'ui:widget': 'select' }, targetTemperature: { 'ui:widget': 'range' } },
          formData: { mode: 'auto', targetTemperature: 22, fanSpeed: 'auto', schedule: { enabled: true, startTime: '08:00', endTime: '18:00' }, timestamp: new Date().toISOString() }
        },
        lightingController: {
          name: 'Lighting Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_city', 'smart_farm'],
          schema: {
            type: 'object',
            title: 'Lighting Control',
            properties: {
              zoneId: { type: 'string', title: 'Zone ID' },
              brightness: { type: 'number', title: 'Brightness (%)', minimum: 0, maximum: 100 },
              colorTemperature: { type: 'number', title: 'Color Temperature (K)', minimum: 2700, maximum: 6500 },
              mode: { type: 'string', enum: ['manual', 'auto', 'schedule', 'scene'], title: 'Mode' },
              scene: { type: 'string', enum: ['daylight', 'warm', 'cool', 'focus', 'relax'], title: 'Scene' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['zoneId', 'brightness', 'timestamp']
          },
          uiSchema: { brightness: { 'ui:widget': 'range' }, mode: { 'ui:widget': 'select' }, scene: { 'ui:widget': 'select' } },
          formData: { zoneId: 'LGT-001', brightness: 75, colorTemperature: 4000, mode: 'auto', timestamp: new Date().toISOString() }
        },
        industrialPLC: {
          name: 'Industrial PLC Controller',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'PLC Controller Command',
            properties: {
              plcId: { type: 'string', title: 'PLC ID' },
              programNumber: { type: 'integer', title: 'Program Number', minimum: 1 },
              runMode: { type: 'string', enum: ['run', 'stop', 'pause', 'step'], title: 'Run Mode' },
              registers: { type: 'object', title: 'Register Setpoints', additionalProperties: { type: 'number' } },
              digitalOutputs: { type: 'array', items: { type: 'object', properties: { address: { type: 'string' }, value: { type: 'boolean' } } }, title: 'Digital Outputs' },
              analogOutputs: { type: 'array', items: { type: 'object', properties: { address: { type: 'string' }, value: { type: 'number' } } }, title: 'Analog Outputs' },
              watchdogEnabled: { type: 'boolean', title: 'Watchdog Enabled' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['plcId', 'runMode', 'timestamp']
          },
          uiSchema: { runMode: { 'ui:widget': 'select' } },
          formData: { plcId: 'PLC-001', programNumber: 1, runMode: 'run', watchdogEnabled: true, timestamp: new Date().toISOString() }
        },
        processController: {
          name: 'Process Automation Controller',
          icon: <Factory className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Process Control Command',
            properties: {
              processId: { type: 'string', title: 'Process ID' },
              batchNumber: { type: 'string', title: 'Batch Number' },
              recipe: { type: 'string', title: 'Recipe Name' },
              stage: { type: 'integer', title: 'Current Stage', minimum: 1 },
              setpoints: {
                type: 'object', title: 'Process Setpoints',
                properties: {
                  temperature: { type: 'number', title: 'Temperature (°C)' },
                  pressure: { type: 'number', title: 'Pressure (bar)' },
                  flowRate: { type: 'number', title: 'Flow Rate (L/min)' },
                  mixSpeed: { type: 'number', title: 'Mix Speed (RPM)' }
                }
              },
              controlMode: { type: 'string', enum: ['auto', 'manual', 'cascade', 'ratio'], title: 'Control Mode' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['processId', 'controlMode', 'timestamp']
          },
          uiSchema: { controlMode: { 'ui:widget': 'select' } },
          formData: { processId: 'PROC-001', stage: 1, controlMode: 'auto', setpoints: { temperature: 85, pressure: 2.5, flowRate: 100 }, timestamp: new Date().toISOString() }
        },
        roboticController: {
          name: 'Robotic Arm Controller',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['industry_40'],
          schema: {
            type: 'object',
            title: 'Robotic Controller Command',
            properties: {
              robotId: { type: 'string', title: 'Robot ID' },
              program: { type: 'string', title: 'Program Name' },
              mode: { type: 'string', enum: ['auto', 'manual', 'teach', 'remote'], title: 'Operation Mode' },
              speed: { type: 'number', title: 'Speed (%)', minimum: 0, maximum: 100 },
              position: {
                type: 'object', title: 'Target Position',
                properties: { x: { type: 'number' }, y: { type: 'number' }, z: { type: 'number' }, rx: { type: 'number' }, ry: { type: 'number' }, rz: { type: 'number' } }
              },
              tool: { type: 'integer', title: 'Active Tool', minimum: 0 },
              gripper: { type: 'string', enum: ['open', 'close', 'partial'], title: 'Gripper State' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['robotId', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' }, gripper: { 'ui:widget': 'select' }, speed: { 'ui:widget': 'range' } },
          formData: { robotId: 'ROB-001', mode: 'auto', speed: 75, tool: 1, gripper: 'close', timestamp: new Date().toISOString() }
        },
        irrigationSystemController: {
          name: 'Irrigation System Controller',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Irrigation Control Command',
            properties: {
              systemId: { type: 'string', title: 'System ID' },
              zones: {
                type: 'array', title: 'Zone Controls',
                items: {
                  type: 'object',
                  properties: {
                    zoneId: { type: 'string' },
                    enabled: { type: 'boolean' },
                    duration: { type: 'number', title: 'Duration (min)' },
                    flowTarget: { type: 'number', title: 'Flow Target (L/min)' }
                  }
                }
              },
              mode: { type: 'string', enum: ['manual', 'schedule', 'sensor-based', 'off'], title: 'Operation Mode' },
              soilMoistureThreshold: { type: 'number', title: 'Soil Moisture Threshold (%)', minimum: 0, maximum: 100 },
              fertigation: { type: 'object', title: 'Fertigation', properties: { enabled: { type: 'boolean' }, concentration: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['systemId', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' } },
          formData: { systemId: 'IRR-SYS-001', mode: 'sensor-based', soilMoistureThreshold: 30, fertigation: { enabled: false }, timestamp: new Date().toISOString() }
        },
        greenhouseController: {
          name: 'Greenhouse Climate Controller',
          icon: <Thermometer className="h-4 w-4" />,
          industries: ['smart_farm'],
          schema: {
            type: 'object',
            title: 'Greenhouse Control Command',
            properties: {
              greenhouseId: { type: 'string', title: 'Greenhouse ID' },
              climate: {
                type: 'object', title: 'Climate Setpoints',
                properties: {
                  temperatureMin: { type: 'number', title: 'Min Temperature (°C)' },
                  temperatureMax: { type: 'number', title: 'Max Temperature (°C)' },
                  humidityMin: { type: 'number', title: 'Min Humidity (%)' },
                  humidityMax: { type: 'number', title: 'Max Humidity (%)' },
                  co2Target: { type: 'number', title: 'CO2 Target (ppm)' }
                }
              },
              ventilation: { type: 'string', enum: ['closed', 'natural', 'forced', 'auto'], title: 'Ventilation Mode' },
              shading: { type: 'number', title: 'Shade Screen (%)', minimum: 0, maximum: 100 },
              lighting: { type: 'object', title: 'Supplemental Lighting', properties: { enabled: { type: 'boolean' }, intensity: { type: 'number' }, duration: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['greenhouseId', 'ventilation', 'timestamp']
          },
          uiSchema: { ventilation: { 'ui:widget': 'select' }, shading: { 'ui:widget': 'range' } },
          formData: { greenhouseId: 'GH-001', climate: { temperatureMin: 18, temperatureMax: 28, humidityMin: 60, humidityMax: 85, co2Target: 1000 }, ventilation: 'auto', shading: 50, timestamp: new Date().toISOString() }
        },
        medicalDeviceController: {
          name: 'Medical Equipment Controller',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Medical Device Control',
            properties: {
              deviceId: { type: 'string', title: 'Device ID' },
              patientId: { type: 'string', title: 'Patient ID' },
              mode: { type: 'string', enum: ['standby', 'active', 'calibration', 'maintenance'], title: 'Operation Mode' },
              parameters: {
                type: 'object', title: 'Treatment Parameters',
                properties: {
                  intensity: { type: 'number', title: 'Intensity (%)' },
                  duration: { type: 'number', title: 'Duration (min)' },
                  frequency: { type: 'number', title: 'Frequency (Hz)' }
                }
              },
              alarms: { type: 'object', title: 'Alarm Settings', properties: { soundEnabled: { type: 'boolean' }, visualEnabled: { type: 'boolean' }, escalationLevel: { type: 'integer' } } },
              safetyOverride: { type: 'boolean', title: 'Safety Override (Admin Only)' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['deviceId', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' } },
          formData: { deviceId: 'MED-CTL-001', mode: 'standby', parameters: { intensity: 50, duration: 30 }, alarms: { soundEnabled: true, visualEnabled: true }, safetyOverride: false, timestamp: new Date().toISOString() }
        },
        infusionPumpController: {
          name: 'Infusion Pump Controller',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['health_medical'],
          schema: {
            type: 'object',
            title: 'Infusion Pump Control',
            properties: {
              pumpId: { type: 'string', title: 'Pump ID' },
              patientId: { type: 'string', title: 'Patient ID' },
              drugName: { type: 'string', title: 'Drug Name' },
              concentration: { type: 'number', title: 'Drug Concentration (mg/mL)' },
              infusionRate: { type: 'number', title: 'Infusion Rate (mL/hr)', minimum: 0 },
              volumeToBeInfused: { type: 'number', title: 'VTBI (mL)' },
              mode: { type: 'string', enum: ['continuous', 'intermittent', 'pca', 'taper'], title: 'Infusion Mode' },
              primarySecondary: { type: 'string', enum: ['primary', 'secondary'], title: 'Line Type' },
              occlusion: { type: 'object', title: 'Occlusion Limits', properties: { upstream: { type: 'number' }, downstream: { type: 'number' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['pumpId', 'infusionRate', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' }, primarySecondary: { 'ui:widget': 'radio' } },
          formData: { pumpId: 'PUMP-001', infusionRate: 100, volumeToBeInfused: 500, mode: 'continuous', primarySecondary: 'primary', timestamp: new Date().toISOString() }
        },
        energyManagementController: {
          name: 'Energy Management Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy'],
          schema: {
            type: 'object',
            title: 'Energy Management Control',
            properties: {
              controllerId: { type: 'string', title: 'Controller ID' },
              mode: { type: 'string', enum: ['normal', 'peak-shaving', 'load-shifting', 'emergency'], title: 'Operation Mode' },
              gridImportLimit: { type: 'number', title: 'Grid Import Limit (kW)' },
              gridExportLimit: { type: 'number', title: 'Grid Export Limit (kW)' },
              batteryTargetSoC: { type: 'number', title: 'Battery Target SoC (%)', minimum: 0, maximum: 100 },
              loadPriorities: {
                type: 'array', title: 'Load Priorities',
                items: { type: 'object', properties: { loadId: { type: 'string' }, priority: { type: 'integer' }, canShed: { type: 'boolean' } } }
              },
              derDispatch: { type: 'object', title: 'DER Dispatch', properties: { solarCurtailment: { type: 'number' }, batteryDischarge: { type: 'number' }, gensetStart: { type: 'boolean' } } },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['controllerId', 'mode', 'timestamp']
          },
          uiSchema: { mode: { 'ui:widget': 'select' }, batteryTargetSoC: { 'ui:widget': 'range' } },
          formData: { controllerId: 'EMS-001', mode: 'normal', gridImportLimit: 500, batteryTargetSoC: 80, timestamp: new Date().toISOString() }
        },
        evChargingController: {
          name: 'EV Charging Controller',
          icon: <Zap className="h-4 w-4" />,
          industries: ['smart_energy', 'smart_city'],
          schema: {
            type: 'object',
            title: 'EV Charging Control',
            properties: {
              stationId: { type: 'string', title: 'Station ID' },
              connectorId: { type: 'integer', title: 'Connector ID' },
              command: { type: 'string', enum: ['start', 'stop', 'suspend', 'resume', 'unlock'], title: 'Command' },
              chargingProfile: {
                type: 'object', title: 'Charging Profile',
                properties: {
                  maxPower: { type: 'number', title: 'Max Power (kW)' },
                  targetSoC: { type: 'number', title: 'Target SoC (%)' },
                  departureTime: { type: 'string', format: 'date-time' }
                }
              },
              tariffOverride: { type: 'number', title: 'Tariff Override ($/kWh)' },
              vehicleId: { type: 'string', title: 'Vehicle ID' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['stationId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' } },
          formData: { stationId: 'EVSE-001', connectorId: 1, command: 'start', chargingProfile: { maxPower: 22, targetSoC: 80 }, timestamp: new Date().toISOString() }
        },
        accessController: {
          name: 'Access Control System',
          icon: <Radio className="h-4 w-4" />,
          industries: ['smart_city', 'health_medical', 'industry_40'],
          schema: {
            type: 'object',
            title: 'Access Control Command',
            properties: {
              controllerId: { type: 'string', title: 'Controller ID' },
              doorId: { type: 'string', title: 'Door/Gate ID' },
              command: { type: 'string', enum: ['lock', 'unlock', 'pulse', 'hold_open', 'lockdown'], title: 'Command' },
              duration: { type: 'number', title: 'Duration (seconds)' },
              scheduleOverride: { type: 'boolean', title: 'Schedule Override' },
              accessLevel: { type: 'integer', title: 'Required Access Level', minimum: 0, maximum: 10 },
              antiPassback: { type: 'boolean', title: 'Anti-Passback Enabled' },
              interlocks: { type: 'array', items: { type: 'string' }, title: 'Interlock Doors' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['controllerId', 'doorId', 'command', 'timestamp']
          },
          uiSchema: { command: { 'ui:widget': 'select' } },
          formData: { controllerId: 'ACC-001', doorId: 'DOOR-001', command: 'lock', antiPassback: true, timestamp: new Date().toISOString() }
        },
        buildingAutomationController: {
          name: 'Building Automation Controller',
          icon: <Cpu className="h-4 w-4" />,
          industries: ['smart_city', 'smart_energy'],
          schema: {
            type: 'object',
            title: 'Building Automation Control',
            properties: {
              buildingId: { type: 'string', title: 'Building ID' },
              zoneId: { type: 'string', title: 'Zone ID' },
              hvacSetpoint: { type: 'number', title: 'HVAC Setpoint (°C)' },
              lightingLevel: { type: 'number', title: 'Lighting Level (%)', minimum: 0, maximum: 100 },
              shadingPosition: { type: 'number', title: 'Shading Position (%)', minimum: 0, maximum: 100 },
              occupancyMode: { type: 'string', enum: ['occupied', 'unoccupied', 'standby', 'holiday'], title: 'Occupancy Mode' },
              scheduleOverride: { type: 'boolean', title: 'Schedule Override' },
              demandLimit: { type: 'number', title: 'Demand Limit (kW)' },
              alarmReset: { type: 'boolean', title: 'Reset All Alarms' },
              timestamp: { type: 'string', format: 'date-time', title: 'Timestamp' }
            },
            required: ['buildingId', 'occupancyMode', 'timestamp']
          },
          uiSchema: { occupancyMode: { 'ui:widget': 'select' }, lightingLevel: { 'ui:widget': 'range' }, shadingPosition: { 'ui:widget': 'range' } },
          formData: { buildingId: 'BLD-001', zoneId: 'ZONE-1', hvacSetpoint: 22, lightingLevel: 75, occupancyMode: 'occupied', timestamp: new Date().toISOString() }
        }
      }
    };

    // Map edge_gateway to gateway, and other specialized types to their base types
    const baseType = deviceType.includes('gateway') ? 'gateway' :
                     deviceType.includes('sensor') ? 'sensor' :
                     deviceType.includes('actuator') ? 'actuator' :
                     deviceType.includes('controller') ? 'controller' :
                     deviceType;

    const typeTemplates = allTemplates[baseType] || {};

    // Skip filtering if showAllTemplates is enabled
    if (showAllTemplates) {
      return typeTemplates;
    }

    // Filter templates by industry if specified
    if (industry && industry !== 'general') {
      const filtered: Record<string, any> = {};
      Object.entries(typeTemplates).forEach(([key, template]: [string, any]) => {
        // Include if template has no industries restriction OR if current industry is in template's industries list
        if (!template.industries || template.industries.includes(industry)) {
          filtered[key] = template;
        }
      });
      return filtered;
    }

    return typeTemplates;
  };

  const templates = getSchemaTemplates();

  const loadTemplate = (templateKey: string) => {
    const template = templates[templateKey];
    if (template) {
      console.log(`DeviceSchemaEditor: Loading template '${templateKey}'`);
      
      setSchema(template.schema);
      setUiSchema(template.uiSchema);
      setFormData(template.formData);
      setSelectedTemplate(templateKey);
      const metadata = {
        templateId: templateKey,
        templateName: template.name,
        customized: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      setSchemaMetadata(metadata);
      
      onSchemaChange({
        schema: template.schema,
        uiSchema: template.uiSchema,
        formData: template.formData,
        metadata
      });

      // Mark as saved since template is auto-saved to parent
      lastSavedSchemaRef.current = JSON.stringify({
        schema: template.schema,
        uiSchema: template.uiSchema,
        formData: template.formData
      });
      setHasUnsavedChanges(false);

      // Show template loaded toast
      toast.success(`Template "${template.name}" loaded`, {
        duration: 3000,
        description: 'You can now customize the schema or save as-is.'
      });
    }
  };

  const loadSavedTemplate = (template: any) => {
    console.log('DeviceSchemaEditor: Loading saved template', template);
    
    setSchema(template.schema);
    setUiSchema(template.uiSchema || {});
    setFormData({});
    setSelectedTemplate('');
    const metadata = {
      templateId: template.id,
      templateName: template.name,
      customized: false,
      createdAt: template.createdAt,
      updatedAt: template.modifiedAt || template.createdAt,
      savedTemplate: true
    };
    setSchemaMetadata(metadata);
    
    onSchemaChange({
      schema: template.schema,
      uiSchema: template.uiSchema || {},
      formData: {},
      metadata
    });

    // Mark as saved since saved template is auto-saved to parent
    lastSavedSchemaRef.current = JSON.stringify({
      schema: template.schema,
      uiSchema: template.uiSchema || {},
      formData: {}
    });
    setHasUnsavedChanges(false);

    toast.success(`Saved template "${template.name}" loaded`, {
      duration: 3000,
      description: `Template with ${template.sensors.length} sensors loaded successfully.`
    });
  };

  const resetSchema = () => {
    console.log('DeviceSchemaEditor: Reset button clicked');

    setSchema({});
    setUiSchema({});
    setFormData({});
    setSelectedTemplate('');
    setSchemaMetadata({});
    onSchemaChange({
      schema: {},
      uiSchema: {},
      formData: {},
      metadata: {}
    });

    // Mark as saved since reset is auto-saved to parent
    lastSavedSchemaRef.current = JSON.stringify({
      schema: {},
      uiSchema: {},
      formData: {}
    });
    setHasUnsavedChanges(false);

    // Show reset toast
    toast.info('Schema reset to empty state', {
      duration: 3000,
      description: 'All schema configurations have been cleared.'
    });
  };

  const saveSchema = () => {
    console.log('DeviceSchemaEditor: Save Schema button clicked');
    console.log('Current schema:', schema);
    console.log('Current uiSchema:', uiSchema);
    console.log('Current formData:', formData);

    // Update metadata to mark as customized if changed
    const updatedMetadata = {
      ...schemaMetadata,
      customized: true,
      updatedAt: new Date().toISOString()
    };
    setSchemaMetadata(updatedMetadata);

    // Call the parent's onSchemaChange callback
    onSchemaChange({
      schema,
      uiSchema,
      formData,
      metadata: updatedMetadata
    });

    // Mark current state as saved (reset dirty state)
    lastSavedSchemaRef.current = JSON.stringify({ schema, uiSchema, formData });
    setHasUnsavedChanges(false);

    // Show success toast
    toast.success('Schema saved! Remember to click "Update Device" or "Create Device" to persist changes.', {
      duration: 4000,
      description: 'The schema has been updated in the form.'
    });
  };

  const handleSchemaAssistantGenerated = (generatedSchema: {
    schema: RJSFSchema;
    uiSchema: UiSchema;
    formData: Record<string, any>;
    metadata?: any;
  }) => {
    // Update the schema editor with generated schema
    setSchema(generatedSchema.schema);
    setUiSchema(generatedSchema.uiSchema);
    setFormData(generatedSchema.formData || {});
    setSelectedTemplate(''); // Clear any selected template
    
    // Switch to schema tab to show the generated schema
    setCurrentTab('schema');
    
    // Create metadata for AI-generated schema
    const metadata = {
      templateId: 'ai-generated',
      templateName: 'AI Assistant Generated',
      customized: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...generatedSchema.metadata
    };
    setSchemaMetadata(metadata);
    
    // Notify parent component
    onSchemaChange({
      schema: generatedSchema.schema,
      uiSchema: generatedSchema.uiSchema,
      formData: generatedSchema.formData || {},
      metadata
    });

    // Mark as saved since AI-generated schema is auto-saved to parent
    lastSavedSchemaRef.current = JSON.stringify({
      schema: generatedSchema.schema,
      uiSchema: generatedSchema.uiSchema,
      formData: generatedSchema.formData || {}
    });
    setHasUnsavedChanges(false);

    // Show success message
    toast.success('Schema generated successfully!', {
      duration: 4000,
      description: 'AI Assistant has created a combined schema for your selected sensors.'
    });
  };

  useEffect(() => {
    if (initialSchema) {
      setSchema(initialSchema.schema);
      setUiSchema(initialSchema.uiSchema || {});
      setFormData(initialSchema.formData || {});
      setSchemaMetadata(initialSchema.metadata || {});
      setSelectedTemplate(initialSchema.metadata?.templateId || '');
    }
  }, [initialSchema]);

  // Load saved templates from localStorage
  useEffect(() => {
    const loadSavedTemplates = () => {
      try {
        const saved = localStorage.getItem('tesa_schema_templates');
        if (saved) {
          const templates = JSON.parse(saved);
          setSavedTemplates(templates);
        }
      } catch (error) {
        console.error('Error loading saved templates:', error);
      }
    };
    
    loadSavedTemplates();
    
    // Listen for storage events to sync across tabs
    window.addEventListener('storage', loadSavedTemplates);
    return () => window.removeEventListener('storage', loadSavedTemplates);
  }, []);

  // Detect unsaved changes by comparing current state to last saved state
  useEffect(() => {
    const currentState = JSON.stringify({ schema, uiSchema, formData });
    const isDirty = currentState !== lastSavedSchemaRef.current;

    if (isDirty !== hasUnsavedChanges) {
      setHasUnsavedChanges(isDirty);
    }
  }, [schema, uiSchema, formData, hasUnsavedChanges]);

  // Notify parent component when unsaved changes state changes
  useEffect(() => {
    if (onHasUnsavedChanges) {
      onHasUnsavedChanges(hasUnsavedChanges);
    }
  }, [hasUnsavedChanges, onHasUnsavedChanges]);

  const getDeviceTypeIcon = () => {
    if (deviceType.includes('sensor')) return <Thermometer className="h-4 w-4" />;
    if (deviceType.includes('actuator')) return <Zap className="h-4 w-4" />;
    if (deviceType.includes('gateway')) return <Radio className="h-4 w-4" />;
    if (deviceType.includes('controller')) return <Cpu className="h-4 w-4" />;
    // Default icon
    return <Thermometer className="h-4 w-4" />;
  };

  return (
    <div className="w-full min-w-0 space-y-4 overflow-visible">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          {getDeviceTypeIcon()}
          <h3 className="text-lg font-semibold">
            {deviceType.charAt(0).toUpperCase() + deviceType.slice(1)} Schema Editor
          </h3>
          <div className="flex items-center gap-2">
            {selectedTemplate && templates[selectedTemplate] && (
              <Badge variant="secondary" className="flex items-center gap-1">
                {templates[selectedTemplate].icon}
                {templates[selectedTemplate].name}
              </Badge>
            )}
            {schemaMetadata.templateId === 'ai-generated' && (
              <Badge variant="secondary" className="flex items-center gap-1 bg-gradient-to-r from-blue-500/20 to-purple-600/20">
                <Sparkles className="h-3 w-3" />
                AI Generated
              </Badge>
            )}
            {schemaMetadata.customized && (
              <Badge variant="outline" className="text-xs">
                Customized
              </Badge>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSchemaAssistantOpen(true)}
            disabled={disabled}
            className="bg-gradient-to-r from-blue-500/10 to-purple-600/10 hover:from-blue-500/20 hover:to-purple-600/20 border-blue-500/50"
          >
            <Sparkles className="h-4 w-4 mr-1" />
            Data Schema Assistant
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={resetSchema}
            disabled={disabled}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Reset
          </Button>
          <Button
            size="sm"
            onClick={saveSchema}
            disabled={disabled}
            title={disabled ? "Cannot save schema while device is being created" : "Save schema changes"}
          >
            <Save className="h-4 w-4 mr-1" />
            Save Schema
          </Button>
        </div>
      </div>

      <Tabs value={currentTab} onValueChange={setCurrentTab} className="w-full min-w-0 overflow-visible">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="template" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="schema" className="flex items-center gap-2">
            <Schema className="h-4 w-4" />
            Schema
          </TabsTrigger>
          <TabsTrigger value="preview" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent value="template" className="w-full min-w-0 space-y-4 overflow-visible">
          {/* Current Schema Display */}
          {Object.keys(schema).length > 0 && showCurrentSchema && (
            <Card className="border-2 border-primary/50 bg-gradient-to-br from-primary/5 to-primary/10">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Schema className="h-5 w-5" />
                    Current Schema
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowCurrentSchema(false)}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-start gap-4">
                  {/* Template Icon and Info */}
                  <div className="flex-shrink-0">
                    {schemaMetadata.templateId === 'ai-generated' ? (
                      <div className="h-12 w-12 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-600/20 flex items-center justify-center">
                        <Sparkles className="h-6 w-6 text-blue-600" />
                      </div>
                    ) : selectedTemplate && templates[selectedTemplate] ? (
                      <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                        {React.cloneElement(templates[selectedTemplate].icon, { className: "h-6 w-6" })}
                      </div>
                    ) : (
                      <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center">
                        <Schema className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                  
                  {/* Schema Details */}
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold">
                        {schemaMetadata.templateName || 'Custom Schema'}
                      </h4>
                      {schemaMetadata.customized && (
                        <Badge variant="outline" className="text-xs">Customized</Badge>
                      )}
                    </div>
                    
                    {/* Schema Properties Preview */}
                    <div className="text-sm text-muted-foreground">
                      {schema.properties && (
                        <div className="space-y-1">
                          <div>Properties: {Object.keys(schema.properties).length}</div>
                          <div className="flex flex-wrap gap-1">
                            {Object.keys(schema.properties).slice(0, 5).map((prop) => (
                              <Badge key={prop} variant="secondary" className="text-xs">
                                {prop}
                              </Badge>
                            ))}
                            {Object.keys(schema.properties).length > 5 && (
                              <Badge variant="secondary" className="text-xs">
                                +{Object.keys(schema.properties).length - 5} more
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Timestamps */}
                    {(schemaMetadata.createdAt || schemaMetadata.updatedAt) && (
                      <div className="text-xs text-muted-foreground pt-1 border-t">
                        {schemaMetadata.createdAt && (
                          <div>Created: {new Date(schemaMetadata.createdAt).toLocaleDateString()}</div>
                        )}
                        {schemaMetadata.updatedAt && schemaMetadata.updatedAt !== schemaMetadata.createdAt && (
                          <div>Updated: {new Date(schemaMetadata.updatedAt).toLocaleDateString()}</div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {/* Actions */}
                  <div className="flex-shrink-0 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentTab('schema')}
                      disabled={disabled}
                    >
                      <Code className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentTab('preview')}
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      Preview
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          
          {!showCurrentSchema && Object.keys(schema).length > 0 && (
            <Alert className="bg-primary/5">
              <Info className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>You have a saved schema configuration</span>
                <Button variant="link" size="sm" onClick={() => setShowCurrentSchema(true)}>
                  Show current schema
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <Alert>
            <FileText className="h-4 w-4" />
            <AlertDescription>
              Select a pre-built template for {deviceType} data structure. Templates provide a starting point that you can customize.
            </AlertDescription>
          </Alert>

          {/* Show All Templates Toggle */}
          <div className="flex items-center justify-between bg-muted/50 rounded-lg px-4 py-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="show-all-templates" className="text-sm font-medium cursor-pointer">
                Show All Templates
              </Label>
              <span className="text-xs text-muted-foreground">
                {showAllTemplates ? '(All templates shown)' : `(Filtered by: ${industry || 'none'})`}
              </span>
            </div>
            <Switch
              id="show-all-templates"
              checked={showAllTemplates}
              onCheckedChange={setShowAllTemplates}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 w-full min-w-0">
            {/* AI Assistant Card */}
            <Card 
              className="cursor-pointer transition-all hover:shadow-lg border-2 border-dashed border-blue-500/50 bg-gradient-to-br from-blue-500/5 to-purple-600/5 hover:from-blue-500/10 hover:to-purple-600/10"
              onClick={() => !disabled && setSchemaAssistantOpen(true)}
            >
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Sparkles className="h-5 w-5 text-blue-600" />
                  Schema Assistant
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  <p className="mb-2">Create custom schemas by combining multiple sensors with AI assistance.</p>
                  <Badge variant="secondary" className="text-xs">
                    Recommended
                  </Badge>
                </div>
              </CardContent>
            </Card>
            
            {/* Saved Templates */}
            {savedTemplates.map((template) => {
              const isCurrentTemplate = schemaMetadata.templateId === template.id;
              return (
                <Card 
                  key={template.id}
                  className={`cursor-pointer transition-all hover:shadow-lg relative overflow-hidden ${
                    isCurrentTemplate ? 'border-2 border-primary bg-primary/5' : 'hover:bg-accent'
                  } bg-gradient-to-br from-green-500/5 to-emerald-600/5`}
                  onClick={() => !disabled && loadSavedTemplate(template)}
                >
                  {isCurrentTemplate && (
                    <div className="absolute top-2 right-2">
                      <Badge variant="default" className="text-xs">
                        Current
                      </Badge>
                    </div>
                  )}
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Save className="h-5 w-5 text-green-600" />
                      {template.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground">
                      <p className="mb-2">{template.description || 'Custom saved template'}</p>
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="secondary" className="text-xs">
                          {template.sensors.length} sensors
                        </Badge>
                        {template.tags && template.tags.map((tag: string) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <div className="text-xs">
                        Saved: {new Date(template.createdAt).toLocaleDateString()}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
            
            {/* Existing templates */}
            {Object.entries(templates).map(([key, template]) => {
              const isCurrentTemplate = selectedTemplate === key && !schemaMetadata.customized;
              return (
                <Card 
                  key={key} 
                  className={`cursor-pointer transition-all hover:shadow-lg relative overflow-hidden ${
                    isCurrentTemplate ? 'border-2 border-primary bg-primary/5' : 'hover:bg-accent'
                  }`}
                  onClick={() => !disabled && loadTemplate(key)}
                >
                  {isCurrentTemplate && (
                    <div className="absolute top-2 right-2">
                      <Badge variant="default" className="text-xs">
                        Current
                      </Badge>
                    </div>
                  )}
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                      {template.icon}
                      {template.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-muted-foreground">
                      Ready-to-use schema for {template.name.toLowerCase()} with industry-standard fields.
                    </div>
                    {template.schema.properties && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {Object.keys(template.schema.properties).slice(0, 3).map((prop) => (
                          <Badge key={prop} variant="outline" className="text-xs">
                            {prop}
                          </Badge>
                        ))}
                        {Object.keys(template.schema.properties).length > 3 && (
                          <Badge variant="outline" className="text-xs">
                            +{Object.keys(template.schema.properties).length - 3}
                          </Badge>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="schema" className="w-full min-w-0 space-y-4">
          {/* Schema Visualization Card */}
          {Object.keys(schema).length > 0 && schema.properties && (
            <Card className="border-dashed">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Schema className="h-5 w-5" />
                  Schema Structure
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Type:</span>
                      <Badge variant="outline" className="ml-2">{schema.type || 'object'}</Badge>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Properties:</span>
                      <Badge variant="outline" className="ml-2">{Object.keys(schema.properties || {}).length}</Badge>
                    </div>
                  </div>
                  
                  {/* Properties Tree View */}
                  <div className="border rounded-lg p-3 bg-muted/30">
                    <div className="font-medium text-sm mb-2">Properties:</div>
                    <div className="space-y-1">
                      {Object.entries(schema.properties || {}).map(([key, prop]: [string, any]) => (
                        <div key={key} className="flex items-center gap-2 text-sm pl-4">
                          <span className="font-mono">{key}</span>
                          <span className="text-muted-foreground">:</span>
                          <Badge variant="secondary" className="text-xs">
                            {prop.type || 'any'}
                          </Badge>
                          {prop.required && (
                            <Badge variant="destructive" className="text-xs">required</Badge>
                          )}
                          {prop.description && (
                            <span className="text-xs text-muted-foreground">- {prop.description}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Required Fields */}
                  {schema.required && schema.required.length > 0 && (
                    <div>
                      <div className="font-medium text-sm mb-1">Required Fields:</div>
                      <div className="flex flex-wrap gap-1">
                        {schema.required.map((field: string) => (
                          <Badge key={field} variant="destructive" className="text-xs">
                            {field}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          <Alert>
            <Code className="h-4 w-4" />
            <AlertDescription>
              Advanced users can edit the JSON Schema directly. Changes will be reflected in the preview.
            </AlertDescription>
          </Alert>

          <div className="w-full min-w-0 space-y-4">
            <div className="w-full min-w-0">
              <Label className="text-sm font-medium">JSON Schema</Label>
              <textarea
                className="w-full h-80 p-3 text-sm font-mono border rounded-md resize-y min-w-0 max-w-full"
                value={JSON.stringify(schema, null, 2)}
                onChange={(e) => {
                  try {
                    const newSchema = JSON.parse(e.target.value);
                    setSchema(newSchema);
                  } catch (error) {
                    // Invalid JSON, don't update
                  }
                }}
                disabled={disabled}
                placeholder="Enter JSON Schema..."
              />
            </div>
            <div className="w-full min-w-0">
              <Label className="text-sm font-medium">UI Schema (Optional)</Label>
              <textarea
                className="w-full h-64 p-3 text-sm font-mono border rounded-md resize-y min-w-0"
                value={JSON.stringify(uiSchema, null, 2)}
                onChange={(e) => {
                  try {
                    const newUiSchema = JSON.parse(e.target.value);
                    setUiSchema(newUiSchema);
                  } catch (error) {
                    // Invalid JSON, don't update
                  }
                }}
                disabled={disabled}
                placeholder="Enter UI Schema for form customization..."
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="preview" className="w-full min-w-0 space-y-4">
          <Alert>
            <Eye className="h-4 w-4" />
            <AlertDescription>
              Preview how the form will appear to users. Use this to test your schema configuration.
            </AlertDescription>
          </Alert>

          {Object.keys(schema).length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Form Preview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="schema-form-preview">
                  <Form
                    schema={schema}
                    uiSchema={uiSchema}
                    formData={formData}
                    validator={validator}
                    onChange={(e) => setFormData(e.formData)}
                    disabled={disabled}
                    noHtml5Validate
                    className="rjsf"
                  >
                    <div className="mt-4 flex justify-end">
                      <Button type="submit" disabled variant="outline">
                        Preview Mode - Submit Disabled
                      </Button>
                    </div>
                  </Form>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center text-muted-foreground">
                  <Schema className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No schema defined yet. Select a template or create a custom schema to see the preview.</p>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Schema Assistant Modal */}
      <SchemaAssistant
        open={schemaAssistantOpen}
        onOpenChange={setSchemaAssistantOpen}
        onSchemaGenerated={handleSchemaAssistantGenerated}
        currentSchema={schema}
        deviceType={deviceType}
      />
    </div>
  );
};