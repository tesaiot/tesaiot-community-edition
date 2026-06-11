/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { type MessageFormatElement } from 'react-intl';

export type LanguageCode = 'en' | 'fr' | 'ar' | 'zh';

export type LanguageDirection = 'ltr' | 'rtl';

export interface Language {
  label: string;
  code: LanguageCode;
  direction: LanguageDirection;
  flag: string;
  messages: Record<string, string> | Record<string, MessageFormatElement[]>;
}

export interface I18nProviderProps {
  currenLanguage: Language;
  isRTL: () => boolean;

  changeLanguage: (lang: Language) => void;
}
