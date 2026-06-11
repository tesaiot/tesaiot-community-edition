/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Main device interface representing an IoT device in the system
 */
export interface Device {
  id: string;
  device_id?: string;  // Actual device ID for API calls
  name: string;
  type: 'sensor' | 'actuator' | 'gateway' | 'controller';
  status: 'online' | 'offline' | 'error' | 'maintenance';
  organizationId: string;
  organizationName: string;
  serialNumber: string;
  firmwareVersion: string;
  lastSeen: Date | null;
  registeredAt: Date;
  location?: {
    name: string;
    latitude?: number;
    longitude?: number;
  };
  metadata: {
    manufacturer?: string;
    model?: string;
    protocol: 'mqtts' | 'https';
    network_type?: 'nbiot' | 'lorawan' | 'wifi' | 'cellular' | 'bluetooth' | 'zigbee' | 'modbus' | 'opcua' | 'matter';
    ipAddress?: string;
    macAddress?: string;
    devicePicture?: string | null;
    industry?: string;
    industrySpecificData?: Record<string, any> | null;
    factory_uid?: string;
    certificate_generation_method?: string; // CSR field in metadata
  };
  // Public key fields
  publicKey?: DevicePublicKey;
  hasPublicKey?: boolean;
  keyStatus?: KeyStatus;
  keyEncryptionStatus?: KeyEncryptionStatus;
  keyAlgorithm?: KeyAlgorithm;
  keyFingerprint?: string;
  keyExpiresAt?: Date;
  keyRotationNeeded?: boolean;
  // Additional encryption fields from backend
  device_public_key?: any; // Backend field name
  public_key?: string; // Alternative backend field name
  key_encryption_enabled?: boolean; // Backend field for encryption enablement
  telemetry: {
    messagesPerMinute: number;
    dataUsage: number; // MB
    uptime: number; // seconds
    signalStrength?: number; // RSSI
    batteryLevel?: number; // percentage
  };
  certificate?: {
    serial: string;
    expiresAt: Date;
    status: 'active' | 'expiring' | 'expired' | 'valid';
    generationMethod?: 'auto-generate' | 'upload-csr';
    type?: CertificateType;
    format?: CertificateFormat;
    algorithm?: CertificateAlgorithm | string;
    keySize?: number;
    csrDetails?: CSRDetails;
    // Additional fields for certificate details display
    validFrom?: Date;
    validTo?: Date;
    issuer?: string;
    subject?: string;
  };
  tags: string[];
  config?: Record<string, any>;
  auth_mode?: 'mtls' | 'server_tls'; // Authentication mode for device connection (mTLS includes OPTIGA Trust M support)
  mqtt_password?: string; // MQTT password for server_tls devices (only available during creation)
  trustm_uid?: string; // Infineon OPTIGA Trust M unique identifier (54 hex characters from OID 0xE0C2)
  
  // Certificate fields from API response
  certificate_algorithm?: string;
  certificate_info?: any;
  certificate_serial?: string;
  certificate_issued_at?: string;
  certificate_expires_at?: string;
  certificate_status?: string;
  
  // CSR-related fields for device detection
  certificate_generation_method?: string;
  generation_method?: string;
  csr_provided?: boolean;
  
  // React-JSONSchema-Form integration for IoT device schema management
  telemetrySchema?: {
    schema: Record<string, any>;      // JSON Schema for telemetry data structure
    uiSchema?: Record<string, any>;   // UI Schema for form customization
    formData?: Record<string, any>;   // Sample/default telemetry data
    lastUpdated?: Date;               // Schema last modified timestamp
    metadata?: {                      // Schema metadata for tracking
      templateId?: string;            // ID of the template used
      templateName?: string;          // Human-readable template name
      customized?: boolean;           // Whether schema was customized
      createdAt?: string;             // When schema was created
      updatedAt?: string;             // When schema was last updated
    };
  };
  actuatorSchema?: {
    schema: Record<string, any>;      // JSON Schema for actuator commands
    uiSchema?: Record<string, any>;   // UI Schema for command forms
    formData?: Record<string, any>;   // Sample/default command data
    lastUpdated?: Date;               // Schema last modified timestamp
    metadata?: {                      // Schema metadata for tracking
      templateId?: string;            // ID of the template used
      templateName?: string;          // Human-readable template name
      customized?: boolean;           // Whether schema was customized
      createdAt?: string;             // When schema was created
      updatedAt?: string;             // When schema was last updated
    };
  };
}

/**
 * Device group for organizing multiple devices
 */
export interface DeviceGroup {
  id: string;
  name: string;
  description: string;
  deviceCount: number;
  tags: string[];
}

/**
 * Firmware update information
 */
export interface FirmwareUpdate {
  id: string;
  version: string;
  deviceType: string;
  releaseDate: Date;
  size: number; // bytes
  changelog: string;
  status: 'available' | 'downloading' | 'installing' | 'installed';
  progress?: number;
}

/**
 * Device type enum for type safety
 */
export enum DeviceType {
  SENSOR = 'sensor',
  ACTUATOR = 'actuator',
  GATEWAY = 'gateway',
  CONTROLLER = 'controller'
}

/**
 * Authentication mode enum for device connections
 */
export enum AuthMode {
  MTLS = 'mtls',
  SERVER_TLS = 'server_tls'
}

/**
 * Device status enum for type safety
 */
export enum DeviceStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  ERROR = 'error',
  MAINTENANCE = 'maintenance'
}

/**
 * Protocol enum for device communication
 */
export enum DeviceProtocol {
  MQTTS = 'mqtts',
  HTTPS = 'https'
}

/**
 * Network type enum for device connectivity
 */
export enum NetworkType {
  NBIOT = 'nbiot',
  LORAWAN = 'lorawan',
  WIFI = 'wifi',
  CELLULAR = 'cellular',
  BLUETOOTH = 'bluetooth',
  ZIGBEE = 'zigbee',
  MODBUS = 'modbus',
  OPCUA = 'opcua',
  MATTER = 'matter'
}

/**
 * Certificate status enum
 */
export enum CertificateStatus {
  ACTIVE = 'active',
  EXPIRING = 'expiring',
  EXPIRED = 'expired',
  VALID = 'valid'
}

/**
 * Firmware update status enum
 */
export enum FirmwareUpdateStatus {
  AVAILABLE = 'available',
  DOWNLOADING = 'downloading',
  INSTALLING = 'installing',
  INSTALLED = 'installed'
}

/**
 * Certificate generation method enum
 */
export enum CertificateGenerationMethod {
  AUTO_GENERATE = 'auto-generate',
  UPLOAD_CSR = 'upload-csr'
}

/**
 * Certificate type enum
 */
export enum CertificateType {
  AUTO = 'auto',
  ECC_P256 = 'ecc-p256',
  ECC_P384 = 'ecc-p384',
  RSA_2048 = 'rsa-2048',
  RSA_3072 = 'rsa-3072',
  RSA_4096 = 'rsa-4096'
}

/**
 * Certificate format enum
 */
export enum CertificateFormat {
  PEM = 'pem',
  DER = 'der',
  PKCS12 = 'pkcs12'
}

/**
 * Certificate algorithm enum for CSR validation
 */
export enum CertificateAlgorithm {
  RSA = 'RSA',
  ECDSA = 'ECDSA',
  EC = 'EC'
}

/**
 * CSR validation status enum
 */
export enum CSRValidationStatus {
  PENDING = 'pending',
  VALIDATING = 'validating',
  VALID = 'valid',
  INVALID = 'invalid',
  ERROR = 'error'
}

/**
 * CSR Subject interface for certificate details
 */
export interface CSRSubject {
  CN?: string; // Common Name (optional - platform will replace with device_id)
  O?: string; // Organization
  OU?: string; // Organizational Unit
  C?: string; // Country
  ST?: string; // State/Province
  L?: string; // Locality/City
  emailAddress?: string; // Email Address
}

/**
 * CSR Extensions interface
 */
export interface CSRExtensions {
  subjectAltName?: string[];
  keyUsage?: string[];
  extendedKeyUsage?: string[];
  basicConstraints?: {
    CA: boolean;
    pathLenConstraint?: number;
  };
}

/**
 * CSR Details interface for parsed CSR information
 */
export interface CSRDetails {
  subject: CSRSubject;
  keyAlgorithm: string;
  keySize: number;
  signatureAlgorithm: string;
  publicKey?: string;
  extensions?: CSRExtensions;
  version?: number;
  fingerprint?: string;
}

/**
 * CSR Validation Response interface
 */
export interface CSRValidationResponse {
  isValid: boolean;
  message: string;
  details?: CSRDetails;
  errors?: string[];
  warnings?: string[];
}

/**
 * Certificate Generation Request interface
 */
export interface CertificateGenerationRequest {
  deviceId: string;
  generationMethod: CertificateGenerationMethod;
  certificateType?: CertificateType;
  certificateFormat?: CertificateFormat;
  csrContent?: string;
  validityDays?: number;
  keyUsage?: string[];
  extendedKeyUsage?: string[];
  subjectAltNames?: string[];
}

/**
 * Certificate Generation Response interface
 */
export interface CertificateGenerationResponse {
  success: boolean;
  certificate?: {
    id: string;
    deviceId: string;
    serial: string;
    issuer: string;
    subject: string;
    validFrom: Date;
    validTo: Date;
    algorithm: string;
    keySize: number;
    fingerprint: string;
    status: CertificateStatus;
    format: CertificateFormat;
    content: string; // PEM, DER, or PKCS12 content
    privateKey?: string; // Only for auto-generated certificates
  };
  warnings?: string[];
  error?: string;
}

/**
 * Form data interface for certificate options
 */
export interface CertificateFormData {
  certificateGenerationMethod: CertificateGenerationMethod;
  certificateType: CertificateType;
  certificateFormat: CertificateFormat;
  csrContent?: string;
  validityDays?: number;
  keyUsage?: string[];
  extendedKeyUsage?: string[];
  subjectAltNames?: string[];
}

/**
 * CSR Validation State interface for form management
 */
export interface CSRValidationState {
  status: CSRValidationStatus;
  isValid: boolean;
  hasValidated: boolean;
  message: string;
  details?: CSRDetails;
  errors?: string[];
  warnings?: string[];
}

/**
 * Certificate Options Component Props interface
 */
export interface CertificateOptionsProps {
  formData: CertificateFormData;
  onFormDataChange: (data: CertificateFormData) => void;
  onCSRValidationChange?: (isValid: boolean, hasValidated: boolean, details?: CSRDetails) => void;
  validationState?: CSRValidationState;
  hasError?: boolean;
  errorMessage?: string;
  disabled?: boolean;
  showAdvancedOptions?: boolean;
}

/**
 * API Error interface for CSR/Certificate operations
 */
export interface CertificateAPIError {
  code: string;
  message: string;
  details?: Record<string, any>;
  field?: string; // Field that caused the error
  suggestions?: string[]; // Suggested fixes
}

/**
 * Device Certificate Management interface
 */
export interface DeviceCertificateManagement {
  autoRenewal: boolean;
  renewalThresholdDays: number;
  notificationEnabled: boolean;
  backupEnabled: boolean;
  encryptionEnabled: boolean;
  keyRotationEnabled: boolean;
  keyRotationIntervalDays: number;
}

/**
 * Certificate Template interface for predefined configurations
 */
export interface CertificateTemplate {
  id: string;
  name: string;
  description: string;
  deviceTypes: DeviceType[];
  certificateType: CertificateType;
  certificateFormat: CertificateFormat;
  validityDays: number;
  keyUsage: string[];
  extendedKeyUsage: string[];
  subjectTemplate: Partial<CSRSubject>;
  extensions?: Partial<CSRExtensions>;
  isDefault: boolean;
}

/**
 * Device Public Key interface representing cryptographic keys for devices
 */
export interface DevicePublicKey {
  keyId: string; // Unique key identifier (key_id in backend)
  deviceId: string; // Device this key belongs to
  organizationId: string; // Organization that owns this key
  sessionId?: string; // Generation session that created this key
  algorithm: string; // Key algorithm (ECC-P256, RSA-3072, etc.)
  deviceType?: string; // Type of device (sensor, gateway, etc.)
  keyFingerprint: string; // SHA-256 fingerprint of public key
  status: KeyStatus; // Key lifecycle status
  generatedAt: Date; // When key was generated
  activatedAt?: Date; // When key was activated
  expiresAt: Date; // When key expires
  revokedAt?: Date; // When key was revoked (if applicable)
  rotatedAt?: Date; // When key was rotated (if applicable)
  publicKeyPem: string; // Public key in PEM format
  encryptedPrivateKey?: string; // Encrypted private key (if not in Vault)
  vaultPath?: string; // Path in Vault where private key is stored
  distributionStatus?: string; // pending, distributed, downloaded, expired
  distributionMethod?: string; // secure_download, escrow, direct_push, ota_update
  distributedAt?: Date; // When key was distributed
  downloadCount?: number; // Number of times key was downloaded
  lastDownloadedAt?: Date; // Last download timestamp
  metadata?: Record<string, any>; // Additional key metadata
  usageStats?: {
    signaturesCreated: number;
    lastUsed: Date;
    useCount: number;
  };
}

/**
 * Key Encryption Status enum for tracking encryption state
 */
export enum KeyEncryptionStatus {
  UNENCRYPTED = 'unencrypted',
  ENCRYPTED = 'encrypted',
  VAULT_STORED = 'vault_stored',
  ESCROWED = 'escrowed',
  KEY_WRAPPED = 'key_wrapped'
}

/**
 * Key Status enum matching backend KeyStatus
 */
export enum KeyStatus {
  PENDING = 'pending',
  GENERATED = 'generated',
  DISTRIBUTED = 'distributed',
  ACTIVE = 'active',
  REVOKED = 'revoked',
  EXPIRED = 'expired',
  ROTATED = 'rotated'
}

/**
 * Key Distribution Status enum
 */
export enum KeyDistributionStatus {
  PENDING = 'pending',
  DISTRIBUTED = 'distributed',
  DOWNLOADED = 'downloaded',
  EXPIRED = 'expired'
}

/**
 * Key Distribution Method enum
 */
export enum KeyDistributionMethod {
  SECURE_DOWNLOAD = 'secure_download',
  ESCROW = 'escrow',
  DIRECT_PUSH = 'direct_push',
  OTA_UPDATE = 'ota_update'
}

/**
 * Key Algorithm enum for supported algorithms
 */
export enum KeyAlgorithm {
  ECC_P256 = 'ECC-P256',
  ECC_P384 = 'ECC-P384',
  RSA_2048 = 'RSA-2048',
  RSA_3072 = 'RSA-3072',
  RSA_4096 = 'RSA-4096'
}

/**
 * Type guards for runtime type checking
 */
export const isValidCertificateGenerationMethod = (value: any): value is CertificateGenerationMethod => {
  return Object.values(CertificateGenerationMethod).includes(value);
};

export const isValidCertificateType = (value: any): value is CertificateType => {
  return Object.values(CertificateType).includes(value);
};

export const isValidCertificateFormat = (value: any): value is CertificateFormat => {
  return Object.values(CertificateFormat).includes(value);
};

export const isValidCSRValidationStatus = (value: any): value is CSRValidationStatus => {
  return Object.values(CSRValidationStatus).includes(value);
};

export const isValidKeyStatus = (value: any): value is KeyStatus => {
  return Object.values(KeyStatus).includes(value);
};

export const isValidKeyEncryptionStatus = (value: any): value is KeyEncryptionStatus => {
  return Object.values(KeyEncryptionStatus).includes(value);
};

export const isValidEncryptionUIStatus = (value: any): value is EncryptionUIStatus => {
  return Object.values(EncryptionUIStatus).includes(value);
};

export const isValidKeyDistributionMethod = (value: any): value is KeyDistributionMethod => {
  return Object.values(KeyDistributionMethod).includes(value);
};

export const isValidKeyAlgorithm = (value: any): value is KeyAlgorithm => {
  return Object.values(KeyAlgorithm).includes(value);
};

export const isValidNetworkType = (value: any): value is NetworkType => {
  return Object.values(NetworkType).includes(value);
};

export const isValidDeviceProtocol = (value: any): value is DeviceProtocol => {
  return Object.values(DeviceProtocol).includes(value);
};

/**
 * Public Key Generation Request interface
 */
export interface PublicKeyGenerationRequest {
  deviceId: string;
  algorithm: KeyAlgorithm;
  validityDays?: number;
  keyUsage?: string[];
  extendedKeyUsage?: string[];
  metadata?: Record<string, any>;
}

/**
 * Public Key Generation Response interface
 */
export interface PublicKeyGenerationResponse {
  success: boolean;
  key?: DevicePublicKey;
  sessionId?: string;
  warnings?: string[];
  error?: string;
}

/**
 * Key Provisioning Session interface
 */
export interface KeyProvisioningSession {
  sessionId: string;
  organizationId: string;
  initiatedBy: string;
  initiatedAt: Date;
  completedAt?: Date;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  totalDevices: number;
  successful: number;
  failed: number;
  keyType: string;
  errors?: string[];
}

/**
 * Key Distribution Request interface
 */
export interface KeyDistributionRequest {
  sessionId: string;
  deviceIds: string[];
  method: KeyDistributionMethod;
  expiresInHours?: number;
  maxDownloads?: number;
  notifyDevices?: boolean;
}

/**
 * Key Distribution Response interface
 */
export interface KeyDistributionResponse {
  success: boolean;
  distributionId: string;
  downloadLinks?: Array<{
    deviceId: string;
    token: string;
    url: string;
    expiresAt: Date;
  }>;
  error?: string;
}

/**
 * Key Rotation Request interface
 */
export interface KeyRotationRequest {
  deviceId: string;
  currentKeyId: string;
  algorithm?: KeyAlgorithm;
  reason: string;
  immediate?: boolean;
}

/**
 * Key Rotation Response interface
 */
export interface KeyRotationResponse {
  success: boolean;
  oldKeyId: string;
  newKey?: DevicePublicKey;
  rotationScheduledAt?: Date;
  error?: string;
}

/**
 * Key Status Summary interface for dashboard
 */
export interface KeyStatusSummary {
  totalKeys: number;
  byStatus: Record<KeyStatus, number>;
  expiringSoon: number;
  rotationNeeded: number;
  byAlgorithm: Record<string, number>;
  lastUpdated: Date;
}

/**
 * Encryption UI Status enum for tracking UI state
 */
export enum EncryptionUIStatus {
  IDLE = 'idle',
  UPLOADING = 'uploading',
  VALIDATING = 'validating',
  PROCESSING = 'processing',
  SUCCESS = 'success',
  ERROR = 'error',
  GENERATING = 'generating',
  DISTRIBUTING = 'distributing'
}

/**
 * Public Key Upload State interface for UI state management
 */
export interface PublicKeyUploadState {
  status: EncryptionUIStatus;
  progress: number; // 0-100 percentage
  message: string;
  isUploading: boolean;
  isValidating: boolean;
  hasUploaded: boolean;
  hasValidated: boolean;
  uploadedAt?: Date;
  validatedAt?: Date;
  file?: {
    name: string;
    size: number;
    type: string;
    lastModified: Date;
  };
  validationResult?: KeyValidationResult;
  errors?: string[];
  warnings?: string[];
}

/**
 * Key Validation Result interface for public key validation
 */
export interface KeyValidationResult {
  isValid: boolean;
  keyType: string;
  algorithm: string;
  keySize: number;
  fingerprint: string;
  format: 'PEM' | 'DER' | 'SSH' | 'JWK';
  encoding?: string;
  publicKeyData?: string;
  keyUsage?: string[];
  expiresAt?: Date;
  issuer?: string;
  subject?: string;
  serialNumber?: string;
  version?: number;
  signatureAlgorithm?: string;
  extensions?: Record<string, any>;
  errors?: string[];
  warnings?: string[];
  metadata?: {
    uploadedFileName?: string;
    uploadedFileSize?: number;
    detectedFormat?: string;
    conversionApplied?: boolean;
    validationTimestamp?: Date;
  };
}

/**
 * Enhanced Certificate Form Data interface with encryption fields
 */
export interface EnhancedCertificateFormData extends CertificateFormData {
  // Public key upload fields
  publicKeyFile?: File;
  publicKeyContent?: string;
  publicKeyFormat?: 'PEM' | 'DER' | 'SSH' | 'JWK';
  
  // Encryption options
  encryptionEnabled?: boolean;
  keyEncryptionMethod?: 'vault' | 'escrow' | 'local';
  encryptionPassword?: string;
  confirmEncryptionPassword?: string;
  
  // Key distribution settings
  distributionMethod?: KeyDistributionMethod;
  distributionExpiryHours?: number;
  maxDownloads?: number;
  notifyDevices?: boolean;
  
  // Auto-rotation settings
  autoRotationEnabled?: boolean;
  rotationIntervalDays?: number;
  rotationNotificationDays?: number;
  
  // Backup and recovery
  backupEnabled?: boolean;
  recoveryKeygenerated?: boolean;
  escrowEnabled?: boolean;
}

/**
 * Device Form Data interface with encryption support
 */
export interface DeviceFormData {
  // Basic device information
  name: string;
  type: DeviceType;
  serialNumber: string;
  organizationId: string;
  
  // Location and metadata
  location?: {
    name: string;
    latitude?: number;
    longitude?: number;
  };
  metadata: {
    manufacturer?: string;
    model?: string;
    protocol: 'mqtts' | 'https';
    network_type?: 'nbiot' | 'lorawan' | 'wifi' | 'cellular' | 'bluetooth' | 'zigbee' | 'modbus' | 'opcua' | 'matter';
    ipAddress?: string;
    macAddress?: string;
    devicePicture?: string | null;
    industry?: string;
    industrySpecificData?: Record<string, any> | null;
    certificate_generation_method?: string; // CSR field in metadata
  };
  
  // Certificate and encryption settings
  certificate?: EnhancedCertificateFormData;
  
  // Public key settings
  publicKey?: {
    uploadState: PublicKeyUploadState;
    generationSettings?: {
      algorithm: KeyAlgorithm;
      keySize?: number;
      validityDays?: number;
      autoGenerate?: boolean;
    };
    distributionSettings?: {
      method: KeyDistributionMethod;
      expiryHours?: number;
      maxDownloads?: number;
      notifyDevices?: boolean;
    };
  };
  
  // Security settings
  security?: {
    encryptionEnabled: boolean;
    keyRotationEnabled: boolean;
    rotationIntervalDays?: number;
    backupEnabled: boolean;
    escrowEnabled: boolean;
    auditLoggingEnabled: boolean;
  };
  
  // Device configuration
  tags: string[];
  config?: Record<string, any>;
}

/**
 * Public Key Validation Schema interface
 */
export interface PublicKeyValidationSchema {
  required: boolean;
  allowedFormats: Array<'PEM' | 'DER' | 'SSH' | 'JWK'>;
  allowedAlgorithms: KeyAlgorithm[];
  minKeySize: Record<string, number>; // Algorithm -> min key size
  maxKeySize: Record<string, number>; // Algorithm -> max key size
  maxFileSize: number; // bytes
  allowedExtensions: string[];
  requireValidSignature: boolean;
  allowExpiredKeys: boolean;
  maxValidityDays?: number;
  customValidation?: {
    requireKeyUsage?: string[];
    requireExtendedKeyUsage?: string[];
    allowSelfSigned?: boolean;
    requireCA?: boolean;
  };
}

/**
 * Form Validation Error interface for encryption operations
 */
export interface EncryptionFormError {
  field: string;
  message: string;
  code: string;
  severity: 'error' | 'warning' | 'info';
  suggestions?: string[];
  relatedFields?: string[];
}

/**
 * Form Validation State interface for encryption forms
 */
export interface EncryptionFormValidationState {
  isValid: boolean;
  isValidating: boolean;
  hasValidated: boolean;
  errors: EncryptionFormError[];
  warnings: EncryptionFormError[];
  fieldErrors: Record<string, string[]>;
  validatedFields: Set<string>;
  lastValidated?: Date;
}

/**
 * Encryption UI Props interface for component properties
 */
export interface EncryptionUIProps {
  formData: EnhancedCertificateFormData;
  uploadState: PublicKeyUploadState;
  validationState: EncryptionFormValidationState;
  validationSchema: PublicKeyValidationSchema;
  onFormDataChange: (data: EnhancedCertificateFormData) => void;
  onUploadStateChange: (state: PublicKeyUploadState) => void;
  onValidationChange: (state: EncryptionFormValidationState) => void;
  onFileUpload: (file: File) => Promise<void>;
  onKeyGeneration: (algorithm: KeyAlgorithm) => Promise<void>;
  onKeyDistribution: (settings: KeyDistributionRequest) => Promise<void>;
  disabled?: boolean;
  showAdvancedOptions?: boolean;
  allowKeyGeneration?: boolean;
  allowFileUpload?: boolean;
}

/**
 * Key Generation UI State interface
 */
export interface KeyGenerationUIState {
  status: EncryptionUIStatus;
  progress: number;
  algorithm?: KeyAlgorithm;
  keySize?: number;
  isGenerating: boolean;
  hasGenerated: boolean;
  generatedAt?: Date;
  keyId?: string;
  sessionId?: string;
  errors?: string[];
  warnings?: string[];
}

/**
 * Key Distribution UI State interface
 */
export interface KeyDistributionUIState {
  status: EncryptionUIStatus;
  progress: number;
  method?: KeyDistributionMethod;
  isDistributing: boolean;
  hasDistributed: boolean;
  distributedAt?: Date;
  distributionId?: string;
  downloadLinks?: Array<{
    deviceId: string;
    token: string;
    url: string;
    expiresAt: Date;
  }>;
  errors?: string[];
  warnings?: string[];
}
