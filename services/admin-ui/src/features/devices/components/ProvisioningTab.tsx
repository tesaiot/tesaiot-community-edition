/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Provisioning Tab - Trust M Device Bulk Import
 * Provides CSV upload interface for bulk device pre-registration
 */

import React, { useState } from 'react';
import { Upload, Download, FileText, AlertCircle, CheckCircle, XCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { CSVUploader } from './CSVUploader';
import { useToast } from '@/hooks/use-toast';
import { tesaApi } from '@/services/api/tesaApi';

interface ProvisioningTabProps {
  onDevicesImported?: (count: number) => void;
}

export const ProvisioningTab: React.FC<ProvisioningTabProps> = ({ onDevicesImported }) => {
  const { toast } = useToast();
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadTemplate = async () => {
    setIsDownloading(true);
    try {
      const response = await tesaApi.get('/devices/bulk-import/template', {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'device_bulk_import_template.csv');
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      toast({
        title: 'Template Downloaded',
        description: 'CSV template has been downloaded successfully.',
      });
    } catch (error: any) {
      console.error('Error downloading template:', error);
      toast({
        title: 'Download Failed',
        description: error.response?.data?.error || 'Failed to download CSV template',
        variant: 'destructive',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Bulk Device Provisioning
          </CardTitle>
          <CardDescription>
            Pre-register multiple Trust M devices using CSV file upload
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Instructions */}
          <Alert>
            <FileText className="h-4 w-4" />
            <AlertTitle>How to Use Bulk Import</AlertTitle>
            <AlertDescription className="space-y-2">
              <ol className="list-decimal list-inside space-y-1">
                <li>Download the CSV template below</li>
                <li>Fill in device information including Trust M UIDs (54 hex characters)</li>
                <li>Upload the completed CSV file</li>
                <li>Review validation results and fix any errors</li>
                <li>Confirm import to create devices</li>
              </ol>
            </AlertDescription>
          </Alert>

          {/* Download Template Button */}
          <div className="flex items-center gap-4">
            <Button
              onClick={handleDownloadTemplate}
              disabled={isDownloading}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              {isDownloading ? 'Downloading...' : 'Download CSV Template'}
            </Button>
          </div>

          {/* CSV Format Info */}
          <div className="bg-muted p-4 rounded-md">
            <h4 className="font-semibold mb-2">CSV Format</h4>
            <p className="text-sm text-muted-foreground mb-2">
              Required fields: <code>device_id</code>, <code>name</code>, <code>type</code>, <code>auth_mode</code>
            </p>
            <p className="text-sm text-muted-foreground mb-2">
              Optional fields: <code>trustm_uid</code>, <code>location_name</code>, <code>latitude</code>,
              <code>longitude</code>, <code>description</code>, <code>manufacturer</code>, <code>model</code>,
              <code>network_type</code>, <code>firmware_version</code>
            </p>
            <p className="text-sm text-muted-foreground">
              <strong>Trust M UID</strong>: Must be exactly 54 hexadecimal characters (27 bytes)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* CSV Uploader */}
      <CSVUploader onDevicesImported={onDevicesImported} />

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Troubleshooting</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 text-yellow-500" />
            <div>
              <p className="font-medium">Duplicate Trust M UIDs</p>
              <p className="text-sm text-muted-foreground">
                Each Trust M UID must be unique. Check your CSV for duplicates.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 text-yellow-500" />
            <div>
              <p className="font-medium">Invalid UID Format</p>
              <p className="text-sm text-muted-foreground">
                Trust M UIDs must be exactly 54 hexadecimal characters (0-9, A-F).
              </p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 mt-0.5 text-green-500" />
            <div>
              <p className="font-medium">Auto-Activation</p>
              <p className="text-sm text-muted-foreground">
                Devices with Trust M UIDs will auto-activate on first connection using factory certificates.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
