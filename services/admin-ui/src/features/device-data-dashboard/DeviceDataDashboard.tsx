/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  BarChart3, 
  TrendingUp, 
  Activity, 
  Zap, 
  Plus, 
  Settings, 
  Grid3X3,
  LineChart,
  Table,
  Gauge,
  Brain,
  AlertTriangle,
  Layers
} from 'lucide-react';
import { authFetch } from '@/utils/auth-fetch';
import { useAuth } from '@/hooks/useAuth';

// Import new dashboard components
import { SimpleDashboardBuilder } from './components/SimpleDashboardBuilder';
import { ExcelStyleDataGrid } from './components/ExcelStyleDataGrid';

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
}

interface WidgetTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  category: 'kpi' | 'chart' | 'status' | 'grid' | 'analysis';
  preview: string;
}

export const DeviceDataDashboard: React.FC = () => {
  const { currentUser } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState('overview');
  const [showGridStackBuilder, setShowGridStackBuilder] = useState(false);
  const [showDataGrid, setShowDataGrid] = useState(false);

  // Widget templates for the new dashboard
  const widgetTemplates: WidgetTemplate[] = [
    {
      id: 'kpi-card',
      name: 'KPI Card',
      description: 'Real-time metrics with statistical context',
      icon: Gauge,
      category: 'kpi',
      preview: 'Display key performance indicators with trend analysis'
    },
    {
      id: 'time-series-chart',
      name: 'Time Series Chart', 
      description: 'Interactive charts with forecasting',
      icon: LineChart,
      category: 'chart',
      preview: 'Advanced time-series visualization with predictions'
    },
    {
      id: 'anomaly-detector',
      name: 'Anomaly Detector',
      description: 'Real-time anomaly detection and alerts',
      icon: Brain,
      category: 'analysis',
      preview: 'AI-powered anomaly detection with explanations'
    },
    {
      id: 'status-matrix',
      name: 'Device Status Matrix',
      description: 'Fleet health visualization',
      icon: Grid3X3,
      category: 'status',
      preview: 'Visual overview of device fleet health status'
    },
    {
      id: 'data-grid',
      name: 'Data Grid',
      description: 'Advanced data table with analytics',
      icon: Table,
      category: 'grid',
      preview: 'Spreadsheet-like data analysis capabilities'
    },
    {
      id: 'correlation-heatmap',
      name: 'Correlation Analysis',
      description: 'Sensor correlation heatmap',
      icon: BarChart3,
      category: 'analysis', 
      preview: 'Statistical correlation analysis between sensors'
    }
  ];

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      // Build URL with organization filter for non-admin users
      let url = '/api/v1/devices';
      
      // Filter devices by organization for non-super admin users
      if (currentUser && currentUser.role !== 'super_admin' && currentUser.organization_id) {
        url += `?organization=${currentUser.organization_id}`;
        console.log('DeviceDataDashboard: Filtering devices for organization:', currentUser.organization_id, 'Role:', currentUser.role);
      }
      
      console.log('DeviceDataDashboard: Fetching devices from', url);
      const response = await authFetch(url);
      if (response.ok) {
        const data = await response.json();
        console.log('DeviceDataDashboard: API response data:', data);
        // API returns array directly, not wrapped in 'devices' property like DeviceManagementWithCerts
        const devicesArray = Array.isArray(data) ? data : (data.devices || []);
        console.log('DeviceDataDashboard: Setting devices array:', devicesArray);
        console.log('DeviceDataDashboard: Number of devices:', devicesArray.length);
        setDevices(devicesArray);
      } else {
        console.error('DeviceDataDashboard: API response not ok:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('DeviceDataDashboard: Failed to fetch devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const onlineDevices = devices.filter(d => d.status === 'online');
  const totalDevices = devices.length;
  const totalMessages = devices.reduce((sum, d) => sum + (d.telemetry?.totalMessages || 0), 0);
  const avgMessagesPerMin = Math.round(
    devices.reduce((sum, d) => sum + (d.telemetry?.messagesPerMinute || 0), 0) / Math.max(onlineDevices.length, 1)
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (showGridStackBuilder) {
    console.log('DeviceDataDashboard: Rendering SimpleDashboardBuilder with devices:', devices);
    console.log('DeviceDataDashboard: Device count being passed:', devices.length);
    return (
      <SimpleDashboardBuilder 
        devices={devices}
        onClose={() => setShowGridStackBuilder(false)}
        onSave={(layout) => {
          console.log('Dashboard layout saved:', layout);
          // TODO: Persist layout to backend
        }}
      />
    );
  }

  if (showDataGrid) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Data Grid Analysis</h1>
          <Button variant="outline" onClick={() => setShowDataGrid(false)}>
            Back to Dashboard
          </Button>
        </div>
        <ExcelStyleDataGrid devices={devices} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Device Data Dashboard</h1>
          <p className="text-muted-foreground">
            Advanced IoT data visualization with statistical algorithms & flexible layouts
          </p>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Online Devices</p>
                <p className="text-2xl font-bold text-green-600">{onlineDevices.length}</p>
              </div>
              <Activity className="h-8 w-8 text-green-600" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              of {totalDevices} total devices
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Data Rate</p>
                <p className="text-2xl font-bold">{avgMessagesPerMin}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-600" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              messages per minute
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Messages</p>
                <p className="text-2xl font-bold">{totalMessages.toLocaleString()}</p>
              </div>
              <Zap className="h-8 w-8 text-yellow-600" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              lifetime processed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Dashboard Status</p>
                <p className="text-2xl font-bold text-blue-600">Ready</p>
              </div>
              <Grid3X3 className="h-8 w-8 text-blue-600" />
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              for advanced analytics
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Dashboard Tabs */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="widgets">Widget Gallery</TabsTrigger>
          <TabsTrigger value="builder">Dashboard Builder</TabsTrigger>
          <TabsTrigger value="analytics">AI Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {/* Feature Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Layers className="h-5 w-5" />
                  Flexible Layout System
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Drag-and-drop widgets with GridStack.js. Create custom layouts for different use cases.
                </p>
                <ul className="text-sm space-y-1">
                  <li>• Responsive grid system</li>
                  <li>• Persistent dashboard configurations</li>
                  <li>• Widget catalog with templates</li>
                  <li>• Multi-device optimization</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Brain className="h-5 w-5" />
                  Statistical Algorithms
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Advanced AI-powered analytics with real-time processing capabilities.
                </p>
                <ul className="text-sm space-y-1">
                  <li>• Anomaly detection (RF, Autoencoder)</li>
                  <li>• Time series forecasting (ARIMA, LSTM)</li>
                  <li>• Correlation analysis</li>
                  <li>• Pattern recognition</li>
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Data Presentation Styles
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  Multiple visualization options for different data types and analysis needs.
                </p>
                <ul className="text-sm space-y-1">
                  <li>• KPI cards with statistical context</li>
                  <li>• Interactive time-series charts</li>
                  <li>• Advanced data grids</li>
                  <li>• Status matrices and heatmaps</li>
                </ul>
              </CardContent>
            </Card>
          </div>

          {/* Current Telemetry Preview */}
          {onlineDevices.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Current Device Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {onlineDevices.slice(0, 4).map(device => (
                    <div key={device.id} className="text-center p-3 bg-muted rounded-lg">
                      <div className="flex items-center justify-center gap-2 mb-2">
                        <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                        <span className="font-medium text-sm">{device.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{device.type}</p>
                      {device.telemetry && (
                        <p className="text-xs mt-1">
                          {device.telemetry.messagesPerMinute} msg/min
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="widgets" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Widget Gallery</h3>
            <p className="text-sm text-muted-foreground">
              Choose from pre-built widgets or create custom ones
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {widgetTemplates.map(widget => (
              <Card key={widget.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <widget.icon className="h-4 w-4" />
                    {widget.name}
                    <Badge variant="outline" className="ml-auto">
                      {widget.category.toUpperCase()}
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-2">
                    {widget.description}
                  </p>
                  <p className="text-xs bg-muted p-2 rounded">
                    {widget.preview}
                  </p>
                  <Button 
                    size="sm" 
                    className="w-full mt-3"
                    onClick={() => {
                      if (widget.id === 'data-grid') {
                        setShowDataGrid(true);
                      } else {
                        setShowGridStackBuilder(true);
                      }
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    {widget.id === 'data-grid' ? 'Open Data Grid' : 'Add to Builder'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="builder" className="space-y-4">
          <div className="text-center py-12">
            <Grid3X3 className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Dashboard Builder</h3>
            <p className="text-muted-foreground mb-4">
              Drag-and-drop dashboard builder with GridStack.js integration
            </p>
            <div className="space-y-2 text-sm text-muted-foreground max-w-md mx-auto">
              <p>✅ GridStack.js integration ready</p>
              <p>✅ Widget framework designed</p>
              <p>✅ Real-time data pipeline prepared</p>
              <p>🚧 UI implementation in progress</p>
            </div>
            <Button 
              className="mt-4"
              onClick={() => setShowGridStackBuilder(true)}
            >
              <Settings className="h-4 w-4 mr-2" />
              Launch Dashboard Builder
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="text-center py-12">
            <Brain className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">AI Analytics Engine</h3>
            <p className="text-muted-foreground mb-4">
              Advanced statistical algorithms for IoT data analysis
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto text-left">
              <div className="p-4 bg-muted rounded-lg">
                <h4 className="font-medium mb-2">Anomaly Detection</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• Isolation Forest</li>
                  <li>• Autoencoder Neural Networks</li>
                  <li>• Statistical outlier detection</li>
                  <li>• Real-time scoring</li>
                </ul>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <h4 className="font-medium mb-2">Time Series Forecasting</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• ARIMA models</li>
                  <li>• LSTM neural networks</li>
                  <li>• Prophet algorithm</li>
                  <li>• Confidence intervals</li>
                </ul>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <Button 
                onClick={() => setShowDataGrid(true)}
              >
                <Table className="h-4 w-4 mr-2" />
                Open Data Grid
              </Button>
              <Button variant="outline" disabled>
                <AlertTriangle className="h-4 w-4 mr-2" />
                Advanced Analytics (Coming Soon)
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Development Status */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <div className="bg-blue-100 p-2 rounded-full">
              <Settings className="h-4 w-4 text-blue-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-blue-900 mb-1">Development Status</h4>
              <p className="text-sm text-blue-700 mb-2">
                The advanced Device Data Dashboard is under active development. Core research and architecture completed.
              </p>
              <div className="text-xs text-blue-600 space-y-1">
                <p>✅ Research & Best Practices Analysis Complete</p>
                <p>✅ Technical Architecture Defined</p>
                <p>✅ GridStack.js Integration Implemented</p>
                <p>✅ Advanced Data Grid with AG-Grid Enterprise</p>
                <p>✅ Statistical Analysis Backend Service</p>
                <p>🚧 Advanced AI Analytics Integration</p>
              </div>
              <div className="mt-3">
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setShowGridStackBuilder(true)}
                    className="border-blue-300 text-blue-700 hover:bg-blue-100"
                  >
                    <Grid3X3 className="h-4 w-4 mr-2" />
                    Try Dashboard Builder
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => setShowDataGrid(true)}
                    className="border-blue-300 text-blue-700 hover:bg-blue-100"
                  >
                    <Table className="h-4 w-4 mr-2" />
                    Try Data Grid
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};