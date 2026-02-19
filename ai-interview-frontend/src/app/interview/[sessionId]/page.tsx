// COMPLETE REWRITE: ai-interview-frontend/src/app/interview/[sessionId]/page.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function VoiceInterviewPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const videoRef = useRef<HTMLVideoElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const timelineRef = useRef<any[]>([]);
  const interviewStartTimeRef = useRef<number>(0);

  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'ready' | 'active' | 'ended'>('connecting');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [candidateSpeaking, setCandidateSpeaking] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);
  const [interviewId, setInterviewId] = useState<number | null>(null);

  // Audio context for playing AI voice
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioBufferSourceNode[]>([]);

  // Speech recognition
  const recognitionRef = useRef<any>(null);
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      initCamera();
      initAudio();
      initSpeechRecognition();
      connectWebSocket();
    }, 100);

    return () => {
      clearTimeout(timer);
      stopEverything();
    };
  }, []);

  const initCamera = async () => {
    const video = document.getElementById('interview-video') as HTMLVideoElement;
    if (!video) {
      setTimeout(initCamera, 200);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
        audio: true
      });

      video.srcObject = stream;
      await video.play();
      setCameraActive(true);

      // Start recording
      startRecording(stream);

    } catch (err) {
      console.error('Camera error:', err);
    }
  };

  const startRecording = (stream: MediaStream) => {
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'video/webm;codecs=vp9',
      videoBitsPerSecond: 2500000
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunksRef.current.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      uploadRecording();
    };

    mediaRecorder.start(1000); // Capture chunks every second
    mediaRecorderRef.current = mediaRecorder;

    // Mark interview start time
    interviewStartTimeRef.current = Date.now();
  };

  const initAudio = () => {
    if (typeof window !== 'undefined') {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  };

  const initSpeechRecognition = () => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    let finalTranscript = '';

    recognition.onresult = (event: any) => {
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
          
          // Log filler words
          detectFillerWords(transcript, getCurrentTimestamp());
        } else {
          interimTranscript += transcript;
        }
      }

      // Reset silence timer on speech
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }

      // Set 2.5s silence timer
      silenceTimerRef.current = setTimeout(() => {
        if (finalTranscript.trim() && ws) {
          ws.send(JSON.stringify({
            type: 'response_complete',
            transcript: finalTranscript.trim()
          }));
          finalTranscript = '';
        }
      }, 2500);

      setCandidateSpeaking(interimTranscript.length > 0);
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
    };

    recognitionRef.current = recognition;
  };

  const detectFillerWords = (text: string, timestamp: number) => {
    const fillerWords = ['um', 'uh', 'like', 'you know', 'basically', 'literally'];
    const words = text.toLowerCase().split(' ');

    words.forEach(word => {
      if (fillerWords.includes(word.replace(/[.,!?]/g, ''))) {
        logEvent({
          timestamp,
          type: 'filler_word',
          data: { word },
          severity: 'warning'
        });
      }
    });
  };

  const logEvent = (event: any) => {
    timelineRef.current.push(event);
  };

  const getCurrentTimestamp = () => {
    return (Date.now() - interviewStartTimeRef.current) / 1000;
  };

  const connectWebSocket = () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const wsUrl = `ws://localhost:8000/api/interviews/${sessionId}/ws?token=${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('✅ WebSocket connected');
    };

    websocket.onmessage = async (event) => {
      const message = JSON.parse(event.data);
      handleMessage(message);
    };

    websocket.onerror = () => {
      alert('Connection failed');
      router.push('/dashboard');
    };

    websocket.onclose = () => {
      stopEverything();
    };

    setWs(websocket);
  };

  const handleMessage = async (message: any) => {
    switch (message.type) {
      case 'ready':
        setStatus('ready');
        // Start speech recognition
        if (recognitionRef.current) {
          recognitionRef.current.start();
        }
        break;

      case 'question':
        setCurrentQuestion(message.text);
        setQuestionIndex(message.index);
        setStatus('active');
        setAiSpeaking(true);
        logEvent({
          timestamp: getCurrentTimestamp(),
          type: 'question_asked',
          data: { question: message.text, index: message.index },
          severity: 'info'
        });
        break;

      case 'ai_audio':
        await playAudioChunk(message.audio);
        break;

      case 'ai_done_speaking':
        setAiSpeaking(false);
        break;

      case 'ended':
        setStatus('ended');
        setInterviewId(message.interview_id);
        stopEverything();
        break;
    }
  };

  const playAudioChunk = async (audioBase64: string) => {
    if (!audioContextRef.current) return;

    try {
      const audioData = Uint8Array.from(atob(audioBase64), c => c.charCodeAt(0));
      const audioBuffer = await audioContextRef.current.decodeAudioData(audioData.buffer);

      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      source.start();

      audioQueueRef.current.push(source);
    } catch (err) {
      console.error('Audio playback error:', err);
    }
  };

  const stopEverything = () => {
    // Stop recording
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }

    // Stop camera
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
    }

    setCameraActive(false);
  };

  const uploadRecording = async () => {
    if (!interviewId || recordedChunksRef.current.length === 0) return;

    const videoBlob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
    const duration = Math.floor((Date.now() - interviewStartTimeRef.current) / 1000);

    const formData = new FormData();
    formData.append('video', videoBlob, 'recording.webm');
    formData.append('timeline', JSON.stringify(timelineRef.current));
    formData.append('duration', duration.toString());

    const token = localStorage.getItem('token');

    try {
      const response = await fetch(
        `http://localhost:8000/api/recordings/interviews/${interviewId}/upload-recording`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
          body: formData
        }
      );

      if (response.ok) {
        console.log('✅ Recording uploaded');
        setTimeout(() => router.push(`/feedback/${interviewId}`), 2000);
      }
    } catch (err) {
      console.error('Upload failed:', err);
      setTimeout(() => router.push(`/feedback/${interviewId}`), 2000);
    }
  };

  const endInterview = () => {
    if (ws && confirm('End interview?')) {
      ws.send(JSON.stringify({ type: 'end' }));
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">🎤 Voice Interview</h1>
            <p className="text-sm text-gray-400">Session: {sessionId.slice(0, 8)}...</p>
          </div>
          <div className={`w-3 h-3 rounded-full ${status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {status === 'connecting' && (
          <div className="text-center py-20">
            <div className="text-xl">Connecting...</div>
          </div>
        )}

        {status === 'ready' && (
          <div className="text-center py-20">
            <div className="text-2xl font-bold mb-4">🎤 Interview Ready!</div>
            <div className="text-gray-400">AI is preparing your first question...</div>
          </div>
        )}

        {status === 'ended' && (
          <div className="text-center py-20">
            <div className="text-3xl font-bold mb-4">✅ Complete!</div>
            <div className="text-gray-400">Uploading recording...</div>
          </div>
        )}

        {status === 'active' && (
          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-6">
              {/* AI Avatar */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center">
                <div className={`w-32 h-32 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-5xl mb-4 ${aiSpeaking ? 'ring-4 ring-blue-400 animate-pulse' : ''}`}>
                  👨‍💼
                </div>
                <div className="text-sm text-gray-400">
                  {aiSpeaking ? '🎤 AI Speaking...' : '👂 AI Listening...'}
                </div>
              </div>

              {/* Question Display */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div className="text-sm text-gray-400 mb-2">Question {questionIndex}</div>
                <div className="text-xl font-medium">{currentQuestion}</div>
              </div>

              {/* Video Feed */}
              <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
                <video
                  id="interview-video"
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-64 object-cover"
                  style={{ transform: 'scaleX(-1)' }}
                />
                <div className="p-3 bg-gray-800/50 flex justify-between text-xs">
                  <span>{candidateSpeaking ? '🎤 You are speaking...' : '⏸️ Listening...'}</span>
                  <span className={cameraActive ? 'text-green-400' : 'text-red-400'}>
                    {cameraActive ? '● Recording' : '● Off'}
                  </span>
                </div>
              </div>

              <button onClick={endInterview} className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-medium">
                End Interview
              </button>
            </div>

            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-400 mb-3">💡 Tips</h3>
              <ul className="text-xs text-gray-500 space-y-2">
                <li>• Speak clearly into your microphone</li>
                <li>• Look at the camera</li>
                <li>• Avoid filler words (um, uh, like)</li>
                <li>• Use the STAR method</li>
                <li>• Take brief pauses to think</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}