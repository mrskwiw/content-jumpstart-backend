/**
 * Comprehensive tests for ThemeContext
 */
import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { renderHook, act } from '@testing-library/react';
import { ThemeProvider, useTheme } from '../ThemeContext';

describe('ThemeContext', () => {
  const mockMatchMedia = (matches: boolean) => {
    return jest.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })) as unknown as typeof window.matchMedia;
  };

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
    window.matchMedia = mockMatchMedia(false);
  });

  describe('Provider initialization', () => {
    it('should default to system theme when no theme is stored', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      expect(result.current.theme).toBe('system');
      expect(result.current.actualTheme).toBe('light');
    });

    it('should load stored theme from localStorage', () => {
      localStorage.setItem('theme', 'dark');

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      expect(result.current.theme).toBe('dark');
      expect(result.current.actualTheme).toBe('dark');
    });

    it('should apply light theme to document element', () => {
      localStorage.setItem('theme', 'light');

      renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('should apply dark theme to document element', () => {
      localStorage.setItem('theme', 'dark');

      renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('setTheme', () => {
    it('should change theme to dark', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      act(() => {
        result.current.setTheme('dark');
      });

      expect(result.current.theme).toBe('dark');
      expect(result.current.actualTheme).toBe('dark');
      expect(localStorage.getItem('theme')).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should change theme to light', () => {
      localStorage.setItem('theme', 'dark');

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      act(() => {
        result.current.setTheme('light');
      });

      expect(result.current.theme).toBe('light');
      expect(result.current.actualTheme).toBe('light');
      expect(localStorage.getItem('theme')).toBe('light');
      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('should use system preference for system theme when system is dark', () => {
      window.matchMedia = mockMatchMedia(true);

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      act(() => {
        result.current.setTheme('system');
      });

      expect(result.current.theme).toBe('system');
      expect(result.current.actualTheme).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should use system preference for system theme when system is light', () => {
      window.matchMedia = mockMatchMedia(false);

      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      act(() => {
        result.current.setTheme('system');
      });

      expect(result.current.theme).toBe('system');
      expect(result.current.actualTheme).toBe('light');
      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('should remove previous theme class when changing themes', () => {
      const { result } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      act(() => {
        result.current.setTheme('dark');
      });

      expect(document.documentElement.classList.contains('dark')).toBe(true);
      expect(document.documentElement.classList.contains('light')).toBe(false);

      act(() => {
        result.current.setTheme('light');
      });

      expect(document.documentElement.classList.contains('light')).toBe(true);
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('system theme listener', () => {
    it('should add event listener when theme is system', () => {
      const addEventListenerSpy = jest.fn();
      window.matchMedia = jest.fn().mockImplementation((query: string) => ({
        matches: false,
        addEventListener: addEventListenerSpy,
        removeEventListener: jest.fn(),
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })) as unknown as typeof window.matchMedia;

      renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      expect(addEventListenerSpy).toHaveBeenCalledWith('change', expect.any(Function));
    });

    it('should remove event listener on unmount when using system theme', () => {
      const removeEventListenerSpy = jest.fn();
      window.matchMedia = jest.fn().mockImplementation((query: string) => ({
        matches: false,
        addEventListener: jest.fn(),
        removeEventListener: removeEventListenerSpy,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })) as unknown as typeof window.matchMedia;

      const { unmount } = renderHook(() => useTheme(), {
        wrapper: ThemeProvider,
      });

      unmount();

      expect(removeEventListenerSpy).toHaveBeenCalledWith('change', expect.any(Function));
    });
  });

  describe('useTheme hook', () => {
    it('should throw error when used outside ThemeProvider', () => {
      expect(() => {
        renderHook(() => useTheme());
      }).toThrow('useTheme must be used within a ThemeProvider');
    });
  });
});
