/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * First-run setup wizard (Community Edition).
 *
 * Shown only while the instance is unclaimed (no administrator exists). Gated
 * server-side by the one-time SETUP_TOKEN printed by the installer; after
 * completion every setup endpoint permanently refuses, so this page simply
 * redirects to sign-in. Visual language mirrors the sign-in screen: radial
 * midnight backdrop + glassmorphism card.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  Database,
  Eye,
  EyeOff,
  Globe,
  KeyRound,
  Loader2,
  Lock,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toAbsoluteUrl } from '@/lib/helpers';
import { isValidEmail } from '@/lib/email';

type SetupStatus = {
  setup_required: boolean;
  version?: string;
  domain?: string;
  admin_email_prefill?: string;
  timezone?: string;
  token_configured?: boolean;
  health?: { mongodb?: boolean; redis?: boolean; vault?: boolean };
};

const STEPS = [
  { id: 1, label: 'Welcome' },
  { id: 2, label: 'Administrator' },
  { id: 3, label: 'Organization' },
  { id: 4, label: 'Finish' },
] as const;

// Mirrors the server-side validate_password policy exactly.
const PASSWORD_RULES = [
  { key: 'length', label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { key: 'upper', label: 'An uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
  { key: 'lower', label: 'A lowercase letter', test: (p: string) => /[a-z]/.test(p) },
  { key: 'digit', label: 'A number', test: (p: string) => /[0-9]/.test(p) },
  {
    key: 'special',
    label: 'A special character',
    test: (p: string) => /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(p),
  },
] as const;

const inputClass =
  'w-full rounded-lg border border-white/10 bg-white/[0.06] px-3.5 py-2.5 text-sm text-white ' +
  'placeholder:text-slate-500 outline-none transition-colors ' +
  'focus:border-sky-400/60 focus:bg-white/[0.08] focus:ring-2 focus:ring-sky-400/20';

const labelClass = 'mb-1.5 block text-[13px] font-medium text-slate-300';

function HealthChip({ ok, label }: { ok?: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.04] px-3 py-2">
      <span
        className={`h-2 w-2 rounded-full ${ok ? 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.8)]' : 'bg-amber-400'}`}
      />
      <span className="text-xs font-medium text-slate-200">{label}</span>
    </div>
  );
}

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="mb-8 flex items-center justify-center">
      {STEPS.map((step, i) => {
        const done = current > step.id;
        const active = current === step.id;
        return (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={
                  'flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-all duration-300 ' +
                  (done
                    ? 'border-emerald-400/70 bg-emerald-400/15 text-emerald-300'
                    : active
                      ? 'border-sky-400/80 bg-sky-400/15 text-sky-200 ring-4 ring-sky-400/10'
                      : 'border-white/15 bg-white/[0.03] text-slate-500')
                }
              >
                {done ? <Check className="h-4 w-4" /> : step.id}
              </div>
              <span
                className={
                  'mt-1.5 text-[11px] font-medium tracking-wide ' +
                  (active ? 'text-sky-200' : done ? 'text-emerald-300/80' : 'text-slate-500')
                }
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={
                  'mx-2 mb-5 h-px w-10 transition-colors duration-300 sm:w-14 ' +
                  (current > step.id ? 'bg-emerald-400/50' : 'bg-white/10')
                }
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function SetupWizardPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [completed, setCompleted] = useState(false);

  // Form state
  const [token, setToken] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [orgName, setOrgName] = useState('');
  const [timezone, setTimezone] = useState('');

  useEffect(() => {
    fetch('/api/v1/setup/status')
      .then((r) => r.json())
      .then((s: SetupStatus) => {
        if (!s.setup_required) {
          navigate('/auth/signin', { replace: true });
          return;
        }
        setStatus(s);
        setEmail((prev) => prev || s.admin_email_prefill || '');
        setTimezone((prev) => prev || s.timezone || '');
      })
      .catch(() => setError('Cannot reach the platform API. Is the stack running?'));
  }, [navigate]);

  const passwordChecks = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, ok: r.test(password) })),
    [password],
  );
  const passwordValid = passwordChecks.every((c) => c.ok);
  const emailValid = isValidEmail(email);

  const verifyToken = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const res = await fetch('/api/v1/setup/verify-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.trim() }),
      });
      if (res.ok) {
        setStep(2);
      } else if (res.status === 410) {
        navigate('/auth/signin', { replace: true });
      } else {
        setError('That setup token is not valid. It was printed by "make install" and is stored in .env as SETUP_TOKEN.');
      }
    } catch {
      setError('Could not verify the token — the API is unreachable.');
    } finally {
      setBusy(false);
    }
  }, [token, navigate]);

  const completeSetup = useCallback(async () => {
    setBusy(true);
    setError('');
    try {
      const res = await fetch('/api/v1/setup/complete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token.trim()}`,
        },
        body: JSON.stringify({
          email: email.trim(),
          username: username.trim() || 'admin',
          password,
          organization_name: orgName.trim(),
          timezone: timezone.trim(),
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 201) {
        setCompleted(true);
      } else if (res.status === 410) {
        navigate('/auth/signin', { replace: true });
      } else {
        setError(body.error || 'Setup failed — please review your entries and try again.');
        if (body.field === 'password') setStep(2);
        if (body.field === 'email') setStep(2);
      }
    } catch {
      setError('Could not complete setup — the API is unreachable.');
    } finally {
      setBusy(false);
    }
  }, [token, email, username, password, orgName, timezone, navigate]);

  const canContinueStep2 = emailValid && passwordValid && password === confirm;

  return (
    <div
      className="fixed inset-0 overflow-y-auto"
      style={{
        background:
          'radial-gradient(125% 125% at 50% 10%, #1e293b 0%, #0f172a 45%, #020617 100%)',
      }}
    >
      <div className="flex min-h-full items-center justify-center p-4 py-10">
        <div className="w-full max-w-xl">
          {/* Brand */}
          <div className="mb-6 text-center">
            <img
              src={toAbsoluteUrl('/images/TESA_logo.png')}
              className="mx-auto mb-3 h-20"
              alt="TESA Logo"
            />
            <h1 className="text-xl font-semibold text-white">
              TES
              <span style={{ fontSize: '1.4em', verticalAlign: 'super', position: 'relative', top: '0.26em' }}>
                ⩓
              </span>
              IoT Platform
            </h1>
            <p className="mt-1 text-[13px] font-medium tracking-wide text-slate-400">
              FIRST-RUN SETUP
            </p>
          </div>

          {/* Card */}
          <div className="rounded-2xl border border-white/[0.05] bg-white/[0.09] p-8 shadow-2xl backdrop-blur-md dark:bg-gray-900/[0.09]">
            {completed ? (
              /* ------------------------------------------------ Success */
              <div className="py-6 text-center">
                <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-full border border-emerald-400/40 bg-emerald-400/10 ring-8 ring-emerald-400/5">
                  <Check className="h-8 w-8 text-emerald-300" />
                </div>
                <h2 className="text-lg font-semibold text-white">Your platform is ready</h2>
                <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
                  The administrator account <span className="text-slate-200">{email}</span> has been
                  created and the setup token is now permanently inert.
                </p>
                <button
                  onClick={() => navigate('/auth/signin', { replace: true })}
                  className="mt-7 inline-flex items-center gap-2 rounded-lg bg-sky-500 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition hover:bg-sky-400"
                >
                  Continue to sign in <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <>
                <StepIndicator current={step} />

                {error && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-lg border border-red-400/30 bg-red-400/10 px-3.5 py-3 text-[13px] leading-relaxed text-red-200">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {/* ------------------------------------------------ Step 1 */}
                {step === 1 && (
                  <div>
                    <h2 className="text-lg font-semibold text-white">Welcome</h2>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                      This instance has not been claimed yet. Enter the one-time setup token to
                      create the administrator account — it was printed by{' '}
                      <code className="rounded bg-white/10 px-1.5 py-0.5 text-[12px] text-sky-200">
                        make install
                      </code>{' '}
                      and stored in <code className="rounded bg-white/10 px-1.5 py-0.5 text-[12px] text-sky-200">.env</code>.
                    </p>

                    <div className="mt-5 grid grid-cols-3 gap-2">
                      <HealthChip ok={status?.health?.mongodb} label="Database" />
                      <HealthChip ok={status?.health?.vault} label="Vault PKI" />
                      <HealthChip ok={status?.health?.redis} label="Cache" />
                    </div>

                    <div className="mt-6">
                      <label className={labelClass}>
                        <span className="inline-flex items-center gap-1.5">
                          <KeyRound className="h-3.5 w-3.5 text-slate-400" /> Setup token
                        </span>
                      </label>
                      <input
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && token.trim() && verifyToken()}
                        placeholder="Paste your SETUP_TOKEN"
                        autoFocus
                        className={inputClass + ' font-mono text-[13px] tracking-tight'}
                      />
                    </div>

                    <div className="mt-7 flex items-center justify-between">
                      <span className="text-[11px] text-slate-500">
                        {status?.version && `Platform ${status.version}`}
                      </span>
                      <button
                        onClick={verifyToken}
                        disabled={!token.trim() || busy}
                        className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                        Continue <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* ------------------------------------------------ Step 2 */}
                {step === 2 && (
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                      <UserRound className="h-5 w-5 text-sky-300" /> Create your administrator
                    </h2>
                    <p className="mt-1.5 text-sm text-slate-400">
                      This account owns the platform. Choose a strong, unique password.
                    </p>

                    <div className="mt-5 space-y-4">
                      <div>
                        <label className={labelClass}>Email</label>
                        <input
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className={inputClass}
                          placeholder="admin@your-domain"
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Username</label>
                        <input
                          value={username}
                          onChange={(e) => setUsername(e.target.value)}
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Password</label>
                        <div className="relative">
                          <input
                            type={showPassword ? 'text' : 'password'}
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className={inputClass + ' pr-10'}
                            placeholder="••••••••••••"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword((v) => !v)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
                          >
                            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        <div className="mt-2.5 grid grid-cols-2 gap-x-4 gap-y-1">
                          {passwordChecks.map((c) => (
                            <div
                              key={c.key}
                              className={
                                'flex items-center gap-1.5 text-[12px] transition-colors ' +
                                (c.ok ? 'text-emerald-300' : 'text-slate-500')
                              }
                            >
                              <Check className={'h-3 w-3 ' + (c.ok ? 'opacity-100' : 'opacity-30')} />
                              {c.label}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <label className={labelClass}>Confirm password</label>
                        <input
                          type={showPassword ? 'text' : 'password'}
                          value={confirm}
                          onChange={(e) => setConfirm(e.target.value)}
                          className={inputClass}
                          placeholder="••••••••••••"
                        />
                        {confirm && confirm !== password && (
                          <p className="mt-1.5 text-[12px] text-amber-300">Passwords do not match yet.</p>
                        )}
                      </div>
                    </div>

                    <div className="mt-7 flex items-center justify-between">
                      <button
                        onClick={() => setStep(1)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-400 transition hover:text-slate-200"
                      >
                        <ArrowLeft className="h-4 w-4" /> Back
                      </button>
                      <button
                        onClick={() => setStep(3)}
                        disabled={!canContinueStep2}
                        className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Continue <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* ------------------------------------------------ Step 3 */}
                {step === 3 && (
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                      <Building2 className="h-5 w-5 text-sky-300" /> Your organization
                    </h2>
                    <p className="mt-1.5 text-sm text-slate-400">
                      Sensible defaults are fine — everything here can be changed later.
                    </p>

                    <div className="mt-5 space-y-4">
                      <div>
                        <label className={labelClass}>Organization name</label>
                        <input
                          value={orgName}
                          onChange={(e) => setOrgName(e.target.value)}
                          className={inputClass}
                          placeholder="Default Organization"
                        />
                      </div>
                      <div>
                        <label className={labelClass}>Timezone</label>
                        <input
                          value={timezone}
                          onChange={(e) => setTimezone(e.target.value)}
                          className={inputClass}
                          placeholder="Asia/Bangkok"
                        />
                      </div>
                      <div className="rounded-lg border border-white/[0.06] bg-white/[0.03] px-3.5 py-3">
                        <div className="flex items-center gap-2 text-[13px] font-medium text-slate-300">
                          <Globe className="h-4 w-4 text-slate-400" /> Domain
                          <span className="ml-auto font-mono text-[12px] text-sky-200">
                            {status?.domain || 'localhost'}
                          </span>
                        </div>
                        <p className="mt-1.5 text-[12px] leading-relaxed text-slate-500">
                          The public domain drives TLS certificates and MQTT endpoints, so it is
                          configured on the host — to change it later run{' '}
                          <code className="rounded bg-white/10 px-1 py-0.5 text-sky-200">
                            make set-domain DOMAIN=iot.example.com
                          </code>
                          .
                        </p>
                      </div>
                    </div>

                    <div className="mt-7 flex items-center justify-between">
                      <button
                        onClick={() => setStep(2)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-400 transition hover:text-slate-200"
                      >
                        <ArrowLeft className="h-4 w-4" /> Back
                      </button>
                      <button
                        onClick={() => setStep(4)}
                        className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition hover:bg-sky-400"
                      >
                        Continue <ArrowRight className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* ------------------------------------------------ Step 4 */}
                {step === 4 && (
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold text-white">
                      <ShieldCheck className="h-5 w-5 text-emerald-300" /> Review &amp; finish
                    </h2>
                    <p className="mt-1.5 text-sm text-slate-400">
                      Creating the administrator permanently retires the setup token.
                    </p>

                    <div className="mt-5 divide-y divide-white/[0.06] rounded-lg border border-white/[0.06] bg-white/[0.03]">
                      {[
                        { icon: UserRound, label: 'Administrator', value: email },
                        { icon: Lock, label: 'Password', value: '••••••••••••' },
                        {
                          icon: Building2,
                          label: 'Organization',
                          value: orgName.trim() || 'Default Organization',
                        },
                        { icon: Globe, label: 'Domain', value: status?.domain || 'localhost' },
                        { icon: Database, label: 'Timezone', value: timezone || '—' },
                      ].map((row) => (
                        <div key={row.label} className="flex items-center gap-3 px-4 py-3">
                          <row.icon className="h-4 w-4 shrink-0 text-slate-400" />
                          <span className="w-32 text-[13px] font-medium text-slate-400">
                            {row.label}
                          </span>
                          <span className="truncate text-[13px] text-slate-100">{row.value}</span>
                        </div>
                      ))}
                    </div>

                    <div className="mt-7 flex items-center justify-between">
                      <button
                        onClick={() => setStep(3)}
                        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-400 transition hover:text-slate-200"
                      >
                        <ArrowLeft className="h-4 w-4" /> Back
                      </button>
                      <button
                        onClick={completeSetup}
                        disabled={busy}
                        className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-emerald-500/25 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                        Complete setup
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>

          <p className="mt-5 text-center text-[11px] tracking-wide text-slate-600">
            TESAIoT Community Edition · Secure by design
          </p>
        </div>
      </div>
    </div>
  );
}
