/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useState } from 'react';

declare global {
  interface Window {
    __TESA_BUILD__?: {
      time: string;
      timestamp: number;
      hash: string;
      id: string;
    };
  }
}

export function BuildVersion() {
  const [buildInfo, setBuildInfo] = useState<typeof window.__TESA_BUILD__>();
  const [showBuild, setShowBuild] = useState(false);

  useEffect(() => {
    // Only show in development or if explicitly enabled
    const isDev = import.meta.env.DEV;
    const isDebug = localStorage.getItem('tesa_debug') === 'true';
    
    if (isDev || isDebug) {
      setShowBuild(true);
      setBuildInfo(window.__TESA_BUILD__);
    }

    // Listen for debug mode toggle (Ctrl+Shift+D)
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        const newDebug = localStorage.getItem('tesa_debug') !== 'true';
        localStorage.setItem('tesa_debug', String(newDebug));
        window.location.reload();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);

  if (!showBuild || !buildInfo) return null;

  const buildDate = new Date(buildInfo.time);
  const ageMinutes = Math.floor((Date.now() - buildInfo.timestamp) / 60000);
  
  return (
    <div className="fixed bottom-4 right-4 z-50 bg-black/80 text-white text-xs p-2 rounded-lg font-mono max-w-sm">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-green-400">● BUILD INFO</span>
        <span className="text-gray-400">({ageMinutes}m old)</span>
      </div>
      <div className="space-y-1 text-gray-300">
        <div>Hash: <span className="text-blue-400">{buildInfo.hash.substring(0, 8)}</span></div>
        <div>Time: {buildDate.toLocaleTimeString()}</div>
        <div>ID: {buildInfo.id}</div>
      </div>
      <div className="mt-2 text-gray-500">
        Press Ctrl+Shift+D to toggle
      </div>
    </div>
  );
}