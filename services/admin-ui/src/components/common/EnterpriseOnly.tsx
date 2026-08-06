/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Marking a capability that the Community Edition does not ship.
 *
 * CE inherited screens from the full platform that describe workflows it cannot
 * perform — OPTIGA Trust M Protected Update being the clearest case: the UI told
 * the operator to "trigger a Protected Update job", but no such job exists in
 * this build (there is no protected_update service and PRINCIPLES/ncsa document
 * the omission). Instructions for a button that is not there read as a bug in
 * the install long before they read as an edition boundary.
 *
 * The honest fix is to say which edition the step belongs to and keep the
 * explanation — the information is still useful to someone planning a fleet, and
 * deleting it would leave the surrounding OID guidance dangling. These two
 * components are that marker, so the wording stays consistent wherever it
 * appears rather than being re-invented per screen.
 */

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

/** Inline chip: put it next to a heading or list item that names the feature. */
export function EnterpriseOnlyBadge({ className }: { className?: string }) {
  return (
    <Badge
      variant="warning"
      appearance="outline"
      size="sm"
      className={cn('align-middle', className)}
      title="Available in TESAIoT Enterprise Cloud — not shipped in the Community Edition"
    >
      Enterprise only
    </Badge>
  );
}

/**
 * Block note for a paragraph that describes an unavailable workflow.
 *
 * `feature` names the capability; `children` may add what CE does instead, which
 * is usually the more useful half — an operator who cannot run Protected Update
 * still needs to know the CSR path exists.
 */
export function EnterpriseOnlyNote({
  feature,
  className,
  children,
}: {
  feature: string;
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        'rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-900',
        'dark:border-yellow-950 dark:bg-yellow-950/40 dark:text-yellow-200',
        className,
      )}
    >
      <span className="font-medium">{feature}</span> is part of TESAIoT
      Enterprise Cloud and is not shipped in the Community Edition. The steps
      below are documented so a fleet can be planned against them; this build
      cannot run them.
      {children ? <div className="mt-1">{children}</div> : null}
    </div>
  );
}
