// ai-interview-frontend/src/hooks/useSpeechRecognition.ts

import { useEffect, useRef, useState } from 'react';

interface UseSpeechRecognitionProps {
  onTranscript: (text: string, isFinal: boolean) => void;
  onSpeakingChange: (speaking: boolean) => void;
  enabled: boolean;
}

declare global {
  interface Window {
    SpeechSDK?: any;
  }
}

const SPEECH_SDK_SCRIPT_ID = 'azure-speech-sdk-script';
const SPEECH_SDK_SCRIPT_SRC = 'https://aka.ms/csspeech/jsbrowserpackageraw';

async function loadAzureSpeechSDK(): Promise<any> {
  if (typeof window === 'undefined') {
    throw new Error('Browser environment is required for Azure Speech SDK.');
  }

  if (window.SpeechSDK) return window.SpeechSDK;

  const existingScript = document.getElementById(SPEECH_SDK_SCRIPT_ID) as HTMLScriptElement | null;

  if (existingScript) {
    await new Promise<void>((resolve, reject) => {
      if (window.SpeechSDK) {
        resolve();
        return;
      }

      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Azure Speech SDK script.')), {
        once: true,
      });
    });

    if (!window.SpeechSDK) {
      throw new Error('Azure Speech SDK script loaded, but SpeechSDK is unavailable.');
    }

    return window.SpeechSDK;
  }

  const script = document.createElement('script');
  script.id = SPEECH_SDK_SCRIPT_ID;
  script.src = SPEECH_SDK_SCRIPT_SRC;
  script.async = true;

  const loaded = new Promise<void>((resolve, reject) => {
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Azure Speech SDK script.'));
  });

  document.head.appendChild(script);
  await loaded;

  if (!window.SpeechSDK) {
    throw new Error('Azure Speech SDK loaded but SpeechSDK is undefined.');
  }

  return window.SpeechSDK;
}

export function useSpeechRecognition({
  onTranscript,
  onSpeakingChange,
  enabled,
}: UseSpeechRecognitionProps) {
  const recognizerRef = useRef<any>(null);
  const speechConfigRef = useRef<any>(null);
  const audioConfigRef = useRef<any>(null);

  const onTranscriptRef = useRef(onTranscript);
  const onSpeakingChangeRef = useRef(onSpeakingChange);
  const enabledRef = useRef(enabled);
  const manuallyStoppedRef = useRef(false);
  const restartTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const restartAttemptRef = useRef(0);

  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
    onSpeakingChangeRef.current = onSpeakingChange;
  }, [onTranscript, onSpeakingChange]);

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  const clearRestartTimer = () => {
    if (restartTimeoutRef.current) {
      clearTimeout(restartTimeoutRef.current);
      restartTimeoutRef.current = null;
    }
  };

  const stopAndDisposeRecognizer = () => {
    const recognizer = recognizerRef.current;
    recognizerRef.current = null;

    if (recognizer) {
      recognizer.stopContinuousRecognitionAsync(
        () => {
          recognizer.close();
        },
        () => {
          recognizer.close();
        }
      );
    }

    if (audioConfigRef.current) {
      try {
        audioConfigRef.current.close?.();
      } catch {
        // noop
      }
      audioConfigRef.current = null;
    }
  };

  const scheduleRestart = (reason: 'network' | 'service' | 'normal') => {
    if (!enabledRef.current || manuallyStoppedRef.current) return;
    if (restartTimeoutRef.current) return;

    restartAttemptRef.current += 1;

    let delayMs = 1000;
    if (reason === 'network' || reason === 'service') {
      delayMs = Math.min(30000, 1000 * 2 ** Math.min(restartAttemptRef.current, 5));
    }

    restartTimeoutRef.current = setTimeout(() => {
      restartTimeoutRef.current = null;
      void startRecognition();
    }, delayMs);
  };

  const startRecognition = async () => {
    if (!enabledRef.current || manuallyStoppedRef.current) return;

    clearRestartTimer();
    stopAndDisposeRecognizer();

    try {
      const speechKey = process.env.NEXT_PUBLIC_AZURE_SPEECH_KEY;
      const speechRegion = process.env.NEXT_PUBLIC_AZURE_SPEECH_REGION;
      const speechLanguage = process.env.NEXT_PUBLIC_AZURE_SPEECH_LANGUAGE || 'en-US';

      if (!speechKey || !speechRegion) {
        setError('Missing Azure Speech config. Set NEXT_PUBLIC_AZURE_SPEECH_KEY and NEXT_PUBLIC_AZURE_SPEECH_REGION.');
        return;
      }

      const SpeechSDK = await loadAzureSpeechSDK();

      const speechConfig = SpeechSDK.SpeechConfig.fromSubscription(speechKey, speechRegion);
      speechConfig.speechRecognitionLanguage = speechLanguage;

      const audioConfig = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      const recognizer = new SpeechSDK.SpeechRecognizer(speechConfig, audioConfig);

      speechConfigRef.current = speechConfig;
      audioConfigRef.current = audioConfig;
      recognizerRef.current = recognizer;

      recognizer.recognizing = (_: any, event: any) => {
        const text = event?.result?.text?.trim?.() ?? '';
        if (!text) return;

        setIsListening(true);
        onSpeakingChangeRef.current(true);
        onTranscriptRef.current(text, false);
      };

      recognizer.recognized = (_: any, event: any) => {
        const result = event?.result;
        const text = result?.text?.trim?.() ?? '';

        if (result?.reason === SpeechSDK.ResultReason.RecognizedSpeech && text) {
          onTranscriptRef.current(text, true);
        }

        onSpeakingChangeRef.current(false);
      };

      recognizer.sessionStarted = () => {
        setIsListening(true);
        setError(null);
        restartAttemptRef.current = 0;
      };

      recognizer.sessionStopped = () => {
        setIsListening(false);
        onSpeakingChangeRef.current(false);

        if (!enabledRef.current || manuallyStoppedRef.current) return;
        scheduleRestart('normal');
      };

      recognizer.canceled = (_: any, event: any) => {
        setIsListening(false);
        onSpeakingChangeRef.current(false);

        const reason = event?.reason;
        const errorDetails = event?.errorDetails || 'Speech recognition cancelled.';

        if (reason === SpeechSDK.CancellationReason.EndOfStream && !manuallyStoppedRef.current) {
          scheduleRestart('normal');
          return;
        }

        setError(errorDetails);

        if (!enabledRef.current || manuallyStoppedRef.current) return;

        if (reason === SpeechSDK.CancellationReason.Error) {
          const lower = String(errorDetails).toLowerCase();
          if (lower.includes('network') || lower.includes('connection')) {
            scheduleRestart('network');
          } else {
            scheduleRestart('service');
          }
        }
      };

      await new Promise<void>((resolve, reject) => {
        recognizer.startContinuousRecognitionAsync(
          () => resolve(),
          (err: any) => reject(err)
        );
      });

      setIsListening(true);
    } catch (err: any) {
      setIsListening(false);
      onSpeakingChangeRef.current(false);
      setError(err?.message || 'Failed to start Azure Speech recognition.');
      scheduleRestart('service');
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;

    manuallyStoppedRef.current = !enabled;

    if (enabled) {
      void startRecognition();
    } else {
      clearRestartTimer();
      stopAndDisposeRecognizer();
      setIsListening(false);
      onSpeakingChangeRef.current(false);
    }

    return () => {
      manuallyStoppedRef.current = true;
      clearRestartTimer();
      stopAndDisposeRecognizer();
      setIsListening(false);
      onSpeakingChangeRef.current(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const stop = () => {
    manuallyStoppedRef.current = true;
    clearRestartTimer();
    stopAndDisposeRecognizer();
    setIsListening(false);
    onSpeakingChangeRef.current(false);
  };

  return {
    isListening,
    error,
    stop,
  };
}
