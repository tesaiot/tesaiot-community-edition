/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { Fragment } from 'react';
import { flexRender } from '@tanstack/react-table';
import { ChevronDown, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, MoreHorizontal } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { useBdhDataGridContext } from './bdh-data-grid-context';
import { cn } from '@/lib/utils';
import type { RowAction } from './types';

interface BdhDataGridTableProps {
  className?: string;
  stickyHeader?: boolean;
  showRowBorders?: boolean;
  stripedRows?: boolean;
  compactMode?: boolean;
}

/**
 * BdhDataGridTable Component
 *
 * Renders the data table with:
 * - Sortable column headers
 * - Row selection checkboxes
 * - Expandable rows
 * - Row actions menu
 *
 * @example
 * ```tsx
 * <BdhDataGrid data={data} columns={columns}>
 *   <BdhDataGridToolbar />
 *   <BdhDataGridTable stickyHeader stripedRows />
 *   <BdhDataGridPagination />
 * </BdhDataGrid>
 * ```
 */
export function BdhDataGridTable({
  className,
  stickyHeader = false,
  showRowBorders = true,
  stripedRows = false,
  compactMode = false,
}: BdhDataGridTableProps) {
  const {
    table,
    features,
    selection,
    actions,
    rowActions,
    renderExpandedRow,
    onRowClick,
    onRowDoubleClick,
    classNames,
    isLoading,
    paginatedData,
  } = useBdhDataGridContext();

  const rows = table.getRowModel().rows;
  const headerGroups = table.getHeaderGroups();

  // Render loading skeleton
  if (isLoading && rows.length === 0) {
    return (
      <div className={cn('rounded-md border', className)}>
        <Table>
          <TableHeader>
            <TableRow>
              {Array.from({ length: 5 }).map((_, i) => (
                <TableHead key={i}>
                  <Skeleton className="h-4 w-24" />
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, rowIdx) => (
              <TableRow key={rowIdx}>
                {Array.from({ length: 5 }).map((_, cellIdx) => (
                  <TableCell key={cellIdx}>
                    <Skeleton className="h-4 w-full" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  return (
    <div className={cn('rounded-md border overflow-auto', className)}>
      <Table className={classNames.table}>
        <TableHeader className={cn(stickyHeader && 'sticky top-0 bg-background z-10')}>
          {headerGroups.map((headerGroup) => (
            <TableRow key={headerGroup.id} className={classNames.header}>
              {/* Selection column */}
              {features.selection && (
                <TableHead className="w-[40px]">
                  <Checkbox
                    checked={selection.isAllSelected}
                    ref={(el) => {
                      if (el) {
                        (el as HTMLButtonElement).indeterminate = selection.isPartiallySelected;
                      }
                    }}
                    onCheckedChange={actions.toggleSelectAll}
                    aria-label="Select all"
                  />
                </TableHead>
              )}

              {/* Expand column */}
              {features.expandableRows && (
                <TableHead className="w-[40px]" />
              )}

              {/* Data columns */}
              {headerGroup.headers.map((header) => {
                const canSort = header.column.getCanSort();
                const isSorted = header.column.getIsSorted();

                return (
                  <TableHead
                    key={header.id}
                    className={cn(compactMode && 'py-2')}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={cn(
                          'flex items-center gap-2',
                          canSort && 'cursor-pointer select-none hover:text-foreground'
                        )}
                        onClick={canSort ? () => header.column.toggleSorting() : undefined}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {canSort && (
                          <span className="text-muted-foreground">
                            {isSorted === 'asc' ? (
                              <ArrowUp className="h-4 w-4" />
                            ) : isSorted === 'desc' ? (
                              <ArrowDown className="h-4 w-4" />
                            ) : (
                              <ArrowUpDown className="h-4 w-4 opacity-50" />
                            )}
                          </span>
                        )}
                      </div>
                    )}
                  </TableHead>
                );
              })}

              {/* Row actions column */}
              {features.rowActions && rowActions.length > 0 && (
                <TableHead className="w-[50px]" />
              )}
            </TableRow>
          ))}
        </TableHeader>

        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={
                  headerGroups[0]?.headers.length +
                  (features.selection ? 1 : 0) +
                  (features.expandableRows ? 1 : 0) +
                  (features.rowActions && rowActions.length > 0 ? 1 : 0)
                }
                className="h-24 text-center text-muted-foreground"
              >
                No results found
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, rowIdx) => {
              const rowId = row.id;
              const isSelected = selection.isSelected(rowId);
              const isExpanded = row.getIsExpanded();
              const rowData = row.original;

              // Determine row class
              let rowClass = '';
              if (typeof classNames.row === 'function') {
                rowClass = classNames.row(rowData);
              } else if (classNames.row) {
                rowClass = classNames.row;
              }

              return (
                <Fragment key={rowId}>
                  <TableRow
                    className={cn(
                      isSelected && 'bg-muted/50',
                      stripedRows && rowIdx % 2 === 1 && 'bg-muted/30',
                      !showRowBorders && 'border-0',
                      onRowClick && 'cursor-pointer',
                      compactMode && 'h-10',
                      rowClass
                    )}
                    onClick={() => onRowClick?.(rowData)}
                    onDoubleClick={() => onRowDoubleClick?.(rowData)}
                    data-state={isSelected ? 'selected' : undefined}
                  >
                    {/* Selection cell */}
                    {features.selection && (
                      <TableCell
                        className={cn('w-[40px]', compactMode && 'py-1')}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => actions.toggleSelection(rowId)}
                          aria-label={`Select row ${rowIdx + 1}`}
                        />
                      </TableCell>
                    )}

                    {/* Expand cell */}
                    {features.expandableRows && (
                      <TableCell
                        className={cn('w-[40px]', compactMode && 'py-1')}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => actions.toggleRowExpansion(rowId)}
                          aria-label={isExpanded ? 'Collapse row' : 'Expand row'}
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </Button>
                      </TableCell>
                    )}

                    {/* Data cells */}
                    {row.getVisibleCells().map((cell) => (
                      <TableCell
                        key={cell.id}
                        className={cn(compactMode && 'py-1')}
                      >
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext()
                        )}
                      </TableCell>
                    ))}

                    {/* Row actions cell */}
                    {features.rowActions && rowActions.length > 0 && (
                      <TableCell
                        className={cn('w-[50px]', compactMode && 'py-1')}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <RowActionsMenu
                          rowData={rowData}
                          actions={rowActions as RowAction<unknown>[]}
                        />
                      </TableCell>
                    )}
                  </TableRow>

                  {/* Expanded row content */}
                  {features.expandableRows && isExpanded && renderExpandedRow && (
                    <TableRow>
                      <TableCell
                        colSpan={
                          row.getVisibleCells().length +
                          (features.selection ? 1 : 0) +
                          1 + // expand column
                          (features.rowActions && rowActions.length > 0 ? 1 : 0)
                        }
                        className="p-0"
                      >
                        <div className="px-4 py-3 bg-muted/50">
                          {renderExpandedRow(rowData)}
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}

/**
 * Row Actions Menu Component
 */
function RowActionsMenu<TData>({
  rowData,
  actions,
}: {
  rowData: TData;
  actions: RowAction<TData>[];
}) {
  // Filter visible actions
  const visibleActions = actions.filter((action) => {
    if (typeof action.hidden === 'function') {
      return !action.hidden(rowData);
    }
    return !action.hidden;
  });

  if (visibleActions.length === 0) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <MoreHorizontal className="h-4 w-4" />
          <span className="sr-only">Open menu</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Actions</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {visibleActions.map((action) => {
          const isDisabled =
            typeof action.disabled === 'function'
              ? action.disabled(rowData)
              : action.disabled;

          return (
            <DropdownMenuItem
              key={action.id}
              onClick={() => action.onClick(rowData)}
              disabled={isDisabled}
              className={cn(
                action.variant === 'destructive' && 'text-destructive focus:text-destructive'
              )}
            >
              {action.icon && <span className="mr-2">{action.icon}</span>}
              {action.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default BdhDataGridTable;
