/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

'use client';

import { useEffect } from 'react';

export function useBodyClass(className: string) {
  useEffect(() => {
    // Split classNames by spaces, including multi-line support
    const classList = className.split(/\s+/).filter(Boolean);

    // Add each class to the body element when the component mounts
    classList.forEach((className) => {
      document.body.classList.add(className);
    });

    // Cleanup function to remove classes when the component unmounts
    return () => {
      classList.forEach((className) => {
        document.body.classList.remove(className);
      });
    };
  }, [className]); // Re-run the effect if classNames changes
}
