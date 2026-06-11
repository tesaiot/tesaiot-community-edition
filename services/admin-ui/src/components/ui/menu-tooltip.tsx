/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Info } from 'lucide-react';
import { cn } from '@/lib/utils';

interface MenuTooltipProps {
  title: string;
  content: string;
  className?: string;
  iconClassName?: string;
}

export const MenuTooltip: React.FC<MenuTooltipProps> = ({ 
  title, 
  content, 
  className,
  iconClassName 
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isVisible && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setPosition({
        top: rect.top + rect.height / 2,
        left: rect.right + 12
      });
    }
  }, [isVisible]);

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true);
    }, 300);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className={cn(
          "inline-flex items-center justify-center rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 p-0.5 transition-colors duration-150",
          className
        )}
        onClick={(e) => e.preventDefault()}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <Info className={cn(
          "h-3.5 w-3.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors duration-150",
          iconClassName
        )} />
        <span className="sr-only">More information about {title}</span>
      </button>
      
      {isVisible && createPortal(
        <div 
          className="fixed z-[9999]"
          style={{ 
            top: `${position.top}px`,
            left: `${position.left}px`,
            transform: 'translateY(-50%)'
          }}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <div className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 text-xs rounded px-3 py-2 shadow-lg max-w-xs whitespace-pre-line">
            {content}
          </div>
        </div>,
        document.body
      )}
    </>
  );
};