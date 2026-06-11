/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Plus, 
  Save, 
  Trash2, 
  Settings, 
  BarChart3, 
  Gauge, 
  Activity,
  Grid3X3,
  LineChart,
  Table
} from 'lucide-react';

// Import GridStack and its CSS
import 'gridstack/dist/gridstack.min.css';
import './gridstack-custom.css';
import { GridStack } from 'gridstack';

interface WidgetConfig {
  id: string;
  type: 'kpi' | 'chart' | 'status' | 'grid' | 'analysis';
  title: string;
  dataSource?: string;
  config?: Record<string, any>;
}

interface GridStackWidget {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  config: WidgetConfig;
}

interface GridStackDashboardProps {
  devices: any[];
  onSave?: (layout: GridStackWidget[]) => void;
  onClose?: () => void;
}

const widgetTemplates = [
  {
    type: 'kpi' as const,
    title: 'KPI Card',
    icon: Gauge,
    defaultSize: { w: 2, h: 2 },
    color: 'bg-blue-500'
  },
  {
    type: 'chart' as const,
    title: 'Time Series Chart',
    icon: LineChart,
    defaultSize: { w: 4, h: 3 },
    color: 'bg-green-500'
  },
  {
    type: 'status' as const,
    title: 'Device Status',
    icon: Activity,
    defaultSize: { w: 3, h: 2 },
    color: 'bg-yellow-500'
  },
  {
    type: 'grid' as const,
    title: 'Data Grid',
    icon: Table,
    defaultSize: { w: 6, h: 4 },
    color: 'bg-purple-500'
  },
  {
    type: 'analysis' as const,
    title: 'Analytics Widget',
    icon: BarChart3,
    defaultSize: { w: 4, h: 3 },
    color: 'bg-red-500'
  }
];

export const GridStackDashboard: React.FC<GridStackDashboardProps> = ({
  devices,
  onSave,
  onClose
}) => {
  const gridRef = useRef<HTMLDivElement>(null);
  const gridStackRef = useRef<GridStack | null>(null);
  const [widgets, setWidgets] = useState<GridStackWidget[]>([]);
  const [isEditing, setIsEditing] = useState(true);

  useEffect(() => {
    // Simplified implementation without GridStack for now
    // This will be a manual drag-drop implementation
    console.log('Dashboard builder initialized');
  }, []);

  const addWidget = (template: typeof widgetTemplates[0]) => {
    if (!gridStackRef.current) return;

    const widgetId = `widget-${Date.now()}`;
    const widgetConfig: WidgetConfig = {
      id: widgetId,
      type: template.type,
      title: template.title,
      dataSource: devices[0]?.id || 'all',
      config: {}
    };

    const widgetEl = document.createElement('div');
    widgetEl.className = 'grid-stack-item';
    widgetEl.setAttribute('data-widget-id', widgetId);
    widgetEl.setAttribute('data-widget-config', JSON.stringify(widgetConfig));

    const contentEl = document.createElement('div');
    contentEl.className = 'grid-stack-item-content bg-white border rounded-lg shadow-sm p-4';
    contentEl.innerHTML = `
      <div class="flex items-center justify-between mb-2">
        <h3 class="font-medium text-sm">${template.title}</h3>
        <div class="flex gap-1">
          <button class="text-gray-400 hover:text-gray-600 p-1" onclick="editWidget('${widgetId}')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
            </svg>
          </button>
          <button class="text-red-400 hover:text-red-600 p-1" onclick="removeWidget('${widgetId}')">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
          </button>
        </div>
      </div>
      <div class="text-xs text-gray-500 mb-2">Device: ${devices[0]?.name || 'All Devices'}</div>
      <div class="h-20 ${template.color} bg-opacity-10 border-2 border-dashed ${template.color.replace('bg-', 'border-')} border-opacity-30 rounded flex items-center justify-center">
        <div class="text-center">
          <div class="${template.color.replace('bg-', 'text-')} mb-1">
            ${getIconSvg(template.icon)}
          </div>
          <div class="text-xs text-gray-600">Widget Content</div>
        </div>
      </div>
    `;

    widgetEl.appendChild(contentEl);

    gridStackRef.current.addWidget(widgetEl, {
      w: template.defaultSize.w,
      h: template.defaultSize.h
    });
  };

  const getIconSvg = (IconComponent: any) => {
    // Simple icon representations for HTML
    const iconMap: Record<string, string> = {
      'Gauge': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>',
      'LineChart': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4"></path></svg>',
      'Activity': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>',
      'Table': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0V4a1 1 0 011-1h12a1 1 0 011 1v16a1 1 0 01-1 1H5a1 1 0 01-1-1V10z"></path></svg>',
      'BarChart3': '<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>'
    };
    return iconMap[IconComponent.name] || iconMap['BarChart3'];
  };

  // Add global functions for widget management
  useEffect(() => {
    (window as any).editWidget = (widgetId: string) => {
      console.log('Edit widget:', widgetId);
      // TODO: Open widget configuration dialog
    };

    (window as any).removeWidget = (widgetId: string) => {
      if (gridStackRef.current) {
        const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (widgetEl) {
          gridStackRef.current.removeWidget(widgetEl as HTMLElement);
        }
      }
    };

    return () => {
      delete (window as any).editWidget;
      delete (window as any).removeWidget;
    };
  }, []);

  const saveLayout = () => {
    if (onSave) {
      onSave(widgets);
    }
    console.log('Saving layout:', widgets);
  };

  const clearAll = () => {
    if (gridStackRef.current && confirm('Clear all widgets? This cannot be undone.')) {
      gridStackRef.current.removeAll();
      setWidgets([]);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white">
        <div>
          <h2 className="text-xl font-bold">Dashboard Builder</h2>
          <p className="text-sm text-muted-foreground">
            Drag widgets from the palette to create your custom dashboard
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {widgets.length} widgets
          </Badge>
          <Button variant="outline" size="sm" onClick={clearAll}>
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All
          </Button>
          <Button variant="outline" size="sm" onClick={saveLayout}>
            <Save className="h-4 w-4 mr-2" />
            Save Layout
          </Button>
          {onClose && (
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Widget Palette */}
        <div className="w-64 border-r bg-gray-50 p-4">
          <h3 className="font-medium mb-4">Widget Palette</h3>
          <div className="space-y-2">
            {widgetTemplates.map((template) => (
              <Card 
                key={template.type} 
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => addWidget(template)}
              >
                <CardContent className="p-3">
                  <div className="flex items-center gap-2">
                    <div className={`p-2 rounded ${template.color} bg-opacity-20`}>
                      <template.icon className={`h-4 w-4 ${template.color.replace('bg-', 'text-')}`} />
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{template.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {template.defaultSize.w}x{template.defaultSize.h}
                      </div>
                    </div>
                    <Plus className="h-4 w-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {devices.length > 0 && (
            <div className="mt-6">
              <h4 className="font-medium text-sm mb-2">Available Devices</h4>
              <div className="space-y-1">
                {devices.slice(0, 5).map((device) => (
                  <div key={device.id} className="text-xs p-2 bg-white rounded border">
                    <div className="font-medium">{device.name}</div>
                    <div className="text-muted-foreground">{device.type}</div>
                  </div>
                ))}
                {devices.length > 5 && (
                  <div className="text-xs text-muted-foreground p-2">
                    +{devices.length - 5} more devices
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* GridStack Canvas */}
        <div className="flex-1 overflow-auto bg-gray-100 p-4">
          <div 
            ref={gridRef} 
            className="grid-stack min-h-[600px]"
          >
            {/* GridStack widgets will be added here dynamically */}
          </div>
          
          {widgets.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-center">
              <div>
                <Grid3X3 className="h-16 w-16 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-600 mb-2">
                  Start Building Your Dashboard
                </h3>
                <p className="text-gray-500 max-w-md">
                  Click on widgets from the palette on the left to add them to your dashboard. 
                  Drag and resize to customize your layout.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};