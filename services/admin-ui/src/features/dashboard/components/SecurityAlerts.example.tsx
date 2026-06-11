/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React from 'react';
import { SecurityAlerts } from './SecurityAlerts';

/**
 * Example usage of the SecurityAlerts component
 * 
 * The component now supports:
 * 1. Real-time data fetching from /api/v1/dashboard/realtime/security-analytics
 * 2. WebSocket updates for live alerts
 * 3. Different alert types: RBAC violations, auth failures, certificate warnings, compliance, threats
 * 4. Auto-refresh every 30 seconds (configurable)
 * 5. Click handlers for detailed views
 * 6. Loading states and error handling
 */

export const SecurityAlertsExample = () => {
  // Basic usage - will fetch and display all security alerts
  const basicExample = <SecurityAlerts />;

  // Enhanced mode with more detailed information
  const enhancedExample = <SecurityAlerts enhanced={true} />;

  // Custom configuration
  const customExample = (
    <SecurityAlerts
      enhanced={true}
      maxAlerts={20}
      autoRefresh={true}
      refreshInterval={60000} // Refresh every minute
      onAlertClick={(alert) => {
        console.log('Alert clicked:', alert);
        // Handle alert click - could open a modal, navigate to details, etc.
        switch (alert.type) {
          case 'rbac':
            console.log('RBAC violation details:', alert.details);
            break;
          case 'certificate':
            console.log('Certificate warning:', alert.details);
            // Could trigger certificate renewal flow
            break;
          case 'compliance':
            console.log('Compliance alert:', alert.details);
            // Could show compliance documentation
            break;
          case 'auth':
            console.log('Authentication failures:', alert.details);
            // Could show IP blocking options
            break;
          case 'threat':
            console.log('Threat detection:', alert.details);
            // Could show threat analysis dashboard
            break;
        }
      }}
    />
  );

  return (
    <div className="space-y-8 p-8">
      <div>
        <h2 className="text-2xl font-bold mb-4">Security Alerts Component Examples</h2>
        
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-2">Basic Usage</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Default configuration with auto-refresh every 30 seconds
            </p>
            {basicExample}
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-2">Enhanced Mode</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Shows more detailed information and additional alert types
            </p>
            {enhancedExample}
          </div>

          <div>
            <h3 className="text-lg font-semibold mb-2">Custom Configuration</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Custom refresh interval, max alerts, and click handlers
            </p>
            {customExample}
          </div>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">API Response Format</h3>
        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-xs">
{`// Expected API response from /api/v1/dashboard/realtime/security-analytics
{
  "rbac_violations": [
    {
      "id": "viol-123",
      "user_id": "user-456",
      "user_email": "user@example.com",
      "attempted_action": "DELETE_DEVICE",
      "resource": "device/dev-789",
      "timestamp": "2025-06-26T10:30:00Z",
      "severity": "high",
      "details": "User attempted to delete device without proper permissions"
    }
  ],
  "threat_detection": {
    "anomaly_score": 0.85,
    "suspicious_activities": 3,
    "blocked_attempts": 2,
    "risk_level": "high"
  },
  "compliance_alerts": [
    {
      "id": "comp-001",
      "type": "ETSI_EN_303_645",
      "title": "Default Password Policy Violation",
      "description": "5 devices still using default passwords",
      "severity": "critical",
      "timestamp": "2025-06-26T09:00:00Z",
      "action_required": "Update device passwords immediately"
    }
  ],
  "certificate_warnings": [
    {
      "id": "cert-001",
      "device_id": "dev-123",
      "device_name": "Temperature Sensor 01",
      "certificate_cn": "dev-123.iot.local",
      "expiry_date": "2025-07-15T00:00:00Z",
      "days_until_expiry": 19,
      "severity": "medium"
    }
  ],
  "failed_auth_attempts": {
    "count": 7,
    "recent_attempts": [
      {
        "username": "admin@test.com",
        "ip_address": "192.168.1.100",
        "timestamp": "2025-06-26T10:15:00Z",
        "reason": "Invalid password"
      }
    ]
  }
}`}
        </pre>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-lg font-semibold mb-4">WebSocket Connection</h3>
        <p className="text-sm text-muted-foreground mb-2">
          The component automatically connects to WebSocket for real-time updates:
        </p>
        <code className="bg-muted px-2 py-1 rounded text-sm">
          wss://[host]/ws/security-analytics
        </code>
      </div>
    </div>
  );
};

export default SecurityAlertsExample;