/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Clean MongoDB extended JSON format from telemetry data
 */
export function cleanMongoDBExtendedJSON(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj;
  }

  // Handle arrays
  if (Array.isArray(obj)) {
    return obj.map(item => cleanMongoDBExtendedJSON(item));
  }

  // Handle objects
  if (typeof obj === 'object') {
    // Check for MongoDB ObjectId format
    if (obj.$oid) {
      return obj.$oid;
    }

    // Check for MongoDB Date format
    if (obj.$date) {
      return new Date(obj.$date).toISOString();
    }

    // Check for MongoDB NumberLong format
    if (obj.$numberLong) {
      return parseInt(obj.$numberLong);
    }

    // Check for MongoDB NumberDecimal format
    if (obj.$numberDecimal) {
      return parseFloat(obj.$numberDecimal);
    }

    // Recursively clean nested objects
    const cleaned: any = {};
    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        // Skip internal MongoDB fields
        if (key.startsWith('_') && key !== '_id') {
          continue;
        }
        cleaned[key] = cleanMongoDBExtendedJSON(obj[key]);
      }
    }
    return cleaned;
  }

  // Return primitive values as-is
  return obj;
}

/**
 * Format telemetry data for display
 */
export function formatTelemetryData(telemetry: any): any {
  if (!telemetry) return null;

  // Clean MongoDB extended JSON format
  const cleaned = cleanMongoDBExtendedJSON(telemetry);

  // If it's an array, process each item
  if (Array.isArray(cleaned)) {
    return cleaned.map(item => formatSingleTelemetryRecord(item));
  }

  // Single record
  return formatSingleTelemetryRecord(cleaned);
}

/**
 * Format a single telemetry record
 */
function formatSingleTelemetryRecord(record: any): any {
  if (!record) return {};

  const formatted: any = {
    timestamp: record.timestamp || new Date().toISOString(),
    device_id: record.device_id || '',
    data: {},
    metadata: record.metadata || {}
  };

  // Handle data field
  if (record.data && typeof record.data === 'object') {
    formatted.data = cleanMongoDBExtendedJSON(record.data);
  } else {
    // Extract telemetry values from root level
    const skipFields = ['_id', 'timestamp', 'device_id', 'metadata', 'organization_id'];
    for (const key in record) {
      if (!skipFields.includes(key) && record.hasOwnProperty(key)) {
        formatted.data[key] = cleanMongoDBExtendedJSON(record[key]);
      }
    }
  }

  return formatted;
}

/**
 * Format telemetry value for display
 */
export function formatTelemetryValue(value: any): string {
  if (value === null || value === undefined) {
    return '--';
  }

  if (typeof value === 'number') {
    // Format numbers to 1 decimal place
    return value.toFixed(1);
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (typeof value === 'object') {
    // Handle any remaining MongoDB extended JSON
    const cleaned = cleanMongoDBExtendedJSON(value);
    if (typeof cleaned === 'object' && cleaned !== null) {
      // Instead of JSON.stringify, try to extract meaningful values
      
      // Handle common IoT sensor data patterns
      if (cleaned.x !== undefined && cleaned.y !== undefined && cleaned.z !== undefined) {
        // Accelerometer/gyroscope data
        const x = typeof cleaned.x === 'number' ? cleaned.x.toFixed(2) : cleaned.x;
        const y = typeof cleaned.y === 'number' ? cleaned.y.toFixed(2) : cleaned.y;
        const z = typeof cleaned.z === 'number' ? cleaned.z.toFixed(2) : cleaned.z;
        return `X:${x} Y:${y} Z:${z}`;
      }
      
      // Handle specific telemetry patterns
      const keys = Object.keys(cleaned);
      
      // Handle connection info objects
      if (cleaned.rssi !== undefined || cleaned.auth_mode || cleaned.mqtt_qos || cleaned.protocol) {
        const parts: string[] = [];
        if (cleaned.rssi !== undefined) parts.push(`RSSI: ${cleaned.rssi}dBm`);
        if (cleaned.auth_mode) parts.push(`Auth: ${cleaned.auth_mode}`);
        if (cleaned.mqtt_qos !== undefined) parts.push(`QoS: ${cleaned.mqtt_qos}`);
        if (cleaned.protocol) parts.push(`${cleaned.protocol}`);
        return parts.join(' • ');
      }
      
      // Handle device health objects
      if (cleaned.battery_level !== undefined || cleaned.cpu_usage !== undefined || cleaned.memory_usage !== undefined || cleaned.uptime_hours !== undefined) {
        const parts: string[] = [];
        if (cleaned.battery_level !== undefined) parts.push(`🔋 ${cleaned.battery_level}%`);
        if (cleaned.cpu_usage !== undefined) parts.push(`CPU: ${cleaned.cpu_usage}%`);
        if (cleaned.memory_usage !== undefined) parts.push(`Mem: ${cleaned.memory_usage}%`);
        if (cleaned.uptime_hours !== undefined) parts.push(`Up: ${cleaned.uptime_hours}h`);
        return parts.join(' • ');
      }
      
      // Handle motion data objects
      if (cleaned.motion_detected !== undefined || cleaned.accelerometer !== undefined || cleaned.gyroscope !== undefined) {
        const parts: string[] = [];
        if (cleaned.motion_detected !== undefined) {
          parts.push(cleaned.motion_detected ? '🟢 Motion' : '⚫ No Motion');
        }
        if (cleaned.accelerometer && typeof cleaned.accelerometer === 'object') {
          const acc = cleaned.accelerometer;
          const x = typeof acc.x === 'number' ? acc.x.toFixed(2) : acc.x;
          const y = typeof acc.y === 'number' ? acc.y.toFixed(2) : acc.y;
          const z = typeof acc.z === 'number' ? acc.z.toFixed(2) : acc.z;
          parts.push(`Accel[${x},${y},${z}]`);
        }
        if (cleaned.gyroscope && typeof cleaned.gyroscope === 'object') {
          const gyro = cleaned.gyroscope;
          const x = typeof gyro.x === 'number' ? gyro.x.toFixed(2) : gyro.x;
          const y = typeof gyro.y === 'number' ? gyro.y.toFixed(2) : gyro.y;
          const z = typeof gyro.z === 'number' ? gyro.z.toFixed(2) : gyro.z;
          parts.push(`Gyro[${x},${y},${z}]`);
        }
        return parts.join(' • ');
      }
      
      // Generic key-value pairs for small objects
      if (keys.length === 1) {
        // Single key-value: just show the value
        const key = keys[0];
        const val = cleaned[key];
        if (typeof val === 'string' || typeof val === 'number') {
          return String(val);
        }
      } else if (keys.length <= 3) {
        // Multiple key-value pairs: show as clean format
        return keys.map(key => {
          const val = cleaned[key];
          if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') {
            // Use cleaner format without showing keys for known patterns
            if (key === 'x' || key === 'y' || key === 'z') {
              return val;
            }
            return `${val}`;
          }
          return formatTelemetryValue(val);
        }).join(' • ');
      }
      
      // For complex objects, show a summary instead of full JSON
      return `${keys.length} fields`;
    }
    return String(cleaned);
  }

  return String(value);
}