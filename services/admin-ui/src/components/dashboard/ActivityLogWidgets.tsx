/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import { 
  AlertCircle, 
  Shield, 
  Activity, 
  TrendingUp, 
  TrendingDown,
  Bell,
  CheckCircle,
  Clock,
  Zap,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, formatDistanceToNow } from 'date-fns';
import { tesaApi } from '@/services/api/tesaApi';
import { SEVERITY_COLORS, PHASE1_SEVERITY_LEVELS } from '@/constants/activityLogs';
import { getActivityLogsWebSocket } from '@/services/websocket/activityLogsWebSocket';
import { WS_EVENT_TYPES } from '@/constants/activityLogs';

interface CriticalEvent {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  source: string;
  resolved: boolean;
  acknowledgedBy?: string;
}

export const CriticalEventsMonitor: React.FC = () => {
  const [events, setEvents] = useState<CriticalEvent[]>([]);
  const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCriticalEvents();
    
    // Subscribe to WebSocket updates
    const ws = getActivityLogsWebSocket();
    ws.connect();
    
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.CRITICAL_ALERT, (data) => {
      // Safe access with validation
      if (data?.event) {
        setEvents(prev => [data.event, ...prev].slice(0, 5));
        if (!data.event.resolved) {
          setUnacknowledgedCount(prev => prev + 1);
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const fetchCriticalEvents = async () => {
    try {
      const response = await tesaApi.getCriticalEvents({ limit: 5 });
      // Safe access with fallback
      setEvents(response?.events || []);
      setUnacknowledgedCount(response?.unacknowledgedCount || 0);
    } catch (error) {
      console.error('Failed to fetch critical events:', error);
      // Set safe defaults on error
      setEvents([]);
      setUnacknowledgedCount(0);
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (eventId: string) => {
    if (!eventId) return;
    
    try {
      await tesaApi.acknowledgeCriticalEvent(eventId);
      setEvents(prev => prev.map(event => 
        event?.id === eventId ? { ...event, resolved: true } : event
      ));
      setUnacknowledgedCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Failed to acknowledge event:', error);
      // Could add toast notification here for user feedback
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            Critical Events
          </CardTitle>
          {unacknowledgedCount > 0 && (
            <Badge variant="destructive" className="animate-pulse">
              {unacknowledgedCount} Unresolved
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-16 bg-gray-200 dark:bg-gray-800 rounded-lg" />
                </div>
              ))}
            </div>
          ) : events.length > 0 ? (
            <div className="space-y-3">
              {events.map((event, index) => (
                <div
                  key={event?.id || index}
                  className={cn(
                    "p-3 rounded-lg border transition-all",
                    event?.resolved 
                      ? "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
                      : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {event?.message || 'Unknown Event'}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {event?.timestamp ? formatDistanceToNow(new Date(event.timestamp), { addSuffix: true }) : 'Unknown time'}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          • {event?.source || 'Unknown source'}
                        </span>
                      </div>
                    </div>
                    {!event?.resolved && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleAcknowledge(event?.id)}
                        className="h-7 px-2"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <CheckCircle className="h-12 w-12 text-green-500 mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No critical events
              </p>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export const SecurityAlertsWidget: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSecurityAlerts();
    
    // Subscribe to security alerts
    const ws = getActivityLogsWebSocket();
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.SECURITY_ALERT, (data) => {
      // Safe access with validation
      if (data) {
        setAlerts(prev => [data, ...prev].slice(0, 10));
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const fetchSecurityAlerts = async () => {
    try {
      const response = await tesaApi.getActivityLogs({
        category: 'security',
        severity: 'warning,error,critical',
        limit: 10
      });
      // Safe access with fallback
      setAlerts(response?.data?.logs || []);
    } catch (error) {
      console.error('Failed to fetch security alerts:', error);
      // Set empty array on error to prevent crashes
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="h-5 w-5 text-purple-500" />
          Security Alerts
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {loading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-12 bg-gray-200 dark:bg-gray-800 rounded" />
                </div>
              ))}
            </div>
          ) : alerts && alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.map((alert, index) => (
                <div
                  key={alert?.id || index}
                  className="p-2 rounded border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className={cn(
                        "h-4 w-4",
                        SEVERITY_COLORS[alert?.severity as keyof typeof SEVERITY_COLORS]?.text || "text-gray-500"
                      )} />
                      <span className="text-sm font-medium">{alert?.action || 'Unknown Action'}</span>
                    </div>
                    <Badge variant="secondary" className="text-xs">
                      {alert?.severity || 'unknown'}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {alert?.timestamp ? formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true }) : 'Unknown time'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <Shield className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No security alerts
              </p>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export const ActivityTimelineWidget: React.FC = () => {
  const [activities, setActivities] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecentActivity();
    
    // Subscribe to new logs
    const ws = getActivityLogsWebSocket();
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.LOG_NEW, (data) => {
      // Safe access with validation
      if (data) {
        setActivities(prev => [data, ...prev].slice(0, 20));
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const fetchRecentActivity = async () => {
    try {
      const response = await tesaApi.getRealtimeActivityLogs({ limit: 20 });
      // Safe access with fallback
      setActivities(response?.logs || []);
    } catch (error) {
      console.error('Failed to fetch recent activity:', error);
      // Set empty array on error to prevent crashes
      setActivities([]);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (category: string) => {
    const icons: Record<string, any> = {
      auth: Shield,
      device: Zap,
      user: Activity,
      system: Activity,
      api: Zap
    };
    const Icon = icons[category] || Activity;
    return <Icon className="h-3 w-3" />;
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-5 w-5 text-blue-500" />
          Real-time Activity
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px] pr-4">
          {loading ? (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded" />
                </div>
              ))}
            </div>
          ) : activities && activities.length > 0 ? (
            <div className="space-y-1">
              {activities.map((activity, index) => (
                <div
                  key={activity?.id || index}
                  className="flex items-center gap-2 p-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className={cn(
                    "p-1 rounded",
                    SEVERITY_COLORS[activity?.severity as keyof typeof SEVERITY_COLORS]?.bg || "bg-gray-100 dark:bg-gray-800"
                  )}>
                    {getCategoryIcon(activity?.category || 'system')}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">
                      {activity?.action || 'Unknown Action'}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {activity?.user?.name || 'Unknown User'} • {activity?.timestamp ? format(new Date(activity.timestamp), 'HH:mm:ss') : 'Unknown time'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <Activity className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-3" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No recent activity
              </p>
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export const LogStatsOverview: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    
    // Subscribe to stats updates
    const ws = getActivityLogsWebSocket();
    const unsubscribe = ws.subscribe(WS_EVENT_TYPES.STATS_UPDATE, (data) => {
      // Safe access with validation
      const statsData = data?.stats || null;
      setStats(statsData);
      if (statsData) {
        calculateTrend(statsData);
      }
    });

    const interval = setInterval(fetchStats, 30000); // Refresh every 30 seconds

    return () => {
      unsubscribe();
      clearInterval(interval);
    };
  }, []);

  const fetchStats = async () => {
    try {
      const response = await tesaApi.getActivityLogs({ timeRange: '1h' });
      // Safe access with fallback
      const statsData = response?.data?.stats || null;
      setStats(statsData);
      if (statsData) {
        calculateTrend(statsData);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      // Set null on error to prevent crashes
      setStats(null);
      setTrend('stable');
    } finally {
      setLoading(false);
    }
  };

  const calculateTrend = (statsData: any) => {
    // Enhanced null/undefined checking
    if (!statsData || !statsData.trendsLastHour || !Array.isArray(statsData.trendsLastHour) || statsData.trendsLastHour.length < 2) {
      setTrend('stable');
      return;
    }

    try {
      const recent = statsData.trendsLastHour.slice(-10);
      const older = statsData.trendsLastHour.slice(0, 10);
      
      // Add validation for empty arrays
      if (recent.length === 0 || older.length === 0) {
        setTrend('stable');
        return;
      }
      
      const recentAvg = recent.reduce((sum: number, item: any) => sum + (item?.count || 0), 0) / recent.length;
      const olderAvg = older.reduce((sum: number, item: any) => sum + (item?.count || 0), 0) / older.length;
      
      // Prevent division by zero
      if (olderAvg === 0) {
        setTrend('stable');
        return;
      }
      
      const percentChange = ((recentAvg - olderAvg) / olderAvg) * 100;
      
      if (percentChange > 10) {
        setTrend('up');
      } else if (percentChange < -10) {
        setTrend('down');
      } else {
        setTrend('stable');
      }
    } catch (error) {
      console.error('Error calculating trend:', error);
      setTrend('stable');
    }
  };

  if (loading) {
    return (
      <Card className="h-full">
        <CardContent className="p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded" />
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded" />
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Add error state handling
  if (!stats) {
    return (
      <Card className="h-full">
        <CardHeader className="pb-4">
          <CardTitle className="text-lg">Statistics Overview</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <AlertTriangle className="h-8 w-8 text-amber-500 mb-2" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Unable to load statistics
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Please check your connection and try again
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Statistics Overview</CardTitle>
          <div className="flex items-center gap-2">
            {trend === 'up' && <TrendingUp className="h-4 w-4 text-red-500" />}
            {trend === 'down' && <TrendingDown className="h-4 w-4 text-green-500" />}
            {trend === 'stable' && <Activity className="h-4 w-4 text-gray-500" />}
            <span className="text-sm text-gray-500">Last hour</span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Events</p>
            <p className="text-2xl font-semibold">{stats?.total || 0}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Recent Activity</p>
            <p className="text-2xl font-semibold">{stats?.recentActivity || 0}</p>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Critical</span>
              <span className="text-sm text-gray-500">{stats?.criticalCount || 0}</span>
            </div>
            <Progress 
              value={stats?.total ? (stats.criticalCount || 0) / stats.total * 100 : 0} 
              className="h-2 bg-gray-200 dark:bg-gray-700"
            />
          </div>
          
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Errors</span>
              <span className="text-sm text-gray-500">{stats?.errorCount || 0}</span>
            </div>
            <Progress 
              value={stats?.total ? (stats.errorCount || 0) / stats.total * 100 : 0} 
              className="h-2 bg-gray-200 dark:bg-gray-700"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">Warnings</span>
              <span className="text-sm text-gray-500">{stats?.warningCount || 0}</span>
            </div>
            <Progress 
              value={stats?.total ? (stats.warningCount || 0) / stats.total * 100 : 0} 
              className="h-2 bg-gray-200 dark:bg-gray-700"
            />
          </div>
        </div>

        {stats?.topActions && Array.isArray(stats.topActions) && stats.topActions.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Top Actions</p>
            <div className="space-y-1">
              {stats.topActions.slice(0, 3).map((action: any, index: number) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400 truncate">{action?.action || 'Unknown Action'}</span>
                  <span className="text-gray-500">{action?.count || 0}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};