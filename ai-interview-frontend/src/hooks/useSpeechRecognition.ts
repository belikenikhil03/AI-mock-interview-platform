// ai-interview-frontend/src/hooks/useSpeechRecognition.ts

import { useEffect, useRef, useState } from 'react';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string, isFinal: boolean) => void;
  onSpeakingChange: (speaking: boolean) => void;
  enabled: boolean;
}

export function useSpeechRecognition({
  onTranscript,
  onSpeakingChange,
  enabled
}: UseSpeechRecognitionProps) {
  const recognitionRef = useRef<any>(null);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !enabled) return;

    const SpeechRecognition = 
      (window as any).SpeechRecognition || 
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setError('Speech recognition not supported');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      console.log('🎤 Speech recognition started');
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let interimText = '';
      let finalText = '';
      let hasSpeech = false;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        
        if (event.results[i].isFinal) {
          finalText += transcript + ' ';
          onTranscript(transcript, true);
        } else {
          interimText += transcript;
          onTranscript(transcript, false);
          hasSpeech = true;
        }
      }

      onSpeakingChange(hasSpeech || finalText.length > 0);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setError(event.error);

      // Auto-restart on network error
      if (event.error === 'network') {
        setTimeout(() => {
          if (enabled) {
            try {
              recognition.start();
            } catch (e) {
              console.log('Already started');
            }
          }
        }, 1000);
      }
    };

    recognition.onend = () => {
      console.log('Speech recognition ended');
      setIsListening(false);

      // Auto-restart if still enabled
      if (enabled) {
        setTimeout(() => {
          try {
            recognition.start();
          } catch (e) {
            console.log('Failed to restart');
          }
        }, 100);
      }
    };

    recognitionRef.current = recognition;

    // Start recognition
    try {
      recognition.start();
    } catch (e) {
      console.error('Failed to start recognition:', e);
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
    };
  }, [enabled, onTranscript, onSpeakingChange]);

  const stop = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
        setIsListening(false);
      } catch (e) {}
    }
  };

  return {
    isListening,
    error,
    stop
  };
}
