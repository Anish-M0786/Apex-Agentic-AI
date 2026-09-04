import { Mic, Square, Loader2 } from 'lucide-react';
import { useVoice } from '@/hooks/useVoice';

export function VoiceButton({ 
  onTranscription, 
  disabled 
}: { 
  onTranscription: (text: string) => void;
  disabled?: boolean;
}) {
  const { isListening, isTranscribing, startListening, stopListening } = useVoice();

  const handleClick = async () => {
    if (isListening) {
      const text = await stopListening();
      if (text) onTranscription(text);
    } else {
      await startListening();
    }
  };

  if (isTranscribing) {
    return (
      <button className="composer-btn" disabled aria-label="Transcribing">
        <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
      </button>
    );
  }

  return (
    <button 
      className={`composer-btn ${isListening ? 'listening' : ''}`} 
      onClick={handleClick} 
      aria-label={isListening ? 'Stop listening' : 'Voice input'} 
      disabled={disabled}
      style={isListening ? { color: 'red' } : {}}
    >
      {isListening ? <Square size={20} /> : <Mic size={20} />}
    </button>
  );
}
