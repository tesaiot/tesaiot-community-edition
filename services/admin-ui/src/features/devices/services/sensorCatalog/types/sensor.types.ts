/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Core type definitions for sensor catalog system
 * Extracted from sensorCatalog.ts for better modularity
 */

import { RJSFSchema, UiSchema } from '@rjsf/utils';
import React from 'react';

export interface SensorTemplate {
  id: string;
  name: string;
  category: string;
  subcategory?: string;
  description: string;
  manufacturer?: string;
  tags: string[];
  icon?: React.FC<any> | null;
  schema: RJSFSchema;
  uiSchema: UiSchema;
  exampleData?: Record<string, any>;
  units?: Record<string, string>;
  ranges?: Record<string, { min: number; max: number }>;
  accuracy?: Record<string, number>;
  standards?: string[];
  datasheet?: string;
}

export interface SensorCategory {
  id: string;
  name: string;
  description: string;
  icon: React.FC<any> | null;
  sensors: SensorTemplate[];
}
