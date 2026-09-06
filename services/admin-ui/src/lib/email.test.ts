/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Regression guard. `admin@localhost` is not a curiosity — it is the address
 * generate-secrets.sh writes into .env on every install that does not pass
 * --domain, and the one install.sh prints as the bootstrap login. A validator
 * that rejects it locks the operator out of a brand-new install, which is what
 * happened before this file existed.
 */

import { describe, expect, it } from 'vitest';

import { getSigninSchema } from '@/auth/forms/signin-schema';
import { EMAIL_PATTERN, isValidEmail } from '@/lib/email';

const INSTALLER_ISSUED = [
  'admin@localhost', // DOMAIN unset -> the default install
  'bridge@localhost', // BRIDGE_API_USER, same derivation
  'admin@iot.acme.com', // make install DOMAIN=iot.acme.com
  'admin@tesa-api', // a container name, reachable inside the compose network
];

const ORDINARY = ['user@example.com', 'first.last+tag@sub.example.co.uk'];

const NOT_EMAILS = [
  '',
  'admin',
  'admin@',
  '@localhost',
  'admin @localhost',
  'admin@local host',
  'admin@@localhost',
];

describe('isValidEmail', () => {
  it.each(INSTALLER_ISSUED)('accepts what the installer issues: %s', (v) => {
    expect(isValidEmail(v)).toBe(true);
  });

  it.each(ORDINARY)('accepts ordinary addresses: %s', (v) => {
    expect(isValidEmail(v)).toBe(true);
  });

  it.each(NOT_EMAILS)('rejects %j', (v) => {
    expect(isValidEmail(v)).toBe(false);
  });

  it('is anchored at both ends', () => {
    expect(EMAIL_PATTERN.test('x admin@localhost')).toBe(false);
    expect(EMAIL_PATTERN.test('admin@localhost y')).toBe(false);
  });
});

describe('the sign-in form accepts the credentials install.sh prints', () => {
  it.each(INSTALLER_ISSUED)('%s', (email) => {
    const result = getSigninSchema().safeParse({
      email,
      password: 'whatever-the-installer-generated',
      rememberMe: false,
    });
    expect(result.success).toBe(true);
  });

  it('still rejects a non-address', () => {
    const result = getSigninSchema().safeParse({
      email: 'not-an-address',
      password: 'x',
      rememberMe: false,
    });
    expect(result.success).toBe(false);
  });
});
