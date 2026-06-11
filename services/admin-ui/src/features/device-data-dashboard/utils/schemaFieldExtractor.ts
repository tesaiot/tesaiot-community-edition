/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { RJSFSchema } from '@rjsf/utils';

export interface SchemaField {
  key: string;
  title: string;
  type: string;
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  format?: string;
  isRequired: boolean;
  unit?: string;
  category: 'sensor' | 'status' | 'computed' | 'metadata';
  widgetTypes: string[]; // Compatible widget types for this field
}

export interface DeviceSchemaFields {
  deviceId: string;
  deviceName: string;
  deviceType: 'sensor' | 'actuator' | 'gateway' | 'controller';
  telemetryFields: SchemaField[];
  actuatorFields: SchemaField[];
  hasSchema: boolean;
  lastUpdated?: Date;
}

/**
 * Extract fields from JSON Schema recursively
 */
function extractFieldsFromSchema(
  schema: RJSFSchema, 
  parentKey = '', 
  required: string[] = []
): SchemaField[] {
  const fields: SchemaField[] = [];

  if (!schema.properties) {
    return fields;
  }

  Object.entries(schema.properties).forEach(([key, property]) => {
    const fullKey = parentKey ? `${parentKey}.${key}` : key;
    const prop = property as RJSFSchema;
    
    // Handle nested objects
    if (prop.type === 'object' && prop.properties) {
      const nestedFields = extractFieldsFromSchema(
        prop, 
        fullKey, 
        prop.required || []
      );
      fields.push(...nestedFields);
      return;
    }

    // Determine field category based on type and naming patterns
    const category = categorizeField(key, prop);
    
    // Determine compatible widget types
    const widgetTypes = getCompatibleWidgetTypes(prop.type, prop.format, prop.enum);
    
    // Extract unit from title or description
    const unit = extractUnit(prop.title || key, prop.description);

    const field: SchemaField = {
      key: fullKey,
      title: prop.title || key,
      type: prop.type || 'string',
      description: prop.description,
      enum: prop.enum,
      minimum: prop.minimum,
      maximum: prop.maximum,
      format: prop.format,
      isRequired: required.includes(key),
      unit,
      category,
      widgetTypes
    };

    fields.push(field);
  });

  return fields;
}

/**
 * Categorize field based on name patterns and type
 */
function categorizeField(key: string, property: RJSFSchema): SchemaField['category'] {
  const lowerKey = key.toLowerCase();
  
  // Sensor data patterns
  if (
    lowerKey.includes('temperature') ||
    lowerKey.includes('humidity') ||
    lowerKey.includes('pressure') ||
    lowerKey.includes('voltage') ||
    lowerKey.includes('current') ||
    lowerKey.includes('flow') ||
    lowerKey.includes('level') ||
    lowerKey.includes('ph') ||
    lowerKey.includes('conductivity') ||
    lowerKey.includes('vibration') ||
    lowerKey.includes('pm25') ||
    lowerKey.includes('pm10') ||
    lowerKey.includes('co2') ||
    property.type === 'number' && (property.minimum !== undefined || property.maximum !== undefined)
  ) {
    return 'sensor';
  }
  
  // Status/state patterns
  if (
    lowerKey.includes('status') ||
    lowerKey.includes('state') ||
    lowerKey.includes('mode') ||
    lowerKey.includes('enabled') ||
    lowerKey.includes('active') ||
    property.enum ||
    property.type === 'boolean'
  ) {
    return 'status';
  }
  
  // Computed/derived patterns
  if (
    lowerKey.includes('usage') ||
    lowerKey.includes('rate') ||
    lowerKey.includes('average') ||
    lowerKey.includes('total') ||
    lowerKey.includes('count')
  ) {
    return 'computed';
  }
  
  // Metadata patterns
  if (
    lowerKey.includes('timestamp') ||
    lowerKey.includes('id') ||
    lowerKey.includes('name') ||
    lowerKey.includes('version') ||
    property.format === 'date-time' ||
    property.format === 'date'
  ) {
    return 'metadata';
  }
  
  return 'sensor'; // Default to sensor
}

/**
 * Determine compatible widget types for a field
 */
function getCompatibleWidgetTypes(
  type?: string, 
  format?: string, 
  enumValues?: string[]
): string[] {
  const widgets: string[] = [];
  
  switch (type) {
    case 'number':
    case 'integer':
      widgets.push('gauge', 'line-chart', 'bar-chart', 'stat-card', 'sparkline');
      break;
      
    case 'boolean':
      widgets.push('status-indicator', 'switch-control', 'stat-card');
      break;
      
    case 'string':
      if (enumValues) {
        widgets.push('status-indicator', 'pie-chart', 'stat-card');
      } else if (format === 'date-time' || format === 'date') {
        widgets.push('timestamp-display', 'stat-card');
      } else {
        widgets.push('text-display', 'stat-card');
      }
      break;
      
    default:
      widgets.push('stat-card', 'text-display');
  }
  
  return widgets;
}

/**
 * Extract unit information from title or description
 */
function extractUnit(title: string, description?: string): string | undefined {
  const text = `${title} ${description || ''}`.toLowerCase();
  
  const unitPatterns = [
    { pattern: /\(([^)]+)\)/, group: 1 }, // Extract from parentheses
    { pattern: /°c|celsius/, unit: '°C' },
    { pattern: /°f|fahrenheit/, unit: '°F' },
    { pattern: /%|percent/, unit: '%' },
    { pattern: /hpa|hectopascal/, unit: 'hPa' },
    { pattern: /psi/, unit: 'PSI' },
    { pattern: /volts?|v\b/, unit: 'V' },
    { pattern: /amps?|ampere|a\b/, unit: 'A' },
    { pattern: /watts?|w\b/, unit: 'W' },
    { pattern: /l\/min|liters?.*minute/, unit: 'L/min' },
    { pattern: /m\/s²|meters.*second.*squared/, unit: 'm/s²' },
    { pattern: /µg\/m³|micrograms.*cubic/, unit: 'µg/m³' },
    { pattern: /ppm|parts.*million/, unit: 'ppm' },
    { pattern: /dbm/, unit: 'dBm' },
    { pattern: /kbps|kilobits.*second/, unit: 'kbps' },
    { pattern: /seconds?|s\b/, unit: 's' },
    { pattern: /minutes?|min\b/, unit: 'min' },
    { pattern: /hours?|h\b/, unit: 'h' }
  ];
  
  for (const { pattern, unit } of unitPatterns) {
    if (pattern instanceof RegExp) {
      const match = text.match(pattern);
      if (match) {
        return unit || match[1]?.trim();
      }
    }
  }
  
  return undefined;
}

/**
 * Extract all available fields from device schemas
 */
export function extractDeviceSchemaFields(devices: any[]): DeviceSchemaFields[] {
  return devices.map(device => {
    const telemetryFields = device.telemetrySchema?.schema 
      ? extractFieldsFromSchema(
          device.telemetrySchema.schema, 
          '', 
          device.telemetrySchema.schema.required || []
        )
      : [];
      
    const actuatorFields = device.actuatorSchema?.schema 
      ? extractFieldsFromSchema(
          device.actuatorSchema.schema, 
          '', 
          device.actuatorSchema.schema.required || []
        )
      : [];

    return {
      deviceId: device.id || device.device_id,
      deviceName: device.name || device.device_id || 'Unnamed Device',
      deviceType: device.type || 'sensor',
      telemetryFields,
      actuatorFields,
      hasSchema: telemetryFields.length > 0 || actuatorFields.length > 0,
      lastUpdated: device.telemetrySchema?.lastUpdated || device.actuatorSchema?.lastUpdated
    };
  });
}

/**
 * Get fields compatible with a specific widget type
 */
export function getFieldsForWidgetType(
  deviceFields: DeviceSchemaFields[], 
  widgetType: string
): Array<{
  deviceId: string;
  deviceName: string;
  field: SchemaField;
}> {
  const compatibleFields: Array<{
    deviceId: string;
    deviceName: string;
    field: SchemaField;
  }> = [];
  
  deviceFields.forEach(device => {
    [...device.telemetryFields, ...device.actuatorFields].forEach(field => {
      if (field.widgetTypes.includes(widgetType)) {
        compatibleFields.push({
          deviceId: device.deviceId,
          deviceName: device.deviceName,
          field
        });
      }
    });
  });
  
  return compatibleFields;
}

/**
 * Generate field selection options for dropdowns
 */
export function generateFieldOptions(
  deviceFields: DeviceSchemaFields[], 
  widgetType?: string
): Array<{
  value: string;
  label: string;
  group: string;
  field: SchemaField;
  deviceName: string;
}> {
  const options: Array<{
    value: string;
    label: string;
    group: string;
    field: SchemaField;
    deviceName: string;
  }> = [];
  
  deviceFields.forEach(device => {
    const fields = [...device.telemetryFields, ...device.actuatorFields];
    
    fields.forEach(field => {
      // Filter by widget type if specified
      if (widgetType && !field.widgetTypes.includes(widgetType)) {
        return;
      }
      
      const value = `${device.deviceId}:${field.key}`;
      const label = `${field.title}${field.unit ? ` (${field.unit})` : ''}${field.isRequired ? ' *' : ''}`;
      const group = `${device.deviceName} (${device.deviceType})`;
      
      options.push({
        value,
        label,
        group,
        field,
        deviceName: device.deviceName
      });
    });
  });
  
  // Sort by device name, then by field title
  return options.sort((a, b) => {
    if (a.group !== b.group) {
      return a.group.localeCompare(b.group);
    }
    return a.label.localeCompare(b.label);
  });
}

/**
 * Parse field value string back to device ID and field key
 */
export function parseFieldValue(fieldValue: string): { deviceId: string; fieldKey: string } | null {
  const parts = fieldValue.split(':');
  if (parts.length !== 2) {
    return null;
  }
  
  return {
    deviceId: parts[0],
    fieldKey: parts[1]
  };
}