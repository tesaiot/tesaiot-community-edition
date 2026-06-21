/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { ShieldCheck, Shield, Check, X, BookOpen } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { useLicenseContext } from '@/providers/license-provider';

// Authoritative posture figures, kept in step with the header
// ETSIComplianceBadge. The Community Edition ships the server-side technical
// controls — about the Level 1-2 baseline — and is honest about the gaps.
const ETSI_TOTAL = 13;
const ISO_TOTAL = 8;

function Standard({
  icon, name, met, total,
}: { icon: React.ReactNode; name: string; met: number; total: number }) {
  const pct = Math.round((met / total) * 100);
  const colour = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium">{name}</span>
        </div>
        <span className="text-sm font-semibold">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
        <div className={cn('h-full transition-all duration-500', colour)} style={{ width: `${pct}%` }} />
      </div>
      <p className="text-xs text-muted-foreground mt-1">{met} of {total} requirements met</p>
    </div>
  );
}

export default function CompliancePage() {
  const { edition } = useLicenseContext();
  const isCommercial = edition !== 'community';

  const etsiMet = isCommercial ? ETSI_TOTAL : 9;
  const isoMet = isCommercial ? ISO_TOTAL : 5;

  const keyAreas = [
    { name: 'No Default Passwords', status: true },
    { name: 'Secure Communication', status: true },
    { name: 'Regular Updates', status: true },
    { name: 'Data Protection', status: true },
    { name: 'Input Validation', status: isCommercial },
    { name: 'Privacy Controls', status: isCommercial },
  ];

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 p-2">
            <ShieldCheck className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Compliance</h1>
            <p className="text-sm text-muted-foreground">
              Security standards posture for this deployment (ETSI EN 303 645 and related controls).
            </p>
          </div>
        </div>
        <Badge
          variant="outline"
          className="border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-400"
        >
          {isCommercial ? '100% · commercial' : 'about 70% baseline · platform layer'}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Standards coverage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <Standard icon={<Shield className="h-4 w-4 text-primary" />} name="ETSI EN 303 645" met={etsiMet} total={ETSI_TOTAL} />
          <Standard icon={<ShieldCheck className="h-4 w-4 text-primary" />} name="ISO/IEC 27402" met={isoMet} total={ISO_TOTAL} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Key compliance areas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {keyAreas.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                {item.status
                  ? <Check className="h-4 w-4 text-emerald-500 shrink-0" />
                  : <X className="h-4 w-4 text-amber-500 shrink-0" />}
                <span className="text-sm">{item.name}</span>
                {!item.status && (
                  <span className="text-xs text-muted-foreground">(operator / roadmap)</span>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What this means</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Out of the box, the Community Edition implements the <span className="text-foreground font-medium">server-side
            technical controls</span> of ETSI EN 303 645 / NCSA — about 70% of the Level 1-2 baseline,
            verified against the codebase: per-device X.509 identities via Vault PKI, non-spoofable mTLS,
            fail-closed authentication with brute-force lockout, AEAD-only TLS, attack-surface
            minimization, input validation, and a published vulnerability-disclosure policy.
          </p>
          <p>
            Because you self-host, the final posture also depends on you: coverage rises toward full
            when CE is paired with a secure device (hardware secure element / HSM plus secure boot)
            and sound operations (timely updates, monitoring). Privacy/consent UX, cryptographically
            signed updates and accredited penetration testing are operator responsibilities or on the
            roadmap — the gaps are published as openly as the strengths.
          </p>
          <p className="flex items-center gap-2 text-foreground">
            <BookOpen className="h-4 w-4 text-emerald-500" />
            Full mapping and methodology: <code className="text-xs">docs/en/compliance-en-303-645-ncsa.md</code>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
