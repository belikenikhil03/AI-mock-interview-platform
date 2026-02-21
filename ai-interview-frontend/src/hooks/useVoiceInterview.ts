// UPDATE: src/hooks/useVoiceInterview.ts
// Add logging to see what messages are coming

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
    console.log('✅ AudioPlayer initialized');

    const wsUrl = `ws://localhost:8000/api/interviews/${sessionId}/ws?token=${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('✅ WebSocket connected');
    };

    websocket.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      console.log('📨 WS Message:', message.type, message);  // DEBUG
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
        console.log('📝 Interview ready');
        updateState({ status: 'ready' });
        break;

      case 'question':
        console.log(`Question ${message.index} starting`);
        updateState({
          status: 'active',
          currentQuestion: '',  // Clear for streaming
          questionIndex: message.index,
          aiSpeaking: true
        });
        break;

      case 'ai_audio':
        console.log('🔊 Audio chunk received, length:', message.audio?.length);
        if (audioPlayerRef.current) {
          console.log('📢 Playing audio chunk...');
          try {
            await audioPlayerRef.current.playChunk(message.audio);
            console.log('✅ Audio played');
          } catch (err) {
            console.error('❌ Audio play error:', err);
          }
        } else {
          console.error('❌ No AudioPlayer instance!');
        }
        break;
      
      case 'ai_transcript_delta':
        // Stream AI text word by word as it speaks
        updateState({ 
          currentQuestion: (state.current.currentQuestion || '') + message.text
        });
        break;  

      case 'ai_done_speaking':
        console.log('✅ AI finished speaking');
        updateState({ aiSpeaking: false });
        break;

      case 'ended':
        console.log('🏁 Interview ended');
        updateState({
          status: 'ended',
          interviewId: message.interview_id
        });
        break;

      case 'error':
        console.error('❌ Interview error:', message.message);
        break;
        
      default:
        console.log('⚠️ Unknown message type:', message.type);
    }
  };

  const sendTranscript = useCallback((transcript: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      console.log('📤 Sending transcript:', transcript.slice(0, 50));
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