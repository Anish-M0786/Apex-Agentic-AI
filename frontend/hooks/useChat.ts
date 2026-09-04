'use client';

import { useState } from 'react';
import { runChat } from '@/lib/agent';
import type { Activity } from '@/types/activity';
import type { Message, MessageAttachment } from '@/types/chat';

const make = (
  role: Message['role'],
  content = '',
  status: Message['status'] = 'idle',
  attachments?: MessageAttachment[],
  activities?: Activity[],
): Message => ({
  id: crypto.randomUUID(),
  role,
  content,
  status,
  createdAt: new Date().toISOString(),
  attachments,
  activities,
});

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);

  const send = async (
    content: string,
    document_ids: string[] = [],
    attachments: MessageAttachment[] = [],
  ) => {
    const history = messages
      .filter(item => item.content)
      .slice(-8)
      .map(item => ({ role: item.role, content: item.content }));

    const user = make('user', content, 'completed', attachments);
    // Show the thinking indicator while waiting for the real backend response.
    // No fake activity simulation — activity events come from SSE for agent workflows.
    const assistant = make('assistant', '', 'thinking');
    setMessages(m => [...m, user, assistant]);

    try {
      const result = await runChat(content, document_ids, history);
      setMessages(m =>
        m.map(x =>
          x.id === assistant.id
            ? { ...x, content: result.response, status: 'completed' }
            : x,
        ),
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Unable to complete the request.';
      setMessages(m =>
        m.map(x =>
          x.id === assistant.id ? { ...x, content: message, status: 'error' } : x,
        ),
      );
    }
  };

  return { messages, send, setMessages };
}
