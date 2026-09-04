import { useState, useRef, useCallback } from 'react';

export function useVoice() {
  const [isListening, setIsListening] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isPlayingTTS, setIsPlayingTTS] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start();
      setIsListening(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  }, []);

  const stopListening = useCallback(async (): Promise<string | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current) {
        resolve(null);
        return;
      }

      mediaRecorderRef.current.onstop = async () => {
        setIsListening(false);
        setIsTranscribing(true);
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Stop all tracks to release microphone
        mediaRecorderRef.current?.stream.getTracks().forEach(track => track.stop());
        
        try {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');
          
          const response = await fetch('/api/voice/transcribe', {
            method: 'POST',
            body: formData,
          });
          
          if (!response.ok) throw new Error('Transcription failed');
          
          const data = await response.json();
          setIsTranscribing(false);
          resolve(data.transcript || '');
        } catch (error) {
          console.error('Error transcribing audio:', error);
          setIsTranscribing(false);
          resolve(null);
        }
      };

      mediaRecorderRef.current.stop();
    });
  }, []);

  const playTTS = useCallback(async (text: string) => {
    try {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      setIsPlayingTTS(true);

      const response = await fetch('/api/voice/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) throw new Error('TTS failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      const audio = new Audio(url);
      audioRef.current = audio;
      
      audio.onended = () => {
        setIsPlayingTTS(false);
        URL.revokeObjectURL(url);
      };
      
      audio.onerror = () => {
        setIsPlayingTTS(false);
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch (error) {
      console.error('Error playing TTS:', error);
      setIsPlayingTTS(false);
    }
  }, []);

  const stopTTS = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setIsPlayingTTS(false);
  }, []);

  return {
    isListening,
    isTranscribing,
    isPlayingTTS,
    startListening,
    stopListening,
    playTTS,
    stopTTS
  };
}
