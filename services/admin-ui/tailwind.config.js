/*
 * TESAIoT Community Edition
 * SPDX-License-Identifier: Apache-2.0
 * Copyright TESAIoT Platform contributors
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      gridTemplateColumns: {
        // Ensure all grid column variations are available
        '1': 'repeat(1, minmax(0, 1fr))',
        '2': 'repeat(2, minmax(0, 1fr))',
        '3': 'repeat(3, minmax(0, 1fr))',
        '4': 'repeat(4, minmax(0, 1fr))',
        '5': 'repeat(5, minmax(0, 1fr))',
        '6': 'repeat(6, minmax(0, 1fr))',
      }
    },
  },
  plugins: [],
  // Safelist to ensure these classes are always included
  safelist: [
    // Grid classes
    'grid-cols-1',
    'grid-cols-2',
    'grid-cols-3',
    'grid-cols-4',
    'grid-cols-5',
    'sm:grid-cols-1',
    'sm:grid-cols-2',
    'sm:grid-cols-3',
    'md:grid-cols-1',
    'md:grid-cols-2',
    'md:grid-cols-3',
    'md:grid-cols-4',
    'lg:grid-cols-1',
    'lg:grid-cols-2',
    'lg:grid-cols-3',
    'lg:grid-cols-4',
    'lg:grid-cols-5',
    'xl:grid-cols-1',
    'xl:grid-cols-2',
    'xl:grid-cols-3',
    'xl:grid-cols-4',
    'xl:grid-cols-5',
    '2xl:grid-cols-1',
    '2xl:grid-cols-2',
    '2xl:grid-cols-3',
    '2xl:grid-cols-4',
    '2xl:grid-cols-5',
    // Width utilities
    'w-full',
    'min-w-0',
    'max-w-full',
    'max-w-5xl',
    // Flex utilities
    'flex-1',
    'flex-grow',
    'flex-shrink-0',
    // Overflow utilities
    'overflow-visible',
    'overflow-hidden',
    'overflow-auto',
  ]
}