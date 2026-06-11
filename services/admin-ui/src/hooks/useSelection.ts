/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import type { RowSelectionState } from '@tanstack/react-table';
import type { UseSelectionOptions, UseSelectionReturn } from '@/components/ui/bdh-data-grid/types';

/**
 * useSelection Hook
 *
 * @example
 * ```tsx
 * const selection = useSelection({
 *   data: devices,
 *   getRowId: (device) => device.id,
 *   selectionMode: 'multiple',
 *   onSelectionChange: (ids, rows) => console.log('Selected:', rows)
 * });
 *
 * // Use with checkbox
 * <Checkbox
 *   checked={selection.isSelected(device.id)}
 *   onCheckedChange={() => selection.toggleSelection(device.id)}
 * />
 * ```
 */
export function useSelection<TData>(
  options: UseSelectionOptions<TData>
): UseSelectionReturn<TData> {
  const {
    data,
    getRowId,
    selectionMode = 'multiple',
    initialSelection = [],
    onSelectionChange,
  } = options;

  // State - store selected IDs as a Set for O(1) lookup
  const [selectedIdsSet, setSelectedIdsSet] = useState<Set<string>>(
    () => new Set(initialSelection)
  );

  // Convert to array for external consumption
  const selectedIds = useMemo(
    () => Array.from(selectedIdsSet),
    [selectedIdsSet]
  );

  // Get selected rows (maintain data order)
  const selectedRows = useMemo(() => {
    return data.filter((row) => selectedIdsSet.has(getRowId(row)));
  }, [data, selectedIdsSet, getRowId]);

  // Create RowSelectionState for TanStack Table compatibility
  const rowSelection = useMemo((): RowSelectionState => {
    const state: RowSelectionState = {};
    selectedIdsSet.forEach((id) => {
      state[id] = true;
    });
    return state;
  }, [selectedIdsSet]);

  // Check if a specific row is selected
  const isSelected = useCallback(
    (id: string) => selectedIdsSet.has(id),
    [selectedIdsSet]
  );

  // Check if all visible rows are selected
  const isAllSelected = useMemo(() => {
    if (data.length === 0) return false;
    return data.every((row) => selectedIdsSet.has(getRowId(row)));
  }, [data, selectedIdsSet, getRowId]);

  // Check if some (but not all) rows are selected
  const isPartiallySelected = useMemo(() => {
    if (data.length === 0) return false;
    const selectedCount = data.filter((row) =>
      selectedIdsSet.has(getRowId(row))
    ).length;
    return selectedCount > 0 && selectedCount < data.length;
  }, [data, selectedIdsSet, getRowId]);

  // Notify on selection change
  useEffect(() => {
    onSelectionChange?.(selectedIds, selectedRows);
  }, [selectedIds, selectedRows, onSelectionChange]);

  // Toggle selection of a single row
  const toggleSelection = useCallback(
    (id: string) => {
      setSelectedIdsSet((prev) => {
        const next = new Set(prev);

        if (selectionMode === 'single') {
          // Single mode: clear all and select only this one (or deselect if already selected)
          if (prev.has(id)) {
            next.clear();
          } else {
            next.clear();
            next.add(id);
          }
        } else {
          // Multiple mode: toggle this row
          if (next.has(id)) {
            next.delete(id);
          } else {
            next.add(id);
          }
        }

        return next;
      });
    },
    [selectionMode]
  );

  // Toggle select all (visible rows)
  const toggleSelectAll = useCallback(() => {
    setSelectedIdsSet((prev) => {
      if (isAllSelected) {
        // Deselect all visible rows
        const next = new Set(prev);
        data.forEach((row) => next.delete(getRowId(row)));
        return next;
      } else {
        // Select all visible rows
        const next = new Set(prev);
        data.forEach((row) => next.add(getRowId(row)));
        return next;
      }
    });
  }, [data, getRowId, isAllSelected]);

  // Select all visible rows
  const selectAll = useCallback(() => {
    setSelectedIdsSet((prev) => {
      const next = new Set(prev);
      data.forEach((row) => next.add(getRowId(row)));
      return next;
    });
  }, [data, getRowId]);

  // Deselect all rows
  const deselectAll = useCallback(() => {
    setSelectedIdsSet(new Set());
  }, []);

  // Set selection to specific IDs
  const setSelection = useCallback((ids: string[]) => {
    setSelectedIdsSet(new Set(ids));
  }, []);

  // Clean up selection when data changes (remove IDs that no longer exist)
  useEffect(() => {
    const dataIds = new Set(data.map(getRowId));
    setSelectedIdsSet((prev) => {
      const next = new Set<string>();
      prev.forEach((id) => {
        if (dataIds.has(id)) {
          next.add(id);
        }
      });
      // Only update if something changed
      if (next.size !== prev.size) {
        return next;
      }
      return prev;
    });
  }, [data, getRowId]);

  return {
    selectedIds,
    selectedRows,
    rowSelection,
    isSelected,
    isAllSelected,
    isPartiallySelected,
    toggleSelection,
    toggleSelectAll,
    selectAll,
    deselectAll,
    setSelection,
  };
}

export default useSelection;
