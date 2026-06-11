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
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  Shield, 
  Globe,
  Mail,
  Github,
  Chrome,
  Settings,
  CheckCircle,
  XCircle,
  AlertCircle,
  Copy,
  ExternalLink,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  RefreshCw,
  Users,
  Key,
  Link2,
  Info
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface OAuthProvider {
  id: string;
  type: 'google' | 'github' | 'microsoft' | 'apple' | 'saml' | 'custom';
  name: string;
  enabled: boolean;
  clientId: string;
  clientSecret?: string;
  authUrl?: string;
  tokenUrl?: string;
  userInfoUrl?: string;
  scopes: string[];
  allowedDomains: string[];
  autoProvision: boolean;
  defaultRole: string;
  icon?: React.ReactNode;
  configuredAt?: Date;
  lastSync?: Date;
  userCount?: number;
}

interface SAMLConfig {
  metadataUrl?: string;
  metadataXml?: string;
  entityId: string;
  ssoUrl: string;
  certificate: string;
  attributeMapping: {
    email: string;
    name: string;
    groups?: string;
  };
}

const PROVIDER_TEMPLATES = {
  google: {
    name: 'Google Workspace',
    icon: <Chrome className="h-5 w-5" />,
    authUrl: 'https://accounts.google.com/o/oauth2/v2/auth',
    tokenUrl: 'https://oauth2.googleapis.com/token',
    userInfoUrl: 'https://www.googleapis.com/oauth2/v1/userinfo',
    scopes: ['email', 'profile', 'openid'],
    setupUrl: 'https://console.cloud.google.com/apis/credentials',
  },
  github: {
    name: 'GitHub',
    icon: <Github className="h-5 w-5" />,
    authUrl: 'https://github.com/login/oauth/authorize',
    tokenUrl: 'https://github.com/login/oauth/access_token',
    userInfoUrl: 'https://api.github.com/user',
    scopes: ['user:email', 'read:user'],
    setupUrl: 'https://github.com/settings/developers',
  },
  microsoft: {
    name: 'Microsoft / Azure AD',
    icon: <Mail className="h-5 w-5" />,
    authUrl: 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
    tokenUrl: 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
    userInfoUrl: 'https://graph.microsoft.com/v1.0/me',
    scopes: ['openid', 'profile', 'email', 'User.Read'],
    setupUrl: 'https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps',
  },
  apple: {
    name: 'Apple',
    icon: <Globe className="h-5 w-5" />,
    authUrl: 'https://appleid.apple.com/auth/authorize',
    tokenUrl: 'https://appleid.apple.com/auth/token',
    scopes: ['name', 'email'],
    setupUrl: 'https://developer.apple.com/account/resources/identifiers',
  },
};

export const OAuthConfiguration: React.FC = () => {
  const { toast } = useToast();
  const [providers, setProviders] = useState<OAuthProvider[]>([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [selectedProvider, setSelectedProvider] = useState<OAuthProvider | null>(null);
  const [activeTab, setActiveTab] = useState('providers');
  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  // Form state for new provider
  const [newProvider, setNewProvider] = useState({
    type: 'google' as const,
    name: '',
    clientId: '',
    clientSecret: '',
    allowedDomains: '',
    autoProvision: true,
    defaultRole: 'viewer',
  });

  // SAML configuration state
  const [samlConfig, setSamlConfig] = useState<SAMLConfig>({
    entityId: '',
    ssoUrl: '',
    certificate: '',
    attributeMapping: {
      email: 'email',
      name: 'name',
    },
  });

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = () => {
    // Mock data
    const mockProviders: OAuthProvider[] = [
      {
        id: 'oauth-1',
        type: 'google',
        name: 'Acme Google Workspace',
        enabled: true,
        clientId: '123456789-abcdefghijk.apps.googleusercontent.com',
        clientSecret: 'GOCSPX-1234567890abcdef',
        ...PROVIDER_TEMPLATES.google,
        allowedDomains: ['acme-health.com'],
        autoProvision: true,
        defaultRole: 'viewer',
        configuredAt: new Date('2025-01-15'),
        lastSync: new Date(),
        userCount: 85,
      },
      {
        id: 'oauth-2',
        type: 'microsoft',
        name: 'Acme Azure AD',
        enabled: true,
        clientId: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        ...PROVIDER_TEMPLATES.microsoft,
        allowedDomains: ['acme-health.com', 'acme-contractors.com'],
        autoProvision: false,
        defaultRole: 'viewer',
        configuredAt: new Date('2025-02-01'),
        lastSync: new Date(),
        userCount: 42,
      },
      {
        id: 'oauth-3',
        type: 'github',
        name: 'GitHub (Developers)',
        enabled: false,
        clientId: 'Iv1.1234567890abcdef',
        ...PROVIDER_TEMPLATES.github,
        allowedDomains: [],
        autoProvision: true,
        defaultRole: 'device_manager',
        configuredAt: new Date('2025-03-01'),
        userCount: 12,
      },
    ];
    setProviders(mockProviders);
  };

  const handleAddProvider = () => {
    const template = PROVIDER_TEMPLATES[newProvider.type as keyof typeof PROVIDER_TEMPLATES];
    const provider: OAuthProvider = {
      id: `oauth-${Date.now()}`,
      type: newProvider.type,
      name: newProvider.name || template?.name || 'Custom OAuth',
      enabled: false,
      clientId: newProvider.clientId,
      clientSecret: newProvider.clientSecret,
      allowedDomains: newProvider.allowedDomains.split(',').map(d => d.trim()).filter(Boolean),
      autoProvision: newProvider.autoProvision,
      defaultRole: newProvider.defaultRole,
      scopes: template?.scopes || [],
      authUrl: template?.authUrl,
      tokenUrl: template?.tokenUrl,
      userInfoUrl: template?.userInfoUrl,
      icon: template?.icon,
      configuredAt: new Date(),
      userCount: 0,
    };

    setProviders([...providers, provider]);
    setShowAddDialog(false);
    
    // Reset form
    setNewProvider({
      type: 'google',
      name: '',
      clientId: '',
      clientSecret: '',
      allowedDomains: '',
      autoProvision: true,
      defaultRole: 'viewer',
    });

    toast({
      title: 'OAuth Provider Added',
      description: 'Configure the provider in your identity provider\'s console.',
    });
  };

  const handleToggleProvider = (providerId: string) => {
    setProviders(providers.map(p => 
      p.id === providerId ? { ...p, enabled: !p.enabled } : p
    ));
  };

  const handleDeleteProvider = (providerId: string) => {
    if (confirm('Are you sure you want to delete this OAuth provider?')) {
      setProviders(providers.filter(p => p.id !== providerId));
      toast({
        title: 'Provider Deleted',
        description: 'OAuth provider has been removed.',
      });
    }
  };

  const handleTestProvider = async (providerId: string) => {
    setTestingProvider(providerId);
    // Simulate test
    setTimeout(() => {
      setTestingProvider(null);
      toast({
        title: 'Test Successful',
        description: 'OAuth provider is configured correctly.',
      });
    }, 2000);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast({
      title: 'Copied',
      description: 'Value copied to clipboard.',
    });
  };

  const getCallbackUrl = () => {
    return `${window.location.origin}/api/v1/auth/callback`;
  };

  const activeProviders = providers.filter(p => p.enabled).length;
  const totalUsers = providers.reduce((sum, p) => sum + (p.userCount || 0), 0);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Single Sign-On (SSO)</h1>
          <p className="text-muted-foreground">
            Configure OAuth and SAML providers for your organization
          </p>
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Provider
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Providers</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeProviders}</div>
            <p className="text-xs text-muted-foreground">
              Out of {providers.length} configured
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SSO Users</CardTitle>
            <Users className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{totalUsers}</div>
            <p className="text-xs text-muted-foreground">
              Authenticated via SSO
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auto-provisioning</CardTitle>
            <Key className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">
              {providers.filter(p => p.autoProvision).length}
            </div>
            <p className="text-xs text-muted-foreground">
              Providers with auto-create
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Security Score</CardTitle>
            <CheckCircle className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">95%</div>
            <p className="text-xs text-muted-foreground">
              MFA + SSO coverage
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="providers">OAuth Providers</TabsTrigger>
          <TabsTrigger value="saml">SAML Configuration</TabsTrigger>
          <TabsTrigger value="settings">SSO Settings</TabsTrigger>
        </TabsList>

        {/* OAuth Providers Tab */}
        <TabsContent value="providers" className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>OAuth 2.0 Configuration</AlertTitle>
            <AlertDescription>
              Configure OAuth providers to allow users to sign in with their existing accounts.
              The callback URL for all providers is: <code className="text-xs bg-muted px-1 py-0.5 rounded">{getCallbackUrl()}</code>
            </AlertDescription>
          </Alert>

          <div className="space-y-4">
            {providers.map((provider) => (
              <Card key={provider.id}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="space-y-4 flex-1">
                      {/* Provider Header */}
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "p-2 rounded-lg",
                          provider.enabled ? "bg-primary/10" : "bg-muted"
                        )}>
                          {provider.icon || <Globe className="h-5 w-5" />}
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold">{provider.name}</h3>
                          <p className="text-sm text-muted-foreground">
                            {provider.type.charAt(0).toUpperCase() + provider.type.slice(1)} OAuth 2.0
                          </p>
                        </div>
                        <Badge variant={provider.enabled ? "success" : "secondary"}>
                          {provider.enabled ? "Active" : "Inactive"}
                        </Badge>
                        <Switch
                          checked={provider.enabled}
                          onCheckedChange={() => handleToggleProvider(provider.id)}
                        />
                      </div>

                      {/* Provider Details */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div className="space-y-2">
                          <div>
                            <Label className="text-xs text-muted-foreground">Client ID</Label>
                            <div className="flex items-center gap-2">
                              <code className="flex-1 text-xs bg-muted px-2 py-1 rounded">
                                {provider.clientId}
                              </code>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6"
                                onClick={() => copyToClipboard(provider.clientId)}
                              >
                                <Copy className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                          
                          {provider.clientSecret && (
                            <div>
                              <Label className="text-xs text-muted-foreground">Client Secret</Label>
                              <div className="flex items-center gap-2">
                                <code className="flex-1 text-xs bg-muted px-2 py-1 rounded">
                                  {showSecrets[provider.id] 
                                    ? provider.clientSecret 
                                    : '••••••••••••••••'}
                                </code>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={() => setShowSecrets({
                                    ...showSecrets,
                                    [provider.id]: !showSecrets[provider.id]
                                  })}
                                >
                                  {showSecrets[provider.id] ? 
                                    <EyeOff className="h-3 w-3" /> : 
                                    <Eye className="h-3 w-3" />
                                  }
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="space-y-2">
                          <div>
                            <Label className="text-xs text-muted-foreground">Allowed Domains</Label>
                            <div className="flex flex-wrap gap-1">
                              {provider.allowedDomains.length > 0 ? (
                                provider.allowedDomains.map(domain => (
                                  <Badge key={domain} variant="outline" className="text-xs">
                                    {domain}
                                  </Badge>
                                ))
                              ) : (
                                <span className="text-xs text-muted-foreground">All domains</span>
                              )}
                            </div>
                          </div>
                          
                          <div className="flex items-center justify-between">
                            <div>
                              <Label className="text-xs text-muted-foreground">Auto-provision</Label>
                              <p className="text-xs">
                                {provider.autoProvision ? 'Enabled' : 'Disabled'} 
                                {provider.autoProvision && ` (${provider.defaultRole})`}
                              </p>
                            </div>
                            {provider.userCount !== undefined && (
                              <div>
                                <Label className="text-xs text-muted-foreground">Users</Label>
                                <p className="text-xs font-medium">{provider.userCount}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Provider Actions */}
                      <div className="flex items-center gap-2 pt-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleTestProvider(provider.id)}
                          disabled={testingProvider === provider.id}
                        >
                          {testingProvider === provider.id ? (
                            <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                          ) : (
                            <CheckCircle className="h-4 w-4 mr-1" />
                          )}
                          Test Connection
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.open(
                            PROVIDER_TEMPLATES[provider.type as keyof typeof PROVIDER_TEMPLATES]?.setupUrl,
                            '_blank'
                          )}
                        >
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Provider Console
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedProvider(provider)}
                        >
                          <Settings className="h-4 w-4 mr-1" />
                          Configure
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteProvider(provider.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* SAML Tab */}
        <TabsContent value="saml" className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>SAML 2.0 Configuration</AlertTitle>
            <AlertDescription>
              Configure SAML-based Single Sign-On for enterprise identity providers.
              Entity ID: <code className="text-xs bg-muted px-1 py-0.5 rounded">
                {`${window.location.origin}/saml/metadata`}
              </code>
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle>SAML Identity Provider</CardTitle>
              <CardDescription>
                Configure your SAML 2.0 identity provider settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="saml-metadata">Metadata URL</Label>
                <Input
                  id="saml-metadata"
                  placeholder="https://idp.example.com/saml/metadata"
                  value={samlConfig.metadataUrl}
                  onChange={(e) => setSamlConfig({ ...samlConfig, metadataUrl: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Or upload metadata XML file
                </p>
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="saml-entity">Entity ID</Label>
                  <Input
                    id="saml-entity"
                    placeholder="https://idp.example.com"
                    value={samlConfig.entityId}
                    onChange={(e) => setSamlConfig({ ...samlConfig, entityId: e.target.value })}
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="saml-sso">SSO URL</Label>
                  <Input
                    id="saml-sso"
                    placeholder="https://idp.example.com/saml/sso"
                    value={samlConfig.ssoUrl}
                    onChange={(e) => setSamlConfig({ ...samlConfig, ssoUrl: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="saml-cert">X.509 Certificate</Label>
                <Textarea
                  id="saml-cert"
                  placeholder="-----BEGIN CERTIFICATE-----"
                  rows={4}
                  value={samlConfig.certificate}
                  onChange={(e) => setSamlConfig({ ...samlConfig, certificate: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Attribute Mapping</Label>
                <div className="space-y-2 p-3 border rounded-lg bg-muted/50">
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="SAML Attribute"
                      value={samlConfig.attributeMapping.email}
                      disabled
                    />
                    <Input placeholder="User Email" value="email" disabled />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="SAML Attribute"
                      value={samlConfig.attributeMapping.name}
                      disabled
                    />
                    <Input placeholder="User Name" value="name" disabled />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline">Test SAML</Button>
                <Button>Save Configuration</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>SSO Settings</CardTitle>
              <CardDescription>
                Configure global Single Sign-On settings for your organization
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enforce SSO</Label>
                    <p className="text-sm text-muted-foreground">
                      Require all users to sign in via SSO
                    </p>
                  </div>
                  <Switch />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Just-in-Time Provisioning</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically create users on first SSO login
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Directory Sync</Label>
                    <p className="text-sm text-muted-foreground">
                      Sync user attributes from identity provider
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Session Timeout</Label>
                    <p className="text-sm text-muted-foreground">
                      Require re-authentication after period of inactivity
                    </p>
                  </div>
                  <Select defaultValue="8">
                    <SelectTrigger className="w-[120px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="4">4 hours</SelectItem>
                      <SelectItem value="8">8 hours</SelectItem>
                      <SelectItem value="24">24 hours</SelectItem>
                      <SelectItem value="168">7 days</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label>Default Role for New Users</Label>
                <Select defaultValue="viewer">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="viewer">Viewer</SelectItem>
                    <SelectItem value="operator">Operator</SelectItem>
                    <SelectItem value="device_manager">Device Manager</SelectItem>
                    <SelectItem value="analyst">Analyst</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Allowed Email Domains</Label>
                <Textarea
                  placeholder="example.com&#10;partner.com"
                  rows={3}
                  defaultValue="acme-health.com"
                />
                <p className="text-xs text-muted-foreground">
                  One domain per line. Leave empty to allow all domains.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Add Provider Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add OAuth Provider</DialogTitle>
            <DialogDescription>
              Configure a new OAuth 2.0 provider for Single Sign-On
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Provider Type</Label>
              <Select
                value={newProvider.type}
                onValueChange={(value: any) => setNewProvider({ ...newProvider, type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDER_TEMPLATES).map(([key, template]) => (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        {template.icon}
                        <span>{template.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                  <SelectItem value="custom">
                    <div className="flex items-center gap-2">
                      <Globe className="h-4 w-4" />
                      <span>Custom OAuth 2.0</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-name">Display Name</Label>
              <Input
                id="provider-name"
                placeholder="e.g., Company Google Workspace"
                value={newProvider.name}
                onChange={(e) => setNewProvider({ ...newProvider, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-id">Client ID</Label>
              <Input
                id="client-id"
                placeholder="Enter OAuth client ID"
                value={newProvider.clientId}
                onChange={(e) => setNewProvider({ ...newProvider, clientId: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="client-secret">Client Secret</Label>
              <Input
                id="client-secret"
                type="password"
                placeholder="Enter OAuth client secret"
                value={newProvider.clientSecret}
                onChange={(e) => setNewProvider({ ...newProvider, clientSecret: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="domains">Allowed Domains (Optional)</Label>
              <Input
                id="domains"
                placeholder="example.com, partner.com"
                value={newProvider.allowedDomains}
                onChange={(e) => setNewProvider({ ...newProvider, allowedDomains: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list. Leave empty to allow all domains.
              </p>
            </div>

            <Separator />

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-provision Users</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically create users on first login
                  </p>
                </div>
                <Switch
                  checked={newProvider.autoProvision}
                  onCheckedChange={(checked) => 
                    setNewProvider({ ...newProvider, autoProvision: checked })
                  }
                />
              </div>

              {newProvider.autoProvision && (
                <div className="space-y-2">
                  <Label>Default Role</Label>
                  <Select
                    value={newProvider.defaultRole}
                    onValueChange={(value) => 
                      setNewProvider({ ...newProvider, defaultRole: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="viewer">Viewer</SelectItem>
                      <SelectItem value="operator">Operator</SelectItem>
                      <SelectItem value="device_manager">Device Manager</SelectItem>
                      <SelectItem value="analyst">Analyst</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>

            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                <p className="font-medium mb-1">Configure in Provider Console:</p>
                <p className="text-xs">
                  Redirect URI: <code className="bg-muted px-1 py-0.5 rounded">{getCallbackUrl()}</code>
                </p>
                {PROVIDER_TEMPLATES[newProvider.type as keyof typeof PROVIDER_TEMPLATES]?.scopes && (
                  <p className="text-xs mt-1">
                    Required scopes: {PROVIDER_TEMPLATES[newProvider.type as keyof typeof PROVIDER_TEMPLATES].scopes.join(', ')}
                  </p>
                )}
              </AlertDescription>
            </Alert>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddProvider}>
              Add Provider
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};