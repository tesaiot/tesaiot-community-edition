/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import authFetch from '@/utils/auth-fetch';

// Types for Industry Schema Management
export interface FieldDefinition {
  id: string;
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'multiselect' | 'switch' | 'date' | 'datetime' | 'location' | 'keyvalue';
  required?: boolean;
  placeholder?: string;
  helpText?: string;
  options?: Array<{ value: string; label: string }>;
  validation?: ValidationRule;
  dependsOn?: string; // Field ID that this field depends on
  showWhen?: { field: string; value: any }; // Conditional display
}

export interface ValidationRule {
  pattern?: string;
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
  message?: string;
  custom?: (value: any, formData: any) => string | null;
}

export interface IndustrySchema {
  id: string;
  name: string;
  icon: string;
  description: string;
  category: string[]; // Backend device categories this maps to
  requiredFields: FieldDefinition[];
  optionalFields: FieldDefinition[];
  validations: Record<string, ValidationRule>;
  helpTexts: Record<string, string>;
  templateData?: Record<string, any>; // Default values for new devices
}

export interface ImageMetadata {
  filename: string;
  size: number;
  mimeType: string;
  width?: number;
  height?: number;
  uploadedAt: string;
}

// Industry definitions aligned with backend schemas
export const INDUSTRIES: IndustrySchema[] = [
  {
    id: 'health_medical',
    name: 'Health & Medical',
    icon: '🏥',
    description: 'FDA-compliant medical devices, patient monitors, diagnostic equipment',
    category: ['medical_device', 'wellness_device'],
    requiredFields: [],
    optionalFields: [],
    validations: {},
    helpTexts: {
      fdaClass: 'FDA classification determines regulatory requirements. Class I (low risk), Class II (moderate risk), Class III (high risk)',
      udi: 'Unique Device Identifier required for Class II and III devices',
      calibrationInterval: 'Maximum days between calibrations to maintain accuracy'
    }
  },
  {
    id: 'industry_40',
    name: 'Industry 4.0',
    icon: '🏭',
    description: 'Smart manufacturing, robotics, industrial automation',
    category: ['industrial_iot', 'robotics', 'amr_agv'],
    requiredFields: [],
    optionalFields: [],
    validations: {},
    helpTexts: {
      opcuaEndpoint: 'OPC-UA server endpoint URL (e.g., opc.tcp://192.168.1.100:4840)',
      modbusSlaveId: 'Modbus slave ID (1-247)',
      safetyZones: 'Define collaborative, restricted, and forbidden zones for safe operation'
    }
  },
  {
    id: 'smart_city',
    name: 'Smart City & Building',
    icon: '🏙️',
    description: 'Urban infrastructure, smart buildings, environmental monitoring',
    category: ['smart_home', 'sensor', 'actuator'],
    requiredFields: [],
    optionalFields: [],
    validations: {},
    helpTexts: {
      deploymentType: 'Physical installation location type',
      publicDataAccess: 'Enable citizen access to aggregated/anonymized data',
      emergencyAlerts: 'Broadcast emergency notifications to nearby citizens'
    }
  },
  {
    id: 'smart_energy',
    name: 'Smart Energy',
    icon: '⚡',
    description: 'Smart meters, grid monitoring, renewable energy systems',
    category: ['sensor', 'actuator', 'gateway'],
    requiredFields: [],
    optionalFields: [],
    validations: {},
    helpTexts: {
      connectionType: 'Grid connection configuration',
      netMetering: 'Enable bidirectional energy flow measurement',
      demandResponse: 'Participate in utility demand response programs'
    }
  },
  {
    id: 'smart_farm',
    name: 'Smart Agriculture',
    icon: '🌾',
    description: 'Precision farming, soil monitoring, livestock tracking',
    category: ['sensor', 'actuator', 'controller'],
    requiredFields: [],
    optionalFields: [],
    validations: {},
    helpTexts: {
      farmType: 'Primary agricultural operation type',
      soilSensors: 'Configure soil monitoring depth and parameters',
      irrigationType: 'Automated irrigation system configuration'
    }
  }
];

class IndustrySchemaService {
  private cache: Map<string, any> = new Map();

  /**
   * Get schema fields for a specific industry
   */
  async getSchemaForIndustry(industryId: string): Promise<IndustrySchema | null> {
    const industry = INDUSTRIES.find(i => i.id === industryId);
    if (!industry) return null;

    // Check cache first
    const cacheKey = `schema_${industryId}`;
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    try {
      // Fetch dynamic fields from backend for each category
      const schemaPromises = industry.category.map(cat => 
        this.fetchCategorySchema(cat)
      );
      
      const schemas = await Promise.all(schemaPromises);
      
      // Merge schemas and convert to field definitions
      const mergedFields = this.mergeSchemas(schemas);
      const fieldDefinitions = this.convertToFieldDefinitions(mergedFields, industryId);
      
      // Update industry with dynamic fields
      const enrichedIndustry = {
        ...industry,
        requiredFields: fieldDefinitions.required,
        optionalFields: fieldDefinitions.optional
      };
      
      // Cache for 5 minutes
      this.cache.set(cacheKey, enrichedIndustry);
      setTimeout(() => this.cache.delete(cacheKey), 5 * 60 * 1000);
      
      return enrichedIndustry;
    } catch (error) {
      console.error(`Failed to fetch schema for industry ${industryId}:`, error);
      // Return static industry definition as fallback
      return industry;
    }
  }

  /**
   * Fetch schema from backend for a device category
   */
  private async fetchCategorySchema(category: string): Promise<any> {
    try {
      const response = await authFetch(`/api/v1/devices/schemas/${category}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch schema: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`Failed to fetch schema for category ${category}:`, error);
      return null;
    }
  }

  /**
   * Merge multiple schemas into a single schema
   */
  private mergeSchemas(schemas: any[]): any {
    const merged: any = {
      properties: {},
      required: []
    };

    schemas.filter(s => s).forEach(schema => {
      if (schema.properties) {
        Object.assign(merged.properties, schema.properties);
      }
      if (schema.required) {
        merged.required.push(...schema.required);
      }
    });

    // Remove duplicates from required array
    merged.required = [...new Set(merged.required)];

    return merged;
  }

  /**
   * Convert backend schema to field definitions
   */
  private convertToFieldDefinitions(schema: any, industryId: string): {
    required: FieldDefinition[];
    optional: FieldDefinition[];
  } {
    const required: FieldDefinition[] = [];
    const optional: FieldDefinition[] = [];

    if (!schema.properties) {
      return { required, optional };
    }

    // Get industry-specific field mappings
    const fieldMappings = this.getIndustryFieldMappings(industryId);

    Object.entries(schema.properties).forEach(([key, prop]: [string, any]) => {
      // Skip base fields that are already in the main form
      if (this.isBaseField(key)) return;

      // Check if field should be included for this industry
      if (fieldMappings && !fieldMappings.includes(key)) return;

      const field = this.createFieldDefinition(key, prop, industryId);
      
      if (schema.required?.includes(key)) {
        required.push(field);
      } else {
        optional.push(field);
      }
    });

    return { required, optional };
  }

  /**
   * Check if field is a base field (already in main form)
   */
  private isBaseField(fieldName: string): boolean {
    const baseFields = [
      'device_id', 'name', 'type', 'category', 'organization_id',
      'status', 'last_seen', 'firmware_version', 'hardware_version'
    ];
    return baseFields.includes(fieldName);
  }

  /**
   * Get industry-specific field mappings
   */
  private getIndustryFieldMappings(industryId: string): string[] | null {
    const mappings: Record<string, string[]> = {
      health_medical: [
        'device_classification', 'clinical_parameters', 'data_security',
        'interoperability', 'clinical_validation', 'maintenance'
      ],
      industry_40: [
        'industrial_protocols', 'process_data', 'integration',
        'redundancy', 'robot_specs', 'kinematics', 'safety_systems'
      ],
      smart_city: [
        'location', 'deployment_type', 'environmental_sensors',
        'public_access', 'emergency_alerts', 'infrastructure_type'
      ],
      smart_energy: [
        'connection_type', 'generation_type', 'storage_system',
        'tariff_config', 'demand_response', 'grid_services'
      ],
      smart_farm: [
        'farm_type', 'soil_sensors', 'irrigation_system',
        'weather_integration', 'pest_monitoring', 'yield_tracking'
      ]
    };

    return mappings[industryId] || null;
  }

  /**
   * Create field definition from schema property
   */
  private createFieldDefinition(key: string, prop: any, industryId: string): FieldDefinition {
    const field: FieldDefinition = {
      id: key,
      name: key,
      label: this.humanizeLabel(key),
      type: this.getFieldType(prop),
      placeholder: prop.description || '',
      helpText: this.getHelpText(key, industryId)
    };

    // Add validation rules
    if (prop.minLength || prop.maxLength || prop.pattern) {
      field.validation = {
        minLength: prop.minLength,
        maxLength: prop.maxLength,
        pattern: prop.pattern,
        message: prop.validationMessage
      };
    }

    // Add options for enum fields
    if (prop.enum) {
      field.options = prop.enum.map((value: string) => ({
        value,
        label: this.humanizeLabel(value)
      }));
    }

    return field;
  }

  /**
   * Determine field type from schema property
   */
  private getFieldType(prop: any): FieldDefinition['type'] {
    if (prop.enum) return 'select';
    if (prop.type === 'boolean') return 'switch';
    if (prop.type === 'integer' || prop.type === 'number') return 'number';
    if (prop.format === 'date') return 'date';
    if (prop.format === 'date-time') return 'datetime';
    if (prop.type === 'object' && prop.properties?.lat && prop.properties?.lng) return 'location';
    if (prop.type === 'object') return 'keyvalue';
    return 'text';
  }

  /**
   * Convert snake_case to human readable label
   */
  private humanizeLabel(str: string): string {
    return str
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
      .trim();
  }

  /**
   * Get help text for a field
   */
  private getHelpText(fieldName: string, industryId: string): string {
    const industry = INDUSTRIES.find(i => i.id === industryId);
    return industry?.helpTexts[fieldName] || '';
  }

  /**
   * Validate device data against industry schema
   */
  async validateIndustryData(industryId: string, data: any): Promise<{
    valid: boolean;
    errors: Record<string, string>;
  }> {
    const schema = await this.getSchemaForIndustry(industryId);
    if (!schema) {
      return { valid: false, errors: { _general: 'Invalid industry' } };
    }

    const errors: Record<string, string> = {};

    // Validate required fields
    schema.requiredFields.forEach(field => {
      if (!data[field.id] || data[field.id] === '') {
        errors[field.id] = `${field.label} is required`;
      }
    });

    // Validate field-specific rules
    [...schema.requiredFields, ...schema.optionalFields].forEach(field => {
      const value = data[field.id];
      if (value && field.validation) {
        const error = this.validateField(value, field.validation, data);
        if (error) {
          errors[field.id] = error;
        }
      }
    });

    return {
      valid: Object.keys(errors).length === 0,
      errors
    };
  }

  /**
   * Validate a single field value
   */
  private validateField(value: any, validation: ValidationRule, formData: any): string | null {
    if (validation.pattern && !new RegExp(validation.pattern).test(value)) {
      return validation.message || 'Invalid format';
    }

    if (validation.minLength && value.length < validation.minLength) {
      return `Minimum length is ${validation.minLength}`;
    }

    if (validation.maxLength && value.length > validation.maxLength) {
      return `Maximum length is ${validation.maxLength}`;
    }

    if (validation.min !== undefined && Number(value) < validation.min) {
      return `Minimum value is ${validation.min}`;
    }

    if (validation.max !== undefined && Number(value) > validation.max) {
      return `Maximum value is ${validation.max}`;
    }

    if (validation.custom) {
      return validation.custom(value, formData);
    }

    return null;
  }

  /**
   * Get field mappings for backend API
   */
  async getFieldMappings(industryId: string): Promise<Record<string, string>> {
    // Map frontend field names to backend field names
    const mappings: Record<string, Record<string, string>> = {
      health_medical: {
        fdaClass: 'device_classification.fda_class',
        ceMark: 'device_classification.ce_mark',
        udi: 'device_classification.udi_di',
        calibrationInterval: 'maintenance.preventive_maintenance.interval_days'
      },
      industry_40: {
        opcuaEndpoint: 'industrial_protocols.opcua_endpoint',
        modbusSlaveId: 'industrial_protocols.modbus_slave_id',
        productionLine: 'process_data.production_line',
        safetyZones: 'safety_systems.safety_zones'
      },
      smart_city: {
        deploymentType: 'deployment.type',
        publicDataAccess: 'public_access.enabled',
        dataPortalUrl: 'public_access.portal_url',
        emergencyAlerts: 'emergency_system.enabled'
      },
      smart_energy: {
        connectionType: 'grid_connection.type',
        maxPower: 'grid_connection.max_power_kw',
        hasStorage: 'energy_storage.enabled',
        demandResponse: 'grid_services.demand_response'
      },
      smart_farm: {
        farmType: 'farm_info.type',
        cropType: 'farm_info.crop_type',
        hasIrrigation: 'irrigation.enabled',
        soilSensors: 'monitoring.soil_sensors'
      }
    };

    return mappings[industryId] || {};
  }

  /**
   * Detect industry type from device data
   */
  detectIndustryFromDevice(device: any): string | null {
    // Check explicit industry field
    if (device.industry) {
      return device.industry;
    }

    // Check device category
    const categoryToIndustry: Record<string, string> = {
      'medical_device': 'health_medical',
      'wellness_device': 'health_medical',
      'industrial_iot': 'industry_40',
      'robotics': 'industry_40',
      'amr_agv': 'industry_40',
      'smart_home': 'smart_city',
      'wearable': 'health_medical',
      'drone': 'industry_40'
    };

    if (device.category && categoryToIndustry[device.category]) {
      return categoryToIndustry[device.category];
    }

    // Analyze metadata for hints
    if (device.metadata) {
      if (device.metadata.fda_class || device.metadata.clinical_parameters) {
        return 'health_medical';
      }
      if (device.metadata.opcua_endpoint || device.metadata.modbus_config) {
        return 'industry_40';
      }
      if (device.metadata.public_access || device.metadata.deployment_type) {
        return 'smart_city';
      }
      if (device.metadata.grid_connection || device.metadata.energy_storage) {
        return 'smart_energy';
      }
      if (device.metadata.farm_type || device.metadata.soil_sensors) {
        return 'smart_farm';
      }
    }

    return null;
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
  }
}

// Export singleton instance
export const industrySchemaService = new IndustrySchemaService();