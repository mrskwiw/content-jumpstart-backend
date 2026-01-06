import { useState, useRef, useEffect, useCallback } from 'react';
import { MessageCircle, X, Send, RotateCcw, Sparkles } from 'lucide-react';
import { useLocation } from 'react-router-dom';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AssistantResponse {
  message: string;
  suggestions: string[];
}

export default function AIAssistantSidebar() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const location = useLocation();

  // Get current page context from URL
  const getCurrentPage = () => {
    const path = location.pathname;
    if (path.includes('/wizard')) return 'wizard';
    if (path.includes('/projects')) return 'projects';
    if (path.includes('/clients')) return 'clients';
    if (path.includes('/content-review')) return 'content-review';
    if (path.includes('/deliverables')) return 'deliverables';
    if (path.includes('/settings')) return 'settings';
    return 'overview';
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // SECURITY FIX: Wrap in useCallback to fix React Hook dependency issue (TR-017)
  const loadContextSuggestions = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/assistant/context', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          page: getCurrentPage(),
          data: {}, // TODO: Add page-specific data (project ID, client ID, etc.)
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to load context suggestions:', error);
    }
  }, [location.pathname]); // Dependencies: location changes trigger new suggestions

  // Load context suggestions when sidebar opens or page changes
  useEffect(() => {
    if (isOpen && suggestions.length === 0) {
      loadContextSuggestions();
    }
  }, [isOpen, location.pathname, suggestions.length, loadContextSuggestions]); // SECURITY FIX: Added all dependencies (TR-017)

  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || inputMessage.trim();
    if (!textToSend || isLoading) return;

    // Add user message
    const userMessage: Message = {
      role: 'user',
      content: textToSend,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: textToSend,
          context: {
            page: getCurrentPage(),
            // TODO: Add more context (current project, client, etc.)
          },
          conversation_history: messages,
        }),
      });

      if (response.ok) {
        const data: AssistantResponse = await response.json();

        // Add assistant response
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.message,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, assistantMessage]);

        // Update suggestions
        if (data.suggestions && data.suggestions.length > 0) {
          setSuggestions(data.suggestions);
        }
      } else {
        throw new Error('Failed to get response from assistant');
      }
    } catch (error) {
      console.error('Assistant error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const resetConversation = async () => {
    try {
      const token = localStorage.getItem('access_token');
      await fetch('/api/assistant/reset', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      setMessages([]);
      loadContextSuggestions();
    } catch (error) {
      console.error('Failed to reset conversation:', error);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      {/* Toggle Button - Fixed position */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-purple-700 text-white shadow-lg transition-transform hover:scale-110 hover:shadow-xl"
        aria-label="Toggle AI Assistant"
      >
        {isOpen ? (
          <X className="h-6 w-6" />
        ) : (
          <Sparkles className="h-6 w-6" />
        )}
      </button>

      {/* Sidebar Panel */}
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
                  onClick={resetConversation}
                  className="rounded p-1 hover:bg-white/20"
                  title="Reset conversation"
                >
                  <RotateCcw className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="rounded p-1 hover:bg-white/20"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <p className="mt-1 text-xs text-purple-100">
              {getCurrentPage().replace('-', ' ').replace(/\b\w/g, (l) => l.toUpperCase())} Page
            </p>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-8">
                <Sparkles className="h-12 w-12 mx-auto text-purple-500 mb-3" />
                <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
                  Hi! I'm your AI assistant. How can I help you today?
                </p>

                {/* Suggestions */}
                {suggestions.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                      Quick suggestions:
                    </p>
                    {suggestions.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestionClick(suggestion)}
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

            {isLoading && (
              <div className="flex justify-start">
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

          {/* Input Area */}
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
        </div>
      </div>

      {/* Overlay when sidebar is open */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/20 backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
