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
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Shield, 
  Key, 
  Certificate, 
  AlertCircle, 
  CheckCircle, 
  Clock,
  TrendingUp,
  Activity,
  Users,
  Database,
  RefreshCw,
  Download,
  Eye,
  Settings,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, parseISO, differenceInDays } from 'date-fns';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar
} from 'recharts';

interface PKIStats {
  totalCertificates: number;
  activeCertificates: number;
  expiringSoon: number;
  revokedCertificates: number;
  totalCAs: number;
  activeRoles: number;
  certificateUsageByType: Array<{
    type: string;
    count: number;
    percentage: number;
  }>;
  expirationTrend: Array<{
    date: string;
    expiring: number;
    issued: number;
  }>;
  healthScore: number;
  lastUpdated: string;
}

interface CAInfo {
  id: string;
  name: string;
  type: 'root' | 'intermediate';
  status: 'active' | 'inactive' | 'expired';
  serialNumber: string;
  issuer: string;
  subject: string;
  notBefore: string;
  notAfter: string;
  keyType: string;
  keyBits: number;
  issuedCertificates: number;
  maxPathLength?: number;
}

interface RecentActivity {
  id: string;
  type: 'certificate_issued' | 'certificate_revoked' | 'role_created' | 'ca_rotation';
  description: string;
  timestamp: string;
  user: string;
  status: 'success' | 'warning' | 'error';
  details?: any;
}

export const PKIDashboard: React.FC = () => {
  const [pkiStats, setPkiStats] = useState<PKIStats | null>(null);
  const [caList, setCaList] = useState<CAInfo[]>([]);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch PKI dashboard data
  const fetchDashboardData = async () => {
    try {
      setRefreshing(true);
      
      // Fetch PKI statistics
      const statsResponse = await fetch('/api/v1/pki/ca/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!statsResponse.ok) {
        throw new Error('Failed to fetch PKI statistics');
      }
      
      const stats = await statsResponse.json();
      setPkiStats(stats);
      
      // Fetch CA list
      const caResponse = await fetch('/api/v1/pki/ca/list', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!caResponse.ok) {
        throw new Error('Failed to fetch CA list');
      }
      
      const caData = await caResponse.json();
      setCaList(caData.cas || []);
      
      // Fetch recent activity
      const activityResponse = await fetch('/api/v1/pki/ca/activity?limit=10', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!activityResponse.ok) {
        throw new Error('Failed to fetch recent activity');
      }
      
      const activityData = await activityResponse.json();
      setRecentActivity(activityData.activities || []);
      
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    
    // Refresh data every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthScoreColor = (score: number) => {
    if (score >= 90) return 'text-green-600';
    if (score >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getCAStatusBadge = (status: string) => {
    const variants = {
      active: 'bg-green-100 text-green-800',
      inactive: 'bg-gray-100 text-gray-800',
      expired: 'bg-red-100 text-red-800'
    };
    return variants[status as keyof typeof variants] || variants.inactive;
  };

  const getActivityStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  if (loading && !pkiStats) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">PKI Certificate Authority Dashboard</h1>
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span className="text-sm text-gray-500">Loading...</span>
          </div>
        </div>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div className="h-4 w-20 bg-gray-200 rounded animate-pulse" />
                <div className="h-4 w-4 bg-gray-200 rounded animate-pulse" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 bg-gray-200 rounded animate-pulse mb-2" />
                <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold tracking-tight">PKI Certificate Authority Dashboard</h1>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <Button onClick={fetchDashboardData} variant="outline">
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">PKI Certificate Authority Dashboard</h1>
          <p className="text-gray-500">
            Monitor and manage your PKI infrastructure
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button 
            onClick={fetchDashboardData} 
            variant="outline" 
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", refreshing && "animate-spin")} />
            Refresh
          </Button>
          <Button asChild>
            <a href="/admin/pki/certificates">
              <Certificate className="h-4 w-4 mr-2" />
              Manage Certificates
            </a>
          </Button>
        </div>
      </div>

      {/* PKI Health Score */}
      {pkiStats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>PKI Health Score</span>
              <Badge variant="outline" className={getHealthScoreColor(pkiStats.healthScore)}>
                {pkiStats.healthScore}/100
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Progress value={pkiStats.healthScore} className="w-full" />
              <div className="flex justify-between text-sm text-gray-500">
                <span>Last updated: {format(parseISO(pkiStats.lastUpdated), 'PPpp')}</span>
                <span>
                  {pkiStats.healthScore >= 90 && "Excellent"}
                  {pkiStats.healthScore >= 70 && pkiStats.healthScore < 90 && "Good"}
                  {pkiStats.healthScore < 70 && "Needs Attention"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Statistics Cards */}
      {pkiStats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Certificates</CardTitle>
              <Certificate className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pkiStats.totalCertificates.toLocaleString()}</div>
              <p className="text-xs text-gray-500">
                {pkiStats.activeCertificates} active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Expiring Soon</CardTitle>
              <Clock className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">{pkiStats.expiringSoon}</div>
              <p className="text-xs text-gray-500">
                Within 30 days
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Certificate Authorities</CardTitle>
              <Shield className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pkiStats.totalCAs}</div>
              <p className="text-xs text-gray-500">
                {caList.filter(ca => ca.status === 'active').length} active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Roles</CardTitle>
              <Users className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pkiStats.activeRoles}</div>
              <p className="text-xs text-gray-500">
                Certificate issuing roles
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Certificate Usage Chart */}
        {pkiStats && pkiStats.certificateUsageByType.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Certificate Usage by Type</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={pkiStats.certificateUsageByType}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ type, percentage }) => `${type} (${percentage}%)`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {pkiStats.certificateUsageByType.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Expiration Trend Chart */}
        {pkiStats && pkiStats.expirationTrend.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Certificate Expiration Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={pkiStats.expirationTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="expiring" 
                    stroke="#ff7300" 
                    name="Expiring"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="issued" 
                    stroke="#00c49f" 
                    name="Issued"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Certificate Authorities */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Certificate Authorities</CardTitle>
              <Button variant="outline" size="sm" asChild>
                <a href="/admin/pki/cas">
                  <Eye className="h-4 w-4 mr-2" />
                  View All
                </a>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-64">
              <div className="space-y-3">
                {caList.slice(0, 5).map((ca) => (
                  <div key={ca.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium">{ca.name}</h4>
                        <Badge variant="outline" className={getCAStatusBadge(ca.status)}>
                          {ca.status}
                        </Badge>
                        <Badge variant="secondary">
                          {ca.type}
                        </Badge>
                      </div>
                      <p className="text-sm text-gray-500 mb-1">
                        {ca.subject}
                      </p>
                      <div className="flex items-center space-x-4 text-xs text-gray-400">
                        <span>Serial: {ca.serialNumber.slice(0, 16)}...</span>
                        <span>Expires: {format(parseISO(ca.notAfter), 'MMM dd, yyyy')}</span>
                        <span>{ca.issuedCertificates} certs issued</span>
                      </div>
                    </div>
                    <div className="flex space-x-1">
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm">
                        <Download className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Recent Activity</CardTitle>
              <Button variant="outline" size="sm" asChild>
                <a href="/admin/pki/audit">
                  <Activity className="h-4 w-4 mr-2" />
                  View All
                </a>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-64">
              <div className="space-y-3">
                {recentActivity.map((activity) => (
                  <div key={activity.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                    <div className="flex-shrink-0 mt-1">
                      {getActivityStatusIcon(activity.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium">
                        {activity.description}
                      </p>
                      <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
                        <span>{activity.user}</span>
                        <span>•</span>
                        <span>{format(parseISO(activity.timestamp), 'MMM dd, HH:mm')}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Button variant="outline" className="h-auto p-4" asChild>
              <a href="/admin/pki/certificates/issue">
                <div className="flex flex-col items-center space-y-2">
                  <Certificate className="h-6 w-6" />
                  <span>Issue Certificate</span>
                </div>
              </a>
            </Button>
            
            <Button variant="outline" className="h-auto p-4" asChild>
              <a href="/admin/pki/roles">
                <div className="flex flex-col items-center space-y-2">
                  <Users className="h-6 w-6" />
                  <span>Manage Roles</span>
                </div>
              </a>
            </Button>
            
            <Button variant="outline" className="h-auto p-4" asChild>
              <a href="/admin/pki/configuration">
                <div className="flex flex-col items-center space-y-2">
                  <Settings className="h-6 w-6" />
                  <span>PKI Configuration</span>
                </div>
              </a>
            </Button>
            
            <Button variant="outline" className="h-auto p-4" asChild>
              <a href="/admin/pki/backup">
                <div className="flex flex-col items-center space-y-2">
                  <Database className="h-6 w-6" />
                  <span>Backup & Recovery</span>
                </div>
              </a>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};