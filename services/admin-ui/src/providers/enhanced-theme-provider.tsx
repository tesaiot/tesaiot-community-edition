/*
 * Copyright TESAIoT Platform contributors
 * SPDX-License-Identifier: Apache-2.0
 *
 * Origin: TESAIoT Secure IoT Platform (relicensed subset for the Community Edition).
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { ThemeProvider as NextThemesProvider, useTheme as useNextTheme } from 'next-themes';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useLicenseContext } from './license-provider';
import { cn } from '@/lib/utils';
import { Sun, Moon } from 'lucide-react';

// Metronic theme colors
export const METRONIC_THEMES = {
  light: {
    name: 'Light',
    class: 'light',
    colors: {
      primary: '#7239ea',  // Purple as primary
      secondary: '#e3d6ff',
      success: '#50cd89',
      info: '#009ef7',
      warning: '#ffc700',
      danger: '#f1416c',
      dark: '#3f3f46',     // Dark gray for text
      light: '#f5f8fa',
      textPrimary: '#3f3f46', // Dark gray text
      textSecondary: '#71717a', // Medium gray text
    },
  },
  dark: {
    name: 'Dark',
    class: 'dark',
    colors: {
      primary: '#7239ea',  // Purple as primary
      secondary: '#e3d6ff',
      success: '#50cd89',
      info: '#009ef7',
      warning: '#ffc700',
      danger: '#f1416c',
      dark: '#1e1e2d',
      light: '#2b2b40',
      textPrimary: '#e4e4e7', // Light gray text
      textSecondary: '#c7c7d1', // Slightly lighter for better contrast
    },
  },
  // Commercial-only themes
  blue: {
    name: 'Blue',
    class: 'theme-blue',
    commercial: true,
    colors: {
      primary: '#3699ff',
      secondary: '#e1f0ff',
      success: '#1bc5bd',
      info: '#8950fc',
      warning: '#ffa800',
      danger: '#f64e60',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
  green: {
    name: 'Green',
    class: 'theme-green',
    commercial: true,
    colors: {
      primary: '#1bc5bd',
      secondary: '#c9f7f5',
      success: '#50cd89',
      info: '#7239ea',
      warning: '#ffc700',
      danger: '#f1416c',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
  purple: {
    name: 'Purple',
    class: 'theme-purple',
    commercial: true,
    colors: {
      primary: '#7239ea',
      secondary: '#e3d6ff',
      success: '#50cd89',
      info: '#009ef7',
      warning: '#ffc700',
      danger: '#f1416c',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
  red: {
    name: 'Red',
    class: 'theme-red',
    commercial: true,
    colors: {
      primary: '#f1416c',
      secondary: '#ffe2e5',
      success: '#50cd89',
      info: '#7239ea',
      warning: '#ffc700',
      danger: '#ff6c75',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
  orange: {
    name: 'Orange',
    class: 'theme-orange',
    commercial: true,
    colors: {
      primary: '#ffa800',
      secondary: '#fff4de',
      success: '#50cd89',
      info: '#7239ea',
      warning: '#f6c000',
      danger: '#f1416c',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
  teal: {
    name: 'Teal',
    class: 'theme-teal',
    commercial: true,
    colors: {
      primary: '#20c9a6',
      secondary: '#d8f9f3',
      success: '#50cd89',
      info: '#7239ea',
      warning: '#ffc700',
      danger: '#f1416c',
      dark: '#181c32',
      light: '#f3f6f9',
    },
  },
};

interface ThemeContextType {
  currentTheme: string;
  availableThemes: typeof METRONIC_THEMES;
  setTheme: (theme: string) => void;
  toggleTheme: () => void;
  isThemeAvailable: (theme: string) => boolean;
  getThemeColors: () => typeof METRONIC_THEMES.light.colors;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function EnhancedThemeProvider({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <NextThemesProvider
        attribute="class"
        defaultTheme="light"
        enableSystem={false}
        disableTransitionOnChange
      >
        <TooltipProvider delayDuration={0}>{children}</TooltipProvider>
      </NextThemesProvider>
    );
  }

  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      disableTransitionOnChange
    >
      <ThemeProviderInner>{children}</ThemeProviderInner>
    </NextThemesProvider>
  );
}

function ThemeProviderInner({ children }: { children: React.ReactNode }) {
  const { hasFeature, getAvailableThemes } = useLicenseContext();
  const { theme: nextTheme, setTheme: setNextTheme } = useNextTheme();
  const [currentTheme, setCurrentTheme] = useState('light');

  // Get available themes based on license
  const getFilteredThemes = () => {
    const availableThemeNames = getAvailableThemes();
    const filtered: typeof METRONIC_THEMES = {} as any;
    
    Object.entries(METRONIC_THEMES).forEach(([key, theme]) => {
      if (availableThemeNames.includes(key)) {
        filtered[key as keyof typeof METRONIC_THEMES] = theme;
      }
    });
    
    return filtered;
  };

  const availableThemes = getFilteredThemes();

  // Check if a theme is available
  const isThemeAvailable = (theme: string): boolean => {
    return theme in availableThemes;
  };

  // Set theme with license check
  const setTheme = (theme: string) => {
    if (isThemeAvailable(theme)) {
      setCurrentTheme(theme);
      
      // For dark/light themes, use next-themes
      if (theme === 'dark' || theme === 'light') {
        setNextTheme(theme);
      } else {
        // For custom themes, add additional class
        setNextTheme('light'); // Base on light theme
        document.documentElement.classList.add(METRONIC_THEMES[theme as keyof typeof METRONIC_THEMES].class);
      }
      
      localStorage.setItem('tesa-theme', theme);
      
      // Apply theme colors as CSS variables
      const colors = METRONIC_THEMES[theme as keyof typeof METRONIC_THEMES].colors;
      Object.entries(colors).forEach(([key, value]) => {
        document.documentElement.style.setProperty(`--color-${key}`, value);
      });
      
      // Apply text color classes
      if (theme === 'dark') {
        document.documentElement.classList.add('text-gray-200');
        document.documentElement.classList.remove('text-gray-700');
      } else {
        document.documentElement.classList.add('text-gray-700');
        document.documentElement.classList.remove('text-gray-200');
      }
    }
  };

  // Toggle between light and dark (or just light for community)
  const toggleTheme = () => {
    if (hasFeature('darkTheme')) {
      setTheme(currentTheme === 'light' ? 'dark' : 'light');
    }
  };

  // Get current theme colors
  const getThemeColors = () => {
    return METRONIC_THEMES[currentTheme as keyof typeof METRONIC_THEMES]?.colors || METRONIC_THEMES.light.colors;
  };

  // Load saved theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('tesa-theme') || nextTheme || 'light';
    if (isThemeAvailable(savedTheme)) {
      setTheme(savedTheme);
    } else {
      setTheme('light'); // Fallback to light if saved theme not available
    }
  }, [nextTheme]);

  // Sync currentTheme with nextTheme
  useEffect(() => {
    if (nextTheme && (nextTheme === 'dark' || nextTheme === 'light')) {
      setCurrentTheme(nextTheme);
    }
  }, [nextTheme]);

  const value: ThemeContextType = {
    currentTheme,
    availableThemes,
    setTheme,
    toggleTheme,
    isThemeAvailable,
    getThemeColors,
  };

  return (
    <ThemeContext.Provider value={value}>
      <TooltipProvider delayDuration={0}>
        {children}
      </TooltipProvider>
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    // PRODUCTION FIX: Return safe defaults instead of crashing
    console.warn('useTheme called outside EnhancedThemeProvider - using defaults');
    return {
      theme: 'light' as Theme,
      colorMode: 'light' as ColorMode,
      setTheme: () => {},
      setColorMode: () => {},
      systemPreference: 'light' as Theme,
      resolvedTheme: 'light' as Theme,
      toggleTheme: () => {},
      toggleColorMode: () => {},
    };
  }
  return context;
}

// Theme selector component
export function ThemeSelector() {
  const { currentTheme, availableThemes, setTheme } = useTheme();
  const { hasFeature } = useLicenseContext();

  // Don't show selector if only light theme is available
  if (Object.keys(availableThemes).length <= 1) {
    return null;
  }

  return (
    <div className="relative">
      <select
        value={currentTheme}
        onChange={(e) => setTheme(e.target.value)}
        className="appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {Object.entries(availableThemes).map(([key, theme]) => (
          <option key={key} value={key}>
            {theme.name}
          </option>
        ))}
      </select>
      <div className="absolute inset-y-0 right-0 flex items-center px-2 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

// Quick theme toggle button
export function ThemeToggle() {
  const { currentTheme, toggleTheme } = useTheme();
  const { hasFeature } = useLicenseContext();

  if (!hasFeature('darkTheme')) {
    return null;
  }

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
        "bg-gradient-to-r from-purple-600 to-purple-700",
        "hover:from-purple-700 hover:to-purple-800",
        currentTheme === 'light' ? "text-white" : "text-gray-900"
      )}
      aria-label="Toggle theme"
    >
      {currentTheme === 'light' ? (
        <>
          <Sun className="h-3.5 w-3.5" />
          <span>LIGHT</span>
        </>
      ) : (
        <>
          <Moon className="h-3.5 w-3.5" />
          <span>DARK</span>
        </>
      )}
    </button>
  );
}
