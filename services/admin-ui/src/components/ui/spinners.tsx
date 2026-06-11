/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import * as React from 'react';

type SpinnerProps = React.HTMLAttributes<HTMLDivElement> & {
  size?: 'sm' | 'md' | 'lg';
};

function Spinner({ className, style, size = 'md', ...props }: SpinnerProps) {
  const sizeMap = {
    sm: { logo: '20px', dots: '4px' },
    md: { logo: '24px', dots: '6px' },
    lg: { logo: '32px', dots: '8px' }
  };

  const currentSize = sizeMap[size];

  return (
    <div className={`flex items-center gap-2 ${className || ''}`} style={style} {...props}>
      <img
        src="/images/TESA_LOGO.svg"
        alt="TESA"
        style={{ width: currentSize.logo, height: currentSize.logo }}
      />
      <div className="flex gap-1">
        <span 
          className="animate-bounce" 
          style={{
            width: currentSize.dots,
            height: currentSize.dots,
            backgroundColor: 'currentColor',
            borderRadius: '50%',
            animationDelay: '0ms'
          }}
        />
        <span 
          className="animate-bounce" 
          style={{
            width: currentSize.dots,
            height: currentSize.dots,
            backgroundColor: 'currentColor',
            borderRadius: '50%',
            animationDelay: '150ms'
          }}
        />
        <span 
          className="animate-bounce" 
          style={{
            width: currentSize.dots,
            height: currentSize.dots,
            backgroundColor: 'currentColor',
            borderRadius: '50%',
            animationDelay: '300ms'
          }}
        />
      </div>
    </div>
  );
}

export { Spinner };
