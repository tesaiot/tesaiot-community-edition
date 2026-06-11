/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { AxiosError } from 'axios';
import type { ApiError } from '../types/common.api.types';

/**
 * Handle API errors and convert to standard format
 */
export function handleApiError(error: unknown, defaultMessage: string): Error {
  if (error instanceof AxiosError) {
    const apiError = error.response?.data as ApiError | undefined;
    const message = apiError?.message || error.message || defaultMessage;
    const errorObj = new Error(message);
    (errorObj as any).code = apiError?.code;
    (errorObj as any).status = error.response?.status;
    return errorObj;
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error(defaultMessage);
}
