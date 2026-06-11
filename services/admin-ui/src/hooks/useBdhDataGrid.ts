/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useMemo, useCallback } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getExpandedRowModel,
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  ExpandedState,
  Table,
} from '@tanstack/react-table';
import { usePagination } from './usePagination';
import { useSelection } from './useSelection';
import { useAutoSync } from './useAutoSync';
import { useExport } from './useExport';
import type {
  BulkAction,
  RowAction,
  SyncStatus,
  ExportFormat,
} from '@/components/ui/bdh-data-grid/types';

export interface UseBdhDataGridOptions<TData> {
  // Data
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  getRowId?: (row: TData) => string;

  // Feature Flags
  enableSelection?: boolean;
  enableSorting?: boolean;
  enableExpandableRows?: boolean;
  enablePagination?: boolean;
  enableSearch?: boolean;
  enableColumnFilters?: boolean;
  enableColumnVisibility?: boolean;
  enableAutoSync?: boolean;
  enableExport?: boolean;

  // Pagination
  initialPage?: number;
  initialPageSize?: number;
  pageSizeOptions?: number[];
  serverSidePagination?: boolean;
  onPageChange?: (page: number, pageSize: number) => void;

  // Selection
  selectionMode?: 'single' | 'multiple';
  initialSelection?: string[];
  onSelectionChange?: (selectedIds: string[], selectedRows: TData[]) => void;

  // Auto-Sync
  syncMode?: 'polling' | 'websocket' | 'both';
  pollingInterval?: number;
  wsEndpoint?: string;
  onDataRefresh?: () => Promise<TData[]>;
  onSyncStatusChange?: (status: SyncStatus) => void;

  // Export
  exportFormats?: ExportFormat[];
  exportFilename?: string;
  onExport?: (format: ExportFormat, data: TData[]) => void;

  // Events
  onSortingChange?: (sorting: SortingState) => void;
  onFilterChange?: (filters: ColumnFiltersState) => void;
  onSearchChange?: (searchTerm: string) => void;
}

export interface UseBdhDataGridReturn<TData> {
  // Table instance
  table: Table<TData>;

  // Data
  data: TData[];
  filteredData: TData[];
  paginatedData: TData[];

  // States
  sorting: SortingState;
  columnFilters: ColumnFiltersState;
  columnVisibility: VisibilityState;
  expanded: ExpandedState;
  globalFilter: string;

  // Pagination
  pagination: {
    currentPage: number;
    pageSize: number;
    totalPages: number;
    totalItems: number;
    startIndex: number;
    endIndex: number;
    canNextPage: boolean;
    canPrevPage: boolean;
    pageNumbers: number[];
    pageSizeOptions: number[];
  };

  // Selection
  selection: {
    selectedIds: string[];
    selectedRows: TData[];
    isSelected: (id: string) => boolean;
    isAllSelected: boolean;
    isPartiallySelected: boolean;
  };

  // Sync
  sync: {
    status: SyncStatus;
    isConnected: boolean;
    isSyncing: boolean;
    lastSyncedAt: Date | null;
  };

  // Export
  export: {
    isExporting: boolean;
    supportedFormats: ExportFormat[];
  };

  // Actions
  actions: {
    // Pagination
    setPage: (page: number) => void;
    setPageSize: (size: number) => void;
    nextPage: () => void;
    prevPage: () => void;

    // Selection
    toggleSelection: (id: string) => void;
    toggleSelectAll: () => void;
    selectAll: () => void;
    deselectAll: () => void;
    setSelection: (ids: string[]) => void;

    // Search & Filters
    setSearchTerm: (term: string) => void;
    setColumnFilter: (columnId: string, value: unknown) => void;
    clearFilters: () => void;

    // Sorting
    setSorting: (sorting: SortingState) => void;
    toggleSort: (columnId: string) => void;

    // Column Visibility
    toggleColumn: (columnId: string) => void;
    setColumnVisibility: (visibility: VisibilityState) => void;

    // Row Expansion
    toggleRowExpansion: (rowId: string) => void;
    expandAll: () => void;
    collapseAll: () => void;

    // Sync
    refresh: () => Promise<void>;
    pauseSync: () => void;
    resumeSync: () => void;

    // Export
    exportCSV: () => void;
    exportExcel: () => void;
    exportJSON: () => void;
    exportData: (format: ExportFormat) => void;
  };
}

/**
 * useBdhDataGrid Hook
 *
 * Main hook for building custom data grid implementations.
 *
 * @example
 * ```tsx
 * function CustomDeviceGrid() {
 *   const {
 *     table,
 *     pagination,
 *     selection,
 *     actions,
 *   } = useBdhDataGrid({
 *     data: devices,
 *     columns: deviceColumns,
 *     enablePagination: true,
 *     enableSelection: true,
 *   });
 *
 *   return (
 *     <div>
 *       <MyCustomToolbar onSearch={actions.setSearchTerm} />
 *       <MyCustomTable table={table} />
 *       <MyCustomPagination
 *         page={pagination.currentPage}
 *         total={pagination.totalPages}
 *         onPageChange={actions.setPage}
 *       />
 *     </div>
 *   );
 * }
 * ```
 */
export function useBdhDataGrid<TData>(
  options: UseBdhDataGridOptions<TData>
): UseBdhDataGridReturn<TData> {
  const {
    data,
    columns,
    getRowId = (row: TData) => {
      const r = row as Record<string, unknown>;
      return String(r.id ?? r._id ?? Math.random());
    },

    enableSelection = true,
    enableSorting = true,
    enableExpandableRows = false,
    enablePagination = true,
    enableSearch = true,
    enableColumnFilters = false,
    enableColumnVisibility = true,
    enableAutoSync = false,
    enableExport = true,

    initialPage = 1,
    initialPageSize = 10,
    pageSizeOptions = [10, 20, 50, 100],
    serverSidePagination = false,
    onPageChange,

    selectionMode = 'multiple',
    initialSelection = [],
    onSelectionChange,

    syncMode = 'polling',
    pollingInterval = 30000,
    wsEndpoint,
    onDataRefresh,
    onSyncStatusChange,

    exportFormats = ['csv', 'excel', 'json'],
    exportFilename = 'export',
    onExport,

    onSortingChange,
    onFilterChange,
    onSearchChange,
  } = options;

  // ============================================================================
  // State
  // ============================================================================

  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [expanded, setExpanded] = useState<ExpandedState>({});
  const [globalFilter, setGlobalFilter] = useState('');

  // ============================================================================
  // Hooks
  // ============================================================================

  const selection = useSelection({
    data,
    getRowId,
    selectionMode,
    initialSelection,
    onSelectionChange,
  });

  const totalItems = data.length;

  const pagination = usePagination({
    initialPage,
    initialPageSize,
    pageSizeOptions,
    totalItems,
    onPageChange,
  });

  const autoSync = useAutoSync({
    enabled: enableAutoSync,
    mode: syncMode,
    pollingInterval,
    wsEndpoint,
    onDataRefresh,
    onStatusChange: onSyncStatusChange,
  });

  const exportHook = useExport({
    data,
    columns,
    filename: exportFilename,
    formats: exportFormats,
    onExport,
  });

  // ============================================================================
  // Table Instance
  // ============================================================================

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      expanded,
      globalFilter,
      rowSelection: selection.rowSelection,
      pagination: {
        pageIndex: pagination.currentPage - 1,
        pageSize: pagination.pageSize,
      },
    },
    getRowId,
    enableRowSelection: enableSelection,
    enableSorting,
    enableColumnFilters,
    enableGlobalFilter: enableSearch,
    enableExpanding: enableExpandableRows,
    onSortingChange: (updater) => {
      const newSorting = typeof updater === 'function' ? updater(sorting) : updater;
      setSorting(newSorting);
      onSortingChange?.(newSorting);
    },
    onColumnFiltersChange: (updater) => {
      const newFilters = typeof updater === 'function' ? updater(columnFilters) : updater;
      setColumnFilters(newFilters);
      onFilterChange?.(newFilters);
    },
    onColumnVisibilityChange: setColumnVisibility,
    onExpandedChange: setExpanded,
    onGlobalFilterChange: (value) => {
      setGlobalFilter(value);
      onSearchChange?.(value);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    getFilteredRowModel: enableSearch || enableColumnFilters ? getFilteredRowModel() : undefined,
    getPaginationRowModel: enablePagination && !serverSidePagination ? getPaginationRowModel() : undefined,
    getExpandedRowModel: enableExpandableRows ? getExpandedRowModel() : undefined,
    manualPagination: serverSidePagination,
  });

  // ============================================================================
  // Derived Data
  // ============================================================================

  const filteredData = useMemo(() => {
    return table.getFilteredRowModel().rows.map((row) => row.original);
  }, [table]);

  const paginatedData = useMemo(() => {
    return table.getRowModel().rows.map((row) => row.original);
  }, [table]);

  // ============================================================================
  // Actions
  // ============================================================================

  const actions = useMemo(() => ({
    // Pagination
    setPage: pagination.setPage,
    setPageSize: pagination.setPageSize,
    nextPage: pagination.nextPage,
    prevPage: pagination.prevPage,

    // Selection
    toggleSelection: selection.toggleSelection,
    toggleSelectAll: selection.toggleSelectAll,
    selectAll: selection.selectAll,
    deselectAll: selection.deselectAll,
    setSelection: selection.setSelection,

    // Search & Filters
    setSearchTerm: (term: string) => {
      setGlobalFilter(term);
      onSearchChange?.(term);
    },
    setColumnFilter: (columnId: string, value: unknown) => {
      table.getColumn(columnId)?.setFilterValue(value);
    },
    clearFilters: () => {
      setColumnFilters([]);
      setGlobalFilter('');
    },

    // Sorting
    setSorting,
    toggleSort: (columnId: string) => {
      table.getColumn(columnId)?.toggleSorting();
    },

    // Column Visibility
    toggleColumn: (columnId: string) => {
      table.getColumn(columnId)?.toggleVisibility();
    },
    setColumnVisibility,

    // Row Expansion
    toggleRowExpansion: (rowId: string) => {
      setExpanded((prev) => ({
        ...prev,
        [rowId]: !prev[rowId as keyof typeof prev],
      }));
    },
    expandAll: () => table.toggleAllRowsExpanded(true),
    collapseAll: () => table.toggleAllRowsExpanded(false),

    // Sync
    refresh: autoSync.refresh,
    pauseSync: autoSync.pause,
    resumeSync: autoSync.resume,

    // Export
    exportCSV: exportHook.exportCSV,
    exportExcel: exportHook.exportExcel,
    exportJSON: exportHook.exportJSON,
    exportData: exportHook.exportData,
  }), [pagination, selection, table, autoSync, exportHook, onSearchChange]);

  // ============================================================================
  // Return
  // ============================================================================

  return {
    table,
    data,
    filteredData,
    paginatedData,
    sorting,
    columnFilters,
    columnVisibility,
    expanded,
    globalFilter,
    pagination: {
      currentPage: pagination.currentPage,
      pageSize: pagination.pageSize,
      totalPages: pagination.totalPages,
      totalItems: pagination.totalItems,
      startIndex: pagination.startIndex,
      endIndex: pagination.endIndex,
      canNextPage: pagination.canNextPage,
      canPrevPage: pagination.canPrevPage,
      pageNumbers: pagination.pageNumbers,
      pageSizeOptions: pagination.pageSizeOptions,
    },
    selection: {
      selectedIds: selection.selectedIds,
      selectedRows: selection.selectedRows,
      isSelected: selection.isSelected,
      isAllSelected: selection.isAllSelected,
      isPartiallySelected: selection.isPartiallySelected,
    },
    sync: {
      status: autoSync.status,
      isConnected: autoSync.isConnected,
      isSyncing: autoSync.isSyncing,
      lastSyncedAt: autoSync.lastSyncedAt,
    },
    export: {
      isExporting: exportHook.isExporting,
      supportedFormats: exportHook.supportedFormats,
    },
    actions,
  };
}

export default useBdhDataGrid;
