/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

/**
 * TESA IoT Platform - Password Setup Component
 * Copyright (C) 2024-2025 TESA IoT Platform
 * 
 * Password setup component for new users after OTP verification
 */

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  Lock, 
  Eye, 
  EyeOff, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  ArrowRight,
  Shield,
  RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

interface PasswordSetupProps {
  tempToken: string;
  email: string;
  isPasswordReset?: boolean;
}

interface PasswordStrength {
  score: number;
  label: string;
  color: string;
}

export default function PasswordSetup({ tempToken, email, isPasswordReset = false }: PasswordSetupProps) {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Password validation states
  const [passwordCriteria, setPasswordCriteria] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    special: false
  });

  const checkPasswordStrength = (pwd: string): PasswordStrength => {
    let score = 0;
    
    if (pwd.length >= 8) score++;
    if (pwd.length >= 12) score++;
    if (/[A-Z]/.test(pwd)) score++;
    if (/[a-z]/.test(pwd)) score++;
    if (/[0-9]/.test(pwd)) score++;
    if (/[^A-Za-z0-9]/.test(pwd)) score++;

    if (score <= 2) return { score: 25, label: 'Weak', color: 'bg-red-500' };
    if (score <= 4) return { score: 50, label: 'Fair', color: 'bg-yellow-500' };
    if (score <= 5) return { score: 75, label: 'Good', color: 'bg-blue-500' };
    return { score: 100, label: 'Strong', color: 'bg-green-500' };
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    setError('');
    
    // Update criteria checks
    setPasswordCriteria({
      length: value.length >= 8,
      uppercase: /[A-Z]/.test(value),
      lowercase: /[a-z]/.test(value),
      number: /[0-9]/.test(value),
      special: /[^A-Za-z0-9]/.test(value)
    });
  };

  const validatePasswords = (): boolean => {
    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return false;
    }

    if (!passwordCriteria.uppercase || !passwordCriteria.lowercase || !passwordCriteria.number) {
      setError('Password must contain uppercase, lowercase, and numbers');
      return false;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validatePasswords()) return;

    setLoading(true);
    setError('');

    try {
      const endpoint = isPasswordReset 
        ? '/api/v1/auth/otp/forgot-password/reset'
        : '/api/v1/auth/otp/set-initial-password';

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          temp_token: tempToken,
          password
        })
      });

      const data = await response.json();

      if (response.ok && data.success) {
        toast.success('🎉 Password Set Successfully!', {
          description: isPasswordReset 
            ? 'Your password has been reset. You can now sign in with your new password.'
            : 'Your account is now active! You can sign in with your new password.'
        });

        // Store token if provided (for initial setup)
        if (data.token) {
          localStorage.setItem('jwt_token', data.token);
          localStorage.setItem('user', JSON.stringify(data.user));
        }

        // Redirect to login or dashboard
        setTimeout(() => {
          if (data.token) {
            navigate('/dashboard');
          } else {
            navigate('/auth/signin');
          }
        }, 1500);
      } else {
        setError(data.message || 'Failed to set password');
      }
    } catch (error) {
      console.error('Password setup error:', error);
      setError('Failed to set password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const strength = checkPasswordStrength(password);

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto w-12 h-12 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-4">
          <Lock className="h-6 w-6 text-green-600 dark:text-green-400" />
        </div>
        <CardTitle>
          {isPasswordReset ? 'Reset Your Password' : 'Set Your Password'}
        </CardTitle>
        <CardDescription>
          {isPasswordReset 
            ? 'Choose a new secure password for your account'
            : 'Create a secure password to complete your account setup'
          }
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email Display */}
          <div className="text-center p-3 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground">Setting password for</p>
            <p className="font-medium">{email}</p>
          </div>

          {/* Password Input */}
          <div className="space-y-2">
            <Label htmlFor="password">New Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => handlePasswordChange(e.target.value)}
                placeholder="Enter your password"
                className="pr-10"
                disabled={loading}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Password Strength Indicator */}
          {password && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Password Strength</span>
                <span className={`font-medium ${
                  strength.label === 'Strong' ? 'text-green-600' :
                  strength.label === 'Good' ? 'text-blue-600' :
                  strength.label === 'Fair' ? 'text-yellow-600' :
                  'text-red-600'
                }`}>
                  {strength.label}
                </span>
              </div>
              <Progress value={strength.score} className="h-2" />
            </div>
          )}

          {/* Password Criteria */}
          <div className="space-y-1 text-sm">
            <div className="flex items-center gap-2">
              {passwordCriteria.length ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={passwordCriteria.length ? 'text-green-600' : 'text-muted-foreground'}>
                At least 8 characters
              </span>
            </div>
            <div className="flex items-center gap-2">
              {passwordCriteria.uppercase ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={passwordCriteria.uppercase ? 'text-green-600' : 'text-muted-foreground'}>
                One uppercase letter
              </span>
            </div>
            <div className="flex items-center gap-2">
              {passwordCriteria.lowercase ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={passwordCriteria.lowercase ? 'text-green-600' : 'text-muted-foreground'}>
                One lowercase letter
              </span>
            </div>
            <div className="flex items-center gap-2">
              {passwordCriteria.number ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={passwordCriteria.number ? 'text-green-600' : 'text-muted-foreground'}>
                One number
              </span>
            </div>
            <div className="flex items-center gap-2">
              {passwordCriteria.special ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <XCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={passwordCriteria.special ? 'text-green-600' : 'text-muted-foreground'}>
                One special character (recommended)
              </span>
            </div>
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  setError('');
                }}
                placeholder="Confirm your password"
                className="pr-10"
                disabled={loading}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Password Match Indicator */}
          {confirmPassword && (
            <div className="flex items-center gap-2 text-sm">
              {password === confirmPassword ? (
                <>
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <span className="text-green-600">Passwords match</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-red-600" />
                  <span className="text-red-600">Passwords do not match</span>
                </>
              )}
            </div>
          )}

          {/* Error Message */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !password || !confirmPassword || password !== confirmPassword}
          >
            {loading ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                Setting Password...
              </>
            ) : (
              <>
                Set Password
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>

          {/* Security Note */}
          <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-950/50">
            <Shield className="h-4 w-4 text-blue-600" />
            <AlertDescription className="text-sm">
              <strong>Security Note:</strong> Your password is encrypted and stored securely. 
              We recommend using a unique password that you don't use for other accounts.
            </AlertDescription>
          </Alert>
        </form>
      </CardContent>
    </Card>
  );
}