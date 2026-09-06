/*
 * TESAIoT Community Edition
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 */

import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import globals from 'globals';
import tseslint from 'typescript-eslint';

// Clean up globals by removing entries with whitespace
const cleanGlobals = Object.fromEntries(
  Object.entries(globals.browser).map(([key, value]) => [key.trim(), value]),
);

export default tseslint.config(
  { ignores: ['dist'] },
  {
    extends: [...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: cleanGlobals,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,

      // ═══════════════════════════════════════════════════════════════════════
      // CUSTOM IMPORT PATH VALIDATION RULES
      // Added: 2025-10-02 - Prevent import path errors during modularization
      // ═══════════════════════════════════════════════════════════════════════

      // Enforce path aliases (@/) for deep cross-feature imports
      'no-restricted-imports': ['error', {
        patterns: [
          {
            group: ['../../../*', '../../../../*'],
            message: 'Use path aliases (@/) instead of deep relative imports. Example: @/features/devices/types'
          }
        ]
      }],

      // ═══════════════════════════════════════════════════════════════════════
      // `any` IS A WARNING, AND THE COUNT IS RATCHETED
      // ═══════════════════════════════════════════════════════════════════════
      // There are 899 of these. While the rule was an error, `npx eslint src`
      // exited 1, the Build admin UI job died at its Lint step, and the two
      // steps after it — tsc and vite build — never ran at all. So the job that
      // exists to prove the UI still builds proved nothing, for every commit
      // since the rule started failing.
      //
      // Downgrading it does not forgive the 899: CI counts them and fails if the
      // number grows (see .eslint-any-baseline and the ratchet step in ci.yml).
      // New code cannot add one, existing code can be typed properly a file at a
      // time, and the build is verified again in the meantime. Removing them is
      // a typing effort, not a cleanup — 899 call sites is its own work package.
      '@typescript-eslint/no-explicit-any': 'warn',

      // Warn about potential case-sensitive import issues
      '@typescript-eslint/no-unused-vars': ['warn', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
      }],
    },
  },

  // ═══════════════════════════════════════════════════════════════════════
  // SPECIAL RULES: Sensor Modules Exception
  // Note: Sensor modules (sensorCatalog/sensors/*.ts) REQUIRE deep imports
  // They are exempt from the deep import rule and validated by validate-imports.sh
  // ═══════════════════════════════════════════════════════════════════════
  {
    files: ['src/features/devices/services/sensorCatalog/sensors/*.ts'],
    rules: {
      // Disable deep import warning for sensor modules (they need ../../../)
      'no-restricted-imports': 'off',
    },
  },
);
