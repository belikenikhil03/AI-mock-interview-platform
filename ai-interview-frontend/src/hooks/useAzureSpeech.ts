// ai-interview-frontend/src/hooks/useAzureSpeech.ts
// REPLACES: useSpeechRecognition.ts

import { useEffect, useRef, useState } from 'react';
import * as sdk from 'microsoft-cognitiveservices-speech-sdk';

interface UseAzureSpeechProps {
  onTranscript: (text: string, isFinal: boolean) => void;
  onSpeakingChange: (speaking: boolean) => void;
  enabled: boolean;
}

export function useAzureSpeech({
  onTranscript,
  onSpeakingChange,
  enabled
}: UseAzureSpeechProps) {
  const recognizerRef = useRef<sdk.SpeechRecognizer | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;

    // Get Azure credentials from backend
    initializeSpeechRecognizer();

    return () => {
      cleanup();
    };
  }, [enabled]);

  const initializeSpeechRecognizer = async () => {
    try {
      // Get speech config from backend
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/speech/token', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error('Failed to get speech token');
      }

      const { token: speechToken, region } = await response.json();

      // Create speech config
      const speechConfig = sdk.SpeechConfig.fromAuthorizationToken(speechToken, region);
      speechConfig.speechRecognitionLanguage = 'en-US';
      speechConfig.enableDictation();

      // Create audio config from microphone
      const audioConfig = sdk.AudioConfig.fromDefaultMicrophoneInput();

      // Create recognizer
      const recognizer = new sdk.SpeechRecognizer(speechConfig, audioConfig);

      // Recognizing (interim results)
      recognizer.recognizing = (s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizingSpeech) {
          onTranscript(e.result.text, false);
          onSpeakingChange(true);
        }
      };

      // Recognized (final results)
      recognizer.recognized = (s, e) => {
        if (e.result.reason === sdk.ResultReason.RecognizedSpeech) {
          onTranscript(e.result.text, true);
          onSpeakingChange(false);
        } else if (e.result.reason === sdk.ResultReason.NoMatch) {
          console.log('No speech recognized');
        }
      };

      // Session started
      recognizer.sessionStarted = (s, e) => {
        console.log('✅ Azure Speech session started');
        setIsListening(true);
        setError(null);
      };

      // Session stopped
      recognizer.sessionStopped = (s, e) => {
        console.log('Azure Speech session stopped');
        setIsListening(false);
      };

      // Canceled
      recognizer.canceled = (s, e) => {
        console.error('Azure Speech canceled:', e.errorDetails);
        setError(e.errorDetails);
        setIsListening(false);
      };

      recognizerRef.current = recognizer;

      // Start continuous recognition
      recognizer.startContinuousRecognitionAsync(
        () => {
          console.log('✅ Continuous recognition started');
        },
        (err) => {
          console.error('❌ Failed to start recognition:', err);
          setError(err);
        }
      );

    } catch (err: any) {
      console.error('Azure Speech initialization error:', err);
      setError(err.message);
    }
  };

  const cleanup = () => {
    if (recognizerRef.current) {
      recognizerRef.current.stopContinuousRecognitionAsync(
        () => {
          recognizerRef.current?.close();
          recognizerRef.current = null;
          console.log('✅ Speech recognizer cleaned up');
        },
        (err) => {
          console.error('Cleanup error:', err);
        }
      );
    }
  };

  const stop = () => {
    cleanup();
    setIsListening(false);
  };

  return {
    isListening,
    error,
    stop
  };
}
