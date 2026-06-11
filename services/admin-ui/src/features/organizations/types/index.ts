/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

export interface Organization {
  id: string;
  organization_id?: string;
  name: string;
  description?: string;
  plan: 'community' | 'starter' | 'business' | 'enterprise';
  status: 'active' | 'trial' | 'suspended' | 'inactive';
  
  // Contact information
  contact: {
    name: string;
    email: string;
    phone?: string;
  };
  
  // Address information
  address?: {
    street: string;
    city: string;
    country: string;
    postalCode: string;
  };
  
  // PKI configuration
  pki: {
    enabled: boolean;
    type?: 'shared' | 'dedicated' | 'hsm';
    caId?: string;
    settings?: PKISettings;
  };
  
  // Billing information (optional for trials)
  billing?: {
    plan: string;
    price: number;
    billingCycle: 'monthly' | 'yearly';
    nextBillingDate?: Date;
  };
  
  // Important dates
  createdAt: Date;
  expiresAt: Date;
  
  // Usage metrics
  usage: {
    devices: number;
    users: number;
    certificates?: number;
    apiCalls: number;
    storage: number; // in GB
  };
  
  // Plan limits (-1 means unlimited)
  limits: {
    devices: number;
    users: number;
    certificates?: number;
    apiCalls: number;
    storage: number; // in GB
  };
  
  // Additional PKI service configuration
  pkiService?: {
    enabled: boolean;
    caType: 'root' | 'intermediate' | 'subordinate';
    validityPeriod: number; // in days
  };
  
  // Direct count fields from API (v2.5.5 addition)
  device_count?: number;
  user_count?: number;
  api_calls?: number;
  sub_organizations_count?: number;
  
  // Hierarchy fields for sub-organizations
  parent_id?: string;
  type?: string;
  depth?: number;
}

/**
 * PKI Settings for an organization
 */
export interface PKISettings {
  commonName: string;
  validityPeriod: number; // in days
  keyAlgorithm: 'RSA-2048' | 'RSA-4096' | 'ECC-P256' | 'ECC-P384';
  allowedDeviceTypes: string[];
  autoRenewalEnabled: boolean;
  autoRenewalDays: number;
}

/**
 * Form data for creating a new organization
 */
export interface OrganizationFormData {
  name: string;
  description?: string;
  plan: string;
  contact: {
    name: string;
    email: string;
    phone?: string;
  };
  billing?: {
    plan: string;
    billingCycle: 'monthly' | 'yearly';
  };
}

/**
 * PKI Service configuration request
 */
export interface PKIServiceRequest {
  type: 'shared' | 'dedicated' | 'hsm';
  settings: PKISettings;
}

/**
 * Organization statistics
 */
export interface OrganizationStats {
  total: number;
  active: number;
  trial: number;
  suspended: number;
}

/**
 * Organization administrator
 */
export interface OrganizationAdmin {
  id: string;
  name: string;
  email: string;
  role: string;
  status: 'active' | 'inactive';
  lastLogin: string;
  permissions: string[];
}