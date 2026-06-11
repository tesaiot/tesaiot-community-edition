/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/// <reference types="vite/client" />

declare const __BUILD_TIME__: string;
declare const __GIT_COMMIT__: string;
declare const __APP_VERSION__: string;

interface ImportMetaEnv {
  readonly VITE_APP_TITLE: string
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_NOTIFICATIONS_WS_ENABLED?: string
  // more env variables...
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
