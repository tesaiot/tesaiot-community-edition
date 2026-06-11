/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { Brain, Shield, Activity, Users, AlertTriangle, Bell, Cpu } from 'lucide-react';

interface NotificationItemProps {
  notification: {
    id: string;
    type: string;
    title: string;
    message: string;
    status: 'read' | 'unread';
    priority: 'low' | 'medium' | 'high' | 'critical';
    created_at: string;
    metadata?: {
      model_name?: string;
      accuracy?: number;
      anomaly_score?: number;
      device_id?: string;
    };
  };
  onClick?: () => void;
}

export function NotificationItem({ notification, onClick }: NotificationItemProps) {
  const priorityColors = {
    low: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200',
    high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-200',
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-200'
  };

  const typeIcons = {
    system: Cpu,
    ai_ml: Brain,
    security: Shield,
    device: Activity,
    user: Users,
    maintenance: AlertTriangle,
    personal: Bell
  };
  
  const typeColors = {
    system: 'text-blue-600 dark:text-blue-400',
    ai_ml: 'text-purple-600 dark:text-purple-400',
    security: 'text-red-600 dark:text-red-400',
    device: 'text-green-600 dark:text-green-400',
    user: 'text-indigo-600 dark:text-indigo-400',
    maintenance: 'text-yellow-600 dark:text-yellow-400',
    personal: 'text-gray-600 dark:text-gray-400'
  };
  
  const Icon = typeIcons[notification.type as keyof typeof typeIcons] || Bell;

  return (
    <div
      className={cn(
        'p-4 border-b last:border-b-0 cursor-pointer transition-all duration-200',
        notification.status === 'unread' ? 'bg-blue-50/50 dark:bg-blue-900/10' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
        'hover:shadow-sm'
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className={cn(
          'flex items-center justify-center w-10 h-10 rounded-lg',
          notification.type === 'ai_ml' && 'bg-gradient-to-br from-purple-500/20 to-pink-500/20',
          notification.type === 'system' && 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20',
          notification.type === 'security' && 'bg-gradient-to-br from-red-500/20 to-orange-500/20',
          notification.type === 'device' && 'bg-gradient-to-br from-green-500/20 to-emerald-500/20',
          notification.type === 'maintenance' && 'bg-gradient-to-br from-yellow-500/20 to-amber-500/20',
          notification.type === 'user' && 'bg-gradient-to-br from-indigo-500/20 to-purple-500/20',
          notification.type === 'personal' && 'bg-gradient-to-br from-gray-500/20 to-slate-500/20'
        )}>
          <Icon className={cn('w-5 h-5', typeColors[notification.type as keyof typeof typeColors])} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className={cn(
              'text-sm font-medium truncate',
              notification.status === 'unread' && 'font-semibold'
            )}>
              {notification.title}
            </h4>
            <Badge 
              variant="secondary" 
              className={cn('text-xs', priorityColors[notification.priority])}
            >
              {notification.priority}
            </Badge>
            {notification.status === 'unread' && (
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            )}
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {notification.message}
          </p>
          
          {/* AI/ML specific metadata */}
          {notification.type === 'ai_ml' && notification.metadata && (
            <div className="mt-2 flex flex-wrap gap-2">
              {notification.metadata.model_name && (
                <span className="text-xs text-muted-foreground">
                  Model: {notification.metadata.model_name}
                </span>
              )}
              {notification.metadata.accuracy && (
                <span className="text-xs text-muted-foreground">
                  Accuracy: {notification.metadata.accuracy}%
                </span>
              )}
            </div>
          )}
          
          <p className="text-xs text-muted-foreground mt-1">
            {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
          </p>
        </div>
      </div>
    </div>
  );
}