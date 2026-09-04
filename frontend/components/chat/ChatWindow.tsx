'use client';
import { useEffect, useRef, useState } from 'react';
import { uploadPdf } from '@/lib/api';
import { FileText, X } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { useAgent } from '@/hooks/useAgent';
import { useActivityStream } from '@/hooks/useActivityStream';
import { Composer } from './Composer';
import { MessageList } from './MessageList';
import { WelcomeScreen } from './WelcomeScreen';
import type { Message, MessageAttachment } from '@/types/chat';

const CREATION_VERBS = /\b(create|make|generate|export|produce|build|write|draft)\b/i;
const CREATION_TARGETS = /\b(pdf|excel|xlsx|spreadsheet|powerpoint|ppt|presentation|docx|word document|notes|study guide|quiz|mcqs?|flashcards?|questions|report|summary report)\b/i;
const isAgentWorkflow = (text: string) => CREATION_VERBS.test(text) && CREATION_TARGETS.test(text);

export function ChatWindow() {
  const scrollRef = useRef<HTMLElement>(null);
  const chat = useChat();
  const agent = useAgent();
  const [documents, setDocuments] = useState<MessageAttachment[]>([]);
  const [pendingAttachments, setPendingAttachments] = useState<MessageAttachment[]>([]);
  const [seed, setSeed] = useState('');
  const [agentMessage, setAgentMessage] = useState<Message>();

  useActivityStream(agent.requestId, {
    onActivity: agent.onActivity,
    onComplete: r => {
      agent.onComplete(r);
      const artifacts = r.artifacts || [];
      const content = artifacts.length
        ? artifacts.map(a => '- Created **' + a.filename + '**').join('\n')
        : r.summary?.startsWith('Executed') ? 'Workflow completed.' : r.summary || 'Completed.';
      setAgentMessage(m => {
        if (!m) return m;
        const updated = { ...m, status: r.status === 'completed' ? 'completed' : 'error' as Message['status'], content, activities: agent.activities, artifacts: agent.artifacts };
        chat.setMessages(messages => messages.map(item => item.id === m.id ? updated : item));
        return updated;
      });
    },
    onError: message => {
      agent.onError(message);
      setAgentMessage(m => m ? { ...m, status: 'error', content: message } : undefined);
    },
  });

  const send = async (text: string) => {
    const attachmentSnapshot = pendingAttachments;
    if (isAgentWorkflow(text)) {
      const user: Message = { id: crypto.randomUUID(), role: 'user', content: text, status: 'completed', createdAt: new Date().toISOString(), attachments: attachmentSnapshot };
      const placeholder: Message = { id: crypto.randomUUID(), role: 'assistant', content: '', status: 'thinking', createdAt: new Date().toISOString(), activities: [] };
      chat.setMessages(m => [...m, user, placeholder]);
      setPendingAttachments([]);
      setAgentMessage(placeholder);
      try { await agent.start(text, documents.map(d => d.id)); }
      catch { chat.setMessages(m => m.map(x => x.id === placeholder.id ? { ...x, content: 'Something went wrong.', status: 'error' } : x)); }
    } else {
      setAgentMessage(undefined);
      await chat.send(text, documents.map(d => d.id), attachmentSnapshot);
      setPendingAttachments([]);
    }
  };

  const displayed = agentMessage ? [...chat.messages.filter(m => m.id !== agentMessage.id), { ...agentMessage, activities: agent.activities, artifacts: agent.artifacts, status: agent.error ? 'error' : agent.result ? 'completed' : 'streaming' as Message['status'] }] : chat.messages;
  const handleUpload = async (file: File) => {
    const r = await uploadPdf(file);
    const document: MessageAttachment = { id: r.document_id, filename: r.filename, type: 'pdf' };
    setDocuments(prev => prev.some(d => d.id === document.id) ? prev : [...prev, document]);
    setPendingAttachments(prev => prev.some(d => d.id === document.id) ? prev : [...prev, document]);
  };
  const busy = Boolean(agent.requestId && !agent.result && !agent.error);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [displayed.length, agent.activities.length, agent.result]);

  return <main ref={scrollRef} className="chat-window">
    {!displayed.length ? <WelcomeScreen onSelect={setSeed} /> : <MessageList messages={displayed} />}
    {pendingAttachments.length > 0 && <div className="upload-preview" aria-label="Attached documents">
      {pendingAttachments.map(file => <div className="upload-chip" key={file.id}>
        <FileText size={16} aria-hidden="true" /><span title={file.filename}>{file.filename}</span>
        <button type="button" aria-label={'Remove ' + file.filename} onClick={() => setPendingAttachments(prev => prev.filter(d => d.id !== file.id))}><X size={14} /></button>
      </div>)}
    </div>}
    {documents.length > 0 && <p className="upload-status">{documents.length} document{documents.length > 1 ? 's' : ''} available for this chat</p>}
    <Composer key={seed} initial={seed} busy={busy} onSend={send} onUpload={handleUpload} />
  </main>;
}