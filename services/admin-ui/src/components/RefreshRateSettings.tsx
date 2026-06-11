/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Zap,
  Clock,
  Battery,
  Gauge,
  AlertCircle,
  Settings,
  Save,
  RotateCcw,
  Activity,
  Cpu,
  HardDrive,
  Wifi,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RefreshRateConfig, PerformanceMetrics } from '@/hooks/useSmartRefreshRate';

interface RefreshRateSettingsProps {
  currentConfig: RefreshRateConfig;
  performanceMetrics?: PerformanceMetrics;
  refreshMode?: 'active' | 'background' | 'idle' | 'lowPerformance';
  onConfigChange: (config: Partial<RefreshRateConfig>) => void;
  onSave?: () => void;
  onReset?: () => void;
  className?: string;
}

const PRESET_DESCRIPTIONS = {
  realtime: {
    name: 'Real-time',
    description: 'Fastest updates for critical monitoring',
    icon: <Zap className="h-4 w-4" />,
    color: 'text-red-500',
  },
  normal: {
    name: 'Normal',
    description: 'Balanced performance and updates',
    icon: <Clock className="h-4 w-4" />,
    color: 'text-blue-500',
  },
  conservative: {
    name: 'Conservative',
    description: 'Reduced updates to save resources',
    icon: <Battery className="h-4 w-4" />,
    color: 'text-green-500',
  },
  manual: {
    name: 'Manual',
    description: 'Custom refresh intervals',
    icon: <Settings className="h-4 w-4" />,
    color: 'text-purple-500',
  },
};

export function RefreshRateSettings({
  currentConfig,
  performanceMetrics,
  refreshMode = 'active',
  onConfigChange,
  onSave,
  onReset,
  className,
}: RefreshRateSettingsProps) {
  const [localConfig, setLocalConfig] = useState<Partial<RefreshRateConfig>>(currentConfig);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    setLocalConfig(currentConfig);
  }, [currentConfig]);

  const handlePresetChange = (preset: string) => {
    const newConfig = {
      ...localConfig,
      userPreference: preset as RefreshRateConfig['userPreference'],
    };
    setLocalConfig(newConfig);
    setHasChanges(true);
    onConfigChange(newConfig);
  };

  const handleCustomIntervalChange = (value: number[]) => {
    const newConfig = {
      ...localConfig,
      customInterval: value[0] * 1000, // Convert to milliseconds
    };
    setLocalConfig(newConfig);
    setHasChanges(true);
    onConfigChange(newConfig);
  };

  const handleThresholdChange = (key: keyof RefreshRateConfig, value: number[]) => {
    const newConfig = {
      ...localConfig,
      [key]: value[0],
    };
    setLocalConfig(newConfig);
    setHasChanges(true);
    onConfigChange(newConfig);
  };

  const handleSave = () => {
    setHasChanges(false);
    onSave?.();
  };

  const handleReset = () => {
    setHasChanges(false);
    onReset?.();
  };

  const formatInterval = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`;
    if (ms < 3600000) return `${(ms / 60000).toFixed(0)}m`;
    return `${(ms / 3600000).toFixed(1)}h`;
  };

  const getPerformanceStatus = () => {
    if (!performanceMetrics) return 'unknown';
    
    const { cpuUsage, memoryUsage, errorRate } = performanceMetrics;
    
    if (cpuUsage > 80 || memoryUsage > 85 || errorRate > 0.1) {
      return 'critical';
    }
    if (cpuUsage > 60 || memoryUsage > 70 || errorRate > 0.05) {
      return 'warning';
    }
    return 'healthy';
  };

  const performanceStatus = getPerformanceStatus();

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gauge className="h-5 w-5" />
          Refresh Rate Configuration
        </CardTitle>
        <CardDescription>
          Configure how often the dashboard updates telemetry data
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Status */}
        <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
          <div className="flex items-center gap-3">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Current Mode:</span>
            <Badge variant={refreshMode === 'lowPerformance' ? 'destructive' : 'secondary'}>
              {refreshMode.replace(/([A-Z])/g, ' $1').trim()}
            </Badge>
          </div>
          {hasChanges && (
            <Badge variant="outline" className="text-orange-600">
              Unsaved Changes
            </Badge>
          )}
        </div>

        {/* Performance Metrics */}
        {performanceMetrics && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium">System Performance</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground">CPU Usage</div>
                  <div className="font-semibold">{performanceMetrics.cpuUsage.toFixed(0)}%</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                <HardDrive className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground">Memory</div>
                  <div className="font-semibold">{performanceMetrics.memoryUsage.toFixed(0)}%</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                <Wifi className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground">Response Time</div>
                  <div className="font-semibold">{performanceMetrics.averageResponseTime.toFixed(0)}ms</div>
                </div>
              </div>
              <div className="flex items-center gap-2 p-2 bg-muted rounded">
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
                <div className="flex-1">
                  <div className="text-xs text-muted-foreground">Error Rate</div>
                  <div className="font-semibold">{(performanceMetrics.errorRate * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>
            
            {performanceStatus === 'critical' && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  High system load detected. Refresh rate automatically reduced.
                </AlertDescription>
              </Alert>
            )}
            {performanceStatus === 'warning' && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Moderate system load. Consider using conservative settings.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <Separator />

        {/* Refresh Presets */}
        <div className="space-y-3">
          <Label>Refresh Rate Preset</Label>
          <RadioGroup
            value={localConfig.userPreference || 'normal'}
            onValueChange={handlePresetChange}
          >
            {Object.entries(PRESET_DESCRIPTIONS).map(([key, preset]) => (
              <div key={key} className="flex items-start space-x-3 p-3 rounded-lg hover:bg-muted/50">
                <RadioGroupItem value={key} id={key} className="mt-0.5" />
                <Label htmlFor={key} className="flex-1 cursor-pointer">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={cn("", preset.color)}>{preset.icon}</span>
                    <span className="font-medium">{preset.name}</span>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {preset.description}
                  </div>
                  {key !== 'manual' && (
                    <div className="text-xs text-muted-foreground mt-1">
                      Active: {formatInterval(localConfig[key]?.active || 30000)} | 
                      Background: {formatInterval(localConfig[key]?.background || 120000)}
                    </div>
                  )}
                </Label>
              </div>
            ))}
          </RadioGroup>
        </div>

        {/* Custom Interval (for manual mode) */}
        {localConfig.userPreference === 'manual' && (
          <div className="space-y-3">
            <Label>Custom Refresh Interval</Label>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  {formatInterval((localConfig.customInterval || 30000))}
                </span>
                <span className="text-sm text-muted-foreground">
                  Every {(localConfig.customInterval || 30000) / 1000} seconds
                </span>
              </div>
              <Slider
                value={[(localConfig.customInterval || 30000) / 1000]}
                onValueChange={handleCustomIntervalChange}
                min={5}
                max={300}
                step={5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>5s</span>
                <span>5m</span>
              </div>
            </div>
          </div>
        )}

        <Separator />

        {/* Advanced Settings */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium">Performance Thresholds</h3>
          
          {/* CPU Threshold */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">CPU Usage Threshold</Label>
              <span className="text-sm text-muted-foreground">
                {localConfig.cpuThreshold || 80}%
              </span>
            </div>
            <Slider
              value={[localConfig.cpuThreshold || 80]}
              onValueChange={(value) => handleThresholdChange('cpuThreshold', value)}
              min={50}
              max={100}
              step={5}
              className="w-full"
            />
          </div>

          {/* Memory Threshold */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Memory Usage Threshold</Label>
              <span className="text-sm text-muted-foreground">
                {localConfig.memoryThreshold || 85}%
              </span>
            </div>
            <Slider
              value={[localConfig.memoryThreshold || 85]}
              onValueChange={(value) => handleThresholdChange('memoryThreshold', value)}
              min={50}
              max={100}
              step={5}
              className="w-full"
            />
          </div>

          {/* Response Time Threshold */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Response Time Threshold</Label>
              <span className="text-sm text-muted-foreground">
                {(localConfig.responseTimeThreshold || 5000) / 1000}s
              </span>
            </div>
            <Slider
              value={[(localConfig.responseTimeThreshold || 5000) / 1000]}
              onValueChange={(value) => handleThresholdChange('responseTimeThreshold', [value[0] * 1000])}
              min={1}
              max={30}
              step={1}
              className="w-full"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-4">
          <Button
            onClick={handleSave}
            disabled={!hasChanges}
            className="flex-1"
          >
            <Save className="h-4 w-4 mr-2" />
            Save Settings
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={!hasChanges}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Reset
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}