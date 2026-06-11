/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import {
  CertificateGenerationMethod,
  CertificateType,
  CertificateFormat,
  CSRValidationStatus,
  CSRDetails
} from './device.types';

/**
 * Validation error severity levels
 */
export enum ValidationSeverity {
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

/**
 * Field validation error interface
 */
export interface FieldValidationError {
  field: string;
  message: string;
  severity: ValidationSeverity;
  code?: string;
  suggestions?: string[];
}

/**
 * CSR content validation rules
 */
export interface CSRValidationRules {
  maxSize: number; // Maximum file size in bytes
  allowedHeaders: string[]; // Allowed PEM headers
  requiredSubjectFields: string[]; // Required subject fields (CN, O, etc.)
  allowedKeyAlgorithms: string[]; // Allowed key algorithms
  minKeySize: number; // Minimum key size
  maxKeySize: number; // Maximum key size
  allowedSignatureAlgorithms: string[]; // Allowed signature algorithms
  requireValidSignature: boolean;
  allowSelfSigned: boolean;
}

/**
 * Certificate form validation rules
 */
export interface CertificateFormValidationRules {
  generationMethod: {
    required: boolean;
    allowedMethods: CertificateGenerationMethod[];
  };
  certificateType: {
    required: boolean;
    allowedTypes: CertificateType[];
    defaultType: CertificateType;
  };
  certificateFormat: {
    required: boolean;
    allowedFormats: CertificateFormat[];
    defaultFormat: CertificateFormat;
  };
  validityDays: {
    min: number;
    max: number;
    default: number;
  };
  csrContent: {
    required: boolean;
    validationRules: CSRValidationRules;
  };
  keyUsage: {
    allowedValues: string[];
    defaultValues: string[];
  };
  extendedKeyUsage: {
    allowedValues: string[];
    defaultValues: string[];
  };
  subjectAltNames: {
    maxCount: number;
    allowedTypes: string[]; // DNS, IP, EMAIL, URI
    validation: {
      dns: RegExp;
      ip: RegExp;
      email: RegExp;
      uri: RegExp;
    };
  };
}

/**
 * Form validation state interface
 */
export interface FormValidationState {
  isValid: boolean;
  hasErrors: boolean;
  hasWarnings: boolean;
  errors: FieldValidationError[];
  warnings: FieldValidationError[];
  touchedFields: Set<string>;
  validatedFields: Set<string>;
}

/**
 * CSR validation context interface
 */
export interface CSRValidationContext {
  status: CSRValidationStatus;
  isValidating: boolean;
  lastValidated?: Date;
  validationDuration?: number; // milliseconds
  errors: FieldValidationError[];
  warnings: FieldValidationError[];
  details?: CSRDetails;
  rawContent?: string;
  normalizedContent?: string;
}

/**
 * Field validation result interface
 */
export interface FieldValidationResult {
  isValid: boolean;
  errors: FieldValidationError[];
  warnings: FieldValidationError[];
  normalizedValue?: any;
  metadata?: Record<string, any>;
}

/**
 * Form validation configuration interface
 */
export interface ValidationConfiguration {
  rules: CertificateFormValidationRules;
  enableRealTimeValidation: boolean;
  debounceMs: number;
  validateOnBlur: boolean;
  validateOnChange: boolean;
  showWarnings: boolean;
  strictMode: boolean; // More rigorous validation
}

/**
 * Validation hook options interface
 */
export interface ValidationHookOptions {
  configuration: ValidationConfiguration;
  onValidationChange?: (state: FormValidationState) => void;
  onCSRValidationChange?: (context: CSRValidationContext) => void;
  onFieldValidation?: (field: string, result: FieldValidationResult) => void;
}

/**
 * CSR file validation result interface
 */
export interface CSRFileValidationResult {
  isValid: boolean;
  fileName: string;
  fileSize: number;
  mimeType: string;
  encoding: string;
  content: string;
  errors: FieldValidationError[];
  warnings: FieldValidationError[];
  metadata: {
    uploadedAt: Date;
    source: 'file' | 'paste';
    hasValidHeaders: boolean;
    hasValidFooters: boolean;
    lineCount: number;
    characterCount: number;
  };
}

/**
 * Validation async operation interface
 */
export interface AsyncValidationOperation {
  id: string;
  field: string;
  operation: 'csr-validation' | 'field-validation' | 'remote-validation';
  status: 'pending' | 'in-progress' | 'completed' | 'failed' | 'cancelled';
  startTime: Date;
  endTime?: Date;
  duration?: number;
  result?: FieldValidationResult | CSRValidationContext;
  error?: Error;
}

/**
 * Validation cache interface for performance optimization
 */
export interface ValidationCache {
  csr: Map<string, CSRValidationContext>; // CSR content hash -> validation result
  fields: Map<string, FieldValidationResult>; // field+value hash -> validation result
  ttl: number; // Time to live in milliseconds
  maxSize: number; // Maximum cache size
}

/**
 * Validation utility functions type definitions
 */
export interface ValidationUtilities {
  validateCSRFormat: (content: string) => FieldValidationResult;
  validateCSRHeaders: (content: string) => FieldValidationResult;
  validatePEMStructure: (content: string) => FieldValidationResult;
  extractCSRInfo: (content: string) => Partial<CSRDetails> | null;
  normalizeCSRContent: (content: string) => string;
  validateSubjectField: (field: string, value: string) => FieldValidationResult;
  validateKeyUsage: (usage: string[]) => FieldValidationResult;
  validateExtendedKeyUsage: (usage: string[]) => FieldValidationResult;
  validateSubjectAltName: (type: string, value: string) => FieldValidationResult;
  sanitizeInput: (input: string, rules?: any) => string;
  generateFieldHash: (field: string, value: any) => string;
  generateCSRHash: (content: string) => string;
}

/**
 * Default validation rules constants
 */
export const DEFAULT_CSR_VALIDATION_RULES: CSRValidationRules = {
  maxSize: 10240, // 10KB
  allowedHeaders: [
    '-----BEGIN CERTIFICATE REQUEST-----',
    '-----BEGIN NEW CERTIFICATE REQUEST-----'
  ],
  requiredSubjectFields: ['CN'], // Common Name is required
  allowedKeyAlgorithms: ['RSA', 'ECDSA', 'EC'],
  minKeySize: 2048,
  maxKeySize: 8192,
  allowedSignatureAlgorithms: [
    'sha256WithRSAEncryption',
    'sha384WithRSAEncryption',
    'sha512WithRSAEncryption',
    'ecdsa-with-SHA256',
    'ecdsa-with-SHA384',
    'ecdsa-with-SHA512'
  ],
  requireValidSignature: true,
  allowSelfSigned: false
};

export const DEFAULT_CERTIFICATE_FORM_VALIDATION_RULES: CertificateFormValidationRules = {
  generationMethod: {
    required: true,
    allowedMethods: [
      CertificateGenerationMethod.AUTO_GENERATE,
      CertificateGenerationMethod.UPLOAD_CSR
    ]
  },
  certificateType: {
    required: true,
    allowedTypes: Object.values(CertificateType),
    defaultType: CertificateType.AUTO
  },
  certificateFormat: {
    required: true,
    allowedFormats: Object.values(CertificateFormat),
    defaultFormat: CertificateFormat.PEM
  },
  validityDays: {
    min: 1,
    max: 3650, // 10 years
    default: 365 // 1 year
  },
  csrContent: {
    required: true, // Only when upload-csr method is selected
    validationRules: DEFAULT_CSR_VALIDATION_RULES
  },
  keyUsage: {
    allowedValues: [
      'digitalSignature',
      'nonRepudiation',
      'keyEncipherment',
      'dataEncipherment',
      'keyAgreement',
      'keyCertSign',
      'cRLSign',
      'encipherOnly',
      'decipherOnly'
    ],
    defaultValues: ['digitalSignature', 'keyEncipherment']
  },
  extendedKeyUsage: {
    allowedValues: [
      'serverAuth',
      'clientAuth',
      'codeSigning',
      'emailProtection',
      'timeStamping',
      'OCSPSigning',
      'msCodeInd',
      'msCodeCom',
      'mcodeind',
      'ipsecEndSystem',
      'ipsecTunnel',
      'ipsecUser'
    ],
    defaultValues: ['clientAuth']
  },
  subjectAltNames: {
    maxCount: 10,
    allowedTypes: ['DNS', 'IP', 'EMAIL', 'URI'],
    validation: {
      dns: /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/,
      ip: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/,
      email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
      uri: /^[a-zA-Z][a-zA-Z0-9+.-]*:/
    }
  }
};

/**
 * Validation error codes enum
 */
export enum ValidationErrorCodes {
  // CSR validation errors
  CSR_INVALID_FORMAT = 'CSR_INVALID_FORMAT',
  CSR_INVALID_HEADERS = 'CSR_INVALID_HEADERS',
  CSR_INVALID_SIGNATURE = 'CSR_INVALID_SIGNATURE',
  CSR_UNSUPPORTED_ALGORITHM = 'CSR_UNSUPPORTED_ALGORITHM',
  CSR_KEY_SIZE_TOO_SMALL = 'CSR_KEY_SIZE_TOO_SMALL',
  CSR_KEY_SIZE_TOO_LARGE = 'CSR_KEY_SIZE_TOO_LARGE',
  CSR_MISSING_SUBJECT_FIELD = 'CSR_MISSING_SUBJECT_FIELD',
  CSR_INVALID_SUBJECT_FIELD = 'CSR_INVALID_SUBJECT_FIELD',
  CSR_FILE_TOO_LARGE = 'CSR_FILE_TOO_LARGE',
  CSR_EMPTY_CONTENT = 'CSR_EMPTY_CONTENT',
  
  // Form validation errors
  FIELD_REQUIRED = 'FIELD_REQUIRED',
  FIELD_INVALID_VALUE = 'FIELD_INVALID_VALUE',
  FIELD_OUT_OF_RANGE = 'FIELD_OUT_OF_RANGE',
  FIELD_INVALID_FORMAT = 'FIELD_INVALID_FORMAT',
  FIELD_TOO_LONG = 'FIELD_TOO_LONG',
  FIELD_TOO_SHORT = 'FIELD_TOO_SHORT',
  
  // Certificate generation errors
  CERT_INVALID_TYPE = 'CERT_INVALID_TYPE',
  CERT_INVALID_FORMAT = 'CERT_INVALID_FORMAT',
  CERT_INVALID_VALIDITY = 'CERT_INVALID_VALIDITY',
  CERT_INVALID_KEY_USAGE = 'CERT_INVALID_KEY_USAGE',
  CERT_INVALID_EXTENDED_KEY_USAGE = 'CERT_INVALID_EXTENDED_KEY_USAGE',
  CERT_INVALID_SUBJECT_ALT_NAME = 'CERT_INVALID_SUBJECT_ALT_NAME',
  
  // API errors
  API_VALIDATION_FAILED = 'API_VALIDATION_FAILED',
  API_TIMEOUT = 'API_TIMEOUT',
  API_NETWORK_ERROR = 'API_NETWORK_ERROR',
  API_SERVER_ERROR = 'API_SERVER_ERROR'
}

/**
 * Type guard functions for validation types
 */
export const isFieldValidationError = (value: any): value is FieldValidationError => {
  return value && 
    typeof value.field === 'string' && 
    typeof value.message === 'string' && 
    Object.values(ValidationSeverity).includes(value.severity);
};

export const isCSRValidationContext = (value: any): value is CSRValidationContext => {
  return value && 
    Object.values(CSRValidationStatus).includes(value.status) &&
    typeof value.isValidating === 'boolean' &&
    Array.isArray(value.errors) &&
    Array.isArray(value.warnings);
};

export const isFormValidationState = (value: any): value is FormValidationState => {
  return value &&
    typeof value.isValid === 'boolean' &&
    typeof value.hasErrors === 'boolean' &&
    typeof value.hasWarnings === 'boolean' &&
    Array.isArray(value.errors) &&
    Array.isArray(value.warnings);
};