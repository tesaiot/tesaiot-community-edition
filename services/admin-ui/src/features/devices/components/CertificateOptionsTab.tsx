/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useCallback, useEffect } from 'react';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  Shield,
  Key,
  Info,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Fingerprint,
  AlertTriangle,
  X,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Download,
  Copy,
  RefreshCw
} from 'lucide-react';
import authFetch from '@/utils/auth-fetch';
import { CertificateTTL, CertificateTTLValue } from '@/components/CertificateTTL';

// Import proper types
import {
  CSRDetails,
  CSRValidationResponse,
  CertificateFormData,
  CSRValidationState,
  CertificateGenerationMethod,
  CertificateType,
  CertificateFormat,
  CSRValidationStatus,
  DevicePublicKey,
  KeyStatus,
  KeyEncryptionStatus,
  KeyAlgorithm,
  PublicKeyGenerationRequest,
  PublicKeyGenerationResponse
} from '@/features/devices/types/device.types';

import {
  FieldValidationError,
  ValidationSeverity,
  CSRFileValidationResult,
  ValidationErrorCodes
} from '@/features/devices/types/validation.types';

// Extended interface for certificate options
interface ExtendedCertificateFormData extends CertificateFormData {
  devicePublicKey?: DevicePublicKey | null;
  certificateTTL?: CertificateTTLValue;
  csrAltNames?: string; // optional SANs input (e.g., DNS:dev-01,URI:urn:tesa:device:dev-01)
}

interface CertificateOptionsTabProps {
  formData: ExtendedCertificateFormData;
  onFormDataChange: (data: ExtendedCertificateFormData) => void;
  onCSRValidationChange?: (isValid: boolean, hasValidated: boolean, details?: CSRDetails) => void;
  validationState?: CSRValidationState;
  hasError?: boolean;
  errorMessage?: string;
  disabled?: boolean;
  showAdvancedOptions?: boolean;
  deviceId?: string;
  currentPublicKey?: DevicePublicKey | null;
}

export const CertificateOptionsTab: React.FC<CertificateOptionsTabProps> = ({
  formData,
  onFormDataChange,
  onCSRValidationChange,
  validationState,
  hasError = false,
  errorMessage,
  disabled = false,
  showAdvancedOptions = false,
  deviceId,
  currentPublicKey
}) => {
  const [csrInputMethod, setCsrInputMethod] = useState<'file' | 'paste'>('file');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [csrValidation, setCsrValidation] = useState<CSRValidationResponse | null>(null);
  const [csrDetails, setCsrDetails] = useState<CSRDetails | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [validationErrors, setValidationErrors] = useState<FieldValidationError[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<FieldValidationError[]>([]);

  // Organization certificate policy (must be defined before effects that depend on it)
  const [policy, setPolicy] = React.useState<any>(null);
  React.useEffect(() => {
    (async () => {
      try {
        const res = await authFetch('/api/v1/certificates/policies/certificates', { method: 'GET' });
        const json = await res.json();
        setPolicy(json.policy || {});
      } catch (e) {
        // Non-fatal; default to CSR-first UX
        setPolicy({});
      }
    })();
  }, []);

  const allowAutoGen = React.useMemo(
    () => !!(policy?.allow_server_side_key_gen && policy?.retain_private_key_at_rest),
    [policy]
  );
  const allowButNoRetain = React.useMemo(
    () => !!(policy?.allow_server_side_key_gen && !policy?.retain_private_key_at_rest),
    [policy]
  );
  const requireCSR = policy?.require_csr !== undefined ? !!policy.require_csr : true;

  // Initialize certificate generation method:
  // - If policy disallows auto-generate, default to UPLOAD_CSR
  // - Else keep AUTO_GENERATE as previous default for convenience
  useEffect(() => {
    if (!formData.certificateGenerationMethod) {
      onFormDataChange({
        ...formData,
        certificateGenerationMethod: !allowAutoGen
          ? CertificateGenerationMethod.UPLOAD_CSR
          : CertificateGenerationMethod.AUTO_GENERATE,
      });
    }
  }, [formData.certificateGenerationMethod, onFormDataChange, allowAutoGen]);

  // If policy toggles to disallow auto-generate while the user is on AUTO_GENERATE,
  // switch to UPLOAD_CSR to prevent confusion and present the CSR panel immediately.
  useEffect(() => {
    if (!allowAutoGen && formData.certificateGenerationMethod === CertificateGenerationMethod.AUTO_GENERATE) {
      onCSRValidationChange?.(false, false);
      onFormDataChange({
        ...formData,
        certificateGenerationMethod: CertificateGenerationMethod.UPLOAD_CSR,
      });
    }
  }, [allowAutoGen]);

  // Validate CSR when content changes
  useEffect(() => {
    if (formData.certificateGenerationMethod === CertificateGenerationMethod.UPLOAD_CSR && formData.csrContent) {
      const timer = setTimeout(() => {
        validateCSR(formData.csrContent || '');
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [formData.csrContent, formData.certificateGenerationMethod]);

  const handleCSRFileUpload = async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = event.target.files?.[0];
    if (!file) return;

    const validationResult: CSRFileValidationResult = {
      isValid: true,
      fileName: file.name,
      fileSize: file.size,
      mimeType: file.type,
      encoding: 'utf-8',
      content: '',
      errors: [],
      warnings: [],
      metadata: {
        uploadedAt: new Date(),
        source: 'file',
        hasValidHeaders: false,
        hasValidFooters: false,
        lineCount: 0,
        characterCount: 0
      }
    };

    // Check file size (max 10KB)
    if (file.size > 10240) {
      const error: FieldValidationError = {
        field: 'csrFile',
        message: 'File size exceeds 10KB limit. CSR files are typically 1-2KB.',
        severity: ValidationSeverity.ERROR,
        code: ValidationErrorCodes.CSR_FILE_TOO_LARGE
      };
      validationResult.isValid = false;
      validationResult.errors.push(error);
      setValidationErrors([error]);
      setCsrValidation({
        isValid: false,
        message: error.message,
        errors: [error.message]
      });
      return;
    }

    setUploadedFile(file);
    
    try {
      const content = await file.text();
      validationResult.content = content;
      validationResult.metadata.lineCount = content.split('\n').length;
      validationResult.metadata.characterCount = content.length;
      validationResult.metadata.hasValidHeaders = content.includes('-----BEGIN CERTIFICATE REQUEST-----');
      validationResult.metadata.hasValidFooters = content.includes('-----END CERTIFICATE REQUEST-----');
      
      onFormDataChange({ ...formData, csrContent: content });
    } catch (error) {
      const validationError: FieldValidationError = {
        field: 'csrFile',
        message: 'Failed to read file. Please ensure it\'s a valid text file.',
        severity: ValidationSeverity.ERROR,
        code: ValidationErrorCodes.CSR_INVALID_FORMAT
      };
      validationResult.isValid = false;
      validationResult.errors.push(validationError);
      setValidationErrors([validationError]);
      setCsrValidation({
        isValid: false,
        message: validationError.message,
        errors: [validationError.message]
      });
    }
  };

  const validateCSR = useCallback(async (csrContent: string): Promise<void> => {
    // Reset previous validation
    setCsrValidation(null);
    setCsrDetails(null);
    setValidationErrors([]);
    setValidationWarnings([]);

    if (!csrContent.trim()) {
      const error: FieldValidationError = {
        field: 'csrContent',
        message: 'CSR content is required',
        severity: ValidationSeverity.ERROR,
        code: ValidationErrorCodes.CSR_EMPTY_CONTENT
      };
      setValidationErrors([error]);
      return;
    }

    setIsValidating(true);

    // Basic format validation
    const csrRegex = /-----BEGIN CERTIFICATE REQUEST-----[\s\S]+-----END CERTIFICATE REQUEST-----/;
    if (!csrRegex.test(csrContent)) {
      const error: FieldValidationError = {
        field: 'csrContent',
        message: 'Invalid CSR format. Must be in PEM format with proper headers.',
        severity: ValidationSeverity.ERROR,
        code: ValidationErrorCodes.CSR_INVALID_FORMAT,
        suggestions: [
          'Ensure the CSR starts with "-----BEGIN CERTIFICATE REQUEST-----"',
          'Ensure the CSR ends with "-----END CERTIFICATE REQUEST-----"',
          'Check that the content is properly base64 encoded'
        ]
      };
      
      setCsrValidation({
        isValid: false,
        message: error.message,
        errors: [error.message]
      });
      setValidationErrors([error]);
      onCSRValidationChange?.(false, true);
      setIsValidating(false);
      return;
    }

    try {
      // Call API to validate and parse CSR
      const response = await authFetch('/api/v1/certificates/validate-csr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csr: csrContent }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const error: FieldValidationError = {
          field: 'csrContent',
          message: errorData.message || 'Invalid CSR',
          severity: ValidationSeverity.ERROR,
          code: ValidationErrorCodes.API_VALIDATION_FAILED
        };
        
        setCsrValidation({
          isValid: false,
          message: error.message,
          errors: [error.message]
        });
        setValidationErrors([error]);
        onCSRValidationChange?.(false, true);
        return;
      }

      const validationResponse: CSRValidationResponse = await response.json();
      setCsrValidation(validationResponse);
      
      if (validationResponse.details) {
        setCsrDetails(validationResponse.details);
      }
      
      // Set warnings if any
      if (validationResponse.warnings && validationResponse.warnings.length > 0) {
        const warnings: FieldValidationError[] = validationResponse.warnings.map((warning, index) => ({
          field: 'csrContent',
          message: warning,
          severity: ValidationSeverity.WARNING,
          code: `CSR_WARNING_${index + 1}`
        }));
        setValidationWarnings(warnings);
      }
      
      // Notify parent component of validation state
      onCSRValidationChange?.(validationResponse.isValid, true, validationResponse.details);
    } catch (error) {
      const validationError: FieldValidationError = {
        field: 'csrContent',
        message: 'Failed to validate CSR. Please check the format and try again.',
        severity: ValidationSeverity.ERROR,
        code: ValidationErrorCodes.API_NETWORK_ERROR
      };
      
      setCsrValidation({
        isValid: false,
        message: validationError.message,
        errors: [validationError.message]
      });
      setValidationErrors([validationError]);
      
      // Notify parent component of validation failure
      onCSRValidationChange?.(false, true);
    } finally {
      setIsValidating(false);
    }
  }, [onCSRValidationChange]);

  const clearCSR = () => {
    setUploadedFile(null);
    setCsrValidation(null);
    setCsrDetails(null);
    onFormDataChange({ ...formData, csrContent: '' });
    
    // Reset validation state in parent
    onCSRValidationChange?.(false, false);
  };

  // Copy text to clipboard helper
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      // Could add a toast notification here
    });
  };

  

  return (
    <div className="space-y-4">
      {/* Certificate Generation Info Alert */}
      <Alert className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30">
        <Shield className="h-4 w-4 text-green-600 dark:text-green-400" />
        <AlertDescription className="text-green-800 dark:text-green-200">
          <strong>Secure Certificate Generation:</strong> Choose how the certificate is issued.
          <ul className="mt-2 space-y-1 text-sm">
            <li>• <strong>Upload CSR (Recommended):</strong> Device generates and keeps the private key. Platform signs the CSR.</li>
            <li>• <strong>Auto-generate:</strong> Platform creates keys and certificate (enabled only if allowed by policy)</li>
          </ul>
        </AlertDescription>
      </Alert>

      {/* Certificate Generation Method Selection */}
      <div className="space-y-2">
        <Label>Certificate Generation Method</Label>
        <RadioGroup 
          value={formData.certificateGenerationMethod} 
          onValueChange={(value: CertificateGenerationMethod) => {
            // Clear CSR data when switching to auto-generate
            if (value === CertificateGenerationMethod.AUTO_GENERATE) {
              clearCSR();
            } else if (value === CertificateGenerationMethod.UPLOAD_CSR) {
              // Reset validation state when switching to CSR upload
              onCSRValidationChange?.(false, false);
            }
            onFormDataChange({ ...formData, certificateGenerationMethod: value });
          }}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value={CertificateGenerationMethod.AUTO_GENERATE} id="cert-auto-generate" disabled={!allowAutoGen} />
            <Label htmlFor="cert-auto-generate" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium flex items-center gap-2">
                  <Key className="h-4 w-4 text-blue-500" />
                  Auto-generate Certificate {allowAutoGen ? '' : '(Disabled by policy)'}
                </div>
                <div className="text-sm text-muted-foreground">
                  Platform generates private key and certificate automatically{!allowAutoGen ? ' — disabled by your organization policy' : ''}
                </div>
              </div>
            </Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <RadioGroupItem value={CertificateGenerationMethod.UPLOAD_CSR} id="cert-upload-csr" />
            <Label htmlFor="cert-upload-csr" className="font-normal cursor-pointer">
              <div>
                <div className="font-medium flex items-center gap-2">
                  <Upload className="h-4 w-4 text-purple-500" />
                  Upload CSR (Bring Your Own Certificate Request)
                </div>
                <div className="text-sm text-muted-foreground">
                  Upload a pre-generated CSR - you manage the private key
                </div>
              </div>
            </Label>
          </div>
        </RadioGroup>
      </div>

      {!allowAutoGen && (
        <Alert className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          {allowButNoRetain ? (
            <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
              Auto‑generate is disabled because key retention is off. Ask an organization admin to enable <em>Allow Server‑side Key Generation</em> in Settings (this implies retaining device private keys for auto‑generated certificates). CSR remains available and recommended for production.
            </AlertDescription>
          ) : (
            <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
              Your organization policy requires CSR for certificate issuance. Auto‑generate is disabled.
            </AlertDescription>
          )}
        </Alert>
      )}

      {/* CSR Upload Section */}
      {formData.certificateGenerationMethod === CertificateGenerationMethod.UPLOAD_CSR && (
        <div className="space-y-4 mt-6 p-4 border border-border rounded-lg bg-muted/20">
          <div className="space-y-2">
            <Label htmlFor="csr-upload" className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Certificate Signing Request (CSR)
            </Label>
            
            {/* File Upload and Text Paste Tabs */}
            <Tabs value={csrInputMethod} onValueChange={setCsrInputMethod}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="file">Upload File</TabsTrigger>
                <TabsTrigger value="paste">Paste Text</TabsTrigger>
              </TabsList>
              
              <TabsContent value="file" className="space-y-2">
                <div className="border-2 border-dashed border-border rounded-lg p-6 hover:border-primary/50 transition-colors">
                  <input
                    id="csr-file-upload"
                    type="file"
                    accept=".csr,.pem,.txt"
                    onChange={handleCSRFileUpload}
                    className="hidden"
                  />
                  <label
                    htmlFor="csr-file-upload"
                    className="flex flex-col items-center gap-2 cursor-pointer"
                  >
                    <Upload className="h-8 w-8 text-muted-foreground" />
                    <span className="text-sm font-medium">Click to upload CSR file</span>
                    <span className="text-xs text-muted-foreground">Supports .csr, .pem, .txt files (max 10KB)</span>
                  </label>
                </div>
                
                {uploadedFile && (
                  <div className="flex items-center gap-2 p-2 bg-background rounded-md">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm flex-1">{uploadedFile.name}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={clearCSR}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </TabsContent>
              
              <TabsContent value="paste" className="space-y-2">
                <Textarea
                  placeholder={`Paste your CSR content here...\n\n-----BEGIN CERTIFICATE REQUEST-----\nMIICvDCCAaQCAQAwdzELMAkGA1UEBhMCVVMxDTALBgNVBAgMBFV0YWgxDzANBgNV\n...\n-----END CERTIFICATE REQUEST-----`}
                  value={formData.csrContent || ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    onFormDataChange({ ...formData, csrContent: value });
                    
                    // Reset validation state when content is cleared
                    if (!value.trim()) {
                      setCsrValidation(null);
                      setCsrDetails(null);
                      onCSRValidationChange?.(false, false);
                    }
                  }}
                  className={`min-h-[200px] font-mono text-xs ${hasError ? 'border-red-500 focus:border-red-500' : ''}`}
                />
              </TabsContent>
            </Tabs>
            
            {/* External validation error from parent form */}
            {hasError && errorMessage && (
              <Alert className="border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30 mt-2">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <AlertDescription className="text-red-800 dark:text-red-200">
                  {errorMessage}
                </AlertDescription>
              </Alert>
            )}
          </div>
          
          {/* CSR Validation Status */}
          {isValidating && (
            <Alert className="border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950/30">
              <AlertDescription className="flex items-center gap-2 text-slate-800 dark:text-slate-200">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                Validating CSR...
              </AlertDescription>
            </Alert>
          )}

          {!isValidating && csrValidation && (
            <Alert className={cn(
              "transition-all",
              csrValidation.isValid
                ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30"
                : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/30"
            )}>
              {csrValidation.isValid ? (
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
              )}
              <AlertDescription className={csrValidation.isValid ? "text-green-800 dark:text-green-200" : "text-red-800 dark:text-red-200"}>
                {csrValidation.message}
              </AlertDescription>
            </Alert>
          )}
          
          {/* CSR Details Preview */}
          {csrDetails && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Fingerprint className="h-4 w-4" />
                  CSR Details
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-muted-foreground text-xs">Common Name (CN)</div>
                    <div className="font-medium font-mono">
                      {csrDetails.subject.CN || <span className="text-muted-foreground italic text-xs">(Will be replaced by device_id)</span>}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Key Algorithm</div>
                    <div className="font-medium">{csrDetails.keyAlgorithm}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Key Size</div>
                    <div className="font-medium">{csrDetails.keySize} bits</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground text-xs">Signature Algorithm</div>
                    <div className="font-medium">{csrDetails.signatureAlgorithm}</div>
                  </div>
                  {csrDetails.subject.O && (
                    <div>
                      <div className="text-muted-foreground text-xs">Organization</div>
                      <div className="font-medium">{csrDetails.subject.O}</div>
                    </div>
                  )}
                  {csrDetails.subject.OU && (
                    <div>
                      <div className="text-muted-foreground text-xs">Organizational Unit</div>
                      <div className="font-medium">{csrDetails.subject.OU}</div>
                    </div>
                  )}
                  {csrDetails.extensions?.subjectAltName && (
                    <div className="col-span-2">
                      <div className="text-muted-foreground text-xs">Subject Alternative Names</div>
                      <div className="font-medium text-xs mt-1">
                        {csrDetails.extensions.subjectAltName.join(', ')}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Optional SANs (altNames) */}
          <div className="space-y-2">
            <Label htmlFor="alt-names" className="flex items-center gap-2">
              Subject Alternative Names (Optional)
            </Label>
            <Input
              id="alt-names"
              placeholder="e.g., DNS:device-001, URI:urn:tesa:device:device-001"
              value={formData.csrAltNames || ''}
              onChange={(e) => onFormDataChange({ ...formData, csrAltNames: e.target.value })}
            />
            <div className="text-xs text-muted-foreground">
              Comma-separated values. Supported formats: <code>DNS:&lt;name&gt;</code>, <code>URI:&lt;urn&gt;</code>. Leave empty if not needed.
            </div>
          </div>
        </div>
      )}

      {/* Auto-generation Status Section */}
      {formData.certificateGenerationMethod === CertificateGenerationMethod.AUTO_GENERATE && (
        <div className="space-y-4 p-4 border border-green-200 rounded-lg bg-green-50/30">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-full">
              <Shield className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex-1">
              <Label className="text-base font-medium text-green-900">
                Automatic Certificate Generation
              </Label>
              <p className="text-sm text-green-700 mt-1">
                Security keys are automatically generated and managed by the platform. 
                No manual configuration required.
              </p>
            </div>
            <Badge className="bg-green-100 text-green-800 border-green-200">
              <Lock className="h-3 w-3 mr-1" />
              Auto-Managed
            </Badge>
          </div>

          {/* Features Display */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="bg-white/50 border-green-200">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Key className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium">Key Generation</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Cryptographic keys automatically generated based on device type
                </p>
              </CardContent>
            </Card>
            
            <Card className="bg-white/50 border-green-200">
              <CardContent className="pt-4">
                <div className="flex items-center gap-2 mb-2">
                  <Fingerprint className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium">Secure Delivery</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Private keys are protected for secure transfer to your device
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Auto-generation Options */}
      {formData.certificateGenerationMethod === CertificateGenerationMethod.AUTO_GENERATE && (
        <>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label>Certificate Algorithm</Label>
                <Info className="h-4 w-4 text-muted-foreground cursor-help" 
                  title="The platform automatically selects the optimal cryptographic algorithm based on your device type. ECC is best for low-power IoT sensors, while RSA 3072 provides the optimal balance of security and performance for gateways." />
              </div>
              <RadioGroup 
                value={formData.certificateType} 
                onValueChange={(value: CertificateType) => onFormDataChange({ ...formData, certificateType: value })}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.AUTO} id="cert-auto" />
                  <Label htmlFor="cert-auto" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">Automatic (Recommended)</div>
                      <div className="text-sm text-muted-foreground">
                        ECC P-256 for IoT devices, RSA 3072 for gateways
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.ECC_P256} id="cert-ecc-p256" />
                  <Label htmlFor="cert-ecc-p256" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">ECC P-256</div>
                      <div className="text-sm text-muted-foreground">
                        Smaller keys, faster operations, ideal for constrained devices
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.ECC_P384} id="cert-ecc-p384" />
                  <Label htmlFor="cert-ecc-p384" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">ECC P-384</div>
                      <div className="text-sm text-muted-foreground">
                        Higher security than P-256, for sensitive applications
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.RSA_2048} id="cert-rsa-2048" />
                  <Label htmlFor="cert-rsa-2048" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">RSA 2048</div>
                      <div className="text-sm text-muted-foreground">
                        Legacy standard, widely compatible, faster than larger keys
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.RSA_3072} id="cert-rsa-3072" />
                  <Label htmlFor="cert-rsa-3072" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">RSA 3072 (Recommended for Gateways)</div>
                      <div className="text-sm text-muted-foreground">
                        NIST approved, optimal balance, 2x faster than RSA 4096
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateType.RSA_4096} id="cert-rsa-4096" />
                  <Label htmlFor="cert-rsa-4096" className="font-normal cursor-pointer">
                    <div>
                      <div className="font-medium">RSA 4096</div>
                      <div className="text-sm text-muted-foreground">
                        Maximum security, slower generation, for critical infrastructure
                      </div>
                    </div>
                  </Label>
                </div>
              </RadioGroup>
            </div>

            <div className="space-y-2">
              <Label>Certificate Format</Label>
              <RadioGroup 
                value={formData.certificateFormat} 
                onValueChange={(value: CertificateFormat) => onFormDataChange({ ...formData, certificateFormat: value })}
              >
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateFormat.PEM} id="format-pem" />
                  <Label htmlFor="format-pem" className="font-normal cursor-pointer">
                    PEM (Privacy Enhanced Mail) - Text format, most common
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateFormat.DER} id="format-der" />
                  <Label htmlFor="format-der" className="font-normal cursor-pointer">
                    DER (Distinguished Encoding Rules) - Binary format
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value={CertificateFormat.PKCS12} id="format-pkcs12" />
                  <Label htmlFor="format-pkcs12" className="font-normal cursor-pointer">
                    PKCS#12 - Bundle with private key (requires password)
                  </Label>
                </div>
              </RadioGroup>
            </div>

            {/* Certificate TTL Configuration */}
            <div className="space-y-2">
              <CertificateTTL
                value={formData.certificateTTL}
                onChange={(ttlValue) => onFormDataChange({ ...formData, certificateTTL: ttlValue })}
                disabled={disabled}
                showRecommendations={true}
                organizationMaxTTL={1095} // 3 years max
              />
            </div>
          </div>

          <Alert className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
            <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <AlertDescription className="text-blue-800 dark:text-blue-200">
              <strong>Security Features:</strong>
              <ul className="mt-2 space-y-1 text-sm">
                <li>• Keys are automatically generated using optimal algorithms for your device type</li>
                <li>• All key management is handled by the platform</li>
                <li>• Secure delivery methods ensure private keys remain protected</li>
                <li>• No manual configuration required</li>
              </ul>
            </AlertDescription>
          </Alert>
        </>
      )}

      {/* CSR Upload Warning */}
      {formData.certificateGenerationMethod === CertificateGenerationMethod.UPLOAD_CSR && (
        <Alert className="border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950/30">
          <Shield className="h-4 w-4 text-slate-600 dark:text-slate-400" />
          <AlertDescription className="text-slate-800 dark:text-slate-200">
            <strong>Important:</strong> When using CSR upload, you are responsible for managing the private key.
            The platform will only provide the signed certificate, not the private key.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
