import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { ConversationMessage } from './ConversationMessage';
import { ExtractedFieldsPreview, ExtractedField } from './ExtractedFieldsPreview';
import { Button } from '@/components/ui';
import { aiDiscoveryService } from '@/services/aiDiscoveryService';

export interface AIDiscoveryPanelProps {
  onDataExtracted?: (data: Partial<ClientBriefFormData>) => void;
  onComplete?: () => void;
  onCancel?: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ClientBriefFormData {
  companyName: string;
  businessDescription: string;
  idealCustomer: string;
  mainProblemSolved: string;
  tonePreference: string;
  platforms: string[];
  customerPainPoints: string[];
  customerQuestions: string[];
}

/**
 * Generate a unique message id. Defined at module scope so the impure
 * `Date.now()` call lives outside the component body (satisfies
 * react-hooks/purity) — these ids are only ever created inside event handlers.
 */
function makeMessageId(offset = 0): string {
  return (Date.now() + offset).toString();
}

/**
 * AI-powered client discovery panel with conversational interface
 * Extracts structured client data from natural conversation
 */
export function AIDiscoveryPanel({ onDataExtracted, onComplete, onCancel }: AIDiscoveryPanelProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [extractedFields, setExtractedFields] = useState<ExtractedField[]>([
    { name: 'companyName', label: 'Company Name', status: 'pending' },
    { name: 'businessDescription', label: 'Business Description', status: 'pending' },
    { name: 'idealCustomer', label: 'Ideal Customer', status: 'pending' },
    { name: 'mainProblemSolved', label: 'Main Problem Solved', status: 'pending' },
    { name: 'tonePreference', label: 'Tone Preference', status: 'pending' },
    { name: 'platforms', label: 'Target Platforms', status: 'pending' },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Initialize discovery session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const session = await aiDiscoveryService.startDiscovery();
        setSessionId(session.id);
        setMessages([
          {
            id: '1',
            role: 'assistant',
            content: session.firstQuestion,
            timestamp: session.createdAt,
          },
        ]);
      } catch (error) {
        console.error('Failed to start discovery session:', error);
        // Fall back to manual mode
        onCancel?.();
      }
    };
    initSession();
  }, [onCancel]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isProcessing || !sessionId) return;

    const userMessage: Message = {
      id: makeMessageId(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsProcessing(true);

    try {
      // Call AI discovery service
      const response = await aiDiscoveryService.sendMessage(sessionId, userMessage.content);

      // Add AI response to messages
      const aiMessage: Message = {
        id: makeMessageId(1),
        role: 'assistant',
        content: response.message,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, aiMessage]);

      // Update extracted fields
      updateExtractedFields(response.extractedFields, response.confidence);

      // Notify parent of extracted data
      if (onDataExtracted) {
        onDataExtracted(response.extractedFields as Partial<ClientBriefFormData>);
      }

      setIsProcessing(false);
    } catch (error) {
      console.error('Failed to send message:', error);
      setIsProcessing(false);

      // Show error message
      const errorMessage: Message = {
        id: makeMessageId(1),
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again or switch to manual entry.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const updateExtractedFields = (
    fields: Partial<ClientBriefFormData>,
    confidence: Record<string, number>
  ) => {
    setExtractedFields(prev =>
      prev.map(field => {
        const fieldValue = fields[field.name as keyof ClientBriefFormData];
        const fieldConfidence = confidence[field.name];

        if (fieldValue) {
          // Determine status based on confidence and length requirements
          let status: 'extracted' | 'partial' | 'pending' = 'extracted';

          if (field.name === 'businessDescription' && typeof fieldValue === 'string' && fieldValue.length < 70) {
            status = 'partial';
          } else if (field.name === 'idealCustomer' && typeof fieldValue === 'string' && fieldValue.length < 20) {
            status = 'partial';
          } else if (field.name === 'mainProblemSolved' && typeof fieldValue === 'string' && fieldValue.length < 30) {
            status = 'partial';
          } else if (fieldConfidence && fieldConfidence < 0.7) {
            status = 'partial';
          }

          return {
            ...field,
            value: Array.isArray(fieldValue) ? fieldValue.join(', ') : String(fieldValue),
            status,
            confidence: fieldConfidence,
          };
        }

        return field;
      })
    );
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const isComplete = extractedFields.filter(f => f.status === 'extracted').length >= 4;

  return (
    <div className="h-full flex flex-col gap-4">
      {/* Conversation area */}
      <div className="flex-1 min-h-0 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50 p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map(message => (
            <ConversationMessage
              key={message.id}
              role={message.role}
              content={message.content}
              timestamp={message.timestamp}
            />
          ))}
          {isProcessing && (
            <div className="flex gap-3 justify-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Loader2 className="h-4 w-4 text-blue-600 dark:text-blue-400 animate-spin" />
              </div>
              <div className="bg-neutral-100 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 rounded-lg px-4 py-2.5">
                <p className="text-sm">Thinking...</p>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="flex-shrink-0">
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your response..."
              rows={2}
              disabled={isProcessing}
              className="flex-1 resize-none bg-transparent text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 dark:placeholder:text-neutral-500 outline-none"
            />
            <Button
              variant="primary"
              size="sm"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isProcessing}
              className="self-end"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Extracted data preview */}
      <div className="flex-shrink-0">
        <ExtractedFieldsPreview
          fields={extractedFields}
          onEdit={() => {
            // TODO: Allow editing extracted fields
          }}
        />
      </div>

      {/* Action buttons */}
      <div className="flex-shrink-0 flex items-center justify-between gap-3 pt-2">
        <Button variant="secondary" size="sm" onClick={onCancel}>
          Switch to Manual Entry
        </Button>
        <Button
          variant="primary"
          size="sm"
          onClick={onComplete}
          disabled={!isComplete}
        >
          Continue →
        </Button>
      </div>
    </div>
  );
}
