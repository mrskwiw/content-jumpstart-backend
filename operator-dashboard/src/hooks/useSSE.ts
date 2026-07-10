/**
 * React hook for consuming Server-Sent Events (SSE) streams
 *
 * Provides real-time updates from backend streaming endpoints with
 * automatic connection management and error handling.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface SSEOptions {
  /**
   * Callback fired when a message is received
   */
  onMessage?: (data: unknown) => void;

  /**
   * Callback fired when the stream completes
   */
  onComplete?: () => void;

  /**
   * Callback fired on errors
   */
  onError?: (error: Error) => void;

  /**
   * Whether to automatically reconnect on connection loss
   */
  autoReconnect?: boolean;

  /**
   * Maximum reconnection attempts
   */
  maxReconnectAttempts?: number;
}

export function useSSE(url: string | null, options: SSEOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  // Holds the latest `connect` so the reconnect timer can call it without
  // referencing `connect` before its own declaration (avoids self-reference).
  const connectRef = useRef<() => void>(() => {});

  const {
    onMessage,
    onComplete,
    onError,
    autoReconnect = false,
    maxReconnectAttempts = 3,
  } = options;

  const connect = useCallback(() => {
    if (!url) return;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'complete') {
            onComplete?.();
            eventSource.close();
            setIsConnected(false);
          } else if (data.type === 'error') {
            const err = new Error(data.error || 'Stream error');
            setError(err);
            onError?.(err);
            eventSource.close();
            setIsConnected(false);
          } else {
            onMessage?.(data);
          }
        } catch {
          const parseError = new Error('Failed to parse SSE message');
          setError(parseError);
          onError?.(parseError);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        const err = new Error('SSE connection error');
        setError(err);
        onError?.(err);
        eventSource.close();

        // Auto-reconnect logic
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          setTimeout(() => connectRef.current(), 1000 * reconnectAttemptsRef.current);
        }
      };
    } catch (err) {
      const connectionError = err instanceof Error ? err : new Error('Connection failed');
      setError(connectionError);
      onError?.(connectionError);
    }
  }, [url, onMessage, onComplete, onError, autoReconnect, maxReconnectAttempts]);

  // Keep the reconnect timer pointing at the latest `connect`.
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
    }
  }, []);

  // Open/close the SSE connection to the external EventSource system on mount
  // and when `url` changes. `connect` only sets state from async EventSource
  // event handlers, not synchronously, so this is a valid external-sync effect.
  useEffect(() => {
    if (url) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- connect() only setState()s inside async EventSource handlers
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]);

  return {
    isConnected,
    error,
    disconnect,
  };
}
