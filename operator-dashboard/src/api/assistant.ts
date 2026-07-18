import apiClient from './client';

export interface AssistantMessage {
  id: string;
  role: 'user' | 'assistant' | 'tool';
  content: string | null;
  tool_calls: Array<Record<string, unknown>> | null;
  tool_call_id: string | null;
  created_at: string | null;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  page_context: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ConversationDetail extends ConversationSummary {
  messages: AssistantMessage[];
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

export const assistantApi = {
  async listConversations(skip = 0, limit = 50) {
    const { data } = await apiClient.get<ConversationListResponse>(
      '/api/assistant/conversations',
      { params: { skip, limit } }
    );
    return data;
  },

  async getConversation(conversationId: string) {
    const { data } = await apiClient.get<ConversationDetail>(
      `/api/assistant/conversations/${conversationId}`
    );
    return data;
  },

  async deleteConversation(conversationId: string) {
    const { data } = await apiClient.delete<{ success: boolean; message: string }>(
      `/api/assistant/conversations/${conversationId}`
    );
    return data;
  },
};
