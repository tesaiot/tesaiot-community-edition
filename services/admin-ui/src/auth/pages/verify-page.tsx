/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Pages - Verify Page
 * Copyright (C) 2024-2025 TESA IoT Platform
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, Check, Mail, Shield, Clock } from 'lucide-react';
import { Alert, AlertIcon, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';

const VerifyPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState<'otp' | 'password'>('otp');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [tempToken, setTempToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [isPasswordReset, setIsPasswordReset] = useState(false);
  // Countdown state removed as Resend OTP is no longer available
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    // Get email from URL params if provided
    const emailParam = searchParams.get('email');
    const resetParam = searchParams.get('reset');
    if (emailParam) {
      setEmail(emailParam);
    }
    if (resetParam === 'true') {
      setIsPasswordReset(true);
    }
  }, [searchParams]);

  // Check if email came from URL parameter (should be read-only)
  const isEmailFromUrl = searchParams.get('email') !== null;

  // Handle OTP input change
  const handleOtpChange = (index: number, value: string) => {
    if (value.length > 1) return;
    
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    
    // Auto-focus next input
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  // Handle OTP verification
  const handleVerifyOTP = async () => {
    const otpCode = otp.join('');
    if (otpCode.length !== 6) {
      setError('Please enter all 6 digits');
      return;
    }

    if (!email) {
      setError('Please enter your email address');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Use different endpoint based on whether this is password reset or new user verification
      const endpoint = isPasswordReset 
        ? '/api/v1/auth/otp/forgot-password/verify-otp'
        : '/api/v1/auth/otp/verify-otp';
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, otp: otpCode })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setTempToken(data.temp_token);
        if (isPasswordReset) {
          setSuccess('Verification successful! Please set your new password.');
        } else {
          setSuccess('Email verified successfully! Please set your password.');
        }
        setStep('password');
      } else {
        setError(data.message || 'Verification failed');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to verify OTP');
    } finally {
      setLoading(false);
    }
  };

  // Handle password setup
  const handleSetPassword = async () => {
    if (!password || !confirmPassword) {
      setError('Please enter both password fields');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Use different endpoint based on whether this is password reset or new user setup
      const endpoint = isPasswordReset 
        ? '/api/v1/auth/otp/forgot-password/reset-password'
        : '/api/v1/auth/otp/set-initial-password';
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          temp_token: tempToken, 
          password: password 
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        if (isPasswordReset) {
          toast.success('Password reset successfully! Redirecting to login...');
          setTimeout(() => {
            navigate('/auth/signin?pwd_reset=success');
          }, 2000);
        } else {
          toast.success('Account setup complete! Redirecting to login...');
          setTimeout(() => {
            navigate('/auth/signin', { 
              state: { 
                message: 'Your account has been successfully set up. Please login with your new password.' 
              } 
            });
          }, 2000);
        }
      } else {
        setError(data.message || 'Failed to set password');
      }
    } catch (err: any) {
      setError(err.message || 'Failed to set password');
    } finally {
      setLoading(false);
    }
  };

  // Resend OTP functionality removed - users should contact admin if needed

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-xl border-gray-200 dark:border-gray-700">
          <CardHeader className="space-y-1 text-center pb-6">
            <div className="mb-4 flex justify-center">
              <div className="p-3 bg-primary/10 rounded-full">
                <Shield className="h-12 w-12 text-primary" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">TESA IoT Platform</CardTitle>
            <CardDescription className="text-base">
              {step === 'otp' 
                ? (isPasswordReset ? 'Reset Your Password' : 'Verify Your Account')
                : (isPasswordReset ? 'Set New Password' : 'Set Your Password')
              }
            </CardDescription>
          </CardHeader>

        <CardContent className="space-y-4">
          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{error}</AlertTitle>
            </Alert>
          )}

          {/* Success Alert */}
          {success && (
            <Alert>
              <Check className="h-4 w-4" />
              <AlertTitle>{success}</AlertTitle>
            </Alert>
          )}

          {step === 'otp' ? (
            <>
              {/* Email Input */}
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading || isEmailFromUrl}
                  className={isEmailFromUrl ? "bg-muted" : ""}
                />
                {isEmailFromUrl && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Email address is pre-filled and cannot be changed
                  </p>
                )}
              </div>

              {/* OTP Input */}
              <div className="space-y-2">
                <Label>Verification Code</Label>
                <div className="flex gap-2 justify-center">
                  {otp.map((digit, index) => (
                    <Input
                      key={index}
                      ref={(el) => (inputRefs.current[index] = el)}
                      type="text"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleOtpChange(index, e.target.value)}
                      className="w-12 h-12 text-center text-lg font-semibold"
                      disabled={loading}
                    />
                  ))}
                </div>
              </div>

              {/* Verify Button */}
              <Button 
                onClick={handleVerifyOTP} 
                className="w-full" 
                disabled={loading || otp.join('').length !== 6 || !email}
              >
                {loading ? 'Verifying...' : 'Verify Email'}
              </Button>

              {/* Resend OTP button removed - users should contact admin if needed */}
              <div className="text-center mt-4">
                <p className="text-sm text-muted-foreground">
                  Didn't receive the code? Please contact your administrator.
                </p>
              </div>
            </>
          ) : (
            <>
              {/* Password Input */}
              <div className="space-y-2">
                <Label htmlFor="password">{isPasswordReset ? 'New Password' : 'Password'}</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder={isPasswordReset ? 'Enter your new password' : 'Enter your password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* Confirm Password */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder={isPasswordReset ? 'Confirm your new password' : 'Confirm your password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* Set Password Button */}
              <Button 
                onClick={handleSetPassword} 
                className="w-full" 
                disabled={loading || !password || !confirmPassword}
              >
                {loading 
                  ? (isPasswordReset ? 'Resetting Password...' : 'Setting Password...')
                  : (isPasswordReset ? 'Reset Password' : 'Set Password')
                }
              </Button>
            </>
          )}
        </CardContent>

        <CardFooter className="flex flex-col space-y-2 text-center text-sm text-muted-foreground">
          <div>
            Need help? Contact your platform administrator.
          </div>
          <div className="text-xs">
            © 2025 TESA IoT Platform by Thai Embedded Systems Association (TESA)
          </div>
        </CardFooter>
      </Card>
      </div>
    </div>
  );
};

export default VerifyPage;