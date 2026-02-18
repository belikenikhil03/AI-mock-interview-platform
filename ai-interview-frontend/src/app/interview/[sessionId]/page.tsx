// src/app/interview/[sessionId]/page.tsx - FINAL WORKING VERSION
'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function InterviewPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const cameraInitialized = useRef(false); // Prevent double init
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'ready' | 'active' | 'ended'>('connecting');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(8);
  const [answer, setAnswer] = useState('');
  const [metrics, setMetrics] = useState({
    filler_words: 0,
    total_words: 0,
    speech_rate_wpm: 0,
    questions_answered: 0,
  });
  const [timeRemaining, setTimeRemaining] = useState(480);
  const [cameraActive, setCameraActive] = useState(false);

  useEffect(() => {
    if (!cameraInitialized.current) {
      cameraInitialized.current = true;
      startCamera();
      connectWebSocket();
    }
    
    return () => {
      stopCamera();
      if (ws) ws.close();
    };
  }, []);

  useEffect(() => {
    if (status === 'ended') {
      stopCamera();
    }
  }, [status]);

  useEffect(() => {
    if (status === 'active') {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => Math.max(0, prev - 1));
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [status]);

  const startCamera = async () => {
    if (!navigator?.mediaDevices?.getUserMedia) {
      console.error('Camera not supported');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false 
      });
      
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setCameraActive(true);
        console.log('✅ Camera active');
      }
    } catch (err) {
      console.error('Camera error:', err);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
  };

  const connectWebSocket = () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const websocket = new WebSocket(`ws://localhost:8000/api/interviews/${sessionId}/ws?token=${token}`);

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'ready':
          setStatus('ready');
          setTotalQuestions(message.total_questions);
          break;
        case 'question':
          setCurrentQuestion(message.text);
          setQuestionIndex(message.index);
          setStatus('active');
          setAnswer('');
          break;
        case 'metrics':
          setMetrics({
            filler_words: message.filler_words_count,
            total_words: message.total_words,
            speech_rate_wpm: message.speech_rate_wpm || 0,
            questions_answered: message.questions_answered,
          });
          break;
        case 'ended':
          setStatus('ended');
          stopCamera();
          setTimeout(() => router.push(message.interview_id ? `/feedback/${message.interview_id}` : '/dashboard'), 2000);
          break;
      }
    };

    websocket.onerror = () => {
      stopCamera();
      router.push('/dashboard');
    };

    websocket.onclose = stopCamera;

    setWs(websocket);
  };

  const sendAnswer = () => {
    if (answer.trim() && ws) {
      ws.send(JSON.stringify({ type: 'text', data: answer.trim() }));
      setAnswer('');
    }
  };

  const endInterview = () => {
    if (ws && confirm('End interview?')) {
      ws.send(JSON.stringify({ type: 'end' }));
      stopCamera();
    }
  };

  const formatTime = (s: number) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`;

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">Live Interview</h1>
            <p className="text-sm text-gray-400">Session: {sessionId.slice(0,8)}...</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-2xl font-mono font-bold">{formatTime(timeRemaining)}</div>
              <div className="text-xs text-gray-400">Time Remaining</div>
            </div>
            <div className={`w-3 h-3 rounded-full ${status==='active'?'bg-green-500 animate-pulse':'bg-gray-500'}`}/>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {status==='connecting' && <div className="text-center py-20"><div className="text-xl">Connecting...</div></div>}
        {status==='ready' && <div className="text-center py-20"><div className="text-2xl font-bold mb-4">🎤 Ready!</div></div>}
        {status==='ended' && <div className="text-center py-20"><div className="text-3xl font-bold mb-4">✅ Complete!</div></div>}
        
        {status==='active' && (
          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-6">
              <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
                <video ref={videoRef} autoPlay playsInline muted className="w-full h-64 object-cover" style={{transform:'scaleX(-1)'}}/>
                <div className="p-3 bg-gray-800/50 flex justify-between text-xs">
                  <span>📹 Recording</span>
                  <span className={cameraActive?'text-green-400':'text-red-400'}>{cameraActive?'● Active':'● Off'}</span>
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div className="flex justify-between mb-4 text-sm text-gray-400">
                  <span>Q {questionIndex}/{totalQuestions}</span>
                  <div className="h-2 w-32 bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{width:`${(questionIndex/totalQuestions)*100}%`}}/>
                  </div>
                </div>
                <div className="text-xl font-medium">{currentQuestion}</div>
              </div>

              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <textarea value={answer} onChange={e=>setAnswer(e.target.value)} onKeyDown={e=>e.key==='Enter'&&e.ctrlKey&&sendAnswer()} placeholder="Type answer (Ctrl+Enter)" className="w-full h-32 bg-gray-900 border border-gray-700 rounded-lg p-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 resize-none"/>
                <div className="flex justify-between mt-4">
                  <span className="text-sm text-gray-500">{answer.split(' ').filter(Boolean).length} words</span>
                  <div className="flex gap-3">
                    <button onClick={endInterview} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm">End</button>
                    <button onClick={sendAnswer} disabled={!answer.trim()} className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 rounded-lg">Submit →</button>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Metrics</h3>
              <div className="space-y-3">
                <div><div className="text-2xl font-bold text-blue-400">{metrics.questions_answered}</div><div className="text-xs text-gray-500">Questions</div></div>
                <div><div className="text-2xl font-bold text-green-400">{metrics.total_words}</div><div className="text-xs text-gray-500">Words</div></div>
                <div><div className="text-2xl font-bold text-yellow-400">{metrics.filler_words}</div><div className="text-xs text-gray-500">Fillers</div></div>
                <div><div className="text-2xl font-bold text-purple-400">{metrics.speech_rate_wpm}</div><div className="text-xs text-gray-500">WPM</div></div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}