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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { useAuth } from '@/hooks/useAuth';
import { tesaApi } from '@/services/api/tesaApi';
import { User, Mail, Phone, Building, Key, Save, AlertCircle, Shield, CheckCircle, Eye, EyeOff, Camera } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

// Professional avatars - Business/Corporate style
const SAMPLE_AVATARS = [
  // Professional Asian Business People
  { id: 'asian_engineer_m', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=AsianEngineer&backgroundColor=e0f2fe&glasses=variant01&hairColor=0a0a0a' },
  { id: 'asian_manager_f', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=AsianManager&backgroundColor=fef3c7&hairColor=1a1a1a&hair=variant26' },
  { id: 'asian_officer_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=AsianOfficer&backgroundColor=f3f4f6&glasses=variant02' },
  { id: 'asian_worker_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=AsianWorker&backgroundColor=dbeafe&hairColor=0a0a0a' },
  { id: 'asian_executive_f', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=AsianExecutive&backgroundColor=fce7f3&hair=variant18' },
  
  // Professional Caucasian Business People  
  { id: 'white_engineer_m', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=WhiteEngineer&backgroundColor=e0e7ff&hairColor=8b4513&glasses=variant04' },
  { id: 'white_manager_f', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=WhiteManager&backgroundColor=fed7aa&hairColor=d2b48c&hair=variant24' },
  { id: 'white_officer_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=WhiteOfficer&backgroundColor=f0f9ff&hairColor=696969' },
  { id: 'white_director_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=WhiteDirector&backgroundColor=ecfccb&glasses=variant03' },
  { id: 'white_supervisor_f', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=WhiteSupervisor&backgroundColor=ffe4e6&hair=variant15' },
  
  // Professional African/Black Business People
  { id: 'black_engineer_m', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=BlackEngineer&backgroundColor=dcfce7&hairColor=0a0a0a&glasses=variant05' },
  { id: 'black_manager_f', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=BlackManager&backgroundColor=fef9c3&hairColor=1a1a1a&hair=variant22' },
  { id: 'black_officer_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=BlackOfficer&backgroundColor=e9d5ff&hairColor=0a0a0a' },
  { id: 'black_executive_m', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=BlackExecutive&backgroundColor=ccfbf1&glasses=variant01' },
  { id: 'black_coordinator_f', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=BlackCoordinator&backgroundColor=cffafe&hair=variant20' },
  
  // Mixed Professional Roles
  { id: 'tech_lead', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=TechLead&backgroundColor=ddd6fe&glasses=variant02' },
  { id: 'project_manager', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=ProjectManager&backgroundColor=bfdbfe&hair=variant28' },
  { id: 'qa_engineer', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=QAEngineer&backgroundColor=a7f3d0' },
  { id: 'devops_engineer', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=DevOpsEngineer&backgroundColor=fbbf24' },
  { id: 'security_officer', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=SecurityOfficer&backgroundColor=fecaca' },
  
  // Additional Professional Avatars
  { id: 'cto', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=CTO&backgroundColor=c7d2fe&glasses=variant03' },
  { id: 'architect', url: 'https://api.dicebear.com/7.x/lorelei/svg?seed=Architect&backgroundColor=99f6e4' },
  { id: 'analyst', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Analyst&backgroundColor=fed7e2' },
  { id: 'consultant', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=Consultant&backgroundColor=d9f99d' },
  { id: 'team_lead', url: 'https://api.dicebear.com/7.x/notionists/svg?seed=TeamLead&backgroundColor=c084fc' },
];

export function SimpleUserProfile() {
  const { user, updateUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [profileCompleteness, setProfileCompleteness] = useState(0);
  const [selectedAvatar, setSelectedAvatar] = useState('');
  const [avatarDialogOpen, setAvatarDialogOpen] = useState(false);
  const [profileData, setProfileData] = useState({
    name: '',
    email: '',
    phone: '',
    organization: '',
    role: '',
    avatar: ''
  });
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  // Load user data and calculate profile completeness
  useEffect(() => {
    if (user) {
      const data = {
        name: user.name || user.username || '',
        email: user.email || '',
        phone: user.phone || '',
        organization: user.organization || '',
        role: user.role || 'user',
        avatar: user.avatar || SAMPLE_AVATARS[0].url
      };
      setProfileData(data);
      setSelectedAvatar(data.avatar);
      
      // Calculate profile completeness (excluding organization as it's read-only)
      const fields = ['name', 'email', 'phone'];
      const filledFields = fields.filter(field => data[field as keyof typeof data]);
      setProfileCompleteness(Math.round((filledFields.length / fields.length) * 100));
    }
  }, [user]);

  // Handle avatar selection
  const handleAvatarSelect = async (avatarUrl: string) => {
    setSelectedAvatar(avatarUrl);
    setProfileData({ ...profileData, avatar: avatarUrl });
    setAvatarDialogOpen(false);
    
    // Immediately save the avatar change
    try {
      const { organization, ...updateData } = profileData;
      updateData.avatar = avatarUrl;
      const response = await tesaApi.updateProfile(updateData);
      if (response.success) {
        toast.success('Avatar updated successfully');
        if (updateUser) {
          await updateUser({ ...profileData, avatar: avatarUrl });
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to update avatar');
    }
  };

  // Handle profile update
  const handleProfileUpdate = async () => {
    setLoading(true);
    try {
      // Don't send organization field in update
      const { organization, ...updateData } = profileData;
      const response = await tesaApi.updateProfile(updateData);
      if (response.success) {
        toast.success('Profile updated successfully');
        if (updateUser) {
          await updateUser(profileData);
        }
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  // Handle password change
  const handlePasswordChange = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (passwordData.newPassword.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      const response = await tesaApi.changePassword({
        current_password: passwordData.currentPassword,
        new_password: passwordData.newPassword
      });
      
      if (response.success) {
        toast.success('Password changed successfully');
        setPasswordData({
          currentPassword: '',
          newPassword: '',
          confirmPassword: ''
        });
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Please log in to view your profile
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-5xl">
      {/* Profile Header Section */}
      <div className="flex flex-col md:flex-row gap-6 mb-8 p-6 bg-card rounded-lg border">
        <div className="relative">
          <Avatar className="h-24 w-24">
            <AvatarImage src={selectedAvatar || profileData.avatar} alt={profileData.name} />
            <AvatarFallback className="text-lg bg-primary/10 text-primary">
              {profileData.name?.charAt(0)?.toUpperCase() || user?.username?.charAt(0)?.toUpperCase() || 'U'}
            </AvatarFallback>
          </Avatar>
          <Dialog open={avatarDialogOpen} onOpenChange={setAvatarDialogOpen}>
            <DialogTrigger asChild>
              <Button
                size="sm"
                variant="secondary"
                className="absolute -bottom-2 -right-2 rounded-full p-2 h-8 w-8"
              >
                <Camera className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>Choose Your Avatar</DialogTitle>
                <DialogDescription>
                  Select a professional avatar for your DevOps/Admin/Security profile
                </DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-5 gap-3 py-4">
                {SAMPLE_AVATARS.map((avatar) => (
                  <button
                    key={avatar.id}
                    onClick={() => handleAvatarSelect(avatar.url)}
                    className="relative rounded-lg overflow-hidden border-2 hover:border-primary transition-colors"
                    style={{
                      borderColor: selectedAvatar === avatar.url ? 'var(--primary)' : 'transparent'
                    }}
                  >
                    <img
                      src={avatar.url}
                      alt={`Avatar ${avatar.id}`}
                      className="w-full h-full object-cover"
                    />
                    {selectedAvatar === avatar.url && (
                      <div className="absolute inset-0 bg-primary/20 flex items-center justify-center">
                        <CheckCircle className="h-6 w-6 text-primary" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </DialogContent>
          </Dialog>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-2xl font-semibold">{profileData.name || user?.username || 'User'}</h1>
            <Badge variant="outline" className="capitalize">{profileData.role}</Badge>
          </div>
          <p className="text-muted-foreground mb-3">{profileData.email}</p>
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Profile Completion</span>
              <span className="text-sm font-medium">{profileCompleteness}%</span>
            </div>
            <Progress value={profileCompleteness} className="h-2" />
          </div>
        </div>
      </div>
      
      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-2 mb-6">
          <TabsTrigger value="profile" className="flex items-center gap-2">
            <User className="w-4 h-4" />
            Profile Information
          </TabsTrigger>
          <TabsTrigger value="password" className="flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Security
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
            <CardHeader className="relative">
              <CardTitle className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <User className="h-5 w-5 text-primary" />
                </div>
                Profile Information
              </CardTitle>
              <CardDescription>
                Manage your personal information and account details
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-6">
              {/* Personal Information Section */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-4">PERSONAL INFORMATION</h3>
                <div className="grid grid-cols-1 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-muted/50">
                        <User className="h-3.5 w-3.5" />
                      </div>
                      Full Name
                    </Label>
                    <Input
                      id="name"
                      value={profileData.name}
                      onChange={(e) => setProfileData({...profileData, name: e.target.value})}
                      placeholder="Enter your full name"
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-muted/50">
                        <Mail className="h-3.5 w-3.5" />
                      </div>
                      Email Address
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      value={profileData.email}
                      disabled
                      placeholder="your.email@example.com"
                      className="h-11 bg-muted/50 cursor-not-allowed"
                      title="Email address cannot be changed here. Please contact support."
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      To change your email address, please contact support
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Contact Information Section */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-4">CONTACT INFORMATION</h3>
                <div className="grid grid-cols-1 gap-6">

                  <div className="space-y-2">
                    <Label htmlFor="phone" className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-muted/50">
                        <Phone className="h-3.5 w-3.5" />
                      </div>
                      Phone Number
                    </Label>
                    <Input
                      id="phone"
                      value={profileData.phone}
                      onChange={(e) => setProfileData({...profileData, phone: e.target.value})}
                      placeholder="+66 XX XXX XXXX"
                      className="h-11"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="organization" className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-muted/50">
                        <Building className="h-3.5 w-3.5" />
                      </div>
                      Organization
                    </Label>
                    <Input
                      id="organization"
                      value={profileData.organization}
                      disabled
                      className="h-11 bg-muted/50 cursor-not-allowed"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button 
                  onClick={handleProfileUpdate}
                  disabled={loading}
                  className="min-h-[44px] px-6"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Save Changes
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="password">
          <Card className="relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent" />
            <CardHeader className="relative">
              <CardTitle className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                Security Settings
              </CardTitle>
              <CardDescription>
                Manage your password and security preferences
              </CardDescription>
            </CardHeader>
            <CardContent className="relative space-y-6">
              <div className="space-y-2">
                <Label htmlFor="currentPassword" className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-muted/50">
                    <Key className="h-3.5 w-3.5" />
                  </div>
                  Current Password
                </Label>
                <div className="relative">
                  <Input
                    id="currentPassword"
                    type={showCurrentPassword ? "text" : "password"}
                    value={passwordData.currentPassword}
                    onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
                    placeholder="Enter your current password"
                    className="h-11 pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-11 px-3 hover:bg-transparent"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  >
                    {showCurrentPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label htmlFor="newPassword" className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-muted/50">
                    <Key className="h-3.5 w-3.5" />
                  </div>
                  New Password
                </Label>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showNewPassword ? "text" : "password"}
                    value={passwordData.newPassword}
                    onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
                    placeholder="Enter a strong new password"
                    className="h-11 pr-10"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="absolute right-0 top-0 h-11 px-3 hover:bg-transparent"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                  >
                    {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-muted/50">
                    <Key className="h-3.5 w-3.5" />
                  </div>
                  Confirm New Password
                </Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                  placeholder="Re-enter your new password"
                  className="h-11"
                />
              </div>

              <Alert className="bg-muted/50 border-muted">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Password Requirements:</strong>
                  <ul className="mt-2 space-y-1 text-sm">
                    <li className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${passwordData.newPassword.length >= 8 ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      At least 8 characters long
                    </li>
                    <li className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${/[A-Z]/.test(passwordData.newPassword) ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      Contains uppercase letter
                    </li>
                    <li className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${/[a-z]/.test(passwordData.newPassword) ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      Contains lowercase letter
                    </li>
                    <li className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${/[0-9]/.test(passwordData.newPassword) ? 'bg-green-500' : 'bg-muted-foreground'}`} />
                      Contains number
                    </li>
                  </ul>
                </AlertDescription>
              </Alert>

              <div className="flex justify-end pt-2">
                <Button 
                  onClick={handlePasswordChange}
                  disabled={loading || !passwordData.currentPassword || !passwordData.newPassword}
                  className="min-h-[44px] px-6"
                >
                  {loading ? (
                    <>
                      <div className="w-4 h-4 mr-2 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      Updating...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4 mr-2" />
                      Update Password
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}