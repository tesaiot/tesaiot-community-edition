/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Card } from '@/components/ui/card';
import { 
  Settings, 
  Award, 
  ShieldUser, 
  Euro, 
  ShieldOff,
  Users,
  Building,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock
} from 'lucide-react';

const PlatformAdminDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Check if user is Platform Admin
  const isPlatformAdmin = user?.role === 'platform_admin';
  
  useEffect(() => {
    if (!isPlatformAdmin) {
      navigate('/');
    }
  }, [isPlatformAdmin, navigate]);
  
  if (!isPlatformAdmin) {
    return null;
  }

  const adminCards = [
    {
      title: 'Service Configuration',
      description: 'Manage features, tiers, and service limits',
      icon: Settings,
      path: '/platform-admin/service-config',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50',
      stats: { features: 45, tiers: 3, limits: 12 }
    },
    {
      title: 'License Management',
      description: 'Control licenses, templates, and expirations',
      icon: Award,
      path: '/platform-admin/licenses',
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      stats: { active: 28, expiring: 5, templates: 8 }
    },
    {
      title: 'Platform Control',
      description: 'System configuration and deployment management',
      icon: ShieldUser,
      path: '/platform-admin/control',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      stats: { services: 12, healthy: 11, deployments: 3 }
    },
    {
      title: 'Billing & Revenue',
      description: 'Monitor subscriptions and payment analytics',
      icon: Euro,
      path: '/platform-admin/billing',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      stats: { subscriptions: 34, revenue: '€125K', growth: '+15%' }
    },
    {
      title: 'Advanced Security',
      description: 'Security policies, audits, and threat detection',
      icon: ShieldOff,
      path: '/platform-admin/security',
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      stats: { policies: 18, audits: 256, threats: 0 }
    }
  ];

  const systemStats = [
    { label: 'Total Organizations', value: '47', icon: Building, trend: '+3' },
    { label: 'Active Users', value: '1,284', icon: Users, trend: '+42' },
    { label: 'System Uptime', value: '99.98%', icon: TrendingUp, trend: 'stable' },
    { label: 'Active Alerts', value: '2', icon: AlertCircle, trend: '-1' }
  ];

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <ShieldUser className="h-8 w-8 text-purple-600" />
          <h1 className="text-3xl font-bold">Platform Admin Dashboard</h1>
        </div>
        <p className="text-gray-600">
          Exclusive platform administration for users with the platform_admin role
        </p>
      </div>

      {/* System Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {systemStats.map((stat, index) => (
          <Card key={index} className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.label}</p>
                <p className="text-2xl font-bold mt-1">{stat.value}</p>
                <p className="text-xs text-green-600 mt-1">{stat.trend}</p>
              </div>
              <stat.icon className="h-8 w-8 text-gray-400" />
            </div>
          </Card>
        ))}
      </div>

      {/* Admin Function Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {adminCards.map((card, index) => (
          <Card 
            key={index}
            className="hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => navigate(card.path)}
          >
            <div className="p-6">
              <div className={`inline-flex p-3 rounded-lg ${card.bgColor} mb-4`}>
                <card.icon className={`h-6 w-6 ${card.color}`} />
              </div>
              <h3 className="text-lg font-semibold mb-2">{card.title}</h3>
              <p className="text-gray-600 text-sm mb-4">{card.description}</p>
              
              {/* Stats */}
              <div className="flex gap-4 text-xs">
                {Object.entries(card.stats).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-gray-500 capitalize">{key}:</span>
                    <span className="ml-1 font-semibold">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Activity */}
      <Card className="mt-8">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Platform Activity</h2>
          <div className="space-y-3">
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-gray-600">Service tier updated for Organization ABC</span>
              <span className="ml-auto text-xs text-gray-400">2 mins ago</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <Clock className="h-4 w-4 text-yellow-600" />
              <span className="text-gray-600">License expiring soon for Organization XYZ</span>
              <span className="ml-auto text-xs text-gray-400">15 mins ago</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <span className="text-gray-600">New deployment completed successfully</span>
              <span className="ml-auto text-xs text-gray-400">1 hour ago</span>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <span className="text-gray-600">Security policy violation detected and resolved</span>
              <span className="ml-auto text-xs text-gray-400">3 hours ago</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default PlatformAdminDashboard;