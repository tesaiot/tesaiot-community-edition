/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 *
 * The Community Edition ships a single edition without the demo store-client
 * module, so this provider is a transparent passthrough.
 */

import { ReactNode } from 'react';

export function ModulesProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
