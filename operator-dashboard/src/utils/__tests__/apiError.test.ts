/**
 * Tests for API error message extraction
 */
import { describe, it, expect } from '@jest/globals';
import { getApiErrorMessage } from '../apiError';

describe('getApiErrorMessage', () => {
  it('should return fallback for null or undefined', () => {
    expect(getApiErrorMessage(null)).toBe('An unexpected error occurred.');
    expect(getApiErrorMessage(undefined)).toBe('An unexpected error occurred.');
  });

  it('should return custom fallback when provided', () => {
    expect(getApiErrorMessage(null, 'Custom fallback')).toBe('Custom fallback');
    expect(getApiErrorMessage(undefined, 'Custom message')).toBe('Custom message');
  });

  it('should return fallback for non-object errors', () => {
    expect(getApiErrorMessage('string error')).toBe('An unexpected error occurred.');
    expect(getApiErrorMessage(123)).toBe('An unexpected error occurred.');
    expect(getApiErrorMessage(true)).toBe('An unexpected error occurred.');
  });

  it('should extract detail string from FastAPI response', () => {
    const error = {
      response: {
        status: 400,
        data: {
          detail: 'Invalid email format',
        },
      },
    };
    expect(getApiErrorMessage(error)).toBe('Invalid email format');
  });

  it('should extract detail.message from structured response', () => {
    const error = {
      response: {
        status: 400,
        data: {
          detail: {
            message: 'Validation failed for field "email"',
            code: 'VALIDATION_ERROR',
          },
        },
      },
    };
    expect(getApiErrorMessage(error)).toBe('Validation failed for field "email"');
  });

  it('should extract message from response data', () => {
    const error = {
      response: {
        status: 500,
        data: {
          message: 'Database connection failed',
        },
      },
    };
    expect(getApiErrorMessage(error)).toBe('Database connection failed');
  });

  it('should use status code messages as fallback', () => {
    expect(getApiErrorMessage({ response: { status: 400, data: {} } }))
      .toBe('Invalid request. Please check your input and try again.');

    expect(getApiErrorMessage({ response: { status: 401, data: {} } }))
      .toBe('Your session has expired. Please log in again.');

    expect(getApiErrorMessage({ response: { status: 403, data: {} } }))
      .toBe('You do not have permission to perform this action.');

    expect(getApiErrorMessage({ response: { status: 404, data: {} } }))
      .toBe('The requested resource was not found.');

    expect(getApiErrorMessage({ response: { status: 409, data: {} } }))
      .toBe('This action conflicts with existing data. Please refresh and try again.');

    expect(getApiErrorMessage({ response: { status: 422, data: {} } }))
      .toBe('Validation failed. Please check your input values.');

    expect(getApiErrorMessage({ response: { status: 429, data: {} } }))
      .toBe('Too many requests. Please wait a moment before trying again.');

    expect(getApiErrorMessage({ response: { status: 500, data: {} } }))
      .toBe('Server error. Please try again or contact support if the issue persists.');

    expect(getApiErrorMessage({ response: { status: 502, data: {} } }))
      .toBe('Service temporarily unavailable. Please try again in a moment.');

    expect(getApiErrorMessage({ response: { status: 503, data: {} } }))
      .toBe('Service temporarily unavailable. Please try again in a moment.');
  });

  it('should handle network errors', () => {
    const error = {
      code: 'ERR_NETWORK',
      message: 'Network Error',
    };
    expect(getApiErrorMessage(error)).toBe('Network error. Please check your connection and try again.');
  });

  it('should extract message from standard Error objects', () => {
    const error = new Error('Custom error message');
    expect(getApiErrorMessage(error)).toBe('Custom error message');
  });

  it('should not return generic "Network Error" message', () => {
    const error = new Error('Network Error');
    expect(getApiErrorMessage(error)).toBe('An unexpected error occurred.');
  });

  it('should prioritize detail over message', () => {
    const error = {
      response: {
        status: 400,
        data: {
          detail: 'Detail message',
          message: 'Message field',
        },
      },
    };
    expect(getApiErrorMessage(error)).toBe('Detail message');
  });

  it('should prioritize detail over status code', () => {
    const error = {
      response: {
        status: 400,
        data: {
          detail: 'Specific validation error',
        },
      },
    };
    expect(getApiErrorMessage(error)).toBe('Specific validation error');
  });

  it('should handle response without data', () => {
    const error = {
      response: {
        status: 500,
      },
    };
    expect(getApiErrorMessage(error)).toBe('Server error. Please try again or contact support if the issue persists.');
  });

  it('should handle unknown status codes', () => {
    const error = {
      response: {
        status: 418, // I'm a teapot
        data: {},
      },
    };
    expect(getApiErrorMessage(error)).toBe('An unexpected error occurred.');
  });
});
