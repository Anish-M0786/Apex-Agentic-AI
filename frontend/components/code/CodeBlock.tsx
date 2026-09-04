'use client';
import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Check, Copy } from 'lucide-react';

interface CodeBlockProps {
  language: string;
  code: string;
}

export function CodeBlock({ language, code }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code.trim());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code: ', err);
    }
  };

  return (
    <div className="rounded-xl overflow-hidden border border-gray-700 bg-[#1e1e1e] my-4 shadow-sm group">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#2d2d2d] text-gray-300 text-xs font-sans border-b border-gray-700">
        <span className="capitalize">{language || 'Code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded transition-colors text-gray-400 hover:text-gray-100 hover:bg-white/5 opacity-80 group-hover:opacity-100 focus:opacity-100"
          aria-label="Copy code"
          title={copied ? 'Copied!' : 'Copy code'}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Code */}
      <div className="text-sm">
        <SyntaxHighlighter
          language={language.toLowerCase() || 'text'}
          style={oneDark}
          showLineNumbers={true}
          customStyle={{ margin: 0, padding: '1rem', backgroundColor: 'transparent' }}
          lineNumberStyle={{ minWidth: '3em', paddingRight: '1em', color: '#666', textAlign: 'right' }}
        >
          {code.trim()}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
