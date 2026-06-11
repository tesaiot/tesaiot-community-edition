/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { ColumnDef, Table, Row, RowSelectionState, SortingState, ColumnFiltersState, VisibilityState, ExpandedState } from '@tanstack/react-table';
import { ReactNode } from 'react';

// ============================================================================
// Core Props Interface
// ============================================================================

export interface BdhDataGridProps<TData> {
  // Data
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  getRowId?: (row: TData) => string;

  // Feature Flags
  enableSelection?: boolean;
  enableBulkActions?: boolean;
  enableSorting?: boolean;
  enableExpandableRows?: boolean;
  enablePagination?: boolean;
  enableSearch?: boolean;
  enableColumnFilters?: boolean;
  enableColumnVisibility?: boolean;
  enableAutoSync?: boolean;
  enableExport?: boolean;
  enableRowActions?: boolean;

  // Pagination Options
  initialPage?: number;
  initialPageSize?: number;
  pageSizeOptions?: number[];
  totalItems?: number;
  serverSidePagination?: boolean;
  onPageChange?: (page: number, pageSize: number) => void;

  // Selection Options
  selectionMode?: 'single' | 'multiple';
  initialSelection?: string[];
  onSelectionChange?: (selectedIds: string[], selectedRows: TData[]) => void;

  // Bulk Actions
  bulkActions?: BulkAction<TData>[];
  onBulkAction?: (actionId: string, selectedRows: TData[]) => void | Promise<void>;

  // Row Actions
  rowActions?: RowAction<TData>[];

  // Expandable Rows
  renderExpandedRow?: (row: TData) => ReactNode;
  onRowExpand?: (row: TData, isExpanded: boolean) => void;

  // Search & Filters
  searchPlaceholder?: string;
  searchColumns?: string[];
  filterConfig?: FilterConfig[];
  onSearchChange?: (searchTerm: string) => void;
  onFilterChange?: (filters: ColumnFiltersState) => void;

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

  // Styling
  className?: string;
  tableClassName?: string;
  headerClassName?: string;
  rowClassName?: string | ((row: TData) => string);

  // Loading & Empty States
  isLoading?: boolean;
  loadingComponent?: ReactNode;
  emptyComponent?: ReactNode;
  emptyMessage?: string;

  // Events
  onRowClick?: (row: TData) => void;
  onRowDoubleClick?: (row: TData) => void;
  onSortingChange?: (sorting: SortingState) => void;
}

// ============================================================================
// Bulk Actions
// ============================================================================

export interface BulkAction<TData> {
  id: string;
  label: string;
  icon?: ReactNode;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost';
  disabled?: boolean | ((selectedRows: TData[]) => boolean);
  hidden?: boolean | ((selectedRows: TData[]) => boolean);
  requireConfirmation?: boolean;
  confirmationMessage?: string;
  onClick: (selectedRows: TData[]) => void | Promise<void>;
}

// ============================================================================
// Row Actions
// ============================================================================

export interface RowAction<TData> {
  id: string;
  label: string;
  icon?: ReactNode;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost';
  disabled?: boolean | ((row: TData) => boolean);
  hidden?: boolean | ((row: TData) => boolean);
  onClick: (row: TData) => void | Promise<void>;
}

// ============================================================================
// Filter Configuration
// ============================================================================

export interface FilterConfig {
  columnId: string;
  label: string;
  type: 'text' | 'select' | 'multiSelect' | 'date' | 'dateRange' | 'number' | 'numberRange';
  options?: FilterOption[];
  placeholder?: string;
  defaultValue?: unknown;
}

export interface FilterOption {
  label: string;
  value: string;
  icon?: ReactNode;
}

// ============================================================================
// Sync Status
// ============================================================================

export type SyncStatusType = 'idle' | 'syncing' | 'connected' | 'disconnected' | 'error';

export interface SyncStatus {
  status: SyncStatusType;
  lastSyncedAt: Date | null;
  error?: string;
  isConnected: boolean;
  isSyncing: boolean;
}

// ============================================================================
// Export
// ============================================================================

export type ExportFormat = 'csv' | 'excel' | 'json';

export interface ExportOptions<TData> {
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  filename: string;
  format: ExportFormat;
  includeHeaders?: boolean;
  selectedOnly?: boolean;
}

// ============================================================================
// Context Value
// ============================================================================

export interface BdhDataGridContextValue<TData> {
  // Table Instance
  table: Table<TData>;

  // Data
  data: TData[];
  filteredData: TData[];
  paginatedData: TData[];

  // Feature Flags
  features: {
    selection: boolean;
    bulkActions: boolean;
    sorting: boolean;
    expandableRows: boolean;
    pagination: boolean;
    search: boolean;
    columnFilters: boolean;
    columnVisibility: boolean;
    autoSync: boolean;
    export: boolean;
    rowActions: boolean;
  };

  // Pagination State
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

  // Selection State
  selection: {
    selectedIds: string[];
    selectedRows: TData[];
    isSelected: (id: string) => boolean;
    isAllSelected: boolean;
    isPartiallySelected: boolean;
  };

  // Sync State
  sync: SyncStatus;

  // Loading State
  isLoading: boolean;

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
    exportData: (format: ExportFormat) => void;
  };

  // Bulk Actions
  bulkActions: BulkAction<TData>[];

  // Row Actions
  rowActions: RowAction<TData>[];

  // Callbacks
  renderExpandedRow?: (row: TData) => ReactNode;
  onRowClick?: (row: TData) => void;
  onRowDoubleClick?: (row: TData) => void;

  // Styling
  classNames: {
    table?: string;
    header?: string;
    row?: string | ((row: TData) => string);
  };
}

// ============================================================================
// Hook Return Types
// ============================================================================

export interface UsePaginationOptions {
  initialPage?: number;
  initialPageSize?: number;
  pageSizeOptions?: number[];
  totalItems: number;
  onPageChange?: (page: number, pageSize: number) => void;
}

export interface UsePaginationReturn {
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
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  nextPage: () => void;
  prevPage: () => void;
  reset: () => void;
}

export interface UseSelectionOptions<TData> {
  data: TData[];
  getRowId: (row: TData) => string;
  selectionMode?: 'single' | 'multiple';
  initialSelection?: string[];
  onSelectionChange?: (selectedIds: string[], selectedRows: TData[]) => void;
}

export interface UseSelectionReturn<TData> {
  selectedIds: string[];
  selectedRows: TData[];
  rowSelection: RowSelectionState;
  isSelected: (id: string) => boolean;
  isAllSelected: boolean;
  isPartiallySelected: boolean;
  toggleSelection: (id: string) => void;
  toggleSelectAll: () => void;
  selectAll: () => void;
  deselectAll: () => void;
  setSelection: (ids: string[]) => void;
}

export interface UseAutoSyncOptions<TData> {
  enabled?: boolean;
  mode?: 'polling' | 'websocket' | 'both';
  pollingInterval?: number;
  wsEndpoint?: string;
  onDataRefresh?: () => Promise<TData[]>;
  onStatusChange?: (status: SyncStatus) => void;
}

export interface UseAutoSyncReturn {
  status: SyncStatus;
  refresh: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  isConnected: boolean;
  isSyncing: boolean;
  lastSyncedAt: Date | null;
}

export interface UseExportOptions<TData> {
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  filename?: string;
  formats?: ExportFormat[];
  onExport?: (format: ExportFormat, data: TData[]) => void;
}

export interface UseExportReturn {
  exportCSV: () => void;
  exportExcel: () => void;
  exportJSON: () => void;
  exportData: (format: ExportFormat) => void;
  isExporting: boolean;
  supportedFormats: ExportFormat[];
}

// ============================================================================
// Utility Types
// ============================================================================

export type DataGridColumnDef<TData> = ColumnDef<TData, unknown> & {
  enableSorting?: boolean;
  enableFiltering?: boolean;
  enableHiding?: boolean;
  exportable?: boolean;
  exportHeader?: string;
  exportValue?: (row: TData) => string | number | boolean | null;
};
