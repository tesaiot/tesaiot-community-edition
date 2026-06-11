/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Settings } from './types';

export const APP_SETTINGS: Settings = {
  layout: '',
  container: 'fixed',
  layouts: {
    demo1: {
      sidebarCollapse: false,
      sidebarTheme: 'light',
    },
    demo2: {
      headerSticky: true,
      headerStickyOffset: 200,
    },
    demo5: {
      headerSticky: true,
      headerStickyOffset: 200,
    },
    demo7: {
      headerSticky: true,
      headerStickyOffset: 200,
    },
    demo9: {
      headerSticky: true,
      headerStickyOffset: 200,
    },
  },
};
