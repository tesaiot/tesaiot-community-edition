/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useState, useCallback, useMemo } from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import type { ExportFormat, UseExportOptions, UseExportReturn } from '@/components/ui/bdh-data-grid/types';

/**
 * Extract header name from column definition
 */
function getColumnHeader<TData>(column: ColumnDef<TData, unknown>): string {
  if (typeof column.header === 'string') {
    return column.header;
  }
  // Fallback to column ID
  return (column as { id?: string }).id || 'Unknown';
}

/**
 * Extract cell value from row based on column definition
 */
function getCellValue<TData>(row: TData, column: ColumnDef<TData, unknown>): string {
  const accessorKey = (column as { accessorKey?: string }).accessorKey;
  const accessorFn = (column as { accessorFn?: (row: TData) => unknown }).accessorFn;

  let value: unknown;

  if (accessorKey) {
    // Handle nested keys like "device.name"
    value = accessorKey.split('.').reduce((obj: unknown, key) => {
      if (obj && typeof obj === 'object') {
        return (obj as Record<string, unknown>)[key];
      }
      return undefined;
    }, row as unknown);
  } else if (accessorFn) {
    value = accessorFn(row);
  } else {
    value = '';
  }

  // Convert value to string
  if (value === null || value === undefined) {
    return '';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

/**
 * Escape CSV field (handle commas, quotes, newlines)
 */
function escapeCSVField(value: string): string {
  // If value contains comma, quote, or newline, wrap in quotes and escape existing quotes
  if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Convert data to CSV string
 */
function toCSV<TData>(data: TData[], columns: ColumnDef<TData, unknown>[]): string {
  // Filter out non-exportable columns (like selection or actions)
  const exportableColumns = columns.filter((col) => {
    const colId = (col as { id?: string }).id;
    return colId !== 'select' && colId !== 'actions' && colId !== 'expand';
  });

  // Create header row
  const headers = exportableColumns.map((col) => escapeCSVField(getColumnHeader(col)));
  const headerRow = headers.join(',');

  // Create data rows
  const dataRows = data.map((row) => {
    const values = exportableColumns.map((col) => escapeCSVField(getCellValue(row, col)));
    return values.join(',');
  });

  // Combine with BOM for Excel UTF-8 compatibility
  return '\uFEFF' + [headerRow, ...dataRows].join('\r\n');
}

/**
 * Convert data to JSON string
 */
function toJSON<TData>(data: TData[], columns: ColumnDef<TData, unknown>[]): string {
  // Filter out non-exportable columns
  const exportableColumns = columns.filter((col) => {
    const colId = (col as { id?: string }).id;
    return colId !== 'select' && colId !== 'actions' && colId !== 'expand';
  });

  // Create export objects with column headers as keys
  const exportData = data.map((row) => {
    const obj: Record<string, string> = {};
    exportableColumns.forEach((col) => {
      const header = getColumnHeader(col);
      obj[header] = getCellValue(row, col);
    });
    return obj;
  });

  return JSON.stringify(exportData, null, 2);
}

/**
 * Download content as file
 */
function downloadFile(content: string | Blob, filename: string, mimeType: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generate filename with timestamp
 */
function generateFilename(baseName: string, extension: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  return `${baseName}-${timestamp}.${extension}`;
}

/**
 * useExport Hook
 *
 * @example
 * ```tsx
 * const { exportCSV, exportExcel, exportJSON, isExporting } = useExport({
 *   data: devices,
 *   columns: tableColumns,
 *   filename: 'devices',
 * });
 *
 * <Button onClick={exportCSV} disabled={isExporting}>
 *   Export CSV
 * </Button>
 * ```
 */
export function useExport<TData>(options: UseExportOptions<TData>): UseExportReturn {
  const {
    data,
    columns,
    filename = 'export',
    formats = ['csv', 'excel', 'json'],
    onExport,
  } = options;

  const [isExporting, setIsExporting] = useState(false);

  const supportedFormats = useMemo(() => formats, [formats]);

  // Export to CSV
  const exportCSV = useCallback(async () => {
    if (isExporting) return;
    setIsExporting(true);

    try {
      const csvContent = toCSV(data, columns);
      const csvFilename = generateFilename(filename, 'csv');
      downloadFile(csvContent, csvFilename, 'text/csv;charset=utf-8');
      onExport?.('csv', data);
    } catch (error) {
      console.error('[useExport] CSV export failed:', error);
    } finally {
      setIsExporting(false);
    }
  }, [data, columns, filename, isExporting, onExport]);

  // Export to Excel (XLSX)
  const exportExcel = useCallback(async () => {
    if (isExporting) return;
    setIsExporting(true);

    try {
      // Dynamic import xlsx library
      const XLSX = await import('xlsx').catch(() => null);

      if (!XLSX) {
        // Fallback to CSV if xlsx not available
        console.warn('[useExport] xlsx library not available, falling back to CSV');
        const csvContent = toCSV(data, columns);
        const csvFilename = generateFilename(filename, 'csv');
        downloadFile(csvContent, csvFilename, 'text/csv;charset=utf-8');
        onExport?.('excel', data);
        return;
      }

      // Filter exportable columns
      const exportableColumns = columns.filter((col) => {
        const colId = (col as { id?: string }).id;
        return colId !== 'select' && colId !== 'actions' && colId !== 'expand';
      });

      // Create worksheet data
      const headers = exportableColumns.map((col) => getColumnHeader(col));
      const rows = data.map((row) =>
        exportableColumns.map((col) => getCellValue(row, col))
      );

      const wsData = [headers, ...rows];

      // Create workbook and worksheet
      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.aoa_to_sheet(wsData);

      // Auto-size columns
      const colWidths = headers.map((header, i) => {
        const maxDataLength = Math.max(
          header.length,
          ...rows.map((row) => String(row[i] || '').length)
        );
        return { wch: Math.min(maxDataLength + 2, 50) };
      });
      ws['!cols'] = colWidths;

      XLSX.utils.book_append_sheet(wb, ws, 'Data');

      // Generate and download
      const xlsxFilename = generateFilename(filename, 'xlsx');
      XLSX.writeFile(wb, xlsxFilename);
      onExport?.('excel', data);
    } catch (error) {
      console.error('[useExport] Excel export failed:', error);
    } finally {
      setIsExporting(false);
    }
  }, [data, columns, filename, isExporting, onExport]);

  // Export to JSON
  const exportJSON = useCallback(async () => {
    if (isExporting) return;
    setIsExporting(true);

    try {
      const jsonContent = toJSON(data, columns);
      const jsonFilename = generateFilename(filename, 'json');
      downloadFile(jsonContent, jsonFilename, 'application/json');
      onExport?.('json', data);
    } catch (error) {
      console.error('[useExport] JSON export failed:', error);
    } finally {
      setIsExporting(false);
    }
  }, [data, columns, filename, isExporting, onExport]);

  // Generic export function
  const exportData = useCallback(
    async (format: ExportFormat) => {
      switch (format) {
        case 'csv':
          await exportCSV();
          break;
        case 'excel':
          await exportExcel();
          break;
        case 'json':
          await exportJSON();
          break;
        default:
          console.warn(`[useExport] Unknown export format: ${format}`);
      }
    },
    [exportCSV, exportExcel, exportJSON]
  );

  return {
    exportCSV,
    exportExcel,
    exportJSON,
    exportData,
    isExporting,
    supportedFormats,
  };
}

export default useExport;
