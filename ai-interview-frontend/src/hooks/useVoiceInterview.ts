// ai-interview-frontend/src/hooks/useVoiceInterview.ts

import { useState, useRef, useCallback } from 'react';
import { AudioPlayer } from '@/utils/audioUtils';

interface VoiceInterviewState {
  status: 'connecting' | 'ready' | 'active' | 'ended';
  currentQuestion: string;
  questionIndex: number;
  aiSpeaking: boolean;
  interviewId: number | null;
}

interface UseVoiceInterviewProps {
  sessionId: string;
  onStateChange: (state: VoiceInterviewState) => void;
}

export function useVoiceInterview({ sessionId, onStateChange }: UseVoiceInterviewProps) {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const audioPlayerRef = useRef<AudioPlayer | null>(null);
  
  const state = useRef<VoiceInterviewState>({
    status: 'connecting',
    currentQuestion: '',
    questionIndex: 0,
    aiSpeaking: false,
    interviewId: null
  });

  const updateState = (updates: Partial<VoiceInterviewState>) => {
    state.current = { ...state.current, ...updates };
    onStateChange(state.current);
  };

  const connect = useCallback(() => {
    const token = localStorage.getItem('token');
    if (!token) throw new Error('No token');

    // Initialize audio player
    audioPlayerRef.current = new AudioPlayer();

    const wsUrl = `ws://localhost:8000/api/interviews/${sessionId}/ws?token=${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('✅ WebSocket connected');
    };

    websocket.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      await handleMessage(message);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('WebSocket closed');
      cleanup();
    };

    setWs(websocket);
    return websocket;
  }, [sessionId]);

  const handleMessage = async (message: any) => {
    switch (message.type) {
      case 'ready':
        updateState({ status: 'ready' });
        break;

      case 'question':
        updateState({
          status: 'active',
          currentQuestion: message.text,
          questionIndex: message.index,
          aiSpeaking: true
        });
        break;

      case 'ai_audio':
        if (audioPlayerRef.current) {
          await audioPlayerRef.current.playChunk(message.audio);
        }
        break;

      case 'ai_done_speaking':
        updateState({ aiSpeaking: false });
        break;

      case 'ended':
        updateState({
          status: 'ended',
          interviewId: message.interview_id
        });
        break;

      case 'error':
        console.error('Interview error:', message.message);
        break;
    }
  };

  const sendTranscript = useCallback((transcript: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'response_complete',
        transcript
      }));
    }
  }, [ws]);

  const endInterview = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'end' }));
    }
  }, [ws]);

  const cleanup = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.close();
      audioPlayerRef.current = null;
    }
    if (ws) {
      ws.close();
      setWs(null);
    }
  };

  return {
    connect,
    sendTranscript,
    endInterview,
    cleanup,
    currentState: state.current
  };
}