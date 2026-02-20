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
  const enabledRef = useRef(enabled);
  const restartAttempts = useRef(0);

  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const MAX_RESTARTS = 3;

  // Keep latest enabled value
  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    if (typeof window === 'undefined') return;

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

    recognition.onstart = () => {
      console.log('✅ Speech recognition started');
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let speaking = false;

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          onTranscript(transcript, true);
        } else {
          onTranscript(transcript, false);
          speaking = true;
        }
      }

      onSpeakingChange(speaking);
    };

    recognition.onerror = (event: any) => {
      console.error('❌ Speech error:', event.error);
      setError(event.error);
    };

    recognition.onend = () => {
      console.log('Speech recognition ended');
      setIsListening(false);

      if (!enabledRef.current) return;

      if (restartAttempts.current >= MAX_RESTARTS) {
        console.error('❌ Max restart attempts reached');
        setError('Speech recognition failed');
        return;
      }

      restartAttempts.current++;

      setTimeout(() => {
        try {
          recognition.start();
        } catch (err) {
          console.log('Restart failed');
        }
      }, 1500);
    };

    recognitionRef.current = recognition;

    if (enabled) {
      try {
        recognition.start();
      } catch (err) {
        console.error('Initial start failed');
      }
    }

    return () => {
      recognition.onend = null; // prevent auto restart on unmount
      recognition.stop();
    };
  }, []);

  // Control start/stop based on enabled
  useEffect(() => {
    const recognition = recognitionRef.current;
    if (!recognition) return;

    if (enabled) {
      restartAttempts.current = 0;
      try {
        recognition.start();
      } catch {}
    } else {
      recognition.stop();
    }
  }, [enabled]);

  const stop = () => {
    enabledRef.current = false;
    recognitionRef.current?.stop();
  };

  return {
    isListening,
    error,
    stop
  };
}