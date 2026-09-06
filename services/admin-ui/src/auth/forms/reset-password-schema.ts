/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { z } from 'zod';

import { EMAIL_INVALID_MESSAGE, EMAIL_PATTERN } from '@/lib/email';

// Schema for requesting a password reset email
export const getResetRequestSchema = () => {
  return z.object({
    email: z
      .string()
      .regex(EMAIL_PATTERN, { message: EMAIL_INVALID_MESSAGE })
      .min(1, { message: 'Email is required.' }),
  });
};

// Schema for setting a new password
export const getNewPasswordSchema = () => {
  return z
    .object({
      password: z
        .string()
        .min(6, { message: 'Password must be at least 6 characters.' })
        .regex(/[A-Z]/, {
          message: 'Password must contain at least one uppercase letter.',
        })
        .regex(/[0-9]/, {
          message: 'Password must contain at least one number.',
        }),
      confirmPassword: z
        .string()
        .min(1, { message: 'Please confirm your password.' }),
    })
    .refine((data) => data.password === data.confirmPassword, {
      message: "Passwords don't match",
      path: ['confirmPassword'],
    });
};

export type ResetRequestSchemaType = z.infer<
  ReturnType<typeof getResetRequestSchema>
>;
export type NewPasswordSchemaType = z.infer<
  ReturnType<typeof getNewPasswordSchema>
>;
