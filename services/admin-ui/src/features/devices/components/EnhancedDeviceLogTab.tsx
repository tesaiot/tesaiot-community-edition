/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Terminal,
  Search,
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
  Shield,
  Wifi,
  Key,
  Activity,
  Filter,
  RefreshCw,
  Settings2,
  Bug
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, formatDistanceToNow } from 'date-fns';
import { CSRWorkflowWidget } from './CSRWorkflowWidget';

// Log level configurations
const LOG_LEVELS = {
  TRACE: { icon: Bug, color: 'text-gray-400', bg: 'bg-gray-50 dark:bg-gray-900' },
  DEBUG: { icon: Terminal, color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-gray-800' },
  INFO: { icon: Info, color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-900/20' },
  WARN: { icon: AlertTriangle, color: 'text-yellow-600', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
  ERROR: { icon: XCircle, color: 'text-red-600', bg: 'bg-red-50 dark:bg-red-900/20' },
  CRITICAL: { icon: AlertCircle, color: 'text-purple-600', bg: 'bg-purple-50 dark:bg-purple-900/20' }
};

// Log category configurations
const LOG_CATEGORIES = {
  security: { icon: Shield, label: 'Security', color: 'text-red-500' },
  mqtt: { icon: Wifi, label: 'MQTT', color: 'text-green-500' },
  csr: { icon: Key, label: 'CSR', color: 'text-blue-500' },
  telemetry: { icon: Activity, label: 'Telemetry', color: 'text-cyan-500' },
  connectivity: { icon: Wifi, label: 'Connectivity', color: 'text-orange-500' },
  system: { icon: Settings2, label: 'System', color: 'text-gray-500' }
};

interface EnhancedDeviceLog {
  _id: string;
  device_id: string;
  timestamp: string;
  level: keyof typeof LOG_LEVELS;
  category: keyof typeof LOG_CATEGORIES;
  source: string;
  event_type: string;
  message: string;
  correlation_id?: string;
  details?: Record<string, any>;
  tags?: string[];
}

interface EnhancedDeviceLogTabProps {
  deviceId: string;
  className?: string;
}

export const EnhancedDeviceLogTab: React.FC<EnhancedDeviceLogTabProps> = ({
  deviceId,
  className
}) => {
  const [logs, setLogs] = useState<EnhancedDeviceLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<EnhancedDeviceLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [isLive, setIsLive] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLevels, setSelectedLevels] = useState<string[]>(['INFO', 'WARN', 'ERROR', 'CRITICAL']);
  const [selectedCategories, setSelectedCategories] = useState<string[]>(Object.keys(LOG_CATEGORIES));
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [correlationFilter, setCorrelationFilter] = useState<string>('');
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [sources, setSources] = useState<string[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [activeTab, setActiveTab] = useState('all');
  const [showFilters, setShowFilters] = useState(false);

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch initial logs
  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        limit: '200',
        levels: selectedLevels.join(','),
        categories: selectedCategories.join(',')
      });

      if (selectedSource !== 'all') {
        params.append('sources', selectedSource);
      }

      const response = await fetch(
        `/api/v1/device-management/logs/${deviceId}/enhanced?${params}`
      );

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setLogs(data.data.logs);
          // Extract unique sources
          const uniqueSources = Array.from(
            new Set(data.data.logs.map((log: EnhancedDeviceLog) => log.source))
          ).filter(Boolean) as string[];
          setSources(uniqueSources);
        }
      }
    } catch (error) {
      console.error('Failed to fetch enhanced logs:', error);
    } finally {
      setLoading(false);
    }
  }, [deviceId, selectedLevels, selectedCategories, selectedSource]);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/v1/device-management/logs/${deviceId}/statistics?hours=24`
      );

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setStats(data.data.by_level);
        }
      }
    } catch (error) {
      console.error('Failed to fetch log statistics:', error);
    }
  }, [deviceId]);

  // WebSocket connection for real-time logs
  useEffect(() => {
    if (!isLive) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/device-management/log-stream/ws?token=${token}`;

    const connect = () => {
      try {
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          // Subscribe to logs for this device
          wsRef.current?.send(JSON.stringify({
            type: 'subscribe',
            device_id: deviceId,
            filters: {
              categories: selectedCategories,
              levels: selectedLevels,
              include_csr_workflow: true
            }
          }));
        };

        wsRef.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'log_event' && message.device_id === deviceId) {
              if (!isPaused) {
                setLogs(prev => [message.log, ...prev].slice(0, 500));
              }
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        wsRef.current.onclose = () => {
          // Reconnect after 5 seconds
          setTimeout(connect, 5000);
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    };

    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [deviceId, isLive, isPaused, selectedCategories, selectedLevels]);

  // Initial data fetch
  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs, fetchStats]);

  // Apply filters
  useEffect(() => {
    let filtered = logs;

    // Level filter
    filtered = filtered.filter(log => selectedLevels.includes(log.level));

    // Category filter
    if (activeTab !== 'all') {
      filtered = filtered.filter(log => log.category === activeTab);
    } else {
      filtered = filtered.filter(log => selectedCategories.includes(log.category));
    }

    // Source filter
    if (selectedSource !== 'all') {
      filtered = filtered.filter(log => log.source === selectedSource);
    }

    // Correlation filter
    if (correlationFilter) {
      filtered = filtered.filter(log =>
        log.correlation_id?.toLowerCase().includes(correlationFilter.toLowerCase())
      );
    }

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(log =>
        log.message.toLowerCase().includes(term) ||
        log.event_type.toLowerCase().includes(term) ||
        (log.details && JSON.stringify(log.details).toLowerCase().includes(term))
      );
    }

    setFilteredLogs(filtered);
  }, [logs, selectedLevels, selectedCategories, selectedSource, correlationFilter, searchTerm, activeTab]);

  const handleLevelToggle = (level: string) => {
    setSelectedLevels(prev =>
      prev.includes(level) ? prev.filter(l => l !== level) : [...prev, level]
    );
  };

  const handleCategoryToggle = (category: string) => {
    setSelectedCategories(prev =>
      prev.includes(category) ? prev.filter(c => c !== category) : [...prev, category]
    );
  };

  const handleClearLogs = () => {
    setLogs([]);
    setFilteredLogs([]);
  };

  const handleExportLogs = async () => {
    try {
      const response = await fetch(
        `/api/v1/device-management/logs/${deviceId}/export?format=json`
      );

      if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `device-logs-${deviceId}-${format(new Date(), 'yyyyMMdd-HHmmss')}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to export logs:', error);
    }
  };

  const handleCopyLog = (log: EnhancedDeviceLog) => {
    const logText = JSON.stringify(log, null, 2);
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

  const LogIcon = ({ level }: { level: keyof typeof LOG_LEVELS }) => {
    const config = LOG_LEVELS[level];
    const Icon = config.icon;
    return <Icon className={cn("h-4 w-4", config.color)} />;
  };

  const CategoryIcon = ({ category }: { category: keyof typeof LOG_CATEGORIES }) => {
    const config = LOG_CATEGORIES[category];
    if (!config) return null;
    const Icon = config.icon;
    return <Icon className={cn("h-3.5 w-3.5", config.color)} />;
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* CSR Workflow Widget */}
      <CSRWorkflowWidget deviceId={deviceId} compact />

      {/* Main Log Viewer */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Terminal className="h-5 w-5 text-green-500" />
              Enhanced Device Logs
              {isLive && !isPaused && (
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs text-gray-500">Live</span>
                </div>
              )}
            </CardTitle>
            <div className="flex items-center gap-2">
              {/* Stats badges */}
              {Object.entries(stats).map(([level, count]) => (
                <Badge
                  key={level}
                  variant="outline"
                  className={cn("text-xs", LOG_LEVELS[level as keyof typeof LOG_LEVELS]?.color)}
                >
                  {level}: {count}
                </Badge>
              ))}
              <Badge variant="outline" className="text-xs">
                {filteredLogs.length} / {logs.length}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Controls */}
          <div className="space-y-3 mb-4">
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
              <Input
                placeholder="Correlation ID..."
                value={correlationFilter}
                onChange={(e) => setCorrelationFilter(e.target.value)}
                className="w-40"
              />
              <Select value={selectedSource} onValueChange={setSelectedSource}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Source" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  {sources.map(source => (
                    <SelectItem key={source} value={source}>{source}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className={cn(showFilters && "bg-gray-100 dark:bg-gray-800")}
              >
                <Filter className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsPaused(!isPaused)}
              >
                {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={fetchLogs}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleExportLogs}
              >
                <Download className="h-4 w-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleClearLogs}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>

            {/* Filter panel */}
            {showFilters && (
              <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-3">
                {/* Level filters */}
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium w-20">Levels:</span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(LOG_LEVELS).map(([level, config]) => (
                      <label key={level} className="flex items-center gap-1.5 cursor-pointer">
                        <Checkbox
                          checked={selectedLevels.includes(level)}
                          onCheckedChange={() => handleLevelToggle(level)}
                        />
                        <span className={cn("text-sm", config.color)}>{level}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Category filters */}
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium w-20">Categories:</span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(LOG_CATEGORIES).map(([category, config]) => (
                      <label key={category} className="flex items-center gap-1.5 cursor-pointer">
                        <Checkbox
                          checked={selectedCategories.includes(category)}
                          onCheckedChange={() => handleCategoryToggle(category)}
                        />
                        <span className={cn("text-sm flex items-center gap-1", config.color)}>
                          <config.icon className="h-3.5 w-3.5" />
                          {config.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Live switch */}
                <div className="flex items-center gap-2">
                  <Switch
                    checked={isLive}
                    onCheckedChange={setIsLive}
                  />
                  <Label>Real-time streaming</Label>
                </div>
              </div>
            )}
          </div>

          {/* Category tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="mb-3">
              <TabsTrigger value="all">All</TabsTrigger>
              {Object.entries(LOG_CATEGORIES).map(([category, config]) => (
                <TabsTrigger key={category} value={category} className="flex items-center gap-1">
                  <config.icon className={cn("h-3.5 w-3.5", config.color)} />
                  {config.label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value={activeTab}>
              {/* Log list */}
              <ScrollArea className="h-[500px]" ref={scrollAreaRef}>
                <div className="space-y-1 font-mono text-sm">
                  {loading ? (
                    <div className="flex items-center justify-center h-64">
                      <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
                    </div>
                  ) : filteredLogs.length > 0 ? (
                    filteredLogs.map((log) => {
                      const isExpanded = expandedLogs.has(log._id);
                      const hasDetails = log.details && Object.keys(log.details).length > 0;
                      const levelConfig = LOG_LEVELS[log.level];

                      return (
                        <div
                          key={log._id}
                          className={cn(
                            "group rounded p-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors border-l-2",
                            levelConfig.bg,
                            log.level === 'ERROR' && "border-l-red-500",
                            log.level === 'WARN' && "border-l-yellow-500",
                            log.level === 'CRITICAL' && "border-l-purple-500",
                            log.level === 'INFO' && "border-l-blue-500",
                            log.level === 'DEBUG' && "border-l-gray-400"
                          )}
                        >
                          <div className="flex items-start gap-2">
                            <LogIcon level={log.level} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs text-gray-500">
                                  {format(new Date(log.timestamp), 'HH:mm:ss.SSS')}
                                </span>
                                <Badge variant="outline" className="text-xs flex items-center gap-1">
                                  <CategoryIcon category={log.category} />
                                  {log.category}
                                </Badge>
                                <span className="text-xs text-gray-500">
                                  [{log.source}]
                                </span>
                                <Badge variant="secondary" className="text-xs">
                                  {log.event_type}
                                </Badge>
                                {log.correlation_id && (
                                  <span className="text-xs text-blue-500 font-mono">
                                    #{log.correlation_id.slice(0, 8)}
                                  </span>
                                )}
                              </div>
                              <div className="mt-1">
                                <p className="break-all whitespace-pre-wrap">{log.message}</p>
                                {hasDetails && (
                                  <div className="mt-2">
                                    <button
                                      onClick={() => toggleLogExpansion(log._id)}
                                      className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                                    >
                                      <ChevronDown className={cn(
                                        "h-3 w-3 transition-transform",
                                        isExpanded && "rotate-180"
                                      )} />
                                      Details
                                    </button>
                                    {isExpanded && (
                                      <pre className="mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-x-auto">
                                        {JSON.stringify(log.details, null, 2)}
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
                      <p className="text-sm text-gray-500">
                        {logs.length === 0 ? 'No logs available' : 'No logs match the current filters'}
                      </p>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default EnhancedDeviceLogTab;
