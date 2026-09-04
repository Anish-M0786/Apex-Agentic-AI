import type { Activity } from './activity';
import type { Artifact } from './artifact';

export type MessageStatus = 'idle' | 'thinking' | 'streaming' | 'completed' | 'error';
export interface MessageAttachment { id: string; filename: string; type: 'pdf' | 'image' | 'file'; }
export interface Message { id: string; role: 'user' | 'assistant'; content: string; createdAt: string; status: MessageStatus; activities?: Activity[]; artifacts?: Artifact[]; attachments?: MessageAttachment[]; }
export interface Conversation { id: string; title: string; createdAt: string; updatedAt: string; messages: Message[]; }