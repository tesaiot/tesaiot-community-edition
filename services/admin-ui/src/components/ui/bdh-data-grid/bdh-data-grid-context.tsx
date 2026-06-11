/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { createContext, useContext, ReactNode } from 'react';
import type { BdhDataGridContextValue } from './types';

// Create context with undefined default (will be provided by BdhDataGrid)
const BdhDataGridContext = createContext<BdhDataGridContextValue<unknown> | undefined>(
  undefined
);

/**
 * Provider component for BdhDataGrid context
 */
export function BdhDataGridProvider<TData>({
  children,
  value,
}: {
  children: ReactNode;
  value: BdhDataGridContextValue<TData>;
}) {
  return (
    <BdhDataGridContext.Provider value={value as BdhDataGridContextValue<unknown>}>
      {children}
    </BdhDataGridContext.Provider>
  );
}

/**
 * Hook to access BdhDataGrid context
 *
 * @throws Error if used outside of BdhDataGrid
 *
 * @example
 * ```tsx
 * function MyCustomPagination() {
 *   const { pagination, actions } = useBdhDataGridContext();
 *   return (
 *     <div>
 *       Page {pagination.currentPage} of {pagination.totalPages}
 *       <button onClick={actions.nextPage}>Next</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useBdhDataGridContext<TData = unknown>(): BdhDataGridContextValue<TData> {
  const context = useContext(BdhDataGridContext);

  if (context === undefined) {
    throw new Error(
      'useBdhDataGridContext must be used within a BdhDataGrid component'
    );
  }

  return context as BdhDataGridContextValue<TData>;
}

export default BdhDataGridContext;
