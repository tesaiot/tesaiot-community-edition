/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useBdhDataGridContext } from './bdh-data-grid-context';
import { cn } from '@/lib/utils';
import type { BulkAction } from './types';

interface BdhDataGridBulkActionsProps {
  className?: string;
  position?: 'top' | 'bottom' | 'floating';
}

/**
 * BdhDataGridBulkActions Component
 *
 * Displays a bar with:
 * - Selection count
 * - Deselect all button
 * - Action buttons for bulk operations
 *
 * Actions can optionally require confirmation.
 *
 * @example
 * ```tsx
 * const bulkActions = [
 *   { id: 'delete', label: 'Delete', variant: 'destructive', onClick: handleDelete },
 *   { id: 'export', label: 'Export', onClick: handleExport },
 * ];
 *
 * <BdhDataGrid bulkActions={bulkActions}>
 *   <BdhDataGridBulkActions position="floating" />
 *   <BdhDataGridTable />
 * </BdhDataGrid>
 * ```
 */
export function BdhDataGridBulkActions({
  className,
  position = 'floating',
}: BdhDataGridBulkActionsProps) {
  const { selection, actions, bulkActions, features, isLoading } =
    useBdhDataGridContext();

  const [confirmAction, setConfirmAction] = useState<BulkAction<unknown> | null>(null);
  const [executingAction, setExecutingAction] = useState<string | null>(null);

  // Don't render if bulk actions are disabled or no items selected
  if (!features.bulkActions || selection.selectedIds.length === 0) {
    return null;
  }

  const { selectedIds, selectedRows } = selection;
  const { deselectAll } = actions;

  // Handle action click
  const handleActionClick = async (action: BulkAction<unknown>) => {
    if (action.requireConfirmation) {
      setConfirmAction(action);
      return;
    }

    await executeAction(action);
  };

  // Execute action
  const executeAction = async (action: BulkAction<unknown>) => {
    setExecutingAction(action.id);
    try {
      await action.onClick(selectedRows);
    } catch (error) {
      console.error(`[BulkActions] Error executing ${action.id}:`, error);
    } finally {
      setExecutingAction(null);
      setConfirmAction(null);
    }
  };

  // Check if action should be disabled
  const isActionDisabled = (action: BulkAction<unknown>): boolean => {
    if (isLoading || executingAction !== null) return true;
    if (typeof action.disabled === 'function') {
      return action.disabled(selectedRows);
    }
    return action.disabled ?? false;
  };

  // Check if action should be hidden
  const isActionHidden = (action: BulkAction<unknown>): boolean => {
    if (typeof action.hidden === 'function') {
      return action.hidden(selectedRows);
    }
    return action.hidden ?? false;
  };

  // Filter visible actions
  const visibleActions = bulkActions.filter((action) => !isActionHidden(action));

  const positionClasses = {
    top: 'relative mb-4',
    bottom: 'relative mt-4',
    floating: 'fixed bottom-4 left-1/2 -translate-x-1/2 z-50 shadow-lg',
  };

  return (
    <>
      <div
        className={cn(
          'flex items-center gap-3 px-4 py-3 bg-primary text-primary-foreground rounded-lg',
          positionClasses[position],
          className
        )}
        role="toolbar"
        aria-label="Bulk actions"
      >
        {/* Selection count */}
        <div className="flex items-center gap-2 text-sm font-medium whitespace-nowrap">
          <span>{selectedIds.length} selected</span>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 text-primary-foreground hover:bg-primary-foreground/20"
            onClick={deselectAll}
            aria-label="Deselect all"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Separator */}
        <div className="h-6 w-px bg-primary-foreground/30" />

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          {visibleActions.map((action) => {
            const disabled = isActionDisabled(action);
            const isExecuting = executingAction === action.id;

            return (
              <Button
                key={action.id}
                variant={action.variant === 'destructive' ? 'destructive' : 'secondary'}
                size="sm"
                onClick={() => handleActionClick(action)}
                disabled={disabled}
                className={cn(
                  action.variant !== 'destructive' &&
                    'bg-primary-foreground text-primary hover:bg-primary-foreground/90'
                )}
              >
                {isExecuting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : action.icon ? (
                  <span className="mr-2">{action.icon}</span>
                ) : null}
                {action.label}
              </Button>
            );
          })}
        </div>
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog open={confirmAction !== null} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.label ?? 'Confirm Action'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.confirmationMessage ??
                `Are you sure you want to ${confirmAction?.label?.toLowerCase()} ${selectedIds.length} item${selectedIds.length === 1 ? '' : 's'}? This action cannot be undone.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={executingAction !== null}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => confirmAction && executeAction(confirmAction)}
              disabled={executingAction !== null}
              className={cn(
                confirmAction?.variant === 'destructive' &&
                  'bg-destructive text-destructive-foreground hover:bg-destructive/90'
              )}
            >
              {executingAction !== null && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              {confirmAction?.label}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default BdhDataGridBulkActions;
