/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Reusable CSR Upload + Validate panel
 * - File/Paste tabs
 * - Calls /api/v1/certificates/validate-csr
 * - Shows success banner and parsed CSR details
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Upload, FileText, X, Info, CheckCircle2, AlertCircle } from 'lucide-react';
import authFetch from '@/utils/auth-fetch';

type CSRDetails = {
  subject: Record<string, string> & { CN?: string; O?: string; OU?: string };
  keyAlgorithm: string;
  keySize: number;
  signatureAlgorithm?: string;
  extensions?: {
    subjectAltName?: string[];
  };
};

interface Props {
  value: string;
  onChange: (csr: string) => void;
  onValidationChange?: (isValid: boolean, details?: CSRDetails | null) => void;
  disabled?: boolean;
}

const CsrUploadPanel: React.FC<Props> = ({ value, onChange, onValidationChange, disabled }) => {
  const [tab, setTab] = useState<'file' | 'paste'>('file');
  const [fileName, setFileName] = useState<string>('');
  const [isValidating, setIsValidating] = useState(false);
  const [error, setError] = useState<string>('');
  const [details, setDetails] = useState<CSRDetails | null>(null);
  const [valid, setValid] = useState<boolean>(false);

  useEffect(() => {
    // auto-validate on content change with debounce
    if (!value) {
      setValid(false);
      setDetails(null);
      setError('');
      onValidationChange?.(false, null);
      return;
    }
    const timer = setTimeout(() => validate(value), 400);
    return () => clearTimeout(timer);
  }, [value]);

  const validate = useCallback(async (csr: string) => {
    setIsValidating(true);
    setError('');
    setValid(false);
    setDetails(null);
    const pemRe = /-----BEGIN CERTIFICATE REQUEST-----[\s\S]+-----END CERTIFICATE REQUEST-----/;
    if (!pemRe.test(csr)) {
      setIsValidating(false);
      setError('Invalid CSR format. Must be PEM with proper headers.');
      onValidationChange?.(false, null);
      return;
    }
    try {
      const res = await authFetch('/api/v1/certificates/validate-csr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csr })
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.message || `HTTP ${res.status}`);
      }
      const j = await res.json();
      const ok = !!j.valid || !!j.isValid;
      setValid(ok);
      setDetails(j.details || null);
      onValidationChange?.(ok, j.details || null);
    } catch (e: any) {
      setError(e?.message || 'Failed to validate CSR');
      onValidationChange?.(false, null);
    } finally {
      setIsValidating(false);
    }
  }, [onValidationChange]);

  const handleFile = async (f: File) => {
    const text = await f.text();
    setFileName(f.name);
    onChange(text.trim());
  };

  const clear = () => {
    setFileName('');
    setError('');
    setDetails(null);
    setValid(false);
    onChange('');
  };

  return (
    <div className="space-y-3">
      <Label className="flex items-center gap-2"><FileText className="h-4 w-4" />Certificate Signing Request (CSR)</Label>

      <Tabs value={tab} onValueChange={(v: any) => {
        setTab(v);
        // Reset validation state when switching tabs to prevent stale errors
        setError('');
        setDetails(null);
        setValid(false);
      }}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="file">Upload File</TabsTrigger>
          <TabsTrigger value="paste">Paste Text</TabsTrigger>
        </TabsList>

        <TabsContent value="file" className="space-y-2">
          <div className="border-2 border-dashed border-border rounded-lg p-6 hover:border-primary/50 transition-colors">
            <input id="csr-file" type="file" accept=".csr,.pem,.txt" className="hidden"
                   disabled={disabled}
                   onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
            <label htmlFor="csr-file" className="flex flex-col items-center gap-2 cursor-pointer">
              <Upload className="h-8 w-8 text-muted-foreground" />
              <span className="text-sm font-medium">Click to upload CSR file</span>
              <span className="text-xs text-muted-foreground">Supports .csr, .pem, .txt files (max 10KB)</span>
            </label>
          </div>
          {fileName && (
            <div className="flex items-center gap-2 p-2 bg-background rounded-md">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm flex-1">{fileName}</span>
              <Button size="sm" variant="ghost" onClick={clear}><X className="h-4 w-4" /></Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="paste">
          <Textarea
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={`Paste CSR here...\n-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----`}
            className="min-h-[200px] font-mono text-xs"
            disabled={disabled}
          />
        </TabsContent>
      </Tabs>

      {valid && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">CSR validated successfully</AlertDescription>
        </Alert>
      )}
      {!valid && error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {details && (
        <Card>
          <CardHeader><CardTitle className="text-sm">CSR Details</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {details.subject?.CN && (
                <div>
                  <div className="text-muted-foreground text-xs">Common Name (CN)</div>
                  <div className="font-medium font-mono">{details.subject.CN}</div>
                </div>
              )}
              <div>
                <div className="text-muted-foreground text-xs">Key Algorithm</div>
                <div className="font-medium">{details.keyAlgorithm}</div>
              </div>
              <div>
                <div className="text-muted-foreground text-xs">Key Size</div>
                <div className="font-medium">{details.keySize} bits</div>
              </div>
              {details.signatureAlgorithm && (
                <div>
                  <div className="text-muted-foreground text-xs">Signature Algorithm</div>
                  <div className="font-medium">{details.signatureAlgorithm}</div>
                </div>
              )}
              {details.subject?.O && (
                <div>
                  <div className="text-muted-foreground text-xs">Organization</div>
                  <div className="font-medium">{details.subject.O}</div>
                </div>
              )}
              {details.subject?.OU && (
                <div>
                  <div className="text-muted-foreground text-xs">Organizational Unit</div>
                  <div className="font-medium">{details.subject.OU}</div>
                </div>
              )}
              {details.extensions?.subjectAltName && (
                <div className="col-span-2">
                  <div className="text-muted-foreground text-xs">Subject Alternative Names</div>
                  <div className="font-medium text-xs mt-1">{details.extensions.subjectAltName.join(', ')}</div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default CsrUploadPanel;

