/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect } from 'react';
import CsrUploadPanel from '@/features/certificates/components/CsrUploadPanel';
import { CertificateOptionsTab } from '@/features/devices/components/CertificateOptionsTab';
import {
  CertificateGenerationMethod,
  CertificateType,
  CertificateFormat,
  CSRValidationState,
  CertificateFormData
} from '@/features/devices/types/device.types';
import { useNavigate } from 'react-router-dom';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogDescription,
  DialogFooter
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Download,
  Shield,
  ShieldCheck,
  Key,
  FileText,
  Package,
  Info,
  CheckCircle,
  AlertCircle,
  Cpu,
  Wifi,
  AlertTriangle,
  Clock,
  Lock,
  Unlock,
  RefreshCw,
  Copy,
  ExternalLink,
  Activity,
  Fingerprint,
  Server,
  Zap,
  HelpCircle,
  KeyRound,
  FileKey2,
  FileKey,
  Loader2
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { getFeatureFlags } from '@/config/features.config';
import authFetch from '@/utils/auth-fetch';
import { AuthTokenManager } from '@/utils/auth-token-manager';
import { deviceService } from '../services/deviceService';

interface CertificateGenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  device: any;
  onSuccess?: () => void;
  defaultTab?: 'overview' | 'download' | 'lifecycle' | 'technical';
}

// Certificate lifecycle states
type CertificateState = 'checking' | 'none' | 'valid' | 'expiring' | 'expired' | 'generating' | 'error';

interface CertificateMetrics {
  totalGenerated: number;
  lastGeneratedAt?: string;
  averageLifetime?: number;
  renewalCount: number;
}

export const CertificateGenerationDialog: React.FC<CertificateGenerationDialogProps> = (
  p,
) => {
  // Avoid using names like "isOpen", "visible" or even "props" directly to
  // prevent any chance of minifier hoisting producing free identifiers.
  const dialogOpenFlag = !!p.isOpen;
  const onClose = p.onClose;
  const device = p.device;
  const onSuccess = p.onSuccess;
  // NOTE: derive initial tab via useState initializer function to avoid any
  // chance of a free identifier being referenced at module evaluation time.
  const [isGenerating, setIsGenerating] = useState(false);
  const [certificateInfo, setCertificateInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasExistingCert, setHasExistingCert] = useState(false);
  const [certState, setCertState] = useState<CertificateState>('checking');
  const [activeTab, setActiveTab] = useState<'overview' | 'download' | 'lifecycle' | 'technical'>(() => (p.defaultTab as any) ?? 'overview');
  const featureFlags = getFeatureFlags();
  const [downloadProgress, setDownloadProgress] = useState<Record<string, number>>({});
  const [certMetrics, setCertMetrics] = useState<CertificateMetrics>({
    totalGenerated: 0,
    renewalCount: 0
  });
  const [copySuccess, setCopySuccess] = useState<Record<string, boolean>>({});
  const [showPublicKeyDialog, setShowPublicKeyDialog] = useState(false);
  const [publicKeyFormat, setPublicKeyFormat] = useState<'pem' | 'der' | 'json'>('pem');
  const [policy, setPolicy] = useState<any>(null);
  // CSR replace/renew states
  const [csrContent, setCsrContent] = useState<string>('');
  const [csrFileName, setCsrFileName] = useState<string>('');
  const [isSigningCSR, setIsSigningCSR] = useState<boolean>(false);
  // Renewal flow state (reuses Create Device UI options)
  const [renewForm, setRenewForm] = useState<CertificateFormData>({
    certificateGenerationMethod: CertificateGenerationMethod.AUTO_GENERATE,
    certificateType: CertificateType.ECC_P256,
    certificateFormat: CertificateFormat.PEM,
    csrContent: '',
    validityDays: 365,
  });
  const [renewValidation, setRenewValidation] = useState<CSRValidationState | undefined>(undefined);
  const [revokeOldOnRenew, setRevokeOldOnRenew] = useState<boolean>(false);
  const navigate = useNavigate();
  const [isDownloadingTrustMBundle, setIsDownloadingTrustMBundle] = useState(false);

  // Enhanced device categorization with resource constraints
  const deviceCategories = {
    ultraLowPower: ['sensor', 'air_quality', 'temperature_sensor', 'pressure_sensor', 
                     'soil_moisture', 'parking_sensor', 'humidity_sensor', 'light_sensor'],
    lowPower: ['actuator', 'streetlight', 'traffic_sensor', 'weather_station', 'smart_meter'],
    medium: ['fpga_edge', 'patient_monitor', 'industrial_controller', 'plc_controller'],
    highPerformance: ['gateway', 'iot_gateway', 'edge_server', 'mini_pc', 'edge_compute', 
                      'fog_node', 'router', 'concentrator']
  };

  const getDeviceCategory = () => {
    const type = device?.type || 'sensor';
    for (const [category, types] of Object.entries(deviceCategories)) {
      if (types.includes(type)) return category;
    }
    return 'ultraLowPower'; // Default to most constrained
  };

  const deviceCategory = getDeviceCategory();
  const isIoTDevice = ['ultraLowPower', 'lowPower', 'medium'].includes(deviceCategory);
  const authMode = String(device?.auth_mode || '').toLowerCase();
  const metadata = device?.metadata || {};
  const secureElement = metadata.secure_element || metadata.secureElement;
  const trustProfile = device?.trust_profile || metadata.trust_profile;
  const factoryUid = metadata.factory_uid;
  const isTrustMDevice = authMode === 'optiga_trust_mtls'
    || authMode === 'trustm_mtls'
    || authMode === 'optiga_trustm'
    || secureElement === 'infineon_optiga_trust_m'
    || trustProfile === 'infineon_optiga_trust_m'
    || (!!factoryUid && !!metadata.protected_update_enabled)
    || !!device?.trustm_uid; // Trust M UID indicates Trust M device

  const handleDownloadTrustMStarterBundle = async () => {
    if (!device?.device_id) {
      toast.error('Device ID missing — cannot download Trust M bundle');
      return;
    }
    setIsDownloadingTrustMBundle(true);
    try {
      const response = await deviceService.downloadCertificateResponse(device.device_id, 'trustm-starter-bundle');
      if (!response.ok) {
        const details = await response.text().catch(() => '');
        throw new Error(details || 'Failed to download Trust M MQTTs + HTTPS bundle');
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
        filename = `${device.device_id}-trustm-mqtts-https-bundle-${ts}.zip`;
      }
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast.success('OPTIGA™ Trust M MQTTs + HTTPS bundle download started');
    } catch (bundleError: any) {
      console.error('Trust M bundle download failed:', bundleError);
      toast.error(bundleError?.message || 'Failed to download Trust M MQTTs + HTTPS bundle');
    } finally {
      setIsDownloadingTrustMBundle(false);
    }
  };

  // Check for existing certificate when dialog opens (only for mTLS devices, skip CSR devices)
  useEffect(() => {
    // Intentionally keep logs minimal in production build
    if (!dialogOpenFlag || !device) return;
      // Fetch org certificate policy to gate UI surface
      (async () => {
        try {
          const res = await authFetch('/api/v1/certificates/policies/certificates', { method: 'GET' });
          const json = await res.json();
          setPolicy(json.policy || {});
          // Default lifecycle toggles from org policy when dialog opens
          const p = json.policy || {};
          if (typeof p.auto_revoke_on_renew === 'boolean') setRevokeOldOnRenew(!!p.auto_revoke_on_renew);
          else if (typeof p.auto_revoke_previous_certificate === 'boolean') setRevokeOldOnRenew(!!p.auto_revoke_previous_certificate);
          else if (typeof p.auto_revoke === 'boolean') setRevokeOldOnRenew(!!p.auto_revoke);
        } catch (e) {
          setPolicy({});
        }
      })();

      // Subscribe to Settings broadcasts so the dialog syncs without manual refresh
      const handlePolicyUpdate = (e: Event) => {
        const pol = (e as CustomEvent).detail || {};
        setPolicy(pol);
        if (typeof pol.auto_revoke_on_renew === 'boolean') setRevokeOldOnRenew(!!pol.auto_revoke_on_renew);
        else if (typeof pol.auto_revoke_previous_certificate === 'boolean') setRevokeOldOnRenew(!!pol.auto_revoke_previous_certificate);
        else if (typeof pol.auto_revoke === 'boolean') setRevokeOldOnRenew(!!pol.auto_revoke);
      };
      const handleSoftRefresh = async () => {
        try {
          const res = await authFetch('/api/v1/certificates/policies/certificates', { method: 'GET' });
          const json = await res.json();
          handlePolicyUpdate(new CustomEvent('org-policy-updated', { detail: json.policy || {} }));
        } catch {}
      };
      window.addEventListener('org-policy-updated', handlePolicyUpdate as any);
      window.addEventListener('certificate-dialog-soft-refresh', handleSoftRefresh as any);
      // Check if this is a CSR device - comprehensive check for all possible CSR indicators
      const isCsr = !!(
        device.generation_method === 'upload_csr' ||
        device.generation_method === 'upload-csr' ||
        device.metadata?.certificate_generation_method === 'upload-csr' ||
        device.metadata?.certificate_generation_method === 'upload_csr' ||
        device.csr_provided === true ||
        device.certificate_type === 'user_csr' ||
        device.certificate_type === 'USER_CSR' ||
        device.certificate_generation_method === 'upload-csr' ||
        device.certificate_generation_method === 'upload_csr' ||
        // Check if device name indicates CSR (fallback)
        (device.name && device.name.toLowerCase().includes('csr'))
      );
      
      console.log('CertificateGenerationDialog: isCSRDevice:', isCsr);
      console.log('CertificateGenerationDialog: device.certificate_generation_method:', device.certificate_generation_method);
      console.log('CertificateGenerationDialog: device.generation_method:', device.generation_method);
      console.log('CertificateGenerationDialog: device.csr_provided:', device.csr_provided);
      
      // For CSR devices, we still need to check if certificate exists
      // CSR devices should have certificates after signing
      if (isCsr) {
        // Check if CSR device has a signed certificate
        if (device.certificate_status === 'valid' || device.certificate_status === 'Valid') {
          // CSR device has a valid certificate, fetch it
          checkExistingCertificate();
        } else {
          // CSR device certificate not yet signed
          setLoading(false);
          setCertState('none');
          setCertificateInfo(null);
        }
      } else if (device.auth_mode !== 'server_tls') {
        checkExistingCertificate();
      } else {
        // For server_tls devices, just set loading to false
        setLoading(false);
        setCertState('none');
      }
      return () => {
        window.removeEventListener('org-policy-updated', handlePolicyUpdate as any);
        window.removeEventListener('certificate-dialog-soft-refresh', handleSoftRefresh as any);
      };
  }, [dialogOpenFlag, device]);

  // Reset active tab whenever dialog opens or defaultTab prop changes
  useEffect(() => {
    if (dialogOpenFlag) {
      setActiveTab(((p.defaultTab as any) ?? 'overview'));
    }
  }, [dialogOpenFlag, p.defaultTab]);

  // Prefill recommended SANs for CSR devices (non-destructive; only when empty)
  useEffect(() => {
    if (!dialogOpenFlag || !device) return;
    const deviceIdentifier = device.device_id || device.serialNumber || device._id || device.id;
    if (!deviceIdentifier) return;
    if (!isCSRDevice()) return;
    // Prefill once when empty to guide users
    // @ts-ignore allow flexible field
    if (!(renewForm as any).csrAltNames) {
      const recommended = `DNS:${deviceIdentifier},URI:urn:tesa:device:${deviceIdentifier}`;
      setRenewForm(prev => ({ ...(prev as any), csrAltNames: recommended } as any));
    }
  }, [dialogOpenFlag, device]);

  const checkExistingCertificate = async () => {
    if (!device) return;
    
    setLoading(true);
    setError(null);
    setCertState('checking');
    
    try {
      // Use actual device_id for API calls
      const deviceIdentifier = device.device_id || device.serialNumber || device._id || device.id;
      const response = await authFetch(`/api/v1/certificates/devices/${deviceIdentifier}/certificate`);
      
      if (response.ok) {
        const data = await response.json();
        console.log('[CertificateDialog] Certificate check response:', {
          exists: data.exists,
          hasCertificate: !!data.certificate,
          certificateKeys: data.certificate ? Object.keys(data.certificate) : [],
          deviceName: device.name,
          generationMethod: device.generation_method,
          csrProvided: device.csr_provided
        });
        
        // STRICT validation: Only set certificate info if we have ALL required fields
        const hasValidCertificate = data.exists && 
                                   data.certificate && 
                                   data.certificate.expires_at &&
                                   data.certificate.serial_number &&
                                   data.certificate.issued_at;
        
        if (hasValidCertificate) {
          console.log('[CertificateDialog] Valid certificate found, enabling downloads');
          setCertificateInfo({ certificate: data.certificate });
          setHasExistingCert(true);
          
          // Calculate certificate state
          const expiresAt = new Date(data.certificate.expires_at);
          const now = new Date();
          const daysUntilExpiry = Math.floor((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
          
          if (daysUntilExpiry < 0) {
            setCertState('expired');
          } else if (daysUntilExpiry < 30) {
            setCertState('expiring');
          } else {
            setCertState('valid');
          }
          
          // Update metrics
          setCertMetrics(prev => ({
            ...prev,
            totalGenerated: data.metrics?.totalGenerated || 1,
            lastGeneratedAt: data.certificate.issued_at,
            renewalCount: data.metrics?.renewalCount || 0
          }));
        } else if (data.exists && (data.not_after || data.not_before || data.serial_number)) {
          // Modular API shape normalization (no nested certificate object)
          const issuedAt = (data.not_before || data.issued_at || new Date().toISOString());
          const expiresAt = (data.not_after || data.expires_at || new Date(Date.now() + 86400000).toISOString());
          const certObj = {
            serial_number: data.serial_number || data.certificate_id || data.fingerprint || 'unknown',
            issued_at: issuedAt,
            expires_at: expiresAt,
            key_algorithm: data.algorithm || (device?.certificate_algorithm ? algorithmDisplayMap[normalizeAlgorithm(device?.certificate_algorithm) || 'ecc-p256']?.type : undefined)
          } as any;
          setCertificateInfo({ certificate: certObj });
          setHasExistingCert(true);
          // Evaluate state
          const expiresDt = new Date(expiresAt);
          const days = Math.floor((expiresDt.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
          setCertState(days < 0 ? 'expired' : days < 30 ? 'expiring' : 'valid');
        } else {
          // No full certificate info yet
          setHasExistingCert(false);
          // If device shows issuance metadata (compat flow), reflect processing state
          const deviceHasIssuedMeta = Boolean(
            device?.certificate_serial || device?.certificate_issued_at || device?.certificate_status === 'valid'
          );
          setCertState(deviceHasIssuedMeta ? 'generating' : 'none');
          setCertificateInfo(null); // Clear any existing certificate info
        }
      }
    } catch (err) {
      console.error('Failed to check certificate:', err);
      setCertState('error');
    } finally {
      setLoading(false);
    }
  };

  // Algorithm display mapping (dynamic based on device/cert data)
  const algorithmDisplayMap: Record<string, any> = {
    'ecc-p256': {
      type: 'ECC P-256',
      icon: Zap,
      badge: 'Ultra-Low Power',
      color: 'text-green-600',
      description: 'Minimal power consumption for battery-operated sensors',
      benefits: ['10-year battery life', '256-bit security', 'Fast wake-up time', 'Minimal memory usage'],
      specs: { keySize: '256 bits', signatureSize: '64 bytes', processingTime: '< 50ms', powerUsage: '< 1mW' }
    },
    'ecc-p384': {
      type: 'ECC P-384',
      icon: Activity,
      badge: 'Edge Computing',
      color: 'text-purple-600',
      description: 'Enhanced security for gateway and edge devices',
      benefits: ['Stronger security', 'Future-proof', 'Good performance', 'Supports post-quantum transition'],
      specs: { keySize: '384 bits', signatureSize: '96 bytes', processingTime: '< 200ms', powerUsage: '< 100mW' }
    },
    'rsa-3072': {
      type: 'RSA 3072',
      icon: Server,
      badge: 'Enterprise Grade',
      color: 'text-orange-600',
      description: 'Optimal security/performance balance for gateways and edge servers',
      benefits: ['128-bit security strength', 'NIST approved beyond 2030', 'Hardware acceleration support', '2x faster than RSA 4096'],
      specs: { keySize: '3072 bits', signatureSize: '384 bytes', processingTime: '< 250ms', powerUsage: 'Moderate' }
    },
    'rsa-4096': {
      type: 'RSA 4096',
      icon: Server,
      badge: 'Max Security',
      color: 'text-orange-700',
      description: 'Maximum cryptographic strength with higher CPU usage',
      benefits: ['High security margin', 'Broad compatibility'],
      specs: { keySize: '4096 bits', signatureSize: '512 bytes', processingTime: '< 500ms', powerUsage: 'Higher' }
    }
  };

  // Fallback mapping based on device category (used when device has no explicit algorithm)
  const categoryFallbackMap: Record<string, string> = {
    ultraLowPower: 'ecc-p256',
    lowPower: 'ecc-p256',
    medium: 'ecc-p384',
    highPerformance: 'rsa-3072'
  };

  // Normalize any algorithm string from device/cert/metadata to canonical keys above
  const normalizeAlgorithm = (value?: string | null): string | null => {
    if (!value) return null;
    const v = String(value).toLowerCase().replace(/_/g, '-');
    const map: Record<string, string> = {
      'ecc256': 'ecc-p256',
      'p-256': 'ecc-p256',
      'prime256v1': 'ecc-p256',
      'secp256r1': 'ecc-p256',
      'ecc p-256': 'ecc-p256',
      'ecc 256': 'ecc-p256',
      'ecc-p256': 'ecc-p256',
      'ecc384': 'ecc-p384',
      'p-384': 'ecc-p384',
      'secp384r1': 'ecc-p384',
      'ecc p-384': 'ecc-p384',
      'ecc 384': 'ecc-p384',
      'ecc-p384': 'ecc-p384',
      'rsa3072': 'rsa-3072',
      'rsa-3072': 'rsa-3072',
      'rsa4096': 'rsa-4096',
      'rsa-4096': 'rsa-4096',
      'rsa 3072': 'rsa-3072',
      'rsa 4096': 'rsa-4096'
    };
    return map[v] || null;
  };

  // Determine selected algorithm: prefer active certificate, then device fields, else category fallback
  const algoFromCert = normalizeAlgorithm(certificateInfo?.certificate?.key_algorithm);
  const algoFromDevice = normalizeAlgorithm(device?.certificate_algorithm) ||
                         normalizeAlgorithm(device?.metadata?.certificate_algorithm);
  const resolvedAlgorithm = (
    algoFromCert ||
    algoFromDevice ||
    categoryFallbackMap[deviceCategory] ||
    'ecc-p256'
  );
  const explicitAlgorithmSource: 'certificate' | 'device' | null = algoFromCert ? 'certificate' : (algoFromDevice ? 'device' : null);
  
  const keyInfo = algorithmDisplayMap[resolvedAlgorithm];

  // CSR-aware presentation: if in CSR mode and algorithm cannot be inferred yet,
  // render a neutral CSR card instead of showing the auto-selection (e.g., RSA 3072).
  const csrMode = isCSRDevice();
  const csrAlgorithmKnown = Boolean(algoFromCert || algoFromDevice);

  // Build dynamic header title and badge based on mode
  let headerTitle: string = explicitAlgorithmSource ? 'Selected Algorithm' : 'Automatic Key Algorithm Selection';
  let badgeText: string = keyInfo?.badge || '';
  let badgeBgClass: string = keyInfo?.color ? keyInfo.color.replace('text-', 'bg-').replace('600', '100') : '';

  // When CSR mode, prefer CSR wording
  if (csrMode) {
    headerTitle = 'CSR-Selected Algorithm';
    badgeText = 'User CSR';
    // Keep badge color tied to ECC/RSA if known; otherwise use neutral emerald
    badgeBgClass = csrAlgorithmKnown && keyInfo?.color
      ? keyInfo.color.replace('text-', 'bg-').replace('600', '100')
      : 'bg-emerald-100';
  }

  // Final key info for rendering: use neutral CSR card if CSR algorithm not yet known
  const displayedKeyInfo = (csrMode && !csrAlgorithmKnown)
    ? {
        type: 'CSR-Selected',
        icon: KeyRound,
        badge: 'User CSR',
        color: 'text-emerald-600',
        description: 'Uses the key algorithm embedded in your CSR (e.g., ECC P-256). The exact algorithm will appear after signing.',
        benefits: [
          'Device-generated private key (no key-at-rest)',
          'Meets NIST SP 800-57 CSR model',
          'Best for constrained devices and HSM/TPM use'
        ],
        specs: { keySize: 'From CSR', signatureSize: 'From CSR', processingTime: '—', powerUsage: '—' }
      }
    : keyInfo;

  // Enhanced CSR device detection function
  function isCSRDevice() {
    if (!device) return false;

    // IMPORTANT: Trust M devices are NOT CSR devices even if name contains "CSR"
    // Trust M devices use factory certificates, not user-provided CSR
    // Check both snake_case (from API) and camelCase (from UI)
    const trustMUid = (device as any).trustm_uid || (device as any).trustmUid;
    if (trustMUid) {
      console.log('[CSR Detection] Device has Trust M UID - NOT a CSR device:', trustMUid);
      return false;
    }

    // Log for debugging - check both snake_case and camelCase
    console.log('[CSR Detection] Checking device:', device.name || device.device_id || device.serialNumber);
    console.log('[CSR Detection] metadata:', device.metadata);
    console.log('[CSR Detection] metadata.certificate_generation_method:', device.metadata?.certificate_generation_method);
    console.log('[CSR Detection] certificate_generation_method:', (device as any).certificate_generation_method || (device as any).certificateGenerationMethod);
    console.log('[CSR Detection] generation_method:', (device as any).generation_method || (device as any).generationMethod);
    console.log('[CSR Detection] csr_provided:', (device as any).csr_provided ?? (device as any).csrProvided);
    console.log('[CSR Detection] auth_mode:', device.auth_mode);
    console.log('[CSR Detection] device_name:', device.device_name);
    console.log('[CSR Detection] name:', device.name);

    // Check ONLY actual data fields, NEVER check device name
    // Device names are user-controlled and unreliable for detection
    // Support both snake_case (from API) and camelCase (from UI)
    const generationMethod = (device as any).generation_method || (device as any).generationMethod;
    const certGenMethod = (device as any).certificate_generation_method || (device as any).certificateGenerationMethod;
    const csrProvided = (device as any).csr_provided ?? (device as any).csrProvided;

    const isCsr = !!(
      generationMethod === 'upload_csr' ||
      generationMethod === 'upload-csr' ||
      certGenMethod === 'upload-csr' ||
      certGenMethod === 'upload_csr' ||
      device.metadata?.certificate_generation_method === 'upload-csr' ||
      device.metadata?.certificate_generation_method === 'upload_csr' ||
      csrProvided === true ||
      device.certificate_type === 'user_csr' ||
      device.certificate_type === 'USER_CSR' ||
      // Check certificate metadata if available
      (certificateInfo && certificateInfo.metadata?.generation_type === 'csr') ||
      (certificateInfo && certificateInfo.metadata?.csr_provided === true)
    );
    
    console.log('[CSR Detection] Is CSR device:', isCsr);
    return isCsr;
  };

  // Map CertificateType to backend algorithm slug
  const typeToAlg = (t: CertificateType): string => {
    switch (t) {
      case CertificateType.ECC_P256: return 'ecc-p256';
      case CertificateType.ECC_P384: return 'ecc-p384';
      case CertificateType.RSA_2048: return 'rsa-2048';
      case CertificateType.RSA_3072: return 'rsa-3072';
      case CertificateType.RSA_4096: return 'rsa-4096';
      default: return 'ecc-p256';
    }
  };

  const handleRenewAutoGenerate = async () => {
    if (!device) return;
    setIsGenerating(true);
    try {
      const deviceIdentifier = device.device_id || device.serialNumber || device._id || device.id;
      const desiredAlgo = typeToAlg(renewForm.certificateType || CertificateType.ECC_P256);
      const response = await authFetch(`/api/v1/certificates/devices/${deviceIdentifier}/certificate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ algorithm: desiredAlgo })
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ error: `HTTP ${response.status}` }));
        throw new Error(err.error || `HTTP ${response.status}`);
      }
      toast.success('New certificate generated successfully');
      await checkExistingCertificate();
      onSuccess?.();
    } catch (e: any) {
      toast.error(e?.message || 'Failed to renew certificate');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRenewSignCsr = async () => {
    if (!device) return;
    if (!renewForm.csrContent || !renewForm.csrContent.includes('BEGIN CERTIFICATE REQUEST')) {
      toast.error('Please provide a valid PEM-encoded CSR');
      return;
    }
    try {
      setIsSigningCSR(true);
      const deviceIdentifier = device.device_id || device.serialNumber || device._id || device.id;
      const payload: any = { csr: renewForm.csrContent, validity_days: renewForm.validityDays || 365 };
      if (renewForm.csrAltNames && typeof renewForm.csrAltNames === 'string') {
        const arr = renewForm.csrAltNames.split(',').map((s: string) => s.trim()).filter(Boolean);
        if (arr.length) payload.altNames = arr;
      }
      if (revokeOldOnRenew) payload.revokeOld = true;
      const res = await authFetch(`/api/v1/certificates/devices/${deviceIdentifier}/certificate/sign-csr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({} as any));
        const msg = body?.message || body?.error || body?.details || `CSR signing failed (HTTP ${res.status})`;
        throw new Error(msg);
      }
      toast.success('CSR signed successfully. Certificate updated.');
      await checkExistingCertificate();
      setRenewForm({ ...renewForm, csrContent: '' });
      onSuccess?.();
    } catch (e: any) {
      toast.error(e?.message || 'Failed to sign CSR');
    } finally {
      setIsSigningCSR(false);
    }
  };

  const handleGenerateCertificate = async () => {
    if (!device) return;
    
    // Safety check: prevent CSR devices from generating certificates
    if (isCSRDevice()) {
      console.error('[Certificate Generation] Blocked: CSR device cannot generate certificates');
      setError('CSR devices use externally generated certificates and cannot generate new ones here.');
      return;
    }
    
    setIsGenerating(true);
    setCertState('generating');
    setError(null);

    try {
      // Use actual device_id for API calls
      const deviceIdentifier = device.device_id || device.serialNumber || device._id || device.id;
      // Send desired algorithm to API to avoid defaults
      const desiredAlgo = normalizeAlgorithm(
        certificateInfo?.certificate?.key_algorithm ||
        certificateInfo?.certificate?.algorithm ||
        device?.certificate_algorithm ||
        device?.metadata?.certificate_algorithm ||
        resolvedAlgorithm
      ) || 'ecc-p256';
      const response = await authFetch(`/api/v1/certificates/devices/${deviceIdentifier}/certificate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ algorithm: desiredAlgo })
      });

      if (response.ok) {
        const result = await response.json();
        // Determine an algorithm label for the toast across legacy/compat responses
        const algNorm = normalizeAlgorithm(result?.certificate?.key_algorithm) ||
                        normalizeAlgorithm(result?.certificate?.algorithm) ||
                        normalizeAlgorithm(device?.certificate_algorithm) ||
                        resolvedAlgorithm;
        const algLabel = algorithmDisplayMap[algNorm]?.type ||
                         result?.certificate?.key_algorithm ||
                         result?.certificate?.algorithm ||
                         'device';

        // Only set certificate info directly when complete fields are present
        const hasAllFields = Boolean(result?.certificate?.serial_number &&
                                     result?.certificate?.issued_at &&
                                     result?.certificate?.expires_at);
        if (hasAllFields) {
          setCertificateInfo(result);
          setHasExistingCert(true);
        } else {
          // Refresh from server to fetch normalized cert info
          await checkExistingCertificate();
        }

        toast.success(`New ${algLabel} certificate created successfully`);
        onSuccess?.();
      } else {
        const errorData = await response.json();
        if (response.status === 503) {
          throw new Error('Vault PKI service is not available. Please ensure Vault is running and properly configured.');
        } else if (response.status === 500 && errorData.details) {
          throw new Error(`Certificate generation failed: ${errorData.details}`);
        } else {
          throw new Error(errorData.error || 'Failed to generate certificate');
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to generate certificate');
      
      // Show more informative error messages
      if (err.message.includes('Vault PKI')) {
        toast.error(
          'Certificate Service Unavailable',
          {
            description: 'Vault PKI is required for certificate generation. Contact your administrator.',
            duration: 5000
          }
        );
      } else {
        toast.error(err.message || 'Unable to generate certificate');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async (type: string) => {
    const deviceId = device.device_id || device._id || device.id;
    
    // Debug log
    console.log('[handleDownload] Attempting download:', {
      type,
      deviceId,
      deviceName: device?.name,
      hasCertInfo: !!certificateInfo,
      hasCertificate: !!certificateInfo?.certificate,
      serialNumber: certificateInfo?.certificate?.serial_number,
      generationMethod: device?.generation_method,
      csrProvided: device?.csr_provided
    });
    
    // Allow CA chain downloads even without device certificate (needed for server-TLS devices)
    if (type !== 'ca-chain' && (!certificateInfo || 
        !certificateInfo.certificate || 
        !certificateInfo.certificate.serial_number ||
        !certificateInfo.certificate.expires_at)) {
      console.error('[handleDownload] BLOCKED - No valid certificate:', {
        hasInfo: !!certificateInfo,
        hasCert: !!certificateInfo?.certificate,
        hasSerial: !!certificateInfo?.certificate?.serial_number,
        hasExpiry: !!certificateInfo?.certificate?.expires_at,
        downloadType: type
      });
      toast.error('Certificate not available. This device may use a user-provided CSR without a signed certificate yet.');
      return;
    }
    
    // Sync tokens before download to ensure we have the latest
    AuthTokenManager.syncToken();
    
    // Check if device has public key registered
    const hasPublicKey = device.key_encryption_enabled && device.device_public_key;
    
    // For private key downloads, require public key
    if (type === 'device-key' && !hasPublicKey) {
      setShowPublicKeyDialog(true);
      return;
    }
    
    // Set download progress
    setDownloadProgress(prev => ({ ...prev, [type]: 0 }));
    
    try {
      // Build URL; apply auto-encryption only when policy enables one-time delivery
      let downloadUrl = `/api/v1/certificates/devices/${deviceId}/certificate/download/${type}`;
      // For private key downloads: if policy requires one-time encrypted delivery and device has public key, auto-encrypt
      if (type === 'device-key' && hasPublicKey && (policy?.one_time_encrypted_key_delivery === true)) {
        downloadUrl += '?auto_encrypt=true';
      }
      
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setDownloadProgress(prev => ({
          ...prev,
          [type]: Math.min((prev[type] || 0) + 20, 90)
        }));
      }, 200);
      
      const response = await authFetch(downloadUrl);

      if (!response.ok) {
        clearInterval(progressInterval);
        setDownloadProgress(prev => ({ ...prev, [type]: 0 }));
        
        if (response.status === 503) {
          throw new Error('Vault PKI service unavailable');
        } else if (response.status === 500) {
          const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
          throw new Error(errorData.error || 'Certificate generation failed');
        } else {
          throw new Error(`Download failed (${response.status})`);
        }
      }

      const blob = await response.blob();
      clearInterval(progressInterval);
      setDownloadProgress(prev => ({ ...prev, [type]: 100 }));
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Prefer server-provided filename via Content-Disposition header
      const cdHeader = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
      const extractFilename = (cd?: string | null): string | null => {
        if (!cd) return null;
        try {
          // RFC 6266 / 5987 handling: filename* (utf-8) has priority
          const fnStarMatch = cd.match(/filename\*=UTF-8''([^;\n]+)/i);
          if (fnStarMatch && fnStarMatch[1]) {
            return decodeURIComponent(fnStarMatch[1]);
          }
          const fnMatch = cd.match(/filename="?([^";\n]+)"?/i);
          if (fnMatch && fnMatch[1]) return fnMatch[1];
        } catch (_) {
          // fall through to null
        }
        return null;
      };

      // Fallback filename policy mapping per platform rules
      const makeFallbackName = (): string => {
        // timestamp format: YYYY-MM-DDTHH-MM-SS (no milliseconds)
        const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        const deviceHasPublicKey = device.key_encryption_enabled && device.device_public_key;

        // Map UI types to canonical bundle/file names
        let baseName = '';
        let ext = 'pem';

        if (type === 'bundle') {
          // Canonical fallback for MQTTs + mTLS bundle
          baseName = `${deviceId}-mqtts-mtls-bundle-${timestamp}`;
          ext = 'zip';
        } else if (type === 'https-mtls-bundle') {
          baseName = `${deviceId}-https-mtls-bundle-${timestamp}`;
          ext = 'zip';
        } else if (type === 'mqtt-quic-bundle') {
          baseName = `${deviceId}-mqtt-quic-mtls-bundle-${timestamp}`;
          ext = 'zip';
        } else if (type === 'device-cert') {
          baseName = `${deviceId}-device-cert-${timestamp}`;
          ext = 'pem';
        } else if (type === 'device-key') {
          baseName = `${deviceId}-device-key${deviceHasPublicKey ? '-encrypted' : ''}-${timestamp}`;
          ext = deviceHasPublicKey ? 'json' : 'pem';
        } else if (type === 'ca-chain') {
          baseName = `${deviceId}-ca-chain-${timestamp}`;
          ext = 'pem';
        } else {
          // Safe generic fallback
          baseName = `${deviceId}-${type}-${timestamp}`;
          ext = (type.includes('bundle') ? 'zip' : 'pem');
        }
        return `${baseName}.${ext}`;
      };

      const serverFilename = extractFilename(cdHeader);
      const finalFilename = serverFilename || makeFallbackName();

      // Evidence logging for session notes: record header + chosen filename
      if (cdHeader) {
        console.log('[download] Content-Disposition header detected:', cdHeader);
      } else {
        console.warn('[download] No Content-Disposition header; using fallback filename policy');
      }
      console.log('[download] Using filename:', finalFilename);

      a.download = finalFilename;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Show success with file size and key inclusion/omission info
      const fileSize = (blob.size / 1024).toFixed(2);
      const isEncrypted = type === 'device-key' && deviceHasPublicKey;
      const keyIncluded = type === 'device-key' || (['bundle','https-mtls-bundle','mqtt-quic-bundle'].includes(type) && willIncludePrivateKey());
      const policyNote = ['bundle','https-mtls-bundle','mqtt-quic-bundle'].includes(type)
        ? (keyIncluded ? 'Private key included per policy.' : 'Private key omitted per policy/CSR.')
        : (isEncrypted ? 'Private key delivered encrypted.' : '');

      toast.success(`${type} downloaded successfully`, {
        description: `File size: ${fileSize} KB${isEncrypted ? ' (Encrypted with device public key)' : ''}${policyNote ? ' — ' + policyNote : ''}`,
        duration: 3500
      });
      
      // Reset progress after delay
      setTimeout(() => {
        setDownloadProgress(prev => ({ ...prev, [type]: 0 }));
      }, 1000);
      
    } catch (err: any) {
      setDownloadProgress(prev => ({ ...prev, [type]: 0 }));
      
      if (err.message.includes('Vault PKI')) {
        toast.error(
          'Certificate Download Failed',
          {
            description: 'Vault PKI service is required for certificate operations. Contact your administrator.',
            duration: 5000
          }
        );
      } else {
        toast.error(`Unable to download ${type}: ${err.message}`);
      }
    }
  };

  // Determine if bundles will include private key based on policy and device state
  const willIncludePrivateKey = (): boolean => {
    const retain = !!(policy?.allow_server_side_key_gen && policy?.retain_private_key_at_rest);
    if (isCSRDevice()) return false; // CSR path never stores private key on platform
    return retain;
  };

  const handlePublicKeyDownload = async (format: 'pem' | 'der' | 'json') => {
    const deviceId = device.device_id || device._id || device.id;
    
    // Set download progress
    setDownloadProgress(prev => ({ ...prev, 'public-key': 0 }));
    
    try {
      // Build URL with format parameter
      const downloadUrl = `/api/v1/devices/${deviceId}/public-key?format=${format}`;
      
      // Simulate progress for better UX
      const progressInterval = setInterval(() => {
        setDownloadProgress(prev => ({
          ...prev,
          'public-key': Math.min((prev['public-key'] || 0) + 20, 90)
        }));
      }, 200);
      
      const response = await authFetch(downloadUrl);

      if (!response.ok) {
        clearInterval(progressInterval);
        setDownloadProgress(prev => ({ ...prev, 'public-key': 0 }));
        
        if (response.status === 404) {
          throw new Error('No public key registered for this device');
        } else {
          throw new Error(`Download failed (${response.status})`);
        }
      }

      clearInterval(progressInterval);
      setDownloadProgress(prev => ({ ...prev, 'public-key': 100 }));
      
      if (format === 'json') {
        // For JSON format, parse and display the response
        const data = await response.json();
        
        // Create a blob from the JSON data
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        a.download = `${deviceId}-public-key-${timestamp}.json`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Show success with metadata
        toast.success(
          'Public key downloaded successfully',
          {
            description: `Format: JSON${data.algorithm ? ` | Algorithm: ${data.algorithm}` : ''}`,
            duration: 3000
          }
        );
      } else {
        // For PEM/DER formats, download as blob
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        const timestamp = new Date().toISOString().replace(/:/g, '-').split('.')[0];
        a.download = `${deviceId}-public-key-${timestamp}.${format}`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Show success with file size
        const fileSize = (blob.size / 1024).toFixed(2);
        toast.success(
          'Public key downloaded successfully',
          {
            description: `Format: ${format.toUpperCase()} | Size: ${fileSize} KB`,
            duration: 3000
          }
        );
      }
      
      // Reset progress after delay
      setTimeout(() => {
        setDownloadProgress(prev => ({ ...prev, 'public-key': 0 }));
      }, 1000);
      
    } catch (err: any) {
      setDownloadProgress(prev => ({ ...prev, 'public-key': 0 }));
      toast.error(`Unable to download public key: ${err.message}`);
    }
  };

  // Copy certificate details to clipboard
  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopySuccess(prev => ({ ...prev, [field]: true }));
      toast.success('Copied to clipboard');
      
      // Reset after 2 seconds
      setTimeout(() => {
        setCopySuccess(prev => ({ ...prev, [field]: false }));
      }, 2000);
    } catch (err) {
      toast.error('Failed to copy to clipboard');
    }
  };

  // Handle case where dialog is opened without a device
  if (!device) {
    return (
      <Dialog open={dialogOpenFlag} onOpenChange={onClose}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>No Device Selected</DialogTitle>
          </DialogHeader>
          <div className="py-8 text-center text-muted-foreground">
            Please select a device to manage certificates.
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={dialogOpenFlag} onOpenChange={onClose}>
      {/**
       * Layering fix: ensure this dialog floats above any parent device dialog/modal.
       * Set content z to 210 (higher than other dialogs e.g., z-[200]).
       */}
      <DialogContent className="z-[210] max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            {device?.auth_mode === 'server_tls' ? 'CA Certificate' : 'Enterprise Certificate Management'}
          </DialogTitle>
          <DialogDescription className="flex items-center justify-between">
            <span>
              {device?.auth_mode === 'server_tls' 
                ? `Download CA certificate for ${device?.name || device?.device_id}` 
                : `Advanced certificate lifecycle management for ${device?.name || device?.device_id}`}
            </span>
            <span className="text-xs text-muted-foreground">
              Powered by HashiCorp Vault PKI
            </span>
          </DialogDescription>
        </DialogHeader>

        {device?.auth_mode !== 'server_tls' && (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="technical">Technical Details</TabsTrigger>
              <TabsTrigger value="lifecycle">Lifecycle</TabsTrigger>
              <TabsTrigger value="security">Security</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6 mt-6">
            {/* Automatic Encryption Status */}
            <Alert className="border-green-200 bg-green-50 dark:bg-green-950/20">
              <Shield className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-900 dark:text-green-100">Secure Certificate Management</AlertTitle>
              <AlertDescription className="text-green-700 dark:text-green-300">
                All certificates are issued by the enterprise Certificate Authority powered by <strong>HashiCorp Vault PKI</strong>. 
                Security keys are automatically generated and protected based on your device type.
                {error && error.includes('Vault PKI') && (
                  <span className="block mt-2 font-semibold text-amber-600">
                    ⚠️ Vault PKI service is currently unavailable. Please contact your system administrator.
                  </span>
                )}
              </AlertDescription>
            </Alert>

            {isTrustMDevice && (
              <Card className="border-indigo-200 dark:border-indigo-700/50 bg-indigo-50/40 dark:bg-indigo-950/40">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Shield className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                    OPTIGA™ Trust M MQTTs + HTTPS Bundle
                  </CardTitle>
                  <CardDescription>
                    Complete bundle for OPTIGA™ Trust M devices. Contains everything needed for secure MQTTs and HTTPS connections.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    This bundle includes the TESAIoT CA chain, Infineon trust anchor, device certificate, and a preconfigured <code>mqtt_client_config.h</code>
                    ready for use with Trust M secure element. The private key remains securely stored in the Trust M chip (OID 0xE0F1).
                  </p>
                  <Button
                    variant="primary"
                    onClick={handleDownloadTrustMStarterBundle}
                    disabled={isDownloadingTrustMBundle}
                    className="w-full md:w-auto"
                  >
                    {isDownloadingTrustMBundle ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Preparing download...
                      </>
                    ) : (
                      <>
                        <Download className="h-4 w-4 mr-2" />
                        Download MQTTs + HTTPS for Trust M
                      </>
                    )}
                  </Button>
                  <Alert className="border-indigo-200 dark:border-indigo-700/50 bg-indigo-50/50 dark:bg-indigo-950/30">
                    <AlertDescription className="text-xs text-indigo-700 dark:text-indigo-300 space-y-1">
                      <p>OPTIGA™ Trust M OID quick guide:</p>
                      <ul className="list-disc list-inside">
                        <li><code>0xE0C2</code> – Factory UID (read-only)</li>
                        <li><code>0xE0E8</code> – Infineon trust anchor</li>
                        <li><code>0xE0E9</code> – Factory certificate (optional)</li>
                        <li><code>0xE0F1</code> – CSR/key slot for TESAIoT Protected Update rotation</li>
                      </ul>
                    </AlertDescription>
                  </Alert>
                </CardContent>
              </Card>
            )}

            {/* Enhanced Key Type Information Card */}
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <displayedKeyInfo.icon className={`h-5 w-5 ${displayedKeyInfo.color}`} />
                    {headerTitle}
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p className="font-semibold mb-2">Algorithm Source</p>
                          <p className="text-sm">
                            {csrMode
                              ? (csrAlgorithmKnown
                                  ? 'This reflects the algorithm from your signed CSR.'
                                  : 'Defined by your uploaded CSR. Shown precisely after signing.')
                              : (explicitAlgorithmSource
                                  ? (explicitAlgorithmSource === 'certificate'
                                      ? 'This reflects the active certificate algorithm.'
                                      : 'This comes from the device settings.')
                                  : 'The platform auto-selects an optimal algorithm by device type.')}
                          </p>
                          <ul className="text-sm mt-2 space-y-1">
                            {csrMode && !csrAlgorithmKnown ? (
                              <>
                                <li>• <strong>CSR-defined</strong>: Your device controls key type/size</li>
                                <li>• <strong>Typical</strong>: ECC P-256 for IoT (low power)</li>
                              </>
                            ) : (
                              <>
                                <li>• <strong>ECC</strong>: Best for IoT sensors (low power, small keys)</li>
                                <li>• <strong>RSA 3072</strong>: Optimal for gateways (balanced security/performance)</li>
                              </>
                            )}
                          </ul>
                          <p className="text-sm mt-2">
                            All algorithms meet NIST security standards through 2030 and beyond.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </CardTitle>
                  <Badge className={badgeBgClass}>
                    {badgeText}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-semibold text-lg flex items-center gap-2">
                      {displayedKeyInfo.type}
                      <Fingerprint className="h-4 w-4 text-muted-foreground" />
                      {resolvedAlgorithm === 'rsa-3072' && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge variant="outline" className="text-xs cursor-help">
                                <Info className="h-3 w-3 mr-1" />
                                Why not RSA 4096?
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-sm">
                              <p className="font-semibold mb-2">RSA 3072 vs RSA 4096</p>
                              <div className="text-sm space-y-2">
                                <p><strong>RSA 3072 Benefits:</strong></p>
                                <ul className="ml-4 space-y-1">
                                  <li>• 2x faster than RSA 4096</li>
                                  <li>• Hardware acceleration support</li>
                                  <li>• NIST approved beyond 2030</li>
                                  <li>• 128-bit security strength</li>
                                </ul>
                                <p className="mt-2"><strong>RSA 4096 Drawbacks:</strong></p>
                                <ul className="ml-4 space-y-1">
                                  <li>• Doubles processing time</li>
                                  <li>• Limited hardware support</li>
                                  <li>• Minimal security gain</li>
                                  <li>• Higher energy consumption</li>
                                </ul>
                                <p className="mt-2 text-muted-foreground">
                                  For IoT gateways, RSA 3072 provides optimal balance.
                                </p>
                              </div>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      {displayedKeyInfo.description}
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div className="space-y-2">
                      <h5 className="text-sm font-medium">Key Benefits</h5>
                      {displayedKeyInfo.benefits.map((benefit: string, idx: number) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-3 w-3 text-green-500 flex-shrink-0" />
                          <span>{benefit}</span>
                        </div>
                      ))}
                    </div>
                    
                    <div className="space-y-2">
                      <h5 className="text-sm font-medium">Technical Specifications</h5>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Key Size:</span>
                          <span className="font-mono">{displayedKeyInfo.specs.keySize}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Signature:</span>
                          <span className="font-mono">{displayedKeyInfo.specs.signatureSize}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Processing:</span>
                          <span className="font-mono">{displayedKeyInfo.specs.processingTime}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Power:</span>
                          <span className="font-mono">{displayedKeyInfo.specs.powerUsage}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

            {loading ? (
              <Card>
                <CardContent className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-sm text-muted-foreground">Checking certificate status...</p>
                </CardContent>
              </Card>
            ) : !certificateInfo && device && !isCSRDevice() && (
              <Card>
                <CardContent className="text-center py-8">
                  <div className="relative inline-block mb-4">
                    <Shield className="h-16 w-16 text-muted-foreground" />
                    {certState === 'none' && (
                      <AlertCircle className="h-6 w-6 text-amber-500 absolute -bottom-1 -right-1" />
                    )}
                  </div>
                  <h3 className="text-lg font-semibold mb-2">
                    {certState === 'none' ? 'No Certificate Found' : 
                     certState === 'expired' ? 'Certificate Expired' :
                     certState === 'expiring' ? 'Certificate Expiring Soon' :
                     certState === 'generating' ? 'Finalizing Certificate...' :
                     'Certificate Status'}
                  </h3>
                  <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                    {isCSRDevice()
                      ? 'This device uses a user-provided CSR. The certificate has been signed by TESAIoT CA. You can download the certificate and CA chain.'
                      : certState === 'none' 
                      ? 'This device requires a certificate for secure communication. Generate one to enable encrypted data transmission.'
                      : certState === 'expired'
                      ? 'The certificate has expired and needs to be renewed to maintain secure communication.'
                      : certState === 'expiring'
                      ? 'The certificate will expire soon. Generate a new one to ensure uninterrupted service.'
                      : 'Certificate has been requested and is being finalized. Please wait a few seconds, then refresh to see download options.'}
                  </p>
                  {device && !isCSRDevice() && (
                    <div className="flex gap-3 justify-center">
                      <Button 
                        onClick={handleGenerateCertificate} 
                        disabled={isGenerating || certState === 'generating'}
                        size="lg"
                        className="min-w-[200px]"
                      >
                        {isGenerating || certState === 'generating' ? (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            {certState === 'generating' ? 'Finalizing...' : 'Generating Certificate...'}
                          </>
                        ) : (
                          <>
                            <Key className="h-4 w-4 mr-2" />
                            {certState === 'none' ? 'Generate Certificate' : 'Regenerate Certificate'}
                          </>
                        )}
                      </Button>
                    </div>
                  )}
                  
                  {certMetrics.totalGenerated > 0 && (
                    <div className="mt-6 pt-6 border-t">
                      <div className="grid grid-cols-3 gap-4 text-center">
                        <div>
                          <p className="text-2xl font-semibold">{certMetrics.totalGenerated}</p>
                          <p className="text-xs text-muted-foreground">Total Generated</p>
                        </div>
                        <div>
                          <p className="text-2xl font-semibold">{certMetrics.renewalCount}</p>
                          <p className="text-xs text-muted-foreground">Renewals</p>
                        </div>
                        <div>
                          <p className="text-2xl font-semibold">
                            {certMetrics.lastGeneratedAt 
                              ? new Date(certMetrics.lastGeneratedAt).toLocaleDateString()
                              : 'N/A'}
                          </p>
                          <p className="text-xs text-muted-foreground">Last Generated</p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Special case for CSR devices without certificate yet */}
            {!certificateInfo && device && isCSRDevice() && (
              <Card>
                <CardContent className="text-center py-8">
                  {device.trustm_uid ? (
                    // Trust M Device - No platform certificate needed
                    <>
                      <div className="relative inline-block mb-4">
                        <ShieldCheck className="h-16 w-16 text-green-600" />
                      </div>
                      <h3 className="text-lg font-semibold mb-2">
                        OPTIGA™ Trust M Device
                      </h3>
                      <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                        This device uses the factory certificate stored in the Infineon OPTIGA™ Trust M secure element.
                        No platform certificate is required. The device will auto-activate on first connection with the factory certificate.
                      </p>
                      <Alert className="max-w-md mx-auto border-blue-200 bg-blue-50/50">
                        <Info className="h-4 w-4 text-blue-600" />
                        <AlertDescription className="text-blue-900">
                          <strong>Trust M UID:</strong>
                          <br />
                          <code className="text-xs font-mono break-all">{device.trustm_uid}</code>
                        </AlertDescription>
                      </Alert>
                    </>
                  ) : (
                    // CSR Device - Certificate is being processed
                    <>
                      <div className="relative inline-block mb-4">
                        <FileKey2 className="h-16 w-16 text-purple-600" />
                      </div>
                      <h3 className="text-lg font-semibold mb-2">
                        CSR-Based Device
                      </h3>
                      <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto">
                        This device was created with a user-provided CSR. The certificate has been signed by the TESAIoT CA.
                        Since you generated the private key externally, only the certificate and CA chain are available for download.
                      </p>
                      <Alert className="max-w-md mx-auto">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          Certificate is being processed. Please wait a moment and refresh to check the status.
                        </AlertDescription>
                      </Alert>
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Download section - ONLY show if certificate has ALL required fields */}
            {certificateInfo && 
             certificateInfo.certificate && 
             certificateInfo.certificate.serial_number && 
             certificateInfo.certificate.expires_at &&
             certificateInfo.certificate.issued_at && 
             (() => {
               console.log('[Download Section Check]', {
                 deviceName: device?.name,
                 hasInfo: !!certificateInfo,
                 hasCert: !!certificateInfo?.certificate,
                 serialNumber: certificateInfo?.certificate?.serial_number,
                 expiresAt: certificateInfo?.certificate?.expires_at,
                 issuedAt: certificateInfo?.certificate?.issued_at,
                 generationMethod: device?.generation_method,
                 csrProvided: device?.csr_provided
               });
               return true;
             })() && (
              <>
                <Card className="border-green-200 bg-green-50/50 dark:bg-green-900/20">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg flex items-center gap-2 text-green-900 dark:text-green-100">
                      <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                      Certificate Active
                      {/* Certificate Type Indicator */}
                      {isCSRDevice() && (
                        <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          <FileKey className="h-3 w-3 mr-1" />
                          User CSR
                        </Badge>
                      )}
                      <Badge variant="outline" className="ml-auto bg-green-100 text-green-800">
                        {certificateInfo.certificate.key_algorithm || keyInfo.type}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Serial Number</p>
                          <div className="flex items-center gap-2 mt-1">
                            <code className="text-sm font-mono bg-muted px-2 py-1 rounded flex-1 truncate">
                              {certificateInfo.certificate.serial_number}
                            </code>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7 w-7 p-0"
                              onClick={() => copyToClipboard(certificateInfo.certificate.serial_number, 'serial')}
                            >
                              {copySuccess['serial'] ? (
                                <CheckCircle className="h-3 w-3 text-green-500" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                          </div>
                        </div>
                        
                        <div>
                          <p className="text-xs text-muted-foreground">Issued Date</p>
                          <p className="text-sm font-medium flex items-center gap-2 mt-1">
                            <Clock className="h-3 w-3" />
                            {new Date(certificateInfo.certificate.issued_at || Date.now()).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                      
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-muted-foreground">Expiration Date</p>
                          <p className="text-sm font-medium flex items-center gap-2 mt-1">
                            <Clock className="h-3 w-3" />
                            {new Date(certificateInfo.certificate.expires_at).toLocaleDateString()}
                          </p>
                        </div>
                        
                        <div>
                          <p className="text-xs text-muted-foreground">Days Until Expiry</p>
                          <p className="text-sm font-medium">
                            {(() => {
                              const days = Math.floor((new Date(certificateInfo.certificate.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
                              return (
                                <span className={days < 30 ? 'text-amber-600' : 'text-green-600'}>
                                  {days} days
                                </span>
                              );
                            })()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Download className="h-4 w-4" />
                      Download Certificate Files
                    </CardTitle>
                    <CardDescription className="flex items-center justify-between">
                      <span>Download individual components or the complete bundle</span>
                      {device.key_encryption_enabled && device.device_public_key && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200 cursor-help">
                                <KeyRound className="h-3 w-3 mr-1" />
                                Public Key Registered
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p className="font-semibold mb-1">Device Public Key Registered</p>
                              <p className="text-sm">
                                {isCSRDevice()
                                  ? (
                                      <>This device has a registered public key. If you later generate certificates server-side, any private key downloads will be encrypted with this key. For CSR-based certificates, bundles do not include a private key.</>
                                    )
                                  : (
                                      <>Encrypted downloads are enabled. Private keys and eligible bundles will be encrypted with this public key before download to ensure secure delivery.</>
                                    )}
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Button
                      variant="outline"
                      className="w-full justify-between group"
                      onClick={() => handleDownload('ca-chain')}
                      disabled={downloadProgress['ca-chain'] > 0}
                    >
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        <span>CA Certificate Chain</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {downloadProgress['ca-chain'] > 0 && (
                          <Progress value={downloadProgress['ca-chain']} className="w-20 h-2" />
                        )}
                        <span className="text-xs text-muted-foreground group-hover:text-foreground">.pem</span>
                      </div>
                    </Button>

                    <Button
                      variant="outline"
                      className="w-full justify-between group"
                      onClick={() => handleDownload('device-cert')}
                      disabled={downloadProgress['device-cert'] > 0}
                    >
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        <span>Device Certificate</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {downloadProgress['device-cert'] > 0 && (
                          <Progress value={downloadProgress['device-cert']} className="w-20 h-2" />
                        )}
                        <span className="text-xs text-muted-foreground group-hover:text-foreground">.pem</span>
                      </div>
                    </Button>

                    {/* Show informative message for CSR devices */}
                    {isCSRDevice() && (
                      <Alert className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
                        <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        <AlertDescription className="text-blue-800 dark:text-blue-200 text-sm">
                          <strong>CSR Certificate:</strong> Private key remains secure on your device.
                          The platform never has access to your private key per NIST SP 800-57 security standards.
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Only show private key download for Vault PKI certificates, not for user CSR */}
                    {!isCSRDevice() && (policy?.allow_server_side_key_gen && policy?.retain_private_key_at_rest) && (
                      <Button
                        variant="outline"
                        className="w-full justify-between group"
                        onClick={() => handleDownload('device-key')}
                        disabled={downloadProgress['device-key'] > 0}
                      >
                        <div className="flex items-center gap-2">
                          <Key className="h-4 w-4" />
                          <span>Private Key</span>
                        {device.key_encryption_enabled && device.device_public_key ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge className="text-xs bg-green-100 text-green-800 border-green-200 cursor-help">
                                  <Lock className="h-3 w-3 mr-1" />
                                  Encrypted Download
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="font-semibold mb-1">Encrypted Download Format</p>
                                <p className="text-sm">
                                  The private key will be automatically encrypted with the device's 
                                  public key before download. This ensures only your device can decrypt 
                                  and use the private key.
                                </p>
                                <p className="text-sm mt-2">
                                  <strong>Format:</strong> JSON file containing encrypted key data
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Badge className="text-xs bg-amber-100 text-amber-800 border-amber-200 cursor-help">
                                  <Unlock className="h-3 w-3 mr-1" />
                                  Standard PEM Format
                                </Badge>
                              </TooltipTrigger>
                              <TooltipContent className="max-w-xs">
                                <p className="font-semibold mb-1">Standard PEM Format</p>
                                <p className="text-sm">
                                  The private key will be downloaded in standard PEM format without 
                                  additional encryption. Use secure channels to transfer this file 
                                  to your device.
                                </p>
                                <p className="text-sm mt-2 text-amber-600">
                                  <strong>Note:</strong> Consider registering a public key to enable 
                                  encrypted downloads for enhanced security.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {downloadProgress['device-key'] > 0 && (
                          <Progress value={downloadProgress['device-key']} className="w-20 h-2" />
                        )}
                        <span className="text-xs text-muted-foreground group-hover:text-foreground">
                          {device.key_encryption_enabled && device.device_public_key ? '.json' : '.pem'}
                        </span>
                      </div>
                    </Button>
                    )}

                    {/* Only show public key download for Vault PKI certificates */}
                    {device && !isCSRDevice() && (
                      <Button
                        variant="outline"
                        className="w-full justify-between group"
                        onClick={() => handlePublicKeyDownload(publicKeyFormat)}
                        disabled={downloadProgress['public-key'] > 0}
                      >
                        <div className="flex items-center gap-2">
                          <KeyRound className="h-4 w-4" />
                          <span>Device Public Key</span>
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p className="font-semibold mb-2">What is a Public Key?</p>
                              <p className="text-sm mb-2">
                                The public key is used to encrypt data that only the device can decrypt. 
                                It's safe to share publicly.
                              </p>
                              <p className="text-sm font-semibold mb-1">Common uses:</p>
                              <ul className="text-sm space-y-1">
                                <li>• Encrypt configuration files</li>
                                <li>• Secure firmware updates</li>
                                <li>• Verify device signatures</li>
                                <li>• Establish secure channels</li>
                              </ul>
                              <Separator className="my-2" />
                              <p className="text-sm font-semibold mb-1">Format Options:</p>
                              <ul className="text-sm space-y-1">
                                <li>• <strong>PEM:</strong> Base64 encoded, human-readable</li>
                                <li>• <strong>DER:</strong> Binary format, compact</li>
                                <li>• <strong>JSON:</strong> Includes metadata and history</li>
                              </ul>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      </div>
                      <div className="flex items-center gap-2">
                        {downloadProgress['public-key'] > 0 && (
                          <Progress value={downloadProgress['public-key']} className="w-20 h-2" />
                        )}
                        <select
                          className="text-xs border rounded px-2 py-1 bg-background"
                          value={publicKeyFormat}
                          onChange={(e) => setPublicKeyFormat(e.target.value as 'pem' | 'der' | 'json')}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="pem">PEM</option>
                          <option value="der">DER</option>
                          <option value="json">JSON</option>
                        </select>
                      </div>
                    </Button>
                    )}

                    {/* Bundle downloads - hidden for Trust M devices (private key is in chip) */}
                    {!isTrustMDevice && (
                      <>
                        <Separator />

                        <Button
                          className="w-full"
                          size="lg"
                          onClick={() => handleDownload('bundle')}
                          disabled={downloadProgress['bundle'] > 0}
                        >
                          {downloadProgress['bundle'] > 0 ? (
                            <>
                              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                              Downloading... {downloadProgress['bundle']}%
                            </>
                          ) : (
                            <>
                              <Package className="h-4 w-4 mr-2" />
                              Download MQTTs + mTLS Bundle
                              <span className="ml-2 text-xs opacity-70">
                                .zip
                              </span>
                            </>
                          )}
                        </Button>

                        {/* HTTPS + mTLS Bundle: includes HTTPS server CA (if available) + device cert/key per policy */}
                        <Button
                          className="w-full mt-2"
                          onClick={() => handleDownload('https-mtls-bundle')}
                          disabled={downloadProgress['https-mtls-bundle'] > 0}
                        >
                          {downloadProgress['https-mtls-bundle'] > 0 ? (
                            <>
                              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                              Preparing HTTPS + mTLS Bundle... {downloadProgress['https-mtls-bundle']}%
                            </>
                          ) : (
                            <>
                              <Package className="h-4 w-4 mr-2" />
                              Download HTTPS + mTLS Bundle
                              <span className="ml-2 text-xs opacity-70">.zip</span>
                            </>
                          )}
                        </Button>
                        {featureFlags.MQTT_QUIC_BUNDLE && (
                          <Button
                            className="w-full mt-2"
                            variant="outline"
                            onClick={() => handleDownload('mqtt-quic-bundle')}
                            disabled={downloadProgress['mqtt-quic-bundle'] > 0}
                          >
                            {downloadProgress['mqtt-quic-bundle'] > 0 ? (
                              <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                Preparing MQTT QUIC + mTLS Bundle... {downloadProgress['mqtt-quic-bundle']}%
                              </>
                            ) : (
                              <>
                                <Package className="h-4 w-4 mr-2" />
                                MQTT QUIC + mTLS Bundle
                                <span className="ml-2 text-xs opacity-70">.zip</span>
                              </>
                            )}
                          </Button>
                        )}
                      </>
                    )}

                    {/* Trust M device info - explain why bundles are not available */}
                    {isTrustMDevice && (
                      <Alert className="mt-2 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
                        <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                        <AlertDescription className="text-blue-800 dark:text-blue-200 text-sm">
                          <strong>OPTIGA™ Trust M Device:</strong> MQTTs and HTTPS bundles are not available because the private key is securely stored in the Trust M chip (OID 0xE0F1) and never leaves the device. Use the <strong>MQTTs + HTTPS for Trust M</strong> bundle above to configure your device.
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Notice: private key omission with precise messaging */}
                    {!willIncludePrivateKey() && (
                      <Alert className="mt-2 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
                        <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                        <AlertDescription className="text-amber-800 dark:text-amber-200 text-sm">
                          {isTrustMDevice
                            ? (
                                <>Private key is kept at OPTIGA™ Trust M only.</>
                              )
                            : isCSRDevice()
                            ? (
                                <>This certificate was issued from your CSR. The platform never stores your private key, so bundles include only the device certificate and CA chain. There is no private key download for CSR-based certificates.</>
                              )
                            : (
                                <>Private key is not included in bundles due to organization policy. Use the "Private Key" download with encrypted delivery when available.</>
                              )}
                        </AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>

                {/* Hide encryption alerts for Trust M devices - they don't need encrypted downloads */}
                {!isTrustMDevice && (
                  device.key_encryption_enabled && device.device_public_key ? (
                    <Alert className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30">
                      <Shield className="h-4 w-4 text-green-600 dark:text-green-400" />
                      <AlertDescription className="text-green-800 dark:text-green-200 text-sm">
                        {isCSRDevice()
                          ? (
                            <>Public key registered. Any downloads that contain private keys (for server-side generated certificates) would be encrypted with this key. For CSR-based certificates, bundles do not include a private key.</>
                          ) : (
                            <>
                              <strong>Encrypted Download Enabled:</strong> Private keys and eligible bundles will be automatically encrypted using the device's registered public key for secure delivery. You can download the public key above to verify it matches your device's key.
                            </>
                          )}
                      </AlertDescription>
                    </Alert>
                  ) : (
                    <Alert className="border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30">
                      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      <AlertDescription className="text-amber-800 dark:text-amber-200">
                        <strong>Public Key Not Registered:</strong> To enable automatic encryption of private keys,
                        please register the device's public key in the device settings. Once registered, you'll be able
                        to download it here for verification.
                      </AlertDescription>
                    </Alert>
                  )
                )}
              </>
            )}
          </TabsContent>

          <TabsContent value="technical" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Technical Specifications</CardTitle>
                <CardDescription>
                  Detailed cryptographic parameters and compliance information
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm">Algorithm Details</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Algorithm:</span>
                        <span className="font-mono">{keyInfo.type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Key Size:</span>
                        <span className="font-mono">{keyInfo.specs.keySize}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Signature Size:</span>
                        <span className="font-mono">{keyInfo.specs.signatureSize}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Hash Function:</span>
                        <span className="font-mono">SHA-256</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <h4 className="font-semibold text-sm">Performance Metrics</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Sign Time:</span>
                        <span className="font-mono">{keyInfo.specs.processingTime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Verify Time:</span>
                        <span className="font-mono">{keyInfo.specs.processingTime}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Power Usage:</span>
                        <span className="font-mono">{keyInfo.specs.powerUsage}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Memory:</span>
                        <span className="font-mono">&lt; 4KB</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <Separator className="my-6" />
                
                <div className="space-y-4">
                  <h4 className="font-semibold text-sm">Compliance & Standards</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <Badge variant="secondary" className="justify-center">ETSI EN 303 645 V2.1.1</Badge>
                    <Badge variant="secondary" className="justify-center">ISO/IEC 27402:2023</Badge>
                    <Badge variant="secondary" className="justify-center">NIST SP 800-57</Badge>
                    <Badge variant="secondary" className="justify-center">FIPS 140-2 Level 2</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="lifecycle" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Certificate Lifecycle Management</CardTitle>
                <CardDescription>
                  Monitor and manage certificate validity periods
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Certificate Validity Period</span>
                      <span className="font-medium">365 days</span>
                    </div>
                    <Progress value={certificateInfo ? 
                      Math.max(0, Math.min(100, 
                        ((new Date(certificateInfo.certificate.expires_at).getTime() - Date.now()) / 
                         (365 * 24 * 60 * 60 * 1000)) * 100
                      )) : 0
                    } />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <Card>
                      <CardContent className="pt-6">
                        <Lock className="h-8 w-8 mx-auto mb-2 text-green-600" />
                        <p className="text-2xl font-semibold">Active</p>
                        <p className="text-xs text-muted-foreground">Current Status</p>
                      </CardContent>
                    </Card>
                    
                    <Card>
                      <CardContent className="pt-6">
                        <RefreshCw className="h-8 w-8 mx-auto mb-2 text-blue-600" />
                        <p className="text-2xl font-semibold">Auto</p>
                        <p className="text-xs text-muted-foreground">Renewal Mode</p>
                      </CardContent>
                    </Card>
                    
                    <Card>
                      <CardContent className="pt-6">
                        <Activity className="h-8 w-8 mx-auto mb-2 text-purple-600" />
                        <p className="text-2xl font-semibold">100%</p>
                        <p className="text-xs text-muted-foreground">Health Score</p>
                      </CardContent>
                    </Card>
                  </div>
                  
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Certificates will automatically renew 30 days before expiration. 
                      Manual renewal is available at any time through this interface.
                    </AlertDescription>
                  </Alert>
                </div>
              </CardContent>
            </Card>

            {/* Unified Renewal Section: Auto-generate or Upload CSR (reuse Create Device UI) */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileKey className="h-4 w-4" />
                  Renew Certificate
                </CardTitle>
                <CardDescription>
                  Choose Auto-generate or Upload CSR. You can change the method from the original choice.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <CertificateOptionsTab
                  formData={renewForm}
                  onFormDataChange={(d) => setRenewForm(d as CertificateFormData)}
                  onCSRValidationChange={(isValid, hasValidated) => {
                    setRenewValidation({
                      status: hasValidated ? (isValid ? 'valid' : 'invalid') as any : 'pending',
                      isValid,
                      hasValidated
                    } as any);
                  }}
                  disabled={isGenerating || isSigningCSR}
                />

                <div className="flex items-center justify-between pt-2">
                  <div className="text-sm text-muted-foreground">
                    {renewForm.certificateGenerationMethod === CertificateGenerationMethod.AUTO_GENERATE
                      ? 'Platform will generate keys and certificate for this device.'
                      : 'Upload and sign your CSR. Private key stays on device.'}
                  </div>
                </div>

                {/* Optional: revoke previous certificate after renewal (CSR path supports flag) */}
                <div className="flex items-center gap-2">
                  <Switch id="revoke-old" checked={revokeOldOnRenew} onCheckedChange={setRevokeOldOnRenew} />
                  <Label htmlFor="revoke-old">Revoke previous certificate after renewal</Label>
                </div>

                <div className="flex items-center gap-2">
                  {renewForm.certificateGenerationMethod === CertificateGenerationMethod.AUTO_GENERATE ? (
                    <Button disabled={isGenerating} onClick={handleRenewAutoGenerate}>
                      {isGenerating ? 'Generating…' : 'Generate New Certificate'}
                    </Button>
                  ) : (
                    <Button
                      disabled={isSigningCSR || !renewForm.csrContent || !renewForm.csrContent.includes('BEGIN CERTIFICATE REQUEST')}
                      onClick={handleRenewSignCsr}
                    >
                      {isSigningCSR ? 'Signing…' : 'Upload & Sign CSR'}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security" className="space-y-6 mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Security Information</CardTitle>
                <CardDescription>
                  Certificate security features and best practices
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      Security Features
                    </h4>
                    <div className="space-y-2">
                      {[
                        'Hardware Security Module (HSM) protected',
                        'Perfect Forward Secrecy (PFS)',
                        'Certificate Transparency (CT) logging',
                        'OCSP stapling support',
                        'Post-quantum ready infrastructure'
                      ].map((feature, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <CheckCircle className="h-3 w-3 text-green-500" />
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <h4 className="font-semibold text-sm flex items-center gap-2">
                      <Lock className="h-4 w-4" />
                      Best Practices
                    </h4>
                    <div className="space-y-2">
                      {[
                        'Store private keys in secure hardware',
                        'Enable certificate pinning',
                        'Monitor certificate expiration',
                        'Use mutual TLS authentication',
                        'Regular security audits'
                      ].map((practice, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          <Info className="h-3 w-3 text-blue-500" />
                          <span>{practice}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                
                <Separator />
                
                <Alert variant="default" className="border-blue-200 bg-blue-50 dark:bg-blue-950/20">
                  <Shield className="h-4 w-4 text-blue-600" />
                  <AlertTitle className="text-blue-900 dark:text-blue-100">
                    Enterprise PKI Infrastructure
                  </AlertTitle>
                  <AlertDescription className="text-blue-700 dark:text-blue-300">
                    This certificate is issued by your enterprise Certificate Authority (CA) managed by HashiCorp Vault.
                    All certificates are logged and audited for compliance with your organization's security policies.
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </TabsContent>
          </Tabs>
        )}
        
        {/* Server-TLS specific UI - Only CA certificate download */}
        {device?.auth_mode === 'server_tls' && (
          <div className="space-y-6 mt-6">
            <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/20">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertTitle className="text-blue-900 dark:text-blue-100">Server-TLS Authentication</AlertTitle>
              <AlertDescription className="text-blue-700 dark:text-blue-300">
                This device uses Server-TLS authentication and only requires the CA certificate to verify the server's identity. 
                The device will authenticate using its MQTT username and password over a TLS-encrypted connection.
              </AlertDescription>
            </Alert>
            
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Download className="h-4 w-4" />
                  Download CA Certificate
                </CardTitle>
                <CardDescription>
                  Download the Certificate Authority (CA) certificate to configure your device
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  variant="outline"
                  className="w-full justify-between group"
                  onClick={() => handleDownload('ca-chain')}
                  disabled={downloadProgress['ca-chain'] > 0}
                >
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    <span>CA Certificate Chain</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {downloadProgress['ca-chain'] > 0 && (
                      <Progress value={downloadProgress['ca-chain']} className="w-20 h-2" />
                    )}
                    <span className="text-xs text-muted-foreground group-hover:text-foreground">.pem</span>
                  </div>
                </Button>
                
                <Alert className="mt-4">
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <strong>Installation Instructions:</strong>
                    <ol className="list-decimal list-inside mt-2 space-y-1 text-sm">
                      <li>Download the CA certificate chain above</li>
                      <li>Copy the certificate to your device</li>
                      <li>Configure your MQTT client to use the CA certificate for server verification</li>
                      <li>Use your device's MQTT username and password for authentication</li>
                    </ol>
                  </AlertDescription>
                </Alert>
              </CardContent>
            </Card>
          </div>
        )}

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
      
      {/* Public Key Registration Dialog */}
      <Dialog open={showPublicKeyDialog} onOpenChange={setShowPublicKeyDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Public Key Required
            </DialogTitle>
            <DialogDescription>
              To download encrypted private keys, you must first register the device's public key.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <Alert className="border-amber-200 bg-amber-50">
              <Info className="h-4 w-4 text-amber-600" />
              <AlertDescription className="text-amber-800">
                Registering a public key enables automatic encryption of sensitive data like private keys, 
                ensuring secure delivery to your device.
              </AlertDescription>
            </Alert>
            
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Benefits of Public Key Registration:</h4>
              <ul className="text-sm text-muted-foreground space-y-1 ml-4">
                <li>• Automatic encryption of private keys</li>
                <li>• Secure key delivery without passwords</li>
                <li>• Protection against interception</li>
                <li>• Compliance with security best practices</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowPublicKeyDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              setShowPublicKeyDialog(false);
              navigate(`/devices/${device.device_id || device._id || device.id}/edit`);
            }}>
              <Key className="h-4 w-4 mr-2" />
              Go to Device Settings
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
};
// NOTE: Removed an accidental useEffect that was placed outside the component.
// The correct tab-reset logic already exists within the component body.
