/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { ReactNode, useState, useCallback, useEffect, useMemo } from 'react';
import { Calendar, Settings, Settings2, Shield, Users, Bell, Volume2, VolumeX, Archive, Eye, Zap, Brain, AlertTriangle, Cpu, TrendingUp, Activity, Bot, Sparkles } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { tesaApi } from '@/services/api/tesaApi';
import { useToast } from '@/hooks/use-toast';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuth } from '@/hooks/useAuth';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { formatDistanceToNow, isToday, isYesterday, isThisWeek } from 'date-fns';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuPortal,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { NotificationItem } from './notifications/NotificationItem';
import { AuthTokenManager } from '@/utils/auth-token-manager';
// Notification type definitions
type NotificationType = 'system' | 'ai_ml' | 'security' | 'device' | 'maintenance' | 'user' | 'personal';
type NotificationCategory = 'System' | 'AI/ML' | 'Security' | 'Device';

interface NotificationData {
  id: string;
  type: NotificationType;
  category: NotificationCategory;
  title: string;
  message: string;
  status: 'read' | 'unread';
  priority: 'low' | 'medium' | 'high' | 'critical';
  archived: boolean;
  created_at: string;
  read_at?: string;
  archived_at?: string;
  actions?: Array<{
    label: string;
    action: string;
    variant?: 'default' | 'destructive' | 'outline';
  }>;
  metadata?: {
    model_name?: string;
    accuracy?: number;
    anomaly_score?: number;
    device_id?: string;
    threshold?: number;
    suggestion?: string;
    optimization_type?: string;
  };
}

interface NotificationStyleConfig {
  icon: LucideIcon;
  gradient: string;
  bgGradient: string;
  borderColor: string;
  iconColor: string;
}

type RawNotification = Omit<NotificationData, 'category'> & Partial<Pick<NotificationData, 'category'>>;

type NotificationEvent =
  | { type: 'notification'; data: RawNotification }
  | { type: 'init' | 'refresh'; notifications: RawNotification[]; unread_count?: number }
  | { type: 'ack'; action: string; notification_id?: string; affected?: number; success?: boolean }
  | { type: 'error'; code: string; message: string }
  | { type: 'pong'; timestamp: string };

interface NotificationsSheetProps {
  trigger?: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function NotificationsSheet({ trigger, open, onOpenChange }: NotificationsSheetProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [notifications, setNotifications] = useState<NotificationData[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<NotificationCategory | 'All'>('All');
  const [unreadCount, setUnreadCount] = useState(0);
  const { toast } = useToast();
  const { isAuthenticated } = useAuth();
  const notificationsWsEnabled = import.meta.env.VITE_NOTIFICATIONS_WS_ENABLED === 'true';

  // WebSocket connection for real-time notifications
  const wsUrl = useMemo(() => {
    if (!notificationsWsEnabled) {
      return null;
    }
    if (!isAuthenticated) {
      return null;
    }
    if (typeof window === 'undefined') {
      return null;
    }
    const token = AuthTokenManager.getToken();
    if (!token) {
      return null;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = new URL(`${protocol}//${window.location.host}/ws/notifications`);
    url.searchParams.set('token', token);
    return url.toString();
  }, [isAuthenticated, notificationsWsEnabled]);

  const { data: wsData, isConnected } = useWebSocket<NotificationEvent>(wsUrl);
  
  // Notification sound
  const playNotificationSound = useCallback(() => {
    if (soundEnabled) {
      const audio = new Audio('/notification-sound.mp3');
      audio.volume = 0.5;
      audio.play().catch(console.error);
    }
  }, [soundEnabled]);

  // Notification type configurations
  const notificationTypeConfig: Record<NotificationType, NotificationStyleConfig> = {
    ai_ml: {
      icon: Brain,
      gradient: 'from-purple-500 to-pink-500',
      bgGradient: 'bg-gradient-to-r from-purple-500/10 to-pink-500/10',
      borderColor: 'border-purple-500/20',
      iconColor: 'text-purple-600'
    },
    system: {
      icon: Cpu,
      gradient: 'from-blue-500 to-cyan-500',
      bgGradient: 'bg-gradient-to-r from-blue-500/10 to-cyan-500/10',
      borderColor: 'border-blue-500/20',
      iconColor: 'text-blue-600'
    },
    security: {
      icon: Shield,
      gradient: 'from-red-500 to-orange-500',
      bgGradient: 'bg-gradient-to-r from-red-500/10 to-orange-500/10',
      borderColor: 'border-red-500/20',
      iconColor: 'text-red-600'
    },
    device: {
      icon: Activity,
      gradient: 'from-green-500 to-emerald-500',
      bgGradient: 'bg-gradient-to-r from-green-500/10 to-emerald-500/10',
      borderColor: 'border-green-500/20',
      iconColor: 'text-green-600'
    },
    maintenance: {
      icon: AlertTriangle,
      gradient: 'from-yellow-500 to-amber-500',
      bgGradient: 'bg-gradient-to-r from-yellow-500/10 to-amber-500/10',
      borderColor: 'border-yellow-500/20',
      iconColor: 'text-yellow-600'
    },
    user: {
      icon: Users,
      gradient: 'from-indigo-500 to-purple-500',
      bgGradient: 'bg-gradient-to-r from-indigo-500/10 to-purple-500/10',
      borderColor: 'border-indigo-500/20',
      iconColor: 'text-indigo-600'
    },
    personal: {
      icon: Bell,
      gradient: 'from-gray-500 to-slate-500',
      bgGradient: 'bg-gradient-to-r from-gray-500/10 to-slate-500/10',
      borderColor: 'border-gray-500/20',
      iconColor: 'text-gray-600'
    }
  };

  type NotificationStyleConfig = typeof notificationTypeConfig[keyof typeof notificationTypeConfig];

  // Helper function to get category from type
  const getNotificationCategory = useCallback((type: NotificationType): NotificationCategory => {
    switch (type) {
      case 'ai_ml':
        return 'AI/ML';
      case 'system':
        return 'System';
      case 'security':
        return 'Security';
      case 'device':
      case 'maintenance':
        return 'Device';
      default:
        return 'System';
    }
  }, []);

  // Fetch notifications from API
  const fetchNotifications = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await tesaApi.getNotifications({ status: 'all' });
      const enrichedNotifications: NotificationData[] = (response.notifications || []).map((notification: RawNotification) => ({
        ...notification,
        category: getNotificationCategory((notification.type ?? 'system') as NotificationType)
      }));
      setNotifications(enrichedNotifications);
      
      // Update unread count
      const unread = enrichedNotifications.filter((n: NotificationData) => n.status === 'unread').length;
      setUnreadCount(unread);
    } catch (error) {
      console.error('Error fetching notifications:', error);
      toast({
        title: 'Error',
        description: 'Failed to load notifications',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast, getNotificationCategory]);

  const handleArchiveNotification = useCallback(async (notificationId: string) => {
    try {
      const response = await tesaApi.updateNotification(notificationId, { action: 'archive' });
      if (response.success) {
        setNotifications(prev => prev.filter(n => n.id !== notificationId));
        toast({
          title: 'Success',
          description: 'Notification archived',
        });
      }
    } catch (error) {
      console.error('Error archiving notification:', error);
      toast({
        title: 'Error',
        description: 'Failed to archive notification',
        variant: 'destructive',
      });
    }
  }, [toast]);

  // Handle notification actions
  const handleNotificationAction = useCallback(async (notification: NotificationData, action: string) => {
    switch (action) {
      case 'view':
        // Navigate to relevant page based on notification type
        if (notification.type === 'ai_ml' && notification.metadata?.model_name) {
          window.location.href = `/ai/models/${notification.metadata.model_name}`;
        } else if (notification.type === 'device' && notification.metadata?.device_id) {
          window.location.href = `/devices/${notification.metadata.device_id}`;
        } else if (notification.type === 'security') {
          window.location.href = '/security/incidents';
        }
        break;
      case 'dismiss':
        await handleArchiveNotification(notification.id);
        break;
      case 'archive':
        await handleArchiveNotification(notification.id);
        break;
      default:
        console.log('Unknown action:', action);
    }
  }, [handleArchiveNotification]);

  // Handle WebSocket notifications
  useEffect(() => {
    if (!wsData) {
      return;
    }

    if (wsData.type === 'notification' && wsData.data) {
      const enriched: NotificationData = {
        ...wsData.data,
        category: getNotificationCategory(wsData.data.type as NotificationType)
      };
      setNotifications(prev => [enriched, ...prev]);

      if (enriched.status === 'unread') {
        setUnreadCount(prev => prev + 1);
        playNotificationSound();

        if (
          enriched.type === 'ai_ml' &&
          (enriched.priority === 'high' || enriched.priority === 'critical')
        ) {
          toast({
            title: enriched.title,
            description: enriched.message,
            action: (
              <Button size="sm" variant="outline" onClick={() => handleNotificationAction(enriched, 'view')}>
                View Details
              </Button>
            ),
          });
        }
      }
    } else if (wsData.type === 'init' || wsData.type === 'refresh') {
      const enrichedList: NotificationData[] = (wsData.notifications || []).map((n) => ({
        ...n,
        category: getNotificationCategory(n.type as NotificationType)
      }));
      setNotifications(enrichedList);
      const unread = wsData.unread_count ?? enrichedList.filter(n => n.status === 'unread').length;
      setUnreadCount(unread);
    } else if (wsData.type === 'error') {
      toast({
        title: 'Notification stream error',
        description: wsData.message,
        variant: 'destructive'
      });
    }
  }, [wsData, playNotificationSound, toast, handleNotificationAction, getNotificationCategory]);

  // Fetch notifications on mount and when refreshKey changes
  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications, refreshKey]);

  const handleArchiveAll = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await tesaApi.bulkNotificationAction({
        action: 'archiveAll'
      });
      
      if (response.success) {
        toast({
          title: 'Success',
          description: response.message || 'All notifications archived',
        });
        // Force refresh of the notifications list
        setRefreshKey(prev => prev + 1);
        // Clear notifications from the UI
        setNotifications([]);
      } else {
        toast({
          title: 'Error',
          description: 'Failed to archive notifications',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error archiving all notifications:', error);
      toast({
        title: 'Error',
        description: 'Failed to archive notifications',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  const handleMarkAllAsRead = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await tesaApi.bulkNotificationAction({
        action: 'markAllRead'
      });
      
      if (response.success) {
        toast({
          title: 'Success',
          description: response.message || 'All notifications marked as read',
        });
        // Force refresh of the notifications list
        setRefreshKey(prev => prev + 1);
        // Update local state to mark all as read
        setNotifications(prev => prev.map(n => ({ ...n, status: 'read' })));
      } else {
        toast({
          title: 'Error',
          description: 'Failed to mark notifications as read',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Error marking all as read:', error);
      toast({
        title: 'Error',
        description: 'Failed to mark notifications as read',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast]);

  const handleNotificationClick = useCallback(async (notification: NotificationData) => {
    if (notification.status === 'unread') {
      try {
        const response = await tesaApi.markNotificationAsRead(notification.id);
        if (response.success) {
          // Update local state
          setNotifications(prev => 
            prev.map(n => n.id === notification.id ? { ...n, status: 'read' } : n)
          );
          setUnreadCount(prev => Math.max(0, prev - 1));
        }
      } catch (error) {
        console.error('Error marking notification as read:', error);
      }
    }
  }, []);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      {trigger && <SheetTrigger asChild>{trigger}</SheetTrigger>}
      <SheetContent className="p-0 gap-0 sm:w-[500px] sm:max-w-none inset-5 start-auto h-auto rounded-lg p-0 sm:max-w-none [&_[data-slot=sheet-close]]:top-4.5 [&_[data-slot=sheet-close]]:end-5">
        <SheetHeader className="mb-0">
          <SheetTitle className="p-3 flex items-center gap-2">
            Notifications
            {unreadCount > 0 && (
              <Badge variant="secondary" className="px-2 py-0 text-xs font-medium">
                {unreadCount}
              </Badge>
            )}
          </SheetTitle>
        </SheetHeader>
        <SheetBody className="grow p-0">
          <ScrollArea className="h-[calc(100vh-10.5rem)]">
            {/* WebSocket connection status */}
            {notificationsWsEnabled && !isConnected && (
              <div className="px-5 py-2 bg-yellow-50 dark:bg-yellow-900/10 border-b border-yellow-200 dark:border-yellow-800">
                <div className="flex items-center gap-2 text-sm text-yellow-800 dark:text-yellow-200">
                  <Zap className="w-4 h-4" />
                  <span>Real-time updates are currently offline</span>
                </div>
              </div>
            )}
            
            {/* Notification sound toggle */}
            <div className="px-5 py-3 border-b flex items-center justify-between">
              <div className="flex items-center gap-2">
                {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                <span className="text-sm">Notification sounds</span>
              </div>
              <Switch
                checked={soundEnabled}
                onCheckedChange={setSoundEnabled}
                aria-label="Toggle notification sounds"
              />
            </div>
            
            {/* Category filters */}
            <div className="px-5 py-3 border-b">
              <div className="flex gap-2 flex-wrap">
                {(['All', 'System', 'AI/ML', 'Security', 'Device'] as const).map((category) => {
                  const count = category === 'All' 
                    ? notifications.length 
                    : notifications.filter(n => n.category === category).length;
                  
                  return (
                    <Button
                      key={category}
                      variant={selectedCategory === category ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setSelectedCategory(category)}
                      className={cn(
                        'relative',
                        selectedCategory === category && category === 'AI/ML' && 
                        'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white border-0'
                      )}
                    >
                      {category}
                      {count > 0 && (
                        <Badge 
                          variant="secondary" 
                          className="ml-2 px-1.5 py-0 h-5 min-w-[20px] text-xs"
                        >
                          {count}
                        </Badge>
                      )}
                    </Button>
                  );
                })}
              </div>
            </div>
            
            <Tabs defaultValue="all" className="w-full relative">
              <TabsList className="w-full px-5 mb-5">
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="inbox" className="relative">
                  Inbox
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500 absolute top-1 -end-1" />
                </TabsTrigger>
                <TabsTrigger value="team">Team</TabsTrigger>
                <TabsTrigger value="following">Following</TabsTrigger>
                <div className="grow flex items-center justify-end">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        mode="icon"
                        className="mb-1"
                      >
                        <Settings className="size-4.5!" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      className="w-44"
                      side="bottom"
                      align="end"
                    >
                      <DropdownMenuItem asChild>
                        <Link to="/account/members/teams">
                          <Users /> Invite Users
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuSub>
                        <DropdownMenuSubTrigger>
                          <Settings2 />
                          <span>Team Settings</span>
                        </DropdownMenuSubTrigger>
                        <DropdownMenuPortal>
                          <DropdownMenuSubContent className="w-44">
                            <DropdownMenuItem asChild>
                              <Link to="/account/members/import-members">
                                <Shield />
                                Find Members
                              </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem asChild>
                              <Link to="/account/members/import-members">
                                <Calendar /> Meetings
                              </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem asChild>
                              <Link to="/account/members/import-members">
                                <Shield /> Group Settings
                              </Link>
                            </DropdownMenuItem>
                          </DropdownMenuSubContent>
                        </DropdownMenuPortal>
                      </DropdownMenuSub>
                      <DropdownMenuItem asChild>
                        <Link to="/account/security/privacy-settings">
                          <Shield /> Group Settings
                        </Link>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </TabsList>

              {/* All Tab */}
              <TabsContent value="all" className="mt-0">
                <div className="flex flex-col overflow-y-auto">
                  {(() => {
                    // Filter notifications by category
                    const filteredNotifications = selectedCategory === 'All' 
                      ? notifications 
                      : notifications.filter(n => n.category === selectedCategory);
                    
                    // Group notifications by time
                    const groupedNotifications = filteredNotifications.reduce((groups, notification) => {
                      const date = new Date(notification.created_at);
                      let group = 'Older';
                      
                      if (isToday(date)) {
                        group = 'Today';
                      } else if (isYesterday(date)) {
                        group = 'Yesterday';
                      } else if (isThisWeek(date)) {
                        group = 'This Week';
                      }
                      
                      if (!groups[group]) {
                        groups[group] = [];
                      }
                      groups[group].push(notification);
                      return groups;
                    }, {} as Record<string, NotificationData[]>);
                    
                    // Sort notifications by AI-powered prioritization
                    const prioritizeNotifications = (notifications: NotificationData[]) => {
                      return notifications.sort((a, b) => {
                        // Priority order: critical > high > medium > low
                        const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                        const aPriority = priorityOrder[a.priority] ?? 4;
                        const bPriority = priorityOrder[b.priority] ?? 4;
                        
                        if (aPriority !== bPriority) return aPriority - bPriority;
                        
                        // Then by unread status
                        if (a.status !== b.status) return a.status === 'unread' ? -1 : 1;
                        
                        // Then by date
                        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
                      });
                    };
                    
                    if (filteredNotifications.length === 0 && !isLoading) {
                      return (
                        <div className="text-center py-8 text-muted-foreground">
                          <Bell className="w-12 h-12 mx-auto mb-3 opacity-20" />
                          <p>No {selectedCategory !== 'All' ? selectedCategory : ''} notifications</p>
                        </div>
                      );
                    }
                    
                    return (
                      <>
                        {['Today', 'Yesterday', 'This Week', 'Older'].map(group => {
                          if (!groupedNotifications[group] || groupedNotifications[group].length === 0) {
                            return null;
                          }
                          
                          return (
                            <div key={group}>
                              <div className="px-5 py-2 bg-muted/50 sticky top-0 z-10">
                                <h3 className="text-sm font-medium text-muted-foreground">{group}</h3>
                              </div>
                              {prioritizeNotifications(groupedNotifications[group]).map((notification) => (
                                <NotificationCard
                                  key={notification.id}
                                  notification={notification}
                                  config={notificationTypeConfig[notification.type]}
                                  onClick={() => handleNotificationClick(notification)}
                                  onAction={(action) => handleNotificationAction(notification, action)}
                                />
                              ))}
                            </div>
                          );
                        })}
                      </>
                    );
                  })()}
                </div>
              </TabsContent>

              {/* Inbox Tab */}
              <TabsContent value="inbox" className="mt-0">
                <div className="flex flex-col overflow-y-auto">
                  {notifications.filter(n => n.status === 'unread').length === 0 && !isLoading ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No unread notifications</p>
                    </div>
                  ) : (
                    notifications
                      .filter(n => n.status === 'unread')
                      .map((notification) => (
                        <NotificationItem
                          key={notification.id}
                          notification={notification}
                          onClick={() => handleNotificationClick(notification)}
                        />
                      ))
                  )}
                </div>
              </TabsContent>

              {/* Team Tab */}
              <TabsContent value="team" className="mt-0">
                <div className="flex flex-col overflow-y-auto">
                  {notifications.filter(n => ['device', 'maintenance'].includes(n.type)).length === 0 && !isLoading ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No team notifications</p>
                    </div>
                  ) : (
                    notifications
                      .filter(n => ['device', 'maintenance'].includes(n.type))
                      .map((notification) => (
                        <NotificationItem
                          key={notification.id}
                          notification={notification}
                          onClick={() => handleNotificationClick(notification)}
                        />
                      ))
                  )}
                </div>
              </TabsContent>

              {/* Following Tab */}
              <TabsContent value="following" className="mt-0">
                <div className="flex flex-col overflow-y-auto">
                  {notifications.filter(n => n.type === 'personal' || n.type === 'user').length === 0 && !isLoading ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <p>No personal notifications</p>
                    </div>
                  ) : (
                    notifications
                      .filter(n => n.type === 'personal' || n.type === 'user')
                      .map((notification) => (
                        <NotificationItem
                          key={notification.id}
                          notification={notification}
                          onClick={() => handleNotificationClick(notification)}
                        />
                      ))
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </ScrollArea>
        </SheetBody>
        <SheetFooter className="border-t border-border p-5 grid grid-cols-2 gap-2.5">
          <Button 
            variant="outline" 
            onClick={handleArchiveAll}
            disabled={isLoading}
          >
            {isLoading ? 'Archiving...' : 'Archive all'}
          </Button>
          <Button 
            variant="outline" 
            onClick={handleMarkAllAsRead}
            disabled={isLoading}
          >
            {isLoading ? 'Marking...' : 'Mark all as read'}
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

// Enhanced Notification Card Component
function NotificationCard({ 
  notification, 
  config, 
  onClick, 
  onAction 
}: { 
  notification: NotificationData;
  config: NotificationStyleConfig;
  onClick: () => void;
  onAction: (action: string) => void;
}) {
  const Icon = config.icon;
  
  return (
    <div
      className={cn(
        'group relative p-4 border-b transition-all duration-200',
        'hover:shadow-sm cursor-pointer',
        notification.status === 'unread' && 'bg-background',
        config.bgGradient,
        config.borderColor,
        'border-l-4'
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* Icon with gradient background */}
        <div className={cn(
          'relative flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
          'bg-gradient-to-br',
          config.gradient,
          'shadow-sm'
        )}>
          <Icon className="w-5 h-5 text-white" />
          {notification.type === 'ai_ml' && (
            <Sparkles className="absolute -top-1 -right-1 w-3 h-3 text-yellow-400" />
          )}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <h4 className={cn(
                'text-sm font-medium mb-1',
                notification.status === 'unread' && 'font-semibold'
              )}>
                {notification.title}
              </h4>
              <p className="text-sm text-muted-foreground line-clamp-2">
                {notification.message}
              </p>
              
              {/* AI/ML specific metadata */}
              {notification.type === 'ai_ml' && notification.metadata && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {notification.metadata.model_name && (
                    <Badge variant="secondary" className="text-xs">
                      <Bot className="w-3 h-3 mr-1" />
                      {notification.metadata.model_name}
                    </Badge>
                  )}
                  {notification.metadata.accuracy && (
                    <Badge variant="secondary" className="text-xs">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      {notification.metadata.accuracy}% accuracy
                    </Badge>
                  )}
                  {notification.metadata.anomaly_score && (
                    <Badge 
                      variant="secondary" 
                      className={cn(
                        'text-xs',
                        notification.metadata.anomaly_score > 0.8 && 'bg-red-100 text-red-800'
                      )}
                    >
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Anomaly: {(notification.metadata.anomaly_score * 100).toFixed(0)}%
                    </Badge>
                  )}
                </div>
              )}
              
              <div className="flex items-center gap-3 mt-2">
                <span className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                </span>
                <Badge 
                  variant={notification.priority === 'critical' ? 'destructive' : notification.priority === 'high' ? 'default' : 'secondary'}
                  className="text-xs"
                >
                  {notification.priority}
                </Badge>
                {notification.status === 'unread' && (
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                )}
              </div>
            </div>
            
            {/* Action buttons */}
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onAction('view');
                }}
                className="h-8 w-8 p-0"
              >
                <Eye className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={(e) => {
                  e.stopPropagation();
                  onAction('archive');
                }}
                className="h-8 w-8 p-0"
              >
                <Archive className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {/* Custom actions for AI/ML notifications */}
          {notification.actions && notification.actions.length > 0 && (
            <div className="flex gap-2 mt-3">
              {notification.actions.map((action, index) => (
                <Button
                  key={index}
                  size="sm"
                  variant={action.variant || 'outline'}
                  onClick={(e) => {
                    e.stopPropagation();
                    onAction(action.action);
                  }}
                  className="text-xs"
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
