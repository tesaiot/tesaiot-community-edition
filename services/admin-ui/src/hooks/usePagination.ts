/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import type { UsePaginationOptions, UsePaginationReturn } from '@/components/ui/bdh-data-grid/types';

const DEFAULT_PAGE_SIZE_OPTIONS = [10, 20, 50, 100];
const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_PAGE = 1;
const MAX_VISIBLE_PAGES = 5;

/**
 * Calculate visible page numbers with ellipsis support
 */
function calculatePageNumbers(currentPage: number, totalPages: number): number[] {
  if (totalPages <= MAX_VISIBLE_PAGES) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: number[] = [];
  const halfVisible = Math.floor(MAX_VISIBLE_PAGES / 2);

  let startPage = Math.max(1, currentPage - halfVisible);
  let endPage = Math.min(totalPages, currentPage + halfVisible);

  // Adjust if we're near the beginning
  if (currentPage <= halfVisible) {
    endPage = MAX_VISIBLE_PAGES;
  }

  // Adjust if we're near the end
  if (currentPage > totalPages - halfVisible) {
    startPage = totalPages - MAX_VISIBLE_PAGES + 1;
  }

  // Always include first page
  if (startPage > 1) {
    pages.push(1);
    if (startPage > 2) {
      pages.push(-1); // -1 represents ellipsis
    }
  }

  // Add visible pages
  for (let i = startPage; i <= endPage; i++) {
    if (i > 0 && i <= totalPages && !pages.includes(i)) {
      pages.push(i);
    }
  }

  // Always include last page
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      pages.push(-2); // -2 represents ellipsis (different key)
    }
    pages.push(totalPages);
  }

  return pages;
}

/**
 * usePagination Hook
 *
 * @example
 * ```tsx
 * const pagination = usePagination({
 *   totalItems: data.length,
 *   initialPageSize: 20,
 *   onPageChange: (page, pageSize) => fetchData(page, pageSize)
 * });
 *
 * const paginatedData = data.slice(pagination.startIndex, pagination.endIndex);
 * ```
 */
export function usePagination(options: UsePaginationOptions): UsePaginationReturn {
  const {
    initialPage = DEFAULT_PAGE,
    initialPageSize = DEFAULT_PAGE_SIZE,
    pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS,
    totalItems,
    onPageChange,
  } = options;

  // State
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize, setPageSizeState] = useState(initialPageSize);

  // Derived values
  const totalPages = useMemo(() => {
    return Math.max(1, Math.ceil(totalItems / pageSize));
  }, [totalItems, pageSize]);

  const startIndex = useMemo(() => {
    return (currentPage - 1) * pageSize;
  }, [currentPage, pageSize]);

  const endIndex = useMemo(() => {
    return Math.min(startIndex + pageSize, totalItems);
  }, [startIndex, pageSize, totalItems]);

  const canNextPage = useMemo(() => {
    return currentPage < totalPages;
  }, [currentPage, totalPages]);

  const canPrevPage = useMemo(() => {
    return currentPage > 1;
  }, [currentPage]);

  const pageNumbers = useMemo(() => {
    return calculatePageNumbers(currentPage, totalPages);
  }, [currentPage, totalPages]);

  // Ensure current page is valid when totalItems or pageSize changes
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  // Actions
  const setPage = useCallback(
    (page: number) => {
      const validPage = Math.max(1, Math.min(page, totalPages));
      if (validPage !== currentPage) {
        setCurrentPage(validPage);
        onPageChange?.(validPage, pageSize);
      }
    },
    [currentPage, totalPages, pageSize, onPageChange]
  );

  const setPageSize = useCallback(
    (size: number) => {
      if (size !== pageSize && pageSizeOptions.includes(size)) {
        setPageSizeState(size);
        // Reset to page 1 when page size changes
        setCurrentPage(1);
        onPageChange?.(1, size);
      }
    },
    [pageSize, pageSizeOptions, onPageChange]
  );

  const nextPage = useCallback(() => {
    if (canNextPage) {
      setPage(currentPage + 1);
    }
  }, [canNextPage, currentPage, setPage]);

  const prevPage = useCallback(() => {
    if (canPrevPage) {
      setPage(currentPage - 1);
    }
  }, [canPrevPage, currentPage, setPage]);

  const reset = useCallback(() => {
    setCurrentPage(initialPage);
    setPageSizeState(initialPageSize);
    onPageChange?.(initialPage, initialPageSize);
  }, [initialPage, initialPageSize, onPageChange]);

  return {
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
    setPage,
    setPageSize,
    nextPage,
    prevPage,
    reset,
  };
}

export default usePagination;
