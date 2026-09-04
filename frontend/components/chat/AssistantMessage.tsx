'use client';

// @ts-ignore
import { Check, Copy, RefreshCw, X, Volume2, Square } from 'lucide-react';
import { useState, useEffect, useRef, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types/chat';
import { sendFeedback } from '@/lib/api';
import { ArtifactList } from '@/components/artifacts/ArtifactList';
import { CodeBlock } from '@/components/code/CodeBlock';
import { useVoice } from '@/hooks/useVoice';
import { LiveActivityList } from '@/components/activity/LiveActivityList';

function readableResponse(markdown: string): string {
  const tick = String.fromCharCode(96);
  const fence = tick.repeat(3);
  return markdown.replace(new RegExp(fence + '[^\n]*\n([\\s\\S]*?)' + fence, 'g'), '$1')
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '').replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2').replace(new RegExp(tick + '([^' + tick + ']+)' + tick, 'g'), '$1').trim();
}

export function AssistantMessage({ message, prompt, onRegenerate }: { message: Message; prompt?: string; onRegenerate?: () => void }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'positive' | 'negative'>();
  const { playTTS, stopTTS, isPlayingTTS } = useVoice();
  
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const hasTyped = useRef(false);

  useEffect(() => {
    if (!message.content) {
      setDisplayedContent('');
      hasTyped.current = false;
      setIsTyping(false);
      return;
    }

    // Only type once per full message content
    if (hasTyped.current) {
      setDisplayedContent(message.content);
      return;
    }

    setIsTyping(true);
    let i = 0;
    
    // Calculate speed based on length to ensure it doesn't take forever for long messages
    // but remains readable for short ones
    const baseSpeed = 10;
    const speed = message.content.length > 500 ? 2 : baseSpeed;
    
    const interval = setInterval(() => {
      // Add multiple characters per tick for very long messages to speed up
      const charsToAdd = message.content.length > 1000 ? 5 : 1;
      i += charsToAdd;
      
      setDisplayedContent(message.content.slice(0, i));
      
      if (i >= message.content.length) {
        clearInterval(interval);
        setIsTyping(false);
        hasTyped.current = true;
      }
    }, speed);

    return () => clearInterval(interval);
  }, [message.content]);

  const rate = async (rating: 'positive' | 'negative') => {
    if (!prompt || feedback) return;
    setFeedback(rating);
    await sendFeedback(prompt, message.content, rating).catch(() => setFeedback(undefined));
  };

  const copy = async () => {
    const text = readableResponse(message.content);
    try { await navigator.clipboard.writeText(text); }
    catch {
      const area = document.createElement('textarea');
      area.value = text; area.style.position = 'fixed'; area.style.opacity = '0';
      document.body.appendChild(area); area.focus(); area.select(); document.execCommand('copy'); area.remove();
    }
    setCopied(true); window.setTimeout(() => setCopied(false), 1600);
  };

  return <div className="message assistant">
    
    <LiveActivityList activities={message.activities || []} completed={message.status === 'completed' || message.status === 'error'} />

    {displayedContent && <div className={`markdown ${isTyping ? 'typing' : ''}`}><ReactMarkdown remarkPlugins={[remarkGfm]} components={{ code: ({ children, className, ...rest }: any) => { const match = /language-(\w+)/.exec(className || ''); return match ? <CodeBlock language={match[1]} code={String(children).replace(/\\n$/, '')} /> : <code className={className} {...rest}>{children}</code>; } }}>{displayedContent + (isTyping ? '▋' : '')}</ReactMarkdown></div>}
    <ArtifactList artifacts={message.artifacts || []} />
    {message.status === 'error' && <button className="retry" onClick={onRegenerate}>Try again</button>}
    {message.content && !isTyping && <div className="message-tools">
      <button onClick={() => isPlayingTTS ? stopTTS() : playTTS(readableResponse(message.content))} aria-label={isPlayingTTS ? 'Stop reading' : 'Listen to response'} title={isPlayingTTS ? 'Stop' : 'Listen'}>{isPlayingTTS ? <Square size={15} /> : <Volume2 size={15} />}</button>
      <button onClick={copy} aria-label={copied ? 'Response copied' : 'Copy response'} title={copied ? 'Copied' : 'Copy response'}>{copied ? <Check size={15} /> : <Copy size={15} />}</button>
      {onRegenerate && <button onClick={onRegenerate} aria-label="Regenerate response"><RefreshCw size={15} /></button>}
      {prompt && <><button onClick={() => void rate('positive')} aria-label="Helpful response" title="Helpful" className={feedback === 'positive' ? 'feedback-selected' : ''}><Check size={15} /></button><button onClick={() => void rate('negative')} aria-label="Unhelpful response" title="Not helpful" className={feedback === 'negative' ? 'feedback-selected' : ''}><X size={15} /></button></>}
    </div>}
  </div>;
}
