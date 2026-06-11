/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Comprehensive Chart Data Sanitizer for TESA IoT Platform
 * Prevents DecimalError by ensuring all numeric values are valid before chart rendering
 */

import React from 'react';

export interface SanitizedValue {
  value: number;
  isValid: boolean;
  originalValue?: any;
}

/**
 * Ultra-safe numeric value sanitizer - absolutely no NaN can pass through
 */
export const sanitizeNumericValue = (value: any, fallback: number = 0): number => {
  // Handle null/undefined first
  if (value === null || value === undefined) return fallback;
  
  // If already a valid number
  if (typeof value === 'number') {
    return isNaN(value) || !isFinite(value) ? fallback : value;
  }
  
  // Try to convert string to number
  if (typeof value === 'string') {
    const parsed = parseFloat(value);
    return isNaN(parsed) || !isFinite(parsed) ? fallback : parsed;
  }
  
  // For objects, try to extract numeric value
  if (typeof value === 'object' && value !== null) {
    if ('value' in value) return sanitizeNumericValue(value.value, fallback);
    if ('y' in value) return sanitizeNumericValue(value.y, fallback);
    if ('x' in value) return sanitizeNumericValue(value.x, fallback);
  }
  
  return fallback;
};

/**
 * Sanitize array of data for charts - ensures NO NaN values reach Recharts
 */
export const sanitizeChartData = (data: any[], fields: string[] = []): any[] => {
  if (!Array.isArray(data) || data.length === 0) {
    return [];
  }
  
  return data.map((item, index) => {
    if (!item || typeof item !== 'object') {
      console.warn(`[ChartSanitizer] Invalid item at index ${index}:`, item);
      return null;
    }
    
    const sanitized: any = {};
    
    // Copy all non-numeric fields as-is
    Object.keys(item).forEach(key => {
      if (fields.length === 0 || fields.includes(key)) {
        const value = item[key];
        
        // Check if this is a numeric field that needs sanitization
        if (typeof value === 'number' || 
            (typeof value === 'string' && !isNaN(parseFloat(value))) ||
            key.includes('value') || key.includes('Value') ||
            key.includes('percent') || key.includes('Percent') ||
            key.includes('rate') || key.includes('Rate') ||
            key.includes('count') || key.includes('Count') ||
            key.includes('score') || key.includes('Score') ||
            key === 'x' || key === 'y' || key === 'z') {
          
          sanitized[key] = sanitizeNumericValue(value, 0);
        } else {
          sanitized[key] = value;
        }
      } else {
        sanitized[key] = item[key];
      }
    });
    
    return sanitized;
  }).filter(item => item !== null);
};

/**
 * Ultra-safe Recharts data wrapper - ZERO NaN guarantee
 * This version performs DEEP sanitization to prevent any NaN from reaching Recharts axis calculations
 */
export const makeSafeForRecharts = (data: any): any => {
  if (data === null || data === undefined) return [];
  
  if (Array.isArray(data)) {
    const sanitized = sanitizeChartData(data);
    // Additional check: if any item still contains NaN, return empty array
    const stringified = JSON.stringify(sanitized);
    if (stringified.includes('null') || stringified.includes('NaN') || stringified.includes('Infinity')) {
      console.warn('[ChartSanitizer] DEEP: Found NaN in array after sanitization, returning empty array');
      return [];
    }
    return sanitized;
  }
  
  if (typeof data === 'object') {
    const sanitized: any = {};
    Object.keys(data).forEach(key => {
      const value = data[key];
      if (Array.isArray(value)) {
        sanitized[key] = makeSafeForRecharts(value); // Recursive deep clean
      } else if (typeof value === 'number') {
        sanitized[key] = sanitizeNumericValue(value, 0);
      } else if (typeof value === 'object' && value !== null) {
        sanitized[key] = makeSafeForRecharts(value); // Recursive deep clean
      } else {
        sanitized[key] = value;
      }
    });
    
    // Final NaN check on the entire object
    const stringified = JSON.stringify(sanitized);
    if (stringified.includes('null') || stringified.includes('NaN') || stringified.includes('Infinity')) {
      console.warn('[ChartSanitizer] DEEP: Found NaN in object after sanitization, returning safe default');
      return { value: 0, name: 'Safe Data' };
    }
    
    return sanitized;
  }
  
  return data;
};

/**
 * Emergency fallback data generators for different chart types
 */
export const generateSafeFallbackData = (chartType: string = 'line'): any[] => {
  const baseTime = Date.now();
  const timeStep = 24 * 60 * 60 * 1000; // 1 day
  
  switch (chartType) {
    case 'line':
    case 'area':
      return Array.from({ length: 7 }, (_, i) => ({
        time: new Date(baseTime - (6 - i) * timeStep).toISOString().split('T')[0],
        value: 50 + Math.sin(i) * 20,
        trend: i % 2 === 0 ? 'up' : 'down'
      }));
      
    case 'bar':
      return Array.from({ length: 5 }, (_, i) => ({
        name: `Category ${i + 1}`,
        value: 30 + (i * 15),
        percentage: 20 * (i + 1)
      }));
      
    case 'pie':
    case 'donut':
      return [
        { name: 'Normal', value: 70, color: '#10B981' },
        { name: 'Warning', value: 20, color: '#F59E0B' },
        { name: 'Critical', value: 10, color: '#EF4444' }
      ];
      
    case 'scatter':
      return Array.from({ length: 20 }, (_, i) => ({
        x: i * 5,
        y: 25 + Math.random() * 50,
        z: 10 + Math.random() * 15
      }));
      
    case 'heatmap':
      return Array.from({ length: 7 }, (_, day) => 
        Array.from({ length: 24 }, (_, hour) => ({
          day: day + 1,
          hour: hour,
          value: Math.random() * 100,
          intensity: Math.random()
        }))
      ).flat();
      
    default:
      return [
        { name: 'Safe', value: 100 },
        { name: 'Data', value: 0 }
      ];
  }
};

/**
 * Master sanitization function - use this for ALL chart data
 */
export const sanitizeForAnalyticsDashboard = (data: any, componentName: string = 'Unknown'): any => {
  // Debug logging for Unknown components to help identify the source
  if (componentName === 'Unknown' && import.meta.env.DEV) {
    console.debug(`[ChartSanitizer] Component name missing. Call stack:`, new Error().stack?.split('\n').slice(1, 4).join('\n'));
  }
  
  try {
    const sanitized = makeSafeForRecharts(data);
    
    // Validate the result doesn't contain any NaN
    const hasNaN = JSON.stringify(sanitized).includes('null') || 
                   JSON.stringify(sanitized).includes('NaN') ||
                   JSON.stringify(sanitized).includes('Infinity');
    
    if (hasNaN) {
      console.warn(`[ChartSanitizer] Detected NaN in sanitized data for ${componentName}, using fallback`);
      return generateSafeFallbackData();
    }
    
    return sanitized;
    
  } catch (error) {
    console.error(`[ChartSanitizer] Error sanitizing data for ${componentName}:`, error);
    return generateSafeFallbackData();
  }
};

/**
 * React Hook for safe chart data
 */
export const useSafeChartData = (rawData: any, componentName: string) => {
  return React.useMemo(() => {
    return sanitizeForAnalyticsDashboard(rawData, componentName);
  }, [rawData, componentName]);
};


/**
 * Alias for sanitizeNumericValue for backward compatibility
 */
export const safeToNumber = sanitizeNumericValue;

/**
 * Enhanced validation for chart numbers
 */
export const isValidChartNumber = (value: any): boolean => {
  if (value === null || value === undefined) return false;
  const num = typeof value === 'number' ? value : Number(value);
  return !isNaN(num) && isFinite(num);
};

/**
 * Safe tooltip formatter that prevents NaN display
 */
export const safeTooltipFormatter = (value: any, name?: string): [string, string] => {
  const safeValue = sanitizeNumericValue(value, 0);
  const displayValue = typeof safeValue === 'number' ? safeValue.toFixed(1) : '0.0';
  return [displayValue, name || 'Value'];
};

/**
 * Legacy functions for backward compatibility
 */
export const sanitizeAnalyticsDataAuto = sanitizeForAnalyticsDashboard;
export const safeSanitizeAnalyticsData = sanitizeForAnalyticsDashboard;
export const sanitizeBarChartData = sanitizeForAnalyticsDashboard;
export const sanitizeTimeSeriesData = sanitizeForAnalyticsDashboard;
export const sanitizeRadialBarData = sanitizeForAnalyticsDashboard;
export const validateChartData = sanitizeChartData;
export const sanitizeChartDataSmart = sanitizeForAnalyticsDashboard;

/**
 * Safe label formatter for charts
 */
export const safeLabelFormatter = (value: any): string => {
  const safeValue = sanitizeNumericValue(value, 0);
  return typeof safeValue === 'number' ? safeValue.toString() : '0';
};

/**
 * Ultimate Recharts props sanitizer - prevents NaN in ALL chart props including domains
 */
export const sanitizeRechartsProps = (props: any): any => {
  if (!props || typeof props !== 'object') return props;
  
  const sanitized = { ...props };
  
  // Sanitize data arrays
  if (sanitized.data) {
    sanitized.data = makeSafeForRecharts(sanitized.data);
  }
  
  // Sanitize domain props that can cause axis calculation errors
  if (sanitized.domain && Array.isArray(sanitized.domain)) {
    sanitized.domain = sanitized.domain.map((d: any) => {
      if (typeof d === 'number') {
        return sanitizeNumericValue(d, 0);
      }
      return d;
    });
  }
  
  // Sanitize numeric props that can contain NaN
  const numericProps = ['cx', 'cy', 'r', 'x', 'y', 'width', 'height', 'outerRadius', 'innerRadius', 'angle', 'startAngle', 'endAngle'];
  numericProps.forEach(prop => {
    if (sanitized[prop] !== undefined) {
      sanitized[prop] = sanitizeNumericValue(sanitized[prop], 0);
    }
  });
  
  return sanitized;
};

/**
 * Safe Chart Component Wrapper - Ultimate protection
 */
export const withSafeChart = <T extends Record<string, any>>(
  ChartComponent: React.ComponentType<T>,
  chartType: string = 'chart'
) => {
  return React.forwardRef<any, T>((props, ref) => {
    const safeProps = sanitizeRechartsProps(props);
    
    React.useEffect(() => {
      console.log(`[ChartSanitizer] Rendering safe ${chartType} with props:`, safeProps);
    }, [safeProps]);
    
    return React.createElement(ChartComponent, { ...safeProps, ref });
  });
};