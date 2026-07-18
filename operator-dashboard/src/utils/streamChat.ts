/**
 * Authenticated SSE client for the AI assistant streaming endpoint.
 *
 * The shared axios client and the `useSSE` hook can't be used here: `useSSE`
 * wraps `EventSource`, which is GET-only and can't send an Authorization header
 * or a POST body. This helper POSTs to `/api/assistant/chat/stream` with the
 * Bearer token, reads the `ReadableStream` response, parses SSE frames, and
 * dispatches typed events to callbacks. On a 401 it refreshes the token once and
 * retries (mirroring the axios interceptor).
 */
import { getApiBaseUrl } from '@/utils/env';

/** One event emitted by the backend stream (see chat_service.stream_chat). */
export type ChatStreamEvent =
  | { type: 'start'; conversation_id: string }
  | { type: 'token'; text: string }
  | { type: 'tool_running'; tool_call_id: string; name: string }
  | { type: 'tool_result'; tool_call_id: string; name: string; ok: boolean; summary: string }
  | { type: 'suggestions'; items: string[] }
  | { type: 'complete'; conversation_id?: string }
  | { type: 'error'; error: string };

export interface StreamChatParams {
  message: string;
  conversationId?: string | null;
  context?: Record<string, unknown>;
}

export interface StreamChatHandlers {
  onEvent: (event: ChatStreamEvent) => void;
  signal?: AbortSignal;
}

const STREAM_PATH = '/api/assistant/chat/stream';

function buildUrl(): string {
  const base = getApiBaseUrl();
  return base ? `${base}${STREAM_PATH}` : STREAM_PATH;
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;
  const base = getApiBaseUrl();
  const url = base ? `${base}/api/auth/refresh` : '/api/auth/refresh';
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
      return data.access_token as string;
    }
  } catch {
    // fall through to null
  }
  return null;
}

async function openStream(body: string, token: string | null, signal?: AbortSignal): Promise<Response> {
  return fetch(buildUrl(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body,
    signal,
  });
}

/**
 * Parse one raw SSE frame (text between blank lines) into its JSON data payload.
 * Frames look like `event: chat\ndata: {...}`. Comment/ping lines (`: ...`) and
 * frames without a data field are ignored.
 */
function parseFrame(frame: string): ChatStreamEvent | null {
  const dataLines: string[] = [];
  for (const rawLine of frame.split('\n')) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (dataLines.length === 0) return null;
  try {
    return JSON.parse(dataLines.join('\n')) as ChatStreamEvent;
  } catch {
    return null;
  }
}

/**
 * Stream a chat turn. Resolves when the stream ends. Never rejects on protocol
 * errors — it emits an `{ type: 'error' }` event instead — but may reject if the
 * request is aborted.
 */
export async function streamChat(
  params: StreamChatParams,
  handlers: StreamChatHandlers
): Promise<void> {
  const body = JSON.stringify({
    message: params.message,
    conversation_id: params.conversationId ?? undefined,
    context: params.context ?? {},
  });

  let token = localStorage.getItem('access_token');
  let response: Response;
  try {
    response = await openStream(body, token, handlers.signal);
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        token = refreshed;
        response = await openStream(body, token, handlers.signal);
      }
    }
  } catch (err) {
    if ((err as Error)?.name === 'AbortError') throw err;
    handlers.onEvent({ type: 'error', error: 'Could not reach the assistant.' });
    return;
  }

  if (!response.ok || !response.body) {
    handlers.onEvent({
      type: 'error',
      error:
        response.status === 429
          ? 'Rate limit reached. Please wait a moment and try again.'
          : 'The assistant is unavailable right now.',
    });
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const event = parseFrame(frame);
        if (event) handlers.onEvent(event);
      }
    }
    // Flush any trailing frame without a terminating blank line.
    const tail = parseFrame(buffer);
    if (tail) handlers.onEvent(tail);
  } catch (err) {
    if ((err as Error)?.name === 'AbortError') throw err;
    handlers.onEvent({ type: 'error', error: 'The response was interrupted.' });
  }
}
