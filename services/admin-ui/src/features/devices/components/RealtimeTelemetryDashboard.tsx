/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useRef, useCallback, useLayoutEffect, useMemo, memo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Activity, 
  Zap, 
  Thermometer, 
  Droplets, 
  Wind, 
  Sun,
  Gauge,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Play,
  Pause,
  X,
  ExternalLink,
  Download,
  BarChart3
} from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { authFetch } from '@/utils/auth-fetch';
import { cn } from '@/lib/utils';
import { extractDeviceSchemaFields, SchemaField } from '../../device-data-dashboard/utils/schemaFieldExtractor';
import { UnitMappings } from '../services/sensorCatalog';
import { 
  AutoRefreshStatusBar,
  DataUpdateFlash,
  RefreshProgressBar,
  LiveIndicator,
  RefreshCountdown,
  DataFetchSpinner,
  LastUpdateTimestamp,
  logRefreshEvent
} from '@/components/AutoRefreshIndicators';
import ErrorBoundary from '@/components/ui/error-boundary';
import { useThrottledCallback } from '@/hooks/useDebounce';

// Helper functions for unit resolution (temporary stubs)
const resolveUnitFromIntegerEnum = (fieldKey: string, enumValues: string[]): string | undefined => {
  // Simple resolution based on common patterns
  if (fieldKey.toLowerCase().includes('temperature')) {
    return '°C';
  }
  return undefined;
};

const getUnitArrayForField = (fieldKey: string): string[] | undefined => {
  // Return unit arrays for known field types
  const key = fieldKey.toLowerCase();
  if (key.includes('temperature')) {
    return ['°C', '°F', 'K'];
  }
  if (key.includes('pressure')) {
    return ['hPa', 'PSI', 'bar'];
  }
  return undefined;
};

interface TelemetryData {
  timestamp: string;
  temperature?: number;
  humidity?: number;
  pressure?: number;
  vibration?: number;
  light?: number;
  voltage?: number;
  current?: number;
  [key: string]: any;
}

interface Device {
  id: string;
  device_id: string;
  name: string;
  type: string;
  status: string;
  lastSeen: Date;
  telemetry?: {
    messagesPerMinute: number;
    totalMessages: number;
  };
  telemetrySchema?: {
    schema: any;
    uiSchema?: any;
    formData?: any;
    lastUpdated?: string;
  };
}

interface RealtimeTelemetryDashboardProps {
  devices: Device[];
  onClose?: () => void;
}

const RealtimeTelemetryDashboardInner: React.FC<RealtimeTelemetryDashboardProps> = memo(({ 
  devices, 
  onClose 
}) => {
  const navigate = useNavigate();
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [telemetryData, setTelemetryData] = useState<TelemetryData[]>([]);
  const [isStreaming, setIsStreaming] = useState(true);
  const [dataRate, setDataRate] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [schemaFields, setSchemaFields] = useState<SchemaField[]>([]);
  const [unitMappings, setUnitMappings] = useState<Record<string, string>>({});
  const [countdown, setCountdown] = useState<number>(10);
  const [dataChanged, setDataChanged] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [consecutiveErrors, setConsecutiveErrors] = useState(0);
  const [initialLoading, setInitialLoading] = useState(true);
  
  // Refs for scroll position preservation
  const mainContentRef = useRef<HTMLDivElement>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const scrollPositions = useRef({ main: 0, terminal: 0 });
  
  // Render tracking for debugging

  // Filter active/online devices (devices with 'active' or 'online' status)
  const onlineDevices = (devices || []).filter(d => d.status === 'online' || d.status === 'active');

  useEffect(() => {
    // Auto-select first active device
    if (onlineDevices.length > 0 && !selectedDevice) {
      setSelectedDevice(onlineDevices[0]);
    }
  }, [onlineDevices, selectedDevice]);

  useEffect(() => {
    // Extract schema fields when device is selected
    if (selectedDevice?.telemetrySchema?.schema) {
      try {
        // Create a device object compatible with extractDeviceSchemaFields
        const deviceForExtraction = {
          id: selectedDevice.id,
          device_id: selectedDevice.device_id,
          name: selectedDevice.name,
          telemetrySchema: selectedDevice.telemetrySchema
        };
        
        const deviceFields = extractDeviceSchemaFields([deviceForExtraction]);
        if (deviceFields.length > 0 && deviceFields[0].telemetryFields) {
          // Get all displayable fields (sensor, status, computed) - exclude object types
          const displayFields = deviceFields[0].telemetryFields.filter(field => 
            field.category !== 'metadata' && 
            field.type !== 'object' &&
            (field.type === 'number' || field.type === 'integer' || field.type === 'boolean' || field.enum)
          );
          
          // Process fields and resolve unit mappings for integer enums
          const processedFields = displayFields.map(field => {
            let resolvedUnit = field.unit;
            
            // Handle integer enum unit mappings (e.g., temperature: 0=°C, 1=°F, 2=K)
            if (field.type === 'integer' && field.enum && !resolvedUnit) {
              resolvedUnit = resolveUnitFromIntegerEnum(field.key, field.enum);
            }
            
            return {
              ...field,
              unit: resolvedUnit || field.unit
            };
          });
          
          // Take up to 8 fields for the dashboard display
          setSchemaFields(processedFields.slice(0, 8));
          
          // Create unit mappings for integer enums
          const mappings: Record<string, string> = {};
          processedFields.forEach(field => {
            if (field.type === 'integer' && field.enum) {
              const unitArray = getUnitArrayForField(field.key);
              if (unitArray) {
                field.enum.forEach((enumValue, index) => {
                  mappings[`${field.key}_${enumValue}`] = unitArray[parseInt(enumValue)] || enumValue;
                });
              }
            }
          });
          setUnitMappings(mappings);
          
        } else {
          setSchemaFields([]);
          setUnitMappings({});
        }
      } catch (error) {
        console.error('Error extracting schema fields:', error);
        setSchemaFields([]);
        setUnitMappings({});
      }
    } else {
      setSchemaFields([]);
      setUnitMappings({});
    }
  }, [selectedDevice]);

  // Add useLayoutEffect to restore scroll positions after data updates
  useLayoutEffect(() => {
    // Restore scroll positions after DOM updates
    if (mainContentRef.current && scrollPositions.current.main > 0) {
      mainContentRef.current.scrollTop = scrollPositions.current.main;
    }
    if (terminalRef.current && scrollPositions.current.terminal > 0) {
      terminalRef.current.scrollTop = scrollPositions.current.terminal;
    }
  }, [telemetryData]); // Run after telemetryData changes

  const fetchTelemetryDataInternal = useCallback(async () => {
    if (!selectedDevice) return;

    // Save scroll positions before updating data
    if (mainContentRef.current) {
      scrollPositions.current.main = mainContentRef.current.scrollTop;
    }
    if (terminalRef.current) {
      scrollPositions.current.terminal = terminalRef.current.scrollTop;
    }

    try {
      const deviceId = selectedDevice.device_id || selectedDevice.id;
      const response = await authFetch(`/api/v1/devices/${deviceId}/telemetry?limit=20`);
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.telemetry && data.telemetry.length > 0) {
          // Always update telemetry data - let React handle diff optimization
          const newData = data.telemetry;
          
          // Check if data actually changed
          const hasChanged = JSON.stringify(newData) !== JSON.stringify(telemetryData);
          
          // Always update state with new data
          setTelemetryData(newData);
          setLastUpdate(new Date());
          setDataChanged(hasChanged);
          
          // Reset flash effect after 1 second
          if (hasChanged) {
            setTimeout(() => setDataChanged(false), 1000);
          }
          
          // Calculate data rate
          const messages = newData.length;
          const timeSpan = messages > 1 ? 
            (new Date(newData[0].timestamp).getTime() - 
             new Date(newData[messages - 1].timestamp).getTime()) / 1000 : 0;
          
          if (timeSpan > 0) {
            setDataRate(Math.round(messages / timeSpan * 60)); // messages per minute
          }
          
          // Reset error state on successful fetch
          setFetchError(null);
          setConsecutiveErrors(0);
        } else {
          setFetchError('No telemetry data available yet');
        }
      } else {
        console.error('[Telemetry] API Response not OK:', response.status, response.statusText);
        setFetchError(`Failed to fetch telemetry: ${response.status} ${response.statusText}`);
        setConsecutiveErrors(prev => {
          const newCount = prev + 1;
          // Stop auto-refresh after 5 consecutive errors
          if (newCount >= 5) {
            console.error('[Telemetry] Too many consecutive errors, stopping auto-refresh');
            setIsStreaming(false);
          }
          return newCount;
        });
      }
    } catch (error) {
      console.error('[Telemetry] Failed to fetch telemetry:', error);
      setFetchError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setConsecutiveErrors(prev => {
        const newCount = prev + 1;
        // Stop auto-refresh after 5 consecutive errors
        if (newCount >= 5) {
          console.error('[Telemetry] Too many consecutive errors, stopping auto-refresh');
          setIsStreaming(false);
        }
        return newCount;
      });
    }
    
    // Clear initial loading even on error
    if (initialLoading) {
      setInitialLoading(false);
    }
  }, [selectedDevice, initialLoading]);

  // Use throttled version of fetch function (min 1 second between calls)
  const fetchTelemetryData = useThrottledCallback(fetchTelemetryDataInternal, 1000, [fetchTelemetryDataInternal]);

  useEffect(() => {
    // Clear any existing intervals
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }

    if (selectedDevice && isStreaming) {
      
      // Reset countdown
      setCountdown(10);
      
      // Start fetching telemetry data immediately
      fetchTelemetryData();
      
      // Set up countdown timer (updates every second)
      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            return 10; // Reset when reaching 0
          }
          return prev - 1;
        });
      }, 1000);
      
      // Set up polling interval (every 10 seconds for realtime telemetry monitoring)
      intervalRef.current = setInterval(() => {
        fetchTelemetryData();
        setCountdown(10); // Reset countdown
      }, 10000); // 10-second refresh for realtime telemetry monitoring
      
    } else {
    }

    // Cleanup function
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
    };
  }, [selectedDevice, isStreaming, fetchTelemetryData]);

  const getLatestValue = (key: string): number | null => {
    if (telemetryData.length === 0) return null;
    const latestData = telemetryData[0];
    
    
    // Check if data is nested under 'data' field (new structure)
    if (latestData.data && typeof latestData.data === 'object') {
      // First try direct key access
      const value = latestData.data[key];
      if (typeof value === 'number') return value;

      // Try with 'data_' prefix (e.g., 'temperature' -> 'data_temperature')
      const prefixedKey = `data_${key}`;
      const prefixedValue = latestData.data[prefixedKey];
      if (typeof prefixedValue === 'number') return prefixedValue;

      // If not found, search in nested objects (connection_info, device_health, etc.)
      for (const [objKey, objValue] of Object.entries(latestData.data)) {
        if (typeof objValue === 'object' && objValue !== null) {
          if (objValue[key] !== undefined) {
            const nestedValue = objValue[key];
            return typeof nestedValue === 'number' ? nestedValue : null;
          }
        }
      }

      return null;
    }
    
    // Check if data is at root level (old structure)
    const value = latestData[key];
    return typeof value === 'number' ? value : null;
  };

  const getTrend = (key: string): 'up' | 'down' | 'stable' => {
    if (telemetryData.length < 2) return 'stable';
    
    // Helper function to get value from data structure
    const getValue = (data: any, key: string): number | null => {
      if (data.data && typeof data.data === 'object') {
        // First try direct access
        const value = data.data[key];
        if (typeof value === 'number') return value;

        // Try with 'data_' prefix (e.g., 'temperature' -> 'data_temperature')
        const prefixedKey = `data_${key}`;
        const prefixedValue = data.data[prefixedKey];
        if (typeof prefixedValue === 'number') return prefixedValue;

        // Search in nested objects
        for (const [objKey, objValue] of Object.entries(data.data)) {
          if (typeof objValue === 'object' && objValue !== null) {
            if (objValue[key] !== undefined && typeof objValue[key] === 'number') {
              return objValue[key];
            }
          }
        }

        return null;
      }

      // Check root level
      const value = data[key];
      return typeof value === 'number' ? value : null;
    };
    
    // Get latest and previous values
    const latest = getValue(telemetryData[0], key);
    const previous = getValue(telemetryData[1], key);
    
    if (latest === null || previous === null) return 'stable';
    
    const diff = latest - previous;
    if (Math.abs(diff) < 0.1) return 'stable';
    return diff > 0 ? 'up' : 'down';
  };

  const formatValue = (value: any, unit?: string, field?: SchemaField): string => {
    if (value === null || value === undefined) return '--';
    
    // Handle boolean values
    if (typeof value === 'boolean') {
      return value ? 'ON' : 'OFF';
    }
    
    // Handle complex objects (prevent React Error #31)
    if (typeof value === 'object' && value !== null) {
      // Handle coordinate objects (accelerometer, gyroscope, etc.)
      if (value.x !== undefined && value.y !== undefined && value.z !== undefined) {
        const x = typeof value.x === 'number' ? value.x.toFixed(1) : value.x;
        const y = typeof value.y === 'number' ? value.y.toFixed(1) : value.y;
        const z = typeof value.z === 'number' ? value.z.toFixed(1) : value.z;
        return `X:${x} Y:${y} Z:${z}${unit || ''}`;
      }
      
      // Handle other objects by showing key-value pairs or meaningful representation
      try {
        const keys = Object.keys(value);
        
        // Handle specific telemetry patterns
        // Handle connection info objects
        if (value.auth_mode || value.mqtt_qos) {
          const parts: string[] = [];
          if (value.auth_mode) parts.push(`Auth: ${value.auth_mode}`);
          if (value.mqtt_qos) parts.push(`QoS: ${value.mqtt_qos}`);
          return parts.join(', ');
        }
        
        // Handle device health objects
        if (value.battery_level !== undefined || value.cpu_usage !== undefined || value.memory_usage !== undefined) {
          const parts: string[] = [];
          if (value.battery_level !== undefined) parts.push(`Battery: ${value.battery_level}%`);
          if (value.cpu_usage !== undefined) parts.push(`CPU: ${value.cpu_usage}%`);
          if (value.memory_usage !== undefined) parts.push(`Memory: ${value.memory_usage}%`);
          return parts.join(', ');
        }
        
        // Handle motion data objects
        if (value.motion_detected !== undefined || value.acceleration !== undefined) {
          const parts: string[] = [];
          if (value.motion_detected !== undefined) parts.push(`Motion: ${value.motion_detected ? 'Yes' : 'No'}`);
          if (value.acceleration !== undefined) parts.push(`Accel: ${value.acceleration}`);
          return parts.join(', ');
        }
        
        // Handle motion data with accelerometer and gyroscope objects
        if (value.accelerometer || value.gyroscope) {
          const parts: string[] = [];
          if (value.accelerometer && typeof value.accelerometer === 'object') {
            if (value.accelerometer.x !== undefined && value.accelerometer.y !== undefined && value.accelerometer.z !== undefined) {
              const x = typeof value.accelerometer.x === 'number' ? value.accelerometer.x.toFixed(2) : value.accelerometer.x;
              const y = typeof value.accelerometer.y === 'number' ? value.accelerometer.y.toFixed(2) : value.accelerometer.y;
              const z = typeof value.accelerometer.z === 'number' ? value.accelerometer.z.toFixed(2) : value.accelerometer.z;
              parts.push(`Accel[${x},${y},${z}]`);
            } else {
              parts.push(`Accel: ${formatValue(value.accelerometer)}`);
            }
          }
          if (value.gyroscope && typeof value.gyroscope === 'object') {
            if (value.gyroscope.x !== undefined && value.gyroscope.y !== undefined && value.gyroscope.z !== undefined) {
              const x = typeof value.gyroscope.x === 'number' ? value.gyroscope.x.toFixed(2) : value.gyroscope.x;
              const y = typeof value.gyroscope.y === 'number' ? value.gyroscope.y.toFixed(2) : value.gyroscope.y;
              const z = typeof value.gyroscope.z === 'number' ? value.gyroscope.z.toFixed(2) : value.gyroscope.z;
              parts.push(`Gyro[${x},${y},${z}]`);
            } else {
              parts.push(`Gyro: ${formatValue(value.gyroscope)}`);
            }
          }
          return parts.join(', ');
        }
        
        // Generic object handling
        if (keys.length === 1) {
          // Single key-value: just show the value
          const key = keys[0];
          const val = value[key];
          if (typeof val === 'string' || typeof val === 'number') {
            return String(val);
          }
        } else if (keys.length <= 3) {
          // Multiple key-value pairs: show as readable format
          return keys.map(k => {
            const val = value[k];
            if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
              return `${k}: ${val}`;
            }
            return `${k}: [${typeof val}]`;
          }).join(', ');
        } else {
          // For complex objects, show a summary instead of truncated JSON
          return `{${keys.length} fields}`;
        }
      } catch {
        return '[Object]';
      }
    }
    
    // Handle integer enum values (map to unit strings)
    if (field && field.type === 'integer' && field.enum && typeof value === 'number') {
      const unitArray = getUnitArrayForField(field.key);
      if (unitArray && unitArray[value]) {
        return unitArray[value];
      }
      // Fall back to enum string if no unit mapping
      if (field.enum[value]) {
        return field.enum[value];
      }
    }
    
    // Handle numeric values
    if (typeof value === 'number') {
      const precision = value < 10 ? 1 : 0;
      return `${value.toFixed(precision)}${unit || ''}`;
    }
    
    // Handle strings (ensure they're not JSON objects)
    if (typeof value === 'string') {
      // Try to parse if it looks like JSON
      if (value.startsWith('{') || value.startsWith('[')) {
        try {
          const parsed = JSON.parse(value);
          return formatValue(parsed, unit, field); // Recursively format the parsed object
        } catch {
          // If parsing fails, truncate the string
          return value.length > 30 ? value.substring(0, 30) + '...' : value;
        }
      }
      return value;
    }
    
    return String(value);
  };

  const handleOpenDashboardBuilder = () => {
    if (!selectedDevice) return;
    
    // Navigate to dashboard builder with device pre-selected
    navigate('/device-data-dashboard', {
      state: {
        preSelectedDevice: {
          id: selectedDevice.id,
          device_id: selectedDevice.device_id,
          name: selectedDevice.name,
          type: selectedDevice.type,
          schema: selectedDevice.telemetrySchema?.schema
        }
      }
    });
  };

  const handleExportTelemetry = async (format: 'csv' | 'json') => {
    if (!selectedDevice || telemetryData.length === 0) return;

    try {
      let content: string;
      let filename: string;
      let mimeType: string;

      if (format === 'csv') {
        // Generate CSV content
        const headers = ['timestamp', ...Object.keys(telemetryData[0]).filter(key => key !== 'timestamp')];
        const csvRows = [
          headers.join(','),
          ...telemetryData.map(row => 
            headers.map(header => {
              const value = row[header];
              return value !== null && value !== undefined ? value.toString() : '';
            }).join(',')
          )
        ];
        content = csvRows.join('\n');
        filename = `${selectedDevice.device_id}_telemetry_${new Date().toISOString().split('T')[0]}.csv`;
        mimeType = 'text/csv';
      } else {
        // Generate JSON content
        content = JSON.stringify({
          device: {
            id: selectedDevice.device_id,
            name: selectedDevice.name,
            type: selectedDevice.type
          },
          exportDate: new Date().toISOString(),
          dataCount: telemetryData.length,
          telemetryData: telemetryData
        }, null, 2);
        filename = `${selectedDevice.device_id}_telemetry_${new Date().toISOString().split('T')[0]}.json`;
        mimeType = 'application/json';
      }

      // Create and download file
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Error exporting telemetry data:', error);
    }
  };

  const getSchemaFieldValue = useCallback((field: SchemaField): any => {
    if (telemetryData.length === 0) return null;
    const latestData = telemetryData[0];
    
    
    // Check if data is nested under 'data' field (new structure)
    if (latestData.data && typeof latestData.data === 'object') {
      // First try direct key access
      const value = latestData.data[field.key];
      if (value !== undefined) return value;
      
      // If not found, search in nested objects (connection_info, device_health, etc.)
      for (const [objKey, objValue] of Object.entries(latestData.data)) {
        if (typeof objValue === 'object' && objValue !== null) {
          if (objValue[field.key] !== undefined) {
            return objValue[field.key];
          }
        }
      }
      
      // If field key matches one of the object keys, return the whole object for formatting
      if (latestData.data[field.key] !== undefined) {
        return latestData.data[field.key];
      }
      
      return null;
    }
    
    // Check if data is at root level (old structure)  
    const value = latestData[field.key];
    return value !== undefined ? value : null;
  }, [telemetryData]);

  const getSchemaFieldIcon = useCallback((field: SchemaField) => {
    const key = field.key.toLowerCase();
    const title = field.title?.toLowerCase() || '';
    
    // Temperature sensors
    if (key.includes('temperature') || title.includes('temperature') || key.includes('temp')) return Thermometer;
    
    // Humidity sensors
    if (key.includes('humidity') || title.includes('humidity') || key.includes('humid')) return Droplets;
    
    // Pressure sensors
    if (key.includes('pressure') || title.includes('pressure') || key.includes('press')) return Gauge;
    
    // Electrical measurements
    if (key.includes('voltage') || key.includes('volt') || title.includes('voltage')) return Zap;
    if (key.includes('current') || key.includes('amp') || title.includes('current')) return Zap;
    if (key.includes('power') || key.includes('watt') || title.includes('power')) return Zap;
    
    // Motion/vibration sensors
    if (key.includes('vibration') || key.includes('accel') || key.includes('gyro') || title.includes('vibration')) return Activity;
    
    // Light sensors
    if (key.includes('light') || key.includes('lux') || key.includes('illumin') || title.includes('light')) return Sun;
    
    // Air quality
    if (key.includes('air') || key.includes('co2') || key.includes('pm') || key.includes('gas')) return Wind;
    
    // Flow sensors
    if (key.includes('flow') || key.includes('rate') || title.includes('flow')) return Activity;
    
    // Boolean/status fields
    if (field.type === 'boolean' || field.enum) return Activity;
    
    return Gauge; // default icon
  }, []);

  // Prepare chart data (reverse order for chronological display)
  // Memoize chart data preparation for performance and proper React updates
  const chartData = useMemo(() => {
    return [...telemetryData].reverse().map((d, index) => {
      const dataPoint: any = {
        time: new Date(d.timestamp).toLocaleTimeString(),
        // Add unique key for chart rendering
        key: `${d.timestamp}-${index}`
      };
      
      // Check if data is nested under 'data' field (new structure)
      if (d.data && typeof d.data === 'object') {
        Object.keys(d.data).forEach(key => {
          if (typeof d.data[key] === 'number') {
            // Strip 'data_' prefix for compatibility with chart components
            const cleanKey = key.startsWith('data_') ? key.replace('data_', '') : key;
            dataPoint[cleanKey] = d.data[key];
          }
        });
      } else {
        // Include all numeric fields from telemetry data (old structure)
        Object.keys(d).forEach(key => {
          if (key !== 'timestamp' && typeof d[key] === 'number') {
            dataPoint[key] = d[key];
          }
        });
      }
      
      return dataPoint;
    });
  }, [telemetryData]);

  // Conditional wrapper based on usage context
  const WrapperComponent = onClose ? 
    ({ children }: { children: React.ReactNode }) => (
      <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
        <div className={cn(
          "bg-background rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden transition-all duration-300",
          dataChanged && "ring-2 ring-green-500 ring-opacity-50"
        )}>
          {children}
        </div>
      </div>
    ) :
    ({ children }: { children: React.ReactNode }) => (
      <div className={cn(
        "w-full h-full transition-all duration-300",
        dataChanged && "ring-2 ring-green-500 ring-opacity-50"
      )}>
        {children}
      </div>
    );

  return (
    <WrapperComponent>
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Real-time Telemetry Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              Live data streaming from IoT devices via MQTT
            </p>
          </div>
          <div className="flex items-center gap-2">
            {selectedDevice && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleOpenDashboardBuilder}
                  className="flex items-center gap-2"
                >
                  <BarChart3 className="h-4 w-4" />
                  Dashboard Builder
                  <ExternalLink className="h-3 w-3" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExportTelemetry('csv')}
                  disabled={telemetryData.length === 0}
                >
                  <Download className="h-4 w-4 mr-1" />
                  CSV
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExportTelemetry('json')}
                  disabled={telemetryData.length === 0}
                >
                  <Download className="h-4 w-4 mr-1" />
                  JSON
                </Button>
              </>
            )}
            <Button
              variant={isStreaming ? "default" : "outline"}
              size="sm"
              onClick={() => setIsStreaming(!isStreaming)}
            >
              {isStreaming ? (
                <>
                  <Pause className="h-4 w-4 mr-1" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-1" />
                  Resume
                </>
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => fetchTelemetryData()}
              disabled={!selectedDevice || isStreaming}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            {onClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Content */}
        <div 
          ref={mainContentRef}
          className={cn(
            "p-4 overflow-auto",
            onClose ? "max-h-[calc(90vh-80px)]" : "max-h-[60vh]"
          )}
        >
          {/* Device Selector */}
          <div className="mb-4">
            <label className="text-sm font-medium mb-2 block">Select Device</label>
            <div className="flex gap-2 flex-wrap">
              {onlineDevices.map(device => (
                <Button
                  key={device.id}
                  variant={selectedDevice?.id === device.id ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    setSelectedDevice(device);
                    setTelemetryData([]);
                    setFetchError(null);
                    setConsecutiveErrors(0);
                    // Ensure streaming is enabled when switching devices
                    if (!isStreaming) {
                      setIsStreaming(true);
                    }
                  }}
                  className="flex items-center gap-2"
                >
                  <div className={cn(
                    "h-2 w-2 rounded-full",
                    device.status === 'online' ? 'bg-green-500 animate-pulse' : 
                    device.status === 'active' ? 'bg-blue-500 animate-pulse' : 
                    'bg-gray-400'
                  )} />
                  {device.name} ({device.status || 'unknown'})
                  {device.telemetry && (
                    <Badge variant="secondary" className="ml-1">
                      {device.telemetry.messagesPerMinute} msg/min
                    </Badge>
                  )}
                </Button>
              ))}
              {onlineDevices.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No active devices available for telemetry. Check device status or start virtual devices.
                </p>
              )}
            </div>
          </div>

          {selectedDevice && (
            <>
              {/* Status Bar */}
              <div className="flex items-center justify-between mb-4 p-3 bg-muted rounded-lg">
                <div className="flex items-center gap-4">
                  <Badge variant={isStreaming ? "default" : "secondary"} className="flex items-center gap-1">
                    {isStreaming && <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />}
                    {isStreaming ? 'Live' : 'Paused'}
                  </Badge>
                  <span className="text-sm">
                    Data Rate: <strong>{dataRate} msg/min</strong>
                  </span>
                  {lastUpdate && (
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <RefreshCw className={cn("h-3 w-3", isStreaming && "animate-spin")} />
                      Last Update: {lastUpdate.toLocaleTimeString()}
                      {isStreaming && (
                        <span className="text-xs font-medium text-green-600">
                          (next refresh in {countdown}s)
                        </span>
                      )}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {telemetryData.length > 0 && (
                    <span>Showing {telemetryData.length} recent records</span>
                  )}
                  <Badge variant="outline" className="text-xs">
                    Render #{renderCount.current}
                  </Badge>
                </div>
              </div>

              {/* Error Alert */}
              {fetchError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <X className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-red-700 dark:text-red-400">{fetchError}</span>
                    </div>
                    {consecutiveErrors >= 5 && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setConsecutiveErrors(0);
                          setFetchError(null);
                          setIsStreaming(true);
                        }}
                      >
                        Retry
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {/* Schema-Based Quick Metrics */}
              {schemaFields.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-medium text-muted-foreground">Auto-Detected Schema Fields</h3>
                      <Badge variant="secondary" className="text-xs">
                        {schemaFields.length} fields
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        From Device Schema
                      </Badge>
                      {selectedDevice?.telemetrySchema?.lastUpdated && (
                        <Badge variant="outline" className="text-xs text-muted-foreground">
                          Updated: {new Date(selectedDevice.telemetrySchema.lastUpdated).toLocaleDateString()}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className={cn(
                    "grid gap-4 mb-4",
                    schemaFields.length <= 2 ? "grid-cols-1 md:grid-cols-2" :
                    schemaFields.length <= 3 ? "grid-cols-1 md:grid-cols-3" :
                    schemaFields.length <= 4 ? "grid-cols-1 md:grid-cols-2 lg:grid-cols-4" :
                    schemaFields.length <= 6 ? "grid-cols-1 md:grid-cols-3 lg:grid-cols-6" :
                    "grid-cols-1 md:grid-cols-4 lg:grid-cols-4 xl:grid-cols-8"
                  )}>
                    {schemaFields.map((field, index) => {
                      const IconComponent = getSchemaFieldIcon(field);
                      const value = getSchemaFieldValue(field);
                      const trend = field.type === 'boolean' ? 'stable' : getTrend(field.key);
                      
                      // Determine card styling based on field type and value
                      const cardClassName = field.type === 'boolean' && value === true 
                        ? "bg-gradient-to-br from-green-50 to-green-100 border-green-200 dark:from-green-900/20 dark:to-green-800/20 dark:border-green-700"
                        : field.type === 'boolean' && value === false
                        ? "bg-gradient-to-br from-gray-50 to-gray-100 border-gray-200 dark:from-gray-900/20 dark:to-gray-800/20 dark:border-gray-700"
                        : "bg-gradient-to-br from-background to-muted/20";
                      
                      const valueColor = field.type === 'boolean' && value === true 
                        ? "text-green-600 dark:text-green-400"
                        : field.type === 'boolean' && value === false
                        ? "text-gray-600 dark:text-gray-400"
                        : "";
                      
                      return (
                        <Card key={index} className={cardClassName}>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm flex items-center justify-between">
                              <span className="flex items-center gap-2">
                                <IconComponent className="h-4 w-4" />
                                <span className="truncate" title={field.title || field.key}>
                                  {field.title || field.key}
                                </span>
                              </span>
                              {field.type !== 'boolean' && (
                                <>
                                  {trend === 'up' && <TrendingUp className="h-4 w-4 text-green-500" />}
                                  {trend === 'down' && <TrendingDown className="h-4 w-4 text-red-500" />}
                                  {trend === 'stable' && <Minus className="h-4 w-4 text-gray-500" />}
                                </>
                              )}
                              {field.type === 'boolean' && (
                                <div className={cn(
                                  "h-2 w-2 rounded-full",
                                  value ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                                )} />
                              )}
                            </CardTitle>
                          </CardHeader>
                          <CardContent>
                            <p className={cn("text-2xl font-bold", valueColor)}>
                              {formatValue(value, field.unit, field)}
                            </p>
                            {field.description && (
                              <p className="text-xs text-muted-foreground mt-1 line-clamp-2" title={field.description}>
                                {field.description}
                              </p>
                            )}
                            {field.category && (
                              <div className="mt-2">
                                <span className={cn(
                                  "inline-block px-2 py-1 text-xs rounded-full",
                                  field.category === 'sensor' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' :
                                  field.category === 'status' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                                  field.category === 'computed' ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300' :
                                  'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                                )}>
                                  {field.category}
                                </span>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Traditional Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {/* Temperature */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Thermometer className="h-4 w-4" />
                        Temperature
                      </span>
                      {getTrend('temperature') === 'up' && <TrendingUp className="h-4 w-4 text-red-500" />}
                      {getTrend('temperature') === 'down' && <TrendingDown className="h-4 w-4 text-blue-500" />}
                      {getTrend('temperature') === 'stable' && <Minus className="h-4 w-4 text-gray-500" />}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">
                      {formatValue(getLatestValue('temperature'), '°C')}
                    </p>
                  </CardContent>
                </Card>

                {/* Humidity */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Droplets className="h-4 w-4" />
                        Humidity
                      </span>
                      {getTrend('humidity') === 'up' && <TrendingUp className="h-4 w-4 text-blue-500" />}
                      {getTrend('humidity') === 'down' && <TrendingDown className="h-4 w-4 text-orange-500" />}
                      {getTrend('humidity') === 'stable' && <Minus className="h-4 w-4 text-gray-500" />}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">
                      {formatValue(getLatestValue('humidity'), '%')}
                    </p>
                  </CardContent>
                </Card>

                {/* Pressure */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Gauge className="h-4 w-4" />
                      Pressure
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">
                      {formatValue(getLatestValue('pressure'), ' hPa')}
                    </p>
                  </CardContent>
                </Card>

                {/* Voltage */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Zap className="h-4 w-4" />
                      Voltage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold">
                      {formatValue(getLatestValue('voltage'), 'V')}
                    </p>
                  </CardContent>
                </Card>
              </div>

              {/* Charts */}
              <Tabs defaultValue={
                schemaFields.length > 0 
                  ? schemaFields.find(f => f.type === 'number' || f.type === 'integer')?.key || "temperature"
                  : "temperature"
              } className="w-full">
                <TabsList className="grid w-full grid-cols-2 md:grid-cols-4">
                  {schemaFields.length > 0 ? (
                    // Show schema-based tabs (limit to 4 for good UX)
                    schemaFields
                      .filter(field => field.type === 'number' || field.type === 'integer') // Only numeric fields for charts
                      .slice(0, 4)
                      .map((field) => (
                        <TabsTrigger key={field.key} value={field.key}>
                          <span className="truncate">
                            {(field.title || field.key).length > 12 
                              ? `${(field.title || field.key).substring(0, 12)}...`
                              : (field.title || field.key)
                            }
                          </span>
                        </TabsTrigger>
                      ))
                  ) : (
                    // Show default tabs if no schema
                    <>
                      <TabsTrigger value="temperature">Temperature</TabsTrigger>
                      <TabsTrigger value="humidity">Humidity</TabsTrigger>
                      <TabsTrigger value="pressure">Pressure</TabsTrigger>
                      <TabsTrigger value="voltage">Voltage</TabsTrigger>
                    </>
                  )}
                </TabsList>

                <TabsContent value="temperature" className="h-64">
                  <ResponsiveContainer width="100%" height="100%" key="temp-chart">
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Area 
                        type="monotone" 
                        dataKey="temperature" 
                        stroke="#ef4444" 
                        fill="#ef444430"
                        name="Temperature (°C)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </TabsContent>

                <TabsContent value="humidity" className="h-64">
                  <ResponsiveContainer width="100%" height="100%" key="humidity-chart">
                    <AreaChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Area 
                        type="monotone" 
                        dataKey="humidity" 
                        stroke="#3b82f6" 
                        fill="#3b82f630"
                        name="Humidity (%)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </TabsContent>

                <TabsContent value="pressure" className="h-64">
                  <ResponsiveContainer width="100%" height="100%" key="pressure-chart">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="pressure" 
                        stroke="#10b981"
                        name="Pressure (hPa)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </TabsContent>

                <TabsContent value="voltage" className="h-64">
                  <ResponsiveContainer width="100%" height="100%" key="voltage-chart">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Line 
                        type="monotone" 
                        dataKey="voltage" 
                        stroke="#f59e0b"
                        name="Voltage (V)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </TabsContent>
                
                {/* Dynamic schema-based charts */}
                {schemaFields
                  .filter(field => field.type === 'number' || field.type === 'integer')
                  .map((field, chartIndex) => {
                    const colors = [
                      { stroke: '#8b5cf6', fill: '#8b5cf630' }, // purple
                      { stroke: '#06b6d4', fill: '#06b6d430' }, // cyan
                      { stroke: '#10b981', fill: '#10b98130' }, // emerald
                      { stroke: '#f59e0b', fill: '#f59e0b30' }, // amber
                      { stroke: '#ef4444', fill: '#ef444430' }, // red
                      { stroke: '#3b82f6', fill: '#3b82f630' }, // blue
                    ];
                    
                    const color = colors[chartIndex % colors.length];
                    
                    return (
                      <TabsContent key={field.key} value={field.key} className="h-64">
                        <ResponsiveContainer width="100%" height="100%" key={`${field.key}-chart`}>
                          <AreaChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="time" />
                            <YAxis 
                              tickFormatter={(value) => {
                                // Format Y-axis based on field type and unit
                                if (field.type === 'integer' && field.enum) {
                                  const unitArray = getUnitArrayForField(field.key);
                                  if (unitArray && unitArray[value]) {
                                    return unitArray[value];
                                  }
                                }
                                return typeof value === 'number' ? value.toFixed(1) : value;
                              }}
                            />
                            <Tooltip 
                              formatter={(value: any) => {
                                return [formatValue(value, field.unit, field), field.title || field.key];
                              }}
                              labelFormatter={(label) => `Time: ${label}`}
                            />
                            <Area 
                              type="monotone" 
                              dataKey={field.key} 
                              stroke={color.stroke} 
                              fill={color.fill}
                              name={`${field.title || field.key}${field.unit ? ` (${field.unit})` : ''}`}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </TabsContent>
                    );
                  })}
              </Tabs>

              {/* Raw Data Stream */}
              <Card className="mt-4">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm">Live Data Stream</CardTitle>
                      <CardDescription>Recent telemetry messages in terminal format</CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Hybrid View
                      </Badge>
                      {selectedDevice && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleOpenDashboardBuilder}
                          className="text-xs"
                        >
                          <BarChart3 className="h-3 w-3 mr-1" />
                          Advanced Charts
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div 
                    ref={terminalRef}
                    className="bg-black text-green-400 p-3 rounded font-mono text-xs max-h-32 overflow-auto"
                  >
                    {telemetryData.slice(0, 5).map((data, idx) => {
                      // Get the actual data object (handle nested structure)
                      const actualData = data.data && typeof data.data === 'object' ? data.data : data;
                      
                      return (
                        <div key={idx} className="mb-1">
                          [{new Date(data.timestamp).toLocaleTimeString()}] 
                          {/* Show schema-based fields if available */}
                          {schemaFields.length > 0 ? (
                            schemaFields.slice(0, 5).map(field => { // Limit to first 5 fields for terminal display
                              const value = actualData[field.key];
                              if (value !== undefined && value !== null) {
                                // Handle complex objects (like accelerometer data)
                                let displayValue;
                                if (typeof value === 'object' && value !== null) {
                                  // For complex objects, show a summary or key values
                                  if (value.x !== undefined && value.y !== undefined && value.z !== undefined) {
                                    displayValue = `X:${value.x?.toFixed?.(1) || value.x} Y:${value.y?.toFixed?.(1) || value.y} Z:${value.z?.toFixed?.(1) || value.z}`;
                                  } else {
                                    displayValue = JSON.stringify(value).substring(0, 20) + '...';
                                  }
                                } else {
                                  displayValue = formatValue(value, field.unit, field);
                                }
                                
                                const shortKey = (field.title || field.key).length > 8 
                                  ? (field.title || field.key).substring(0, 8)
                                  : (field.title || field.key);
                                return ` ${shortKey}:${displayValue}`;
                              }
                              return '';
                            }).join('')
                          ) : (
                            // Fall back to standard fields
                            <>
                              {actualData.temperature && ` T:${actualData.temperature}°C`}
                              {actualData.humidity && ` H:${actualData.humidity}%`}
                              {actualData.pressure && ` P:${actualData.pressure}hPa`}
                              {actualData.voltage && ` V:${actualData.voltage}V`}
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
    </WrapperComponent>
  );
});

RealtimeTelemetryDashboardInner.displayName = 'RealtimeTelemetryDashboardInner';

// Export with error boundary
export const RealtimeTelemetryDashboard: React.FC<RealtimeTelemetryDashboardProps> = (props) => {
  return (
    <ErrorBoundary>
      <RealtimeTelemetryDashboardInner {...props} />
    </ErrorBoundary>
  );
};