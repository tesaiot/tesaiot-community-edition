/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
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
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { SearchableSelect, SelectOption } from '@/components/ui/searchable-select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { Textarea } from '@/components/ui/textarea';
import {
  Loader2,
  Shield,
  Key,
  Download,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  FileText,
  Package,
  QrCode,
  Lock,
  Info,
  Cpu,
  Gauge,
  Network,
  Router,
  Wifi,
  Radio,
  Satellite,
  Binary,
  Fingerprint,
  ShieldCheck,
  Sparkles,
  Copy
} from 'lucide-react';
import { Device } from '../types/device.types';
import authFetch from '@/utils/auth-fetch';
import { IndustrySpecificTab } from './IndustrySpecificTab';
import { DevicePictureUpload } from './DevicePictureUpload';
import { DeviceSchemaEditor } from './DeviceSchemaEditor';
import { CertificateOptionsTab } from './CertificateOptionsTab';
import { CertificateTTLValue } from '@/components/CertificateTTL';
import { useAuth } from '@/hooks/useAuth';
import { tesaApi } from '@/services/api/tesaApi';
import { deviceService } from '../services/deviceService';

interface DeviceCreationStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error';
}

interface CertificateDetails {
  algorithm: string;
  keySize: string;
  validity: string;
  serialNumber: string;
  fingerprint: string;
  issuer: string;
  subject: string;
  expiresAt: string;
}

interface CertificateBundle {
  certificate: string;
  privateKey: string;
  publicKey: string;
  caChain: string;
}

interface FormValidationErrors {
  name?: string;
  type?: string;
  csrContent?: string;
  certificateGenerationMethod?: string;
  general?: string;
  factoryUid?: string;
}

interface DeviceFormData {
  name: string;
  type: 'sensor' | 'actuator' | 'gateway' | 'controller';
  serialNumber: string;
  location: string;
  manufacturer: string;
  model: string;
  protocol: 'MQTTS' | 'HTTPS';
  firmware: string;
  tags: string[];
  generateCertificate: boolean;
  certificateGenerationMethod: 'auto-generate' | 'upload-csr';
  certificateType: 'auto' | 'ecc-p256' | 'ecc-p384' | 'rsa-2048' | 'rsa-3072' | 'rsa-4096';
  certificateFormat: 'pem' | 'der' | 'pkcs12';
  csrContent: string;
  csrValid: boolean;
  csrValidated: boolean;
  devicePicture: string | null;
  industry: string;
  industrySpecificData: Record<string, any>;
  authMode: 'mtls' | 'server_tls';
  trustmUid?: string;  // Trust M UID (54 hex chars) for Method 2
  factoryUid?: string;
  factoryCertificate?: string;
  telemetrySchema: {
    schema: Record<string, any>;
    uiSchema: Record<string, any>;
    formData: Record<string, any>;
  };
  actuatorSchema: {
    schema: Record<string, any>;
    uiSchema: Record<string, any>;
    formData: Record<string, any>;
  };
  certificateTTL?: CertificateTTLValue;
}

interface DeviceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  device?: Device | null;
  onSave?: (device: Partial<Device>) => Promise<void> | void;
  onSuccess?: () => void;
  mode?: 'create' | 'edit';  // Support both create and edit modes
  enhancedMode?: boolean;    // Use enhanced 4-tab flow
}

export const DeviceDialog: React.FC<DeviceDialogProps> = ({
  open,
  onOpenChange,
  device,
  onSave,
  onSuccess,
  mode = 'create',
  enhancedMode = true,  // Default to enhanced mode
}) => {
  const { user: currentUser } = useAuth();
  const isHighRole = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');
  // Tab management
  const [currentTab, setCurrentTab] = useState('device');
  const [isCreating, setIsCreating] = useState(false);
  const [creationStep, setCreationStep] = useState<string>('');
  const [certificateDetails, setCertificateDetails] = useState<CertificateDetails | null>(null);
  const [certificateBundle, setCertificateBundle] = useState<CertificateBundle | null>(null);
  const [certificateDownloadUrls, setCertificateDownloadUrls] = useState<{
    device_cert?: string;
    device_key?: string;
    ca_chain?: string;
  } | null>(null);
  const [deviceId, setDeviceId] = useState<string>('');
  const [mqttPassword, setMqttPassword] = useState<string>('');
  const [httpsApiKey, setHttpsApiKey] = useState<string>('');
  // Final-step bundle toggles: default ON for create, OFF for edit
  const [bundleIncludePassword, setBundleIncludePassword] = useState<boolean>(mode === 'create');
  const [bundleIncludeApiKey, setBundleIncludeApiKey] = useState<boolean>(mode === 'create');
  const [isDownloadingTrustMBundle, setIsDownloadingTrustMBundle] = useState(false);
  // Org policy gates (default allow; will be restricted if policy denies)
  const [policyAllowBundlePass, setPolicyAllowBundlePass] = useState<boolean>(true);
  const [policyAllowBundleApi, setPolicyAllowBundleApi] = useState<boolean>(true);
  const [policySourcePass, setPolicySourcePass] = useState<'default' | 'env' | 'org'>('default');
  const [policySourceApi, setPolicySourceApi] = useState<'default' | 'env' | 'org'>('default');
  
  // Edit mode state tracking
  const [updateSuccessful, setUpdateSuccessful] = useState(false);
  const [initialFormData, setInitialFormData] = useState<DeviceFormData | null>(null);
  const [hasFormChanged, setHasFormChanged] = useState(false);
  
  // Form validation state
  const [formErrors, setFormErrors] = useState<FormValidationErrors>({});
  const [isFormValid, setIsFormValid] = useState(false);
  const [hasAttemptedSubmit, setHasAttemptedSubmit] = useState(false);

  // Unsaved schema changes warning state
  const [hasUnsavedSchemaChanges, setHasUnsavedSchemaChanges] = useState(false);
  const [showUnsavedWarningDialog, setShowUnsavedWarningDialog] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);

  // Form data with enhanced fields and proper initialization
  const [formData, setFormData] = useState<DeviceFormData>({
    name: '',
    type: 'sensor' as const,
    serialNumber: '',
    location: '',
    manufacturer: '',
    model: '',
    // Protocol selection removed; devices may use MQTTs or HTTPS interchangeably
    firmware: '',
    tags: [] as string[],
    // Certificate options - only generate for mTLS by default
    generateCertificate: false,
    certificateGenerationMethod: 'auto-generate' as 'auto-generate' | 'upload-csr',
    certificateType: 'auto' as 'auto' | 'ecc-p256' | 'ecc-p384' | 'rsa-2048' | 'rsa-3072' | 'rsa-4096',
    certificateFormat: 'pem' as 'pem' | 'der' | 'pkcs12',
    csrContent: '',
    // CSR validation state (managed in parent for form validation)
    csrValid: false,
    csrValidated: false,
    // Device picture
    devicePicture: null as string | null,
    // Authentication mode - default to server_tls for PSoC compatibility
    authMode: 'server_tls' as 'mtls' | 'server_tls',
    trustmUid: '',  // Trust M UID (54 hex chars) for Method 2
    factoryUid: '',
    factoryCertificate: '',
    // Industry specific
    industry: '',
    industrySpecificData: {} as Record<string, any>,
    // Device schema for telemetry and actuator commands
    telemetrySchema: {
      schema: {} as Record<string, any>,
      uiSchema: {} as Record<string, any>,
      formData: {} as Record<string, any>
    },
    actuatorSchema: {
      schema: {} as Record<string, any>,
      uiSchema: {} as Record<string, any>,
      formData: {} as Record<string, any>
    }
  });

  // Creation steps for progress tracking - will be updated based on certificate method
  const getStepsForCertificateMethod = (method: string, authMode: DeviceFormData['authMode']): DeviceCreationStep[] => {
    if (authMode === 'optiga_trust_mtls') {
      return [
        { id: 'device', label: 'Creating device entry', status: 'pending' },
        { id: 'bundle', label: 'Preparing Trust M starter bundle', status: 'pending' }
      ];
    }
    if (method === 'upload-csr') {
      return [
        { id: 'device', label: 'Creating device entry', status: 'pending' },
        { id: 'keypair', label: 'Preparing CSR for signing', status: 'pending' },
        { id: 'signing', label: 'Signing CSR with platform CA', status: 'pending' },
        { id: 'bundle', label: 'Preparing certificate bundle', status: 'pending' }
      ];
    } else {
      return [
        { id: 'device', label: 'Creating device entry', status: 'pending' },
        { id: 'keypair', label: 'Generating cryptographic keys', status: 'pending' },
        { id: 'signing', label: 'Signing certificate with CA', status: 'pending' },
        { id: 'bundle', label: 'Preparing download bundle', status: 'pending' }
      ];
    }
  };

  const steps: DeviceCreationStep[] = getStepsForCertificateMethod(formData.certificateGenerationMethod || 'auto-generate', formData.authMode);
  const isTrustMMode = false;
  // Check if Trust M UID is provided (makes CSR optional instead of required)
  const hasTrustMUid = formData.trustmUid && formData.trustmUid.trim().length === 54 && /^[0-9A-Fa-f]{54}$/.test(formData.trustmUid.trim());
  // Always show Certificate Options tab for mTLS (CSR optional if Trust M UID provided)
  const showCertificateTab = formData.authMode === 'mtls' || isTrustMMode;

  const [creationSteps, setCreationSteps] = useState<DeviceCreationStep[]>(steps);

  // Update creation steps when certificate generation method changes
  useEffect(() => {
    const newSteps = getStepsForCertificateMethod(formData.certificateGenerationMethod || 'auto-generate', formData.authMode);
    setCreationSteps(newSteps);
  }, [formData.certificateGenerationMethod, formData.authMode]);

  // Form validation logic
  const validateForm = () => {
    const errors: FormValidationErrors = {};
    
    // Basic required field validation
    if (!formData.name?.trim()) {
      errors.name = 'Device name is required';
    } else if (formData.name.length < 3) {
      errors.name = 'Device name must be at least 3 characters';
    }
    
    if (!formData.type) {
      errors.type = 'Device type is required';
    }
    
    // CSR-specific validation (only for mTLS mode WITHOUT Trust M UID)
    // If Trust M UID is provided, skip CSR validation (Method 2: Trust M UID Authentication)
    const hasTrustMUid = formData.trustmUid && formData.trustmUid.trim().length === 54 && /^[0-9A-Fa-f]{54}$/.test(formData.trustmUid.trim());

    if (formData.generateCertificate && formData.authMode === 'mtls' && !hasTrustMUid && formData.certificateGenerationMethod === 'upload-csr') {
      if (!formData.csrContent?.trim()) {
        errors.csrContent = 'CSR content is required when using upload method';
      } else if (!formData.csrValid && formData.csrValidated) {
        errors.csrContent = 'Please provide a valid CSR';
      }
    }

    if (false) {
      if (!formData.factoryUid?.trim()) {
        errors.factoryUid = 'Factory UID is required for OPTIGA™ Trust M devices';
      } else {
        const uid = formData.factoryUid.trim();
        if (!/^[a-zA-Z0-9_-]{3,64}$/.test(uid)) {
          errors.factoryUid = 'Factory UID must be 3-64 characters (letters, numbers, hyphen, underscore)';
        }
      }
    }
    
    setFormErrors(errors);
    const isValid = Object.keys(errors).length === 0;
    setIsFormValid(isValid);
    return isValid;
  };

  // Validate form whenever form data changes
  useEffect(() => {
    if (hasAttemptedSubmit || Object.keys(formErrors).length > 0) {
      validateForm();
    }
  }, [formData, hasAttemptedSubmit]);

  useEffect(() => {
    if (device) {
      // Helper function to map database protocol values to UI values
      const mapProtocolForUI = (protocol: string | undefined): 'MQTTS' | 'HTTPS' => {
        if (!protocol) return 'MQTTS';
        const lowerProtocol = protocol.toLowerCase();
        if (lowerProtocol === 'mqtts' || lowerProtocol === 'mqtt') return 'MQTTS';
        if (lowerProtocol === 'https' || lowerProtocol === 'http') return 'HTTPS';
        return 'MQTTS'; // Default fallback
      };
      
      const deviceData = {
        name: device.name,
        type: device.type || 'sensor',
        serialNumber: device.serialNumber || '',
        location: typeof device.location === 'string' ? device.location : (device.location?.name || ''),
        manufacturer: device.metadata?.manufacturer || device.manufacturer || '',
        model: device.metadata?.model || device.model || '',
        protocol: mapProtocolForUI(device.metadata?.protocol || device.protocol),
        firmware: device.firmwareVersion || device.firmware || '',
        tags: device.tags || [],
        generateCertificate: true,
        certificateGenerationMethod: 'auto-generate',
        certificateType: 'auto',
        certificateFormat: 'pem',
        csrContent: '',
        csrValid: false,
        csrValidated: false,
        devicePicture: device.metadata?.devicePicture || null,
        authMode: device.auth_mode || 'server_tls',
        trustmUid: device.trustm_uid || '',  // Load Trust M UID from device
        factoryUid: device.metadata?.factory_uid || '',
        factoryCertificate: (device as any)?.factory_certificate?.pem || (device.metadata?.factory_certificate_pem || ''),
        industry: device.metadata?.industry || '',
        industrySpecificData: device.metadata?.industrySpecificData || {},
        telemetrySchema: device.telemetrySchema || {
          schema: {},
          uiSchema: {},
          formData: {}
        },
        actuatorSchema: device.actuatorSchema || {
          schema: {},
          uiSchema: {},
          formData: {}
        }
      };

      setFormData(deviceData);
      setInitialFormData(JSON.parse(JSON.stringify(deviceData)));
      setUpdateSuccessful(false);
      setHasFormChanged(false);
      // Reset validation state when loading device
      setFormErrors({});
      setHasAttemptedSubmit(false);
    } else {
      // Reset to defaults
      setFormData({
        name: '',
        type: 'sensor',
        serialNumber: '',
        location: '',
        manufacturer: '',
        model: '',
        protocol: 'MQTTS',
        firmware: '',
        tags: [],
        generateCertificate: true,
        certificateGenerationMethod: 'auto-generate',
        certificateType: 'auto',
        certificateFormat: 'pem',
        csrContent: '',
        csrValid: false,
        csrValidated: false,
        devicePicture: null,
        authMode: 'server_tls',
        industry: '',
        industrySpecificData: {},
        telemetrySchema: {
          schema: {},
          uiSchema: {},
          formData: {}
        },
        actuatorSchema: {
          schema: {},
          uiSchema: {},
          formData: {}
        }
      });
      setInitialFormData(null);
      setUpdateSuccessful(false);
      setHasFormChanged(false);
      // Reset validation state for new device
      setFormErrors({});
      setHasAttemptedSubmit(false);
    }
  }, [device]);

  // Detect form changes
  useEffect(() => {
    if (initialFormData && mode === 'edit') {
      // Compare current form data with initial data
      const changed = JSON.stringify(formData) !== JSON.stringify(initialFormData);
      setHasFormChanged(changed);
    }
  }, [formData, initialFormData, mode]);


  // Helper functions
  const getCertificateAlgorithm = () => {
    if (formData.certificateType === 'auto') {
      return ['sensor', 'actuator'].includes(formData.type) ? 'ecc-p256' : 'rsa-3072';
    }
    return formData.certificateType;
  };

  const updateStepStatus = (stepId: string, status: 'active' | 'completed' | 'error') => {
    setCreationSteps(prev => prev.map(step => 
      step.id === stepId ? { ...step, status } : step
    ));
  };

  const downloadFile = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAllCertificates = () => {
    if (!certificateBundle || !deviceId) return;
    
    downloadFile(certificateBundle.certificate, `${deviceId}.crt`);
    
    // Only download private key if available (auto-generated certificates)
    if (certificateBundle.privateKey) {
      downloadFile(certificateBundle.privateKey, `${deviceId}.key`);
    }
    
    // Download public key if available
    if (certificateBundle.publicKey) {
      downloadFile(certificateBundle.publicKey, `${deviceId}.pub`);
    }
    
    downloadFile(certificateBundle.caChain, `${deviceId}-ca-chain.crt`);
    
    const fileCount = 2 + (certificateBundle.privateKey ? 1 : 0) + (certificateBundle.publicKey ? 1 : 0);
    toast.success(`All ${fileCount} certificate files downloaded!`);
  };

  const downloadServerTlsBundle = async (flavor: 'mqtt' | 'https') => {
    if (!deviceId) {
      toast.error('Device ID missing — cannot download bundle');
      return;
    }
    try {
      await tesaApi.downloadServerTlsBundle(deviceId, {
        include_password: isHighRole && policyAllowBundlePass ? bundleIncludePassword : false,
        include_api_key: isHighRole && policyAllowBundleApi ? bundleIncludeApiKey : false,
        flavor
      });
      toast.success('Server‑TLS bundle download started');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to download Server‑TLS bundle');
    }
  };

  const downloadMqttQuicServerTlsBundle = async () => {
    if (!deviceId) {
      toast.error('Device ID missing — cannot download MQTT-QUIC bundle');
      return;
    }
    try {
      await tesaApi.downloadMqttQuicServerTlsBundle(deviceId, {
        include_password: isHighRole && policyAllowBundlePass ? bundleIncludePassword : false,
        include_api_key: isHighRole && policyAllowBundleApi ? bundleIncludeApiKey : false,
      });
      toast.success('MQTT-QUIC Server‑TLS bundle download started');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to download MQTT-QUIC Server‑TLS bundle');
    }
  };

  const downloadTrustMBundle = async () => {
    if (!deviceId) {
      toast.error('Device ID missing — cannot download Trust M starter bundle');
      return;
    }
    setIsDownloadingTrustMBundle(true);
    try {
      const response = await deviceService.downloadCertificateResponse(deviceId, 'trustm-starter-bundle');
      if (!response.ok) {
        const details = await response.text().catch(() => '');
        throw new Error(details || 'Failed to download Trust M starter bundle');
      }
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      let filename = '';
      if (match) {
        filename = decodeURIComponent((match[1] || match[2] || '').trim());
      }
      if (!filename) {
        const ts = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        filename = `${deviceId}-trustm-starter-bundle-${ts}.zip`;
      }
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success('OPTIGA™ Trust M starter bundle download started');
    } catch (error: any) {
      console.error('Trust M starter bundle download failed:', error);
      toast.error(error?.message || 'Failed to download Trust M starter bundle');
    } finally {
      setIsDownloadingTrustMBundle(false);
    }
  };

  // Load org policy for bundle inclusion gates
  useEffect(() => {
    const loadPolicy = async () => {
      try {
        const res = await authFetch('/api/v1/certificates/policies/certificates');
        if (res.ok) {
          const data = await res.json();
          const pol = data?.policy || {};
          if (typeof pol.allow_bundle_include_password === 'boolean') setPolicyAllowBundlePass(pol.allow_bundle_include_password);
          if (typeof pol.allow_bundle_include_api_key === 'boolean') setPolicyAllowBundleApi(pol.allow_bundle_include_api_key);
          const src = data?.sources || {};
          if (typeof src.allow_bundle_include_password === 'string') setPolicySourcePass(src.allow_bundle_include_password);
          if (typeof src.allow_bundle_include_api_key === 'string') setPolicySourceApi(src.allow_bundle_include_api_key);
        }
      } catch {}
    };
    loadPolicy();
    const onUpdate = (e: any) => {
      try {
        const pol = e?.detail || {};
        if (typeof pol.allow_bundle_include_password === 'boolean') setPolicyAllowBundlePass(pol.allow_bundle_include_password);
        if (typeof pol.allow_bundle_include_api_key === 'boolean') setPolicyAllowBundleApi(pol.allow_bundle_include_api_key);
        // Event originates from org save → mark sources as org for these fields
        if (typeof pol.allow_bundle_include_password === 'boolean') setPolicySourcePass('org');
        if (typeof pol.allow_bundle_include_api_key === 'boolean') setPolicySourceApi('org');
      } catch {}
    };
    window.addEventListener('org-policy-updated' as any, onUpdate);
    return () => window.removeEventListener('org-policy-updated' as any, onUpdate);
  }, []);

  // Handle navigation from schema tab with unsaved changes check
  const handleSchemaNavigation = (targetTab: string) => {
    if (currentTab === 'schema' && hasUnsavedSchemaChanges) {
      setPendingNavigation(targetTab);
      setShowUnsavedWarningDialog(true);
    } else {
      setCurrentTab(targetTab);
    }
  };

  // Handle confirmation of navigation despite unsaved changes
  const handleConfirmNavigation = () => {
    if (pendingNavigation) {
      setHasUnsavedSchemaChanges(false); // Reset after navigation
      if (pendingNavigation === 'create') {
        // Special case: user wants to create device with unsaved schema changes
        handleCreateDevice();
      } else {
        setCurrentTab(pendingNavigation);
      }
    }
    setShowUnsavedWarningDialog(false);
    setPendingNavigation(null);
  };

  // Handle cancellation of navigation (stay on schema tab)
  const handleCancelNavigation = () => {
    setShowUnsavedWarningDialog(false);
    setPendingNavigation(null);
  };

  const handleCreateDevice = async () => {
    // Set submit attempt flag and validate form
    setHasAttemptedSubmit(true);
    
    if (!validateForm()) {
      toast.error('Please fix the validation errors before proceeding');
      // Navigate to appropriate tab with errors
      if (formErrors.name || formErrors.type) {
        setCurrentTab('device');
      } else if (formErrors.csrContent) {
        setCurrentTab('certificate');
      }
      return;
    }
    
    setIsCreating(true);
    setCurrentTab('progress');
    
    try {
      // Pre-validation: Validate CSR if upload method is selected and mTLS is enabled
      // EXCEPTION: If Trust M UID provided, CSR is optional (will use factory cert workflow)
      if (formData.generateCertificate && formData.authMode === 'mtls' && formData.certificateGenerationMethod === 'upload-csr') {
        if (!formData.trustmUid?.trim() && !formData.csrContent?.trim()) {
          throw new Error('CSR content is required when using upload method');
        }

        // Only validate CSR if CSR content is provided (skip if using Trust M UID)
        if (formData.csrContent?.trim()) {
          setCreationStep('Validating CSR...');

          const csrValidationResponse = await authFetch('/api/v1/certificates/validate-csr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ csr: formData.csrContent })
          });

          if (!csrValidationResponse.ok) {
            const error = await csrValidationResponse.json();
            throw new Error(`CSR validation failed: ${error.message || 'Invalid CSR'}`);
          }
        }
      }

      // Step 1: Create device
      updateStepStatus('device', 'active');
      setCreationStep('Creating device entry...');
      
      const trimmedFactoryUid = formData.factoryUid?.trim() || undefined;
      const trimmedFactoryCert = formData.factoryCertificate?.trim() || undefined;

      const devicePayload = {
        // device_id is auto-generated by backend unless Trust M UID provided
        name: formData.name,
        type: formData.type,
        location: formData.location ? { name: formData.location } : {},
        metadata: {
          manufacturer: formData.manufacturer,
          model: formData.model,
          // Declare support for both secure protocols
          protocols: ['mqtts', 'https'],
          serialNumber: formData.serialNumber,
          certificateType: formData.certificateType,
          certificate_algorithm: getCertificateAlgorithm(),
          factory_uid: false ? trimmedFactoryUid : undefined,
          // Include industry type
          industry: formData.industry,
          // Include device picture if provided
          devicePicture: formData.devicePicture,
          // Include industry-specific data as a separate object
          industrySpecificData: formData.industrySpecificData && Object.keys(formData.industrySpecificData).length > 0 ? formData.industrySpecificData : null
        },
        // Include device schemas for telemetry and actuator commands
        telemetrySchema: formData.telemetrySchema && Object.keys(formData.telemetrySchema.schema || {}).length > 0 ? {
          schema: formData.telemetrySchema.schema,
          uiSchema: formData.telemetrySchema.uiSchema,
          formData: formData.telemetrySchema.formData,
          lastUpdated: new Date().toISOString()
        } : null,
        actuatorSchema: formData.actuatorSchema && Object.keys(formData.actuatorSchema.schema || {}).length > 0 ? {
          schema: formData.actuatorSchema.schema,
          uiSchema: formData.actuatorSchema.uiSchema,
          formData: formData.actuatorSchema.formData,
          lastUpdated: new Date().toISOString()
        } : null,
        tags: formData.tags,
        certificate_options: formData.generateCertificate && formData.authMode === 'mtls' ? {
          algorithm: getCertificateAlgorithm(),
          format: formData.certificateFormat,
          generation_method: formData.certificateGenerationMethod,
          csr_content: formData.certificateGenerationMethod === 'upload-csr' ? formData.csrContent : null
        } : null,
        certificate_status: formData.generateCertificate && formData.authMode === 'mtls' ? 'valid' : 'none',
        // Add auth_mode field from form data
        auth_mode: formData.authMode,
        // Add Trust M UID if provided (Method 2)
        trustm_uid: formData.trustmUid && formData.trustmUid.trim() ? formData.trustmUid.trim() : undefined,
        factory_uid: false ? trimmedFactoryUid : undefined,
        factory_certificate_pem: false ? trimmedFactoryCert : undefined
      };

      const response = await authFetch('/api/v1/devices/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(devicePayload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.error || errorData.message || `Failed to create device (${response.status})`;
        console.error('Device creation failed:', errorMessage, errorData);
        throw new Error(errorMessage);
      }

      const createdDevice = await response.json();
      setDeviceId(createdDevice.device_id);
      
      // Capture MQTT password for server_tls devices
      if (formData.authMode === 'server_tls' && createdDevice.mqtt_password) {
        setMqttPassword(createdDevice.mqtt_password);
        console.info('MQTT password received for server_tls device');
      }
      
      // Capture HTTPs API key for server_tls devices with HTTPs protocol
      if (formData.authMode === 'server_tls' && createdDevice.https_api_key) {
        setHttpsApiKey(createdDevice.https_api_key);
        console.info('HTTPs API key received for server_tls device');
      }
      
      updateStepStatus('device', 'completed');

      // Only generate certificates for mTLS authentication mode
      if (formData.authMode === 'mtls' && formData.generateCertificate) {
        // Different workflow for CSR vs auto-generate
        if (formData.certificateGenerationMethod === 'upload-csr') {
          // Check if Trust M UID is provided - if so, skip CSR signing (will use factory cert)
          if (formData.trustmUid?.trim()) {
            // Trust M Factory Certificate Workflow - no CSR signing needed
            updateStepStatus('keypair', 'completed');
            updateStepStatus('signing', 'completed');
            updateStepStatus('bundle', 'completed');
            setCreationStep('Device created successfully - will auto-activate with factory certificate');
            console.info('Trust M device created - will use factory cert workflow');

            // Skip certificate workflow - device will auto-activate on first connection
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Skip bundle preparation and certificate details for Trust M workflow
            // Device will use factory cert and get platform cert later via MQTT
          } else {
            // CSR Signing Workflow (normal flow without Trust M UID)
            // Step 2: Prepare for CSR signing
            updateStepStatus('keypair', 'active');
            setCreationStep('Preparing CSR for signing...');
            await new Promise(resolve => setTimeout(resolve, 500));
            updateStepStatus('keypair', 'completed');

            // Step 3: Sign CSR with platform CA
            updateStepStatus('signing', 'active');
            setCreationStep('Signing CSR with platform CA...');

            const payload: any = {
              csr: formData.csrContent,
              validity_days: 365,
            };
            if (formData.csrAltNames && typeof formData.csrAltNames === 'string') {
              const arr = formData.csrAltNames.split(',').map(s => s.trim()).filter(Boolean);
              if (arr.length) payload.altNames = arr;
            }
            const csrSignResponse = await authFetch(`/api/v1/certificates/devices/${createdDevice.device_id}/certificate/sign-csr`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });

            if (!csrSignResponse.ok) {
              const error = await csrSignResponse.json();
              throw new Error(`Failed to sign CSR: ${error.message || 'Signing failed'}`);
            }

            const certData = await csrSignResponse.json();
            updateStepStatus('signing', 'completed');

            // Step 4: Prepare certificate bundle for download
            updateStepStatus('bundle', 'active');
            setCreationStep('Preparing certificate bundle...');

            // Note: For CSR workflow, we only get the signed certificate, not the private key
            setCertificateBundle({
              certificate: certData.certificate || '',
              privateKey: '', // Private key is managed by user in CSR workflow
              publicKey: certData.public_key || '',
              caChain: certData.ca_chain || ''
            });

            // Extract certificate details for CSR-signed certificate
            // Prefer algorithm reported by API/certificate over the UI-selected default
            const algoFromCert = (certData?.certificate?.algorithm || certData?.certificate?.key_algorithm || '').toLowerCase();
            const algo = algoFromCert || getCertificateAlgorithm();
            let displayAlgorithm = '';
            let keySize = '';

            switch(algo) {
              case 'ecc p-256':
              case 'ecc-p256':
              case 'ecdsa-p256':
                displayAlgorithm = 'ECC P-256';
                keySize = '256 bits';
                break;
              case 'ecc p-384':
              case 'ecc-p384':
              case 'ecdsa-p384':
                displayAlgorithm = 'ECC P-384';
                keySize = '384 bits';
                break;
              case 'rsa 2048':
              case 'rsa-2048':
                displayAlgorithm = 'RSA 2048';
                keySize = '2048 bits';
                break;
              case 'rsa 3072':
              case 'rsa-3072':
                displayAlgorithm = 'RSA 3072';
                keySize = '3072 bits';
                break;
              case 'rsa 4096':
              case 'rsa-4096':
                displayAlgorithm = 'RSA 4096';
                keySize = '4096 bits';
                break;
              default:
                displayAlgorithm = (algoFromCert || getCertificateAlgorithm()).toUpperCase().replace('-', ' ');
                keySize = 'Variable';
            }

            setCertificateDetails({
              algorithm: displayAlgorithm,
              keySize: keySize,
              validity: '1 year',
              serialNumber: certData.certificate?.serial_number || certData.serial_number || 'Generated',
              fingerprint: certData.fingerprint || 'SHA256:...',
              issuer: certData.certificate?.issuer || 'CN=TESAIoT Intermediate CA',
              subject: certData.certificate?.subject || `CN=${createdDevice.device_id}.device.tesa.iot`,
              expiresAt: certData.certificate?.expires_at || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
            });

            updateStepStatus('bundle', 'completed');
          }
        } else {
          // Auto-generate Workflow (existing logic)
          // Step 2: Generate keypair
          updateStepStatus('keypair', 'active');
          setCreationStep('Generating cryptographic keys...');
          await new Promise(resolve => setTimeout(resolve, 1000));
          updateStepStatus('keypair', 'completed');

          // Step 3: Sign certificate
          updateStepStatus('signing', 'active');
          setCreationStep('Signing certificate with CA...');
          
          // Add a small delay to ensure the device is fully committed to the database
          await new Promise(resolve => setTimeout(resolve, 1500));
          
          const certResponse = await authFetch(`/api/v1/certificates/devices/${createdDevice.device_id}/certificate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              algorithm: getCertificateAlgorithm(),
              generation_method: formData.certificateGenerationMethod,
              csr_content: null
            })
          });

          if (!certResponse.ok) {
            const errorData = await certResponse.json().catch(() => ({ message: 'Unknown error' }));
            throw new Error(`Failed to generate certificate (${certResponse.status}): ${errorData.message || errorData.error || errorData.detail || 'Certificate generation failed'}`);
          }

          const certData = await certResponse.json();
          updateStepStatus('signing', 'completed');

          // Step 4: Prepare bundle for auto-generated certificate
          updateStepStatus('bundle', 'active');
          setCreationStep('Preparing download bundle...');
          
          const algo = getCertificateAlgorithm();
          let displayAlgorithm = '';
          let keySize = '';
          
          switch(algo) {
            case 'ecc-p256':
              displayAlgorithm = 'ECC P-256';
              keySize = '256 bits';
              break;
            case 'ecc-p384':
              displayAlgorithm = 'ECC P-384';
              keySize = '384 bits';
              break;
            case 'rsa-2048':
              displayAlgorithm = 'RSA 2048';
              keySize = '2048 bits';
              break;
            case 'rsa-3072':
              displayAlgorithm = 'RSA 3072';
              keySize = '3072 bits';
              break;
            case 'rsa-4096':
              displayAlgorithm = 'RSA 4096';
              keySize = '4096 bits';
              break;
            default:
              displayAlgorithm = algo.toUpperCase().replace('-', ' ');
              keySize = 'Unknown';
          }
          
          setCertificateDetails({
            algorithm: displayAlgorithm,
            keySize: keySize,
            validity: '1 year',
            serialNumber: certData.certificate?.serial_number || certData.serial_number || 'Generated',
            fingerprint: certData.fingerprint || 'SHA256:...',
            issuer: certData.certificate?.issuer || 'CN=TESAIoT Intermediate CA',
            subject: certData.certificate?.subject || `CN=${createdDevice.device_id}.device.tesa.iot`,
            expiresAt: certData.certificate?.expires_at || new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString()
          });

          // Store download URLs for later use, but don't fetch automatically
          // This prevents unwanted download attempts and 401 errors
          if (certData.download_urls) {
            // Store the download URLs for when user explicitly requests downloads
            setCertificateDownloadUrls({
              device_cert: certData.download_urls.device_cert,
              device_key: certData.download_urls.device_key,
              ca_chain: certData.download_urls.ca_chain
            });
          }
          
          // Only use certificate data if directly provided by API
          if (certData.certificate || certData.private_key || certData.ca_chain) {
            setCertificateBundle({
              certificate: certData.certificate || '',
              privateKey: certData.private_key || '',
              publicKey: certData.public_key || '',
              caChain: certData.ca_chain || ''
            });
          }
        }

        updateStepStatus('bundle', 'completed');
        setCurrentTab('complete');
      } else if (false) {
        updateStepStatus('bundle', 'active');
        setCreationStep('Preparing Trust M starter bundle...');
        await new Promise(resolve => setTimeout(resolve, 600));
        updateStepStatus('bundle', 'completed');
        setCurrentTab('complete');
      } else {
        setCurrentTab('complete');
      }
      
      toast.success(`Device "${formData.name}" created successfully!`);
      onSuccess?.();
      
    } catch (error) {
      console.error('Device creation failed:', error);
      toast.error('Failed to create device. Please try again.');
      const failedStep = creationSteps.find(s => s.status === 'active');
      if (failedStep) {
        updateStepStatus(failedStep.id, 'error');
      }
    } finally {
      setIsCreating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (enhancedMode && mode === 'create') {
      handleCreateDevice();
    } else if (mode === 'edit') {
      // Validate form for edit mode as well
      setHasAttemptedSubmit(true);
      if (!validateForm()) {
        toast.error('Please fix the validation errors before saving');
        return;
      }
      // For edit mode, format the update payload properly
      setIsCreating(true);
      
      const trimmedFactoryUid = formData.factoryUid?.trim() || undefined;
      const trimmedFactoryCert = formData.factoryCertificate?.trim() || undefined;

      const updatePayload = {
        name: formData.name,
        type: formData.type,
        auth_mode: formData.authMode,  // Include auth_mode for switching authentication modes
        trustm_uid: formData.trustmUid && formData.trustmUid.trim() ? formData.trustmUid.trim() : undefined,  // Trust M UID (Method 2)
        location: formData.location ? { name: formData.location } : {},
        metadata: {
          manufacturer: formData.manufacturer,
          model: formData.model,
          protocols: ['mqtts', 'https'],
          serialNumber: formData.serialNumber,
          industry: formData.industry,
          devicePicture: formData.devicePicture,
          // Include industry-specific data as a separate object
          industrySpecificData: formData.industrySpecificData && Object.keys(formData.industrySpecificData).length > 0 ? formData.industrySpecificData : null,
          factory_uid: false ? trimmedFactoryUid : undefined
        },
        // Include device schemas for telemetry and actuator commands
        telemetrySchema: formData.telemetrySchema && Object.keys(formData.telemetrySchema.schema || {}).length > 0 ? {
          schema: formData.telemetrySchema.schema,
          uiSchema: formData.telemetrySchema.uiSchema,
          formData: formData.telemetrySchema.formData,
          lastUpdated: new Date().toISOString()
        } : null,
        actuatorSchema: formData.actuatorSchema && Object.keys(formData.actuatorSchema.schema || {}).length > 0 ? {
          schema: formData.actuatorSchema.schema,
          uiSchema: formData.actuatorSchema.uiSchema,
          formData: formData.actuatorSchema.formData,
          lastUpdated: new Date().toISOString()
        } : null,
        tags: formData.tags,
        factory_uid: false ? trimmedFactoryUid : undefined,
        factory_certificate_pem: false ? trimmedFactoryCert : undefined
      };
      
      
      try {
        await onSave?.(updatePayload);

        // If onSave succeeds, mark as successful
        setUpdateSuccessful(true);
        setInitialFormData(JSON.parse(JSON.stringify(formData))); // Update initial data to current
        setHasFormChanged(false);
        setIsCreating(false);
      } catch (error) {
        console.error('Error updating device:', error);
        setIsCreating(false);
        // Error handling is done by parent component
      }
    }
    // Only close for create mode, not for edit
    if (mode === 'create') {
      onOpenChange(false);
    }
  };

  // Reset handler for dialog close
  const handleClose = (open: boolean) => {
    if (!open) {
      // Reset states when closing
      setUpdateSuccessful(false);
      setHasFormChanged(false);
      setCurrentTab('device');
      setCreationSteps(steps);
      setCertificateDetails(null);
      setCertificateBundle(null);
      setCertificateDownloadUrls(null);
      setDeviceId('');
      setMqttPassword('');
      // Reset validation state
      setFormErrors({});
      setHasAttemptedSubmit(false);
      setIsFormValid(false);
      // Don't reset form data in edit mode - it should maintain the device data
      if (mode === 'create') {
        setFormData({
          name: '',
          type: 'sensor',
          serialNumber: '',
          location: '',
          manufacturer: '',
          model: '',
          protocol: 'MQTTS',
          firmware: '',
          tags: [],
          generateCertificate: true,
          certificateGenerationMethod: 'auto-generate' as 'auto-generate' | 'upload-csr',
          certificateType: 'auto' as 'auto' | 'ecc-p256' | 'ecc-p384' | 'rsa-2048' | 'rsa-3072' | 'rsa-4096',
          certificateFormat: 'pem' as 'pem' | 'der' | 'pkcs12',
          csrContent: '',
          csrValid: false,
          csrValidated: false,
          devicePicture: null,
          authMode: 'server_tls',
          industry: '',
          industrySpecificData: {},
          telemetrySchema: {
            schema: {},
            uiSchema: {},
            formData: {}
          },
          actuatorSchema: {
            schema: {},
            uiSchema: {},
            formData: {}
          }
        });
      }
    }
    onOpenChange(open);
  };

  // Simple mode rendering (only for non-enhanced create mode)
  if (!enhancedMode && mode === 'create') {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{device ? 'Edit Device' : 'Add New Device'}</DialogTitle>
            <DialogDescription>
              {device ? 'Update device information' : 'Register a new IoT device'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Device Name</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Temperature Sensor 01"
              required
            />
          </div>
          <div>
            <Label htmlFor="type">Device Type</Label>
            <SearchableSelect
              options={[
                { 
                  value: 'sensor', 
                  label: 'Sensor', 
                  icon: <Gauge className="h-4 w-4 text-blue-500" />
                },
                { 
                  value: 'actuator', 
                  label: 'Actuator', 
                  icon: <Cpu className="h-4 w-4 text-green-500" />
                },
                { 
                  value: 'gateway', 
                  label: 'Gateway', 
                  icon: <Router className="h-4 w-4 text-purple-500" />
                }
              ]}
              value={formData.type}
              onValueChange={(value) => setFormData({ ...formData, type: value as Device['type'] })}
              placeholder="Select device type..."
              searchable={false}
              size="md"
            />
          </div>
          <div>
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              placeholder="e.g., Building A, Floor 2"
            />
          </div>
          <div>
            <Label htmlFor="firmware">Firmware Version</Label>
            <Input
              id="firmware"
              value={formData.firmware}
              onChange={(e) => setFormData({ ...formData, firmware: e.target.value })}
              placeholder="e.g., 1.0.0"
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">
              {device ? 'Update' : 'Register'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
    );
  }

  // Enhanced mode with tab interface (for both create and edit modes)
  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-5xl w-full max-h-[95vh] min-h-[85vh] min-w-0 overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>{mode === 'edit' ? 'Edit Device' : 'Create New Device'}</DialogTitle>
          <DialogDescription>
            {mode === 'edit' 
              ? 'Update device information and configure data schemas'
              : 'Register a new IoT device with integrated certificate generation'}
          </DialogDescription>
        </DialogHeader>

        <Tabs value={currentTab} onValueChange={setCurrentTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className={`grid w-full ${mode === 'edit' ? 'grid-cols-3' : showCertificateTab ? 'grid-cols-6' : 'grid-cols-5'} flex-shrink-0`}>
            <TabsTrigger value="device" disabled={isCreating}>Device Info</TabsTrigger>
            <TabsTrigger value="industry" disabled={isCreating}>Specific Industry</TabsTrigger>
            <TabsTrigger value="schema" disabled={isCreating}>Data Schema</TabsTrigger>
            {mode === 'create' && (
              <>
                {showCertificateTab && (
                  <TabsTrigger value="certificate" disabled={isCreating}>
                    {isTrustMMode ? 'Trust M Setup' : 'Certificate Options'}
                  </TabsTrigger>
                )}
                <TabsTrigger value="progress" disabled={!isCreating}>Progress</TabsTrigger>
                <TabsTrigger value="complete" disabled={!certificateDetails && !deviceId}>Complete</TabsTrigger>
              </>
            )}
          </TabsList>

          <div className="flex-1 overflow-y-auto mt-4 min-h-0">
            {/* Device Information Tab */}
            <TabsContent value="device" className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="device-name">Device Name *</Label>
                  <Input
                    id="device-name"
                    placeholder="e.g., Temperature Sensor A1"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className={formErrors.name ? 'border-red-500 focus:border-red-500' : ''}
                  />
                  {formErrors.name && (
                    <p className="text-sm text-red-600 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {formErrors.name}
                    </p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="device-type">Device Type *</Label>
                  <SearchableSelect
                    options={[
                      { 
                        value: 'sensor', 
                        label: 'Sensor', 
                        description: 'Environmental and data collection devices',
                        icon: <Gauge className="h-4 w-4 text-blue-500" />
                      },
                      { 
                        value: 'actuator', 
                        label: 'Actuator', 
                        description: 'Control and action devices',
                        icon: <Cpu className="h-4 w-4 text-green-500" />
                      },
                      { 
                        value: 'gateway', 
                        label: 'Gateway', 
                        description: 'Network connectivity and data routing',
                        icon: <Router className="h-4 w-4 text-purple-500" />
                      },
                      { 
                        value: 'controller', 
                        label: 'Controller', 
                        description: 'Device management and orchestration',
                        icon: <Network className="h-4 w-4 text-orange-500" />
                      }
                    ]}
                    value={formData.type}
                    onValueChange={(value) => setFormData({ ...formData, type: value as Device['type'] })}
                    placeholder="Select device type..."
                    searchable={false}
                    size="md"
                    aria-label="Device Type"
                  />
                  {formErrors.type && (
                    <p className="text-sm text-red-600 flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {formErrors.type}
                    </p>
                  )}
                </div>
              </div>

              {isTrustMMode && (
                <div className="space-y-4 rounded-md border border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-950/30 px-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="factory-uid">OPTIGA™ Factory UID *</Label>
                      <Input
                        id="factory-uid"
                        value={formData.factoryUid || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, factoryUid: e.target.value }))}
                        placeholder="e.g., 507FB3300A9D4206"
                        className={formErrors.factoryUid ? 'border-red-500 focus:border-red-500' : ''}
                      />
                      {formErrors.factoryUid && (
                        <p className="text-sm text-red-600 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          {formErrors.factoryUid}
                        </p>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="factory-cert">OPTIGA™ Factory Device Certificate (PEM)</Label>
                      <Textarea
                        id="factory-cert"
                        value={formData.factoryCertificate || ''}
                        onChange={(e) => setFormData(prev => ({ ...prev, factoryCertificate: e.target.value }))}
                        rows={6}
                        placeholder={`-----BEGIN CERTIFICATE-----\nMIIB...<redacted>...\n...\n-----END CERTIFICATE-----`}
                        className="font-mono text-xs"
                      />
                      <p className="text-xs text-muted-foreground dark:text-slate-400">
                        Used to fingerprint the OPTIGA™ Trust M factory certificate for the very first TLS session.
                      </p>
                    </div>
                  </div>
                  <Alert className="border-indigo-200 dark:border-indigo-700 bg-white dark:bg-indigo-950/50">
                    <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                    <AlertDescription className="text-sm text-indigo-800 dark:text-indigo-200 space-y-1">
                      <p>
                        🔒 TESAIoT will accept the factory certificate once, then securely transition into TESAIoT-issued credentials.
                      </p>
                      <ul className="list-disc list-inside text-xs space-y-1">
                        <li>Factory certificate is used only for initial onboarding.</li>
                        <li>After onboarding, the device will be issued a unique TESAIoT credential.</li>
                        <li>A protected update process ensures secure credential rotation and automatically disables factory access.</li>
                        <li>OPTIGA™ Trust M key slots: UID at <code>0xE0C2</code>, factory certificate at <code>0xE0E0</code>, CSR/key generation at <code>0xE0F1</code>.</li>
                      </ul>
                    </AlertDescription>
                  </Alert>
                </div>
              )}

              {/* Authentication Mode Selector */}
              <div className="space-y-2">
                <Label htmlFor="auth-mode">Authentication Mode</Label>
                <SearchableSelect
                  options={[
                    {
                      value: 'server_tls',
                      label: 'Server-only TLS (Password Authentication)',
                      description: 'Suitable for devices with limited resources',
                      icon: <Lock className="h-4 w-4 text-blue-500" />
                    },
                    {
                      value: 'mtls',
                      label: 'Mutual TLS (Certificate Authentication)',
                      description: 'Certificate-based authentication (supports Trust M devices)',
                      icon: <ShieldCheck className="h-4 w-4 text-green-500" />
                    }
                  ]}
                  value={formData.authMode}
                  onValueChange={(value) => {
                    const nextMode = value as 'mtls' | 'server_tls';
                    setFormData(prev => ({
                      ...prev,
                      authMode: nextMode,
                      generateCertificate: nextMode === 'mtls',
                      certificateGenerationMethod: nextMode === 'mtls' ? prev.certificateGenerationMethod : 'auto-generate'
                    }));
                    setCreationStep('');
                  }}
                  placeholder="Select authentication mode..."
                  searchable={false}
                  size="md"
                  aria-label="Authentication Mode"
                />
                <div className="text-xs text-muted-foreground space-y-1">
                  <div className="flex items-start gap-2">
                    <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>Server-TLS:</strong> Uses username and password for authentication. Ideal for simpler deployments.
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>mTLS:</strong> Requires digital certificates for both device and server. Provides enhanced security.
                    </div>
                  </div>
                  <div className="flex items-start gap-2">
                    <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <div>
                      <strong>OPTIGA™ Trust M:</strong> Hardware-based onboarding with Infineon factory certificate, then protected update ensures secure rotation to TESAIoT credentials.
                    </div>
                  </div>
                </div>
              </div>

              {/* Trust M UID Field (only for mTLS) */}
              {formData.authMode === 'mtls' && (
                <div className="space-y-2">
                  <Label htmlFor="trustm-uid">
                    Trust M UID (Optional)
                    <span className="text-muted-foreground ml-2 font-normal">— For Infineon OPTIGA™ Trust M devices</span>
                  </Label>
                  <Input
                    id="trustm-uid"
                    placeholder="54 hex characters (e.g., CD16339401001C000100000A026D8E0018003F001D801010712440)"
                    value={formData.trustmUid || ''}
                    onChange={(e) => {
                      const value = e.target.value.trim();
                      setFormData({ ...formData, trustmUid: value });
                    }}
                    className="font-mono text-sm"
                  />
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div className="flex items-start gap-2">
                      <Info className="h-3 w-3 mt-0.5 flex-shrink-0" />
                      <div>
                        Leave empty for standard mTLS. Provide UID for hardware-based Trust M authentication.
                      </div>
                    </div>
                    {formData.trustmUid && formData.trustmUid.length !== 54 && (
                      <div className="flex items-start gap-2 text-amber-600">
                        <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <div>
                          Trust M UID must be exactly 54 hexadecimal characters (current: {formData.trustmUid.length})
                        </div>
                      </div>
                    )}
                    {formData.trustmUid && formData.trustmUid.length === 54 && !/^[0-9A-Fa-f]{54}$/.test(formData.trustmUid) && (
                      <div className="flex items-start gap-2 text-red-600">
                        <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <div>
                          Invalid format: Trust M UID must contain only hexadecimal characters (0-9, A-F)
                        </div>
                      </div>
                    )}
                    {formData.trustmUid && /^[0-9A-Fa-f]{54}$/.test(formData.trustmUid) && (
                      <div className="flex items-start gap-2 text-green-600">
                        <CheckCircle2 className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <div>
                          Valid Trust M UID format
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Communication Protocol selection removed by design. Devices may use MQTTs or HTTPS. */}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="serial-number">Serial Number</Label>
                  <Input
                    id="serial-number"
                    placeholder="e.g., SN-2024-0001"
                    value={formData.serialNumber}
                    onChange={(e) => setFormData({ ...formData, serialNumber: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="location">Location</Label>
                  <Input
                    id="location"
                    placeholder="e.g., Building A, Floor 2"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="manufacturer">Manufacturer</Label>
                  <Input
                    id="manufacturer"
                    placeholder="e.g., Infineon Technology"
                    value={formData.manufacturer}
                    onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Input
                    id="model"
                    placeholder="e.g., PSoC Edge"
                    value={formData.model}
                    onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Device Picture</Label>
                <DevicePictureUpload
                  value={formData.devicePicture}
                  onChange={(imageData) => setFormData({ ...formData, devicePicture: imageData })}
                  disabled={false}
                />
              </div>
            </TabsContent>

            {/* Industry Specific Tab */}
            <TabsContent value="industry" className="h-full space-y-4">
              <IndustrySpecificTab
                formData={formData}
                onChange={setFormData}
                errors={{}}
                mode={mode}
              />
            </TabsContent>

            {/* Data Schema Tab */}
            <TabsContent value="schema" className="h-full space-y-6">
              <Alert className="mb-4">
                <Sparkles className="h-4 w-4" />
                <AlertDescription>
                  Use the <strong>Data Schema Assistant</strong> to create schemas by combining multiple sensors, or select from pre-built templates.
                  The platform ensures secure data transmission based on your selected protocol.
                </AlertDescription>
              </Alert>
              
              <div className="w-full min-w-0">
                <h4 className="text-lg font-semibold mb-4">Telemetry Data Schema</h4>
                <DeviceSchemaEditor
                  deviceType={formData.type}
                  industry={formData.industry}
                  initialSchema={formData.telemetrySchema}
                  onSchemaChange={(schema) =>
                    setFormData({
                      ...formData,
                      telemetrySchema: schema
                    })
                  }
                  onHasUnsavedChanges={setHasUnsavedSchemaChanges}
                  disabled={false}
                />
              </div>
              
              {(formData.type === 'actuator' || formData.type === 'controller') && (
                <div className="w-full min-w-0">
                  <h4 className="text-lg font-semibold mb-4">Actuator Command Schema</h4>
                  <DeviceSchemaEditor
                    deviceType={formData.type}
                    industry={formData.industry}
                    initialSchema={formData.actuatorSchema}
                    onSchemaChange={(schema) =>
                      setFormData({
                        ...formData,
                        actuatorSchema: schema
                      })
                    }
                    onHasUnsavedChanges={setHasUnsavedSchemaChanges}
                    disabled={false}
                  />
                </div>
              )}
            </TabsContent>

            {/* Certificate Options Tab */}
            <TabsContent value="certificate" className="space-y-4">
              {isTrustMMode ? (
                <Card className="border-blue-200">
                  <CardContent className="space-y-4 pt-6">
                    <Alert className="border-blue-100 bg-blue-50">
                      <Shield className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="space-y-2 text-blue-800">
                        <p>
                          <strong>Trust M Workflow:</strong> Factory certificates are used only for the first connection.
                          After the device is online, trigger a <strong>Protected Update</strong> job to rotate into a TESAIoT-issued certificate.
                        </p>
                        <ul className="list-disc list-inside text-sm space-y-1">
                          <li>Store the Infineon trust anchor into OID <code>0xE0E8</code>.</li>
                          <li>Keep the factory certificate in OID <code>0xE0E9</code> (optional, for audit).</li>
                          <li>Protected Update writes the TESAIoT certificate into OID <code>0xE0E1</code> and disables factory access automatically.</li>
                        </ul>
                      </AlertDescription>
                    </Alert>
                    <p className="text-sm text-muted-foreground">
                      Use the generated bundle to populate your project. Download the Protected Update manifest after device creation from the device details page.
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <>
                  {/* Info Alert: CSR Optional or Required based on Trust M UID */}
                  {hasTrustMUid ? (
                    <Alert className="border-blue-200 bg-blue-50">
                      <Info className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-blue-800">
                        <strong>CSR Optional (Trust M UID Provided)</strong>
                        <p className="mt-2">
                          You can skip CSR upload. The device will auto-activate with its factory certificate
                          and send a CSR later via MQTT. Alternatively, provide a CSR now for immediate certificate issuance.
                        </p>
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert className="border-amber-200 bg-amber-50">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <AlertDescription className="text-amber-800">
                        <strong>CSR Required (No Trust M UID)</strong>
                        <p className="mt-2">
                          You must upload a Certificate Signing Request (CSR) for certificate issuance.
                          The device generates and keeps the private key securely.
                        </p>
                      </AlertDescription>
                    </Alert>
                  )}

                  <CertificateOptionsTab
                    formData={{
                      certificateGenerationMethod: formData.certificateGenerationMethod,
                      certificateType: formData.certificateType,
                      certificateFormat: formData.certificateFormat,
                      csrContent: formData.csrContent
                    }}
                    onFormDataChange={(data) => {
                      // Update form data and CSR validation state
                      setFormData(prev => ({ ...prev, ...data }));
                    }}
                    onCSRValidationChange={(isValid: boolean, hasValidated: boolean) => {
                      setFormData(prev => ({
                        ...prev,
                        csrValid: isValid,
                        csrValidated: hasValidated
                      }));
                    }}
                    hasError={!!formErrors.csrContent}
                    errorMessage={formErrors.csrContent}
                  />

                  {/* Validation Alerts for CSR Requirements (only if no Trust M UID) */}
                  {!hasTrustMUid && hasAttemptedSubmit && formErrors.csrContent && (
                    <Alert className="border-red-200 bg-red-50">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <AlertDescription className="text-red-800">
                        <strong>Validation Error:</strong> {formErrors.csrContent}
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </TabsContent>

            {/* Progress Tab */}
            <TabsContent value="progress" className="space-y-4">
              <div className="space-y-4">
                {creationSteps.map((step, index) => (
                  <div key={step.id} className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      {step.status === 'completed' && (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      )}
                      {step.status === 'active' && (
                        <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                      )}
                      {step.status === 'pending' && (
                        <div className="h-5 w-5 rounded-full border-2 border-gray-300" />
                      )}
                      {step.status === 'error' && (
                        <AlertTriangle className="h-5 w-5 text-red-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <div className={`text-sm font-medium ${
                        step.status === 'active' ? 'text-blue-600' : 
                        step.status === 'completed' ? 'text-green-600' :
                        step.status === 'error' ? 'text-red-600' : 'text-gray-500'
                      }`}>
                        {step.label}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {creationStep && (
                <div className="mt-6 text-center text-sm text-muted-foreground">
                  {creationStep}
                </div>
              )}
            </TabsContent>

            {/* Complete Tab */}
            <TabsContent value="complete" className="space-y-4">
              <Alert className="border-green-200 bg-green-50">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  Device created successfully! {
                    certificateDetails ? 'Certificate generated and ready for download.' : 
                    formData.authMode === 'server_tls' ? 'MQTT credentials generated.' :
                    false ? 'Trust M starter bundle prepared.' :
                    'No certificate was requested.'
                  }
                </AlertDescription>
              </Alert>

              {false && (
                <Card>
                  <CardContent className="pt-6 space-y-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Shield className="h-4 w-4 text-indigo-500" />
                      OPTIGA™ Trust M Starter Bundle
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Download the factory onboarding bundle for the OPTIGA™ Trust M device. This includes the Infineon
                      trust anchor, recorded factory certificate, and a preconfigured `mqtt_client_config.h` for the
                      PSoC Edge sample.
                    </p>
                    <Button
                      variant="primary"
                      onClick={downloadTrustMBundle}
                      disabled={isDownloadingTrustMBundle}
                    >
                      {isDownloadingTrustMBundle ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Preparing download...
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4 mr-2" />
                          Download Trust M Starter Bundle
                        </>
                      )}
                    </Button>
                    <p className="text-xs text-muted-foreground">
                      Use this bundle for the first boot. After the device connects with its factory certificate, run a
                      Protected Update job to rotate into TESAIoT-issued credentials.
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Server‑TLS Bundle Download (with role‑gated toggles) */}
              {formData.authMode === 'server_tls' && (
                <Card>
                  <CardContent className="pt-6 space-y-4">
                    <h3 className="font-semibold">Download Server‑TLS Bundles</h3>
                    <div className="text-sm text-muted-foreground">
                      Includes CA chain plus selected credentials for faster provisioning.
                    </div>
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="inc-pass">Include Password (one‑time)</Label>
                          {!isHighRole && (
                            <div className="text-xs text-muted-foreground">Restricted to Org Admin only</div>
                          )}
                        </div>
                        <Switch
                          id="inc-pass"
                          checked={bundleIncludePassword && isHighRole}
                          onCheckedChange={setBundleIncludePassword}
                          disabled={!isHighRole}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="space-y-0.5">
                          <Label htmlFor="inc-api">Include API Key</Label>
                          {!isHighRole && (
                            <div className="text-xs text-muted-foreground">Restricted to Org Admin only</div>
                          )}
                        </div>
                        <Switch
                          id="inc-api"
                          checked={bundleIncludeApiKey && isHighRole}
                          onCheckedChange={setBundleIncludeApiKey}
                          disabled={!isHighRole}
                        />
                      </div>
                      {/* Effective policy banner (read-only) */}
                      <div className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                        <div>
                          Password include: <span className={policyAllowBundlePass ? 'text-green-700' : 'text-red-700'}>{policyAllowBundlePass ? 'Allowed' : 'Blocked'}</span> (source: {policySourcePass})
                        </div>
                        <div>
                          API key include: <span className={policyAllowBundleApi ? 'text-green-700' : 'text-red-700'}>{policyAllowBundleApi ? 'Allowed' : 'Blocked'}</span> (source: {policySourceApi})
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      <Button variant="outline" onClick={() => downloadServerTlsBundle('mqtt')}>
                        <Download className="h-4 w-4 mr-2" /> Download MQTTS Server‑TLS Bundle
                      </Button>
                      <Button variant="outline" onClick={() => downloadServerTlsBundle('https')}>
                        <Download className="h-4 w-4 mr-2" /> Download HTTPS Server‑TLS Bundle
                      </Button>
                    </div>
                    <div className="mt-2">
                      <Button variant="outline" className="w-full" onClick={() => downloadMqttQuicServerTlsBundle()}>
                        <Download className="h-4 w-4 mr-2" /> Download MQTT-QUIC Server‑TLS Bundle
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* MQTT Password Display for Server-TLS devices */}
              {formData.authMode === 'server_tls' && mqttPassword && (
                <>
                  <Card>
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <Key className="h-4 w-4" />
                        MQTT Credentials
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Username (Device ID)</div>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm font-mono">{deviceId}</code>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(deviceId);
                                toast.success('Device ID copied to clipboard');
                              }}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Password</div>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm font-mono">{mqttPassword}</code>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(mqttPassword);
                                toast.success('Password copied to clipboard');
                              }}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        
                        <div className="pt-4 border-t">
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => {
                              const credentials = `MQTT Credentials for Device: ${formData.name}\n` +
                                `================================\n\n` +
                                `Device ID (Username): ${deviceId}\n` +
                                `Password: ${mqttPassword}\n\n` +
                                `MQTT Broker: mqtts://your-broker-address:8883\n` +
                                `Authentication Mode: Server-TLS (Password-based)\n\n` +
                                `Note: This password cannot be retrieved after closing this dialog.\n` +
                                `Please store it securely.`;
                              
                              downloadFile(credentials, `${deviceId}-mqtt-credentials.txt`);
                              toast.success('Credentials file downloaded');
                            }}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Download Credentials
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Alert className="border-amber-200 bg-amber-50">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-amber-800">
                      <strong>Important:</strong> This password is shown only once and cannot be retrieved later. 
                      Please save it securely before closing this dialog.
                    </AlertDescription>
                  </Alert>
                </>
              )}

              {/* HTTPs API Key (shown when available) */}
              {formData.authMode === 'server_tls' && httpsApiKey && (
                <>
                  <Card>
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <Key className="h-4 w-4" />
                        HTTPs API Credentials
                      </h3>
                      <div className="space-y-4">
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">Device ID</div>
                          <code className="px-3 py-2 bg-muted rounded-md text-sm font-mono block">{deviceId}</code>
                        </div>
                        <div>
                          <div className="text-sm text-muted-foreground mb-1">API Key</div>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 px-3 py-2 bg-muted rounded-md text-sm font-mono">{httpsApiKey}</code>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                navigator.clipboard.writeText(httpsApiKey);
                                toast.success('API key copied to clipboard');
                              }}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const credentials = 
                                `HTTPs API Credentials for Device: ${formData.name}\n` +
                                `================================\n\n` +
                                `Device ID: ${deviceId}\n` +
                                `API Key: ${httpsApiKey}\n\n` +
                                `API Endpoint: https://your-api-endpoint/api/v1/devices/${deviceId}/telemetry\n` +
                                `Authentication: Bearer Token (use API key as bearer token)\n\n` +
                                `Example curl command:\n` +
                                `curl -X POST https://your-api-endpoint/api/v1/devices/${deviceId}/telemetry \\\n` +
                                `  -H "Authorization: Bearer ${httpsApiKey}" \\\n` +
                                `  -H "Content-Type: application/json" \\\n` +
                                `  -d '{"temperature": 25.5, "humidity": 60}'\n\n` +
                                `Note: This API key is shown only once during device creation.\n` +
                                `Please store it securely.`;
                              
                              downloadFile(credentials, `${deviceId}-https-api-credentials.txt`);
                              toast.success('API credentials file downloaded');
                            }}
                          >
                            <Download className="h-4 w-4 mr-2" />
                            Download API Credentials
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Alert className="border-amber-200 bg-amber-50">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-amber-800">
                      <strong>Important:</strong> This API key is shown only once and cannot be retrieved later. 
                      Please save it securely before closing this dialog.
                    </AlertDescription>
                  </Alert>
                </>
              )}

              {certificateDetails && (
                <>
                  <Card>
                    <CardContent className="pt-6">
                      <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        Certificate Details
                      </h3>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Algorithm</div>
                          <div className="font-medium">{certificateDetails.algorithm}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Key Size</div>
                          <div className="font-medium">{certificateDetails.keySize}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Validity</div>
                          <div className="font-medium">{certificateDetails.validity}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Serial Number</div>
                          <div className="font-medium font-mono text-xs">{certificateDetails.serialNumber}</div>
                        </div>
                        <div className="col-span-2">
                          <div className="text-muted-foreground">Subject</div>
                          <div className="font-medium font-mono text-xs">{certificateDetails.subject}</div>
                        </div>
                        <div className="col-span-2">
                          <div className="text-muted-foreground">Issuer</div>
                          <div className="font-medium">{certificateDetails.issuer}</div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <div className="space-y-3">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Download className="h-4 w-4" />
                      Download Options
                    </h3>
                    
                    <div className="grid grid-cols-2 gap-3">
                      <Button 
                        variant="outline" 
                        className="justify-start"
                        onClick={() => downloadFile(certificateBundle!.certificate, `${deviceId}.crt`)}
                      >
                        <FileText className="h-4 w-4 mr-2" />
                        Device Certificate
                      </Button>
                      {/* Only show private key download if available (auto-generated certificates) */}
                      {certificateBundle?.privateKey && (
                        <Button 
                          variant="outline" 
                          className="justify-start"
                          onClick={() => downloadFile(certificateBundle!.privateKey, `${deviceId}.key`)}
                        >
                          <Key className="h-4 w-4 mr-2" />
                          Private Key
                        </Button>
                      )}
                      {/* Show public key for CSR certificates */}
                      {certificateBundle?.publicKey && !certificateBundle?.privateKey && (
                        <Button 
                          variant="outline" 
                          className="justify-start"
                          onClick={() => downloadFile(certificateBundle!.publicKey, `${deviceId}.pub`)}
                        >
                          <Key className="h-4 w-4 mr-2" />
                          Public Key
                        </Button>
                      )}
                      <Button 
                        variant="outline" 
                        className="justify-start"
                        onClick={() => downloadFile(certificateBundle!.caChain, `${deviceId}-ca.crt`)}
                      >
                        <Shield className="h-4 w-4 mr-2" />
                        CA Certificate
                      </Button>
                      <Button 
                        variant="outline" 
                        className="justify-start"
                        onClick={downloadAllCertificates}
                      >
                        <Package className="h-4 w-4 mr-2" />
                        Download All
                      </Button>
                    </div>

                    <div className="flex justify-end pt-2">
                      <Button variant="outline" className="min-w-[180px]">
                        <QrCode className="h-4 w-4 mr-2" />
                        Generate QR Code
                      </Button>
                    </div>
                  </div>

                  {/* Different security notices for CSR vs auto-generated certificates */}
                  {certificateBundle?.privateKey ? (
                    <Alert>
                      <Lock className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Security Notice:</strong> The private key has been displayed only once. 
                        Store it securely and never share it. You cannot retrieve it again.
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert className="border-blue-200 bg-blue-50">
                      <Info className="h-4 w-4 text-blue-600" />
                      <AlertDescription className="text-blue-800">
                        <strong>CSR Certificate:</strong> This certificate was signed from your CSR. 
                        The private key remains under your management and was not generated by the platform.
                      </AlertDescription>
                    </Alert>
                  )}
                </>
              )}
            </TabsContent>
          </div>
        </Tabs>

        <DialogFooter className="mt-auto pt-4 flex-shrink-0">
          {mode === 'edit' ? (
            // Edit mode footer
            <>
              <Button variant="outline" onClick={() => handleClose(false)}>
                {updateSuccessful ? 'Close' : 'Cancel'}
              </Button>
              <Button onClick={handleSubmit} disabled={isCreating || (updateSuccessful && !hasFormChanged)}>
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Updating...
                  </>
                ) : updateSuccessful && !hasFormChanged ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Updated
                  </>
                ) : (
                  'Update Device'
                )}
              </Button>
            </>
          ) : (
            // Create mode footer
            <>
              {currentTab === 'device' && (
                <>
                  <Button variant="outline" onClick={() => handleClose(false)}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={() => {
                      // Quick validation for required fields before moving to next tab
                      if (!formData.name?.trim()) {
                        setHasAttemptedSubmit(true);
                        validateForm();
                        return;
                      }
                      setCurrentTab('industry');
                    }}
                    disabled={!formData.name?.trim()}
                  >
                    Next: Industry Specific
                  </Button>
                </>
              )}
              
              {currentTab === 'industry' && (
                <>
                  <Button variant="outline" onClick={() => setCurrentTab('device')}>
                    Back
                  </Button>
                  <Button onClick={() => setCurrentTab('schema')}>
                    Next: Data Schema
                  </Button>
                </>
              )}
              
              {currentTab === 'schema' && (
                <>
                  <Button variant="outline" onClick={() => setCurrentTab('industry')}>
                    Back
                  </Button>
                  {formData.authMode === 'mtls' ? (
                    <Button onClick={() => handleSchemaNavigation('certificate')}>
                      Next: Certificate Options
                    </Button>
                  ) : (
                    <Button
                      onClick={() => {
                        if (hasUnsavedSchemaChanges) {
                          setPendingNavigation('create');
                          setShowUnsavedWarningDialog(true);
                        } else {
                          handleCreateDevice();
                        }
                      }}
                      disabled={isCreating || (hasAttemptedSubmit && !isFormValid)}
                    >
                      {isCreating ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create Device'
                      )}
                    </Button>
                  )}
                </>
              )}
              
              {currentTab === 'certificate' && (
                <>
                  <Button variant="outline" onClick={() => setCurrentTab('schema')}>
                    Back
                  </Button>
                  <Button
                    onClick={handleCreateDevice}
                    disabled={
                      isCreating ||
                      (hasAttemptedSubmit && !isFormValid) ||
                      (formData.generateCertificate &&
                       formData.certificateGenerationMethod === 'upload-csr' &&
                       !formData.trustmUid?.trim() &&  // Only require CSR if NO Trust M UID
                       (!formData.csrContent?.trim() || !formData.csrValid))
                    }
                  >
                    {isCreating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        {formData.certificateGenerationMethod === 'upload-csr' ? 'Creating & Signing CSR...' : 'Creating...'}
                      </>
                    ) : (
                      <>
                        {formData.certificateGenerationMethod === 'upload-csr' ? 'Create Device & Sign CSR' : 'Create Device'}
                        {formData.generateCertificate &&
                         formData.certificateGenerationMethod === 'upload-csr' &&
                         !formData.trustmUid?.trim() &&
                         !formData.csrContent?.trim() && (
                          <span className="ml-2 text-xs opacity-60">(CSR Required)</span>
                        )}
                      </>
                    )}
                  </Button>
                </>
              )}
              
              {currentTab === 'progress' && (
                <Button disabled>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </Button>
              )}
              
              {currentTab === 'complete' && (
                <Button onClick={() => handleClose(false)}>
                  Done
                </Button>
              )}
            </>
          )}
        </DialogFooter>
      </DialogContent>

      {/* Unsaved Schema Changes Warning Dialog */}
      <AlertDialog open={showUnsavedWarningDialog} onOpenChange={setShowUnsavedWarningDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved Schema Changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have made changes to the schema that have not been saved.
              If you continue without saving, these changes will be lost when you navigate away.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={handleCancelNavigation}>
              Go Back to Save
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmNavigation}>
              Continue Without Saving
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Dialog>
  );
};
