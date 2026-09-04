import { FileText } from 'lucide-react';
import type { Message } from '@/types/chat';

export function UserMessage({ message }: { message: Message }) {
  return <div className="message user">
    {message.attachments?.map(file => (
      <div className="message-attachment" key={file.id}>
        <FileText size={18} aria-hidden="true" />
        <span title={file.filename}>{file.filename}</span>
        <small>{file.type.toUpperCase()}</small>
      </div>
    ))}
    {message.content && <p>{message.content}</p>}
  </div>;
}