/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { AlertCircle, Zap, Server, Info } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useLicenseContext } from '@/providers/license-provider';

interface FeatureFlag {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  requiresCommercial?: boolean;
  experimental?: boolean;
  category: 'performance' | 'features' | 'experimental';
}

export const FeatureFlags: React.FC = () => {
  const { isCommercial } = useLicenseContext();
  const [flags, setFlags] = useState<FeatureFlag[]>([
    {
      key: 'useRustWebSocket',
      name: 'Rust WebSocket Service',
      description: 'Enable high-performance Rust WebSocket service for real-time telemetry',
      enabled: import.meta.env.VITE_USE_RUST_WEBSOCKET === 'true',
      requiresCommercial: true,
      category: 'performance'
    },
    {
      key: 'enableSmartRefresh',
      name: 'Smart Refresh Rate',
      description: 'Dynamically adjust refresh rates based on user activity',
      enabled: true,
      requiresCommercial: false,
      category: 'performance'
    },
    {
      key: 'enableWebSocketCompression',
      name: 'WebSocket Compression',
      description: 'Enable compression for WebSocket messages to reduce bandwidth',
      enabled: false,
      requiresCommercial: false,
      category: 'performance'
    },
    {
      key: 'enableTelemetryCache',
      name: 'Telemetry Caching',
      description: 'Cache telemetry data for improved performance',
      enabled: true,
      requiresCommercial: false,
      category: 'performance'
    },
    {
      key: 'enableAdvancedAnalytics',
      name: 'Advanced Analytics',
      description: 'Enable advanced analytics features including predictive insights',
      enabled: false,
      requiresCommercial: true,
      category: 'features'
    },
    {
      key: 'enableBatchOperations',
      name: 'Batch Device Operations',
      description: 'Enable batch operations for device management',
      enabled: false,
      requiresCommercial: true,
      category: 'features'
    },
    {
      key: 'enableEdgeComputing',
      name: 'Edge Computing Preview',
      description: 'Preview edge computing capabilities (experimental)',
      enabled: false,
      requiresCommercial: true,
      experimental: true,
      category: 'experimental'
    }
  ]);

  const [rustWsPercentage, setRustWsPercentage] = useState(import.meta.env.VITE_USE_RUST_WEBSOCKET === 'true' ? 100 : 0);
  const [showRestartAlert, setShowRestartAlert] = useState(false);

  useEffect(() => {
    // Load feature flags from localStorage
    const savedFlags = flags.map(flag => ({
      ...flag,
      enabled: localStorage.getItem(flag.key) === 'true'
    }));
    setFlags(savedFlags);

    // Load Rust WS percentage
    const defaultPercentage = import.meta.env.VITE_USE_RUST_WEBSOCKET === 'true' ? 100 : 0;
    const savedPercentage = parseInt(localStorage.getItem('rustWsTrafficPercentage') || defaultPercentage.toString());
    setRustWsPercentage(savedPercentage);
  }, []);

  const toggleFlag = (key: string) => {
    const updatedFlags = flags.map(flag => {
      if (flag.key === key) {
        const newValue = !flag.enabled;
        localStorage.setItem(key, newValue.toString());
        
        // Show restart alert for certain flags
        if (key === 'useRustWebSocket') {
          setShowRestartAlert(true);
        }
        
        return { ...flag, enabled: newValue };
      }
      return flag;
    });
    setFlags(updatedFlags);
  };

  const updateRustWsPercentage = (value: number[]) => {
    const percentage = value[0];
    setRustWsPercentage(percentage);
    localStorage.setItem('rustWsTrafficPercentage', percentage.toString());
  };

  const applyChanges = () => {
    // In a real implementation, this would update the server configuration
    window.location.reload();
  };

  const getCategoryFlags = (category: string) => {
    return flags.filter(flag => flag.category === category);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Feature Flags Configuration</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="performance" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="performance">Performance</TabsTrigger>
            <TabsTrigger value="features">Features</TabsTrigger>
            <TabsTrigger value="experimental">Experimental</TabsTrigger>
          </TabsList>

          <TabsContent value="performance" className="space-y-4">
            {getCategoryFlags('performance').map(flag => (
              <div key={flag.key} className="flex items-start space-x-3 p-4 border rounded-lg">
                <Switch
                  id={flag.key}
                  checked={flag.enabled}
                  onCheckedChange={() => toggleFlag(flag.key)}
                  disabled={flag.requiresCommercial && !isCommercial()}
                />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Label htmlFor={flag.key} className="text-base font-medium">
                      {flag.name}
                    </Label>
                    {flag.requiresCommercial && (
                      <Badge variant="secondary" className="text-xs">
                        Commercial
                      </Badge>
                    )}
                    {flag.key === 'useRustWebSocket' && flag.enabled && (
                      <Badge variant="default" className="text-xs">
                        <Zap className="h-3 w-3 mr-1" />
                        Active
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{flag.description}</p>
                  
                  {/* Special configuration for Rust WebSocket */}
                  {flag.key === 'useRustWebSocket' && flag.enabled && (
                    <div className="mt-4 space-y-3">
                      <div>
                        <Label className="text-sm">Traffic Distribution: {rustWsPercentage}%</Label>
                        <Slider
                          value={[rustWsPercentage]}
                          onValueChange={updateRustWsPercentage}
                          max={100}
                          step={10}
                          className="mt-2"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Percentage of WebSocket traffic routed to Rust service
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="features" className="space-y-4">
            {getCategoryFlags('features').map(flag => (
              <div key={flag.key} className="flex items-start space-x-3 p-4 border rounded-lg">
                <Switch
                  id={flag.key}
                  checked={flag.enabled}
                  onCheckedChange={() => toggleFlag(flag.key)}
                  disabled={flag.requiresCommercial && !isCommercial()}
                />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Label htmlFor={flag.key} className="text-base font-medium">
                      {flag.name}
                    </Label>
                    {flag.requiresCommercial && (
                      <Badge variant="secondary" className="text-xs">
                        Commercial
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{flag.description}</p>
                </div>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="experimental" className="space-y-4">
            <Alert className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Experimental features are under active development and may change or be removed in future versions.
              </AlertDescription>
            </Alert>
            
            {getCategoryFlags('experimental').map(flag => (
              <div key={flag.key} className="flex items-start space-x-3 p-4 border rounded-lg">
                <Switch
                  id={flag.key}
                  checked={flag.enabled}
                  onCheckedChange={() => toggleFlag(flag.key)}
                  disabled={flag.requiresCommercial && !isCommercial()}
                />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <Label htmlFor={flag.key} className="text-base font-medium">
                      {flag.name}
                    </Label>
                    <Badge variant="outline" className="text-xs">
                      Experimental
                    </Badge>
                    {flag.requiresCommercial && (
                      <Badge variant="secondary" className="text-xs">
                        Commercial
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{flag.description}</p>
                </div>
              </div>
            ))}
          </TabsContent>
        </Tabs>

        {showRestartAlert && (
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertDescription>
              Some changes require a page reload to take effect.
              <Button
                variant="link"
                className="ml-2 h-auto p-0"
                onClick={applyChanges}
              >
                Reload now
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {!isCommercial() && (
          <Alert className="mt-4 border-yellow-600">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            <AlertDescription className="text-yellow-600">
              Some features require a Commercial license. Contact sales@tesa.io for more information.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};