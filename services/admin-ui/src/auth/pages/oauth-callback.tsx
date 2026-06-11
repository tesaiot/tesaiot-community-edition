/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Spinner } from '@/components/ui/spinners';

export function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuthData } = useAuth();

  useEffect(() => {
    const handleOAuthCallback = async () => {
      const token = searchParams.get('token');
      const provider = searchParams.get('provider');
      const error = searchParams.get('error');

      if (error) {
        // Handle error
        navigate(`/auth/signin?error=${error}`);
        return;
      }

      if (token) {
        try {
          // Decode the token to get user info
          const parts = token.split('.');
          const payload = JSON.parse(atob(parts[1]));
          
          // Set auth data in context
          setAuthData({
            token,
            user: {
              id: payload.user_id,
              username: payload.username,
              email: payload.email || `${payload.username}@oauth.local`,
              role: payload.role,
              provider: provider || payload.provider
            }
          });

          // Store in localStorage for persistence
          localStorage.setItem('tesa_token', token);
          localStorage.setItem('tesa_user', JSON.stringify({
            id: payload.user_id,
            username: payload.username,
            email: payload.email || `${payload.username}@oauth.local`,
            role: payload.role,
            provider: provider || payload.provider
          }));

          // Redirect to admin dashboard
          navigate('/admin');
        } catch (err) {
          console.error('OAuth callback error:', err);
          navigate('/auth/signin?error=oauth_failed');
        }
      } else {
        navigate('/auth/signin?error=no_token');
      }
    };

    handleOAuthCallback();
  }, [searchParams, navigate, setAuthData]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}