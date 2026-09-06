/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * The one place this UI decides what an e-mail address looks like.
 *
 * Why this exists: the default install creates its bootstrap operator as
 * `admin@localhost` — generate-secrets.sh derives `admin@${DOMAIN}` and DOMAIN
 * defaults to `localhost`. A validator that demands a dot in the domain
 * therefore rejects the only credentials `install.sh` prints, and the operator
 * is locked out of the UI on a brand-new install. The API accepts the address;
 * so does the browser. Only the form disagreed, and it disagreed in three
 * different ways: zod's .email() (needs a TLD), a local /.+@.+\..+/ in two
 * files (needs a dot), and a looser /.+@.+/ in the setup wizard (does not) —
 * so the wizard accepted an address the sign-in page then refused.
 *
 * The pattern below is the WHATWG "valid e-mail address" definition, which is
 * exactly what the browser already enforces on <input type="email">. Using it
 * means the form never disagrees with the control it renders, with the API, or
 * with the installer. Single-label domains (localhost, a container name, an
 * internal host) are valid, as RFC 5321 has always allowed.
 */

export const EMAIL_PATTERN =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

export const EMAIL_INVALID_MESSAGE = 'Please enter a valid email address.';

export const isValidEmail = (value: string): boolean =>
  EMAIL_PATTERN.test(value);
