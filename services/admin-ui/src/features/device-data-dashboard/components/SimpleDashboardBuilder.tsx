/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { SchemaBasedWidgetConfig } from './SchemaBasedWidgetConfig';
import { 
  Plus, 
  Save, 
  Trash2, 
  BarChart3, 
  Gauge, 
  Activity,
  Grid3X3,
  LineChart,
  Table,
  Table2,
  X,
  Settings,
  Move,
  TrendingUp,
  AlertTriangle,
  Zap,
  AreaChart,
  PieChart,
  ScatterChart,
  Target,
  LayoutGrid,
  GitBranch,
  Map,
  Battery,
  Hash,
  Binary,
  MessageSquare,
  AlertCircle,
  Box,
  Clock,
  Percent,
  Layers
} from 'lucide-react';

// Import GridStack and its CSS
import 'gridstack/dist/gridstack.min.css';
import './gridstack-custom.css';
import { GridStack } from 'gridstack';

interface GridStackWidget {
  id: string;
  type: string;
  title: string;
  x?: number;
  y?: number;
  w: number;
  h: number;
  content?: string;
  deviceId?: string;
}

interface SimpleDashboardBuilderProps {
  devices: any[];
  onClose?: () => void;
  onSave?: (widgets: GridStackWidget[]) => void;
}

// Comprehensive IoT Dashboard Widget Types with Custom SVG Icons
const widgetTemplates = [
  // Chart Widgets
  {
    type: 'line-chart',
    title: 'Line Chart',
    icon: TrendingUp,
    size: { rows: 3, cols: 4 },
    color: 'bg-blue-600',
    category: 'chart',
    description: 'Real-time trend visualization'
  },
  {
    type: 'gauge-chart',
    title: 'Gauge Chart',
    icon: Gauge,
    size: { rows: 2, cols: 2 },
    color: 'bg-amber-600',
    category: 'chart',
    description: 'Circular value display'
  },
  {
    type: 'bar-chart',
    title: 'Bar Chart',
    icon: BarChart3,
    size: { rows: 3, cols: 4 },
    color: 'bg-green-600',
    category: 'chart',
    description: 'Comparative visualization'
  },
  {
    type: 'area-chart',
    title: 'Area Chart',
    icon: AreaChart,
    size: { rows: 3, cols: 4 },
    color: 'bg-purple-600',
    category: 'chart',
    description: 'Filled trend visualization'
  },
  {
    type: 'pie-chart',
    title: 'Pie Chart',
    icon: PieChart,
    size: { rows: 3, cols: 3 },
    color: 'bg-pink-600',
    category: 'chart',
    description: 'Proportional data display'
  },
  {
    type: 'heat-map',
    title: 'Heat Map',
    icon: Grid3X3,
    size: { rows: 4, cols: 4 },
    color: 'bg-orange-600',
    category: 'chart',
    description: 'Color-coded matrix'
  },
  {
    type: 'scatter-plot',
    title: 'Scatter Plot',
    icon: ScatterChart,
    size: { rows: 3, cols: 4 },
    color: 'bg-indigo-600',
    category: 'chart',
    description: 'Correlation analysis'
  },
  {
    type: 'radar-chart',
    title: 'Radar Chart',
    icon: Target,
    size: { rows: 3, cols: 3 },
    color: 'bg-teal-600',
    category: 'chart',
    description: 'Multi-axis comparison'
  },
  
  // Status & Grid Widgets
  {
    type: 'status-grid',
    title: 'Status Grid',
    icon: LayoutGrid,
    size: { rows: 3, cols: 3 },
    color: 'bg-gray-700',
    category: 'status',
    description: 'Device state matrix'
  },
  {
    type: 'status-timeline',
    title: 'Status Timeline',
    icon: GitBranch,
    size: { rows: 2, cols: 6 },
    color: 'bg-cyan-600',
    category: 'status',
    description: 'Historical state changes'
  },
  
  // Map & Location
  {
    type: 'map-widget',
    title: 'Map Widget',
    icon: Map,
    size: { rows: 4, cols: 6 },
    color: 'bg-emerald-600',
    category: 'map',
    description: 'Geographic visualization'
  },
  
  // KPI & Progress
  {
    type: 'kpi-card',
    title: 'KPI Card',
    icon: Zap,
    size: { rows: 2, cols: 2 },
    color: 'bg-blue-700',
    category: 'kpi',
    description: 'Key metric display'
  },
  {
    type: 'progress-bar',
    title: 'Progress Bar',
    icon: Battery,
    size: { rows: 1, cols: 4 },
    color: 'bg-violet-600',
    category: 'kpi',
    description: 'Linear completion indicator'
  },
  
  // Data Display
  {
    type: 'table-widget',
    title: 'Table Widget',
    icon: Table2,
    size: { rows: 4, cols: 6 },
    color: 'bg-slate-700',
    category: 'data',
    description: 'Structured data rows'
  },
  {
    type: 'sparkline',
    title: 'Sparkline',
    icon: Activity,
    size: { rows: 1, cols: 2 },
    color: 'bg-sky-600',
    category: 'data',
    description: 'Compact trend display'
  },
  
  // Digital Text Displays
  {
    type: 'digital-counter',
    title: 'Digital Counter',
    icon: Hash,
    size: { rows: 2, cols: 3 },
    color: 'bg-red-700',
    category: 'text',
    description: 'Large numeric counter'
  },
  {
    type: 'led-display',
    title: 'LED Display',
    icon: Binary,
    size: { rows: 1, cols: 3 },
    color: 'bg-green-700',
    category: 'text',
    description: 'Seven-segment readout'
  },
  {
    type: 'metric-card',
    title: 'Metric Card',
    icon: Gauge,
    size: { rows: 2, cols: 2 },
    color: 'bg-blue-600',
    category: 'text',
    description: 'Value with context'
  },
  {
    type: 'text-ticker',
    title: 'Text Ticker',
    icon: MessageSquare,
    size: { rows: 1, cols: 6 },
    color: 'bg-yellow-600',
    category: 'text',
    description: 'Scrolling messages'
  },
  {
    type: 'status-badge',
    title: 'Status Badge',
    icon: AlertCircle,
    size: { rows: 1, cols: 2 },
    color: 'bg-red-600',
    category: 'text',
    description: 'Compact state label'
  },
  {
    type: 'value-box',
    title: 'Value Box',
    icon: Box,
    size: { rows: 2, cols: 3 },
    color: 'bg-purple-700',
    category: 'text',
    description: 'Multiple related values'
  },
  {
    type: 'alert-banner',
    title: 'Alert Banner',
    icon: AlertTriangle,
    size: { rows: 1, cols: 6 },
    color: 'bg-red-700',
    category: 'text',
    description: 'Warning messages'
  },
  {
    type: 'timestamp-display',
    title: 'Timestamp Display',
    icon: Clock,
    size: { rows: 1, cols: 3 },
    color: 'bg-gray-700',
    category: 'text',
    description: 'Date/time display'
  },
  {
    type: 'percentage-indicator',
    title: 'Percentage Indicator',
    icon: Percent,
    size: { rows: 2, cols: 2 },
    color: 'bg-orange-700',
    category: 'text',
    description: 'Percentage display'
  },
  {
    type: 'multi-value-display',
    title: 'Multi-Value Display',
    icon: Layers,
    size: { rows: 2, cols: 4 },
    color: 'bg-indigo-700',
    category: 'text',
    description: 'Grouped metrics'
  }
];

export const SimpleDashboardBuilder: React.FC<SimpleDashboardBuilderProps> = ({
  devices,
  onClose,
  onSave
}) => {
  const [widgets, setWidgets] = useState<GridStackWidget[]>([]);
  const gridRef = useRef<HTMLDivElement>(null);
  const gridStackRef = useRef<GridStack | null>(null);
  const [isGridReady, setIsGridReady] = useState(false);
  const [hasGridItems, setHasGridItems] = useState(false);
  const [showWidgetConfig, setShowWidgetConfig] = useState(false);
  const [selectedWidgetType, setSelectedWidgetType] = useState<string>('');
  const [editingWidget, setEditingWidget] = useState<GridStackWidget | null>(null);

  // Initialize GridStack when component mounts
  useEffect(() => {
    if (!gridRef.current) return;

    // Initialize GridStack with options
    gridStackRef.current = GridStack.init({
      cellHeight: 80,
      column: 12,
      minRow: 1,
      margin: 5,
      float: true,
      animate: true,
      resizable: {
        handles: 'se, sw, ne, nw'
      },
      draggable: {
        handle: '.widget-header'
      },
      removable: true,
      removeTimeout: 100,
      acceptWidgets: true,
      alwaysShowResizeHandle: true
    }, gridRef.current);

    // Force CSS variables update after initialization
    setTimeout(() => {
      if (gridStackRef.current && gridRef.current) {
        const grid = gridStackRef.current;
        const container = gridRef.current;
        
        // Set CSS variables manually based on GridStack settings
        const cellHeight = grid.getCellHeight();
        const margin = 5; // Our margin setting
        const columnWidth = (container.offsetWidth - (margin * 11)) / 12; // 12 columns with 11 gaps
        
        // Set the correct CSS variable names that GridStack uses
        container.style.setProperty('--gs-cell-height', `${cellHeight}px`);
        container.style.setProperty('--gs-column-width', `${columnWidth}px`); // Fixed variable name
        container.style.setProperty('--gs-margin', `${margin}px`);
        
        console.log('CSS variables set:', {
          cellHeight: `${cellHeight}px`,
          cellWidth: `${columnWidth}px`,
          margin: `${margin}px`
        });
      }
    }, 100);

    // Listen to GridStack events
    gridStackRef.current.on('change', (event, items) => {
      console.log('Grid changed:', items);
      updateWidgetPositions();
      setHasGridItems(gridStackRef.current?.getGridItems().length > 0);
    });

    gridStackRef.current.on('removed', (event, items) => {
      console.log('Widget removed:', items);
      updateWidgetPositions();
      setHasGridItems(gridStackRef.current?.getGridItems().length > 0);
    });

    gridStackRef.current.on('added', (event, items) => {
      console.log('Widget added:', items);
      setHasGridItems(true);
    });

    setIsGridReady(true);

    // Cleanup on unmount
    return () => {
      if (gridStackRef.current) {
        gridStackRef.current.destroy(false);
      }
    };
  }, []);

  // Update widget positions from GridStack
  const updateWidgetPositions = () => {
    if (!gridStackRef.current) return;

    const gridItems = gridStackRef.current.getGridItems();
    const updatedWidgets: GridStackWidget[] = [];

    console.log('Updating widget positions, grid items:', gridItems.length);

    gridItems.forEach((el) => {
      const widgetId = el.getAttribute('data-widget-id');
      const gridStackItem = el.gridstackNode;
      
      if (widgetId && gridStackItem) {
        const existingWidget = widgets.find(w => w.id === widgetId);
        if (existingWidget) {
          const updatedWidget = {
            ...existingWidget,
            x: gridStackItem.x,
            y: gridStackItem.y,
            w: gridStackItem.w,
            h: gridStackItem.h
          };
          updatedWidgets.push(updatedWidget);
          console.log('Updated widget position:', updatedWidget);
        }
      }
    });

    console.log('Setting updated widgets:', updatedWidgets);
    setWidgets(updatedWidgets);
    setHasGridItems(updatedWidgets.length > 0);
  };

  const addWidget = (template: typeof widgetTemplates[0]) => {
    // Instead of creating widget immediately, open configuration dialog to select device/sensor
    console.log('Opening widget configuration for type:', template.type);
    setSelectedWidgetType(template.type);
    setEditingWidget(null); // Clear any existing editing widget
    setShowWidgetConfig(true);
  };

  // Function to actually create the widget after configuration
  const createWidgetWithConfig = (config: any) => {
    if (!gridStackRef.current) {
      console.error('GridStack not initialized');
      return;
    }
    
    // Ensure grid is ready and enabled
    console.log('🔍 Grid state check:', {
      gridExists: !!gridStackRef.current,
      gridElement: !!gridRef.current,
      isEnabled: gridStackRef.current.opts.disableDrag === false,
      cellHeight: gridStackRef.current.getCellHeight(),
      column: gridStackRef.current.getColumn()
    });
    
    // Enable the grid if it's disabled
    if (gridStackRef.current.opts.disableDrag) {
      gridStackRef.current.enable();
      console.log('✅ Grid enabled');
    }

    const template = widgetTemplates.find(t => t.type === selectedWidgetType);
    if (!template) {
      console.error('Template not found for type:', selectedWidgetType);
      return;
    }

    const widgetId = `widget-${Date.now()}`;
    const newWidget: GridStackWidget = {
      id: widgetId,
      type: template.type,
      title: config.title || template.title,
      w: template.size.cols,
      h: template.size.rows,
      deviceId: config.deviceId,
      fieldKey: config.fieldKey
    };

    console.log('Creating widget:', newWidget.title);

    // Create widget content HTML
    const content = createWidgetContent(newWidget, template);

    // Create DOM element for widget (GridStack v11 requires DOM element, not string)
    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'grid-stack-item';
    widgetDiv.setAttribute('data-widget-id', widgetId);
    widgetDiv.setAttribute('data-widget-type', newWidget.type);
    widgetDiv.setAttribute('data-widget-title', newWidget.title);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'grid-stack-item-content';
    contentDiv.innerHTML = content;
    
    widgetDiv.appendChild(contentDiv);
    
    console.log('🚀 Attempting to add widget to GridStack...');
    console.log('📦 Widget DOM element:', widgetDiv);
    
    // Use makeWidget for GridStack v11 (addWidget is deprecated)
    const widgetEl = gridStackRef.current.makeWidget(widgetDiv);
    
    // Set widget options after creation
    if (widgetEl && widgetEl.gridstackNode) {
      gridStackRef.current.update(widgetEl, {
        x: 0,
        y: 0,
        w: newWidget.w,
        h: newWidget.h,
        id: widgetId
      });
    }
    
    console.log('🎯 Widget added result:', widgetEl);

    // IMMEDIATE: Force direct pixel positioning right after creation
    if (widgetEl) {
      const container = gridRef.current;
      if (container) {
        const cellWidth = (container.offsetWidth - 55) / 12; // 5px margin * 11 gaps
        const cellHeight = 80;
        const margin = 5;
        
        // Get position from GridStack
        const gridItem = widgetEl.gridstackNode;
        if (gridItem) {
          // Calculate proper dimensions with margins
          const left = gridItem.x * (cellWidth + margin);
          const top = gridItem.y * (cellHeight + margin);
          const width = gridItem.w * cellWidth + (gridItem.w - 1) * margin;
          const height = gridItem.h * cellHeight + (gridItem.h - 1) * margin;
          
          // Apply styles directly - bypass CSS variables completely
          widgetEl.style.setProperty('left', `${left}px`, 'important');
          widgetEl.style.setProperty('top', `${top}px`, 'important');
          widgetEl.style.setProperty('width', `${width}px`, 'important');
          widgetEl.style.setProperty('height', `${height}px`, 'important');
          
          console.log('🔥 FORCED direct pixel positioning:', { left, top, width, height });
          
          // EXTRA DEBUG: Check if widget is in DOM
          setTimeout(() => {
            const checkWidget = document.querySelector(`[data-widget-id="${widgetId}"]`);
            if (checkWidget) {
              const rect = checkWidget.getBoundingClientRect();
              console.log('🔍 Widget DOM check:', {
                found: true,
                inDOM: document.body.contains(checkWidget),
                parentElement: checkWidget.parentElement?.className,
                boundingRect: {
                  top: rect.top,
                  left: rect.left,
                  width: rect.width,
                  height: rect.height,
                  visible: rect.width > 0 && rect.height > 0
                },
                computedStyle: {
                  display: window.getComputedStyle(checkWidget).display,
                  visibility: window.getComputedStyle(checkWidget).visibility,
                  opacity: window.getComputedStyle(checkWidget).opacity,
                  position: window.getComputedStyle(checkWidget).position,
                  zIndex: window.getComputedStyle(checkWidget).zIndex
                }
              });
            } else {
              console.log('❌ Widget NOT found in DOM!');
            }
          }, 500);
        }
      }
    }

    console.log('Widget element created:', widgetEl);
    
    // Debug CSS variables after widget creation
    setTimeout(() => {
      const gridContainer = gridRef.current;
      if (gridContainer && widgetEl) {
        const computedStyle = window.getComputedStyle(gridContainer);
        const widgetStyle = window.getComputedStyle(widgetEl);
        
        console.log('🔍 CSS Debug after widget creation:', {
          containerCSSVars: {
            '--gs-cell-height': computedStyle.getPropertyValue('--gs-cell-height'),
            '--gs-column-width': computedStyle.getPropertyValue('--gs-column-width'),
            '--gs-margin': computedStyle.getPropertyValue('--gs-margin')
          },
          widgetInlineStyle: widgetEl.getAttribute('style'),
          widgetComputedStyle: {
            width: widgetStyle.width,
            height: widgetStyle.height,
            left: widgetStyle.left,
            top: widgetStyle.top
          }
        });
        
        // Force fix positioning if CSS variables are not working
        const widgetInlineStyle = widgetEl.getAttribute('style');
        if (widgetInlineStyle && widgetInlineStyle.includes('calc(') && 
            (widgetStyle.left === 'auto' || widgetStyle.left === '0px' || widgetStyle.left === '')) {
          console.log('🔧 CSS calc() failed, applying manual positioning');
          
          // Get grid item data from GridStack
          const gridItem = widgetEl.gridstackNode;
          if (gridItem) {
            const cellWidth = (gridContainer.offsetWidth - 55) / 12; // 5px margin * 11 gaps
            const cellHeight = 80;
            const margin = 5;
            
            const left = gridItem.x * cellWidth + gridItem.x * margin;
            const top = gridItem.y * cellHeight + gridItem.y * margin;
            const width = gridItem.w * cellWidth + (gridItem.w - 1) * margin;
            const height = gridItem.h * cellHeight + (gridItem.h - 1) * margin;
            
            widgetEl.style.left = `${left}px`;
            widgetEl.style.top = `${top}px`;
            widgetEl.style.width = `${width}px`;
            widgetEl.style.height = `${height}px`;
            
            console.log('✅ Manual positioning applied:', { left, top, width, height });
          }
        }
      }
    }, 200);

    // Update state
    setWidgets(prev => {
      const updated = [...prev, newWidget];
      setHasGridItems(updated.length > 0);
      return updated;
    });
    
    console.log('Widget created successfully');
  };

  const createWidgetContent = (widget: GridStackWidget, template: typeof widgetTemplates[0]) => {
    const Icon = template.icon;
    const iconColor = template.color.replace('bg-', 'text-');
    const selectedDevice = devices.find(d => d.id === widget.deviceId);
    
    return `
      <div class="bg-white border rounded-lg shadow-sm h-full flex flex-col" data-widget-type="${widget.type}" data-widget-title="${widget.title}">
        <div class="widget-header flex items-center justify-between p-3 border-b cursor-move">
          <div class="flex items-center gap-2">
            <div class="p-1.5 rounded ${template.color} flex items-center justify-center">
              ${getIconSvg(Icon.name, 'w-4 h-4 text-white')}
            </div>
            <h4 class="font-medium text-sm">${widget.title}</h4>
          </div>
          <div class="flex items-center gap-1">
            <button class="widget-settings text-gray-500 hover:text-gray-700 p-1 rounded hover:bg-gray-100" data-widget-id="${widget.id}" title="Configure Widget">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
              </svg>
            </button>
            <button class="remove-widget text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50" data-widget-id="${widget.id}" title="Remove Widget">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
              </svg>
            </button>
          </div>
        </div>
        <div class="flex-1 p-4">
          <div class="h-full flex flex-col items-center justify-center">
            <div class="text-center">
              <div class="p-3 rounded ${template.color} mb-3 inline-flex items-center justify-center">
                ${getIconSvg(Icon.name, 'w-10 h-10 text-white')}
              </div>
              ${selectedDevice ? `
                <p class="text-sm font-medium text-gray-900">${selectedDevice.name}</p>
                <p class="text-xs text-gray-500 mt-1">${widget.fieldKey || 'No field selected'}</p>
                <div class="mt-3">
                  <p class="text-2xl font-bold text-gray-900">--</p>
                  <p class="text-xs text-gray-500">Waiting for data...</p>
                </div>
              ` : `
                <p class="text-sm text-gray-500">${template.description}</p>
                <p class="text-xs text-gray-400 mt-2">Click settings to configure</p>
              `}
            </div>
          </div>
        </div>
        <div class="absolute bottom-0 right-0 p-1">
          <svg class="w-4 h-4 text-gray-400 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5"></path>
          </svg>
        </div>
      </div>
    `;
  };

  // Add event delegation for remove buttons, config buttons, and device selectors
  useEffect(() => {
    const handleRemoveClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const removeBtn = target.closest('.remove-widget');
      
      if (removeBtn && gridStackRef.current) {
        const widgetId = removeBtn.getAttribute('data-widget-id');
        const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
        
        if (widgetEl) {
          console.log('Removing widget:', widgetId);
          gridStackRef.current.removeWidget(widgetEl);
          setWidgets(prev => {
            const updated = prev.filter(w => w.id !== widgetId);
            console.log('Updated widgets after removal:', updated);
            setHasGridItems(updated.length > 0);
            return updated;
          });
        }
      }
    };

    const handleConfigClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const configBtn = target.closest('.widget-settings');
      
      if (configBtn) {
        e.preventDefault();
        e.stopPropagation();
        const widgetId = configBtn.getAttribute('data-widget-id');
        const widget = widgets.find(w => w.id === widgetId);
        
        if (widget) {
          console.log('Opening config for widget:', widget);
          setEditingWidget(widget);
          setSelectedWidgetType(widget.type);
          setShowWidgetConfig(true);
        }
      }
    };

    const handleDeviceChange = (e: Event) => {
      const target = e.target as HTMLSelectElement;
      if (target.classList.contains('device-selector')) {
        const widgetId = target.getAttribute('data-widget-id');
        const deviceId = target.value;
        
        if (widgetId) {
          // Update widget state
          setWidgets(prev => prev.map(w => 
            w.id === widgetId ? { ...w, deviceId } : w
          ));
          
          // Update widget content
          const widgetEl = document.querySelector(`[data-widget-id="${widgetId}"]`);
          if (widgetEl) {
            const widget = widgets.find(w => w.id === widgetId);
            const template = widgetTemplates.find(t => t.type === widget?.type);
            
            if (widget && template) {
              const updatedWidget = { ...widget, deviceId };
              const contentEl = widgetEl.querySelector('.grid-stack-item-content');
              if (contentEl) {
                contentEl.innerHTML = createWidgetContent(updatedWidget, template);
              }
            }
          }
        }
      }
    };

    document.addEventListener('click', handleRemoveClick);
    document.addEventListener('click', handleConfigClick);
    document.addEventListener('change', handleDeviceChange);
    
    return () => {
      document.removeEventListener('click', handleRemoveClick);
      document.removeEventListener('click', handleConfigClick);
      document.removeEventListener('change', handleDeviceChange);
    };
  }, [widgets, devices]);

  // SECURITY GUARD: getIconSvg output is rendered via dangerouslySetInnerHTML /
  // template interpolation. It is safe ONLY because `icons` is a CLOSED map of
  // hard-coded SVG strings and unknown names fall through to a hard-coded
  // default. Never extend this to interpolate user/device-provided strings
  // into the returned markup — add new icons as static entries instead.
  const getIconSvg = (iconName: string, className = 'w-6 h-6 text-white') => {
    // Custom SVG designs with white strokes for dark backgrounds
    const icons: Record<string, string> = {
      // Line Chart
      'TrendingUp': `<svg width="20" height="20" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 40L6 10" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M6 40L40 40" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M10 32L16 24L22 28L28 20L36 26" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`,
      
      // Gauge Chart
      'Gauge': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M6 32C6 21.507 14.507 13 25 13C35.493 13 44 21.507 44 32" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="20" cy="32" r="3" fill="white"/>
        <path d="M20 32L26 20" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <path d="M10 26L11 25M30 26L29 25M20 15V13" stroke="white" stroke-width="2" stroke-linecap="round"/>
      </svg>`,
      
      // Bar Chart
      'BarChart3': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="6" y="24" width="6" height="12" fill="white" rx="1"/>
        <rect x="14" y="18" width="6" height="18" fill="white" rx="1"/>
        <rect x="22" y="12" width="6" height="24" fill="white" rx="1"/>
        <rect x="30" y="20" width="6" height="16" fill="white" rx="1"/>
        <path d="M4 36L38 36" stroke="white" stroke-width="2" stroke-linecap="round"/>
      </svg>`,
      
      // Area Chart
      'AreaChart': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 36L4 8M4 36L36 36" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <path d="M8 28L14 20L20 24L26 16L32 22L32 36L8 36Z" fill="white" fill-opacity="0.15"/>
        <path d="M8 28L14 20L20 24L26 16L32 22" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`,
      
      // Pie Chart
      'PieChart': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="20" cy="20" r="16" stroke="white" stroke-width="2.5" fill="none"/>
        <path d="M20 4L20 20L32.9 28" stroke="white" stroke-width="2.5"/>
        <path d="M20 20L7.1 12" stroke="white" stroke-width="2.5"/>
        <path d="M20 4A16 16 0 0 1 32.9 28L20 20Z" fill="white" fill-opacity="0.2"/>
      </svg>`,
      
      // Heat Map
      'Grid3X3': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="4" width="8" height="8" fill="white" fill-opacity="0.2" rx="1"/>
        <rect x="14" y="4" width="8" height="8" fill="white" fill-opacity="0.6" rx="1"/>
        <rect x="24" y="4" width="8" height="8" fill="white" fill-opacity="0.4" rx="1"/>
        <rect x="4" y="14" width="8" height="8" fill="white" fill-opacity="0.4" rx="1"/>
        <rect x="14" y="14" width="8" height="8" fill="white" fill-opacity="1" rx="1"/>
        <rect x="24" y="14" width="8" height="8" fill="white" fill-opacity="0.8" rx="1"/>
        <rect x="4" y="24" width="8" height="8" fill="white" fill-opacity="0.8" rx="1"/>
        <rect x="14" y="24" width="8" height="8" fill="white" fill-opacity="0.4" rx="1"/>
        <rect x="24" y="24" width="8" height="8" fill="white" fill-opacity="0.6" rx="1"/>
      </svg>`,
      
      // Scatter Plot
      'ScatterChart': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 36L4 8M4 36L36 36" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <circle cx="10" cy="28" r="2.5" fill="white"/>
        <circle cx="16" cy="16" r="2.5" fill="white"/>
        <circle cx="24" cy="24" r="2.5" fill="white"/>
        <circle cx="18" cy="30" r="2.5" fill="white"/>
        <circle cx="28" cy="12" r="2.5" fill="white"/>
        <circle cx="32" cy="20" r="2.5" fill="white"/>
      </svg>`,
      
      // Radar Chart
      'Target': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 6L32.66 13L32.66 27L20 34L7.34 27L7.34 13Z" stroke="white" stroke-width="2" stroke-linejoin="round" fill="none"/>
        <path d="M20 6L20 20M32.66 13L20 20M32.66 27L20 20M20 34L20 20M7.34 27L20 20M7.34 13L20 20" stroke="white" stroke-width="1" stroke-opacity="0.2"/>
        <path d="M20 12L26.6 16L26.6 24L20 28L13.4 24L13.4 16Z" fill="white" fill-opacity="0.2" stroke="white" stroke-width="2" stroke-linejoin="round"/>
      </svg>`,
      
      // Status Grid
      'LayoutGrid': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="4" width="14" height="14" rx="3" fill="white"/>
        <rect x="22" y="4" width="14" height="14" rx="3" stroke="white" stroke-width="2.5" fill="none"/>
        <rect x="4" y="22" width="14" height="14" rx="3" fill="white" fill-opacity="0.3"/>
        <rect x="22" y="22" width="14" height="14" rx="3" fill="white"/>
      </svg>`,
      
      // Status Timeline
      'GitBranch': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="2" y1="20" x2="38" y2="20" stroke="white" stroke-width="2.5"/>
        <rect x="4" y="16" width="8" height="8" fill="white" rx="1"/>
        <rect x="14" y="16" width="10" height="8" fill="white" fill-opacity="0.3" rx="1"/>
        <rect x="26" y="16" width="6" height="8" fill="white" rx="1"/>
        <rect x="34" y="16" width="4" height="8" fill="white" fill-opacity="0.6" rx="1"/>
      </svg>`,
      
      // Map Widget
      'Map': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 26C4 26 7 21 13 21C19 21 22 26 28 26C34 26 36 21 36 21" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <path d="M4 32C4 32 7 28 13 28C19 28 22 32 28 32C34 32 36 28 36 28" stroke="white" stroke-width="2" stroke-linecap="round"/>
        <path d="M20 10C20 14 16 20 16 20C16 20 24 20 24 20C24 20 20 14 20 10Z" fill="white"/>
        <circle cx="20" cy="10" r="4" fill="white"/>
      </svg>`,
      
      // KPI Card
      'Zap': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="6" width="36" height="28" rx="4" stroke="white" stroke-width="2.5" fill="none"/>
        <text x="20" y="25" font-family="Arial, sans-serif" font-size="14" font-weight="bold" text-anchor="middle" fill="white">123</text>
        <path d="M28 12L31 9L34 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`,
      
      // Progress Bar
      'Battery': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="16" width="32" height="10" rx="5" stroke="white" stroke-width="2.5" fill="none"/>
        <rect x="4" y="16" width="22" height="10" rx="5" fill="white"/>
      </svg>`,
      
      // Table Widget
      'Table2': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="4" y="6" width="32" height="30" rx="2" stroke="white" stroke-width="2.5" fill="none"/>
        <line x1="4" y1="14" x2="36" y2="14" stroke="white" stroke-width="2.5"/>
        <line x1="4" y1="22" x2="36" y2="22" stroke="white" stroke-width="1.5"/>
        <line x1="4" y1="29" x2="36" y2="29" stroke="white" stroke-width="1.5"/>
        <line x1="14" y1="6" x2="14" y2="36" stroke="white" stroke-width="1.5"/>
        <line x1="26" y1="6" x2="26" y2="36" stroke="white" stroke-width="1.5"/>
        <rect x="4" y="6" width="32" height="8" fill="white" fill-opacity="0.1"/>
      </svg>`,
      
      // Sparkline
      'Activity': `<svg class="${className}" viewBox="0 0 48 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 25L12 20L19 27L26 16L33 23L42 18" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`,
      
      // Digital Counter
      'Hash': `<svg class="${className}" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text x="22" y="32" font-family="Arial Black, sans-serif" font-size="24" font-weight="900" text-anchor="middle" fill="white">999</text>
      </svg>`,
      
      // LED Display
      'Binary': `<svg class="${className}" viewBox="0 0 48 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <g stroke="white" stroke-width="3" fill="none">
          <path d="M7 11L12 11M7 20L12 20M7 11L7 20M12 11L12 20M7 20L12 25M12 20L12 29M7 29L12 29"/>
          <circle cx="14" cy="27" r="1.5" fill="white"/>
          <path d="M18 11L23 11M18 20L23 20M18 11L18 20M23 11L23 20M18 20L23 25M23 20L23 29M18 29L23 29"/>
          <circle cx="25" cy="27" r="1.5" fill="white"/>
          <path d="M29 11L34 11M29 20L34 20M29 11L29 20M34 11L34 20M29 20L34 25M34 20L34 29M29 29L34 29"/>
        </g>
      </svg>`,
      
      
      // Text Ticker
      'MessageSquare': `<svg class="${className}" viewBox="0 0 46 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="15" width="40" height="14" rx="3" stroke="white" stroke-width="3" fill="none"/>
        <path d="M7 22L10 19L13 22M17 22L20 19L23 22M27 22L30 19L33 22" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="37" cy="22" r="1.5" fill="white"/>
        <circle cx="39" cy="22" r="1.5" fill="white" fill-opacity="0.5"/>
        <circle cx="41" cy="22" r="1.5" fill="white" fill-opacity="0.2"/>
      </svg>`,
      
      // Status Badge
      'AlertCircle': `<svg class="${className}" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="9" y="15" width="28" height="14" rx="7" fill="white"/>
        <text x="23" y="25" font-family="Arial, sans-serif" font-size="10" font-weight="bold" text-anchor="middle" fill="black">ON</text>
      </svg>`,
      
      // Value Box
      'Box': `<svg class="${className}" viewBox="0 0 46 44" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="11" width="40" height="22" rx="3" stroke="white" stroke-width="3" fill="none"/>
        <line x1="16" y1="11" x2="16" y2="33" stroke="white" stroke-width="2"/>
        <line x1="30" y1="11" x2="30" y2="33" stroke="white" stroke-width="2"/>
        <text x="9.5" y="26" font-family="Arial, sans-serif" font-size="9" text-anchor="middle" fill="white">A:1</text>
        <text x="23" y="26" font-family="Arial, sans-serif" font-size="9" text-anchor="middle" fill="white">B:2</text>
        <text x="36.5" y="26" font-family="Arial, sans-serif" font-size="9" text-anchor="middle" fill="white">C:3</text>
      </svg>`,
      
      // Alert Banner
      'AlertTriangle': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="12" width="36" height="16" rx="3" stroke="white" stroke-width="2.5" stroke-dasharray="3 3" fill="none"/>
        <path d="M10 16L13 22L16 16Z" fill="white"/>
        <text x="13" y="21" font-family="Arial, sans-serif" font-size="9" font-weight="bold" text-anchor="middle" fill="black">!</text>
      </svg>`,
      
      // Timestamp Display
      'Clock': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="15" cy="20" r="8" stroke="white" stroke-width="2.5" fill="none"/>
        <path d="M12 16L12 20L15 23" stroke="white" stroke-width="2.5" stroke-linecap="round"/>
        <text x="28" y="24" font-family="Arial, sans-serif" font-size="10" font-weight="bold" text-anchor="middle" fill="white">12:34</text>
      </svg>`,
      
      // Percentage Indicator
      'Percent': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <text x="16" y="26" font-family="Arial, sans-serif" font-size="18" font-weight="bold" text-anchor="middle" fill="white">85%</text>
      </svg>`,
      
      // Multi-Value Display
      'Layers': `<svg class="${className}" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="6" width="36" height="30" rx="3" stroke="white" stroke-width="2.5" fill="none"/>
        <line x1="2" y1="15" x2="38" y2="15" stroke="white" stroke-width="1.5"/>
        <line x1="2" y1="24" x2="38" y2="24" stroke="white" stroke-width="1.5"/>
        <text x="5" y="13" font-family="Arial, sans-serif" font-size="6" fill="white" opacity="0.7">Temp:</text>
        <text x="35" y="13" font-family="Arial, sans-serif" font-size="5" text-anchor="end" fill="white" font-weight="bold">25°C</text>
        <text x="5" y="22" font-family="Arial, sans-serif" font-size="6" fill="white" opacity="0.7">Humid:</text>
        <text x="35" y="22" font-family="Arial, sans-serif" font-size="5" text-anchor="end" fill="white" font-weight="bold">65%</text>
        <text x="5" y="31" font-family="Arial, sans-serif" font-size="6" fill="white" opacity="0.7">Press:</text>
        <text x="35" y="31" font-family="Arial, sans-serif" font-size="5" text-anchor="end" fill="white" font-weight="bold">1013</text>
      </svg>`
    };
    return icons[iconName] || icons['Zap'];
  };

  const saveLayout = () => {
    if (!gridStackRef.current) return;
    
    // Get current layout from GridStack
    const layout = gridStackRef.current.save();
    console.log('GridStack layout:', layout);
    
    // Include device connections in saved data
    const widgetsWithDevices = widgets.map(widget => ({
      ...widget,
      deviceId: widget.deviceId || ''
    }));
    
    console.log('Saving widgets with device connections:', widgetsWithDevices);
    
    if (onSave) {
      onSave(widgetsWithDevices);
    }
    alert('Dashboard layout saved with device connections!');
  };

  const clearAll = () => {
    if (!gridStackRef.current) return;
    
    if (confirm('Clear all widgets? This cannot be undone.')) {
      gridStackRef.current.removeAll();
      setWidgets([]);
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white shadow-sm">
        <div>
          <h2 className="text-xl font-bold">Dashboard Builder</h2>
          <p className="text-sm text-muted-foreground">
            Click widgets from the palette to add them to your dashboard
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {gridStackRef.current?.getGridItems().length || widgets.length} widgets
          </Badge>
          <Button variant="outline" size="sm" onClick={clearAll} disabled={widgets.length === 0}>
            <Trash2 className="h-4 w-4 mr-2" />
            Clear All
          </Button>
          <Button variant="outline" size="sm" onClick={saveLayout} disabled={!hasGridItems && widgets.length === 0}>
            <Save className="h-4 w-4 mr-2" />
            Save Layout ({gridStackRef.current?.getGridItems().length || widgets.length})
          </Button>
          {onClose && (
            <Button variant="outline" size="sm" onClick={onClose}>
              <X className="h-4 w-4 mr-2" />
              Close
            </Button>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Widget Palette */}
        <div className="w-80 border-r bg-gray-50 overflow-hidden flex flex-col">
          <div className="p-4 border-b bg-white">
            <h3 className="font-semibold text-lg mb-1">Widget Palette</h3>
            <p className="text-xs text-muted-foreground">Click to add widgets to your dashboard</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {/* Chart Widgets */}
            <div className="mb-6">
              <h4 className="font-medium text-sm text-gray-700 mb-3">Charts & Visualizations</h4>
              <div className="grid grid-cols-2 gap-2">
                {widgetTemplates.filter(t => t.category === 'chart').map((template) => (
                  <Card 
                    key={template.type} 
                    className="cursor-pointer hover:shadow-md transition-all hover:scale-[1.02] group border-gray-200 relative overflow-hidden"
                    onClick={() => addWidget(template)}
                  >
                    <CardContent className="p-3">
                      {/* Hover overlay with "Click to Add" */}
                      <div className="absolute inset-0 bg-blue-500 bg-opacity-90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
                        <div className="text-center text-white">
                          <Plus className="w-4 h-4 mx-auto mb-1" />
                          <span className="text-xs font-semibold">Click to Add</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`p-2 rounded ${template.color} transition-colors flex items-center justify-center`}>
                          <div dangerouslySetInnerHTML={{ __html: getIconSvg(template.icon.name, 'w-5 h-5') }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs truncate">{template.title}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {template.size.cols}×{template.size.rows}
                          </div>
                        </div>
                      </div>
                      <div className="text-[11px] text-gray-600 line-clamp-2">
                        {template.description}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Status & KPI Widgets */}
            <div className="mb-6">
              <h4 className="font-medium text-sm text-gray-700 mb-3">Status & KPIs</h4>
              <div className="grid grid-cols-2 gap-2">
                {widgetTemplates.filter(t => t.category === 'status' || t.category === 'kpi').map((template) => (
                  <Card 
                    key={template.type} 
                    className="cursor-pointer hover:shadow-md transition-all hover:scale-[1.02] group border-gray-200 relative overflow-hidden"
                    onClick={() => addWidget(template)}
                  >
                    <CardContent className="p-3">
                      {/* Hover overlay with "Click to Add" */}
                      <div className="absolute inset-0 bg-blue-500 bg-opacity-90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
                        <div className="text-center text-white">
                          <Plus className="w-4 h-4 mx-auto mb-1" />
                          <span className="text-xs font-semibold">Click to Add</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`p-2 rounded ${template.color} transition-colors flex items-center justify-center`}>
                          <div dangerouslySetInnerHTML={{ __html: getIconSvg(template.icon.name, 'w-5 h-5') }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs truncate">{template.title}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {template.size.cols}×{template.size.rows}
                          </div>
                        </div>
                      </div>
                      <div className="text-[11px] text-gray-600 line-clamp-2">
                        {template.description}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Data & Text Display Widgets */}
            <div className="mb-6">
              <h4 className="font-medium text-sm text-gray-700 mb-3">Data & Text Displays</h4>
              <div className="grid grid-cols-2 gap-2">
                {widgetTemplates.filter(t => t.category === 'data' || t.category === 'text').map((template) => (
                  <Card 
                    key={template.type} 
                    className="cursor-pointer hover:shadow-md transition-all hover:scale-[1.02] group border-gray-200 relative overflow-hidden"
                    onClick={() => addWidget(template)}
                  >
                    <CardContent className="p-3">
                      {/* Hover overlay with "Click to Add" */}
                      <div className="absolute inset-0 bg-blue-500 bg-opacity-90 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
                        <div className="text-center text-white">
                          <Plus className="w-4 h-4 mx-auto mb-1" />
                          <span className="text-xs font-semibold">Click to Add</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`p-2 rounded ${template.color} transition-colors flex items-center justify-center`}>
                          <div dangerouslySetInnerHTML={{ __html: getIconSvg(template.icon.name, 'w-5 h-5') }} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-xs truncate">{template.title}</div>
                          <div className="text-[10px] text-muted-foreground">
                            {template.size.cols}×{template.size.rows}
                          </div>
                        </div>
                      </div>
                      <div className="text-[11px] text-gray-600 line-clamp-2">
                        {template.description}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Map Widget */}
            <div className="mb-6">
              <h4 className="font-medium text-sm text-gray-700 mb-3">Location & Mapping</h4>
              <div className="grid grid-cols-1 gap-2">
                {widgetTemplates.filter(t => t.category === 'map').map((template) => (
                  <Card 
                    key={template.type} 
                    className="cursor-pointer hover:shadow-md transition-all hover:scale-[1.02] group border-gray-200"
                    onClick={() => addWidget(template)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-center gap-2">
                        <div className={`p-2 rounded ${template.color} bg-opacity-10 group-hover:bg-opacity-20 transition-colors`}>
                          <template.icon className={`h-5 w-5 ${template.color.replace('bg-', 'text-')}`} />
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-sm">{template.title}</div>
                          <div className="text-xs text-muted-foreground">
                            {template.size.cols}×{template.size.rows} • {template.description}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {devices.length > 0 && (
            <div className="mt-6 pt-6 border-t">
              <h4 className="font-medium text-sm mb-3 text-gray-700">Data Sources</h4>
              <div className="space-y-2">
                {devices.slice(0, 4).map((device) => (
                  <div key={device.id} className="p-3 bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{device.name}</div>
                        <div className="text-xs text-muted-foreground">{device.type}</div>
                      </div>
                    </div>
                  </div>
                ))}
                {devices.length > 4 && (
                  <div className="text-center text-xs text-muted-foreground py-2">
                    +{devices.length - 4} more available
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Dashboard Canvas with GridStack */}
        <div className="flex-1 overflow-auto p-4 bg-gray-100">
          <div className="min-h-[600px] relative">
            {/* GridStack container */}
            <div ref={gridRef} className="grid-stack min-h-[600px]">
              {/* GridStack will dynamically add widgets here */}
            </div>
            
            {/* Empty state - only show when no widgets and no grid items */}
            {!hasGridItems && widgets.length === 0 && isGridReady && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none transition-opacity duration-300">
                <div className="text-center bg-white/80 p-8 rounded-lg">
                  <Grid3X3 className="h-16 w-16 mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">
                    Start Building Your Dashboard
                  </h3>
                  <p className="text-gray-500 max-w-md">
                    Click on widgets from the palette on the left to add them to your dashboard.
                    Drag widgets to reposition them and resize from the corners.
                  </p>
                  <div className="mt-4 flex items-center justify-center gap-4 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <Move className="h-4 w-4" />
                      <span>Drag to move</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5v-4m0 4h-4m4 0l-5-5" />
                      </svg>
                      <span>Resize from corners</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Widget Configuration Dialog */}
      <Dialog open={showWidgetConfig} onOpenChange={setShowWidgetConfig}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Configure Widget with Device Schema</DialogTitle>
          </DialogHeader>
          <SchemaBasedWidgetConfig
            devices={devices}
            widgetType={selectedWidgetType}
            onConfigured={(config) => {
              createWidgetWithConfig(config);
              setShowWidgetConfig(false);
            }}
            onCancel={() => setShowWidgetConfig(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};