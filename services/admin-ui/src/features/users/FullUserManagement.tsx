/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Users,
  UserPlus,
  Search,
  Filter,
  Download,
  Upload,
  MoreVertical,
  Edit,
  Trash2,
  Key,
  Shield,
  Mail,
  Phone,
  Building2,
  Calendar,
  Activity,
  Lock,
  Unlock,
  UserCheck,
  UserX,
  RefreshCw,
  Settings,
  Eye,
  EyeOff,
  Copy,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  Send
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useAuth } from '@/hooks/useAuth';
import { LicenseService } from '@/services/license/LicenseService';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'super_admin' | 'organization_admin' | 'org_admin' | 'org_user' | 'device' | 'admin' | 'user';
  status: 'active' | 'inactive' | 'suspended' | 'pending';
  organizationId?: string;
  organizationName?: string;
  avatar?: string;
  createdAt: Date;
  lastLogin?: Date;
  emailVerified: boolean;
  mfaEnabled: boolean;
  apiKeys: number;
  devices: number;
  permissions: string[];
  metadata?: {
    department?: string;
    phone?: string;
    location?: string;
    timezone?: string;
  };
}

interface Organization {
  id: string;
  name: string;
  slug: string;
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: Date;
  lastUsed?: Date;
  expiresAt?: Date;
}

interface ActivityLog {
  id: string;
  action: string;
  timestamp: Date;
  ip: string;
  userAgent: string;
  status: 'success' | 'failed';
}

// Normalize role values from backend to match dropdown values
const normalizeRole = (role: string): string => {
  if (!role) return 'org_user';
  // Map various role formats to the expected dropdown values
  const roleMap: Record<string, string> = {
    'organization_admin': 'organization_admin',
    'org_admin': 'organization_admin',
    'super_admin': 'super_admin',
    'admin': 'admin',
    'operator': 'operator',
    'viewer': 'viewer',
    'org_user': 'org_user',
    'user': 'org_user',
    'device': 'device'
  };
  return roleMap[role.toLowerCase()] || role;
};

export default function FullUserManagement() {
  const { user: currentUser, hasBDHOrgAdminAccess } = useAuth();
  const licenseService = LicenseService.getInstance();
  const isCommercial = licenseService.isCommercialEdition();
  const isPlatformAdmin = currentUser?.role === 'platform_admin';
  
  const [users, setUsers] = useState<User[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  
  // Password reset dialog state
  const [showPasswordResetDialog, setShowPasswordResetDialog] = useState(false);
  const [passwordResetData, setPasswordResetData] = useState<{
    user: User | null;
    tempPassword: string;
  }>({ user: null, tempPassword: '' });

  // Reset password confirmation dialog state
  const [showResetPasswordConfirm, setShowResetPasswordConfirm] = useState(false);
  const [userToResetPassword, setUserToResetPassword] = useState<User | null>(null);

  // New user form - OTP flow (no password needed)
  const [newUser, setNewUser] = useState({
    email: '',
    name: '',
    role: 'org_user' as const,
    organizationId: '',
    permissions: [] as string[],
    creationReason: ''
  });

  const currentUserOrgId = currentUser?.organizationId || currentUser?.organization_id || '';
  const isSuperAdminActor = currentUser?.role === 'super_admin';
  const isOrgAdminTarget = newUser.role === 'org_admin' || newUser.role === 'organization_admin';
  const isCrossOrgTarget = Boolean(newUser.organizationId) && (!currentUserOrgId || newUser.organizationId !== currentUserOrgId);
  const shouldShowReasonField = !selectedUser && isSuperAdminActor && isOrgAdminTarget;
  const reasonRequired = shouldShowReasonField && isCrossOrgTarget;

  // Fetch real data
  useEffect(() => {
    // Fetch organizations from API
    const fetchOrganizations = async () => {
      setIsLoadingData(true);
      try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch('/api/v1/organizations', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await response.json();
        if (data.success && data.organizations) {
          const orgs = data.organizations.map((org: any) => ({
            id: org.id || org._id,
            name: org.name,
            slug: org.domain || org.name.toLowerCase().replace(/\s+/g, '-')
          }));
          setOrganizations(orgs);
        }
      } catch (error) {
        console.error('Failed to fetch organizations:', error);
        toast.error("Failed to Load Organizations", {
          description: "Could not connect to the API server. Please check your connection."
        });
        setOrganizations([]);
      }
    };
    
    fetchOrganizations();
  }, []);

  // Fetch users when organizations are loaded
  useEffect(() => {
    if (organizations.length === 0 && !isLoadingData) {
      // Don't fetch users if organizations failed to load
      return;
    }
    
    const fetchUsers = async () => {
      try {
        const token = localStorage.getItem('jwt_token');
        const response = await fetch('/api/v1/users', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await response.json();
        if (data.success && data.users) {
          const apiUsers = data.users.map((user: any) => {
            // Handle name field - it might be a full name or firstName/lastName
            let fullName = '';
            if (user.name) {
              fullName = user.name;
            } else if (user.firstName || user.lastName) {
              fullName = `${user.firstName || ''} ${user.lastName || ''}`.trim();
            } else {
              fullName = user.email.split('@')[0]; // fallback to email prefix
            }
            
            // Find organization name by matching organization_id
            const org = organizations.find(o => 
              o.organization_id === (user.organizationId || user.organization_id) ||
              o.id === (user.organizationId || user.organization_id)
            );
            
            // Use organization name from user data if org lookup fails
            const organizationName = org?.name || user.organization || null;
            
            return {
              id: user.id || user._id,
              email: user.email,
              name: fullName,
              role: user.role,
              status: user.status || 'active',
              // Use stored avatar if available, otherwise use DiceBear as fallback
              avatar: user.avatar || user.pic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.email}`,
              createdAt: new Date(user.createdAt || user.created_at || new Date()),
              lastLogin: (user.lastLogin || user.last_login) ? new Date(user.lastLogin || user.last_login) : null,
              emailVerified: user.emailVerified || false,
              organizationId: user.organizationId || user.organization_id,
              organizationName: organizationName,
              mfaEnabled: user.mfaEnabled || false,
              apiKeys: user.apiKeys || 0,
              devices: user.devices || 0,
              permissions: user.permissions || []
            };
          });
          console.log('Mapped API users:', apiUsers);
          setUsers(apiUsers);
        } else {
          console.error('API returned error:', data);
          toast.error("Error Loading Users", {
            description: data.error || "Failed to load users from API"
          });
          setUsers([]);
        }
      } catch (error) {
        console.error('Failed to fetch users:', error);
        toast.error("Connection Error", {
          description: "Could not connect to the API server. Please check your connection."
        });
        setUsers([]);
      }
    };

    if (organizations.length > 0 || isLoadingData) {
      fetchUsers().finally(() => setIsLoadingData(false));
    }
  }, [organizations]);

  // Filter users
  const filteredUsers = users.filter(user => {
    const matchesSearch = 
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesOrg = 
      selectedOrg === 'all' || 
      user.organizationId === selectedOrg ||
      (selectedOrg === 'platform' && !user.organizationId);
    
    const matchesRole = filterRole === 'all' || user.role === filterRole;
    const matchesStatus = filterStatus === 'all' || user.status === filterStatus;
    
    return matchesSearch && matchesOrg && matchesRole && matchesStatus;
  });

  // Check permissions
  const canManageUser = (user: User): boolean => {
    // Debug logging
    console.log('canManageUser check:', {
      currentUser: currentUser,
      userToManage: user,
      hasBDHOrgAdminAccess: hasBDHOrgAdminAccess
    });
    
    // TESA Admin (super_admin) can manage everyone
    if (currentUser?.role === 'super_admin' || currentUser?.email === 'admin@tesa.local') return true;
    
    // Organization Admin can only manage users in their own organization
    // Handle both 'org_admin' and 'organization_admin' role names
    if (currentUser?.role === 'org_admin' || currentUser?.role === 'organization_admin' || hasBDHOrgAdminAccess) {
      // Cannot manage super admins
      if (user.role === 'super_admin') return false;
      // Can only manage users in same organization
      // Handle both organizationId and organization_id field names
      const currentUserOrgId = currentUser.organizationId || currentUser.organization_id;
      const userOrgId = user.organizationId;
      console.log('Org ID comparison:', { currentUserOrgId, userOrgId, match: userOrgId === currentUserOrgId });
      return userOrgId === currentUserOrgId;
    }
    
    // Regular users cannot manage anyone
    return false;
  };
  
  // Check if current user can create users
  const canCreateUsers = (): boolean => {
    return currentUser?.role === 'super_admin' || currentUser?.role === 'organization_admin' || currentUser?.role === 'admin' || hasBDHOrgAdminAccess;
  };
  
  // Check if current user is TESA admin
  const isTesaAdmin = (): boolean => {
    return currentUser?.role === 'super_admin' || currentUser?.email === 'admin@tesa.local';
  };

  const getRoleBadgeVariant = (role: string) => {
    switch (role) {
      case 'super_admin': return 'destructive';
      case 'organization_admin':
      case 'org_admin':
        return 'default';
      case 'org_user': return 'secondary';
      case 'device': return 'outline';
      default: return 'secondary';
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'inactive': return 'secondary';
      case 'suspended': return 'destructive';
      case 'pending': return 'outline';
      default: return 'secondary';
    }
  };

  const handleCreateUser = async () => {
    if (reasonRequired && !newUser.creationReason.trim()) {
      toast.error("Reason Required", {
        description: "Please document why this administrator needs cross-organization access."
      });
      return;
    }

    setLoading(true);
    
    try {
      const token = localStorage.getItem('jwt_token');
      
      const payload: Record<string, any> = {
        email: newUser.email,
        name: newUser.name,
        role: newUser.role,
        organization_id: newUser.organizationId,
        permissions: newUser.permissions
      };

      if (shouldShowReasonField && newUser.creationReason.trim()) {
        payload.reason = newUser.creationReason.trim();
      }

      // Use OTP endpoint for user creation
      const response = await fetch('/api/v1/users/create-with-otp', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      
      const data = await response.json();
      
      // Check if response was successful
      if (response.ok && data.user) {
        // Refresh the users list
        const fetchResponse = await fetch('/api/v1/users', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const fetchData = await fetchResponse.json();
        if (fetchData.success && fetchData.users) {
          const apiUsers = fetchData.users.map((user: any) => ({
            id: user.id || user._id,
            email: user.email,
            name: user.name || `${user.firstName || ''} ${user.lastName || ''}`.trim(),
            role: user.role,
            status: user.is_active ? 'active' : 'pending',
            // Use stored avatar if available, otherwise use DiceBear as fallback
            avatar: user.avatar || user.pic || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.email}`,
            createdAt: new Date(user.createdAt || user.created_at),
            lastLogin: user.lastLogin ? new Date(user.lastLogin) : null,
            emailVerified: user.email_verified || false,
            organizationId: user.organization_id || user.organizationId,
            permissions: user.permissions || []
          }));
          setUsers(apiUsers);
        }
        
        setShowCreateDialog(false);
        toast.success("✅ User Created Successfully", {
          description: `An activation email with verification code has been sent to ${newUser.email}. The user will need to verify their email and set their own password.`
        });
      } else {
        toast.error("Error", {
          description: data.error || data.message || "Failed to create user"
        });
      }
    } catch (error) {
      console.error('Failed to create user:', error);
      toast.error("Error", {
        description: "Failed to create user"
      });
    } finally {
      setLoading(false);
      // Reset form
      setNewUser({
        email: '',
        name: '',
        role: 'org_user',
        organizationId: '',
        permissions: [],
        creationReason: ''
      });
    }
  };

  const handleUpdateUser = async (user: User) => {
    setLoading(true);
    
    try {
      // Call API to update user
      const token = localStorage.getItem('jwt_token');
      const response = await fetch(`/api/v1/users/${user.id}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: newUser.email,
          name: newUser.name,
          role: newUser.role,
          organizationId: newUser.organizationId
        })
      });
      
      if (response.ok) {
        // Update local state
        setUsers(users.map(u => 
          u.id === user.id 
            ? { ...u, email: newUser.email, name: newUser.name, role: newUser.role, organizationId: newUser.organizationId }
            : u
        ));
        
        toast.success("User Updated", {
          description: `${newUser.name} has been updated successfully`
        });
        
        setShowCreateDialog(false);
        setSelectedUser(null);
      } else {
        throw new Error('Failed to update user');
      }
    } catch (error) {
      toast.error("Update Failed", {
        description: "Failed to update user. Please try again."
      });
    }
    
    setLoading(false);
  };

  // Show confirmation dialog before resetting password
  const handleResetPassword = (user: User) => {
    setUserToResetPassword(user);
    setShowResetPasswordConfirm(true);
  };

  // Actually reset the password after confirmation
  const confirmResetPassword = async () => {
    if (!userToResetPassword) return;

    setLoading(true);
    console.log('Resetting password for user:', userToResetPassword.email);

    try {
      const token = localStorage.getItem('jwt_token');
      const response = await fetch(`/api/v1/users/${userToResetPassword.id}/reset-password`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      console.log('Reset password response status:', response.status);

      if (response.ok) {
        const data = await response.json();
        console.log('Reset password response data:', data);

        // Show the password reset dialog with the temporary password
        setPasswordResetData({
          user: userToResetPassword,
          tempPassword: data.temp_password || ''
        });
        setShowPasswordResetDialog(true);

        // Also log to console for backup
        console.log(`Password reset for ${userToResetPassword.email}. Temporary password: ${data.temp_password}`);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to reset password');
      }
    } catch (error) {
      console.error('Password reset error:', error);
      toast.error("❌ Password Reset Failed", {
        description: error instanceof Error ? error.message : "Failed to reset password"
      });
    }

    setLoading(false);
    setShowResetPasswordConfirm(false);
    setUserToResetPassword(null);
  };

  const handleToggleStatus = async (user: User) => {
    const newStatus = user.status === 'active' ? 'inactive' : 'active';
    
    setUsers(users.map(u => 
      u.id === user.id ? { ...u, status: newStatus } : u
    ));
    
    toast.success("Status Updated", {
      description: `User ${user.name} is now ${newStatus}`
    });
  };

  const handleDeleteUser = async (user: User) => {
    if (!confirm(`Are you sure you want to delete ${user.name}?`)) return;
    
    setLoading(true);
    
    try {
      const token = localStorage.getItem('jwt_token');
      const response = await fetch(`/api/v1/users/${user.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        // Remove from local state after successful API call
        setUsers(users.filter(u => u.id !== user.id));
        
        toast.success("User Deleted", {
          description: `User ${user.name} has been removed`
        });
      } else {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete user');
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
      toast.error("Delete Failed", {
        description: error instanceof Error ? error.message : "Failed to delete user. Please try again."
      });
    }
    
    setLoading(false);
  };

  const handleResendOTP = async (user: User) => {
    setLoading(true);
    
    try {
      const token = localStorage.getItem('jwt_token');
      const response = await fetch('/api/v1/auth/otp/resend-otp', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: user.email,
          purpose: 'verification'
        })
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        toast.success("✅ OTP Resent Successfully", {
          description: `A new verification code has been sent to ${user.email}`
        });
      } else {
        throw new Error(data.error || data.message || 'Failed to resend OTP');
      }
    } catch (error) {
      console.error('Failed to resend OTP:', error);
      toast.error("❌ Resend OTP Failed", {
        description: error instanceof Error ? error.message : "Failed to resend OTP. Please try again."
      });
    }
    
    setLoading(false);
  };

  const exportUsers = () => {
    const csv = [
      ['Name', 'Email', 'Role', 'Organization', 'Status', 'Created', 'Last Login'],
      ...filteredUsers.map(user => [
        user.name,
        user.email,
        user.role,
        user.organizationName || 'Platform',
        user.status,
        format(user.createdAt, 'yyyy-MM-dd'),
        user.lastLogin ? format(user.lastLogin, 'yyyy-MM-dd HH:mm') : 'Never'
      ])
    ].map(row => row.join(',')).join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `users-export-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success("Export Complete", {
      description: `Exported ${filteredUsers.length} users`
    });
  };

  // Platform admins cannot access user management
  if (isPlatformAdmin) {
    return (
      <div className="p-6">
        <div className="max-w-2xl mx-auto">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Access Restricted
              </CardTitle>
              <CardDescription>
                Platform Administrator Access
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="space-y-2">
                  <p>
                    As a platform administrator, you have access to infrastructure management only.
                    User management is restricted to organization administrators.
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Platform administrators can manage:
                  </p>
                  <ul className="list-disc list-inside text-sm text-muted-foreground ml-4">
                    <li>System infrastructure and monitoring</li>
                    <li>Platform-wide settings and configuration</li>
                    <li>Service health and performance metrics</li>
                  </ul>
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">
            Manage users across all organizations
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isCommercial && (
            <>
              <Button variant="outline" onClick={exportUsers}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <Button variant="outline">
                <Upload className="mr-2 h-4 w-4" />
                Import
              </Button>
            </>
          )}
          {canCreateUsers() && (
            <Button onClick={() => setShowCreateDialog(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Create User
            </Button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoadingData ? '-' : users.length}</div>
            <p className="text-xs text-muted-foreground">
              {isLoadingData ? 'Loading...' : `${users.filter(u => u.status === 'active').length} active`}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Organizations</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoadingData ? '-' : organizations.length}</div>
            <p className="text-xs text-muted-foreground">
              {isLoadingData ? 'Loading...' : 'Active tenants'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">With MFA</CardTitle>
            <Shield className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoadingData ? '-' : users.filter(u => u.mfaEnabled).length}
            </div>
            <p className="text-xs text-muted-foreground">
              {isLoadingData ? 'Loading...' : users.length > 0 ? `${Math.round((users.filter(u => u.mfaEnabled).length / users.length) * 100)}% secured` : '0% secured'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Device Users</CardTitle>
            <Key className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoadingData ? '-' : users.filter(u => u.role === 'device').length}
            </div>
            <p className="text-xs text-muted-foreground">
              {isLoadingData ? 'Loading...' : 'Service accounts'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>All Users</CardTitle>
          <CardDescription>
            View and manage users across the platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            {isTesaAdmin() && (
              <Select value={selectedOrg} onValueChange={setSelectedOrg}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Filter by org" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Organizations</SelectItem>
                  <SelectItem value="platform">Platform Users</SelectItem>
                  {organizations.map(org => (
                    <SelectItem key={org.id} value={org.id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            
            <Select value={filterRole} onValueChange={setFilterRole}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter by role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                <SelectItem value="super_admin">Super Admin</SelectItem>
                <SelectItem value="organization_admin">Organization Admin</SelectItem>
                <SelectItem value="org_user">Org User</SelectItem>
                <SelectItem value="device">Device</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Users Table */}
          {isLoadingData ? (
            <div className="flex items-center justify-center p-8">
              <div className="text-center space-y-2">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading users...</p>
              </div>
            </div>
          ) : filteredUsers.length === 0 ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {users.length === 0 
                  ? 'No users found. Create your first user to get started.' 
                  : searchTerm || filterRole !== 'all' || filterStatus !== 'all' 
                    ? `No users match your filters. Found ${users.length} total users.`
                    : 'No users found.'}
              </AlertDescription>
            </Alert>
          ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Organization</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead>Security</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <Avatar className="h-8 w-8">
                          <AvatarImage src={user.avatar} />
                          <AvatarFallback>
                            {user.name.split(' ').map(n => n[0]).join('')}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="font-medium">{user.name}</p>
                          <p className="text-sm text-muted-foreground">{user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {user.organizationName || (
                        <Badge variant="outline">Platform</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={getRoleBadgeVariant(user.role)}>
                        {user.role.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(user.status)}>
                        {user.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {user.lastLogin ? (
                        <span className="text-sm">
                          {formatDistanceToNow(user.lastLogin, { addSuffix: true })}
                        </span>
                      ) : (
                        <span className="text-sm text-muted-foreground">Never</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {user.emailVerified ? (
                          <Mail className="h-4 w-4 text-green-600" />
                        ) : (
                          <Mail className="h-4 w-4 text-muted-foreground" />
                        )}
                        {user.mfaEnabled ? (
                          <Shield className="h-4 w-4 text-green-600" />
                        ) : (
                          <Shield className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      {canManageUser(user) && (
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Actions</DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => {
                              setSelectedUser(user);
                              setShowDetailsDialog(true);
                            }}>
                              <Eye className="mr-2 h-4 w-4" />
                              View Details
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => {
                              setSelectedUser(user);
                              setNewUser({
                                email: user.email,
                                name: user.name,
                                role: normalizeRole(user.role) as any,
                                organizationId: user.organizationId || '',
                                sendInvite: false,
                                temporaryPassword: '',
                                permissions: user.permissions || [],
                                creationReason: ''
                              });
                              setShowCreateDialog(true);
                            }}>
                              <Edit className="mr-2 h-4 w-4" />
                              Edit User
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleResetPassword(user)}>
                              <Key className="mr-2 h-4 w-4" />
                              Reset Password
                            </DropdownMenuItem>
                            {/* Show Resend OTP for pending users or users who have never logged in */}
                            {(user.status === 'pending' || !user.lastLogin) && (
                              <DropdownMenuItem onClick={() => handleResendOTP(user)}>
                                <Send className="mr-2 h-4 w-4" />
                                Resend OTP
                              </DropdownMenuItem>
                            )}
                            {/* Prevent users from deactivating themselves */}
                            {currentUser?.email !== user.email && (
                              <DropdownMenuItem onClick={() => handleToggleStatus(user)}>
                                {user.status === 'active' ? (
                                  <>
                                    <UserX className="mr-2 h-4 w-4" />
                                    Deactivate
                                  </>
                                ) : (
                                  <>
                                    <UserCheck className="mr-2 h-4 w-4" />
                                    Activate
                                  </>
                                )}
                              </DropdownMenuItem>
                            )}
                            {/* Prevent users from deleting themselves */}
                            {currentUser?.email !== user.email && (
                              <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem 
                                  className="text-red-600"
                                  onClick={() => handleDeleteUser(user)}
                                >
                                  <Trash2 className="mr-2 h-4 w-4" />
                                  Delete User
                                </DropdownMenuItem>
                              </>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit User Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={(open) => {
        setShowCreateDialog(open);
        if (!open) setSelectedUser(null);
      }}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>{selectedUser ? 'Edit User' : 'Create New User'}</DialogTitle>
            <DialogDescription>
              {selectedUser ? 'Update user information' : 'Add a new user to the platform or organization'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@example.com"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  disabled={!!selectedUser}
                />
                {selectedUser && (
                  <p className="text-xs text-muted-foreground">
                    Email cannot be changed after user creation
                  </p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input
                  id="name"
                  placeholder="John Doe"
                  value={newUser.name}
                  onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select 
                  value={newUser.role} 
                  onValueChange={(value: any) => setNewUser({ ...newUser, role: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    {isTesaAdmin() && (
                      <SelectItem value="super_admin">Super Admin</SelectItem>
                    )}
                    <SelectItem value="organization_admin">Organization Admin</SelectItem>
                    <SelectItem value="operator">Operator</SelectItem>
                    <SelectItem value="product_industrial_designer">Product Model Designer</SelectItem>
                    <SelectItem value="org_user">Organization User</SelectItem>
                    <SelectItem value="device">Device/Service Account</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="organization">Organization</Label>
                <Select 
                  value={newUser.organizationId} 
                  onValueChange={(value) => setNewUser({ ...newUser, organizationId: value })}
                  disabled={!isTesaAdmin()}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select organization" />
                  </SelectTrigger>
                  <SelectContent>
                    {organizations.map(org => (
                      <SelectItem key={org.id} value={org.id}>
                        {org.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {shouldShowReasonField && (
              <div className="space-y-2">
                <Label htmlFor="creationReason">Onboarding Reason</Label>
                <Input
                  id="creationReason"
                  placeholder="e.g. Provisioning initial admin for BDH organization"
                  value={newUser.creationReason}
                  onChange={(e) => setNewUser({ ...newUser, creationReason: e.target.value })}
                  disabled={!newUser.organizationId}
                />
                <p className="text-xs text-muted-foreground">
                  This note is stored in the audit log to document why cross-organization admin access is granted.
                </p>
                {reasonRequired && !newUser.creationReason.trim() && (
                  <p className="text-xs text-red-500">
                    Please provide a reason before creating an administrator for another organization.
                  </p>
                )}
              </div>
            )}

            {/* OTP Information Alert */}
            {!selectedUser && (
              <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/50">
                <Mail className="h-4 w-4 text-blue-600" />
                <AlertDescription className="text-blue-900 dark:text-blue-100">
                  <strong>Secure Account Creation with OTP</strong>
                  <ul className="mt-2 space-y-1 text-sm">
                    <li>• User will receive an email with a 6-digit verification code</li>
                    <li>• Code expires soon for security</li>
                    <li>• User verifies email and sets their own password</li>
                    <li>• No temporary passwords needed - more secure!</li>
                  </ul>
                </AlertDescription>
              </Alert>
            )}
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setShowCreateDialog(false);
              setSelectedUser(null);
            }}>
              Cancel
            </Button>
            <Button 
              onClick={selectedUser ? () => handleUpdateUser(selectedUser) : handleCreateUser} 
              disabled={loading || !newUser.email || !newUser.name || (!selectedUser && reasonRequired && !newUser.creationReason.trim())}
            >
              {loading ? (selectedUser ? 'Updating...' : 'Creating...') : (selectedUser ? 'Update User' : 'Create User')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* User Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="sm:max-w-[700px]">
          <DialogHeader>
            <DialogTitle>User Details</DialogTitle>
            <DialogDescription>
              View detailed information about {selectedUser?.name}
            </DialogDescription>
          </DialogHeader>
          
          {selectedUser && (
            <Tabs defaultValue="info" className="mt-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="info">Information</TabsTrigger>
                <TabsTrigger value="security">Security</TabsTrigger>
                <TabsTrigger value="activity">Activity</TabsTrigger>
              </TabsList>
              
              <TabsContent value="info" className="space-y-4">
                <div className="flex items-center gap-4">
                  <Avatar className="h-16 w-16">
                    <AvatarImage src={selectedUser.avatar} />
                    <AvatarFallback>
                      {selectedUser.name.split(' ').map(n => n[0]).join('')}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <h3 className="text-lg font-semibold">{selectedUser.name}</h3>
                    <p className="text-sm text-muted-foreground">{selectedUser.email}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={getRoleBadgeVariant(selectedUser.role)}>
                        {selectedUser.role.replace('_', ' ')}
                      </Badge>
                      <Badge variant={getStatusBadgeVariant(selectedUser.status)}>
                        {selectedUser.status}
                      </Badge>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Organization</p>
                    <p className="mt-1">{selectedUser.organizationName || 'Platform'}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Member Since</p>
                    <p className="mt-1">{format(selectedUser.createdAt, 'MMM d, yyyy')}</p>
                  </div>
                  {selectedUser.metadata?.department && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Department</p>
                      <p className="mt-1">{selectedUser.metadata.department}</p>
                    </div>
                  )}
                  {selectedUser.metadata?.location && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Location</p>
                      <p className="mt-1">{selectedUser.metadata.location}</p>
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Permissions</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedUser.permissions.map((perm) => (
                      <Badge key={perm} variant="secondary">
                        {perm}
                      </Badge>
                    ))}
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="security" className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">Email Verification</p>
                        <p className="text-sm text-muted-foreground">
                          Email address verification status
                        </p>
                      </div>
                    </div>
                    <Badge variant={selectedUser.emailVerified ? 'default' : 'secondary'}>
                      {selectedUser.emailVerified ? 'Verified' : 'Unverified'}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Shield className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">Two-Factor Authentication</p>
                        <p className="text-sm text-muted-foreground">
                          Additional security for account access
                        </p>
                      </div>
                    </div>
                    <Badge variant={selectedUser.mfaEnabled ? 'default' : 'secondary'}>
                      {selectedUser.mfaEnabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Key className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">API Keys</p>
                        <p className="text-sm text-muted-foreground">
                          Active API keys for programmatic access
                        </p>
                      </div>
                    </div>
                    <span className="font-medium">{selectedUser.apiKeys}</span>
                  </div>

                  <div className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center gap-3">
                      <Activity className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">Last Login</p>
                        <p className="text-sm text-muted-foreground">
                          Most recent account access
                        </p>
                      </div>
                    </div>
                    <span className="text-sm">
                      {selectedUser.lastLogin 
                        ? format(selectedUser.lastLogin, 'MMM d, yyyy HH:mm')
                        : 'Never'
                      }
                    </span>
                  </div>
                </div>
              </TabsContent>
              
              <TabsContent value="activity" className="space-y-4">
                <Alert>
                  <Activity className="h-4 w-4" />
                  <AlertDescription>
                    Recent activity log for this user will be displayed here.
                    This feature is available in the commercial edition.
                  </AlertDescription>
                </Alert>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>

      {/* Password Reset Success Dialog */}
      <Dialog open={showPasswordResetDialog} onOpenChange={setShowPasswordResetDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              Password Reset Successful
            </DialogTitle>
            <DialogDescription>
              The password has been reset successfully. Please provide the temporary password to the user securely.
            </DialogDescription>
          </DialogHeader>

          {passwordResetData.user && (
            <div className="space-y-4">
              <div className="bg-muted p-4 rounded-lg space-y-3">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">User</p>
                  <p className="font-medium">{passwordResetData.user.name}</p>
                  <p className="text-sm text-muted-foreground">{passwordResetData.user.email}</p>
                </div>

                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Temporary Password</p>
                  <div className="flex items-center gap-2">
                    <code className="bg-background px-3 py-2 rounded text-lg font-mono select-all">
                      {passwordResetData.tempPassword}
                    </code>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(passwordResetData.tempPassword);
                        toast.success("Copied!", {
                          description: "Password copied to clipboard"
                        });
                      }}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>

              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Important:</strong> This temporary password is only shown once.
                  The user must change this password on their first login.
                  Make sure to communicate this password securely to the user.
                </AlertDescription>
              </Alert>
            </div>
          )}

          <DialogFooter>
            <Button
              onClick={() => {
                setShowPasswordResetDialog(false);
                setPasswordResetData({ user: null, tempPassword: '' });
              }}
            >
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Password Confirmation Dialog */}
      <AlertDialog open={showResetPasswordConfirm} onOpenChange={setShowResetPasswordConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <Key className="h-5 w-5 text-orange-500" />
              Confirm Password Reset
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>
                Are you sure you want to reset the password for <strong>{userToResetPassword?.name}</strong> ({userToResetPassword?.email})?
              </p>
              <p className="text-orange-600 dark:text-orange-400 font-medium">
                ⚠️ This action will immediately change the user's password. A new temporary password will be generated that must be shared with the user securely.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setShowResetPasswordConfirm(false);
              setUserToResetPassword(null);
            }}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmResetPassword}
              disabled={loading}
              className="bg-orange-600 hover:bg-orange-700"
            >
              {loading ? 'Resetting...' : 'Yes, Reset Password'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      </div>
    </div>
  );
}
