/**
 * Comprehensive tests for errorMessages utility
 */
import { describe, it, expect } from '@jest/globals';
import { getAuthErrorMessage } from '../errorMessages';
import { AxiosError, type InternalAxiosRequestConfig } from 'axios';

describe('getAuthErrorMessage', () => {
  describe('Axios errors', () => {
    it('should handle 401 unauthorized error', () => {
      const error = new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 401,
        data: { detail: 'Invalid credentials' },
        statusText: 'Unauthorized',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Invalid credentials');
    });

    it('should handle invalid_credentials code', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 400,
        data: { code: 'invalid_credentials', detail: 'Wrong password' },
        statusText: 'Bad Request',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Wrong password');
    });

    it('should use default message for 401 without detail', () => {
      const error = new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 401,
        data: {},
        statusText: 'Unauthorized',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Invalid email or password. Please try again.');
    });

    it('should handle 404 not found error', () => {
      const error = new AxiosError('Not Found', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 404,
        data: { detail: 'User does not exist' },
        statusText: 'Not Found',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('User does not exist');
    });

    it('should use default message for 404 without detail', () => {
      const error = new AxiosError('Not Found', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 404,
        data: {},
        statusText: 'Not Found',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Account not found. Please check your email or ask an admin to create one.');
    });

    it('should handle 403 forbidden error', () => {
      const error = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 403,
        data: { detail: 'Access denied' },
        statusText: 'Forbidden',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Access denied');
    });

    it('should use default message for 403 without detail', () => {
      const error = new AxiosError('Forbidden', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 403,
        data: {},
        statusText: 'Forbidden',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('You do not have access to this application.');
    });

    it('should handle 429 rate limit error', () => {
      const error = new AxiosError('Too Many Requests', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 429,
        data: { detail: 'Rate limit exceeded' },
        statusText: 'Too Many Requests',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Rate limit exceeded');
    });

    it('should use default message for 429 without detail', () => {
      const error = new AxiosError('Too Many Requests', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 429,
        data: {},
        statusText: 'Too Many Requests',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Too many attempts. Please wait and retry.');
    });

    it('should handle 500 server error', () => {
      const error = new AxiosError('Internal Server Error', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 500,
        data: { detail: 'Database connection failed' },
        statusText: 'Internal Server Error',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Database connection failed');
    });

    it('should use default message for 500 without detail', () => {
      const error = new AxiosError('Internal Server Error', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 500,
        data: {},
        statusText: 'Internal Server Error',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Server error. Please try again shortly.');
    });

    it('should handle 503 service unavailable', () => {
      const error = new AxiosError('Service Unavailable', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 503,
        data: {},
        statusText: 'Service Unavailable',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Server error. Please try again shortly.');
    });

    it('should handle network error', () => {
      const error = new AxiosError('Network Error', 'ERR_NETWORK', undefined, undefined, undefined);
      error.code = 'ERR_NETWORK';

      expect(getAuthErrorMessage(error)).toBe('Cannot reach the server. Check your connection or VPN and try again.');
    });

    it('should handle status 0 (network error)', () => {
      const error = new AxiosError('Network Error', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 0,
        data: {},
        statusText: '',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Cannot reach the server. Check your connection or VPN and try again.');
    });

    it('should detect HTML response instead of JSON', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 200,
        data: '<!DOCTYPE html><html><body>Error</body></html>',
        statusText: 'OK',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Received HTML instead of an API response. Check VITE_API_URL and that the backend is running.');
    });

    it('should detect HTML response with <html tag', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 200,
        data: '<html><body>Error</body></html>',
        statusText: 'OK',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Received HTML instead of an API response. Check VITE_API_URL and that the backend is running.');
    });

    it('should handle 400 with custom detail', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 400,
        data: { detail: 'Email format is invalid' },
        statusText: 'Bad Request',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Email format is invalid');
    });

    it('should use default message for 400 without detail', () => {
      const error = new AxiosError('Bad Request', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 400,
        data: {},
        statusText: 'Bad Request',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Request was invalid. Please verify your input.');
    });

    it('should extract message from error data field', () => {
      const error = new AxiosError('Error', 'ERR_BAD_REQUEST', undefined, undefined, {
        status: 400,
        data: { message: 'Custom error message' },
        statusText: 'Bad Request',
        headers: {},
        config: {} as InternalAxiosRequestConfig,
      });

      expect(getAuthErrorMessage(error)).toBe('Custom error message');
    });
  });

  describe('Non-Axios errors', () => {
    it('should handle standard Error objects', () => {
      const error = new Error('Something went wrong');
      expect(getAuthErrorMessage(error)).toBe('Something went wrong');
    });

    it('should handle Error without message', () => {
      const error = new Error();
      expect(getAuthErrorMessage(error)).toBe('Unexpected error while signing in. Please retry.');
    });

    it('should handle unknown error types', () => {
      const error = { unknown: 'error' };
      expect(getAuthErrorMessage(error)).toBe('Unexpected error while signing in. Please retry.');
    });

    it('should handle null/undefined', () => {
      expect(getAuthErrorMessage(null)).toBe('Unexpected error while signing in. Please retry.');
      expect(getAuthErrorMessage(undefined)).toBe('Unexpected error while signing in. Please retry.');
    });

    it('should handle string errors', () => {
      const error = 'String error message';
      expect(getAuthErrorMessage(error)).toBe('Unexpected error while signing in. Please retry.');
    });
  });
});
