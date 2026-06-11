/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useToast } from '@/hooks/use-toast';

// Performance monitoring types
interface PerformanceMetrics {
  cpuUsage: number;
  memoryUsage: number;
  activeRequests: number;
  averageResponseTime: number;
  errorRate: number;
}

// Refresh rate configuration
interface RefreshRateConfig {
  // Base intervals in milliseconds
  active: number;        // When tab is active and visible
  background: number;    // When tab is in background
  idle: number;         // When user is idle
  lowPerformance: number; // When system is under load
  
  // User preferences
  userPreference?: 'realtime' | 'normal' | 'conservative' | 'manual';
  customInterval?: number;
  
  // Performance thresholds
  cpuThreshold: number;      // CPU usage threshold (0-100)
  memoryThreshold: number;   // Memory usage threshold (0-100)
  errorRateThreshold: number; // Error rate threshold (0-1)
  responseTimeThreshold: number; // Response time threshold in ms
}

// Hook options
interface SmartRefreshOptions {
  onRefresh: () => Promise<void> | void;
  config?: Partial<RefreshRateConfig>;
  enablePerformanceMonitoring?: boolean;
  enableTabVisibility?: boolean;
  enableIdleDetection?: boolean;
  idleTimeout?: number; // Time before considering user idle (ms)
  minInterval?: number; // Minimum allowed interval (ms)
  maxInterval?: number; // Maximum allowed interval (ms)
  disabled?: boolean; // Disable auto-refresh entirely
}

// Default configuration
const DEFAULT_CONFIG: RefreshRateConfig = {
  active: 30000,        // 30 seconds
  background: 120000,   // 2 minutes
  idle: 300000,        // 5 minutes
  lowPerformance: 600000, // 10 minutes
  cpuThreshold: 80,
  memoryThreshold: 85,
  errorRateThreshold: 0.1,
  responseTimeThreshold: 5000,
};

// User preference presets
const PRESET_INTERVALS = {
  realtime: {
    active: 2000,      // 2 seconds
    background: 10000,  // 10 seconds
    idle: 30000,       // 30 seconds
    lowPerformance: 60000, // 1 minute
  },
  normal: {
    active: 10000,     // 10 seconds
    background: 30000, // 30 seconds
    idle: 120000,      // 2 minutes
    lowPerformance: 300000, // 5 minutes
  },
  conservative: {
    active: 30000,     // 30 seconds
    background: 120000, // 2 minutes
    idle: 300000,      // 5 minutes
    lowPerformance: 600000, // 10 minutes
  },
  manual: {
    active: 0,
    background: 0,
    idle: 0,
    lowPerformance: 0,
  }
};

export function useSmartRefreshRate({
  onRefresh,
  config = {},
  enablePerformanceMonitoring = true,
  enableTabVisibility = true,
  enableIdleDetection = true,
  idleTimeout = 300000, // 5 minutes
  minInterval = 1000,   // 1 second minimum
  maxInterval = 3600000, // 1 hour maximum
  disabled = false, // Disable auto-refresh entirely
}: SmartRefreshOptions) {
  const { toast } = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [currentInterval, setCurrentInterval] = useState<number>(DEFAULT_CONFIG.active);
  const [refreshMode, setRefreshMode] = useState<'active' | 'background' | 'idle' | 'lowPerformance'>('active');
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    cpuUsage: 0,
    memoryUsage: 0,
    activeRequests: 0,
    averageResponseTime: 0,
    errorRate: 0,
  });
  
  // References
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef<number>(Date.now());
  const requestTimingsRef = useRef<number[]>([]);
  const errorCountRef = useRef<number>(0);
  const requestCountRef = useRef<number>(0);
  const activeRequestsRef = useRef<number>(0);
  const performanceObserverRef = useRef<PerformanceObserver | null>(null);
  
  // Merge configurations
  const finalConfig = useRef<RefreshRateConfig>({
    ...DEFAULT_CONFIG,
    ...config,
  });

  // Apply user preference presets
  useEffect(() => {
    if (config.userPreference && config.userPreference !== 'manual') {
      const preset = PRESET_INTERVALS[config.userPreference];
      finalConfig.current = {
        ...finalConfig.current,
        ...preset,
        ...config, // Keep other custom configs
      };
    } else if (config.userPreference === 'manual' && config.customInterval) {
      finalConfig.current = {
        ...finalConfig.current,
        active: config.customInterval,
        background: config.customInterval * 2,
        idle: config.customInterval * 4,
        lowPerformance: config.customInterval * 8,
      };
    }
  }, [config]);

  // Monitor performance
  const updatePerformanceMetrics = useCallback(() => {
    if (!enablePerformanceMonitoring) return;

    // Calculate average response time
    const avgResponseTime = requestTimingsRef.current.length > 0
      ? requestTimingsRef.current.reduce((a, b) => a + b, 0) / requestTimingsRef.current.length
      : 0;

    // Calculate error rate
    const errorRate = requestCountRef.current > 0
      ? errorCountRef.current / requestCountRef.current
      : 0;

    // Estimate CPU usage (based on active requests and response times)
    const estimatedCpuUsage = Math.min(
      100,
      (activeRequestsRef.current * 10) + (avgResponseTime / 100)
    );

    // Estimate memory usage (simplified - in real app, use performance.memory if available)
    const estimatedMemoryUsage = performance.memory
      ? (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
      : 50; // Default to 50% if not available

    setPerformanceMetrics({
      cpuUsage: estimatedCpuUsage,
      memoryUsage: estimatedMemoryUsage,
      activeRequests: activeRequestsRef.current,
      averageResponseTime: avgResponseTime,
      errorRate: errorRate,
    });

    // Clear old data
    if (requestTimingsRef.current.length > 100) {
      requestTimingsRef.current = requestTimingsRef.current.slice(-50);
    }
  }, [enablePerformanceMonitoring]);

  // Determine optimal refresh interval
  const determineOptimalInterval = useCallback(() => {
    const config = finalConfig.current;
    let mode: typeof refreshMode = 'active';
    let interval = config.active;

    // Check performance metrics
    if (enablePerformanceMonitoring) {
      const { cpuUsage, memoryUsage, errorRate, averageResponseTime } = performanceMetrics;
      
      if (
        cpuUsage > config.cpuThreshold ||
        memoryUsage > config.memoryThreshold ||
        errorRate > config.errorRateThreshold ||
        averageResponseTime > config.responseTimeThreshold
      ) {
        mode = 'lowPerformance';
        interval = config.lowPerformance;
      }
    }

    // Check idle state
    if (enableIdleDetection && mode !== 'lowPerformance') {
      const idleTime = Date.now() - lastActivityRef.current;
      if (idleTime > idleTimeout) {
        mode = 'idle';
        interval = config.idle;
      }
    }

    // Check tab visibility
    if (enableTabVisibility && mode === 'active') {
      if (document.hidden) {
        mode = 'background';
        interval = config.background;
      }
    }

    // Apply min/max constraints
    interval = Math.max(minInterval, Math.min(maxInterval, interval));

    setRefreshMode(mode);
    setCurrentInterval(interval);
    return interval;
  }, [
    performanceMetrics,
    enablePerformanceMonitoring,
    enableIdleDetection,
    enableTabVisibility,
    idleTimeout,
    minInterval,
    maxInterval,
  ]);

  // Wrapped refresh function with performance tracking
  const performRefresh = useCallback(async () => {
    if (isRefreshing) return;

    const startTime = performance.now();
    activeRequestsRef.current++;
    requestCountRef.current++;
    setIsRefreshing(true);

    try {
      await onRefresh();
      const endTime = performance.now();
      requestTimingsRef.current.push(endTime - startTime);
    } catch (error) {
      errorCountRef.current++;
      console.error('Refresh error:', error);
    } finally {
      activeRequestsRef.current--;
      setIsRefreshing(false);
      updatePerformanceMetrics();
    }
  }, [onRefresh, isRefreshing, updatePerformanceMetrics]);

  // Setup refresh interval
  const setupInterval = useCallback(() => {
    console.log('[useSmartRefreshRate] setupInterval called, disabled:', disabled);
    
    // Clear existing interval
    if (intervalRef.current) {
      console.log('[useSmartRefreshRate] Clearing existing interval');
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // Don't setup interval if disabled
    if (disabled) {
      console.log('[useSmartRefreshRate] Hook is disabled, not setting up interval');
      return;
    }

    const interval = determineOptimalInterval();
    console.log('[useSmartRefreshRate] Determined optimal interval:', interval, 'ms');
    
    if (interval > 0) {
      console.log('[useSmartRefreshRate] Setting up interval with', interval, 'ms');
      intervalRef.current = setInterval(() => {
        console.log('[useSmartRefreshRate] ⏰ INTERVAL TRIGGERED - calling performRefresh');
        performRefresh();
      }, interval);
      console.log('[useSmartRefreshRate] ✅ Interval set up successfully, intervalRef:', !!intervalRef.current);
    } else {
      console.log('[useSmartRefreshRate] ❌ Interval is 0 or negative, not setting up');
    }
  }, [determineOptimalInterval, performRefresh, disabled]);

  // Activity tracking
  const trackActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
  }, []);

  // Setup event listeners
  useEffect(() => {
    if (enableIdleDetection) {
      const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
      events.forEach(event => {
        document.addEventListener(event, trackActivity);
      });

      return () => {
        events.forEach(event => {
          document.removeEventListener(event, trackActivity);
        });
      };
    }
  }, [enableIdleDetection, trackActivity]);

  // Tab visibility listener
  useEffect(() => {
    if (enableTabVisibility) {
      const handleVisibilityChange = () => {
        setupInterval();
      };

      document.addEventListener('visibilitychange', handleVisibilityChange);
      return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }
  }, [enableTabVisibility, setupInterval]);

  // Performance observer for resource timing
  useEffect(() => {
    if (enablePerformanceMonitoring && 'PerformanceObserver' in window) {
      try {
        performanceObserverRef.current = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          entries.forEach((entry) => {
            if (entry.entryType === 'resource' && entry.name.includes('/api/')) {
              requestTimingsRef.current.push(entry.duration);
            }
          });
        });

        performanceObserverRef.current.observe({ entryTypes: ['resource'] });
      } catch (error) {
        console.warn('PerformanceObserver not supported:', error);
      }

      return () => {
        performanceObserverRef.current?.disconnect();
      };
    }
  }, [enablePerformanceMonitoring]);

  // Monitor performance metrics periodically
  useEffect(() => {
    if (enablePerformanceMonitoring) {
      const metricsInterval = setInterval(updatePerformanceMetrics, 5000);
      return () => clearInterval(metricsInterval);
    }
  }, [enablePerformanceMonitoring, updatePerformanceMetrics]);

  // Setup and update interval
  useEffect(() => {
    console.log('[useSmartRefreshRate] Main effect triggered. Disabled:', disabled);
    setupInterval();
    
    // Re-evaluate interval periodically (only if not disabled)
    let evaluationInterval: NodeJS.Timeout | null = null;
    if (!disabled) {
      console.log('[useSmartRefreshRate] Setting up 30s evaluation interval');
      evaluationInterval = setInterval(() => {
        console.log('[useSmartRefreshRate] Re-evaluating interval (30s check)');
        setupInterval();
      }, 30000); // Every 30 seconds
    } else {
      console.log('[useSmartRefreshRate] Skipping evaluation interval (disabled)');
    }

    return () => {
      if (intervalRef.current) {
        console.log('[useSmartRefreshRate] Cleanup: clearing main interval');
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (evaluationInterval) {
        console.log('[useSmartRefreshRate] Cleanup: clearing evaluation interval');
        clearInterval(evaluationInterval);
      }
    };
  }, [setupInterval, disabled]);

  // Manual controls
  const pause = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const resume = useCallback(() => {
    if (!disabled) {
      setupInterval();
    }
  }, [setupInterval, disabled]);

  const forceRefresh = useCallback(() => {
    trackActivity();
    performRefresh();
  }, [trackActivity, performRefresh]);

  const updateConfig = useCallback((newConfig: Partial<RefreshRateConfig>) => {
    finalConfig.current = {
      ...finalConfig.current,
      ...newConfig,
    };
    setupInterval();
  }, [setupInterval]);

  const showPerformanceWarning = useCallback(() => {
    if (refreshMode === 'lowPerformance') {
      toast({
        title: "Performance Mode Active",
        description: "Refresh rate reduced due to high system load",
        variant: "warning",
      });
    }
  }, [refreshMode, toast]);

  // Show performance warnings
  useEffect(() => {
    if (refreshMode === 'lowPerformance') {
      showPerformanceWarning();
    }
  }, [refreshMode, showPerformanceWarning]);

  return {
    // State
    isRefreshing,
    currentInterval,
    refreshMode,
    performanceMetrics,
    
    // Controls
    pause,
    resume,
    forceRefresh,
    updateConfig,
    
    // Info
    isActive: intervalRef.current !== null,
    nextRefreshIn: intervalRef.current ? currentInterval - (Date.now() % currentInterval) : 0,
  };
}

// Export types for external use
export type { RefreshRateConfig, PerformanceMetrics, SmartRefreshOptions };