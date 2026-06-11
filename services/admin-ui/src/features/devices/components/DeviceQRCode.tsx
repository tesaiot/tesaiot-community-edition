/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Device QR Code Display
 * Shows QR code for Trust M devices in device details
 */

import React, { useState, useEffect } from 'react';
import { QrCode, Download, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { tesaApi } from '@/services/api/tesaApi';

interface DeviceQRCodeProps {
  deviceId: string;
  trustmUid?: string;
}

export const DeviceQRCode: React.FC<DeviceQRCodeProps> = ({ deviceId, trustmUid }) => {
  const { toast } = useToast();
  const [qrCodeData, setQRCodeData] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qrType] = useState<'factory' | 'customer'>('factory'); // Phase 1: Factory only

  useEffect(() => {
    if (trustmUid) {
      loadQRCode();
    }
  }, [deviceId, trustmUid]);

  const loadQRCode = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await tesaApi.get(`/api/v1/devices/${deviceId}/qrcode`, {
        params: { format: 'png', size: 10 },
      });

      // Validate response structure
      // Note: API returns data directly, Axios wraps in .data
      if (!response) {
        throw new Error('Invalid response from server');
      }

      const responseData = response.data || response;

      if (!responseData.image_base64) {
        throw new Error('QR code image data not found in response');
      }

      setQRCodeData(responseData.image_base64);
    } catch (error: any) {
      console.error('Error loading QR code:', error);
      const errorMessage = error.response?.data?.message
        || error.message
        || 'Failed to load QR code';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadQR = () => {
    if (!qrCodeData) return;

    // Convert base64 to blob and download
    const link = document.createElement('a');
    link.href = qrCodeData;
    link.download = `${deviceId}_qrcode.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    toast({
      title: 'QR Code Downloaded',
      description: `QR code for ${deviceId} has been downloaded`,
    });
  };

  if (!trustmUid) {
    return (
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          This device does not have a Trust M UID. QR codes are only available for Trust M devices.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Card className="border-2">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1.5">
            <CardTitle className="flex items-center gap-2 text-xl">
              <QrCode className="h-5 w-5" />
              Device QR Code
              <Badge variant="secondary" className="ml-2">Phase 1: Factory</Badge>
            </CardTitle>
            <CardDescription className="text-base">
              QR code for factory registration and bulk import workflows
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* QR Code Display */}
        {isLoading && (
          <div className="flex items-center justify-center p-8 border rounded-lg">
            <p className="text-muted-foreground">Loading QR code...</p>
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {qrCodeData && !isLoading && (
          <div className="space-y-6">
            {/* QR Code Type Info */}
            <Alert className="border-blue-200 bg-blue-50">
              <AlertCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-sm text-blue-900">
                <strong>Factory Registration QR Code</strong> - URL-based format compatible with all mobile cameras. Contains Trust M UID and Device ID for factory workflows.
              </AlertDescription>
            </Alert>

            {/* QR Code Image */}
            <div className="flex justify-center p-6 border-2 border-dashed rounded-lg bg-white">
              <img src={qrCodeData} alt="Device QR Code" className="w-72 h-72" />
            </div>

            {/* QR Content Info */}
            <div className="space-y-3 p-4 bg-muted/50 rounded-lg border">
              <div className="flex flex-col gap-2">
                <span className="text-sm font-semibold">QR URL:</span>
                <code className="text-xs bg-background px-3 py-2 rounded border break-all font-mono">
                  https://provision.{typeof window !== 'undefined' ? window.location.hostname : 'localhost'}/factory?uid={trustmUid}&device={deviceId}
                </code>
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-sm font-semibold">OPTIGA™ Trust M UID:</span>
                <code className="text-xs bg-background px-3 py-2 rounded border break-all font-mono">
                  {trustmUid}
                </code>
              </div>
              <div className="flex flex-col gap-2">
                <span className="text-sm font-semibold">Device ID:</span>
                <code className="text-xs bg-background px-3 py-2 rounded border break-all font-mono">
                  {deviceId}
                </code>
              </div>
            </div>

            {/* Download Button */}
            <Button onClick={handleDownloadQR} className="w-full" size="lg">
              <Download className="h-4 w-4 mr-2" />
              Download QR Code (PNG)
            </Button>

            {/* Usage Instructions - Factory Workflow */}
            <div className="space-y-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="font-semibold text-sm text-amber-900 flex items-center gap-2">
                <QrCode className="h-4 w-4" />
                Factory Registration Workflow:
              </p>
              <ol className="list-decimal list-inside space-y-2 text-sm text-amber-900">
                <li>Print QR code and attach to physical device packaging</li>
                <li>Scan with mobile camera → Opens provisioning page with device info</li>
                <li>Copy Trust M UID from URL parameters or page display</li>
                <li>Use UID in bulk import CSV or factory registration tool</li>
                <li>Complete device provisioning with certificate generation</li>
              </ol>
            </div>

            {/* Phase 2 Preview */}
            <div className="space-y-2 p-4 bg-gray-50 border border-gray-200 rounded-lg opacity-60">
              <p className="font-semibold text-sm text-gray-700 flex items-center gap-2">
                <Badge variant="outline" className="text-xs">Coming Soon</Badge>
                Customer Provisioning QR Code
              </p>
              <p className="text-xs text-gray-600">
                URL-based QR code for end-customer onboarding with guided setup experience. Available when product is ready for market.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
