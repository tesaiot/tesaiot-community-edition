/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useBdhDataGridContext } from './bdh-data-grid-context';
import { cn } from '@/lib/utils';

interface BdhDataGridPaginationProps {
  className?: string;
  showRowsPerPage?: boolean;
  showPageNumbers?: boolean;
  showItemCount?: boolean;
  showFirstLast?: boolean;
}

/**
 * BdhDataGridPagination Component
 *
 * Displays pagination controls including:
 * - Rows per page selector
 * - Current item range (e.g., "1-10 of 100")
 * - Page navigation buttons
 * - Page number buttons (optional)
 *
 * @example
 * ```tsx
 * <BdhDataGrid data={data} columns={columns}>
 *   <BdhDataGridTable />
 *   <BdhDataGridPagination
 *     showRowsPerPage={true}
 *     showPageNumbers={true}
 *   />
 * </BdhDataGrid>
 * ```
 */
export function BdhDataGridPagination({
  className,
  showRowsPerPage = true,
  showPageNumbers = true,
  showItemCount = true,
  showFirstLast = false,
}: BdhDataGridPaginationProps) {
  const { pagination, actions, features, isLoading } = useBdhDataGridContext();

  // Don't render if pagination is disabled
  if (!features.pagination) {
    return null;
  }

  const {
    currentPage,
    pageSize,
    totalPages,
    totalItems,
    startIndex,
    endIndex,
    canNextPage,
    canPrevPage,
    pageNumbers,
    pageSizeOptions,
  } = pagination;

  const { setPage, setPageSize, nextPage, prevPage } = actions;

  return (
    <div
      className={cn(
        'flex flex-col sm:flex-row items-center justify-between gap-4 px-2 py-4',
        className
      )}
    >
      {/* Left side: Rows per page */}
      {showRowsPerPage && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Rows per page:</span>
          <Select
            value={String(pageSize)}
            onValueChange={(value) => setPageSize(Number(value))}
            disabled={isLoading}
          >
            <SelectTrigger className="h-8 w-[70px]">
              <SelectValue placeholder={String(pageSize)} />
            </SelectTrigger>
            <SelectContent>
              {pageSizeOptions.map((size) => (
                <SelectItem key={size} value={String(size)}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Center/Right: Item count and navigation */}
      <div className="flex items-center gap-4">
        {/* Item count */}
        {showItemCount && (
          <div className="text-sm text-muted-foreground whitespace-nowrap">
            {totalItems > 0 ? (
              <>
                {startIndex + 1}-{endIndex} of {totalItems}
              </>
            ) : (
              'No items'
            )}
          </div>
        )}

        {/* Navigation */}
        <div className="flex items-center gap-1">
          {/* First page button */}
          {showFirstLast && (
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage(1)}
              disabled={!canPrevPage || isLoading}
              aria-label="First page"
            >
              <ChevronsLeft className="h-4 w-4" />
            </Button>
          )}

          {/* Previous page button */}
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={prevPage}
            disabled={!canPrevPage || isLoading}
            aria-label="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {/* Page numbers */}
          {showPageNumbers && totalPages > 1 && (
            <div className="flex items-center gap-1">
              {pageNumbers.map((pageNum, idx) => {
                // Handle ellipsis
                if (pageNum < 0) {
                  return (
                    <span
                      key={`ellipsis-${idx}`}
                      className="px-2 text-muted-foreground"
                    >
                      ...
                    </span>
                  );
                }

                return (
                  <Button
                    key={pageNum}
                    variant={pageNum === currentPage ? 'default' : 'outline'}
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setPage(pageNum)}
                    disabled={isLoading}
                    aria-label={`Page ${pageNum}`}
                    aria-current={pageNum === currentPage ? 'page' : undefined}
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </div>
          )}

          {/* Next page button */}
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={nextPage}
            disabled={!canNextPage || isLoading}
            aria-label="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>

          {/* Last page button */}
          {showFirstLast && (
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => setPage(totalPages)}
              disabled={!canNextPage || isLoading}
              aria-label="Last page"
            >
              <ChevronsRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

export default BdhDataGridPagination;
