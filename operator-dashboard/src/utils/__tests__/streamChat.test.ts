import { TextEncoder, TextDecoder } from 'util';
import { streamChat, type ChatStreamEvent } from '../streamChat';

// jsdom lacks the web-streams / encoding globals that streamChat relies on.
(globalThis as unknown as { TextEncoder: typeof TextEncoder }).TextEncoder ??= TextEncoder;
(globalThis as unknown as { TextDecoder: typeof TextDecoder }).TextDecoder ??=
  TextDecoder as unknown as typeof globalThis.TextDecoder;

/** Minimal Response-like object exposing exactly what streamChat reads. */
function fakeResponse(status: number, chunks: string[]) {
  const encoder = new TextEncoder();
  let i = 0;
  const reader = {
    read: async () =>
      i < chunks.length
        ? { done: false, value: encoder.encode(chunks[i++]) }
        : { done: true, value: undefined },
  };
  return {
    status,
    ok: status >= 200 && status < 300,
    body: status >= 200 && status < 300 ? { getReader: () => reader } : null,
  } as unknown as Response;
}

function sse(obj: Record<string, unknown>): string {
  return `event: chat\ndata: ${JSON.stringify(obj)}\n\n`;
}

describe('streamChat', () => {
  const realFetch = global.fetch;
  beforeEach(() => localStorage.setItem('access_token', 'tok'));
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('parses SSE frames into typed events, even when split across chunks', async () => {
    const response = fakeResponse(200, [
      sse({ type: 'start', conversation_id: 'c1' }),
      'event: chat\ndata: {"type":"to', // deliberately split mid-frame
      'ken","text":"Hi"}\n\n',
      sse({ type: 'complete', conversation_id: 'c1' }),
    ]);
    global.fetch = jest.fn().mockResolvedValue(response) as unknown as typeof fetch;

    const events: ChatStreamEvent[] = [];
    await streamChat({ message: 'hi' }, { onEvent: (e) => events.push(e) });

    expect(events.map((e) => e.type)).toEqual(['start', 'token', 'complete']);
    const token = events.find((e) => e.type === 'token') as { text: string };
    expect(token.text).toBe('Hi');
  });

  it('emits an error event on a rate-limit (429) response', async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValue(fakeResponse(429, [])) as unknown as typeof fetch;

    const events: ChatStreamEvent[] = [];
    await streamChat({ message: 'hi' }, { onEvent: (e) => events.push(e) });

    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('error');
  });

  it('sends the conversation id and Bearer token', async () => {
    const fetchMock = jest
      .fn()
      .mockResolvedValue(fakeResponse(200, [sse({ type: 'complete' })]));
    global.fetch = fetchMock as unknown as typeof fetch;

    await streamChat({ message: 'hi', conversationId: 'c9' }, { onEvent: () => {} });

    const init = fetchMock.mock.calls[0][1];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
    expect(JSON.parse(init.body as string)).toMatchObject({
      message: 'hi',
      conversation_id: 'c9',
    });
  });
});
