/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import axios from 'axios';

// Use relative URL to use the same protocol (HTTPS) as the admin portal
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const authApi = {
  // Send OTP to email
  sendOTP: async (email: string, purpose: 'verification' | 'password_reset' = 'verification') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/otp/send-otp`, {
        email,
        purpose
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || 'Failed to send OTP');
    }
  },

  // Verify OTP code
  verifyOTP: async (email: string, otp: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/otp/verify-otp`, {
        email,
        otp
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || 'Failed to verify OTP');
    }
  },

  // Resend OTP
  resendOTP: async (email: string, purpose: 'verification' | 'password_reset' = 'verification') => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/otp/resend-otp`, {
        email,
        purpose
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || 'Failed to resend OTP');
    }
  },

  // Set initial password after OTP verification
  setInitialPassword: async (tempToken: string, password: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/otp/set-initial-password`, {
        temp_token: tempToken,
        password
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || 'Failed to set password');
    }
  },

  // Reset password with OTP
  resetPasswordWithOTP: async (email: string, otp: string, newPassword: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/auth/otp/forgot-password/reset`, {
        email,
        otp,
        new_password: newPassword
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.error || 'Failed to reset password');
    }
  }
};