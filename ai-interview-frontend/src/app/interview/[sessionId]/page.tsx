// src/app/interview/[sessionId]/page.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function InterviewPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [ws, setWs] = useState<WebSocket | null>(null);
  const [status, setStatus] = useState<'connecting' | 'ready' | 'active' | 'ended'>('connecting');
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(8);
  const [answer, setAnswer] = useState('');
  const [metrics, setMetrics] = useState({
    filler_words: 0,
    total_words: 0,
    questions_answered: 0,
  });
  const [timeRemaining, setTimeRemaining] = useState(480); // 8 minutes
  const [interviewId, setInterviewId] = useState<number | null>(null);

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (ws) ws.close();
    };
  }, []);

  useEffect(() => {
    if (status === 'active') {
      const timer = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 0) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [status]);

  const connectWebSocket = () => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    const wsUrl = `ws://localhost:8000/api/interviews/${sessionId}/ws?token=${token}`;
    const websocket = new WebSocket(wsUrl);

    websocket.onopen = () => {
      console.log('WebSocket connected');
      setStatus('connecting');
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleMessage(message);
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      alert('Connection failed. Please try again.');
      router.push('/dashboard');
    };

    websocket.onclose = () => {
      console.log('WebSocket closed');
    };

    setWs(websocket);
  };

  const handleMessage = (message: any) => {
    console.log('Received:', message);

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
          questions_answered: message.questions_answered,
        });
        break;

      case 'warning':
        alert(message.message);
        break;

      case 'ended':
        setStatus('ended');
        // Get interview ID from the session to view feedback
        setTimeout(() => {
          router.push('/dashboard');
        }, 3000);
        break;

      case 'error':
        alert(message.message);
        break;
    }
  };

  const sendAnswer = () => {
    if (!answer.trim() || !ws) return;

    ws.send(
      JSON.stringify({
        type: 'text',
        data: answer.trim(),
      })
    );

    setAnswer('');
  };

  const endInterview = () => {
    if (ws && confirm('Are you sure you want to end the interview?')) {
      ws.send(JSON.stringify({ type: 'end' }));
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">Live Interview</h1>
            <p className="text-sm text-gray-400">Session: {sessionId.slice(0, 8)}...</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-2xl font-mono font-bold">{formatTime(timeRemaining)}</div>
              <div className="text-xs text-gray-400">Time Remaining</div>
            </div>
            <div
              className={`w-3 h-3 rounded-full ${
                status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
              }`}
            />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Status Messages */}
        {status === 'connecting' && (
          <div className="text-center py-20">
            <div className="text-xl mb-4">Connecting to interview session...</div>
            <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
          </div>
        )}

        {status === 'ready' && (
          <div className="text-center py-20">
            <div className="text-2xl font-bold mb-4">🎤 Interview Ready!</div>
            <div className="text-gray-400 mb-6">
              You'll be asked {totalQuestions} questions. Answer each thoroughly.
            </div>
            <div className="text-sm text-gray-500">Waiting for first question...</div>
          </div>
        )}

        {status === 'ended' && (
          <div className="text-center py-20">
            <div className="text-3xl font-bold mb-4">✅ Interview Complete!</div>
            <div className="text-gray-400 mb-6">Generating your feedback report...</div>
            <div className="text-sm text-gray-500">Redirecting to dashboard...</div>
          </div>
        )}

        {/* Active Interview */}
        {status === 'active' && (
          <div className="grid md:grid-cols-3 gap-6">
            {/* Main Interview Area */}
            <div className="md:col-span-2 space-y-6">
              {/* Current Question */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-gray-400">
                    Question {questionIndex} of {totalQuestions}
                  </span>
                  <div className="h-2 w-32 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 transition-all"
                      style={{ width: `${(questionIndex / totalQuestions) * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-xl font-medium leading-relaxed">{currentQuestion}</div>
              </div>

              {/* Answer Input */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <label className="block text-sm text-gray-400 mb-2">Your Answer:</label>
                <textarea
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.ctrlKey) {
                      sendAnswer();
                    }
                  }}
                  placeholder="Type your answer here... (Ctrl+Enter to submit)"
                  className="w-full h-32 bg-gray-900 border border-gray-700 rounded-lg p-4 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
                <div className="flex justify-between items-center mt-4">
                  <span className="text-sm text-gray-500">
                    {answer.split(' ').filter(Boolean).length} words
                  </span>
                  <div className="flex gap-3">
                    <button
                      onClick={endInterview}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium"
                    >
                      End Interview
                    </button>
                    <button
                      onClick={sendAnswer}
                      disabled={!answer.trim()}
                      className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-lg font-medium"
                    >
                      Submit Answer →
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Metrics Sidebar */}
            <div className="space-y-4">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-sm font-medium text-gray-400 mb-3">Live Metrics</h3>
                <div className="space-y-3">
                  <div>
                    <div className="text-2xl font-bold text-blue-400">
                      {metrics.questions_answered}
                    </div>
                    <div className="text-xs text-gray-500">Questions Answered</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-green-400">{metrics.total_words}</div>
                    <div className="text-xs text-gray-500">Total Words</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-yellow-400">
                      {metrics.filler_words}
                    </div>
                    <div className="text-xs text-gray-500">Filler Words (um, uh, like)</div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-sm font-medium text-gray-400 mb-2">💡 Tips</h3>
                <ul className="text-xs text-gray-500 space-y-2">
                  <li>• Use the STAR method for behavioral questions</li>
                  <li>• Avoid filler words (um, uh, like)</li>
                  <li>• Provide specific examples</li>
                  <li>• Take brief pauses to think</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
