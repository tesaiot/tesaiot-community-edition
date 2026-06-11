/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState } from 'react';
import { Globe, Play, Copy, Info } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { toast } from 'sonner';

interface ApiEndpoint {
  method: string;
  path: string;
  description: string;
  params?: Array<{
    name: string;
    required: boolean;
    description: string;
  }>;
  body?: any;
}

interface ApiResponse {
  status: number;
  headers: Record<string, string>;
  data: any;
  timing: number;
}

interface ApiExplorerViewProps {
  baseUrl: string;
  apiEndpoints: ApiEndpoint[];
}

export const ApiExplorerView: React.FC<ApiExplorerViewProps> = ({
  baseUrl,
  apiEndpoints
}) => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [apiParams, setApiParams] = useState<Record<string, string>>({});
  const [apiBody, setApiBody] = useState('');
  const [apiLoading, setApiLoading] = useState(false);
  const [apiResponse, setApiResponse] = useState<ApiResponse | null>(null);
  const [activeTab, setActiveTab] = useState('endpoints');

  const handleCopyEndpoint = (endpoint: ApiEndpoint) => {
    const curlCommand = `curl -X ${endpoint.method} ${baseUrl}${endpoint.path} \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json"`;
    navigator.clipboard.writeText(curlCommand);
    toast.success('Copied', {
      description: 'cURL command copied to clipboard'
    });
  };

  const handleExecuteApi = async () => {
    if (!selectedEndpoint) return;

    try {
      setApiLoading(true);
      const token = localStorage.getItem('jwt_token');
      let url = selectedEndpoint.path;
      
      // Replace path parameters
      if (apiParams) {
        Object.entries(apiParams).forEach(([key, value]) => {
          url = url.replace(`{${key}}`, value);
        });
      }
      
      const startTime = Date.now();
      const response = await fetch(baseUrl + url, {
        method: selectedEndpoint.method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: selectedEndpoint.method !== 'GET' && apiBody ? apiBody : undefined
      });
      
      const timing = Date.now() - startTime;
      const data = await response.json();
      
      setApiResponse({
        status: response.status,
        headers: Object.fromEntries(response.headers.entries()),
        data,
        timing
      });
    } catch (error: any) {
      setApiResponse({
        status: 0,
        headers: {},
        data: { error: error.message },
        timing: 0
      });
    } finally {
      setApiLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            API Explorer
          </CardTitle>
          <CardDescription>
            Explore and test certificate management APIs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="endpoints">Endpoints</TabsTrigger>
              <TabsTrigger value="playground">Playground</TabsTrigger>
              <TabsTrigger value="examples">Examples</TabsTrigger>
            </TabsList>

            <TabsContent value="endpoints" className="space-y-4">
              <div className="space-y-4">
                {apiEndpoints.map((endpoint, idx) => (
                  <div key={idx} className="border rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge variant={
                        endpoint.method === 'GET' ? 'secondary' :
                        endpoint.method === 'POST' ? 'default' :
                        endpoint.method === 'PUT' ? 'outline' :
                        'destructive'
                      }>
                        {endpoint.method}
                      </Badge>
                      <code className="text-sm font-mono">{endpoint.path}</code>
                    </div>
                    <p className="text-sm text-muted-foreground">{endpoint.description}</p>
                    <div className="flex gap-2">
                      <Button 
                        size="sm" 
                        variant="outline" 
                        onClick={() => {
                          setSelectedEndpoint(endpoint);
                          setApiParams({});
                          setApiBody(endpoint.body ? JSON.stringify(endpoint.body, null, 2) : '');
                          setApiResponse(null);
                          setActiveTab('playground');
                        }}
                      >
                        <Play className="h-3 w-3 mr-1" />
                        Try it out
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleCopyEndpoint(endpoint)}>
                        <Copy className="h-3 w-3 mr-1" />
                        Copy
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="playground" className="space-y-4">
              {selectedEndpoint ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Badge>{selectedEndpoint.method}</Badge>
                    <code className="text-sm">{selectedEndpoint.path}</code>
                  </div>
                  
                  {selectedEndpoint.params && selectedEndpoint.params.length > 0 && (
                    <div className="space-y-2">
                      <Label>Parameters</Label>
                      {selectedEndpoint.params.map((param) => (
                        <div key={param.name} className="space-y-1">
                          <Label className="text-xs">{param.name} {param.required && <span className="text-red-500">*</span>}</Label>
                          <Input
                            placeholder={param.description}
                            value={apiParams[param.name] || ''}
                            onChange={(e) => setApiParams({...apiParams, [param.name]: e.target.value})}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {selectedEndpoint.body && (
                    <div className="space-y-2">
                      <Label>Request Body</Label>
                      <textarea
                        className="w-full h-32 p-2 border rounded-md font-mono text-sm"
                        value={apiBody}
                        onChange={(e) => setApiBody(e.target.value)}
                        placeholder={JSON.stringify(selectedEndpoint.body, null, 2)}
                      />
                    </div>
                  )}
                  
                  <Button onClick={handleExecuteApi} disabled={apiLoading}>
                    {apiLoading ? (
                      <>Loading...</>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Execute
                      </>
                    )}
                  </Button>
                  
                  {apiResponse && (
                    <div className="space-y-2">
                      <Label>Response</Label>
                      <pre className="p-4 bg-muted rounded-md overflow-auto max-h-96">
                        <code className="text-sm">{JSON.stringify(apiResponse, null, 2)}</code>
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Select an endpoint from the Endpoints tab to test it.
                  </AlertDescription>
                </Alert>
              )}
            </TabsContent>

            <TabsContent value="examples" className="space-y-4">
              <div className="space-y-4">
                <div className="border rounded-lg p-4 space-y-2">
                  <h4 className="font-medium">Create a Certificate</h4>
                  <pre className="p-2 bg-muted rounded text-sm overflow-auto">
{`curl -X POST ${baseUrl}/api/v1/certificates \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "deviceId": "device-123",
    "organizationId": "org-456",
    "commonName": "device-123.iot.example.com",
    "keyAlgorithm": "rsa",
    "keySize": 2048
  }'`}
                  </pre>
                </div>
                
                <div className="border rounded-lg p-4 space-y-2">
                  <h4 className="font-medium">Renew a Certificate</h4>
                  <pre className="p-2 bg-muted rounded text-sm overflow-auto">
{`curl -X POST ${baseUrl}/api/v1/certificates/{deviceId}/renew \\
  -H "Authorization: Bearer YOUR_TOKEN"`}
                  </pre>
                </div>
                
                <div className="border rounded-lg p-4 space-y-2">
                  <h4 className="font-medium">Revoke a Certificate</h4>
                  <pre className="p-2 bg-muted rounded text-sm overflow-auto">
{`curl -X POST ${baseUrl}/api/v1/certificates/{deviceId}/revoke \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "reason": "keyCompromise"
  }'`}
                  </pre>
                </div>
              </div>
            </TabsContent>
          </Tabs>
          
          <Alert className="mt-4">
            <Info className="h-4 w-4" />
            <AlertDescription>
              <strong>Authentication:</strong> Most endpoints require JWT authentication. The Explorer automatically includes your current session token.
              <br />
              <strong>Base URL:</strong> All endpoints are relative to <code>{baseUrl}</code>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    </div>
  );
};