/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef, GridReadyEvent, ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { 
  Download, 
  Filter, 
  Search, 
  RefreshCw, 
  Settings,
  BarChart3,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { authFetch } from '@/utils/auth-fetch';
import { useTelemetryWebSocket } from '@/hooks/useTelemetryWebSocket';

// Community-only AG Grid: the proprietary ag-grid-enterprise package was
// removed (incompatible with this Apache-2.0 distribution). Enterprise-only
// features (pivot/row-group panels, charts, range selection, set filter,
// Excel export, status bar, side bar) were dropped or replaced with their
// community equivalents.
ModuleRegistry.registerModules([AllCommunityModule]);

interface TelemetryData {
  id: string;
  deviceId: string;
  deviceName: string;
  timestamp: string;
  temperature?: number;
  humidity?: number;
  pressure?: number;
  voltage?: number;
  current?: number;
  status: string;
  batteryLevel?: number;
  signalStrength?: number;
  location?: string;
}

interface ExcelStyleDataGridProps {
  devices: any[];
  refreshInterval?: number;
}

export const ExcelStyleDataGrid: React.FC<ExcelStyleDataGridProps> = ({
  devices,
  refreshInterval = 30000
}) => {
  const [rowData, setRowData] = useState<TelemetryData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [selectedRows, setSelectedRows] = useState(0);
  const [gridApi, setGridApi] = useState<any>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null); // legacy polling (disabled)

  // Column definitions with advanced features
  const columnDefs: ColDef[] = useMemo(() => [
    {
      headerName: 'Device',
      field: 'deviceName',
      pinned: 'left',
      filter: 'agTextColumnFilter',
      sortable: true,
      resizable: true,
      width: 150,
      cellRenderer: (params: any) => {
        const isOnline = params.data.status === 'online';
        return `
          <div class="flex items-center gap-2">
            <div class="w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}"></div>
            <span class="font-medium">${params.value}</span>
          </div>
        `;
      }
    },
    {
      headerName: 'Timestamp',
      field: 'timestamp',
      filter: 'agDateColumnFilter',
      sortable: true,
      resizable: true,
      width: 180,
      valueFormatter: (params: any) => {
        return new Date(params.value).toLocaleString();
      }
    },
    {
      headerName: 'Temperature',
      field: 'temperature',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 120,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        const color = value > 30 ? 'text-red-600' : value < 15 ? 'text-blue-600' : 'text-green-600';
        return `<span class="${color} font-mono">${value.toFixed(1)}°C</span>`;
      }
    },
    {
      headerName: 'Humidity',
      field: 'humidity',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 120,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        return `<span class="font-mono text-blue-600">${value.toFixed(1)}%</span>`;
      }
    },
    {
      headerName: 'Pressure',
      field: 'pressure',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 120,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        return `<span class="font-mono text-purple-600">${value.toFixed(0)} hPa</span>`;
      }
    },
    {
      headerName: 'Voltage',
      field: 'voltage',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 120,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        const color = value < 3.0 ? 'text-red-600' : 'text-green-600';
        return `<span class="${color} font-mono">${value.toFixed(2)}V</span>`;
      }
    },
    {
      headerName: 'Battery',
      field: 'batteryLevel',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 120,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        const color = value < 20 ? 'text-red-600' : value < 50 ? 'text-yellow-600' : 'text-green-600';
        return `
          <div class="flex items-center gap-2">
            <div class="w-12 h-2 bg-gray-200 rounded-full">
              <div class="${color.replace('text-', 'bg-')} h-full rounded-full" style="width: ${value}%"></div>
            </div>
            <span class="${color} font-mono text-xs">${value.toFixed(0)}%</span>
          </div>
        `;
      }
    },
    {
      headerName: 'Signal',
      field: 'signalStrength',
      filter: 'agNumberColumnFilter',
      sortable: true,
      resizable: true,
      width: 100,
      cellRenderer: (params: any) => {
        if (params.value === null || params.value === undefined) return '-';
        const value = parseFloat(params.value);
        const bars = Math.ceil(value / 25);
        const barsHtml = Array.from({ length: 4 }, (_, i) => 
          `<div class="w-1 h-${i + 1} ${i < bars ? 'bg-green-500' : 'bg-gray-300'} rounded"></div>`
        ).join('');
        return `
          <div class="flex items-end gap-0.5 justify-center">
            ${barsHtml}
          </div>
        `;
      }
    },
    {
      headerName: 'Status',
      field: 'status',
      filter: 'agTextColumnFilter',
      sortable: true,
      resizable: true,
      width: 100,
      cellRenderer: (params: any) => {
        const status = params.value;
        const variants: Record<string, string> = {
          online: 'bg-green-100 text-green-800',
          offline: 'bg-red-100 text-red-800',
          warning: 'bg-yellow-100 text-yellow-800',
          error: 'bg-red-100 text-red-800'
        };
        const variant = variants[status] || 'bg-gray-100 text-gray-800';
        return `<span class="px-2 py-1 rounded-full text-xs font-medium ${variant}">${status}</span>`;
      }
    },
    {
      headerName: 'Location',
      field: 'location',
      filter: 'agTextColumnFilter',
      sortable: true,
      resizable: true,
      width: 150
    }
  ], []);

  // Grid options (community features only)
  const defaultColDef = useMemo(() => ({
    sortable: true,
    filter: true,
    resizable: true,
    floatingFilter: true
  }), []);

  // Fetch telemetry data (one-shot seed)
  const fetchTelemetryData = useCallback(async () => {
    try {
      setLoading(true);
      const telemetryPromises = devices.map(async (device) => {
        try {
          const response = await authFetch(`/api/v1/devices/${device.id}/telemetry?limit=100`);
          if (response.ok) {
            const data = await response.json();
            return data.telemetry?.map((t: any) => ({
              id: `${device.id}-${t.timestamp}`,
              deviceId: device.id,
              deviceName: device.name,
              timestamp: t.timestamp,
              temperature: t.temperature,
              humidity: t.humidity,
              pressure: t.pressure,
              voltage: t.voltage,
              current: t.current,
              status: device.status,
              batteryLevel: Math.random() * 100, // Mock data
              signalStrength: Math.random() * 100, // Mock data
              location: device.location || 'Unknown'
            })) || [];
          }
        } catch (error) {
          console.error(`Failed to fetch telemetry for device ${device.id}:`, error);
        }
        return [];
      });

      const results = await Promise.all(telemetryPromises);
      const allTelemetry = results.flat().sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );

      setRowData(allTelemetry);
    } catch (error) {
      console.error('Failed to fetch telemetry data:', error);
    } finally {
      setLoading(false);
    }
  }, [devices]);

  // WebSocket: incremental live updates (WS-only)
  const { subscribeToDevice, unsubscribeFromDevice } = useTelemetryWebSocket({
    onDeviceTelemetry: (deviceId: string, data: any) => {
      // Map incoming message to grid row and append
      const device = devices.find(d => (d.id || d.device_id) === deviceId);
      if (!device || !data || typeof data !== 'object') return;
      const ts = new Date().toISOString();
      const row: TelemetryData = {
        id: `${deviceId}-${ts}`,
        deviceId: deviceId,
        deviceName: device.name || deviceId,
        timestamp: ts,
        temperature: data.temperature,
        humidity: data.humidity,
        pressure: data.pressure,
        voltage: data.voltage,
        current: data.current,
        status: device.status || 'online',
        batteryLevel: typeof data.battery === 'number' ? data.battery : undefined,
        signalStrength: typeof data.rssi === 'number' ? data.rssi : undefined,
        location: device.location || 'Unknown'
      };
      setRowData(prev => {
        const next = [row, ...prev];
        // Cap for performance (e.g., keep last 2000 records)
        return next.slice(0, 2000);
      });
    },
    reconnect: true,
    reconnectInterval: 3000,
    reconnectAttempts: 10,
  });

  useEffect(() => {
    // Disable any legacy polling timer
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null; }

    if (devices.length > 0) {
      // Seed initial data for better UX
      void fetchTelemetryData();
      // Subscribe all devices shown in the grid
      devices.forEach(d => subscribeToDevice(d.id || d.device_id));
    }
    return () => {
      devices.forEach(d => unsubscribeFromDevice(d.id || d.device_id));
    };
  }, [devices, fetchTelemetryData, subscribeToDevice, unsubscribeFromDevice]);

  const onGridReady = (params: GridReadyEvent) => {
    setGridApi(params.api);
  };

  const onQuickFilterChanged = () => {
    if (gridApi) {
      // v31+ API: setQuickFilter was removed in favour of the grid option
      gridApi.setGridOption('quickFilterText', searchText);
    }
  };

  const exportToCsv = () => {
    if (gridApi) {
      gridApi.exportDataAsCsv({
        fileName: `tesa-iot-telemetry-${new Date().toISOString().split('T')[0]}.csv`
      });
    }
  };

  const onSelectionChanged = () => {
    if (gridApi) {
      const selectedNodes = gridApi.getSelectedNodes();
      setSelectedRows(selectedNodes.length);
    }
  };

  const getStatistics = () => {
    if (rowData.length === 0) return null;

    const onlineDevices = rowData.filter(row => row.status === 'online').length;
    const avgTemp = rowData.reduce((sum, row) => sum + (row.temperature || 0), 0) / rowData.length;
    const avgHumidity = rowData.reduce((sum, row) => sum + (row.humidity || 0), 0) / rowData.length;
    const lowBattery = rowData.filter(row => (row.batteryLevel || 100) < 20).length;

    return {
      totalRecords: rowData.length,
      onlineDevices,
      avgTemp: avgTemp.toFixed(1),
      avgHumidity: avgHumidity.toFixed(1),
      lowBattery
    };
  };

  const stats = getStatistics();

  useEffect(() => {
    onQuickFilterChanged();
  }, [searchText]);

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Advanced Data Grid</h2>
          <p className="text-sm text-muted-foreground">
            Advanced IoT telemetry data analysis with filtering, sorting, and CSV export
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchTelemetryData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="outline" size="sm" onClick={exportToCsv}>
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
        </div>
      </div>

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-3">
              <div className="text-2xl font-bold">{stats.totalRecords}</div>
              <div className="text-xs text-muted-foreground">Total Records</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <div className="text-2xl font-bold text-green-600">{stats.onlineDevices}</div>
              <div className="text-xs text-muted-foreground">Online Devices</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <div className="text-2xl font-bold text-blue-600">{stats.avgTemp}°C</div>
              <div className="text-xs text-muted-foreground">Avg Temperature</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <div className="text-2xl font-bold text-cyan-600">{stats.avgHumidity}%</div>
              <div className="text-xs text-muted-foreground">Avg Humidity</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3">
              <div className="text-2xl font-bold text-red-600">{stats.lowBattery}</div>
              <div className="text-xs text-muted-foreground">Low Battery</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search across all data..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>
        {selectedRows > 0 && (
          <Badge variant="secondary">
            {selectedRows} row{selectedRows > 1 ? 's' : ''} selected
          </Badge>
        )}
      </div>

      {/* Data Grid */}
      <Card>
        <CardContent className="p-0">
          <div className="h-[600px] w-full border rounded">
            <AgGridReact
              rowData={rowData}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              onGridReady={onGridReady}
              onSelectionChanged={onSelectionChanged}
              rowSelection="multiple"
              suppressMenuHide={true}
            />
          </div>
        </CardContent>
      </Card>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}
    </div>
  );
};
