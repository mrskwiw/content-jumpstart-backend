import api from '../api/client';

export interface ParsedField {
  value: any;
  confidence: 'high' | 'medium' | 'low';
  source?: string;
}

export interface ParsedBriefResponse {
  success: boolean;
  fields: Record<string, ParsedField>;
  warnings: string[];
  metadata: {
    filename: string;
    parseTimeMs: number;
    fieldsExtracted: number;
    fieldsTotal: number;
  };
}

export interface ParseErrorResponse {
  code: string;
  message: string;
  details?: Record<string, any>;
}

export const briefImportService = {
  /**
   * Upload and parse a brief file
   *
   * @param file - The .txt or .md file to parse
   * @returns Parsed brief data with confidence scores
   * @throws Error with structured error response if parsing fails
   */
  async parseFile(file: File): Promise<ParsedBriefResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await api.post<ParsedBriefResponse>(
        '/briefs/parse',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 30000, // 30 second timeout for parsing
        }
      );

      return response.data;
    } catch (error: any) {
      // Handle structured error responses from backend
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail;

        // Backend returns structured error with code, message, details
        if (typeof detail === 'object' && detail.code) {
          throw new Error(detail.message || 'Failed to parse brief');
        }

        // Fallback for string error messages
        if (typeof detail === 'string') {
          throw new Error(detail);
        }
      }

      // Handle network errors
      if (error.code === 'ECONNABORTED') {
        throw new Error('Request timed out. Please try again.');
      }

      if (error.message === 'Network Error') {
        throw new Error('Network error. Please check your connection.');
      }

      // Generic fallback
      throw new Error('Failed to parse brief file');
    }
  },
};
