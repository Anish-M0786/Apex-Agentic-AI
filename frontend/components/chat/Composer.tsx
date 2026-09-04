'use client';

import { ChangeEvent, KeyboardEvent, useRef, useState, useEffect } from 'react';
// @ts-ignore
import { Paperclip, Send, Square, Mic } from 'lucide-react';

import { VoiceButton } from '@/components/voice/VoiceButton';

export function Composer({
  onSend,
  onUpload,
  busy,
  initial = ''
}: {
  onSend: (text: string) => void;
  onUpload: (file: File) => Promise<void>;
  busy: boolean;
  initial?: string;
}) {
  const [value, setValue] = useState(initial);
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setValue(initial);
  }, [initial]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [value]);

  const submit = () => {
    if (value.trim() && !busy) {
      onSend(value.trim());
      setValue('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const keys = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const upload = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void onUpload(file);
    e.target.value = '';
  };

  return (
    <div className="composer-container">
      <div className="composer-input-wrapper">
        <button className="composer-btn" onClick={() => inputRef.current?.click()} aria-label="Upload document" disabled={busy}>
          <Paperclip size={20} />
        </button>
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={keys}
          placeholder="Ask Apex anything..."
          rows={1}
          disabled={busy}
        />
        <input ref={inputRef} type="file" accept=".pdf,.docx,.pptx,application/pdf" hidden onChange={upload} />
        
        {value.trim() ? (
          <button className="composer-btn primary" onClick={submit} aria-label={busy ? 'Working' : 'Send message'} disabled={!value.trim() || busy}>
            {busy ? <Square size={20} /> : <Send size={20} />}
          </button>
        ) : (
          <VoiceButton 
            onTranscription={(text) => setValue(prev => prev + (prev ? ' ' : '') + text)} 
            disabled={busy} 
          />
        )}
      </div>
    </div>
  );
}
