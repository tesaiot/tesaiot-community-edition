/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * Telemetry WebSocket hook - uses Python WebSocket service workaround
 * Fixed to use functional implementation instead of stub
 */

// The workaround hook file exports the function as `useTelemetryWebSocket`.
// Import it under an alias to keep the current API surface.
import { useTelemetryWebSocket as useTelemetryWebSocketPython } from './useTelemetryWebSocket-python-workaround';

export const useTelemetryWebSocket = (options: any) => {
  // Use the Python WebSocket workaround for now
  const {
    isConnected,
    error,
    lastMessage,
    subscribeToDevice,
    unsubscribeFromDevice,
    reconnect
  } = useTelemetryWebSocketPython(options);
  
  return {
    isConnected,
    error,
    lastMessage,
    subscribeToDevice,
    unsubscribeFromDevice,
    reconnect
  };
};
