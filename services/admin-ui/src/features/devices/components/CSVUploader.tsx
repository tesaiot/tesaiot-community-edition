/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * CSV Uploader - Excel Grid Style Preview
 * Provides file upload, validation preview, and bulk import
 */

import React, { useState, useCallback } from 'react';
import { Upload, AlertTriangle, CheckCircle, X, FileUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { tesaApi } from '@/services/api/tesaApi';

interface CSVUploaderProps {
  onDevicesImported?: (count: number) => void;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  device_count: number;
  preview: any[];
}

export const CSVUploader: React.FC<CSVUploaderProps> = ({ onDevicesImported }) => {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [csvContent, setCSVContent] = useState<string>('');
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (selectedFile: File) => {
    if (!selectedFile.name.endsWith('.csv')) {
      toast({
        title: 'Invalid File Type',
        description: 'Please upload a CSV file (.csv)',
        variant: 'destructive',
      });
      return;
    }

    setFile(selectedFile);
    setValidationResult(null);

    // Read file content
    const reader = new FileReader();
    reader.onload = async (e) => {
      const content = e.target?.result as string;
      setCSVContent(content);

      // Auto-validate
      await validateCSV(content);
    };
    reader.readAsText(selectedFile);
  };

  const validateCSV = async (content: string) => {
    setIsValidating(true);
    try {
      const response = await tesaApi.post('/devices/bulk-import/validate-csv', {
        csv_content: content,
      });

      setValidationResult(response.data);

      if (response.data.valid) {
        toast({
          title: 'Validation Successful',
          description: `${response.data.device_count} devices ready for import`,
        });
      } else {
        toast({
          title: 'Validation Failed',
          description: `Found ${response.data.errors.length} errors`,
          variant: 'destructive',
        });
      }
    } catch (error: any) {
      console.error('Validation error:', error);
      toast({
        title: 'Validation Error',
        description: error.response?.data?.error || 'Failed to validate CSV',
        variant: 'destructive',
      });
      setValidationResult({
        valid: false,
        errors: [error.response?.data?.error || 'Validation failed'],
        warnings: [],
        device_count: 0,
        preview: [],
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleImport = async () => {
    if (!csvContent || !validationResult?.valid) return;

    setIsImporting(true);
    try {
      const response = await tesaApi.post('/devices/bulk-import', {
        file_format: 'csv',
        csv_content: csvContent,
        options: {
          auto_activate: true,
          generate_certificates: false,
          skip_duplicates: true,
        },
      });

      toast({
        title: 'Import Started',
        description: `Importing ${validationResult.device_count} devices...`,
      });

      // Refresh device list
      if (onDevicesImported) {
        onDevicesImported(validationResult.device_count);
      }

      // Reset
      setFile(null);
      setCSVContent('');
      setValidationResult(null);
    } catch (error: any) {
      console.error('Import error:', error);
      toast({
        title: 'Import Failed',
        description: error.response?.data?.error || 'Failed to import devices',
        variant: 'destructive',
      });
    } finally {
      setIsImporting(false);
    }
  };

  const clearFile = () => {
    setFile(null);
    setCSVContent('');
    setValidationResult(null);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload CSV File</CardTitle>
        <CardDescription>
          Drag and drop or click to select a CSV file containing device information
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* File Upload Area */}
        {!file && (
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium mb-2">Drop CSV file here</p>
            <p className="text-sm text-muted-foreground mb-4">or</p>
            <Button variant="outline" onClick={() => document.getElementById('csv-upload')?.click()}>
              <FileUp className="h-4 w-4 mr-2" />
              Browse Files
            </Button>
            <input
              id="csv-upload"
              type="file"
              accept=".csv"
              onChange={handleFileInput}
              className="hidden"
            />
          </div>
        )}

        {/* File Selected */}
        {file && (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <FileUp className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={clearFile}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Validation Progress */}
            {isValidating && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Validating CSV...</p>
                <Progress value={undefined} className="h-2" />
              </div>
            )}

            {/* Validation Results */}
            {validationResult && (
              <div className="space-y-4">
                {/* Summary */}
                <div className="flex items-center gap-2">
                  {validationResult.valid ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                  )}
                  <span className="font-medium">
                    {validationResult.valid ? 'Validation Passed' : 'Validation Failed'}
                  </span>
                  <Badge variant={validationResult.valid ? 'default' : 'destructive'}>
                    {validationResult.device_count} devices
                  </Badge>
                </div>

                {/* Errors */}
                {validationResult.errors.length > 0 && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Errors ({validationResult.errors.length})</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1">
                        {validationResult.errors.slice(0, 5).map((error, idx) => (
                          <li key={idx} className="text-sm">
                            {error}
                          </li>
                        ))}
                        {validationResult.errors.length > 5 && (
                          <li className="text-sm font-medium">
                            ... and {validationResult.errors.length - 5} more errors
                          </li>
                        )}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Warnings */}
                {validationResult.warnings.length > 0 && (
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertTitle>Warnings ({validationResult.warnings.length})</AlertTitle>
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1">
                        {validationResult.warnings.map((warning, idx) => (
                          <li key={idx} className="text-sm">
                            {warning}
                          </li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Preview Table */}
                {validationResult.preview.length > 0 && (
                  <div className="border rounded-lg overflow-hidden">
                    <div className="bg-muted px-4 py-2">
                      <p className="text-sm font-medium">Preview (first 5 devices)</p>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="px-4 py-2 text-left font-medium">Device ID</th>
                            <th className="px-4 py-2 text-left font-medium">Name</th>
                            <th className="px-4 py-2 text-left font-medium">Type</th>
                            <th className="px-4 py-2 text-left font-medium">Auth Mode</th>
                            <th className="px-4 py-2 text-left font-medium">Trust M UID</th>
                          </tr>
                        </thead>
                        <tbody>
                          {validationResult.preview.map((device, idx) => (
                            <tr key={idx} className="border-t">
                              <td className="px-4 py-2">{device.device_id}</td>
                              <td className="px-4 py-2">{device.name}</td>
                              <td className="px-4 py-2">
                                <Badge variant="outline">{device.type}</Badge>
                              </td>
                              <td className="px-4 py-2">
                                <Badge>{device.auth_mode}</Badge>
                              </td>
                              <td className="px-4 py-2 font-mono text-xs">
                                {device.trustm_uid ? device.trustm_uid.substring(0, 16) + '...' : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Import Button */}
                {validationResult.valid && (
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={clearFile}>
                      Cancel
                    </Button>
                    <Button onClick={handleImport} disabled={isImporting}>
                      {isImporting ? 'Importing...' : `Import ${validationResult.device_count} Devices`}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
