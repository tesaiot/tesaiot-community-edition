/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

// Re-export all device types
export * from './device.types';

// Re-export all validation types
export * from './validation.types';

// Re-export all error types
export * from './error.types';

// Convenience type collections for specific use cases

/**
 * Types commonly used in CSR validation components
 */
export type CSRValidationTypes = {
  CSRDetails: import('./device.types').CSRDetails;
  CSRValidationResponse: import('./device.types').CSRValidationResponse;
  CSRValidationState: import('./device.types').CSRValidationState;
  CSRValidationStatus: import('./device.types').CSRValidationStatus;
  FieldValidationError: import('./validation.types').FieldValidationError;
  ValidationSeverity: import('./validation.types').ValidationSeverity;
  CSRValidationContext: import('./validation.types').CSRValidationContext;
};

/**
 * Types commonly used in certificate generation components
 */
export type CertificateGenerationTypes = {
  CertificateGenerationRequest: import('./device.types').CertificateGenerationRequest;
  CertificateGenerationResponse: import('./device.types').CertificateGenerationResponse;
  CertificateFormData: import('./device.types').CertificateFormData;
  CertificateGenerationMethod: import('./device.types').CertificateGenerationMethod;
  CertificateType: import('./device.types').CertificateType;
  CertificateFormat: import('./device.types').CertificateFormat;
  CertificateTemplate: import('./device.types').CertificateTemplate;
};

/**
 * Types commonly used in error handling
 */
export type ErrorHandlingTypes = {
  CSRCertificateError: import('./error.types').CSRCertificateError;
  ErrorCollection: import('./error.types').ErrorCollection;
  ErrorCategory: import('./error.types').ErrorCategory;
  ErrorSeverity: import('./error.types').ErrorSeverity;
  CSRErrorCodes: import('./error.types').CSRErrorCodes;
  CertificateErrorCodes: import('./error.types').CertificateErrorCodes;
  APIErrorCodes: import('./error.types').APIErrorCodes;
};

/**
 * Types commonly used in form validation
 */
export type FormValidationTypes = {
  FormValidationState: import('./validation.types').FormValidationState;
  ValidationConfiguration: import('./validation.types').ValidationConfiguration;
  ValidationHookOptions: import('./validation.types').ValidationHookOptions;
  CSRValidationRules: import('./validation.types').CSRValidationRules;
  CertificateFormValidationRules: import('./validation.types').CertificateFormValidationRules;
};

/**
 * All device-related types
 */
export type DeviceTypes = {
  Device: import('./device.types').Device;
  DeviceGroup: import('./device.types').DeviceGroup;
  DeviceType: import('./device.types').DeviceType;
  DeviceStatus: import('./device.types').DeviceStatus;
  DeviceProtocol: import('./device.types').DeviceProtocol;
  DeviceCertificateManagement: import('./device.types').DeviceCertificateManagement;
};

// Type utility functions

/**
 * Extract the union type of all CSR error codes
 */
export type AllCSRErrorCodes = 
  | import('./error.types').CSRErrorCodes
  | import('./error.types').CertificateErrorCodes
  | import('./error.types').APIErrorCodes
  | import('./validation.types').ValidationErrorCodes;

/**
 * Extract all enum values as a union type
 */
export type CertificateEnumValues = 
  | import('./device.types').CertificateGenerationMethod
  | import('./device.types').CertificateType
  | import('./device.types').CertificateFormat
  | import('./device.types').CertificateStatus;

/**
 * Extract all validation-related enum values
 */
export type ValidationEnumValues =
  | import('./validation.types').ValidationSeverity
  | import('./validation.types').ValidationErrorCodes
  | import('./device.types').CSRValidationStatus;

/**
 * Extract all error-related enum values
 */
export type ErrorEnumValues =
  | import('./error.types').ErrorCategory
  | import('./error.types').ErrorSeverity
  | import('./error.types').CSRErrorCodes
  | import('./error.types').CertificateErrorCodes
  | import('./error.types').APIErrorCodes;

// Component prop interfaces that use multiple type files

/**
 * Comprehensive props for certificate management components
 */
export interface CertificateManagementProps {
  device: import('./device.types').Device;
  formData: import('./device.types').CertificateFormData;
  validationState: import('./device.types').CSRValidationState;
  errors: import('./error.types').CSRCertificateError[];
  onFormChange: (data: import('./device.types').CertificateFormData) => void;
  onValidationChange: (state: import('./device.types').CSRValidationState) => void;
  onErrorReport: (errors: import('./error.types').CSRCertificateError[]) => void;
  disabled?: boolean;
  showAdvanced?: boolean;
}

/**
 * Props for CSR validation components
 */
export interface CSRValidationProps {
  csrContent: string;
  validationRules: import('./validation.types').CSRValidationRules;
  onValidationResult: (context: import('./validation.types').CSRValidationContext) => void;
  onError: (error: import('./error.types').CSRCertificateError) => void;
  debounceMs?: number;
  autoValidate?: boolean;
}

/**
 * Props for error display components
 */
export interface ErrorDisplayProps {
  errors: import('./error.types').CSRCertificateError[];
  showDetails?: boolean;
  showSuggestions?: boolean;
  onDismiss?: (errorCode: string) => void;
  onRetry?: (errorCode: string) => void;
  compact?: boolean;
}

/**
 * Hook return types for CSR/Certificate operations
 */
export interface UseCSRValidationReturn {
  validationState: import('./validation.types').CSRValidationContext;
  validateCSR: (content: string) => Promise<void>;
  clearValidation: () => void;
  isValidating: boolean;
  errors: import('./error.types').CSRCertificateError[];
}

export interface UseCertificateGenerationReturn {
  generateCertificate: (request: import('./device.types').CertificateGenerationRequest) => Promise<import('./device.types').CertificateGenerationResponse>;
  signCSR: (deviceId: string, csrContent: string, options?: any) => Promise<import('./device.types').CertificateGenerationResponse>;
  isGenerating: boolean;
  lastGenerated?: import('./device.types').CertificateGenerationResponse;
  errors: import('./error.types').CSRCertificateError[];
}

// Utility type helpers

/**
 * Make all certificate form fields optional for partial updates
 */
export type PartialCertificateFormData = Partial<import('./device.types').CertificateFormData>;

/**
 * Make all device fields optional except required ones
 */
export type DeviceCreateRequest = Omit<import('./device.types').Device, 'id' | 'lastSeen' | 'registeredAt'> & {
  id?: string;
  lastSeen?: Date | null;
  registeredAt?: Date;
};

/**
 * Extract only the error properties for logging
 */
export type ErrorLogEntry = Pick<
  import('./error.types').CSRCertificateError, 
  'code' | 'message' | 'category' | 'severity' | 'timestamp'
> & {
  context?: Partial<import('./error.types').ErrorContext>;
};

/**
 * Type for API response wrapper
 */
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  errors?: import('./error.types').CSRCertificateError[];
  warnings?: import('./error.types').CSRCertificateError[];
  metadata?: {
    timestamp: Date;
    requestId: string;
    version: string;
  };
}

// Re-export constants and utilities
export { 
  DEFAULT_CSR_VALIDATION_RULES,
  DEFAULT_CERTIFICATE_FORM_VALIDATION_RULES 
} from './validation.types';

export { 
  ERROR_MESSAGES,
  SEVERITY_WEIGHTS,
  DEFAULT_RECOVERY_CONFIG 
} from './error.types';

// Re-export type guards
export {
  isValidCertificateGenerationMethod,
  isValidCertificateType,
  isValidCertificateFormat,
  isValidCSRValidationStatus
} from './device.types';

export {
  isFieldValidationError,
  isCSRValidationContext,
  isFormValidationState
} from './validation.types';

export {
  isCSRCertificateError,
  isErrorCollection,
  isRetryableError
} from './error.types';