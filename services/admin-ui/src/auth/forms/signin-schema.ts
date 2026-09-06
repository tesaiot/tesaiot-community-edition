/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { z } from 'zod';

import { EMAIL_INVALID_MESSAGE, EMAIL_PATTERN } from '@/lib/email';

export const getSigninSchema = () => {
  return z.object({
    email: z
      .string()
      .regex(EMAIL_PATTERN, { message: EMAIL_INVALID_MESSAGE })
      .min(1, { message: 'Email is required.' }),
    password: z.string().min(1, { message: 'Password is required.' }),
    rememberMe: z.boolean().optional(),
  });
};

export type SigninSchemaType = z.infer<ReturnType<typeof getSigninSchema>>;
