/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback } from 'react';
import { toast } from 'sonner';

export interface ApiEndpoint {
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

export interface ApiResponse {
  status: number;
  headers: Record<string, string>;
  data: any;
  timing: number;
}

export const useApiExplorer = () => {
  const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint | null>(null);
  const [apiParams, setApiParams] = useState<Record<string, string>>({});
  const [apiBody, setApiBody] = useState('');
  const [apiResponse, setApiResponse] = useState<ApiResponse | null>(null);
  const [apiLoading, setApiLoading] = useState(false);

  const baseUrl = '';

  const apiEndpoints: ApiEndpoint[] = [
    {
      method: 'GET',
      path: '/api/v1/certificates',
      description: 'List all certificates',
      params: []
    },
    {
      method: 'POST',
      path: '/api/v1/certificates',
      description: 'Create a new certificate',
      params: [],
      body: {
        deviceId: 'device-123',
        organizationId: 'org-456',
        commonName: 'device-123.iot.example.com',
        keyAlgorithm: 'rsa',
        keySize: 2048
      }
    },
    {
      method: 'GET',
      path: '/api/v1/certificates/{certificateId}',
      description: 'Get certificate details',
      params: [
        { name: 'certificateId', required: true, description: 'Certificate ID' }
      ]
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/{deviceId}/renew',
      description: 'Renew a certificate',
      params: [
        { name: 'deviceId', required: true, description: 'Device ID' }
      ]
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/{deviceId}/revoke',
      description: 'Revoke a certificate',
      params: [
        { name: 'deviceId', required: true, description: 'Device ID' }
      ],
      body: {
        reason: 'keyCompromise'
      }
    },
    {
      method: 'GET',
      path: '/api/v1/certificates/audit-trail',
      description: 'Get certificate audit trail',
      params: []
    },
    {
      method: 'POST',
      path: '/api/v1/certificates/bulk',
      description: 'Perform bulk operations on certificates',
      params: [],
      body: {
        action: 'renew',
        device_ids: ['device-1', 'device-2']
      }
    }
  ];

  const copyEndpointAsCurl = useCallback((endpoint: ApiEndpoint) => {
    let curlCommand = `curl -X ${endpoint.method} ${window.location.origin}${endpoint.path} \\\n  -H "Authorization: Bearer YOUR_TOKEN" \\\n  -H "Content-Type: application/json"`;
    
    if (endpoint.body) {
      curlCommand += ` \\\n  -d '${JSON.stringify(endpoint.body, null, 2)}'`;
    }
    
    navigator.clipboard.writeText(curlCommand);
    toast.success('Copied', {
      description: 'cURL command copied to clipboard'
    });
  }, []);

  const executeApiCall = useCallback(async () => {
    if (!selectedEndpoint) {
      toast.error('No endpoint selected', {
        description: 'Please select an endpoint to test'
      });
      return;
    }

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
      
      // Validate required parameters
      if (selectedEndpoint.params) {
        const missingParams = selectedEndpoint.params
          .filter(p => p.required && !apiParams[p.name])
          .map(p => p.name);
        
        if (missingParams.length > 0) {
          toast.error('Missing required parameters', {
            description: `Please provide: ${missingParams.join(', ')}`
          });
          setApiLoading(false);
          return;
        }
      }
      
      const startTime = Date.now();
      const response = await fetch(url, {
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
      
      if (response.ok) {
        toast.success('Request Successful', {
          description: `${selectedEndpoint.method} ${url} completed in ${timing}ms`
        });
      } else {
        toast.error(`Request Failed (${response.status})`, {
          description: data.error || 'An error occurred'
        });
      }
    } catch (error: any) {
      setApiResponse({
        status: 0,
        headers: {},
        data: { error: error.message },
        timing: 0
      });
      toast.error('Request Failed', {
        description: error.message || 'Network error occurred'
      });
    } finally {
      setApiLoading(false);
    }
  }, [selectedEndpoint, apiParams, apiBody, baseUrl]);

  const updateApiParam = useCallback((paramName: string, value: string) => {
    setApiParams(prev => ({
      ...prev,
      [paramName]: value
    }));
  }, []);

  const resetApiExplorer = useCallback(() => {
    setSelectedEndpoint(null);
    setApiParams({});
    setApiBody('');
    setApiResponse(null);
  }, []);

  const formatApiResponse = useCallback((response: ApiResponse) => {
    return JSON.stringify(response, null, 2);
  }, []);

  const getStatusBadgeVariant = useCallback((status: number) => {
    if (status >= 200 && status < 300) return 'success';
    if (status >= 300 && status < 400) return 'warning';
    if (status >= 400 && status < 500) return 'destructive';
    if (status >= 500) return 'destructive';
    return 'secondary';
  }, []);

  return {
    apiEndpoints,
    selectedEndpoint,
    setSelectedEndpoint,
    apiParams,
    apiBody,
    setApiBody,
    apiResponse,
    apiLoading,
    baseUrl,
    copyEndpointAsCurl,
    executeApiCall,
    updateApiParam,
    resetApiExplorer,
    formatApiResponse,
    getStatusBadgeVariant
  };
};