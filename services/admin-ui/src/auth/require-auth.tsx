/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import { useEffect, useRef, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ScreenLoader } from '@/components/common/screen-loader';
// CRITICAL FIX: Use safe hook that handles null context
import { useAuth } from '@/hooks/useAuth';

/**
 * Component to protect routes that require authentication.
 * If user is not authenticated, redirects to the login page.
 */
export const RequireAuth = () => {
  // FIX: Use correct properties from useAuth hook
  const { user, isAuthenticated, isLoading, checkAuth } = useAuth();
  const location = useLocation();
  const [initialCheckDone, setInitialCheckDone] = useState(false);
  const verificationStarted = useRef(false);

  useEffect(() => {
    const performAuthCheck = async () => {
      if (!verificationStarted.current) {
        verificationStarted.current = true;
        try {
          // If checkAuth function exists, call it
          if (checkAuth && typeof checkAuth === 'function') {
            await checkAuth();
          }
        } catch (error) {
          console.error('Auth check failed:', error);
        } finally {
          setInitialCheckDone(true);
        }
      }
    };

    performAuthCheck();
  }, [checkAuth]);

  // Show screen loader while checking authentication
  if (isLoading || !initialCheckDone) {
    return <ScreenLoader />;
  }

  // If not authenticated, redirect to login
  if (!isAuthenticated || !user) {
    return (
      <Navigate
        to={`/auth/signin?next=${encodeURIComponent(location.pathname)}`}
        replace
      />
    );
  }

  // Role-based route protection
  // Product Industrial Designer should only access Product Model Store
  if (user.role === 'product_industrial_designer') {
    const allowedPaths = ['/product-models', '/auth', '/profile'];
    const isAllowed = allowedPaths.some(path => location.pathname.startsWith(path));

    if (!isAllowed) {
      // Redirect to Product Model Store (separate service)
      window.location.href = '/product-models';
      return null;
    }
  }

  // If authenticated, render child routes
  return <Outlet />;
};
