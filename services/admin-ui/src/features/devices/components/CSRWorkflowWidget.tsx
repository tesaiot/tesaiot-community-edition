/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  CheckCircle2,
  Circle,
  XCircle,
  Loader2,
  Clock,
  Shield,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Key,
  FileCheck,
  Send,
  Download,
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format, formatDistanceToNow } from 'date-fns';
import { AuthTokenManager } from '@/utils/auth-token-manager';

// Workflow step definitions
const WORKFLOW_STEPS = [
  {
    key: 'mqtt_connected',
    label: 'MQTT Connected',
    description: 'Device connected to MQTT broker',
    icon: Send
  },
  {
    key: 'csr_submitted',
    label: 'CSR Submitted',
    description: 'Certificate Signing Request received',
    icon: Key
  },
  {
    key: 'csr_validated',
    label: 'CSR Validated',
    description: 'CSR format and content verified',
    icon: FileCheck
  },
  {
    key: 'certificate_signed',
    label: 'Certificate Signed',
    description: 'Certificate signed by Vault CA',
    icon: Shield
  },
  {
    key: 'certificate_delivered',
    label: 'Certificate Delivered',
    description: 'Certificate sent to device via MQTT',
    icon: Download
  },
  {
    key: 'device_acknowledged',
    label: 'Device Acknowledged',
    description: 'Device confirmed certificate installation',
    icon: CheckCircle2
  }
];

// Step status types
type StepStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped';

interface WorkflowStep {
  step: string;
  status: StepStatus;
  timestamp?: string;
  details?: string;
  error?: string;
}

interface CSRWorkflowStatus {
  device_id: string;
  correlation_id: string;
  workflow_status: 'pending' | 'active' | 'completed' | 'failed' | 'expired';
  progress_percentage: number;
  current_step: string;
  started_at: string;
  updated_at: string;
  completed_at?: string;
  error?: string;
  steps: Record<string, WorkflowStep>;
}

interface CSRWorkflowWidgetProps {
  deviceId: string;
  className?: string;
  compact?: boolean;
  onRefresh?: () => void;
}

const StepIcon = ({ status }: { status: StepStatus }) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case 'in_progress':
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-500" />;
    case 'skipped':
      return <Circle className="h-5 w-5 text-gray-400" />;
    default:
      return <Circle className="h-5 w-5 text-gray-300" />;
  }
};

const StatusBadge = ({ status }: { status: string }) => {
  const variants: Record<string, { color: string; bg: string }> = {
    pending: { color: 'text-gray-600', bg: 'bg-gray-100 dark:bg-gray-800' },
    active: { color: 'text-blue-600', bg: 'bg-blue-100 dark:bg-blue-900/30' },
    completed: { color: 'text-green-600', bg: 'bg-green-100 dark:bg-green-900/30' },
    failed: { color: 'text-red-600', bg: 'bg-red-100 dark:bg-red-900/30' },
    expired: { color: 'text-yellow-600', bg: 'bg-yellow-100 dark:bg-yellow-900/30' }
  };
  const variant = variants[status] || variants.pending;

  return (
    <Badge className={cn(variant.color, variant.bg, 'font-medium')}>
      {status.toUpperCase()}
    </Badge>
  );
};

export const CSRWorkflowWidget: React.FC<CSRWorkflowWidgetProps> = ({
  deviceId,
  className,
  compact = false,
  onRefresh
}) => {
  const [workflow, setWorkflow] = useState<CSRWorkflowStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(!compact);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch workflow status
  const fetchWorkflowStatus = useCallback(async () => {
    try {
      setIsRefreshing(true);
      const token = AuthTokenManager.getToken();
      if (!token) {
        console.error('CSRWorkflowWidget: No auth token found');
        return;
      }
      const response = await fetch(
        `/api/v1/devices/${deviceId}/csr-workflow/status`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.status === 404) {
        // No active workflow
        setWorkflow(null);
        setError(null);
      } else if (response.ok) {
        const data = await response.json();
        if (data.status === 'success') {
          setWorkflow(data.data);
          setError(null);
        }
      } else {
        throw new Error('Failed to fetch workflow status');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [deviceId]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const token = AuthTokenManager.getToken();
    if (!token) {
      console.error('CSRWorkflowWidget: No auth token found for WebSocket');
      return;
    }

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/device-logs/${deviceId}?token=${token}`;

    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          // Subscribe to CSR workflow updates for this device
          ws?.send(JSON.stringify({
            type: 'subscribe',
            device_id: deviceId,
            filters: {
              include_csr_workflow: true
            }
          }));
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'csr_workflow_update' && message.device_id === deviceId) {
              setWorkflow(message.workflow);
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          // Reconnect after 5 seconds
          reconnectTimeout = setTimeout(connect, 5000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    };

    // Initial fetch
    fetchWorkflowStatus();

    // Connect WebSocket
    connect();

    // Cleanup
    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, [deviceId, fetchWorkflowStatus]);

  const handleRefresh = () => {
    fetchWorkflowStatus();
    onRefresh?.();
  };

  if (loading) {
    return (
      <Card className={cn("animate-pulse", className)}>
        <CardHeader className="pb-2">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!workflow) {
    return (
      <Card className={cn("border-dashed", className)}>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-gray-400" />
            CSR Workflow
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-4 text-center">
            <Circle className="h-8 w-8 text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">No active CSR workflow</p>
            <p className="text-xs text-gray-400 mt-1">
              Workflow will appear when device initiates certificate signing
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn(
      "transition-all",
      workflow.workflow_status === 'active' && "border-blue-200 dark:border-blue-800",
      workflow.workflow_status === 'failed' && "border-red-200 dark:border-red-800",
      workflow.workflow_status === 'completed' && "border-green-200 dark:border-green-800",
      className
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className={cn(
              "h-4 w-4",
              workflow.workflow_status === 'active' && "text-blue-500",
              workflow.workflow_status === 'completed' && "text-green-500",
              workflow.workflow_status === 'failed' && "text-red-500"
            )} />
            CSR Workflow
            <StatusBadge status={workflow.workflow_status} />
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="h-7 w-7 p-0"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
            </Button>
            {compact && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
                className="h-7 w-7 p-0"
              >
                {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </Button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-2">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{workflow.current_step.replace(/_/g, ' ')}</span>
            <span>{workflow.progress_percentage}%</span>
          </div>
          <Progress
            value={workflow.progress_percentage}
            className={cn(
              "h-2",
              workflow.workflow_status === 'failed' && "[&>div]:bg-red-500"
            )}
          />
        </div>
      </CardHeader>

      {expanded && (
        <CardContent>
          {/* Error message */}
          {workflow.error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-700 dark:text-red-400">Workflow Error</p>
                  <p className="text-xs text-red-600 dark:text-red-300 mt-1">{workflow.error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Workflow steps */}
          <ScrollArea className="max-h-80">
            <div className="space-y-1">
              {WORKFLOW_STEPS.map((step, index) => {
                const stepData = workflow.steps[step.key];
                const StepIconComponent = step.icon;
                const isCurrentStep = workflow.current_step === step.key;

                return (
                  <div
                    key={step.key}
                    className={cn(
                      "flex items-start gap-3 p-2 rounded-lg transition-colors",
                      isCurrentStep && "bg-blue-50 dark:bg-blue-900/20",
                      stepData?.status === 'failed' && "bg-red-50 dark:bg-red-900/20"
                    )}
                  >
                    {/* Step indicator */}
                    <div className="flex flex-col items-center">
                      <StepIcon status={stepData?.status || 'pending'} />
                      {index < WORKFLOW_STEPS.length - 1 && (
                        <div className={cn(
                          "w-0.5 h-8 mt-1",
                          stepData?.status === 'completed' ? "bg-green-300" : "bg-gray-200 dark:bg-gray-700"
                        )} />
                      )}
                    </div>

                    {/* Step content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <StepIconComponent className={cn(
                          "h-4 w-4",
                          stepData?.status === 'completed' && "text-green-500",
                          stepData?.status === 'in_progress' && "text-blue-500",
                          stepData?.status === 'failed' && "text-red-500",
                          !stepData?.status && "text-gray-400"
                        )} />
                        <span className={cn(
                          "text-sm font-medium",
                          stepData?.status === 'completed' && "text-green-700 dark:text-green-400",
                          stepData?.status === 'failed' && "text-red-700 dark:text-red-400",
                          isCurrentStep && "text-blue-700 dark:text-blue-400"
                        )}>
                          {step.label}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {stepData?.details || step.description}
                      </p>
                      {stepData?.timestamp && (
                        <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {format(new Date(stepData.timestamp), 'HH:mm:ss')}
                        </p>
                      )}
                      {stepData?.error && (
                        <p className="text-xs text-red-500 mt-1">{stepData.error}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>

          {/* Footer info */}
          <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Correlation: {workflow.correlation_id.slice(0, 12)}...</span>
              <span>Started: {formatDistanceToNow(new Date(workflow.started_at), { addSuffix: true })}</span>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
};

export default CSRWorkflowWidget;
