/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Terminal, 
  Search, 
  Filter, 
  Download, 
  Pause, 
  Play,
  Trash2,
  Copy,
  AlertCircle,
  Info,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { tesaApi } from '@/services/api/tesaApi';
import { useDeviceHealthWebSocket } from '@/hooks/useDeviceHealthWebSocket';

interface DeviceLog {
  id: string;
  timestamp: string;
  deviceId: string;
  deviceName?: string;
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  category: string;
  message: string;
  metadata?: Record<string, any>;
  source?: string;
  correlationId?: string;
}

interface DeviceLogViewerProps {
  deviceId?: string;
  maxLogs?: number;
  className?: string;
  height?: string;
}

const LOG_LEVELS = {
  debug: { icon: ChevronRight, color: 'text-gray-500 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-800' },
  info: { icon: Info, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/20' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/20' },
  error: { icon: XCircle, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/20' },
  critical: { icon: AlertCircle, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-100 dark:bg-purple-900/20' }
};

export const DeviceLogViewer: React.FC<DeviceLogViewerProps> = ({ 
  deviceId, 
  maxLogs = 500,
  className,
  height = "600px" 
}) => {
  const [logs, setLogs] = useState<DeviceLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<DeviceLog[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevels, setSelectedLevels] = useState<string[]>(['info', 'warning', 'error', 'critical']);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [categories, setCategories] = useState<string[]>(['all']);
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { isConnected, subscribe } = useDeviceHealthWebSocket();

  useEffect(() => {
    fetchInitialLogs();

    // Subscribe to real-time logs
    const unsubscribe = subscribe('device:log:new', (data: DeviceLog) => {
      if (!deviceId || data.deviceId === deviceId) {
        if (!isPaused) {
          setLogs(prev => {
            const newLogs = [data, ...prev];
            return newLogs.slice(0, maxLogs);
          });
          
          // Update categories if new one found
          if (data.category && !categories.includes(data.category)) {
            setCategories(prev => ['all', ...Array.from(new Set([...prev.slice(1), data.category]))]);
          }
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, [deviceId, isPaused, maxLogs]);

  useEffect(() => {
    // Apply filters
    let filtered = logs;

    // Level filter
    filtered = filtered.filter(log => selectedLevels.includes(log.level));

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(log => log.category === selectedCategory);
    }

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(term) ||
        log.category.toLowerCase().includes(term) ||
        (log.source && log.source.toLowerCase().includes(term)) ||
        (log.metadata && JSON.stringify(log.metadata).toLowerCase().includes(term))
      );
    }

    setFilteredLogs(filtered);
  }, [logs, selectedLevels, selectedCategory, searchTerm]);

  useEffect(() => {
    // Auto-scroll to top when new logs arrive
    if (autoScroll && scrollAreaRef.current && filteredLogs.length > 0) {
      scrollAreaRef.current.scrollTop = 0;
    }
  }, [filteredLogs, autoScroll]);

  const fetchInitialLogs = async () => {
    try {
      const response = await tesaApi.getDeviceLogs({
        deviceId,
        limit: 100,
        levels: selectedLevels
      });
      setLogs(response.logs);
      
      // Extract unique categories
      const uniqueCategories = Array.from(new Set(response.logs.map(log => log.category)));
      setCategories(['all', ...uniqueCategories]);
    } catch (error) {
      console.error('Failed to fetch device logs:', error);
    }
  };

  const handleLevelToggle = (level: string) => {
    setSelectedLevels(prev => {
      if (prev.includes(level)) {
        return prev.filter(l => l !== level);
      }
      return [...prev, level];
    });
  };

  const handleClearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const handleExportLogs = async () => {
    try {
      const response = await tesaApi.exportDeviceLogs({
        deviceId,
        format: 'json',
        logs: filteredLogs
      });
      
      // Create download link
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `device-logs-${deviceId || 'all'}-${format(new Date(), 'yyyyMMdd-HHmmss')}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export logs:', error);
    }
  };

  const handleCopyLog = (log: DeviceLog) => {
    const logText = `[${log.timestamp}] [${log.level.toUpperCase()}] [${log.category}] ${log.message}`;
    navigator.clipboard.writeText(logText);
  };

  const toggleLogExpansion = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  const LogIcon = ({ level }: { level: string }) => {
    const config = LOG_LEVELS[level as keyof typeof LOG_LEVELS];
    const Icon = config.icon;
    return <Icon className={cn("h-4 w-4", config.color)} />;
  };

  return (
    <Card className={cn("flex flex-col", className)} style={{ height }}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Terminal className="h-5 w-5 text-green-500" />
            Device Logs
            {deviceId && (
              <Badge variant="secondary" className="ml-2">
                Device: {deviceId}
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isConnected && (
              <div className="flex items-center gap-1">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs text-gray-500">Live</span>
              </div>
            )}
            <Badge variant="outline" className="text-xs">
              {filteredLogs.length} / {logs.length} logs
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-0">
        {/* Controls */}
        <div className="px-4 pb-4 space-y-3 border-b">
          {/* Search and Actions */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search logs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map(cat => (
                  <SelectItem key={cat} value={cat}>
                    {cat === 'all' ? 'All Categories' : cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsPaused(!isPaused)}
              className="h-9 px-2"
            >
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleExportLogs}
              className="h-9 px-2"
            >
              <Download className="h-4 w-4" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleClearLogs}
              className="h-9 px-2"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>

          {/* Level Filters */}
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Levels:</span>
            <div className="flex items-center gap-2">
              {Object.entries(LOG_LEVELS).map(([level, config]) => (
                <label key={level} className="flex items-center gap-1 cursor-pointer">
                  <Checkbox
                    checked={selectedLevels.includes(level)}
                    onCheckedChange={() => handleLevelToggle(level)}
                  />
                  <span className={cn("text-sm", config.color)}>{level}</span>
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 ml-auto cursor-pointer">
              <Checkbox
                checked={autoScroll}
                onCheckedChange={(checked) => setAutoScroll(checked as boolean)}
              />
              <span className="text-sm">Auto-scroll</span>
            </label>
          </div>
        </div>

        {/* Log Display */}
        <ScrollArea className="flex-1" ref={scrollAreaRef}>
          <div className="p-4 space-y-1 font-mono text-sm">
            {filteredLogs.length > 0 ? (
              filteredLogs.map((log) => {
                const isExpanded = expandedLogs.has(log.id);
                const hasMetadata = log.metadata && Object.keys(log.metadata).length > 0;
                
                return (
                  <div
                    key={log.id}
                    className={cn(
                      "group rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors",
                      LOG_LEVELS[log.level as keyof typeof LOG_LEVELS].bg
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <LogIcon level={log.level} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {log.category}
                          </Badge>
                          {log.source && (
                            <span className="text-xs text-gray-500">
                              [{log.source}]
                            </span>
                          )}
                        </div>
                        <div className="mt-1">
                          <p className="break-all whitespace-pre-wrap">{log.message}</p>
                          {hasMetadata && (
                            <div className="mt-2">
                              <button
                                onClick={() => toggleLogExpansion(log.id)}
                                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                              >
                                <ChevronDown className={cn(
                                  "h-3 w-3 transition-transform",
                                  isExpanded && "rotate-180"
                                )} />
                                Metadata
                              </button>
                              {isExpanded && (
                                <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-x-auto">
                                  {JSON.stringify(log.metadata, null, 2)}
                                </pre>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopyLog(log)}
                        className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center">
                <Terminal className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {logs.length === 0 ? 'No logs available' : 'No logs match the current filters'}
                </p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};