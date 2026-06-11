/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useState } from 'react';
import { SupabaseAdapter } from '@/auth/adapters/supabase-adapter';
import { useAuth } from '@/hooks/useAuth';
import { isSameSiteHost } from '@/lib/domain';
import { zodResolver } from '@hookform/resolvers/zod';
import { AlertCircle, Check, Eye, EyeOff } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, AlertIcon, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinners';
import { Icons } from '@/components/common/icons';
import { getSigninSchema, SigninSchemaType } from '../forms/signin-schema';
import { toAbsoluteUrl } from '@/lib/helpers';
import ForgotPasswordModal from '@/components/auth/ForgotPasswordModal';

export function SignInPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showForgotPasswordModal, setShowForgotPasswordModal] = useState(false);
  // OAuth loading states - temporarily disabled for beta
  // const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  // const [isFacebookLoading, setIsFacebookLoading] = useState(false);
  // const [isGitHubLoading, setIsGitHubLoading] = useState(false);
  // const [isAppleLoading, setIsAppleLoading] = useState(false);
  // const [isMicrosoftLoading, setIsMicrosoftLoading] = useState(false);

  // Check for success message from password reset or error messages
  useEffect(() => {
    const pwdReset = searchParams.get('pwd_reset');
    const errorParam = searchParams.get('error');
    const errorDescription = searchParams.get('error_description');

    if (pwdReset === 'success') {
      setSuccessMessage(
        'Your password has been successfully reset. You can now sign in with your new password.',
      );
    }

    if (errorParam) {
      switch (errorParam) {
        case 'auth_callback_failed':
          setError(
            errorDescription || 'Authentication failed. Please try again.',
          );
          break;
        case 'auth_callback_error':
          setError(
            errorDescription ||
              'An error occurred during authentication. Please try again.',
          );
          break;
        case 'auth_token_error':
          setError(
            errorDescription ||
              'Failed to set authentication session. Please try again.',
          );
          break;
        default:
          setError(
            errorDescription || 'Authentication error. Please try again.',
          );
          break;
      }
    }
  }, [searchParams]);

  const form = useForm<SigninSchemaType>({
    resolver: zodResolver(getSigninSchema()),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: true,
    },
  });

  async function onSubmit(values: SigninSchemaType) {
    try {
      setIsProcessing(true);
      setError(null);

      console.log('Attempting to sign in with email:', values.email);

      // Simple validation
      if (!values.email.trim() || !values.password) {
        setError('Email and password are required');
        return;
      }

      // Sign in using the auth context
      const user = await login(values.email, values.password);

      // Role-based redirect
      if (user?.role === 'product_industrial_designer') {
        // Product designers go directly to Product Model Store (separate service)
        // Use window.location for full page navigation to external service
        window.location.href = '/product-models';
        return;
      }

      // Check for redirect URL (used by external services like BENTO IDE)
      const redirectUrl = searchParams.get('redirect');
      if (redirectUrl) {
        // Only allow redirects to the operator's own host or a subdomain of it
        // (derived from window.location at runtime — domain-agnostic self-host).
        try {
          const url = new URL(redirectUrl);
          if (isSameSiteHost(url.hostname)) {
            window.location.href = redirectUrl;
            return;
          }
        } catch {
          // Invalid URL, fall through to default redirect
        }
      }

      // Get the 'next' parameter from URL if it exists (internal routes)
      const nextPath = searchParams.get('next') || '/';

      // Use navigate for internal navigation
      navigate(nextPath);
    } catch (err: any) {
      console.error('Sign-in error:', err);
      
      if (err.message?.includes('Invalid username or password')) {
        setError('Invalid email or password. Please check your credentials and try again.');
      } else if (err.message?.includes('Database unavailable')) {
        setError('Database unavailable. Please try again later.');
      } else if (err.message?.includes('API server not reachable')) {
        setError('Cannot connect to server. Please check if the server is running.');
      } else {
        setError(
          err instanceof Error
            ? err.message
            : 'An unexpected error occurred. Please try again.',
        );
      }
    } finally {
      setIsProcessing(false);
    }
  }

  // Handle OAuth Sign In - temporarily disabled for beta
  /*
  const handleOAuthSignIn = async (provider: 'google' | 'facebook' | 'github' | 'apple' | 'microsoft') => {
    try {
      // Set loading state for the specific provider
      if (provider === 'google') setIsGoogleLoading(true);
      else if (provider === 'facebook') setIsFacebookLoading(true);
      else if (provider === 'github') setIsGitHubLoading(true);
      else if (provider === 'apple') setIsAppleLoading(true);
      else if (provider === 'microsoft') setIsMicrosoftLoading(true);
      
      setError(null);

      // Redirect to backend OAuth endpoint
      window.location.href = `/api/auth/oauth/${provider}`;
    } catch (err) {
      console.error(`${provider} sign-in error:`, err);
      setError(
        err instanceof Error
          ? err.message
          : `Failed to sign in with ${provider}. Please try again.`,
      );
      
      // Reset loading states
      setIsGoogleLoading(false);
      setIsFacebookLoading(false);
      setIsGitHubLoading(false);
      setIsAppleLoading(false);
      setIsMicrosoftLoading(false);
    }
  };
  */

  return (
    <div
      className="fixed inset-0 flex items-center justify-center p-4"
      style={{
        // Self-contained gradient backdrop (no external image asset, no
        // third-party licensing concern) that pairs with the glassmorphism card.
        background: 'radial-gradient(125% 125% at 50% 10%, #1e293b 0%, #0f172a 45%, #020617 100%)'
      }}
    >
      <div className="w-full max-w-md">
        <div className="bg-white/[0.09] dark:bg-gray-900/[0.09] backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-white/[0.05]">
          <div className="text-center mb-6">
            <Link to="/">
              <img
                src={toAbsoluteUrl('/images/TESA_logo.png')}
                className="h-36 mx-auto mb-4"
                alt="TESA Logo"
              />
            </Link>
            <h1 className="font-semibold text-white whitespace-nowrap" style={{ fontSize: '1.5rem' }}>
              TES<span style={{ fontSize: '1.4em', verticalAlign: 'super', position: 'relative', top: '0.26em' }}>⩓</span>IoT Platform
            </h1>
            <p className="text-sm text-gray-100 mt-1 font-medium">
              Secure AIoT Backend Platform
            </p>
          </div>

          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-4"
            >
              {/* OAuth Login Buttons - Temporarily disabled for beta */}
              {/*
              <div className="flex flex-col gap-3">
          <Button
            variant="outline"
            type="button"
            onClick={() => handleOAuthSignIn('google')}
            disabled={isGoogleLoading}
            className="bg-white/90 border-white/30 hover:bg-white text-gray-800 hover:text-gray-900"
          >
            {isGoogleLoading ? (
              'Signing in with Google...'
            ) : (
              <>
                <Icons.googleColorful className="size-5!" /> Sign in with Google
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            type="button"
            onClick={() => handleOAuthSignIn('facebook')}
            disabled={isFacebookLoading}
            className="bg-white/90 border-white/30 hover:bg-white text-gray-800 hover:text-gray-900"
          >
            {isFacebookLoading ? (
              'Signing in with Facebook...'
            ) : (
              <>
                <svg className="size-5!" viewBox="0 0 24 24" fill="#1877F2">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
                <span className="ml-1">Sign in with Facebook</span>
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            type="button"
            onClick={() => handleOAuthSignIn('github')}
            disabled={isGitHubLoading}
            className="bg-white/90 border-white/30 hover:bg-white text-gray-800 hover:text-gray-900"
          >
            {isGitHubLoading ? (
              'Signing in with GitHub...'
            ) : (
              <>
                <svg className="size-5!" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                </svg>
                <span className="ml-1">Sign in with GitHub</span>
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            type="button"
            onClick={() => handleOAuthSignIn('apple')}
            disabled={isAppleLoading}
            className="bg-white/90 border-white/30 hover:bg-white text-gray-800 hover:text-gray-900"
          >
            {isAppleLoading ? (
              'Signing in with Apple...'
            ) : (
              <>
                <svg className="size-5!" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"/>
                </svg>
                <span className="ml-1">Sign in with Apple</span>
              </>
            )}
          </Button>
          
          <Button
            variant="outline"
            type="button"
            onClick={() => handleOAuthSignIn('microsoft')}
            disabled={isMicrosoftLoading}
            className="bg-white/90 border-white/30 hover:bg-white text-gray-800 hover:text-gray-900"
          >
            {isMicrosoftLoading ? (
              'Signing in with Microsoft...'
            ) : (
              <>
                <svg className="size-5!" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11.4 0H0v11.4h11.4V0z" fill="#f25022"/>
                  <path d="M24 0H12.6v11.4H24V0z" fill="#7fba00"/>
                  <path d="M11.4 12.6H0V24h11.4V12.6z" fill="#00a4ef"/>
                  <path d="M24 12.6H12.6V24H24V12.6z" fill="#ffb900"/>
                </svg>
                <span className="ml-1">Sign in with Microsoft</span>
              </>
            )}
          </Button>
        </div>

        <div className="relative py-1">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-white/30" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-transparent px-2 text-white font-medium">or</span>
          </div>
        </div>
        */}

        {error && (
          <Alert
            variant="destructive"
            appearance="light"
            onClose={() => setError(null)}
          >
            <AlertIcon>
              <AlertCircle />
            </AlertIcon>
            <AlertTitle>{error}</AlertTitle>
          </Alert>
        )}

        {successMessage && (
          <Alert appearance="light" onClose={() => setSuccessMessage(null)}>
            <AlertIcon>
              <Check />
            </AlertIcon>
            <AlertTitle>{successMessage}</AlertTitle>
          </Alert>
        )}

        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel className="text-white font-medium">Email</FormLabel>
              <FormControl>
                <Input placeholder="Your email" {...field} className="bg-white/90 border-white/30 placeholder:text-gray-500" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <div className="flex justify-between items-center gap-2.5">
                <FormLabel className="text-white font-medium">Password</FormLabel>
              </div>
              <div className="relative">
                <Input
                  placeholder="Your password"
                  type={passwordVisible ? 'text' : 'password'} // Toggle input type
                  {...field}
                  className="bg-white/90 border-white/30 placeholder:text-gray-500"
                />
                <Button
                  type="button"
                  variant="ghost"
                  mode="icon"
                  onClick={() => setPasswordVisible(!passwordVisible)}
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                >
                  {passwordVisible ? (
                    <EyeOff className="text-gray-600" />
                  ) : (
                    <Eye className="text-gray-600" />
                  )}
                </Button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="rememberMe"
          render={({ field }) => (
            <FormItem className="flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      className="border-white/50 data-[state=checked]:bg-white data-[state=checked]:text-black"
                    />
                  </FormControl>
                  <FormLabel className="text-sm font-normal cursor-pointer text-white">
                    Remember me
                  </FormLabel>
                </div>
                <button
                  type="button"
                  onClick={() => setShowForgotPasswordModal(true)}
                  className="text-sm font-semibold text-white hover:text-gray-200"
                >
                  Forgot Password?
                </button>
              </div>
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" disabled={isProcessing}>
          {isProcessing ? 'Loading...' : 'Sign In'}
        </Button>


        {/* Sign Up link hidden - users are created by admins with OTP verification */}
        {/* <div className="text-center text-sm text-white">
          Don't have an account?{' '}
          <Link
            to="/auth/signup"
            className="text-sm font-semibold text-white hover:text-gray-200 underline"
          >
            Sign Up
          </Link>
        </div> */}
            </form>
          </Form>
        </div>
      </div>
      
      {/* Forgot Password Modal */}
      <ForgotPasswordModal 
        open={showForgotPasswordModal}
        onClose={() => setShowForgotPasswordModal(false)}
      />
    </div>
  );
}
