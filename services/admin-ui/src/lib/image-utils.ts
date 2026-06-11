/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Safely get image source, preventing [object Object] errors
 */
export function safeImageSrc(src: any): string | undefined {
  if (!src) return undefined;
  
  // If it's already a string, return it
  if (typeof src === 'string') {
    // Check if it's not [object Object]
    if (src === '[object Object]' || src.includes('[object')) {
      console.warn('Invalid image source detected:', src);
      return undefined;
    }
    return src;
  }
  
  // If it's an object with a url property
  if (typeof src === 'object' && src.url) {
    return safeImageSrc(src.url);
  }
  
  // If it's an object with a src property
  if (typeof src === 'object' && src.src) {
    return safeImageSrc(src.src);
  }
  
  // If it's an object with a dataURL property
  if (typeof src === 'object' && src.dataURL) {
    return safeImageSrc(src.dataURL);
  }
  
  // Log the problematic object for debugging
  console.warn('Invalid image source object:', src);
  
  // Return undefined for any other type
  return undefined;
}

/**
 * Create a safe img element with error handling
 */
export function createSafeImage(src: any, alt?: string): HTMLImageElement | null {
  const safeSrc = safeImageSrc(src);
  if (!safeSrc) return null;
  
  const img = new Image();
  img.src = safeSrc;
  if (alt) img.alt = alt;
  
  img.onerror = () => {
    console.error('Failed to load image:', safeSrc);
  };
  
  return img;
}

/**
 * React hook for safe image loading
 */
export function useSafeImageSrc(src: any): string | undefined {
  return safeImageSrc(src);
}