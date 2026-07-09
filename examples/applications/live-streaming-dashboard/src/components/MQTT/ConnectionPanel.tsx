/**
 * ConnectionPanel Component
 *
 * MQTT connection management panel with token input and status display.
 * Handles MQTT-over-WebSocket connections to a Community Edition broker.
 *
 * Features:
 * - Token input field with validation
 * - Connect/Disconnect button
 * - Connection status indicator (LED style)
 * - Error message display
 *
 * Token Format:
 *
 * @example
 * ```tsx
 * <ConnectionPanel
 *   token={token}
 *   status="disconnected"
 *   error={null}
 *   onConnect={handleConnect}
 * />
 * ```
 */

import type { ConnectionStatus } from '../../types';

interface ConnectionPanelProps {
  /** MQTT username — the device id on Community Edition */
  username: string;
  /** MQTT password — from POST /api/v1/devices/{id}/reset-mqtt-password */
  password: string;
  /** Callback when the username input changes */
  onUsernameChange: (value: string) => void;
  /** Callback when the password input changes */
  onPasswordChange: (value: string) => void;
  /** Current connection status */
  status: ConnectionStatus;
  /** Error message if connection failed */
  error: string | null;
  /** Callback for connect/disconnect button click */
  onConnect: () => void;
}

/**
 * Get status indicator color based on connection state
 * - Green pulse: Connected
 * - Yellow pulse: Connecting
 * - Red: Disconnected/Error
 */
function getStatusColor(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return 'bg-green-500';
    case 'connecting':
      return 'bg-yellow-500';
    case 'disconnected':
    case 'error':
    default:
      return 'bg-red-500';
  }
}

/**
 * Get human-readable status text
 */
function getStatusText(status: ConnectionStatus): string {
  switch (status) {
    case 'connected':
      return 'Connected';
    case 'connecting':
      return 'Connecting...';
    case 'disconnected':
      return 'Disconnected';
    case 'error':
      return 'Error';
    default:
      return 'Unknown';
  }
}

export function ConnectionPanel({
  username,
  password,
  onUsernameChange,
  onPasswordChange,
  status,
  error,
  onConnect,
}: ConnectionPanelProps) {
  const isConnected = status === 'connected';
  const isConnecting = status === 'connecting';
  const canConnect = !isConnecting && (isConnected || (Boolean(username) && Boolean(password)));

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">MQTT Connection</h2>

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${getStatusColor(status)} ${
              status === 'connected' || status === 'connecting' ? 'animate-pulse' : ''
            }`}
          />
          <span className="text-sm text-gray-400">{getStatusText(status)}</span>
        </div>
      </div>

      {/* Device credentials (Community Edition) */}
      <div className="space-y-4">
        <div>
          <label htmlFor="mqtt-username" className="block text-sm text-gray-400 mb-2">
            Device ID (MQTT username)
          </label>
          <input
            id="mqtt-username"
            type="text"
            value={username}
            onChange={(e) => onUsernameChange(e.target.value)}
            placeholder="my-device-id"
            disabled={isConnected || isConnecting}
            className={`w-full px-4 py-2 bg-gray-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isConnected || isConnecting
                ? 'border-gray-700 opacity-50 cursor-not-allowed'
                : 'border-gray-600'
            }`}
          />
        </div>
        <div>
          <label htmlFor="mqtt-password" className="block text-sm text-gray-400 mb-2">
            MQTT Password
          </label>
          <input
            id="mqtt-password"
            type="password"
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            placeholder="from reset-mqtt-password"
            disabled={isConnected || isConnecting}
            className={`w-full px-4 py-2 bg-gray-900 border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isConnected || isConnecting
                ? 'border-gray-700 opacity-50 cursor-not-allowed'
                : 'border-gray-600'
            }`}
          />
          <p className="text-xs text-gray-500 mt-1">
            Provision a serverTLS device, then get its password from{' '}
            <code>POST /api/v1/devices/&lt;id&gt;/reset-mqtt-password</code>.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-3">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Connect/Disconnect Button */}
        <button
          onClick={onConnect}
          disabled={!canConnect}
          className={`w-full py-2 px-4 rounded-lg font-medium transition-colors ${
            isConnected
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : isConnecting
              ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
              : canConnect
              ? 'bg-blue-600 hover:bg-blue-700 text-white'
              : 'bg-gray-700 text-gray-500 cursor-not-allowed'
          }`}
        >
          {isConnecting ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Connecting...
            </span>
          ) : isConnected ? (
            'Disconnect'
          ) : (
            'Connect'
          )}
        </button>
      </div>
    </div>
  );
}

export default ConnectionPanel;
