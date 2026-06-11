/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useMemo, useCallback, ReactNode } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getExpandedRowModel,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  ExpandedState,
} from '@tanstack/react-table';
import { BdhDataGridProvider } from './bdh-data-grid-context';
import { usePagination } from '@/hooks/usePagination';
import { useSelection } from '@/hooks/useSelection';
import { useAutoSync } from '@/hooks/useAutoSync';
import { useExport } from '@/hooks/useExport';
import { cn } from '@/lib/utils';
import type {
  BdhDataGridProps,
  BdhDataGridContextValue,
  SyncStatus,
  ExportFormat,
} from './types';

/**
 * BdhDataGrid Component
 *
 * A comprehensive data grid with all features toggleable via props.
 *
 * @example
 * ```tsx
 * import {
 *   BdhDataGrid,
 *   BdhDataGridToolbar,
 *   BdhDataGridTable,
 *   BdhDataGridPagination,
 *   BdhDataGridBulkActions,
 * } from '@/components/ui/bdh-data-grid';
 *
 * function DeviceList() {
 *   const columns = [
 *     { accessorKey: 'name', header: 'Device Name' },
 *     { accessorKey: 'status', header: 'Status' },
 *     { accessorKey: 'lastSeen', header: 'Last Seen' },
 *   ];
 *
 *   const bulkActions = [
 *     { id: 'restart', label: 'Restart', onClick: handleRestart },
 *     { id: 'delete', label: 'Delete', variant: 'destructive', onClick: handleDelete },
 *   ];
 *
 *   return (
 *     <BdhDataGrid
 *       data={devices}
 *       columns={columns}
 *       bulkActions={bulkActions}
 *       enablePagination={true}
 *       enableSelection={true}
 *       enableSorting={true}
 *       enableExport={true}
 *     >
 *       <BdhDataGridToolbar />
 *       <BdhDataGridBulkActions position="floating" />
 *       <BdhDataGridTable />
 *       <BdhDataGridPagination />
 *     </BdhDataGrid>
 *   );
 * }
 * ```
 */
export function BdhDataGrid<TData>({
  // Data
  data,
  columns,
  getRowId = (row: TData) => {
    const r = row as Record<string, unknown>;
    return String(r.id ?? r._id ?? Math.random());
  },

  // Feature Flags
  enableSelection = true,
  enableBulkActions = true,
  enableSorting = true,
  enableExpandableRows = false,
  enablePagination = true,
  enableSearch = true,
  enableColumnFilters = false,
  enableColumnVisibility = true,
  enableAutoSync = false,
  enableExport = true,
  enableRowActions = false,

  // Pagination Options
  initialPage = 1,
  initialPageSize = 10,
  pageSizeOptions = [10, 20, 50, 100],
  totalItems,
  serverSidePagination = false,
  onPageChange,

  // Selection Options
  selectionMode = 'multiple',
  initialSelection = [],
  onSelectionChange,

  // Bulk Actions
  bulkActions = [],
  onBulkAction,

  // Row Actions
  rowActions = [],

  // Expandable Rows
  renderExpandedRow,
  onRowExpand,

  // Search & Filters
  searchPlaceholder,
  searchColumns,
  filterConfig,
  onSearchChange,
  onFilterChange,

  // Auto-Sync
  syncMode = 'polling',
  pollingInterval = 30000,
  wsEndpoint,
  onDataRefresh,
  onSyncStatusChange,

  // Export
  exportFormats = ['csv', 'excel', 'json'],
  exportFilename = 'export',
  onExport,

  // Styling
  className,
  tableClassName,
  headerClassName,
  rowClassName,

  // Loading & Empty States
  isLoading = false,
  loadingComponent,
  emptyComponent,
  emptyMessage,

  // Events
  onRowClick,
  onRowDoubleClick,
  onSortingChange,

  // Children
  children,
}: BdhDataGridProps<TData> & { children?: ReactNode }) {
  // ============================================================================
  // State Management
  // ============================================================================

  // Sorting state
  const [sorting, setSorting] = useState<SortingState>([]);

  // Column filters state
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  // Column visibility state
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  // Expanded rows state
  const [expanded, setExpanded] = useState<ExpandedState>({});

  // Global filter (search) state
  const [globalFilter, setGlobalFilter] = useState('');

  // ============================================================================
  // Hooks
  // ============================================================================

  // Selection hook
  const selection = useSelection({
    data,
    getRowId,
    selectionMode,
    initialSelection,
    onSelectionChange,
  });

  // Calculate total items (client-side or server-side)
  const actualTotalItems = totalItems ?? data.length;

  // Pagination hook
  const pagination = usePagination({
    initialPage,
    initialPageSize,
    pageSizeOptions,
    totalItems: actualTotalItems,
    onPageChange,
  });

  // Auto-sync hook
  const autoSync = useAutoSync({
    enabled: enableAutoSync,
    mode: syncMode,
    pollingInterval,
    wsEndpoint,
    onDataRefresh,
    onStatusChange: onSyncStatusChange,
  });

  // Export hook
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
    data: serverSidePagination ? data : data,
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
    enableColumnFilters: enableColumnFilters,
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
    pageCount: serverSidePagination ? Math.ceil(actualTotalItems / pagination.pageSize) : undefined,
  });

  // ============================================================================
  // Derived Data
  // ============================================================================

  // Get filtered data
  const filteredData = useMemo(() => {
    if (serverSidePagination) return data;
    return table.getFilteredRowModel().rows.map((row) => row.original);
  }, [table, data, serverSidePagination]);

  // Get paginated data
  const paginatedData = useMemo(() => {
    if (serverSidePagination) return data;
    return table.getRowModel().rows.map((row) => row.original);
  }, [table, data, serverSidePagination]);

  // ============================================================================
  // Actions
  // ============================================================================

  const contextActions = useMemo(() => ({
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
    setSearchTerm: (term: string) => table.setGlobalFilter(term),
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
    exportData: exportHook.exportData,
  }), [pagination, selection, table, autoSync, exportHook]);

  // ============================================================================
  // Context Value
  // ============================================================================

  const contextValue: BdhDataGridContextValue<TData> = useMemo(() => ({
    // Table instance
    table,

    // Data
    data,
    filteredData,
    paginatedData,

    // Feature flags
    features: {
      selection: enableSelection,
      bulkActions: enableBulkActions,
      sorting: enableSorting,
      expandableRows: enableExpandableRows,
      pagination: enablePagination,
      search: enableSearch,
      columnFilters: enableColumnFilters,
      columnVisibility: enableColumnVisibility,
      autoSync: enableAutoSync,
      export: enableExport,
      rowActions: enableRowActions,
    },

    // Pagination state
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

    // Selection state
    selection: {
      selectedIds: selection.selectedIds,
      selectedRows: selection.selectedRows,
      isSelected: selection.isSelected,
      isAllSelected: selection.isAllSelected,
      isPartiallySelected: selection.isPartiallySelected,
    },

    // Sync state
    sync: autoSync.status,

    // Loading state
    isLoading,

    // Actions
    actions: contextActions,

    // Bulk actions
    bulkActions,

    // Row actions
    rowActions,

    // Callbacks
    renderExpandedRow,
    onRowClick,
    onRowDoubleClick,

    // Styling
    classNames: {
      table: tableClassName,
      header: headerClassName,
      row: rowClassName,
    },
  }), [
    table,
    data,
    filteredData,
    paginatedData,
    enableSelection,
    enableBulkActions,
    enableSorting,
    enableExpandableRows,
    enablePagination,
    enableSearch,
    enableColumnFilters,
    enableColumnVisibility,
    enableAutoSync,
    enableExport,
    enableRowActions,
    pagination,
    selection,
    autoSync.status,
    isLoading,
    contextActions,
    bulkActions,
    rowActions,
    renderExpandedRow,
    onRowClick,
    onRowDoubleClick,
    tableClassName,
    headerClassName,
    rowClassName,
  ]);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <BdhDataGridProvider value={contextValue}>
      <div className={cn('space-y-4', className)}>
        {children}
      </div>
    </BdhDataGridProvider>
  );
}

export default BdhDataGrid;
