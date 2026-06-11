/*
 * TESA IoT Platform
 * Mobile device blocker overlay rendered when viewport is below the supported threshold.
 */

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

interface MobileBlockerOverlayProps {
  visible: boolean;
}

export function MobileBlockerOverlay({ visible }: MobileBlockerOverlayProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!visible || !mounted || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div
      role="alert"
      aria-live="assertive"
      className="fixed inset-0 z-[5000] flex flex-col items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-black text-white px-6 text-center"
    >
      <div className="max-w-sm w-full space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">Desktop or iPad Required</h2>
        <p className="text-sm text-gray-200">
          The TESA Admin Portal is optimised for desktop/notebook and iPad displays. For security and full functionality,
          please sign in from a device with a screen width of at least 768px.
        </p>
        <p className="text-xs text-gray-300">
          Need to work from a phone? Contact the support team for reports or use the API workflow instead.
        </p>
      </div>
    </div>,
    document.body
  );
}

