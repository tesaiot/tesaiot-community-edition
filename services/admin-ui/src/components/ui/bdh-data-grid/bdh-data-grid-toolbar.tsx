/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback } from 'react';
import {
  Search,
  SlidersHorizontal,
  Columns,
  Download,
  RefreshCw,
  Loader2,
  X,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';
import { useBdhDataGridContext } from './bdh-data-grid-context';
import { cn } from '@/lib/utils';
import type { ExportFormat, FilterConfig } from './types';

interface BdhDataGridToolbarProps {
  className?: string;
  searchPlaceholder?: string;
  filterConfig?: FilterConfig[];
  exportFormats?: ExportFormat[];
  showSearch?: boolean;
  showFilters?: boolean;
  showColumnVisibility?: boolean;
  showExport?: boolean;
  showRefresh?: boolean;
  customActions?: React.ReactNode;
}

/**
 * BdhDataGridToolbar Component
 *
 * Provides controls for:
 * - Global search
 * - Column filters
 * - Column visibility toggle
 * - Data export
 * - Manual refresh
 *
 * @example
 * ```tsx
 * <BdhDataGrid data={data} columns={columns}>
 *   <BdhDataGridToolbar
 *     searchPlaceholder="Search devices..."
 *     showExport={true}
 *     exportFormats={['csv', 'excel']}
 *   />
 *   <BdhDataGridTable />
 * </BdhDataGrid>
 * ```
 */
export function BdhDataGridToolbar({
  className,
  searchPlaceholder = 'Search...',
  filterConfig,
  exportFormats = ['csv', 'excel', 'json'],
  showSearch,
  showFilters,
  showColumnVisibility,
  showExport,
  showRefresh,
  customActions,
}: BdhDataGridToolbarProps) {
  const { table, features, actions, sync, isLoading } = useBdhDataGridContext();

  const [searchTerm, setSearchTerm] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  // Determine which features to show
  const shouldShowSearch = showSearch ?? features.search;
  const shouldShowFilters = showFilters ?? features.columnFilters;
  const shouldShowColumnVisibility = showColumnVisibility ?? features.columnVisibility;
  const shouldShowExport = showExport ?? features.export;
  const shouldShowRefresh = showRefresh ?? features.autoSync;

  // Handle search
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchTerm(value);
      actions.setSearchTerm(value);
    },
    [actions]
  );

  // Handle export
  const handleExport = useCallback(
    async (format: ExportFormat) => {
      setIsExporting(true);
      try {
        actions.exportData(format);
      } finally {
        setIsExporting(false);
      }
    },
    [actions]
  );

  // Get visible column count
  const allColumns = table.getAllColumns().filter(
    (col) => col.id !== 'select' && col.id !== 'actions' && col.id !== 'expand'
  );
  const visibleColumns = allColumns.filter((col) => col.getIsVisible());
  const hiddenCount = allColumns.length - visibleColumns.length;

  return (
    <div
      className={cn(
        'flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-4',
        className
      )}
    >
      {/* Left side: Search and filters */}
      <div className="flex flex-1 items-center gap-2 w-full sm:w-auto">
        {/* Search */}
        {shouldShowSearch && (
          <div className="relative flex-1 sm:flex-none sm:w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={searchPlaceholder}
              value={searchTerm}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-8 pr-8"
              disabled={isLoading}
            />
            {searchTerm && (
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-9 w-9"
                onClick={() => handleSearchChange('')}
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        )}

        {/* Filters */}
        {shouldShowFilters && filterConfig && filterConfig.length > 0 && (
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" disabled={isLoading}>
                <SlidersHorizontal className="h-4 w-4 mr-2" />
                Filters
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80" align="start">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="font-medium">Filters</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={actions.clearFilters}
                  >
                    Clear all
                  </Button>
                </div>
                {/* Filter controls would be rendered here based on filterConfig */}
                <p className="text-sm text-muted-foreground">
                  Filter configuration coming soon...
                </p>
              </div>
            </PopoverContent>
          </Popover>
        )}
      </div>

      {/* Right side: Actions */}
      <div className="flex items-center gap-2">
        {/* Custom actions */}
        {customActions}

        {/* Column visibility */}
        {shouldShowColumnVisibility && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" disabled={isLoading}>
                <Columns className="h-4 w-4 mr-2" />
                Columns
                {hiddenCount > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {hiddenCount} hidden
                  </Badge>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {allColumns.map((column) => {
                const header = column.columnDef.header;
                const headerText =
                  typeof header === 'string'
                    ? header
                    : column.id;

                return (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    checked={column.getIsVisible()}
                    onCheckedChange={(checked) => column.toggleVisibility(checked)}
                  >
                    {headerText}
                  </DropdownMenuCheckboxItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Export */}
        {shouldShowExport && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" disabled={isLoading || isExporting}>
                {isExporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Export as</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {exportFormats.includes('csv') && (
                <DropdownMenuCheckboxItem
                  checked={false}
                  onCheckedChange={() => handleExport('csv')}
                >
                  CSV (.csv)
                </DropdownMenuCheckboxItem>
              )}
              {exportFormats.includes('excel') && (
                <DropdownMenuCheckboxItem
                  checked={false}
                  onCheckedChange={() => handleExport('excel')}
                >
                  Excel (.xlsx)
                </DropdownMenuCheckboxItem>
              )}
              {exportFormats.includes('json') && (
                <DropdownMenuCheckboxItem
                  checked={false}
                  onCheckedChange={() => handleExport('json')}
                >
                  JSON (.json)
                </DropdownMenuCheckboxItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Refresh */}
        {shouldShowRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={actions.refresh}
            disabled={isLoading || sync.isSyncing}
          >
            <RefreshCw
              className={cn(
                'h-4 w-4 mr-2',
                sync.isSyncing && 'animate-spin'
              )}
            />
            Refresh
          </Button>
        )}

        {/* Sync status indicator */}
        {features.autoSync && sync.lastSyncedAt && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Check className="h-3 w-3 text-green-500" />
            <span>
              Synced {formatTimeAgo(sync.lastSyncedAt)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Format time ago (e.g., "2 minutes ago")
 */
function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

  if (seconds < 60) {
    return 'just now';
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default BdhDataGridToolbar;
