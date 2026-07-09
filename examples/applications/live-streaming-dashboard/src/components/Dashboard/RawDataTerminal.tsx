/**
 * RawDataTerminal Component
 *
 * Terminal-style display for raw MQTT message data.
 * Shows incoming telemetry messages in a scrollable, monospace format.
 *
 * Features:
 * - Auto-scroll to latest message
 * - JSON syntax highlighting (via color coding)
 * - Timestamp display
 * - Device ID identification
 * - Collapsible JSON data
 *
 * @example
 * ```tsx
 * <RawDataTerminal messages={messages.slice(-50)} />
 * ```
 */

import { useEffect, useRef } from 'react';
import type { TelemetryMessage } from '../../types';

interface RawDataTerminalProps {
  /** Array of telemetry messages to display */
  messages: TelemetryMessage[];
  /** Maximum height of terminal in pixels */
  maxHeight?: number;
}

/**
 * Format timestamp for terminal display
 * Shows HH:MM:SS.mmm format for precise timing
 */
function formatTimestamp(date: Date): string {
  return date.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  } as Intl.DateTimeFormatOptions) + '.' + date.getMilliseconds().toString().padStart(3, '0');
}

/**
 * Truncate device ID for compact display
 * Shows first 8 characters of UUID
 */
function truncateDeviceId(deviceId: string): string {
  if (deviceId.length <= 12) return deviceId;
  return deviceId.substring(0, 8) + '...';
}

/**
 * Format JSON data with basic syntax highlighting
 * Uses colored spans for keys, strings, numbers, and booleans
 */
function formatJsonValue(value: unknown): JSX.Element {
  if (value === null) {
    return <span className="text-gray-500">null</span>;
  }

  if (typeof value === 'number') {
    return <span className="text-yellow-400">{value}</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-purple-400">{value.toString()}</span>;
  }

  if (typeof value === 'string') {
    return <span className="text-green-400">"{value}"</span>;
  }

  if (Array.isArray(value)) {
    return (
      <span className="text-gray-300">
        [{value.map((v, i) => (
          <span key={i}>
            {i > 0 && ', '}
            {formatJsonValue(v)}
          </span>
        ))}]
      </span>
    );
  }

  if (typeof value === 'object') {
    const entries = Object.entries(value);
    return (
      <span className="text-gray-300">
        {'{'}
        {entries.map(([k, v], i) => (
          <span key={k}>
            {i > 0 && ', '}
            <span className="text-blue-400">"{k}"</span>
            <span className="text-gray-500">: </span>
            {formatJsonValue(v)}
          </span>
        ))}
        {'}'}
      </span>
    );
  }

  return <span className="text-gray-400">{String(value)}</span>;
}

/**
 * Single message row in the terminal
 */
function MessageRow({ message }: { message: TelemetryMessage }) {
  const dataEntries = Object.entries(message.data);

  return (
    <div className="border-b border-gray-700 py-2 hover:bg-gray-800/50">
      {/* Header: timestamp and device ID */}
      <div className="flex items-center gap-2 text-xs mb-1">
        <span className="text-gray-500">{formatTimestamp(message.timestamp)}</span>
        <span className="text-cyan-400 font-medium">
          [{truncateDeviceId(message.deviceId)}]
        </span>
        <span className="text-gray-600">→</span>
        <span className="text-gray-400">{message.topic}</span>
      </div>

      {/* Data: formatted JSON */}
      <div className="text-sm font-mono pl-4">
        {dataEntries.length <= 6 ? (
          // Compact format for small payloads
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {dataEntries.map(([key, value]) => (
              <span key={key}>
                <span className="text-blue-400">{key}</span>
                <span className="text-gray-500">: </span>
                {formatJsonValue(value)}
              </span>
            ))}
          </div>
        ) : (
          // Expanded format for larger payloads
          <div className="text-gray-300">
            {formatJsonValue(message.data)}
          </div>
        )}
      </div>
    </div>
  );
}

export function RawDataTerminal({ messages, maxHeight = 300 }: RawDataTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div
        className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-gray-500 flex items-center justify-center"
        style={{ height: maxHeight }}
      >
        Waiting for incoming messages...
      </div>
    );
  }

  return (
    <div
      ref={terminalRef}
      className="bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-y-auto"
      style={{ maxHeight }}
    >
      {/* Terminal header */}
      <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-700">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <span className="text-gray-500 text-xs">
          Raw MQTT Stream ({messages.length} messages)
        </span>
      </div>

      {/* Message list */}
      <div className="space-y-0">
        {messages.map((msg, index) => (
          <MessageRow key={`${msg.timestamp.getTime()}-${index}`} message={msg} />
        ))}
      </div>
    </div>
  );
}

export default RawDataTerminal;
