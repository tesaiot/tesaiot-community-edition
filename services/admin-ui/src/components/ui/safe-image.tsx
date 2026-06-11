/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { safeImageSrc } from '@/lib/image-utils';

interface SafeImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src?: any;
  fallback?: string;
}

export const SafeImage: React.FC<SafeImageProps> = ({ 
  src, 
  fallback, 
  alt = '', 
  ...props 
}) => {
  const safeSrc = safeImageSrc(src);
  
  if (!safeSrc && !fallback) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('SafeImage: No valid source provided', { src, component: 'SafeImage' });
    }
    return null;
  }
  
  return (
    <img 
      src={safeSrc || fallback} 
      alt={alt}
      onError={(e) => {
        if (fallback && e.currentTarget.src !== fallback) {
          e.currentTarget.src = fallback;
        }
      }}
      {...props} 
    />
  );
};