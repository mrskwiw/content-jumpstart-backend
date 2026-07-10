/**
 * Data Transformation Utilities
 *
 * Centralized utilities for transforming data between frontend (camelCase)
 * and backend (snake_case) conventions. Ensures consistency across API clients.
 */

/**
 * Convert camelCase string to snake_case
 *
 * @example
 * toSnakeCase('businessDescription') // 'business_description'
 * toSnakeCase('idealCustomer') // 'ideal_customer'
 */
export function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Convert snake_case string to camelCase
 *
 * @example
 * toCamelCase('business_description') // 'businessDescription'
 * toCamelCase('ideal_customer') // 'idealCustomer'
 */
export function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * Convert object keys from camelCase to snake_case
 *
 * @param obj - Object with camelCase keys
 * @param excludeUndefined - If true, exclude keys with undefined values
 * @returns New object with snake_case keys
 *
 * @example
 * objectToSnakeCase({ firstName: 'John', lastName: 'Doe' })
 * // { first_name: 'John', last_name: 'Doe' }
 */
export function objectToSnakeCase<T extends Record<string, unknown>>(
  obj: T,
  excludeUndefined = true
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    // Skip undefined values if excludeUndefined is true
    if (excludeUndefined && value === undefined) {
      continue;
    }

    const snakeKey = toSnakeCase(key);

    // Recursively convert nested objects
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      result[snakeKey] = objectToSnakeCase(value as Record<string, unknown>, excludeUndefined);
    } else {
      result[snakeKey] = value;
    }
  }

  return result;
}

/**
 * Convert object keys from snake_case to camelCase
 *
 * @param obj - Object with snake_case keys
 * @returns New object with camelCase keys
 *
 * @example
 * objectToCamelCase({ first_name: 'John', last_name: 'Doe' })
 * // { firstName: 'John', lastName: 'Doe' }
 */
export function objectToCamelCase<T extends Record<string, unknown>>(
  obj: T
): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    const camelKey = toCamelCase(key);

    // Recursively convert nested objects
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      result[camelKey] = objectToCamelCase(value as Record<string, unknown>);
    } else {
      result[camelKey] = value;
    }
  }

  return result;
}

/**
 * Build URLSearchParams from object, excluding undefined/null values
 *
 * @param params - Object with query parameters
 * @returns URLSearchParams ready for use in URL
 *
 * @example
 * buildQueryParams({ page: 1, limit: 10, search: undefined })
 * // URLSearchParams with "page=1&limit=10" (search excluded)
 */
export function buildQueryParams(params: Record<string, unknown>): URLSearchParams {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    // Skip undefined and null values
    if (value === undefined || value === null) {
      continue;
    }

    // Convert arrays to comma-separated strings
    if (Array.isArray(value)) {
      searchParams.append(key, value.join(','));
    } else {
      // Convert numbers/booleans to strings
      searchParams.append(key, String(value));
    }
  }

  return searchParams;
}

/**
 * Extract filename from Content-Disposition header
 *
 * Used when downloading files from API endpoints. Parses the
 * Content-Disposition header to extract the suggested filename.
 *
 * @param contentDisposition - Content-Disposition header value
 * @param defaultFilename - Fallback filename if header parsing fails
 * @returns Extracted filename
 *
 * @example
 * extractFilename('attachment; filename="report.pdf"') // 'report.pdf'
 * extractFilename('attachment; filename=data.csv') // 'data.csv'
 * extractFilename(undefined, 'download.txt') // 'download.txt'
 */
export function extractFilename(
  contentDisposition: string | undefined,
  defaultFilename = 'download'
): string {
  if (!contentDisposition) {
    return defaultFilename;
  }

  // Match: filename="something.ext" or filename=something.ext
  const filenameMatch = contentDisposition.match(/filename="?(.+?)"?(?:;|$)/i);

  if (filenameMatch && filenameMatch[1]) {
    // Remove any remaining quotes
    return filenameMatch[1].replace(/"/g, '');
  }

  return defaultFilename;
}

/**
 * Convert template quantities object keys to strings
 *
 * Backend expects template IDs as string keys in template_quantities object.
 * This helper ensures keys are always strings.
 *
 * @param quantities - Template quantities with number or string keys
 * @returns Template quantities with string keys
 *
 * @example
 * normalizeTemplateQuantities({ 1: 10, 2: 20 })
 * // { '1': 10, '2': 20 }
 */
export function normalizeTemplateQuantities(
  quantities: Record<string | number, number> | undefined
): Record<string, number> | undefined {
  if (!quantities) {
    return undefined;
  }

  return Object.fromEntries(
    Object.entries(quantities).map(([id, qty]) => [String(id), qty])
  );
}

/**
 * Build selective update payload
 *
 * Creates a payload object for PATCH/PUT requests by only including fields
 * that are not undefined. Converts camelCase to snake_case automatically.
 *
 * @param input - Partial input object with camelCase keys
 * @returns Payload object with snake_case keys, undefined fields excluded
 *
 * @example
 * buildUpdatePayload({ name: 'John', email: undefined, age: 30 })
 * // { name: 'John', age: 30 }
 */
export function buildUpdatePayload<T extends Record<string, unknown>>(
  input: Partial<T>
): Record<string, unknown> {
  return objectToSnakeCase(input, true);
}

/**
 * Parse comma-separated string to array
 *
 * @param str - Comma-separated string
 * @param trim - Whether to trim whitespace from each value
 * @returns Array of values
 *
 * @example
 * parseCommaSeparated('apple, banana, orange')
 * // ['apple', 'banana', 'orange']
 */
export function parseCommaSeparated(str: string | undefined, trim = true): string[] {
  if (!str) {
    return [];
  }

  const values = str.split(',');
  return trim ? values.map(v => v.trim()).filter(v => v.length > 0) : values;
}

/**
 * Convert array to comma-separated string
 *
 * @param arr - Array of values
 * @returns Comma-separated string
 *
 * @example
 * toCommaSeparated(['apple', 'banana', 'orange'])
 * // 'apple, banana, orange'
 */
export function toCommaSeparated(arr: string[] | undefined): string {
  if (!arr || arr.length === 0) {
    return '';
  }

  return arr.join(', ');
}
