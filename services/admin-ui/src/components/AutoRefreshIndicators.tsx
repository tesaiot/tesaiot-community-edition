/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { 
  RefreshCw, 
  Activity, 
  Clock, 
  Wifi, 
  WifiOff,
  AlertCircle,
  CheckCircle,
  Loader2
} from 'lucide-react';

interface RefreshCountdownProps {
  nextRefreshIn: number; // milliseconds until next refresh
  isActive: boolean;
  className?: string;
}

export function RefreshCountdown({ nextRefreshIn, isActive, className }: RefreshCountdownProps) {
  const [countdown, setCountdown] = useState(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    if (isActive && nextRefreshIn > 0) {
      setCountdown(Math.ceil(nextRefreshIn / 1000));
      
      intervalRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) return Math.ceil(nextRefreshIn / 1000);
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [nextRefreshIn, isActive]);

  if (!isActive) return null;

  return (
    <div className={cn("flex items-center gap-2 text-sm", className)}>
      <Clock className="h-3 w-3 text-muted-foreground" />
      <span className="font-mono text-xs">
        Next refresh in <span className="font-bold">{countdown}s</span>
      </span>
    </div>
  );
}

interface LiveIndicatorProps {
  isActive: boolean;
  isLoading?: boolean;
  hasError?: boolean;
  className?: string;
}

export function LiveIndicator({ isActive, isLoading, hasError, className }: LiveIndicatorProps) {
  if (hasError) {
    return (
      <Badge variant="destructive" className={cn("flex items-center gap-1", className)}>
        <WifiOff className="h-3 w-3" />
        ERROR
      </Badge>
    );
  }

  if (!isActive) {
    return (
      <Badge variant="secondary" className={cn("flex items-center gap-1", className)}>
        <WifiOff className="h-3 w-3" />
        PAUSED
      </Badge>
    );
  }

  return (
    <Badge 
      variant="default" 
      className={cn(
        "flex items-center gap-1 bg-green-500 text-white hover:bg-green-600",
        className
      )}
    >
      <div className="relative">
        <Wifi className="h-3 w-3" />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="h-2 w-2 bg-white rounded-full animate-ping" />
          </div>
        )}
      </div>
      <span className="font-bold">LIVE</span>
      <div className="ml-1 h-2 w-2 bg-white rounded-full animate-pulse" />
    </Badge>
  );
}

interface DataFetchSpinnerProps {
  isLoading: boolean;
  className?: string;
}

export function DataFetchSpinner({ isLoading, className }: DataFetchSpinnerProps) {
  if (!isLoading) return null;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Loader2 className="h-4 w-4 animate-spin text-primary" />
      <span className="text-sm text-muted-foreground">Fetching data...</span>
    </div>
  );
}

interface LastUpdateTimestampProps {
  timestamp: Date | null;
  showSeconds?: boolean;
  className?: string;
}

export function LastUpdateTimestamp({ timestamp, showSeconds = true, className }: LastUpdateTimestampProps) {
  const [displayTime, setDisplayTime] = useState('');

  useEffect(() => {
    const updateTime = () => {
      if (timestamp) {
        const timeString = showSeconds 
          ? timestamp.toLocaleTimeString()
          : timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setDisplayTime(timeString);
      }
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, [timestamp, showSeconds]);

  if (!timestamp) return null;

  return (
    <div className={cn("flex items-center gap-2 text-sm text-muted-foreground", className)}>
      <CheckCircle className="h-3 w-3" />
      <span>Last update: <span className="font-mono">{displayTime}</span></span>
    </div>
  );
}

interface DataUpdateFlashProps {
  trigger: any; // Will flash when this value changes
  className?: string;
}

export function DataUpdateFlash({ trigger, className }: DataUpdateFlashProps) {
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (trigger) {
      setFlash(true);
      const timeout = setTimeout(() => setFlash(false), 500);
      return () => clearTimeout(timeout);
    }
  }, [trigger]);

  return (
    <div 
      className={cn(
        "absolute inset-0 pointer-events-none transition-opacity duration-500",
        flash ? "opacity-100" : "opacity-0",
        className
      )}
    >
      <div className="absolute inset-0 bg-green-500 opacity-20 animate-pulse" />
    </div>
  );
}

interface AutoRefreshStatusBarProps {
  isActive: boolean;
  isLoading: boolean;
  lastUpdate: Date | null;
  nextRefreshIn: number;
  refreshInterval: number;
  onToggle: () => void;
  hasError?: boolean;
  errorMessage?: string;
  dataCount?: number;
  className?: string;
}

export function AutoRefreshStatusBar({
  isActive,
  isLoading,
  lastUpdate,
  nextRefreshIn,
  refreshInterval,
  onToggle,
  hasError,
  errorMessage,
  dataCount,
  className
}: AutoRefreshStatusBarProps) {
  return (
    <div className={cn(
      "flex items-center justify-between p-3 bg-muted/50 rounded-lg border",
      hasError && "border-red-500/50 bg-red-50/50 dark:bg-red-900/20",
      className
    )}>
      <div className="flex items-center gap-4">
        {/* Live Indicator */}
        <LiveIndicator isActive={isActive} isLoading={isLoading} hasError={hasError} />
        
        {/* Refresh Info */}
        <div className="flex items-center gap-4 text-sm">
          {isActive && !hasError && (
            <>
              <RefreshCountdown nextRefreshIn={nextRefreshIn} isActive={isActive} />
              <span className="text-muted-foreground">
                Interval: <span className="font-mono font-bold">{(refreshInterval / 1000).toFixed(0)}s</span>
              </span>
            </>
          )}
          
          {/* Data Count */}
          {dataCount !== undefined && (
            <span className="text-muted-foreground">
              Records: <span className="font-bold">{dataCount}</span>
            </span>
          )}
        </div>
        
        {/* Loading Spinner */}
        <DataFetchSpinner isLoading={isLoading} />
      </div>
      
      <div className="flex items-center gap-4">
        {/* Error Message */}
        {hasError && errorMessage && (
          <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400">
            <AlertCircle className="h-4 w-4" />
            <span>{errorMessage}</span>
          </div>
        )}
        
        {/* Last Update */}
        <LastUpdateTimestamp timestamp={lastUpdate} />
        
        {/* Toggle Button */}
        <button
          onClick={onToggle}
          className={cn(
            "flex items-center gap-2 px-3 py-1 rounded-md text-sm font-medium transition-colors",
            isActive 
              ? "bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
              : "bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
          )}
        >
          {isActive ? (
            <>
              <Activity className="h-3 w-3" />
              Pause
            </>
          ) : (
            <>
              <RefreshCw className="h-3 w-3" />
              Resume
            </>
          )}
        </button>
      </div>
    </div>
  );
}

interface RefreshProgressBarProps {
  nextRefreshIn: number;
  refreshInterval: number;
  isActive: boolean;
  className?: string;
}

export function RefreshProgressBar({ 
  nextRefreshIn, 
  refreshInterval, 
  isActive, 
  className 
}: RefreshProgressBarProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (isActive && refreshInterval > 0) {
      const remaining = Math.max(0, nextRefreshIn);
      const progressPercent = ((refreshInterval - remaining) / refreshInterval) * 100;
      setProgress(progressPercent);
    } else {
      setProgress(0);
    }
  }, [nextRefreshIn, refreshInterval, isActive]);

  if (!isActive) return null;

  return (
    <div className={cn("w-full", className)}>
      <div className="h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div 
          className="h-full bg-primary transition-all duration-1000 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

// Console logging helper for debugging
export function logRefreshEvent(event: string, details?: any) {
  const timestamp = new Date().toISOString();
  console.log(`[Auto-Refresh] ${timestamp} - ${event}`, details || '');
}