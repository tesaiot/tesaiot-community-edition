/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Device Credentials Section
 * Provides easy access to device authentication credentials for different patterns
 */

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { toast } from 'sonner';
import { 
  Copy, 
  Download, 
  Loader2,
  Key, 
  Shield, 
  Code, 
  Smartphone,
  Wifi,
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Cpu,
  Globe,
  Lock,
  Timer,
  Eye
} from 'lucide-react';
import { Device } from '@/services/api/tesaApi';
import { CertificateGenerationDialog } from './CertificateGenerationDialog';
import { tesaApi } from '@/services/api/tesaApi';
import { deviceService } from '../services/deviceService';
import { useAuth } from '@/hooks/useAuth';
import authFetch from '@/utils/auth-fetch';

interface DeviceCredentialsProps {
  device: Device & { auth_mode?: 'mtls' | 'server_tls' | 'optiga_trust_mtls' };
  onRegenerateApiKey?: () => Promise<void>;
  // Optional: when opening from three-dot menu for Server‑TLS, jump to CA tab
  defaultInnerTab?: 'credentials' | 'certificates';
}

export const DeviceCredentialsSection: React.FC<DeviceCredentialsProps> = ({ 
  device, 
  onRegenerateApiKey,
  defaultInnerTab
}) => {
  const { user: currentUser } = useAuth();
  const isHighRole = ['org_admin', 'organization_admin', 'admin', 'super_admin'].includes(currentUser?.role || '');

  // Public endpoints for the display/copy snippets are derived from the host
  // the UI is served from (domain-agnostic self-host) instead of hardcoded
  // tesaiot.dev / tesa-iot.com literals. The authoritative values for the
  // downloadable bundles still come from the backend endpoints.json; these are
  // only the human-facing examples shown next to the copy buttons.
  const publicOrigin =
    typeof window !== 'undefined' ? window.location.origin : 'https://localhost';
  const publicHost =
    typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  // REST telemetry endpoint shown in the HTTPs API credentials card.
  const apiTelemetryEndpoint = `${publicOrigin}/api/v1/device/telemetry`;
  // Server-TLS / mTLS-ingest / MQTT-QUIC example endpoints (default public
  // ports; the bundle endpoints.json carries the install's real values).
  const httpsServerTlsEndpoint = publicOrigin;
  const httpsIngestEndpoint = `https://${publicHost}:9444`;
  const mqttQuicEndpoint = `mqtts://${publicHost}:14567`;
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [showCertificateDialog, setShowCertificateDialog] = useState(false);
  const [isDownloadingCa, setIsDownloadingCa] = useState(false);
  const [isDownloadingTrustMBundle, setIsDownloadingTrustMBundle] = useState(false);
  const [showPasswordResetDialog, setShowPasswordResetDialog] = useState(false);
  const [isResettingPassword, setIsResettingPassword] = useState(false);
  const [showPasswordViewDialog, setShowPasswordViewDialog] = useState(false);
  const [newPassword, setNewPassword] = useState<string | null>(null);
  const [passwordViewExpiry, setPasswordViewExpiry] = useState<Date | null>(null);
  const [isViewingPassword, setIsViewingPassword] = useState(false);
  const [pendingSecretInclude, setPendingSecretInclude] = useState<'password' | 'api_key' | null>(null);

  // API key info state (fetched from backend - shows metadata only, not plaintext key)
  const [apiKeyInfo, setApiKeyInfo] = useState<{
    key_id: string;
    key_prefix: string;
    created_at: string;
    expires_at: string;
    last_used: string | null;
    usage_count: number;
  } | null>(null);
  const [apiKeyInfoLoading, setApiKeyInfoLoading] = useState(false);
  // Track newly generated API key (shown only once after regeneration)
  const [newlyGeneratedApiKey, setNewlyGeneratedApiKey] = useState<string | null>(null);

  // TESAIoT Library License state (for Trust M devices)
  const [licenseData, setLicenseData] = useState<{
    license_key: string;
    trust_m_uid: string;
    created_at: string;
    created_by: string;
    device_id: string;
  } | null>(null);
  const [isLoadingLicense, setIsLoadingLicense] = useState(false);
  const [isGeneratingLicense, setIsGeneratingLicense] = useState(false);
  const [isDownloadingLicenseConfig, setIsDownloadingLicenseConfig] = useState(false);
  // Track newly generated license (shown only once after generation)
  const [newlyGeneratedLicense, setNewlyGeneratedLicense] = useState<string | null>(null);

  // Determine authentication mode (default to mtls for backward compatibility)
  const deviceId = device.device_id || device.id;
  const authMode = device.auth_mode || 'mtls';
  const secureElement = (device as any)?.metadata?.secure_element || (device as any)?.metadata?.secureElement;
  const trustProfile = (device as any)?.trust_profile;
  const isServerTls = authMode === 'server_tls';
  const isTrustM = authMode === 'optiga_trust_mtls'
    || secureElement === 'infineon_optiga_trust_m'
    || trustProfile === 'infineon_optiga_trust_m';
  const isMtls = authMode === 'mtls' || isTrustM;
  const certificateStatus = (device as any)?.certificate_status || '';

  // Get device API key from props (may be set after regeneration) or use newly generated
  const deviceApiKey = newlyGeneratedApiKey || device.https_api_key || device.api_key || '';
  const deviceUuid = device.uuid || deviceId || device.id;

  // Get API key info from device object (stored after regeneration)
  useEffect(() => {
    // Use api_key_hint or api_key_prefix from device object (set by regenerate endpoint)
    // Backend stores both: api_key_hint (display) and api_key_prefix (identification)
    const deviceAny = device as any;
    const keyHint = deviceAny.api_key_hint || deviceAny.api_key_prefix;
    if (keyHint) {
      setApiKeyInfo({
        key_id: deviceAny._id || deviceId,
        key_prefix: keyHint,
        created_at: deviceAny.api_key_regenerated_at || deviceAny.api_key_created_at || deviceAny.created_at || new Date().toISOString(),
        expires_at: '', // Not stored in device object
        last_used: null,
        usage_count: 0
      });
    } else {
      setApiKeyInfo(null);
    }
    setApiKeyInfoLoading(false);
  }, [device, deviceId]);

  // Fetch license data for Trust M devices
  useEffect(() => {
    const fetchLicenseData = async () => {
      if (!isTrustM || !deviceId) return;

      setIsLoadingLicense(true);
      try {
        const response = await authFetch(`/api/v1/device-management/license/${deviceId}`);
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.has_license) {
            setLicenseData({
              license_key: data.license_key,
              trust_m_uid: data.trust_m_uid,
              created_at: data.created_at,
              created_by: data.created_by,
              device_id: data.device_id
            });
          } else {
            setLicenseData(null);
          }
        }
      } catch (error) {
        console.error('Failed to fetch license data:', error);
      } finally {
        setIsLoadingLicense(false);
      }
    };

    fetchLicenseData();
  }, [isTrustM, deviceId]);

  // Generate TESAIoT Library License
  const generateLicense = async () => {
    if (!deviceId) return;

    setIsGeneratingLicense(true);
    try {
      const response = await authFetch(`/api/v1/device-management/license/${deviceId}`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setLicenseData({
            license_key: data.license_key,
            trust_m_uid: data.trust_m_uid,
            created_at: data.created_at,
            created_by: data.created_by,
            device_id: data.device_id
          });
          // Show the newly generated license (user must copy it)
          setNewlyGeneratedLicense(data.license_key);
          toast.success('TESAIoT Library License generated successfully');
        } else {
          toast.error(data.detail || 'Failed to generate license');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        toast.error(errorData.detail || 'Failed to generate license');
      }
    } catch (error: any) {
      console.error('Failed to generate license:', error);
      toast.error(error.message || 'Failed to generate license');
    } finally {
      setIsGeneratingLicense(false);
    }
  };

  // Regenerate TESAIoT Library License
  const regenerateLicense = async () => {
    if (!deviceId) return;

    setIsGeneratingLicense(true);
    try {
      const response = await authFetch(`/api/v1/device-management/license/${deviceId}/regenerate`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setLicenseData({
            license_key: data.license_key,
            trust_m_uid: data.trust_m_uid,
            created_at: data.created_at,
            created_by: data.created_by,
            device_id: data.device_id
          });
          // Show the newly regenerated license (user must copy it)
          setNewlyGeneratedLicense(data.license_key);
          toast.success('TESAIoT Library License regenerated successfully');
        } else {
          toast.error(data.detail || 'Failed to regenerate license');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        toast.error(errorData.detail || 'Failed to regenerate license');
      }
    } catch (error: any) {
      console.error('Failed to regenerate license:', error);
      toast.error(error.message || 'Failed to regenerate license');
    } finally {
      setIsGeneratingLicense(false);
    }
  };

  // Download tesaiot_license_config.h file
  const downloadLicenseConfig = async () => {
    if (!deviceId) return;

    setIsDownloadingLicenseConfig(true);
    try {
      const response = await authFetch(`/api/v1/device-management/license/${deviceId}/config-file`);

      if (response.ok) {
        const content = await response.text();
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'tesaiot_license_config.h';
        link.click();
        URL.revokeObjectURL(url);
        toast.success('Downloaded tesaiot_license_config.h');
      } else {
        const errorData = await response.json().catch(() => ({}));
        toast.error(errorData.detail || 'Failed to download config file');
      }
    } catch (error: any) {
      console.error('Failed to download license config:', error);
      toast.error(error.message || 'Failed to download config file');
    } finally {
      setIsDownloadingLicenseConfig(false);
    }
  };

  const copyToClipboard = async (text: string, fieldName: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldName);
      toast.success(`${fieldName} copied to clipboard`);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      toast.error('Failed to copy to clipboard');
    }
  };

  const downloadCaCertificate = async () => {
    setIsDownloadingCa(true);
    try {
      // Download CA certificate chain
      const response = await tesaApi.downloadCaCertificate();
      toast.success('CA certificate downloaded successfully');
    } catch (error) {
      toast.error('Failed to download CA certificate');
      console.error('CA download error:', error);
    } finally {
      setIsDownloadingCa(false);
    }
  };

  const downloadTrustMStarterBundle = async () => {
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
      const cd = response.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
      let filename = '';
      if (match) filename = decodeURIComponent((match[1] || match[2] || '').trim());
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

  // Bundle download toggles (default false for safety per best practice)
  const [bundleIncludePassword, setBundleIncludePassword] = useState(false);
  const [bundleIncludeApiKey, setBundleIncludeApiKey] = useState(false);

  // Organization policy gates for including secrets in bundle
  const [policyAllowBundlePass, setPolicyAllowBundlePass] = useState<boolean>(false);
  const [policyAllowBundleApi, setPolicyAllowBundleApi] = useState<boolean>(false);

  useEffect(() => {
    const loadPolicy = async () => {
      try {
        const res = await authFetch('/api/v1/certificates/policies/certificates');
        if (res.ok) {
          const data = await res.json();
          const pol = data?.policy || {};
          if (typeof pol.allow_bundle_include_password === 'boolean') setPolicyAllowBundlePass(pol.allow_bundle_include_password);
          if (typeof pol.allow_bundle_include_api_key === 'boolean') setPolicyAllowBundleApi(pol.allow_bundle_include_api_key);
        }
      } catch (e) {
        // Leave defaults (both false) on error
        console.warn('Failed to load org certificate policy:', e);
      }
    };
    loadPolicy();
  }, []);

  const downloadCredentials = (format: 'json' | 'env' | 'arduino') => {
    let content = '';
    let filename = '';
    let mimeType = '';

    switch (format) {
      case 'json':
        const jsonData: any = {
          device_id: deviceId,
          device_uuid: deviceUuid,
          auth_mode: authMode,
          server_url: window.location.origin,
          mqtt_broker: window.location.hostname,
          mqtt_port: 8883,
          https_port: 443
        };
        
        if (isServerTls) {
          jsonData.mqtt_username = deviceId;
          jsonData.mqtt_password = '***SHOWN_ONLY_DURING_CREATION***';
          jsonData.note = 'Password is only visible during device creation. Use CA certificate for TLS connection.';
        } else {
          jsonData.device_api_key = deviceApiKey;
          jsonData.note = 'Use client certificates for mTLS authentication.';
        }
        
        content = JSON.stringify(jsonData, null, 2);
        filename = `${deviceId}-credentials.json`;
        mimeType = 'application/json';
        break;

      case 'env':
        content = `# TESAIoT Device Credentials
TESA_DEVICE_ID=${deviceId}
TESA_DEVICE_UUID=${deviceUuid}
TESA_AUTH_MODE=${authMode}
TESA_SERVER_URL=${window.location.origin}
TESA_MQTT_BROKER=${window.location.hostname}
TESA_MQTT_PORT=8883
TESA_HTTPS_PORT=443\n\n`;
        
        if (isServerTls) {
          content += `# Server-TLS Authentication\nTESA_MQTT_USERNAME=${deviceId}\nTESA_MQTT_PASSWORD=***SHOWN_ONLY_DURING_CREATION***\n# Download CA certificate separately for TLS verification`;
        } else {
          content += `# mTLS Authentication\nTESA_DEVICE_API_KEY=${deviceApiKey}\n# Generate client certificates for mutual TLS`;
        }
        filename = `${deviceId}.env`;
        mimeType = 'text/plain';
        break;

      case 'arduino':
        content = `// TESAIoT Device Configuration
// ${device.name} (${deviceId})
// Authentication Mode: ${authMode.toUpperCase()}

// Device Credentials
const char* DEVICE_ID = "${deviceId}";
const char* DEVICE_UUID = "${deviceUuid}";
`;
        
        if (isServerTls) {
          content += `// Server-TLS Authentication
const char* MQTT_USERNAME = "${deviceId}";
const char* MQTT_PASSWORD = "***SHOWN_ONLY_DURING_CREATION***";

// Server Configuration
const char* TESA_SERVER = "${window.location.hostname}";
const int TESA_MQTT_PORT = 8883;

// TLS Connection Example
void connectMQTT() {
  // Load CA certificate
  client.setCACert(ca_cert);
  
  // Connect with username/password
  mqtt_client.setUsernamePassword(MQTT_USERNAME, MQTT_PASSWORD);
  mqtt_client.connect(TESA_SERVER, TESA_MQTT_PORT);
}`;
        } else {
          content += `const char* DEVICE_API_KEY = "${deviceApiKey}";

// Server Configuration
const char* TESA_SERVER = "${window.location.hostname}";
const int TESA_HTTPS_PORT = 443;
const int TESA_MQTT_PORT = 8883;

// mTLS Connection Example
void connectMQTT() {
  // Load certificates
  client.setCACert(ca_cert);
  client.setCertificate(client_cert);
  client.setPrivateKey(client_key);
  
  // Connect with mTLS
  mqtt_client.connect(TESA_SERVER, TESA_MQTT_PORT);
}`;
        }
        filename = `${deviceId}_config.h`;
        mimeType = 'text/plain';
        break;
    }

    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    
    toast.success(`Downloaded ${filename}`);
  };

  const regenerateApiKey = async () => {
    setIsRegenerating(true);
    try {
      // Call regenerate API directly to get the new key
      const response = await tesaApi.regenerateDeviceApiKey(deviceId, {
        reason: 'API key regeneration requested by administrator'
      });

      // API returns status: 'success' (not success: true)
      if ((response.data.success || response.data.status === 'success') && response.data.api_key) {
        // Store newly generated key for one-time display
        setNewlyGeneratedApiKey(response.data.api_key);
        // Set API key info from regenerate response
        // Use api_key_prefix from backend if available, otherwise create hint from api_key
        const keyPrefix = response.data.api_key_prefix || response.data.api_key.substring(0, 20) + '...';
        setApiKeyInfo({
          key_id: deviceId,
          key_prefix: keyPrefix,
          created_at: new Date().toISOString(),
          expires_at: '',
          last_used: null,
          usage_count: 0
        });
        toast.success('API key regenerated successfully. Copy it now - it will not be shown again.');
      } else {
        toast.error('Failed to regenerate API key');
      }
      // NOTE: Do NOT call onRegenerateApiKey() here - it causes race condition
      // that resets newlyGeneratedApiKey before user can copy it.
      // The callback will be called when user clicks "I've copied it" button.
    } catch (error) {
      console.error('Failed to regenerate API key:', error);
      toast.error('Failed to regenerate API key');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handlePasswordReset = async () => {
    setIsResettingPassword(true);
    try {
      const response = await tesaApi.resetDevicePassword(deviceId, {
        notify: true,
        reason: 'Password reset requested by administrator'
      });

      // New API returns password directly (one-time view)
      if (response.data?.mqtt_password) {
        setShowPasswordResetDialog(false);
        setShowPasswordViewDialog(true);
        setNewPassword(response.data.mqtt_password);
        setPasswordViewExpiry(new Date(Date.now() + 5 * 60 * 1000));
        await navigator.clipboard.writeText(response.data.mqtt_password);
        toast.success('Password reset. Copied to clipboard and shown once.');
      } else {
        toast.error('Password reset failed: missing response');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.message || 'Failed to reset password';
      toast.error(errorMessage);
    } finally {
      setIsResettingPassword(false);
    }
  };

  const confirmSecretInclude = () => {
    if (pendingSecretInclude === 'password') {
      setBundleIncludePassword(true);
      toast.info('Server‑TLS password will be regenerated and included in the bundle.');
    } else if (pendingSecretInclude === 'api_key') {
      setBundleIncludeApiKey(true);
      toast.info('Device API key will be regenerated and included in the bundle.');
    }
    setPendingSecretInclude(null);
  };

  const cancelSecretInclude = () => {
    setPendingSecretInclude(null);
  };

  const downloadServerTlsBundle = async (flavor?: 'mqtt' | 'https') => {
    try {
      await tesaApi.downloadServerTlsBundle(
        deviceId,
        {
          include_password: isHighRole && policyAllowBundlePass ? bundleIncludePassword : false,
          include_api_key: isHighRole && policyAllowBundleApi ? bundleIncludeApiKey : false,
          flavor
        },
        (code, message) => {
          const hint = code === 401
            ? 'Please sign in and ensure you have permission. Try regenerating API key if needed.'
            : code === 404
              ? 'Bundle endpoint not found. Please refresh or contact admin to rebuild API.'
              : 'Please try again later.';
          toast.error(`${message}. ${hint}`);
        }
      );
      toast.success('Server‑TLS bundle downloaded');
    } catch (e: any) {
      // handled above; keep generic fallback
      if (e?.message) toast.error(e.message);
    }
  };

  const downloadMqttQuicServerTlsBundle = async () => {
    try {
      await tesaApi.downloadMqttQuicServerTlsBundle(
        deviceId,
        {
          include_password: isHighRole && policyAllowBundlePass ? bundleIncludePassword : false,
          include_api_key: isHighRole && policyAllowBundleApi ? bundleIncludeApiKey : false,
        },
        (code, message) => {
          const hint = code === 401
            ? 'Please sign in and ensure you have permission. Try regenerating API key if needed.'
            : code === 404
              ? 'MQTT-QUIC bundle endpoint not found. Please refresh or contact admin to rebuild API.'
              : 'Please try again later.';
          toast.error(`${message}. ${hint}`);
        }
      );
      toast.success('MQTT-QUIC Server‑TLS bundle downloaded');
    } catch (e: any) {
      if (e?.message) toast.error(e.message);
    }
  };

  const getExampleCode = (language: string) => {
    if (isServerTls) {
      // Server-TLS Examples
      switch (language) {
        case 'arduino':
          return `// Server-TLS Connection (ESP32 Example)
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

const char* mqtt_server = "${window.location.hostname}";
const int mqtt_port = 8883;
const char* mqtt_username = "${deviceId}";
const char* mqtt_password = "YOUR_DEVICE_PASSWORD"; // From device creation

// CA Certificate (download from platform)
const char* ca_cert = R"EOF(
-----BEGIN CERTIFICATE-----
... paste CA certificate here ...
-----END CERTIFICATE-----
)EOF";

WiFiClientSecure espClient;
PubSubClient client(espClient);

void setup() {
  // Set CA certificate for server verification
  espClient.setCACert(ca_cert);
  
  client.setServer(mqtt_server, mqtt_port);
  connectMQTT();
}

void connectMQTT() {
  while (!client.connected()) {
    if (client.connect("${deviceId}", mqtt_username, mqtt_password)) {
      Serial.println("Connected to MQTT broker");
      client.subscribe("devices/${deviceId}/commands");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(5000);
    }
  }
}`;

        case 'python':
          return `# Server-TLS Connection (Python Example)
import paho.mqtt.client as mqtt
import ssl

# MQTT Configuration
MQTT_BROKER = "${window.location.hostname}"
MQTT_PORT = 8883
MQTT_USERNAME = "${deviceId}"
MQTT_PASSWORD = "YOUR_DEVICE_PASSWORD"  # From device creation

# CA Certificate path (download from platform)
CA_CERT_PATH = "./ca-certificate.pem"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(f"devices/${deviceId}/commands")
    else:
        print(f"Connection failed with code {rc}")

# Create MQTT client
client = mqtt.Client(client_id="${deviceId}")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Configure TLS with CA certificate only
client.tls_set(
    ca_certs=CA_CERT_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

# Set callbacks and connect
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()`;

        case 'nodejs':
          return `// Server-TLS Connection (Node.js Example)
const mqtt = require('mqtt');
const fs = require('fs');

// MQTT Configuration
const options = {
  host: '${window.location.hostname}',
  port: 8883,
  protocol: 'mqtts',
  username: '${deviceId}',
  password: 'YOUR_DEVICE_PASSWORD', // From device creation
  
  // CA Certificate for server verification
  ca: fs.readFileSync('./ca-certificate.pem'),
  
  rejectUnauthorized: true,
  clientId: '${deviceId}'
};

// Connect to MQTT broker
const client = mqtt.connect(options);

client.on('connect', () => {
  console.log('Connected to MQTT broker');
  client.subscribe('devices/${deviceId}/commands');
});

client.on('message', (topic, message) => {
  console.log('Received:', topic, message.toString());
});

// Publish telemetry
function publishTelemetry(data) {
  client.publish(
    'devices/${deviceId}/telemetry',
    JSON.stringify(data),
    { qos: 1 }
  );
}`;

        default:
          return '';
      }
    } else {
      // mTLS Examples
      switch (language) {
        case 'arduino':
          return `// mTLS Connection (ESP32 Example)
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

const char* mqtt_server = "${window.location.hostname}";
const int mqtt_port = 8883;

// Certificates (generate and download from platform)
const char* ca_cert = R"EOF(
-----BEGIN CERTIFICATE-----
... paste CA certificate here ...
-----END CERTIFICATE-----
)EOF";

const char* client_cert = R"EOF(
-----BEGIN CERTIFICATE-----
... paste device certificate here ...
-----END CERTIFICATE-----
)EOF";

const char* client_key = R"EOF(
-----BEGIN PRIVATE KEY-----
... paste device private key here ...
-----END PRIVATE KEY-----
)EOF";

WiFiClientSecure espClient;
PubSubClient client(espClient);

void setup() {
  // Set certificates for mTLS
  espClient.setCACert(ca_cert);
  espClient.setCertificate(client_cert);
  espClient.setPrivateKey(client_key);
  
  client.setServer(mqtt_server, mqtt_port);
  connectMQTT();
}

void connectMQTT() {
  while (!client.connected()) {
    if (client.connect("${deviceId}")) {
      Serial.println("Connected with mTLS");
      client.subscribe("devices/${deviceId}/commands");
    } else {
      Serial.print("Failed, rc=");
      Serial.println(client.state());
      delay(5000);
    }
  }
}`;

        case 'python':
          return `# mTLS Connection (Python Example)
import paho.mqtt.client as mqtt
import ssl

# MQTT Configuration
MQTT_BROKER = "${window.location.hostname}"
MQTT_PORT = 8883

# Certificate paths (generate and download from platform)
CA_CERT_PATH = "./ca-certificate.pem"
CLIENT_CERT_PATH = "./device-certificate.pem"
CLIENT_KEY_PATH = "./device-private-key.pem"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected with mTLS")
        client.subscribe(f"devices/${deviceId}/commands")
    else:
        print(f"Connection failed with code {rc}")

# Create MQTT client
client = mqtt.Client(client_id="${deviceId}")

# Configure mTLS
client.tls_set(
    ca_certs=CA_CERT_PATH,
    certfile=CLIENT_CERT_PATH,
    keyfile=CLIENT_KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

# Set callbacks and connect
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()`;

        case 'nodejs':
          return `// mTLS Connection (Node.js Example)
const mqtt = require('mqtt');
const fs = require('fs');

// MQTT Configuration with mTLS
const options = {
  host: '${window.location.hostname}',
  port: 8883,
  protocol: 'mqtts',
  
  // mTLS certificates
  ca: fs.readFileSync('./ca-certificate.pem'),
  cert: fs.readFileSync('./device-certificate.pem'),
  key: fs.readFileSync('./device-private-key.pem'),
  
  rejectUnauthorized: true,
  clientId: '${deviceId}'
};

// Connect to MQTT broker
const client = mqtt.connect(options);

client.on('connect', () => {
  console.log('Connected with mTLS');
  client.subscribe('devices/${deviceId}/commands');
});

client.on('message', (topic, message) => {
  console.log('Received:', topic, message.toString());
});

// Publish telemetry
function publishTelemetry(data) {
  client.publish(
    'devices/${deviceId}/telemetry',
    JSON.stringify(data),
    { qos: 1 }
  );
}`;

        default:
          return '';
      }
    }
  };

  return (
    <>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Device Credentials & Authentication
        </CardTitle>
        <CardDescription>
          {isServerTls
            ? ((typeof device.metadata?.protocol === 'string' && (device.metadata.protocol.toLowerCase() === 'mqtt' || device.metadata.protocol.toLowerCase() === 'mqtts')) ||
               (Array.isArray(device.metadata?.protocols) && device.metadata.protocols.some((p: string) => p.toLowerCase() === 'mqtt' || p.toLowerCase() === 'mqtts'))
              ? 'Server-TLS authentication using username/password with CA certificate'
              : 'Server-TLS authentication using API key with CA certificate')
            : 'Mutual TLS (mTLS) authentication using client certificates'
          }
        </CardDescription>
        <div className="flex items-center gap-2 mt-2">
          <Badge variant={isServerTls ? 'secondary' : 'default'}>
            <Shield className="h-3 w-3 mr-1" />
            {authMode.toUpperCase()} Mode
          </Badge>
          {isServerTls && (
            (typeof device.metadata?.protocol === 'string' && (device.metadata.protocol.toLowerCase() === 'mqtt' || device.metadata.protocol.toLowerCase() === 'mqtts')) ||
            (Array.isArray(device.metadata?.protocols) && device.metadata.protocols.some((p: string) => p.toLowerCase() === 'mqtt' || p.toLowerCase() === 'mqtts'))
          ) && (
            <Badge variant="outline" className="text-orange-600 border-orange-200">
              <AlertCircle className="h-3 w-3 mr-1" />
              Password shown only during creation
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Authentication Mode Specific Alerts */}
        {isServerTls ? (
          <Alert className="mb-4 border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950/30">
            <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            <AlertDescription className="text-orange-800 dark:text-orange-200">
              <strong>Server-TLS Mode:</strong> {
                (typeof device.metadata?.protocol === 'string' && (device.metadata.protocol.toLowerCase() === 'mqtt' || device.metadata.protocol.toLowerCase() === 'mqtts')) ||
                (Array.isArray(device.metadata?.protocols) && device.metadata.protocols.some((p: string) => p.toLowerCase() === 'mqtt' || p.toLowerCase() === 'mqtts'))
                  ? 'This device uses username/password authentication. The password was only visible during device creation and cannot be retrieved.'
                  : 'This device uses API key authentication for secure HTTPS communication.'
              } Download the CA certificate to establish a secure TLS connection.
            </AlertDescription>
          </Alert>
        ) : (
          <Alert className="mb-4 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
            <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <AlertDescription className="text-blue-800 dark:text-blue-200">
              <strong>mTLS Mode:</strong> This device uses mutual TLS authentication with client certificates.
              Generate and download device certificates to establish a secure connection.
            </AlertDescription>
          </Alert>
        )}

        {/* Additional clarification when device is Server‑TLS and CA only */}
        {isServerTls && certificateStatus === 'ca_only' && (
          <Alert className="mb-4 border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
            <AlertCircle className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <AlertDescription className="text-blue-800 dark:text-blue-200">This device uses Server‑TLS and does not have a client certificate.</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue={defaultInnerTab || "credentials"} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="credentials">Credentials</TabsTrigger>
            <TabsTrigger value="certificates">{isServerTls ? 'CA Certificate' : 'Device Certificates'}</TabsTrigger>
            <TabsTrigger value="examples">Code Examples</TabsTrigger>
          </TabsList>

          {/* Credentials Tab */}
          <TabsContent value="credentials" className="space-y-4">
            <div className="space-y-3">
              {/* ca_only clarification inside Credentials tab */}
              {isServerTls && certificateStatus === 'ca_only' && (
                <p className="text-xs text-muted-foreground italic px-1">
                  This device uses Server‑TLS and does not have a client certificate.
                </p>
              )}

              {/* Device Name */}
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex-1">
                  <p className="text-sm font-medium">Device Name</p>
                  <p className="text-sm text-muted-foreground">{device.name}</p>
                </div>
              </div>

              {/* Device ID */}
              <div className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex-1">
                  <p className="text-sm font-medium">Device ID</p>
                  <p className="text-sm text-muted-foreground font-mono">{deviceId}</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => copyToClipboard(deviceId, 'Device ID')}
                >
                  {copiedField === 'Device ID' ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              
              {/* Authentication Mode */}
              <div className="flex items-center justify-between p-3 border rounded-lg bg-muted/30">
                <div className="flex-1">
                  <p className="text-sm font-medium">Authentication Mode</p>
                  <p className="text-sm text-muted-foreground">
                    {isServerTls
                      ? ((typeof device.metadata?.protocol === 'string' && (device.metadata.protocol.toLowerCase() === 'mqtt' || device.metadata.protocol.toLowerCase() === 'mqtts')) ||
                         (Array.isArray(device.metadata?.protocols) && device.metadata.protocols.some((p: string) => p.toLowerCase() === 'mqtt' || p.toLowerCase() === 'mqtts'))
                        ? 'Server-TLS (Username/Password + CA)'
                        : 'Server-TLS (API Key + CA)')
                      : 'mTLS (Client Certificates)'}
                  </p>
                </div>
                <Badge variant={isServerTls ? 'secondary' : 'default'}>
                  {authMode.toUpperCase()}
                </Badge>
              </div>

              {/* Server-TLS Credentials - Only show MQTT credentials if protocol includes MQTT or MQTTS */}
              {isServerTls && (
                (typeof device.metadata?.protocol === 'string' && (device.metadata.protocol.toLowerCase() === 'mqtt' || device.metadata.protocol.toLowerCase() === 'mqtts')) ||
                (Array.isArray(device.metadata?.protocols) && device.metadata.protocols.some((p: string) => p.toLowerCase() === 'mqtt' || p.toLowerCase() === 'mqtts'))
              ) && (
                <>
                  {/* MQTT Username */}
                  <div className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium">MQTT Username</p>
                      <p className="text-sm text-muted-foreground font-mono">{deviceId}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(deviceId, 'MQTT Username')}
                    >
                      {copiedField === 'MQTT Username' ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </Button>
                  </div>
                  
                  {/* MQTT Password Notice */}
                  <div className="flex items-center justify-between p-3 border rounded-lg bg-orange-50 dark:bg-orange-950/30 border-orange-200 dark:border-orange-800">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-orange-900 dark:text-orange-100">MQTT Password</p>
                      <p className="text-sm text-orange-700 dark:text-orange-300">
                        Password was only shown during device creation and cannot be retrieved
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowPasswordResetDialog(true)}
                        className="bg-white hover:bg-orange-50"
                      >
                        <Lock className="h-4 w-4 mr-1" />
                        Reset Password
                      </Button>
                      <AlertCircle className="h-5 w-5 text-orange-600" />
                    </div>
                  </div>
                </>
              )}
              
              {/* Device API Key for HTTPS communication (fallback authentication) */}
              {/* Note: mTLS devices can use API key as fallback for emergency server-TLS connection */}
              {(isServerTls || isMtls) && (
                <div className="p-3 border rounded-lg bg-muted/50 space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium">Device API Key (for HTTPS)</p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(newlyGeneratedApiKey || apiKeyInfo?.key_prefix || '', 'API Key')}
                        disabled={!newlyGeneratedApiKey && !apiKeyInfo}
                        title={newlyGeneratedApiKey ? 'Copy full API key' : 'Copy key prefix'}
                      >
                        {copiedField === 'API Key' ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={regenerateApiKey}
                        disabled={isRegenerating}
                        title={!apiKeyInfo ? "Generate API key for this device" : "Regenerate API key"}
                      >
                        <RefreshCw className={`h-4 w-4 ${isRegenerating ? 'animate-spin' : ''}`} />
                      </Button>
                    </div>
                  </div>
                  {apiKeyInfoLoading ? (
                    <p className="text-sm text-muted-foreground">Loading API key info...</p>
                  ) : newlyGeneratedApiKey ? (
                    <div className="space-y-2">
                      <div className="p-2 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded">
                        <p className="text-xs text-green-700 dark:text-green-300 mb-1 font-medium">New API Key (copy now - will not be shown again):</p>
                        <p className="text-sm text-green-900 dark:text-green-100 font-mono break-all">{newlyGeneratedApiKey}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setNewlyGeneratedApiKey(null);
                          // Now safe to refresh device data from parent
                          if (onRegenerateApiKey) {
                            onRegenerateApiKey();
                          }
                        }}
                        className="text-xs"
                      >
                        I've copied it - hide key
                      </Button>
                    </div>
                  ) : apiKeyInfo ? (
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground font-mono">{apiKeyInfo.key_prefix}...</p>
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        <p>Created: {new Date(apiKeyInfo.created_at).toLocaleDateString()}</p>
                        {apiKeyInfo.expires_at && <p>Expires: {new Date(apiKeyInfo.expires_at).toLocaleDateString()}</p>}
                        {apiKeyInfo.last_used && <p>Last used: {new Date(apiKeyInfo.last_used).toLocaleString()}</p>}
                        <p>Usage count: {apiKeyInfo.usage_count}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-yellow-600">No API key generated - Click regenerate button to create one</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">
                    Use this API key in X-API-Key header for HTTPS REST API calls
                  </p>
                </div>
              )}

              {/* TESAIoT Library License - Only for Trust M devices */}
              {isTrustM && (
                <div className="p-3 border rounded-lg bg-muted/50 space-y-2">
                  {/* Header row with title, badge, and action buttons */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">TESAIoT Library License</p>
                      <Badge variant="secondary" className="text-xs py-0 inline-flex items-center">
                        <Cpu className="h-3 w-3 mr-1 -mt-[1px]" />
                        OPTIGA™ Trust M
                      </Badge>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(newlyGeneratedLicense || licenseData?.license_key || '', 'License Key')}
                        disabled={!newlyGeneratedLicense && !licenseData}
                        title={newlyGeneratedLicense ? 'Copy full license key' : licenseData ? 'Copy license key' : 'No license'}
                      >
                        {copiedField === 'License Key' ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={downloadLicenseConfig}
                        disabled={isDownloadingLicenseConfig || (!newlyGeneratedLicense && !licenseData)}
                        title="Download tesaiot_license_config.h"
                      >
                        {isDownloadingLicenseConfig ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={licenseData ? regenerateLicense : generateLicense}
                        disabled={isGeneratingLicense || !((device as any)?.trust_m_uid || (device as any)?.optiga_trust_m_uid)}
                        title={licenseData ? "Regenerate license key" : "Generate license key"}
                      >
                        <RefreshCw className={`h-4 w-4 ${isGeneratingLicense ? 'animate-spin' : ''}`} />
                      </Button>
                    </div>
                  </div>

                  {/* License content */}
                  {isLoadingLicense ? (
                    <p className="text-sm text-muted-foreground">Loading license info...</p>
                  ) : newlyGeneratedLicense ? (
                    <div className="space-y-2">
                      <div className="p-2 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded">
                        <p className="text-xs text-green-700 dark:text-green-300 mb-1 font-medium">New License Key (copy now - will not be shown again):</p>
                        <p className="text-sm text-green-900 dark:text-green-100 font-mono break-all">{newlyGeneratedLicense}</p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setNewlyGeneratedLicense(null)}
                        className="text-xs"
                      >
                        I've copied it - hide key
                      </Button>
                    </div>
                  ) : licenseData ? (
                    <div className="space-y-1">
                      <p className="text-sm text-muted-foreground font-mono">{licenseData.license_key.substring(0, 32)}...</p>
                      <div className="text-xs text-muted-foreground space-y-0.5">
                        <p>Created: {new Date(licenseData.created_at).toLocaleDateString()}</p>
                        <p>Algorithm: ECDSA P-256 (secp256r1)</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-yellow-600">No license generated - Click regenerate button to create one</p>
                  )}

                  {/* Trust M UID */}
                  {((device as any)?.trust_m_uid || (device as any)?.optiga_trust_m_uid) && (
                    <div className="pt-2 border-t space-y-1">
                      <div className="flex items-center justify-between">
                        <p className="text-xs text-muted-foreground">Trust M UID (27 bytes)</p>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2"
                          onClick={() => copyToClipboard(
                            (device as any)?.trust_m_uid || (device as any)?.optiga_trust_m_uid || '',
                            'Trust M UID'
                          )}
                        >
                          {copiedField === 'Trust M UID' ? <CheckCircle className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground font-mono break-all">
                        {(device as any)?.trust_m_uid || (device as any)?.optiga_trust_m_uid}
                      </p>
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground mt-2">
                    Download <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">tesaiot_license_config.h</code> for firmware integration
                  </p>
                </div>
              )}
            </div>

            {/* Download Options */}
            <div className="pt-4 border-t">
              <p className="text-sm font-medium mb-3">Download Credentials</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadCredentials('json')}
                >
                  <Download className="h-4 w-4 mr-1" />
                  JSON
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadCredentials('env')}
                >
                  <Download className="h-4 w-4 mr-1" />
                  .env
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadCredentials('arduino')}
                >
                  <Download className="h-4 w-4 mr-1" />
                  Arduino
                </Button>
              </div>
            </div>
          </TabsContent>

          {/* Certificates Tab */}
          <TabsContent value="certificates" className="space-y-4">
            {isServerTls ? (
              /* Server-TLS CA Certificate */
              <div className="space-y-4">
                <Alert className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30">
                  <Shield className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    <strong>CA Certificate Required:</strong> Download the Certificate Authority (CA) certificate
                    to verify the server's identity during TLS handshake.
                  </AlertDescription>
                </Alert>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Shield className="h-5 w-5" />
                      Certificate Authority (CA) Certificate
                    </CardTitle>
                    <CardDescription>
                      Required for validating the server's TLS certificate
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground mb-3">
                          The CA certificate is used to verify that you're connecting to the legitimate TESA IoT Platform server.
                        </p>
                        <ul className="text-sm space-y-1 text-muted-foreground">
                          <li>• Contains the root and intermediate certificates</li>
                          <li>• Required for Server-TLS connections</li>
                          <li>• Same for all devices in your organization</li>
                          <li>• Should be embedded in your device firmware</li>
                        </ul>
                      </div>
                      
                      <Button 
                        onClick={downloadCaCertificate}
                        disabled={isDownloadingCa}
                        className="w-full"
                      >
                        {isDownloadingCa ? (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            Downloading...
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4 mr-2" />
                            Download CA Certificate Chain
                          </>
                        )}
                      </Button>
                      {/* Bundle options (policy + role gated). Hidden when policy forbids. */}
                      {(isHighRole && (policyAllowBundlePass || policyAllowBundleApi)) && (
                        <div className="flex items-center gap-4 py-2">
                          {policyAllowBundlePass && (
                            <label className="text-sm flex items-center gap-2">
                              <input
                                type="checkbox"
                                className="accent-primary"
                                checked={bundleIncludePassword}
                                onChange={(e)=>{
                                  if (e.target.checked) {
                                    setPendingSecretInclude('password');
                                  } else {
                                    setBundleIncludePassword(false);
                                  }
                                }}
                              />
                              Include Password (one-time)
                            </label>
                          )}
                          {policyAllowBundleApi && (
                            <label className="text-sm flex items-center gap-2">
                              <input
                                type="checkbox"
                                className="accent-primary"
                                checked={bundleIncludeApiKey}
                                onChange={(e)=>{
                                  if (e.target.checked) {
                                    setPendingSecretInclude('api_key');
                                  } else {
                                    setBundleIncludeApiKey(false);
                                  }
                                }}
                              />
                              Include API Key
                            </label>
                          )}
                        </div>
                      )}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        <Button onClick={()=>downloadServerTlsBundle('mqtt')}>
                          <Download className="h-4 w-4 mr-2" /> Download MQTTS Server‑TLS Bundle
                        </Button>
                        <Button onClick={()=>downloadServerTlsBundle('https')}>
                          <Download className="h-4 w-4 mr-2" /> Download HTTPS Server‑TLS Bundle
                        </Button>
                      </div>
                      <div className="mt-2">
                        <Button onClick={downloadMqttQuicServerTlsBundle} className="w-full">
                          <Download className="h-4 w-4 mr-2" /> Download MQTT-QUIC Server‑TLS Bundle
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground mt-2">
                        Endpoints: HTTPS Server‑TLS uses <code>{httpsServerTlsEndpoint}</code>,
                        HTTPS mTLS (ingest) uses <code>{httpsIngestEndpoint}</code>,
                        MQTT-QUIC uses <code>{mqttQuicEndpoint}</code> (UDP).
                        Bundles include endpoints.json with these values.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            ) : (
              /* mTLS Device Certificates */
              <div className="space-y-4">
                {isTrustM && (
                  <Card className="border-indigo-200 bg-indigo-50/30">
                    <CardHeader>
                      <CardTitle className="text-lg flex items-center gap-2">
                        <Shield className="h-5 w-5 text-indigo-500" />
                        OPTIGA™ Trust M Starter Bundle
                      </CardTitle>
                      <CardDescription>
                        Download the factory onboarding bundle for OPTIGA™ Trust M devices before the first TLS session.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        Bundle includes the Infineon trust anchor, the recorded factory certificate, a factory metadata
                        summary, and a preconfigured `mqtt_client_config.h`. Use it to preload OPTIGA™ OIDs (0xE0E8/0xE0E9)
                        before running the Protected Update rotation job.
                      </p>
                      <Button
                        variant="primary"
                        onClick={downloadTrustMStarterBundle}
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
                      <Alert className="border-indigo-200 bg-white">
                        <AlertDescription className="text-xs text-muted-foreground space-y-1">
                          <p>OID quick guide:</p>
                          <ul className="list-disc list-inside">
                            <li><code>0xE0C2</code> – Factory UID (read-only)</li>
                            <li><code>0xE0E8</code> – Infineon trust anchor</li>
                            <li><code>0xE0E9</code> – Factory certificate (optional)</li>
                            <li><code>0xE0F1</code> – CSR/key slot for Protected Update rotation</li>
                          </ul>
                        </AlertDescription>
                      </Alert>
                    </CardContent>
                  </Card>
                )}
                <Alert className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
                  <Shield className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <AlertDescription className="text-blue-800 dark:text-blue-200">
                    <strong>Client Certificates Required:</strong> Generate device-specific certificates for
                    mutual TLS authentication. Both client and server verify each other's identity.
                  </AlertDescription>
                </Alert>
                
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Key className="h-5 w-5" />
                      Device Client Certificates
                    </CardTitle>
                    <CardDescription>
                      Generate and download certificates for mTLS authentication
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="p-4 bg-muted rounded-lg">
                        <p className="text-sm text-muted-foreground mb-3">
                          Client certificates provide strong mutual authentication between your device and the platform.
                        </p>
                        <ul className="text-sm space-y-1 text-muted-foreground">
                          <li>• Unique certificate per device</li>
                          <li>• Includes private key (keep secure!)</li>
                          <li>• CA certificate for server verification</li>
                          <li>• Valid for 1 year by default</li>
                        </ul>
                      </div>
                      
                      <Button 
                        onClick={() => setShowCertificateDialog(true)}
                        className="w-full"
                        variant="default"
                      >
                        <Shield className="h-4 w-4 mr-2" />
                        Generate & Download Certificates
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* Auth Patterns Tab - Removed, replaced with Examples */}

          {/* Code Examples Tab */}
          <TabsContent value="examples" className="space-y-4">
            <Alert className="mb-4 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950/30">
              <Code className="h-4 w-4 text-slate-600 dark:text-slate-400" />
              <AlertDescription className="text-slate-800 dark:text-slate-200">
                <strong>{isServerTls ? 'Server-TLS' : 'mTLS'} Connection Examples:</strong>
                {isServerTls
                  ? ' These examples show how to connect using username/password authentication with server certificate verification.'
                  : ' These examples demonstrate mutual TLS authentication where both client and server verify each other\'s certificates.'
                }
              </AlertDescription>
            </Alert>
            
            <div className="space-y-4">
              {/* Arduino Example */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-4 w-4" />
                      <h4 className="font-medium">Arduino / ESP32</h4>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(getExampleCode('arduino'), 'Arduino code')}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    <code>{getExampleCode('arduino')}</code>
                  </pre>
                </CardContent>
              </Card>
              
              {/* Python Example */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      <h4 className="font-medium">Python</h4>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(getExampleCode('python'), 'Python code')}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    <code>{getExampleCode('python')}</code>
                  </pre>
                </CardContent>
              </Card>
              
              {/* Node.js Example */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Code className="h-4 w-4" />
                      <h4 className="font-medium">Node.js</h4>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(getExampleCode('nodejs'), 'Node.js code')}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                    <code>{getExampleCode('nodejs')}</code>
                  </pre>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>

    {/* HTTPs Credentials Section */}
    {device.metadata?.protocol && 
     (Array.isArray(device.metadata.protocol) ? device.metadata.protocol.includes('https') : device.metadata.protocol === 'https') && (
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            HTTPs API Credentials
          </CardTitle>
          <CardDescription>
            Use these credentials for HTTP/REST API communication
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isServerTls && device.https_api_key && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">API Endpoint</label>
                <div className="flex items-center gap-2 mt-1">
                  <code className="flex-1 p-2 bg-muted rounded text-sm font-mono">
                    {apiTelemetryEndpoint}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(apiTelemetryEndpoint, 'API endpoint')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">API Key</label>
                <div className="flex items-center gap-2 mt-1">
                  <code className="flex-1 p-2 bg-muted rounded text-sm font-mono">
                    {device.https_api_key}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(device.https_api_key!, 'API key')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium">Example Usage</label>
                <pre className="p-3 bg-muted rounded text-xs overflow-x-auto mt-1">
{`curl -X POST ${apiTelemetryEndpoint} \\
  -H "X-API-Key: ${device.https_api_key}" \\
  -H "Content-Type: application/json" \\
  -d '{"temperature": 25.5, "humidity": 60}'`}
                </pre>
              </div>
            </div>
          )}
          
          {isMtls && (
            <div className="space-y-4">
              <Alert className="border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-950/30">
                <AlertCircle className="h-4 w-4 text-slate-600 dark:text-slate-400" />
                <AlertDescription className="text-slate-800 dark:text-slate-200">
                  Use the same client certificate and key as MQTT for HTTPs mTLS authentication.
                </AlertDescription>
              </Alert>
              
              <div>
                <label className="text-sm font-medium">API Endpoint</label>
                <div className="flex items-center gap-2 mt-1">
                  <code className="flex-1 p-2 bg-muted rounded text-sm font-mono">
                    {apiTelemetryEndpoint}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(apiTelemetryEndpoint, 'API endpoint')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">Example Usage</label>
                <pre className="p-3 bg-muted rounded text-xs overflow-x-auto mt-1">
{`curl -X POST ${apiTelemetryEndpoint} \\
  --cert device.crt \\
  --key device.key \\
  --cacert ca.crt \\
  -H "Content-Type: application/json" \\
  -d '{"temperature": 25.5, "humidity": 60}'`}
                </pre>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    )}
    
    {/* Certificate Generation Dialog for mTLS */}
    {isMtls && showCertificateDialog && (
      <CertificateGenerationDialog
        device={device}
        isOpen={showCertificateDialog}
        onClose={() => setShowCertificateDialog(false)}
        onSuccess={() => {
          setShowCertificateDialog(false);
          toast.success('Certificates generated and downloaded successfully');
        }}
      />
    )}
    
    {/* Bundle secret confirmation dialog */}
    <Dialog
      open={pendingSecretInclude !== null}
      onOpenChange={(open) => {
        if (!open) setPendingSecretInclude(null);
      }}
    >
      <DialogContent className="z-[200]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            {pendingSecretInclude === 'password' ? 'Include One-Time Password' : 'Include API Key'}
          </DialogTitle>
          <DialogDescription>
            Regenerating credentials ensures only this bundle contains the newest secret.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Alert className="border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950/30">
            <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            <AlertDescription className="text-orange-800 dark:text-orange-200 space-y-2">
              {pendingSecretInclude === 'password' ? (
                <>
                  <p><strong>Caution:</strong></p>
                  <ul className="space-y-1 text-sm">
                    <li>• Generates a brand new password and stores its hash in the TESAIoT's secure database.</li>
                    <li>• Previously issued password stops working once this device reconnects.</li>
                    <li>• The plaintext password appears only inside this download. Please update your device firmware immediately.</li>
                  </ul>
                </>
              ) : (
                <>
                  <p><strong>Caution:</strong></p>
                  <ul className="space-y-1 text-sm">
                    <li>• Issues a new device API key and revokes the old key in the TESAIoT's secure database.</li>
                    <li>• All client integrations must switch to the new key after downloading the bundle.</li>
                    <li>• Action is recorded in the audit log for traceability.</li>
                  </ul>
                </>
              )}
              <p className="text-sm">
                Continue only if you are ready to roll out the updated credential to this device using it.
              </p>
            </AlertDescription>
          </Alert>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={cancelSecretInclude}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={confirmSecretInclude}>
            Regenerate & Include
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    {/* Password Reset Confirmation Dialog */}
    <Dialog open={showPasswordResetDialog} onOpenChange={setShowPasswordResetDialog}>
      <DialogContent className="z-[200]">
          <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5 text-orange-600" />
            Reset Device Password
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to reset the password for this device?
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Alert className="border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950/30">
            <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
            <AlertDescription className="text-orange-800 dark:text-orange-200">
              <strong>Warning:</strong> This action will:
              <ul className="mt-2 space-y-1 text-sm">
                <li>• Generate a new password for the device</li>
                <li>• Disconnect the device if currently connected</li>
                <li>• Require updating the device firmware with the new password</li>
                <li>• Be logged in the audit trail</li>
              </ul>
            </AlertDescription>
          </Alert>
          
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              <strong>Device:</strong> {device.name} ({deviceId})
            </p>
            <p className="text-sm text-muted-foreground">
              <strong>Current Auth Mode:</strong> Server-TLS
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setShowPasswordResetDialog(false)}
            disabled={isResettingPassword}
          >
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handlePasswordReset}
            disabled={isResettingPassword}
          >
            {isResettingPassword ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Resetting...
              </>
            ) : (
              <>
                <Lock className="h-4 w-4 mr-2" />
                Reset Password
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    
    {/* Password View Dialog (one-time display after reset) */}
    <Dialog open={showPasswordViewDialog} onOpenChange={(open) => {
      if (!open && !newPassword) {
        toast.warning('Password view canceled. You will need to reset again.');
      }
      setShowPasswordViewDialog(open);
    }}>
      <DialogContent className="z-[200]">
          <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5 text-green-600" />
            New Device Password
          </DialogTitle>
          <DialogDescription>
            {newPassword 
              ? 'Copy this password now. It will not be shown again.'
              : 'Click the button below to reveal the new password.'
            }
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {!newPassword && (
            <Alert className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30">
              <AlertDescription className="text-blue-800 dark:text-blue-200">
                Use "Reset Password" to generate a new password. It will be shown once here and copied to clipboard automatically.
              </AlertDescription>
            </Alert>
          )}

          {newPassword && (
            <>
              <Alert className="border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/30">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                <AlertDescription className="text-green-800 dark:text-green-200">
                  Password has been reset successfully and copied to clipboard.
                </AlertDescription>
              </Alert>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">New Password</label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 bg-muted rounded text-sm font-mono select-all">
                    {newPassword}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newPassword, 'New password')}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              <div className="pt-4 space-y-3">
                <p className="text-sm text-muted-foreground font-medium">Next Steps:</p>
                <ol className="text-sm space-y-2 text-muted-foreground">
                  <li>1. Save this password securely - it cannot be retrieved again</li>
                  <li>2. Update your device firmware with the new password</li>
                  <li>3. Test the connection with the new credentials</li>
                  <li>4. The device will need to reconnect with the new password</li>
                </ol>
              </div>
            </>
          )}
        </div>
        {newPassword && (
          <DialogFooter>
            <Button
              onClick={() => {
                setShowPasswordViewDialog(false);
                setNewPassword(null);
              }}
            >
              Done
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  </>
  );
};
