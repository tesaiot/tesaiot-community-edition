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
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Terminal,
  Wifi,
  WifiOff,
  Play,
  Pause,
  Trash2,
  Download,
  Copy,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Zap,
  Filter,
  ChevronDown,
  ChevronUp,
  Settings,
  RefreshCw,
  FileJson,
  FileText
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { AuthTokenManager } from '@/utils/auth-token-manager';

interface DebugEvent {
  id: string;
  timestamp: string;
  type: 'log' | 'csr' | 'mqtt' | 'security' | 'system';
  level: 'debug' | 'info' | 'warn' | 'error';
  source: string;
  message: string;
  data?: Record<string, any>;
}

interface ConnectionStatus {
  connected: boolean;
  latency?: number;
  lastPing?: string;
  subscriptions?: string[];
}

interface RealtimeDebugConsoleProps {
  deviceId: string;
  className?: string;
}

const EVENT_COLORS = {
  log: { bg: 'bg-gray-50 dark:bg-gray-900', border: 'border-gray-300', icon: 'text-gray-500' },
  csr: { bg: 'bg-blue-50 dark:bg-blue-900/20', border: 'border-blue-300', icon: 'text-blue-500' },
  mqtt: { bg: 'bg-green-50 dark:bg-green-900/20', border: 'border-green-300', icon: 'text-green-500' },
  security: { bg: 'bg-red-50 dark:bg-red-900/20', border: 'border-red-300', icon: 'text-red-500' },
  system: { bg: 'bg-purple-50 dark:bg-purple-900/20', border: 'border-purple-300', icon: 'text-purple-500' }
};

const LEVEL_COLORS = {
  debug: 'text-gray-400',
  info: 'text-blue-500',
  warn: 'text-yellow-500',
  error: 'text-red-500'
};

export const RealtimeDebugConsole: React.FC<RealtimeDebugConsoleProps> = ({
  deviceId,
  className
}) => {
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({ connected: false });
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [showTimestamp, setShowTimestamp] = useState(true);
  const [showSource, setShowSource] = useState(true);
  const [filterTypes, setFilterTypes] = useState<string[]>(['log', 'csr', 'mqtt', 'security', 'system']);
  const [filterLevels, setFilterLevels] = useState<string[]>(['debug', 'info', 'warn', 'error']);
  const [searchTerm, setSearchTerm] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  // Phase 5.2: Historical logs loading state
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [historicalOffset, setHistoricalOffset] = useState(0);
  const [timeRange, setTimeRange] = useState('1h'); // 15m, 1h, 6h, 24h

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const eventIdsRef = useRef<Set<string>>(new Set()); // Track event IDs to prevent duplicates

  // Connect to WebSocket
  const connect = useCallback(() => {
    const token = AuthTokenManager.getToken();
    if (!token) {
      addSystemEvent('error', 'No authentication token found - please log in');
      console.error('RealtimeDebugConsole: No auth token found');
      return;
    }

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/device-logs/${deviceId}?token=${token}`;

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setConnectionStatus(prev => ({ ...prev, connected: true }));
        addSystemEvent('info', 'Connected to debug stream');

        // Subscribe to device logs
        wsRef.current?.send(JSON.stringify({
          type: 'subscribe',
          device_id: deviceId,
          filters: {
            categories: ['security', 'mqtt', 'csr', 'telemetry', 'system', 'connectivity'],
            levels: ['TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'],
            include_csr_workflow: true
          }
        }));

        // Start ping interval
        pingIntervalRef.current = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            const pingTime = Date.now();
            wsRef.current.send(JSON.stringify({ type: 'ping' }));
            // Calculate latency when pong received
          }
        }, 30000);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };

      wsRef.current.onclose = (event) => {
        setConnectionStatus(prev => ({ ...prev, connected: false }));
        addSystemEvent('warn', `Disconnected (code: ${event.code})`);

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
        }

        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          addSystemEvent('info', 'Attempting to reconnect...');
          connect();
        }, 5000);
      };

      wsRef.current.onerror = () => {
        addSystemEvent('error', 'WebSocket error occurred');
      };
    } catch (e) {
      addSystemEvent('error', `Connection failed: ${e}`);
    }
  }, [deviceId]);

  // Handle incoming WebSocket messages
  const handleWebSocketMessage = useCallback((message: any) => {
    if (isPaused) return;

    switch (message.type) {
      case 'connected':
        setConnectionStatus(prev => ({
          ...prev,
          subscriptions: ['device/' + deviceId]
        }));
        break;

      case 'pong':
        setConnectionStatus(prev => ({
          ...prev,
          lastPing: new Date().toISOString(),
          latency: message.latency || undefined
        }));
        break;

      case 'log_event':
        if (message.device_id === deviceId) {
          const log = message.log;
          addEvent({
            id: log._id || `log-${Date.now()}`,
            timestamp: log.timestamp,
            type: mapCategoryToType(log.category),
            level: mapLogLevel(log.level),
            source: log.source,
            message: log.message,
            data: log.details
          });
        }
        break;

      case 'csr_workflow_update':
        if (message.device_id === deviceId) {
          addEvent({
            id: `csr-${Date.now()}`,
            timestamp: new Date().toISOString(),
            type: 'csr',
            level: 'info',
            source: 'csr_workflow',
            message: `CSR Workflow: ${message.workflow.current_step} (${message.workflow.progress_percentage}%)`,
            data: message.workflow
          });
        }
        break;

      case 'error':
        addSystemEvent('error', message.message);
        break;
    }
  }, [deviceId, isPaused]);

  // Map category to event type
  const mapCategoryToType = (category: string): DebugEvent['type'] => {
    switch (category) {
      case 'security': return 'security';
      case 'mqtt': return 'mqtt';
      case 'csr': return 'csr';
      default: return 'log';
    }
  };

  // Map log level
  const mapLogLevel = (level: string): DebugEvent['level'] => {
    switch (level.toUpperCase()) {
      case 'ERROR':
      case 'CRITICAL':
        return 'error';
      case 'WARN':
      case 'WARNING':
        return 'warn';
      case 'DEBUG':
      case 'TRACE':
        return 'debug';
      default:
        return 'info';
    }
  };

  // Phase 5.2: Fetch historical logs from MongoDB
  const fetchHistoricalLogs = useCallback(async (loadMore = false) => {
    setIsLoadingHistory(true);
    try {
      const token = AuthTokenManager.getToken();
      if (!token) {
        console.error('No auth token found for historical logs');
        return;
      }

      // Calculate time range in hours
      const hoursMap: Record<string, number> = {
        '15m': 0.25,
        '1h': 1,
        '6h': 6,
        '24h': 24
      };
      const hours = hoursMap[timeRange] || 1;
      const fromTime = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();

      const offset = loadMore ? historicalOffset : 0;
      const limit = 100;

      const params = new URLSearchParams({
        limit: limit.toString(),
        skip: offset.toString()  // API uses 'skip' not 'offset'
      });

      const response = await fetch(
        `/api/v1/devices/${deviceId}/logs/enhanced?${params}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to load historical logs: ${response.statusText}`);
      }

      const result = await response.json();
      // API returns { logs: [...] } directly, not { data: { logs: [...] } }
      const historicalLogs = result.logs || [];

      // Convert API format to DebugEvent format
      const convertedEvents: DebugEvent[] = historicalLogs
        .filter((log: any) => !eventIdsRef.current.has(log._id)) // Prevent duplicates
        .map((log: any) => ({
          id: log._id,
          timestamp: log.timestamp,
          type: mapCategoryToType(log.category),
          level: mapLogLevel(log.level),
          source: log.source,
          message: log.message,
          data: log.details
        }));

      // Add to event IDs set
      convertedEvents.forEach(event => eventIdsRef.current.add(event.id));

      if (loadMore) {
        setEvents(prev => [...prev, ...convertedEvents]);
      } else {
        setEvents(convertedEvents);
      }

      setHistoricalOffset(offset + convertedEvents.length);
      setHasMoreHistory(historicalLogs.length === limit);

      if (!loadMore && convertedEvents.length > 0) {
        addSystemEvent('info', `Loaded ${convertedEvents.length} historical logs (${timeRange})`);
      }
    } catch (error) {
      console.error('Error fetching historical logs:', error);
      addSystemEvent('error', `Failed to load historical logs: ${error}`);
    } finally {
      setIsLoadingHistory(false);
    }
  }, [deviceId, timeRange, historicalOffset]);

  // Add event to list (prevent duplicates with eventIdsRef)
  const addEvent = useCallback((event: DebugEvent) => {
    if (eventIdsRef.current.has(event.id)) {
      return; // Skip duplicate events from WebSocket
    }
    eventIdsRef.current.add(event.id);
    setEvents(prev => {
      const newEvents = [event, ...prev].slice(0, 1000);
      return newEvents;
    });
  }, []);

  // Add system event
  const addSystemEvent = useCallback((level: DebugEvent['level'], message: string) => {
    addEvent({
      id: `sys-${Date.now()}`,
      timestamp: new Date().toISOString(),
      type: 'system',
      level,
      source: 'console',
      message
    });
  }, [addEvent]);

  // Phase 5.2: Load historical logs on mount and when timeRange changes
  useEffect(() => {
    fetchHistoricalLogs(false);
  }, [deviceId, timeRange]);

  // Initialize connection
  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
    };
  }, [connect]);

  // Auto scroll
  useEffect(() => {
    if (autoScroll && scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = 0;
    }
  }, [events, autoScroll]);

  // Filter events
  const filteredEvents = events.filter(event => {
    if (!filterTypes.includes(event.type)) return false;
    if (!filterLevels.includes(event.level)) return false;
    if (searchTerm && !event.message.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false;
    }
    return true;
  });

  const handleClearConsole = () => {
    setEvents([]);
    addSystemEvent('info', 'Console cleared');
  };

  // Phase 5.3: Export to JSON
  const handleExportJSON = () => {
    const exportData = {
      device_id: deviceId,
      exported_at: new Date().toISOString(),
      events: filteredEvents
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debug-console-${deviceId}-${format(new Date(), 'yyyyMMdd-HHmmss')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Phase 5.3: Export to CSV
  const handleExportCSV = () => {
    // CSV header
    const headers = ['timestamp', 'level', 'type', 'source', 'message', 'details'];
    const csvRows = [headers.join(',')];

    // CSV data rows
    filteredEvents.forEach(event => {
      const row = [
        event.timestamp,
        event.level,
        event.type,
        event.source,
        `"${event.message.replace(/"/g, '""')}"`, // Escape quotes in message
        event.data ? `"${JSON.stringify(event.data).replace(/"/g, '""')}"` : ''
      ];
      csvRows.push(row.join(','));
    });

    const csvContent = csvRows.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debug-console-${deviceId}-${format(new Date(), 'yyyyMMdd-HHmmss')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyEvent = (event: DebugEvent) => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
  };

  const toggleTypeFilter = (type: string) => {
    setFilterTypes(prev =>
      prev.includes(type) ? prev.filter(t => t !== type) : [...prev, type]
    );
  };

  const toggleLevelFilter = (level: string) => {
    setFilterLevels(prev =>
      prev.includes(level) ? prev.filter(l => l !== level) : [...prev, level]
    );
  };

  const LevelIcon = ({ level }: { level: string }) => {
    switch (level) {
      case 'error': return <XCircle className="h-3.5 w-3.5 text-red-500" />;
      case 'warn': return <AlertTriangle className="h-3.5 w-3.5 text-yellow-500" />;
      case 'info': return <CheckCircle className="h-3.5 w-3.5 text-blue-500" />;
      default: return <Terminal className="h-3.5 w-3.5 text-gray-400" />;
    }
  };

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Terminal className="h-5 w-5 text-green-500" />
            Real-time Debug Console
            <Badge variant={connectionStatus.connected ? "default" : "destructive"} className="ml-2">
              {connectionStatus.connected ? (
                <><Wifi className="h-3 w-3 mr-1" /> Connected</>
              ) : (
                <><WifiOff className="h-3 w-3 mr-1" /> Disconnected</>
              )}
            </Badge>
          </CardTitle>
          <div className="flex items-center gap-2">
            {connectionStatus.latency !== undefined && (
              <Badge variant="outline" className="text-xs">
                <Zap className="h-3 w-3 mr-1" />
                {connectionStatus.latency}ms
              </Badge>
            )}
            <Badge variant="outline" className="text-xs">
              {filteredEvents.length} events
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* Toolbar */}
        <div className="px-4 py-2 border-b flex items-center gap-2">
          <div className="relative flex-1">
            <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Filter events..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 h-8"
            />
          </div>

          {/* Phase 5.2: Time range selector */}
          <div className="flex items-center gap-1 border-r pr-2">
            <Clock className="h-3.5 w-3.5 text-gray-500" />
            {['15m', '1h', '6h', '24h'].map((range) => (
              <Button
                key={range}
                size="sm"
                variant={timeRange === range ? "default" : "ghost"}
                onClick={() => setTimeRange(range)}
                className="h-7 px-2 text-xs"
              >
                {range}
              </Button>
            ))}
          </div>

          <div className="flex items-center gap-1">
            {Object.entries(EVENT_COLORS).map(([type, colors]) => (
              <Button
                key={type}
                size="sm"
                variant={filterTypes.includes(type) ? "default" : "ghost"}
                onClick={() => toggleTypeFilter(type)}
                className={cn("h-7 px-2 text-xs", filterTypes.includes(type) && colors.icon)}
              >
                {type}
              </Button>
            ))}
          </div>

          <Separator orientation="vertical" className="h-6" />

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsPaused(!isPaused)}
            className="h-7 px-2"
          >
            {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowSettings(!showSettings)}
            className={cn("h-7 px-2", showSettings && "bg-gray-100 dark:bg-gray-800")}
          >
            <Settings className="h-4 w-4" />
          </Button>

          {/* Phase 5.3: Export dropdown (JSON/CSV) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2"
              >
                <Download className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleExportJSON}>
                <FileJson className="h-4 w-4 mr-2" />
                Export as JSON
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleExportCSV}>
                <FileText className="h-4 w-4 mr-2" />
                Export as CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Button
            size="sm"
            variant="ghost"
            onClick={handleClearConsole}
            className="h-7 px-2"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Settings panel */}
        {showSettings && (
          <div className="px-4 py-2 bg-gray-50 dark:bg-gray-900 border-b flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Switch checked={autoScroll} onCheckedChange={setAutoScroll} />
              <Label className="text-xs">Auto-scroll</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={showTimestamp} onCheckedChange={setShowTimestamp} />
              <Label className="text-xs">Timestamps</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={showSource} onCheckedChange={setShowSource} />
              <Label className="text-xs">Source</Label>
            </div>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-500 mr-1">Levels:</span>
              {Object.entries(LEVEL_COLORS).map(([level, color]) => (
                <Button
                  key={level}
                  size="sm"
                  variant={filterLevels.includes(level) ? "default" : "ghost"}
                  onClick={() => toggleLevelFilter(level)}
                  className={cn("h-6 px-2 text-xs", filterLevels.includes(level) && color)}
                >
                  {level}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Console output */}
        <ScrollArea className="flex-1 bg-gray-900 text-gray-100" ref={scrollAreaRef}>
          <div className="p-2 font-mono text-xs space-y-0.5">
            {/* Phase 5.2: Loading skeleton for initial load */}
            {isLoadingHistory && events.length === 0 ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex items-start gap-2 px-2 py-1">
                    <div className="h-3.5 w-3.5 bg-gray-700 rounded animate-pulse" />
                    <div className="flex-1 space-y-1">
                      <div className="h-3 bg-gray-700 rounded w-24 animate-pulse" />
                      <div className="h-3 bg-gray-700 rounded w-full animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredEvents.length > 0 ? (
              <>
                {filteredEvents.map((event) => {
                const typeColors = EVENT_COLORS[event.type] || EVENT_COLORS.log;
                const levelColor = LEVEL_COLORS[event.level] || LEVEL_COLORS.info;

                return (
                  <div
                    key={event.id}
                    className={cn(
                      "group flex items-start gap-2 px-2 py-1 rounded hover:bg-gray-800 transition-colors",
                      event.level === 'error' && "bg-red-900/20",
                      event.level === 'warn' && "bg-yellow-900/20"
                    )}
                  >
                    <LevelIcon level={event.level} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        {showTimestamp && (
                          <span className="text-gray-500">
                            [{format(new Date(event.timestamp), 'HH:mm:ss.SSS')}]
                          </span>
                        )}
                        <Badge
                          variant="outline"
                          className={cn("text-[10px] h-4 px-1", typeColors.icon)}
                        >
                          {event.type}
                        </Badge>
                        {showSource && event.source && (
                          <span className="text-gray-500">[{event.source}]</span>
                        )}
                      </div>
                      <p className={cn("mt-0.5", levelColor)}>{event.message}</p>
                      {event.data && (
                        <pre className="mt-1 text-[10px] text-gray-400 overflow-x-auto">
                          {JSON.stringify(event.data, null, 2)}
                        </pre>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopyEvent(event)}
                      className="h-5 w-5 p-0 opacity-0 group-hover:opacity-100"
                    >
                      <Copy className="h-3 w-3 text-gray-400" />
                    </Button>
                  </div>
                );
              })}

              {/* Phase 5.2: Load More button */}
              {hasMoreHistory && !isLoadingHistory && (
                <div className="flex justify-center py-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => fetchHistoricalLogs(true)}
                    className="bg-gray-800 border-gray-700 hover:bg-gray-700 text-gray-300"
                  >
                    <ChevronDown className="h-4 w-4 mr-1" />
                    Load More
                  </Button>
                </div>
              )}

              {/* Loading indicator for Load More */}
              {isLoadingHistory && events.length > 0 && (
                <div className="flex justify-center py-3">
                  <RefreshCw className="h-4 w-4 text-gray-500 animate-spin" />
                </div>
              )}
            </>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-gray-500">
                <Terminal className="h-8 w-8 mb-2" />
                <p>Waiting for events...</p>
                <p className="text-xs mt-1">Device: {deviceId}</p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Status bar */}
        <div className="px-4 py-1.5 border-t bg-gray-50 dark:bg-gray-900 flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>Device: {deviceId}</span>
            {connectionStatus.lastPing && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Last ping: {format(new Date(connectionStatus.lastPing), 'HH:mm:ss')}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isPaused && (
              <Badge variant="secondary" className="text-[10px]">PAUSED</Badge>
            )}
            <span>{events.length} total events</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default RealtimeDebugConsole;
