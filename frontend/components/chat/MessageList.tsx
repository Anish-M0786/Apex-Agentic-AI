import type { Message } from '@/types/chat';
import { AssistantMessage } from './AssistantMessage';
import { UserMessage } from './UserMessage';

export function MessageList({ messages, onRegenerate }: { messages: Message[]; onRegenerate?: (content: string) => void }) {
  return <div className="messages">{messages.map((message, index) => {
    if (message.role === 'user') return <UserMessage key={message.id} message={message} />;
    const previousUser = [...messages.slice(0, index)].reverse().find(item => item.role === 'user');
    return <AssistantMessage key={message.id} message={message} prompt={previousUser?.content} onRegenerate={onRegenerate ? () => onRegenerate(message.content) : undefined} />;
  })}</div>;
}
