/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/spinners';

export function OAuthSuccessPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setToken, setUser } = useAuth();

  useEffect(() => {
    const handleOAuthSuccess = async () => {
      const token = searchParams.get('token');
      const error = searchParams.get('error');

      if (error) {
        // OAuth failed - redirect to login with error
        navigate(`/auth/signin?error=oauth_failed&message=${encodeURIComponent(error)}`);
        return;
      }

      if (!token) {
        // No token - redirect to login
        navigate('/auth/signin?error=oauth_failed&message=No authentication token received');
        return;
      }

      try {
        // Decode JWT token to get user info
        const tokenParts = token.split('.');
        if (tokenParts.length !== 3) {
          throw new Error('Invalid token format');
        }

        const payload = JSON.parse(atob(tokenParts[1]));
        
        // Set auth data
        setToken(token);
        setUser({
          id: payload.user_id,
          email: payload.email,
          name: payload.name,
          role: payload.role,
          provider: payload.provider,
          username: payload.email.split('@')[0]
        });

        // Store in localStorage for persistence
        localStorage.setItem('tesa_auth_token', token);
        localStorage.setItem('tesa_auth_user', JSON.stringify({
          id: payload.user_id,
          email: payload.email,
          name: payload.name,
          role: payload.role,
          provider: payload.provider,
          username: payload.email.split('@')[0]
        }));

        // Redirect to dashboard or requested page
        const nextPath = searchParams.get('next') || '/dashboard';
        navigate(nextPath);
      } catch (error) {
        console.error('OAuth success handler error:', error);
        navigate('/auth/signin?error=oauth_failed&message=Failed to process authentication');
      }
    };

    handleOAuthSuccess();
  }, [searchParams, navigate, setToken, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Spinner className="w-12 h-12 mx-auto mb-4" />
        <h2 className="text-2xl font-semibold mb-2">Completing sign in...</h2>
        <p className="text-muted-foreground">Please wait while we authenticate your account</p>
      </div>
    </div>
  );
}