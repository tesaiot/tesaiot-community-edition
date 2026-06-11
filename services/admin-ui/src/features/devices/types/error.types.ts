/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { ValidationErrorCodes, ValidationSeverity } from './validation.types';

/**
 * Error categories for CSR and certificate operations
 */
export enum ErrorCategory {
  VALIDATION = 'validation',
  NETWORK = 'network',
  API = 'api',
  PARSING = 'parsing',
  FILE_UPLOAD = 'file_upload',
  CERTIFICATE_GENERATION = 'certificate_generation',
  CSR_PROCESSING = 'csr_processing',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  SYSTEM = 'system'
}

/**
 * Error severity levels extending validation severity
 */
export enum ErrorSeverity {
  CRITICAL = 'critical',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info'
}

/**
 * CSR-specific error codes
 */
export enum CSRErrorCodes {
  // Format errors
  INVALID_PEM_FORMAT = 'CSR_INVALID_PEM_FORMAT',
  MISSING_BEGIN_HEADER = 'CSR_MISSING_BEGIN_HEADER',
  MISSING_END_FOOTER = 'CSR_MISSING_END_FOOTER',
  MALFORMED_BASE64 = 'CSR_MALFORMED_BASE64',
  INVALID_ASN1_STRUCTURE = 'CSR_INVALID_ASN1_STRUCTURE',
  
  // Content errors
  EMPTY_CONTENT = 'CSR_EMPTY_CONTENT',
  FILE_TOO_LARGE = 'CSR_FILE_TOO_LARGE',
  UNSUPPORTED_VERSION = 'CSR_UNSUPPORTED_VERSION',
  INVALID_SIGNATURE = 'CSR_INVALID_SIGNATURE',
  
  // Key errors
  UNSUPPORTED_KEY_ALGORITHM = 'CSR_UNSUPPORTED_KEY_ALGORITHM',
  WEAK_KEY_SIZE = 'CSR_WEAK_KEY_SIZE',
  INVALID_PUBLIC_KEY = 'CSR_INVALID_PUBLIC_KEY',
  KEY_PARAMETER_MISMATCH = 'CSR_KEY_PARAMETER_MISMATCH',
  
  // Subject errors
  MISSING_COMMON_NAME = 'CSR_MISSING_COMMON_NAME',
  INVALID_SUBJECT_FORMAT = 'CSR_INVALID_SUBJECT_FORMAT',
  DUPLICATE_SUBJECT_FIELDS = 'CSR_DUPLICATE_SUBJECT_FIELDS',
  
  // Extension errors
  INVALID_EXTENSION = 'CSR_INVALID_EXTENSION',
  MALFORMED_SAN = 'CSR_MALFORMED_SAN',
  UNSUPPORTED_EXTENSION = 'CSR_UNSUPPORTED_EXTENSION',
  
  // Security errors
  SELF_SIGNED_NOT_ALLOWED = 'CSR_SELF_SIGNED_NOT_ALLOWED',
  WEAK_SIGNATURE_ALGORITHM = 'CSR_WEAK_SIGNATURE_ALGORITHM',
  EXPIRED_REQUEST = 'CSR_EXPIRED_REQUEST'
}

/**
 * Certificate generation error codes
 */
export enum CertificateErrorCodes {
  // Generation errors
  GENERATION_FAILED = 'CERT_GENERATION_FAILED',
  INVALID_TEMPLATE = 'CERT_INVALID_TEMPLATE',
  CA_UNAVAILABLE = 'CERT_CA_UNAVAILABLE',
  SIGNING_FAILED = 'CERT_SIGNING_FAILED',
  
  // Configuration errors
  INVALID_VALIDITY_PERIOD = 'CERT_INVALID_VALIDITY_PERIOD',
  UNSUPPORTED_ALGORITHM = 'CERT_UNSUPPORTED_ALGORITHM',
  INVALID_KEY_USAGE = 'CERT_INVALID_KEY_USAGE',
  INVALID_EXTENDED_KEY_USAGE = 'CERT_INVALID_EXTENDED_KEY_USAGE',
  
  // Policy errors
  POLICY_VIOLATION = 'CERT_POLICY_VIOLATION',
  QUOTA_EXCEEDED = 'CERT_QUOTA_EXCEEDED',
  RATE_LIMIT_EXCEEDED = 'CERT_RATE_LIMIT_EXCEEDED',
  
  // Storage errors
  STORAGE_FAILED = 'CERT_STORAGE_FAILED',
  RETRIEVAL_FAILED = 'CERT_RETRIEVAL_FAILED',
  
  // Revocation errors
  REVOCATION_FAILED = 'CERT_REVOCATION_FAILED',
  ALREADY_REVOKED = 'CERT_ALREADY_REVOKED',
  CANNOT_REVOKE = 'CERT_CANNOT_REVOKE'
}

/**
 * API error codes
 */
export enum APIErrorCodes {
  // HTTP errors
  BAD_REQUEST = 'API_BAD_REQUEST',
  UNAUTHORIZED = 'API_UNAUTHORIZED',
  FORBIDDEN = 'API_FORBIDDEN',
  NOT_FOUND = 'API_NOT_FOUND',
  CONFLICT = 'API_CONFLICT',
  INTERNAL_SERVER_ERROR = 'API_INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'API_SERVICE_UNAVAILABLE',
  
  // Network errors
  NETWORK_ERROR = 'API_NETWORK_ERROR',
  TIMEOUT = 'API_TIMEOUT',
  CONNECTION_REFUSED = 'API_CONNECTION_REFUSED',
  
  // Validation errors
  VALIDATION_FAILED = 'API_VALIDATION_FAILED',
  INVALID_PARAMETERS = 'API_INVALID_PARAMETERS',
  MISSING_PARAMETERS = 'API_MISSING_PARAMETERS',
  
  // Rate limiting
  RATE_LIMITED = 'API_RATE_LIMITED',
  QUOTA_EXCEEDED = 'API_QUOTA_EXCEEDED'
}

/**
 * Detailed error interface for CSR and certificate operations
 */
export interface CSRCertificateError {
  code: CSRErrorCodes | CertificateErrorCodes | APIErrorCodes | ValidationErrorCodes;
  message: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  field?: string; // Field that caused the error
  details?: Record<string, any>; // Additional error details
  suggestions?: string[]; // Suggested fixes
  timestamp: Date;
  context?: {
    operation: string; // e.g., 'csr_validation', 'certificate_generation'
    deviceId?: string;
    certificateId?: string;
    requestId?: string;
    userId?: string;
  };
  innerError?: Error; // Original error if wrapped
  retryable: boolean; // Whether the operation can be retried
  helpUrl?: string; // Link to documentation
}

/**
 * Error collection interface for multiple errors
 */
export interface ErrorCollection {
  errors: CSRCertificateError[];
  warnings: CSRCertificateError[];
  hasErrors: boolean;
  hasWarnings: boolean;
  errorCount: number;
  warningCount: number;
  mostSevere: ErrorSeverity;
  summary: string; // Human-readable summary
}

/**
 * Error context for operations
 */
export interface ErrorContext {
  operation: string;
  step?: string;
  deviceId?: string;
  certificateId?: string;
  userId?: string;
  sessionId?: string;
  requestId?: string;
  userAgent?: string;
  timestamp: Date;
  duration?: number; // Operation duration in ms
  metadata?: Record<string, any>;
}

/**
 * Error recovery suggestions interface
 */
export interface ErrorRecovery {
  canRetry: boolean;
  retryDelay?: number; // Suggested delay before retry in ms
  maxRetries?: number;
  autoRetry?: boolean;
  recoveryActions: Array<{
    action: string;
    description: string;
    automated: boolean;
    priority: number;
  }>;
  fallbackOptions?: string[];
}

/**
 * Error reporting interface
 */
export interface ErrorReport {
  error: CSRCertificateError;
  context: ErrorContext;
  recovery: ErrorRecovery;
  reported: boolean;
  reportedAt?: Date;
  reportId?: string;
  userFeedback?: string;
}

/**
 * Error handler interface
 */
export interface ErrorHandler {
  handleError(error: CSRCertificateError, context: ErrorContext): Promise<ErrorReport>;
  handleErrorCollection(collection: ErrorCollection, context: ErrorContext): Promise<ErrorReport[]>;
  canRecover(error: CSRCertificateError): boolean;
  suggestRecovery(error: CSRCertificateError): ErrorRecovery;
  reportError(report: ErrorReport): Promise<void>;
}

/**
 * Error factory interface for creating typed errors
 */
export interface ErrorFactory {
  createCSRError(
    code: CSRErrorCodes,
    message: string,
    details?: Record<string, any>
  ): CSRCertificateError;
  
  createCertificateError(
    code: CertificateErrorCodes,
    message: string,
    details?: Record<string, any>
  ): CSRCertificateError;
  
  createAPIError(
    code: APIErrorCodes,
    message: string,
    httpStatus?: number,
    details?: Record<string, any>
  ): CSRCertificateError;
  
  createValidationError(
    code: ValidationErrorCodes,
    field: string,
    message: string,
    suggestions?: string[]
  ): CSRCertificateError;
  
  wrapError(
    originalError: Error,
    code: string,
    context: ErrorContext
  ): CSRCertificateError;
}

/**
 * Error localization interface
 */
export interface ErrorLocalization {
  getMessage(code: string, locale?: string, params?: Record<string, any>): string;
  getSuggestions(code: string, locale?: string): string[];
  getHelpUrl(code: string, locale?: string): string;
}

/**
 * Error metrics interface for monitoring
 */
export interface ErrorMetrics {
  errorCount: number;
  errorsByCategory: Record<ErrorCategory, number>;
  errorsBySeverity: Record<ErrorSeverity, number>;
  errorsByCode: Record<string, number>;
  averageResolutionTime: number;
  retrySuccessRate: number;
  userReportedErrors: number;
  timeRange: {
    start: Date;
    end: Date;
  };
}

/**
 * Pre-defined error messages for common scenarios
 */
export const ERROR_MESSAGES = {
  CSR: {
    INVALID_FORMAT: 'The CSR format is invalid. Please ensure it\'s a valid PEM-encoded certificate request.',
    MISSING_HEADERS: 'CSR is missing required headers. It should start with "-----BEGIN CERTIFICATE REQUEST-----".',
    WEAK_KEY: 'The key size is too small for security requirements. Please use at least 2048 bits for RSA or 256 bits for ECC.',
    INVALID_SIGNATURE: 'The CSR signature is invalid. Please regenerate the CSR with the correct private key.',
    MISSING_CN: 'Common Name (CN) will be replaced by platform-generated device_id.',
    FILE_TOO_LARGE: 'CSR file is too large. Please ensure the file is under 10KB.'
  },
  CERTIFICATE: {
    GENERATION_FAILED: 'Certificate generation failed. Please try again or contact support.',
    CA_UNAVAILABLE: 'Certificate Authority is temporarily unavailable. Please try again later.',
    INVALID_VALIDITY: 'Invalid validity period. Must be between 1 and 3650 days.',
    QUOTA_EXCEEDED: 'Certificate quota exceeded. Please contact your administrator.',
    POLICY_VIOLATION: 'Certificate request violates organizational policies.'
  },
  API: {
    NETWORK_ERROR: 'Network connection failed. Please check your internet connection and try again.',
    TIMEOUT: 'Request timed out. The server may be under heavy load.',
    UNAUTHORIZED: 'Authentication failed. Please sign in again.',
    FORBIDDEN: 'You don\'t have permission to perform this action.',
    SERVER_ERROR: 'Internal server error. Please try again later or contact support.'
  }
} as const;

/**
 * Error severity weights for priority calculation
 */
export const SEVERITY_WEIGHTS = {
  [ErrorSeverity.CRITICAL]: 1000,
  [ErrorSeverity.ERROR]: 100,
  [ErrorSeverity.WARNING]: 10,
  [ErrorSeverity.INFO]: 1
} as const;

/**
 * Default error recovery configurations
 */
export const DEFAULT_RECOVERY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000, // 1 second
  maxDelay: 30000, // 30 seconds
  backoffMultiplier: 2,
  retryableCategories: [
    ErrorCategory.NETWORK,
    ErrorCategory.API,
    ErrorCategory.SYSTEM
  ],
  nonRetryableCategories: [
    ErrorCategory.VALIDATION,
    ErrorCategory.AUTHENTICATION,
    ErrorCategory.AUTHORIZATION
  ]
} as const;

/**
 * Type guards for error types
 */
export const isCSRCertificateError = (error: any): error is CSRCertificateError => {
  return error && 
    typeof error.code === 'string' &&
    typeof error.message === 'string' &&
    Object.values(ErrorCategory).includes(error.category) &&
    Object.values(ErrorSeverity).includes(error.severity) &&
    error.timestamp instanceof Date &&
    typeof error.retryable === 'boolean';
};

export const isErrorCollection = (value: any): value is ErrorCollection => {
  return value &&
    Array.isArray(value.errors) &&
    Array.isArray(value.warnings) &&
    typeof value.hasErrors === 'boolean' &&
    typeof value.hasWarnings === 'boolean' &&
    typeof value.errorCount === 'number' &&
    typeof value.warningCount === 'number';
};

export const isRetryableError = (error: CSRCertificateError): boolean => {
  return error.retryable && 
    DEFAULT_RECOVERY_CONFIG.retryableCategories.includes(error.category);
};

/**
 * Error utility functions
 */
export const createErrorFromHttpResponse = (
  response: Response,
  message?: string
): CSRCertificateError => {
  let code: APIErrorCodes;
  let category = ErrorCategory.API;
  let severity = ErrorSeverity.ERROR;

  switch (response.status) {
    case 400:
      code = APIErrorCodes.BAD_REQUEST;
      break;
    case 401:
      code = APIErrorCodes.UNAUTHORIZED;
      category = ErrorCategory.AUTHENTICATION;
      break;
    case 403:
      code = APIErrorCodes.FORBIDDEN;
      category = ErrorCategory.AUTHORIZATION;
      break;
    case 404:
      code = APIErrorCodes.NOT_FOUND;
      break;
    case 409:
      code = APIErrorCodes.CONFLICT;
      break;
    case 429:
      code = APIErrorCodes.RATE_LIMITED;
      severity = ErrorSeverity.WARNING;
      break;
    case 500:
      code = APIErrorCodes.INTERNAL_SERVER_ERROR;
      severity = ErrorSeverity.CRITICAL;
      break;
    case 503:
      code = APIErrorCodes.SERVICE_UNAVAILABLE;
      break;
    default:
      code = APIErrorCodes.INTERNAL_SERVER_ERROR;
      severity = ErrorSeverity.CRITICAL;
  }

  return {
    code,
    message: message || `HTTP ${response.status}: ${response.statusText}`,
    category,
    severity,
    timestamp: new Date(),
    retryable: [500, 502, 503, 504, 429].includes(response.status),
    details: {
      httpStatus: response.status,
      statusText: response.statusText,
      url: response.url
    }
  };
};

export const aggregateErrors = (errors: CSRCertificateError[]): ErrorCollection => {
  const warnings = errors.filter(e => e.severity === ErrorSeverity.WARNING || e.severity === ErrorSeverity.INFO);
  const actualErrors = errors.filter(e => e.severity === ErrorSeverity.ERROR || e.severity === ErrorSeverity.CRITICAL);
  
  const severities = errors.map(e => e.severity);
  const mostSevere = severities.includes(ErrorSeverity.CRITICAL) ? ErrorSeverity.CRITICAL :
                    severities.includes(ErrorSeverity.ERROR) ? ErrorSeverity.ERROR :
                    severities.includes(ErrorSeverity.WARNING) ? ErrorSeverity.WARNING :
                    ErrorSeverity.INFO;

  return {
    errors: actualErrors,
    warnings,
    hasErrors: actualErrors.length > 0,
    hasWarnings: warnings.length > 0,
    errorCount: actualErrors.length,
    warningCount: warnings.length,
    mostSevere,
    summary: actualErrors.length > 0 ? 
      `${actualErrors.length} error${actualErrors.length > 1 ? 's' : ''} found` :
      warnings.length > 0 ?
      `${warnings.length} warning${warnings.length > 1 ? 's' : ''} found` :
      'No issues found'
  };
};