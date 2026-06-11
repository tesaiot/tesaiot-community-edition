/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Industry-Specific Field Configuration
 * Based on international standards and regulatory requirements
 * 
 * Standards Referenced:
 * - Industry 4.0: IEC 61360, IEC 62264, ISO/IEC 30162:2022, ISA-95
 * - Smart City: ISO/IEC 5087, IEEE 2413, ISO 37120, ISO 37122
 * - Smart Energy: IEC 61850, IEEE 2030.5, IEC 61850-7-420
 * - Smart Farm: ISO 11783 (ISOBUS), ISO 11783-10
 */

export interface FieldDefinition {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'boolean' | 'date' | 'datetime' | 'json';
  required?: boolean;
  helperText?: string;
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
    options?: Array<{ value: string; label: string }>;
  };
  standard?: string; // Reference to the standard requiring this field
  category?: string; // Group fields by category
}

export interface IndustryFieldsConfig {
  [industry: string]: {
    name: string;
    description: string;
    standards: string[];
    categories: {
      [category: string]: {
        name: string;
        fields: FieldDefinition[];
      };
    };
  };
}

// Common maintenance and operational fields shared across industries
const COMMON_MAINTENANCE_FIELDS: FieldDefinition[] = [
  {
    name: 'manufacture_date',
    label: 'Manufacturing Date',
    type: 'date',
    required: false,
    helperText: 'When device was manufactured (e.g., 2024-01-15). Helps AI predict lifecycle issues'
  },
  {
    name: 'warranty_expiry_date',
    label: 'Warranty Expiry Date',
    type: 'date',
    required: false,
    helperText: 'Warranty end date. AI uses this to suggest maintenance before expiry'
  },
  {
    name: 'last_calibration_date',
    label: 'Last Calibration Date',
    type: 'date',
    helperText: 'When last calibrated (e.g., 2024-12-01). AI tracks accuracy degradation'
  },
  {
    name: 'next_calibration_due',
    label: 'Next Calibration Due',
    type: 'date',
    helperText: 'Planned calibration date. Leave empty if unknown - AI will suggest based on device type'
  },
  {
    name: 'calibration_interval_days',
    label: 'Calibration Interval (days)',
    type: 'number',
    validation: { min: 1, max: 3650 },
    helperText: 'How often to calibrate (e.g., 180 for 6 months). AI learns optimal intervals'
  },
  {
    name: 'mtbf_hours',
    label: 'MTBF (hours)',
    type: 'number',
    validation: { min: 0 },
    helperText: 'Mean Time Between Failures from manufacturer (e.g., 50000). AI predicts failures'
  },
  {
    name: 'operating_hours',
    label: 'Operating Hours',
    type: 'number',
    validation: { min: 0 },
    helperText: 'Total hours running (e.g., 12500). AI calculates remaining life'
  },
  {
    name: 'service_contract_number',
    label: 'Service Contract Number',
    type: 'text',
    helperText: 'Contract # like SVC-2025-001. AI alerts before expiry'
  },
  {
    name: 'technical_contact',
    label: 'Technical Support Contact',
    type: 'text',
    helperText: 'Support email/phone (e.g., support@vendor.com). AI can auto-create tickets'
  },
  {
    name: 'spare_parts_list',
    label: 'Critical Spare Parts',
    type: 'json',
    helperText: 'Part numbers as JSON array (e.g., ["PART-123", "SEAL-456"]). AI tracks inventory'
  }
];

export const INDUSTRY_FIELDS_CONFIG: IndustryFieldsConfig = {
  industry_40: {
    name: 'Industry 4.0 / IIoT',
    description: 'Manufacturing and Industrial IoT devices',
    standards: ['IEC 61360', 'IEC 62264', 'ISO/IEC 30162:2022', 'ISA-95', 'IEC 62443'],
    categories: {
      device_identity: {
        name: 'Device Identity & Classification',
        fields: [
          {
            name: 'device_class',
            label: 'Device Class (IEC 61360)',
            type: 'select',
            required: false,
            helperText: 'Device type (sensor, actuator, PLC, etc.). AI uses this to apply industry best practices',
            validation: {
              options: [
                { value: 'sensor', label: 'Sensor' },
                { value: 'actuator', label: 'Actuator' },
                { value: 'controller', label: 'Controller' },
                { value: 'hmi', label: 'Human Machine Interface' },
                { value: 'plc', label: 'Programmable Logic Controller' },
                { value: 'robot', label: 'Industrial Robot' },
                { value: 'agv', label: 'Automated Guided Vehicle' }
              ]
            },
            standard: 'IEC 61360-4'
          },
          {
            name: 'manufacturer_code',
            label: 'IEC Manufacturer Code',
            type: 'text',
            required: false,
            helperText: 'Format: ABC1234 (3 letters + 4 digits). If unknown, enter manufacturer name',
            validation: {
              pattern: '^[A-Z]{3}[0-9]{4}$'
            },
            standard: 'IEC 61360'
          },
          {
            name: 'model_number',
            label: 'Model Number',
            type: 'text',
            required: false,
            helperText: 'Model/part number (e.g., S7-1200). AI identifies capabilities and common issues'
          },
          {
            name: 'serial_number',
            label: 'Serial Number',
            type: 'text',
            required: false,
            helperText: 'Unique ID from device label. AI tracks individual device history'
          },
          {
            name: 'hardware_version',
            label: 'Hardware Version',
            type: 'text',
            required: false,
            validation: {
              pattern: '^\\d+\\.\\d+\\.\\d+$'
            },
            helperText: 'Format: 1.2.3 (major.minor.patch). AI checks for known hardware issues'
          },
          {
            name: 'firmware_version',
            label: 'Firmware Version',
            type: 'text',
            required: false,
            validation: {
              pattern: '^\\d+\\.\\d+\\.\\d+$'
            },
            helperText: 'Current firmware (e.g., 2.1.0). AI suggests updates for security/bugs'
          }
        ]
      },
      operational: {
        name: 'Operational Parameters (ISA-95)',
        fields: [
          {
            name: 'production_line_id',
            label: 'Production Line ID',
            type: 'text',
            required: false,
            helperText: 'Line identifier (e.g., LINE-01, PackagingA). AI correlates issues across line',
            standard: 'ISA-95'
          },
          {
            name: 'work_center_id',
            label: 'Work Center ID',
            type: 'text',
            required: false,
            helperText: 'Work cell/station (e.g., WC-A123). AI optimizes workflow bottlenecks',
            standard: 'ISA-95'
          },
          {
            name: 'process_segment_id',
            label: 'Process Segment ID',
            type: 'text',
            helperText: 'Manufacturing process segment identifier',
            standard: 'IEC 62264'
          },
          {
            name: 'equipment_hierarchy_level',
            label: 'Equipment Hierarchy Level',
            type: 'select',
            required: false,
            helperText: 'ISA-95 level (0=Process, 1=Control, 2=Supervisory, 3=MES, 4=ERP). AI understands data flow',
            validation: {
              options: [
                { value: '0', label: 'Level 0 - Process' },
                { value: '1', label: 'Level 1 - Basic Control' },
                { value: '2', label: 'Level 2 - Supervisory Control' },
                { value: '3', label: 'Level 3 - Manufacturing Operations' },
                { value: '4', label: 'Level 4 - Business Planning' }
              ]
            },
            standard: 'ISA-95'
          },
          {
            name: 'equipment_state',
            label: 'Equipment State',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'operating', label: 'Operating' },
                { value: 'idle', label: 'Idle' },
                { value: 'maintenance', label: 'Under Maintenance' },
                { value: 'fault', label: 'Fault Condition' }
              ]
            }
          },
          {
            name: 'oee_availability',
            label: 'OEE Availability (%)',
            type: 'number',
            validation: { min: 0, max: 100 },
            helperText: 'Overall Equipment Effectiveness - Availability'
          },
          {
            name: 'oee_performance',
            label: 'OEE Performance (%)',
            type: 'number',
            validation: { min: 0, max: 100 },
            helperText: 'Overall Equipment Effectiveness - Performance'
          },
          {
            name: 'oee_quality',
            label: 'OEE Quality (%)',
            type: 'number',
            validation: { min: 0, max: 100 },
            helperText: 'Overall Equipment Effectiveness - Quality'
          }
        ]
      },
      communication: {
        name: 'Communication & Integration',
        fields: [
          {
            name: 'protocol_type',
            label: 'Industrial Protocol',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'opc-ua', label: 'OPC UA' },
                { value: 'modbus-tcp', label: 'Modbus TCP' },
                { value: 'modbus-rtu', label: 'Modbus RTU' },
                { value: 'profinet', label: 'PROFINET' },
                { value: 'ethernet-ip', label: 'EtherNet/IP' },
                { value: 'profibus', label: 'PROFIBUS' },
                { value: 'canbus', label: 'CANbus' }
              ]
            },
            standard: 'IEC 61158'
          },
          {
            name: 'network_address',
            label: 'Network Address',
            type: 'text',
            required: false,
            helperText: 'IP address or network identifier'
          },
          {
            name: 'data_exchange_rate',
            label: 'Data Exchange Rate (msg/sec)',
            type: 'number',
            validation: { min: 0.1, max: 10000 }
          }
        ]
      },
      security: {
        name: 'Security (IEC 62443)',
        fields: [
          {
            name: 'security_zone_id',
            label: 'Security Zone ID',
            type: 'text',
            required: false,
            helperText: 'IEC 62443 security zone identifier',
            standard: 'IEC 62443'
          },
          {
            name: 'security_level',
            label: 'Security Level',
            type: 'select',
            required: false,
            helperText: 'Security level 0-4 per IEC 62443',
            validation: {
              options: [
                { value: '0', label: 'SL 0 - No specific requirements' },
                { value: '1', label: 'SL 1 - Protection against casual violation' },
                { value: '2', label: 'SL 2 - Protection against intentional violation' },
                { value: '3', label: 'SL 3 - Protection against sophisticated means' },
                { value: '4', label: 'SL 4 - Protection against extended resources' }
              ]
            },
            standard: 'IEC 62443-3-3'
          },
          {
            name: 'last_security_assessment',
            label: 'Last Security Assessment',
            type: 'date',
            required: true
          }
        ]
      },
      maintenance: {
        name: 'Maintenance & Lifecycle',
        fields: [
          ...COMMON_MAINTENANCE_FIELDS,
          {
            name: 'predictive_maintenance_enabled',
            label: 'Predictive Maintenance Enabled',
            type: 'boolean',
            helperText: 'Uses AI/ML for failure prediction'
          },
          {
            name: 'vibration_threshold_mm_s',
            label: 'Vibration Threshold (mm/s)',
            type: 'number',
            validation: { min: 0, max: 100 },
            helperText: 'Alert threshold for vibration analysis'
          },
          {
            name: 'temperature_threshold_c',
            label: 'Temperature Threshold (°C)',
            type: 'number',
            validation: { min: -40, max: 200 },
            helperText: 'Maximum operating temperature'
          },
          {
            name: 'lubrication_interval_hours',
            label: 'Lubrication Interval (hours)',
            type: 'number',
            validation: { min: 1, max: 10000 },
            helperText: 'Hours between lubrication service'
          },
          {
            name: 'production_critical',
            label: 'Production Critical',
            type: 'boolean',
            helperText: 'Device failure stops production line'
          }
        ]
      }
    }
  },

  smart_city: {
    name: 'Smart City & Building',
    description: 'Urban infrastructure and building automation devices',
    standards: ['ISO/IEC 5087', 'IEEE 2413', 'ISO 37120', 'ISO 37122'],
    categories: {
      location: {
        name: 'Location & Context',
        fields: [
          {
            name: 'building_id',
            label: 'Building ID',
            type: 'text',
            required: false,
            helperText: 'Unique building identifier in city registry'
          },
          {
            name: 'floor_number',
            label: 'Floor Number',
            type: 'text',
            helperText: 'Floor or level (e.g., B1, G, 1, 2)'
          },
          {
            name: 'room_id',
            label: 'Room/Zone ID',
            type: 'text',
            helperText: 'Room number or zone identifier'
          },
          {
            name: 'installation_date',
            label: 'Installation Date',
            type: 'date',
            required: true
          },
          {
            name: 'service_area',
            label: 'Service Area',
            type: 'text',
            helperText: 'Area served by this device (e.g., "North Wing", "Parking B")'
          }
        ]
      },
      urban_integration: {
        name: 'Urban Service Integration',
        fields: [
          {
            name: 'city_service_type',
            label: 'City Service Type',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'transportation', label: 'Transportation' },
                { value: 'utilities', label: 'Utilities' },
                { value: 'safety', label: 'Public Safety' },
                { value: 'environment', label: 'Environmental Monitoring' },
                { value: 'lighting', label: 'Street Lighting' },
                { value: 'waste', label: 'Waste Management' }
              ]
            },
            standard: 'ISO 37120'
          },
          {
            name: 'district_id',
            label: 'District ID',
            type: 'text',
            required: false,
            helperText: 'Administrative district identifier'
          },
          {
            name: 'neighborhood_id',
            label: 'Neighborhood ID',
            type: 'text'
          },
          {
            name: 'resident_serving_capacity',
            label: 'Serving Capacity',
            type: 'number',
            helperText: 'Number of residents served by this device'
          }
        ]
      },
      building_automation: {
        name: 'Building Automation',
        fields: [
          {
            name: 'building_automation_protocol',
            label: 'Automation Protocol',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'bacnet', label: 'BACnet' },
                { value: 'knx', label: 'KNX' },
                { value: 'lonworks', label: 'LonWorks' },
                { value: 'zigbee', label: 'Zigbee' },
                { value: 'dali', label: 'DALI (Lighting)' },
                { value: 'modbus', label: 'Modbus' }
              ]
            }
          },
          {
            name: 'energy_efficiency_class',
            label: 'Energy Efficiency Class',
            type: 'select',
            validation: {
              options: [
                { value: 'A+++', label: 'A+++ (Highest)' },
                { value: 'A++', label: 'A++' },
                { value: 'A+', label: 'A+' },
                { value: 'A', label: 'A' },
                { value: 'B', label: 'B' },
                { value: 'C', label: 'C' },
                { value: 'D', label: 'D' },
                { value: 'E', label: 'E' },
                { value: 'F', label: 'F' },
                { value: 'G', label: 'G (Lowest)' }
              ]
            }
          },
          {
            name: 'hvac_zone_id',
            label: 'HVAC Zone ID',
            type: 'text',
            helperText: 'Heating, Ventilation, and Air Conditioning zone'
          },
          {
            name: 'occupancy_sensor_type',
            label: 'Occupancy Sensor Type',
            type: 'select',
            validation: {
              options: [
                { value: 'pir', label: 'PIR (Passive Infrared)' },
                { value: 'ultrasonic', label: 'Ultrasonic' },
                { value: 'microwave', label: 'Microwave' },
                { value: 'camera', label: 'Camera-based' },
                { value: 'combined', label: 'Combined Technology' }
              ]
            }
          }
        ]
      },
      communication_network: {
        name: 'Communication Network',
        fields: [
          {
            name: 'mesh_network_id',
            label: 'Mesh Network ID',
            type: 'text',
            helperText: 'Identifier for mesh network participation'
          },
          {
            name: 'network_topology',
            label: 'Network Topology',
            type: 'select',
            validation: {
              options: [
                { value: 'star', label: 'Star' },
                { value: 'mesh', label: 'Mesh' },
                { value: 'tree', label: 'Tree' },
                { value: 'bus', label: 'Bus' }
              ]
            }
          },
          {
            name: 'communication_standard',
            label: 'Communication Standard',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'zigbee', label: 'Zigbee' },
                { value: '6lowpan', label: '6LoWPAN' },
                { value: 'wi-sun', label: 'Wi-SUN' },
                { value: 'thread', label: 'Thread' },
                { value: 'lora', label: 'LoRa' },
                { value: 'nb-iot', label: 'NB-IoT' }
              ]
            },
            standard: 'IEEE 802.15.4'
          }
        ]
      },
      maintenance: {
        name: 'Maintenance & Public Safety',
        fields: [
          ...COMMON_MAINTENANCE_FIELDS,
          {
            name: 'public_access_area',
            label: 'Public Access Area',
            type: 'boolean',
            helperText: 'Device is in publicly accessible location'
          },
          {
            name: 'vandalism_resistant',
            label: 'Vandalism Resistant (IK Rating)',
            type: 'select',
            validation: {
              options: [
                { value: 'IK00', label: 'IK00 - No protection' },
                { value: 'IK06', label: 'IK06 - 1 joule impact' },
                { value: 'IK08', label: 'IK08 - 5 joule impact' },
                { value: 'IK10', label: 'IK10 - 20 joule impact' }
              ]
            }
          },
          {
            name: 'environmental_rating',
            label: 'Environmental Rating (IP)',
            type: 'select',
            validation: {
              options: [
                { value: 'IP20', label: 'IP20 - Indoor use' },
                { value: 'IP44', label: 'IP44 - Splash proof' },
                { value: 'IP65', label: 'IP65 - Dust tight, water jets' },
                { value: 'IP67', label: 'IP67 - Temporary immersion' },
                { value: 'IP68', label: 'IP68 - Continuous immersion' }
              ]
            }
          },
          {
            name: 'emergency_contact',
            label: 'Emergency Maintenance Contact',
            type: 'text',
            required: false,
            helperText: '24/7 emergency contact for public safety'
          },
          {
            name: 'cleaning_interval_days',
            label: 'Cleaning Interval (days)',
            type: 'number',
            validation: { min: 1, max: 365 },
            helperText: 'Frequency of cleaning for sensors/cameras'
          }
        ]
      }
    }
  },

  smart_energy: {
    name: 'Smart Energy',
    description: 'Energy generation, distribution, and consumption devices',
    standards: ['IEC 61850', 'IEEE 2030.5', 'IEC 61850-7-420'],
    categories: {
      grid_integration: {
        name: 'Grid Integration (IEC 61850)',
        fields: [
          {
            name: 'logical_device_name',
            label: 'Logical Device Name',
            type: 'text',
            required: false,
            helperText: 'Per IEC 61850 naming convention',
            validation: {
              pattern: '^[A-Z0-9]{1,12}$'
            },
            standard: 'IEC 61850-7-2'
          },
          {
            name: 'logical_node_class',
            label: 'Logical Node Class',
            type: 'select',
            required: false,
            helperText: 'IEC 61850 logical node class',
            validation: {
              options: [
                { value: 'MMXU', label: 'MMXU - Measurement' },
                { value: 'XCBR', label: 'XCBR - Circuit Breaker' },
                { value: 'YPTR', label: 'YPTR - Power Transformer' },
                { value: 'ZINV', label: 'ZINV - Inverter' },
                { value: 'ZBAT', label: 'ZBAT - Battery' },
                { value: 'DPVM', label: 'DPVM - Photovoltaic Module' },
                { value: 'DGEN', label: 'DGEN - Generator' }
              ]
            },
            standard: 'IEC 61850-7-4'
          },
          {
            name: 'ied_name',
            label: 'IED Name',
            type: 'text',
            required: false,
            helperText: 'Intelligent Electronic Device name'
          },
          {
            name: 'substation_id',
            label: 'Substation ID',
            type: 'text',
            helperText: 'Electrical substation identifier'
          },
          {
            name: 'feeder_id',
            label: 'Feeder ID',
            type: 'text',
            helperText: 'Distribution feeder identifier'
          },
          {
            name: 'grid_connection_point',
            label: 'Grid Connection Point',
            type: 'text',
            required: true
          }
        ]
      },
      der_capabilities: {
        name: 'DER Capabilities (IEC 61850-7-420)',
        fields: [
          {
            name: 'der_type',
            label: 'DER Type',
            type: 'select',
            required: false,
            helperText: 'Distributed Energy Resource type',
            validation: {
              options: [
                { value: 'solar', label: 'Solar PV' },
                { value: 'wind', label: 'Wind Turbine' },
                { value: 'battery', label: 'Battery Storage' },
                { value: 'ev_charger', label: 'EV Charger' },
                { value: 'fuel_cell', label: 'Fuel Cell' },
                { value: 'controllable_load', label: 'Controllable Load' },
                { value: 'combined_heat_power', label: 'Combined Heat & Power' }
              ]
            },
            standard: 'IEC 61850-7-420'
          },
          {
            name: 'rated_power_kw',
            label: 'Rated Power (kW)',
            type: 'number',
            required: false,
            validation: { min: 0, max: 100000 }
          },
          {
            name: 'max_active_power_kw',
            label: 'Max Active Power (kW)',
            type: 'number',
            required: false,
            validation: { min: 0, max: 100000 }
          },
          {
            name: 'power_factor_min',
            label: 'Min Power Factor',
            type: 'number',
            validation: { min: -1, max: 1 },
            helperText: 'Minimum power factor capability'
          },
          {
            name: 'power_factor_max',
            label: 'Max Power Factor',
            type: 'number',
            validation: { min: -1, max: 1 },
            helperText: 'Maximum power factor capability'
          },
          {
            name: 'voltage_regulation_capability',
            label: 'Voltage Regulation Capable',
            type: 'boolean',
            helperText: 'Can provide voltage regulation services'
          },
          {
            name: 'grid_code_compliance',
            label: 'Grid Code Compliance',
            type: 'text',
            helperText: 'List of grid codes (comma-separated)'
          }
        ]
      },
      communication: {
        name: 'Communication & Time Sync',
        fields: [
          {
            name: 'time_sync_accuracy_us',
            label: 'Time Sync Accuracy (μs)',
            type: 'number',
            required: false,
            validation: { min: 1, max: 1000 },
            helperText: 'Time synchronization accuracy in microseconds',
            standard: 'IEC 61850-9-3'
          },
          {
            name: 'communication_protocol',
            label: 'IEC 61850 Protocol',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'mms', label: 'MMS (Manufacturing Message Specification)' },
                { value: 'goose', label: 'GOOSE (Generic Object Oriented Substation Event)' },
                { value: 'smv', label: 'SMV (Sampled Measured Values)' },
                { value: 'r-goose', label: 'R-GOOSE (Routable GOOSE)' }
              ]
            },
            standard: 'IEC 61850-8-1'
          },
          {
            name: 'data_model_version',
            label: 'IEC 61850 Edition',
            type: 'select',
            validation: {
              options: [
                { value: 'ed1', label: 'Edition 1' },
                { value: 'ed2', label: 'Edition 2' },
                { value: 'ed2.1', label: 'Edition 2.1' }
              ]
            }
          }
        ]
      },
      metering: {
        name: 'Smart Metering',
        fields: [
          {
            name: 'meter_id',
            label: 'Meter ID',
            type: 'text',
            required: false,
            helperText: 'Unique meter identifier'
          },
          {
            name: 'meter_type',
            label: 'Meter Type',
            type: 'select',
            validation: {
              options: [
                { value: 'electricity', label: 'Electricity' },
                { value: 'gas', label: 'Gas' },
                { value: 'water', label: 'Water' },
                { value: 'heat', label: 'Heat' }
              ]
            }
          },
          {
            name: 'tariff_profile',
            label: 'Tariff Profile',
            type: 'text',
            helperText: 'Applied tariff structure'
          },
          {
            name: 'demand_response_capable',
            label: 'Demand Response Capable',
            type: 'boolean',
            standard: 'IEEE 2030.5'
          },
          {
            name: 'prepayment_enabled',
            label: 'Prepayment Enabled',
            type: 'boolean'
          }
        ]
      },
      maintenance: {
        name: 'Grid Maintenance & Compliance',
        fields: [
          ...COMMON_MAINTENANCE_FIELDS,
          {
            name: 'grid_connection_date',
            label: 'Grid Connection Date',
            type: 'date',
            required: false,
            helperText: 'Date of grid interconnection approval'
          },
          {
            name: 'interconnection_agreement_number',
            label: 'Interconnection Agreement #',
            type: 'text',
            required: false,
            helperText: 'Grid operator agreement reference'
          },
          {
            name: 'protection_relay_test_date',
            label: 'Last Protection Relay Test',
            type: 'date',
            helperText: 'Last protection system test date'
          },
          {
            name: 'arc_flash_hazard_category',
            label: 'Arc Flash Hazard Category',
            type: 'select',
            validation: {
              options: [
                { value: '0', label: 'Category 0 - Minimal' },
                { value: '1', label: 'Category 1 - Low' },
                { value: '2', label: 'Category 2 - Moderate' },
                { value: '3', label: 'Category 3 - High' },
                { value: '4', label: 'Category 4 - Very High' }
              ]
            }
          },
          {
            name: 'insulation_resistance_mohm',
            label: 'Insulation Resistance (MΩ)',
            type: 'number',
            validation: { min: 0, max: 10000 },
            helperText: 'Last measured insulation resistance'
          },
          {
            name: 'transformer_oil_test_date',
            label: 'Transformer Oil Test Date',
            type: 'date',
            helperText: 'For oil-filled transformers only'
          }
        ]
      }
    }
  },

  smart_farm: {
    name: 'Smart Farm / Agriculture',
    description: 'Agricultural and farming IoT devices',
    standards: ['ISO 11783 (ISOBUS)', 'ISO 11783-10'],
    categories: {
      isobus_identity: {
        name: 'ISOBUS Identity (ISO 11783)',
        fields: [
          {
            name: 'iso_name',
            label: 'ISO NAME (64-bit)',
            type: 'text',
            required: false,
            helperText: '64-bit NAME per ISO 11783-5',
            validation: {
              pattern: '^[0-9A-F]{16}$'
            },
            standard: 'ISO 11783-5'
          },
          {
            name: 'manufacturer_code',
            label: 'Manufacturer Code',
            type: 'number',
            required: false,
            validation: { min: 0, max: 2047 },
            helperText: '11-bit manufacturer code',
            standard: 'ISO 11783'
          },
          {
            name: 'device_class',
            label: 'Device Class',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: '1', label: 'Tractor' },
                { value: '2', label: 'Tillage' },
                { value: '3', label: 'Secondary Tillage' },
                { value: '4', label: 'Planters/Seeders' },
                { value: '5', label: 'Fertilizers' },
                { value: '6', label: 'Sprayers' },
                { value: '7', label: 'Harvesters' },
                { value: '8', label: 'Root Harvesters' },
                { value: '9', label: 'Forage' },
                { value: '10', label: 'Irrigation' },
                { value: '11', label: 'Transport/Trailers' },
                { value: '12', label: 'Farm Yard Operations' },
                { value: '13', label: 'Powered Auxiliary Devices' },
                { value: '14', label: 'Special Crops' },
                { value: '15', label: 'Earth Work' },
                { value: '16', label: 'Skidder' },
                { value: '17', label: 'Sensor Systems' }
              ]
            },
            standard: 'ISO 11783'
          },
          {
            name: 'device_class_instance',
            label: 'Device Class Instance',
            type: 'number',
            required: false,
            validation: { min: 0, max: 31 }
          },
          {
            name: 'industry_group',
            label: 'Industry Group',
            type: 'select',
            validation: {
              options: [
                { value: '0', label: 'Global/Default' },
                { value: '1', label: 'Highway Equipment' },
                { value: '2', label: 'Agricultural' },
                { value: '3', label: 'Construction' },
                { value: '4', label: 'Marine' },
                { value: '5', label: 'Industrial' }
              ]
            }
          },
          {
            name: 'self_configurable_address',
            label: 'Self-Configurable Address',
            type: 'boolean',
            helperText: 'Device can claim its own address'
          }
        ]
      },
      task_management: {
        name: 'Task Management (ISO 11783-10)',
        fields: [
          {
            name: 'task_controller_capable',
            label: 'Task Controller Capable',
            type: 'boolean',
            required: false,
            standard: 'ISO 11783-10'
          },
          {
            name: 'prescription_control_capable',
            label: 'Prescription Control Capable',
            type: 'boolean',
            helperText: 'Can execute variable rate prescriptions'
          },
          {
            name: 'section_control_capable',
            label: 'Section Control Capable',
            type: 'boolean',
            helperText: 'Supports automatic section control'
          },
          {
            name: 'variable_rate_capable',
            label: 'Variable Rate Capable',
            type: 'boolean',
            helperText: 'Supports variable rate application'
          },
          {
            name: 'isoxml_version',
            label: 'ISOXML Version',
            type: 'select',
            validation: {
              options: [
                { value: '3', label: 'Version 3' },
                { value: '4', label: 'Version 4' }
              ]
            },
            standard: 'ISO 11783-10'
          }
        ]
      },
      agricultural_operations: {
        name: 'Agricultural Operations',
        fields: [
          {
            name: 'implement_type',
            label: 'Implement Type',
            type: 'select',
            required: false,
            validation: {
              options: [
                { value: 'seeder', label: 'Seeder/Planter' },
                { value: 'sprayer', label: 'Sprayer' },
                { value: 'spreader', label: 'Fertilizer Spreader' },
                { value: 'harvester', label: 'Harvester' },
                { value: 'tiller', label: 'Tiller/Cultivator' },
                { value: 'mower', label: 'Mower' },
                { value: 'baler', label: 'Baler' },
                { value: 'irrigation', label: 'Irrigation System' }
              ]
            }
          },
          {
            name: 'working_width_m',
            label: 'Working Width (m)',
            type: 'number',
            required: false,
            validation: { min: 0.1, max: 50 },
            helperText: 'Implement working width in meters'
          },
          {
            name: 'number_of_sections',
            label: 'Number of Sections',
            type: 'number',
            validation: { min: 1, max: 100 },
            helperText: 'Number of controllable sections'
          },
          {
            name: 'application_rate_units',
            label: 'Application Rate Units',
            type: 'select',
            validation: {
              options: [
                { value: 'seeds/m2', label: 'Seeds per m²' },
                { value: 'kg/ha', label: 'Kilograms per hectare' },
                { value: 'L/ha', label: 'Liters per hectare' },
                { value: 'plants/m2', label: 'Plants per m²' }
              ]
            }
          }
        ]
      },
      field_and_crop: {
        name: 'Field & Crop Data',
        fields: [
          {
            name: 'field_id',
            label: 'Field ID',
            type: 'text',
            required: false,
            helperText: 'Unique field identifier'
          },
          {
            name: 'field_area_ha',
            label: 'Field Area (hectares)',
            type: 'number',
            validation: { min: 0.01, max: 10000 }
          },
          {
            name: 'crop_type',
            label: 'Crop Type',
            type: 'select',
            validation: {
              options: [
                { value: 'wheat', label: 'Wheat' },
                { value: 'corn', label: 'Corn/Maize' },
                { value: 'soybean', label: 'Soybean' },
                { value: 'rice', label: 'Rice' },
                { value: 'cotton', label: 'Cotton' },
                { value: 'sugarcane', label: 'Sugarcane' },
                { value: 'vegetables', label: 'Vegetables' },
                { value: 'fruits', label: 'Fruits' },
                { value: 'pasture', label: 'Pasture' }
              ]
            }
          },
          {
            name: 'soil_type',
            label: 'Soil Type',
            type: 'select',
            validation: {
              options: [
                { value: 'clay', label: 'Clay' },
                { value: 'sandy', label: 'Sandy' },
                { value: 'loam', label: 'Loam' },
                { value: 'silt', label: 'Silt' },
                { value: 'peat', label: 'Peat' },
                { value: 'chalk', label: 'Chalk' }
              ]
            }
          },
          {
            name: 'planting_date',
            label: 'Planting Date',
            type: 'date'
          },
          {
            name: 'expected_yield',
            label: 'Expected Yield (tons/ha)',
            type: 'number',
            validation: { min: 0, max: 100 }
          }
        ]
      },
      environmental_sensors: {
        name: 'Environmental Sensors',
        fields: [
          {
            name: 'soil_moisture_percent',
            label: 'Soil Moisture (%)',
            type: 'number',
            validation: { min: 0, max: 100 },
            helperText: 'Volumetric water content'
          },
          {
            name: 'soil_temperature_c',
            label: 'Soil Temperature (°C)',
            type: 'number',
            validation: { min: -40, max: 80 }
          },
          {
            name: 'soil_ph',
            label: 'Soil pH',
            type: 'number',
            validation: { min: 0, max: 14 }
          },
          {
            name: 'electrical_conductivity_ms_cm',
            label: 'EC (mS/cm)',
            type: 'number',
            validation: { min: 0, max: 20 },
            helperText: 'Electrical conductivity in milliSiemens/cm'
          },
          {
            name: 'light_intensity_lux',
            label: 'Light Intensity (lux)',
            type: 'number',
            validation: { min: 0, max: 200000 }
          },
          {
            name: 'nutrient_nitrogen_ppm',
            label: 'Nitrogen (ppm)',
            type: 'number',
            validation: { min: 0, max: 1000 }
          },
          {
            name: 'nutrient_phosphorus_ppm',
            label: 'Phosphorus (ppm)',
            type: 'number',
            validation: { min: 0, max: 1000 }
          },
          {
            name: 'nutrient_potassium_ppm',
            label: 'Potassium (ppm)',
            type: 'number',
            validation: { min: 0, max: 1000 }
          }
        ]
      },
      maintenance: {
        name: 'Agricultural Maintenance & Compliance',
        fields: [
          ...COMMON_MAINTENANCE_FIELDS,
          {
            name: 'hydraulic_oil_change_hours',
            label: 'Hydraulic Oil Change (hours)',
            type: 'number',
            validation: { min: 100, max: 5000 },
            helperText: 'Operating hours between hydraulic oil changes'
          },
          {
            name: 'pto_shaft_inspection_date',
            label: 'PTO Shaft Inspection Date',
            type: 'date',
            helperText: 'Power Take-Off shaft safety inspection'
          },
          {
            name: 'gps_rtk_subscription_expiry',
            label: 'GPS RTK Subscription Expiry',
            type: 'date',
            helperText: 'RTK correction service expiry date'
          },
          {
            name: 'spray_nozzle_check_acres',
            label: 'Spray Nozzle Check (acres)',
            type: 'number',
            validation: { min: 0, max: 10000 },
            helperText: 'Acres between nozzle wear checks'
          },
          {
            name: 'seed_meter_calibration_bags',
            label: 'Seed Meter Calibration (bags)',
            type: 'number',
            validation: { min: 0, max: 1000 },
            helperText: 'Seed bags between meter calibration'
          },
          {
            name: 'pesticide_applicator_license',
            label: 'Pesticide Applicator License #',
            type: 'text',
            helperText: 'Required for spraying equipment'
          },
          {
            name: 'organic_certification_number',
            label: 'Organic Certification #',
            type: 'text',
            helperText: 'If applicable for organic operations'
          }
        ]
      }
    }
  }
};

// Helper function to get fields for a specific industry
export function getIndustryFields(industry: string): FieldDefinition[] {
  const config = INDUSTRY_FIELDS_CONFIG[industry];
  if (!config) return [];
  
  const fields: FieldDefinition[] = [];
  Object.values(config.categories).forEach(category => {
    fields.push(...category.fields);
  });
  
  return fields;
}

// Helper function to get fields by category
export function getIndustryFieldsByCategory(industry: string, categoryKey: string): FieldDefinition[] {
  const config = INDUSTRY_FIELDS_CONFIG[industry];
  if (!config || !config.categories[categoryKey]) return [];
  
  return config.categories[categoryKey].fields;
}

// Helper function to validate field value (AI-friendly: only validate when value is provided)
export function validateFieldValue(field: FieldDefinition, value: any): string | null {
  // AI-friendly approach: No validation for empty/missing values
  // Let users save with partial information and AI will work with what's available
  if (!value || value === '' || value === null || value === undefined) {
    return null; // Always allow empty values
  }
  
  // Only validate when user has actually provided a value
  if (field.validation && value) {
    if (field.type === 'number') {
      const numValue = Number(value);
      if (isNaN(numValue)) {
        return `${field.label} must be a valid number`;
      }
      if (field.validation.min !== undefined && numValue < field.validation.min) {
        return `${field.label} must be at least ${field.validation.min}`;
      }
      if (field.validation.max !== undefined && numValue > field.validation.max) {
        return `${field.label} must be at most ${field.validation.max}`;
      }
    }
    
    if (field.validation.pattern) {
      const regex = new RegExp(field.validation.pattern);
      if (!regex.test(value)) {
        return `${field.label} format should be: ${field.helperText || 'see field description'}`;
      }
    }
  }
  
  return null;
}