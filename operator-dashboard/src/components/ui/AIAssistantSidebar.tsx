import { useState, useRef, useEffect, useCallback } from 'react';
import { X, Send, Plus, Sparkles, History, Trash2 } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { streamChat, type ChatStreamEvent } from '@/utils/streamChat';
import { assistantApi, type ConversationSummary } from '@/api/assistant';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function AIAssistantSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [toolActivity, setToolActivity] = useState<string[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<ConversationSummary[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const location = useLocation();

  // Derive current page context from the URL (stable for hook deps).
  const getCurrentPage = useCallback(() => {
    const path = location.pathname;
    if (path.includes('/wizard')) return 'wizard';
    if (path.includes('/projects')) return 'projects';
    if (path.includes('/clients')) return 'clients';
    if (path.includes('/content-review')) return 'content-review';
    if (path.includes('/deliverables')) return 'deliverables';
    if (path.includes('/settings')) return 'settings';
    return 'overview';
  }, [location.pathname]);

  // Auto-scroll to the latest content.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, toolActivity]);

  // Cancel any in-flight stream on unmount.
  useEffect(() => () => abortRef.current?.abort(), []);

  const loadContextSuggestions = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/assistant/context', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ page: getCurrentPage(), data: {} }),
      });
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to load context suggestions:', error);
    }
  }, [getCurrentPage]);

  useEffect(() => {
    if (isOpen && suggestions.length === 0) {
      loadContextSuggestions();
    }
  }, [isOpen, suggestions.length, loadContextSuggestions]);

  // Append streamed text to the last assistant bubble (creating it if needed).
  const appendToAssistant = useCallback((text: string) => {
    setMessages((prev) => {
      const next = [...prev];
      const last = next[next.length - 1];
      if (last && last.role === 'assistant') {
        next[next.length - 1] = { ...last, content: last.content + text };
      } else {
        next.push({ role: 'assistant', content: text, timestamp: new Date() });
      }
      return next;
    });
  }, []);

  const handleEvent = useCallback(
    (event: ChatStreamEvent) => {
      switch (event.type) {
        case 'start':
          setConversationId(event.conversation_id);
          break;
        case 'token':
          appendToAssistant(event.text);
          break;
        case 'tool_running':
          setToolActivity((prev) => [...prev, `Looking up ${event.name.replace(/_/g, ' ')}…`]);
          break;
        case 'tool_result':
          setToolActivity((prev) => [...prev, `${event.ok ? '✓' : '✗'} ${event.summary}`]);
          break;
        case 'suggestions':
          setSuggestions(event.items || []);
          break;
        case 'error':
          appendToAssistant(`⚠️ ${event.error}`);
          break;
        case 'complete':
          if (event.conversation_id) setConversationId(event.conversation_id);
          break;
      }
    },
    [appendToAssistant]
  );

  const sendMessage = async (messageText?: string) => {
    const textToSend = (messageText ?? inputMessage).trim();
    if (!textToSend || isLoading) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: textToSend, timestamp: new Date() },
    ]);
    setInputMessage('');
    setIsLoading(true);
    setToolActivity([]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        {
          message: textToSend,
          conversationId,
          context: { page: getCurrentPage() },
        },
        { onEvent: handleEvent, signal: controller.signal }
      );
    } catch (error) {
      if ((error as Error)?.name !== 'AbortError') {
        appendToAssistant('\n\n⚠️ Something went wrong. Please try again.');
      }
    } finally {
      setIsLoading(false);
      setToolActivity([]);
      abortRef.current = null;
    }
  };

  const startNewConversation = () => {
    abortRef.current?.abort();
    setMessages([]);
    setConversationId(null);
    setToolActivity([]);
    setShowHistory(false);
    loadContextSuggestions();
  };

  const openHistory = async () => {
    setShowHistory(true);
    try {
      const data = await assistantApi.listConversations();
      setHistory(data.conversations);
    } catch (error) {
      console.error('Failed to load conversation history:', error);
    }
  };

  const loadConversation = async (id: string) => {
    try {
      const conv = await assistantApi.getConversation(id);
      const loaded: Message[] = conv.messages
        .filter((m) => (m.role === 'user' || m.role === 'assistant') && m.content)
        .map((m) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content as string,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
        }));
      setMessages(loaded);
      setConversationId(conv.id);
      setShowHistory(false);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await assistantApi.deleteConversation(id);
      setHistory((prev) => prev.filter((c) => c.id !== id));
      if (id === conversationId) startNewConversation();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-700 text-white shadow-lg transition-transform hover:scale-110 hover:shadow-xl"
        aria-label="Toggle AI Assistant"
      >
        {isOpen ? <X className="h-6 w-6" /> : <Sparkles className="h-6 w-6" />}
      </button>

      {/* Sidebar panel */}
      <div
        className={`fixed right-0 top-0 z-30 h-full w-96 transform bg-white dark:bg-neutral-900 shadow-2xl transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="border-b border-neutral-200 dark:border-neutral-700 bg-gradient-to-r from-purple-500 to-purple-700 p-4 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                <h2 className="font-semibold">AI Assistant</h2>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={showHistory ? () => setShowHistory(false) : openHistory}
                  className="rounded p-1 hover:bg-white/20"
                  title="Conversation history"
                >
                  <History className="h-4 w-4" />
                </button>
                <button
                  onClick={startNewConversation}
                  className="rounded p-1 hover:bg-white/20"
                  title="New conversation"
                >
                  <Plus className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="rounded p-1 hover:bg-white/20"
                  title="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="mt-1 text-xs text-purple-100">
              {getCurrentPage().replace('-', ' ').replace(/\b\w/g, (l) => l.toUpperCase())} Page
            </p>
          </div>

          {/* History view */}
          {showHistory ? (
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                Recent conversations
              </p>
              {history.length === 0 && (
                <p className="text-sm text-neutral-500 dark:text-neutral-400">
                  No past conversations yet.
                </p>
              )}
              {history.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  className="group flex w-full items-center justify-between rounded-lg bg-neutral-100 dark:bg-neutral-800 p-3 text-left hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
                >
                  <span className="truncate text-sm text-neutral-800 dark:text-neutral-200">
                    {conv.title || 'Untitled conversation'}
                  </span>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => deleteConversation(conv.id, e)}
                    className="ml-2 shrink-0 rounded p-1 text-neutral-400 opacity-0 group-hover:opacity-100 hover:text-red-500"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </span>
                </button>
              ))}
            </div>
          ) : (
            /* Messages view */
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center py-8">
                  <Sparkles className="h-12 w-12 mx-auto text-purple-500 mb-3" />
                  <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                    Hi! I'm your AI assistant. Ask me about your projects, clients, posts, or
                    credits.
                  </p>
                  {suggestions.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                        Quick suggestions:
                      </p>
                      {suggestions.map((suggestion, idx) => (
                        <button
                          key={idx}
                          onClick={() => sendMessage(suggestion)}
                          className="block w-full text-left text-sm bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-lg p-3 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {messages.map((message, idx) => (
                <div
                  key={idx}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      message.role === 'user'
                        ? 'bg-purple-500 text-white'
                        : 'bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100'
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <p
                      className={`mt-1 text-xs ${
                        message.role === 'user'
                          ? 'text-purple-100'
                          : 'text-neutral-500 dark:text-neutral-400'
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              ))}

              {/* Tool activity + typing indicator while streaming */}
              {isLoading && (
                <div className="flex flex-col items-start gap-2">
                  {toolActivity.map((line, idx) => (
                    <div
                      key={idx}
                      className="text-xs text-neutral-500 dark:text-neutral-400 bg-neutral-50 dark:bg-neutral-800/60 rounded px-2 py-1"
                    >
                      {line}
                    </div>
                  ))}
                  <div className="bg-neutral-100 dark:bg-neutral-800 rounded-lg p-3">
                    <div className="flex gap-1">
                      <div className="h-2 w-2 rounded-full bg-purple-500 animate-bounce" />
                      <div className="h-2 w-2 rounded-full bg-purple-500 animate-bounce delay-100" />
                      <div className="h-2 w-2 rounded-full bg-purple-500 animate-bounce delay-200" />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Input area */}
          {!showHistory && (
            <div className="border-t border-neutral-200 dark:border-neutral-700 p-4">
              <div className="flex gap-2">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask me anything..."
                  rows={2}
                  className="flex-1 resize-none rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-500 dark:placeholder-neutral-400 focus:border-purple-500 focus:outline-none focus:ring-2 focus:ring-purple-500/20"
                  disabled={isLoading}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={!inputMessage.trim() || isLoading}
                  className="flex h-[calc(100%-8px)] items-center justify-center rounded-lg bg-purple-500 px-4 text-white hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
              <p className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                Press Enter to send • Shift+Enter for new line
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/20 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
