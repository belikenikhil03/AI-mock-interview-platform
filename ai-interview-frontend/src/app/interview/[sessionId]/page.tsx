// COMPLETE: ai-interview-frontend/src/app/interview/[sessionId]/page.tsx
'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useVoiceInterview } from '@/hooks/useVoiceInterview';
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition';
import { useVideoRecorder } from '@/hooks/useVideoRecorder';
import { MicrophoneRecorder } from '@/utils/audioUtils';
import { UploadService } from '@/services/uploadService';

export default function VoiceInterviewPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const videoRef = useRef<HTMLVideoElement>(null);
  const micRecorderRef = useRef<MicrophoneRecorder | null>(null);
  const transcriptBufferRef = useRef<string>('');
  const silenceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const [elapsedTime, setElapsedTime] = useState(0);
  const [cameraActive, setCameraActive] = useState(false);
  const [micLevel, setMicLevel] = useState(0);
  const [candidateSpeaking, setCandidateSpeaking] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showUpload, setShowUpload] = useState(false);

  // Interview state management
  const [interviewState, setInterviewState] = useState({
    status: 'connecting' as 'connecting' | 'ready' | 'active' | 'ended',
    currentQuestion: '',
    questionIndex: 0,
    aiSpeaking: false,
    interviewId: null as number | null
  });

  // Voice interview hook
  const voiceInterview = useVoiceInterview({
    sessionId,
    onStateChange: (state) => {
      setInterviewState(state);
    }
  });

  // Video recorder hook
  const videoRecorder = useVideoRecorder();

  // Speech recognition
  const handleTranscript = (text: string, isFinal: boolean) => {
    if (isFinal) {
      transcriptBufferRef.current += text + ' ';
      
      // Detect filler words
      const fillerWords = ['um', 'uh', 'like', 'you know', 'basically', 'literally'];
      const words = text.toLowerCase().split(' ');
      words.forEach(word => {
        const clean = word.replace(/[.,!?]/g, '');
        if (fillerWords.includes(clean)) {
          videoRecorder.logEvent({
            type: 'filler_word',
            data: { word: clean },
            severity: 'warning'
          });
        }
      });

      // Reset silence timer
      if (silenceTimerRef.current) {
        clearTimeout(silenceTimerRef.current);
      }

      // 2.5s silence = send response
      silenceTimerRef.current = setTimeout(() => {
        if (transcriptBufferRef.current.trim()) {
          console.log('📤 Sending:', transcriptBufferRef.current);
          voiceInterview.sendTranscript(transcriptBufferRef.current.trim());
          transcriptBufferRef.current = '';
          setCandidateSpeaking(false);
        }
      }, 2500);
    }
  };

  const handleSpeakingChange = (speaking: boolean) => {
    setCandidateSpeaking(speaking);
  };

  const speechRecognition = useSpeechRecognition({
    onTranscript: handleTranscript,
    onSpeakingChange: handleSpeakingChange,
    enabled: interviewState.status === 'active'
  });

  // Timer
  useEffect(() => {
    if (interviewState.status === 'active') {
      const timer = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [interviewState.status]);

  // Initialize everything
  useEffect(() => {
    const init = async () => {
      await initCamera();
      voiceInterview.connect();
    };

    setTimeout(init, 500);

    return () => {
      cleanup();
    };
  }, []);

  // Handle interview end
  useEffect(() => {
    if (interviewState.status === 'ended' && interviewState.interviewId) {
      handleInterviewEnd();
    }
  }, [interviewState.status, interviewState.interviewId]);

  const initCamera = async () => {
    const video = document.getElementById('interview-video') as HTMLVideoElement;
    if (!video) {
      setTimeout(initCamera, 300);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
        audio: true
      });

      video.srcObject = stream;
      video.muted = true;
      await video.play();

      setCameraActive(true);
      console.log('✅ Camera active');

      // Setup mic visualizer
      micRecorderRef.current = new MicrophoneRecorder();
      await micRecorderRef.current.initialize(stream);
      micRecorderRef.current.onLevelChange = (level) => setMicLevel(level);

      // Start recording
      await videoRecorder.startRecording(stream);

    } catch (err: any) {
      console.error('Camera error:', err);
      alert(`Camera failed: ${err.message}`);
    }
  };

  const handleInterviewEnd = async () => {
    setShowUpload(true);

    try {
      // Stop recording
      const videoBlob = await videoRecorder.stopRecording();
      const timeline = videoRecorder.getTimeline();
      const duration = videoRecorder.getDuration();

      // Upload with progress
      await UploadService.uploadWithProgress(
        interviewState.interviewId!,
        videoBlob,
        timeline,
        duration,
        (percent) => setUploadProgress(percent)
      );

      console.log('✅ Upload complete');
      
      setTimeout(() => {
        router.push(`/feedback/${interviewState.interviewId}`);
      }, 1000);

    } catch (err) {
      console.error('Upload error:', err);
      setTimeout(() => {
        router.push(`/feedback/${interviewState.interviewId}`);
      }, 2000);
    }
  };

  const cleanup = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }
    if (micRecorderRef.current) {
      micRecorderRef.current.stop();
    }
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => track.stop());
    }
    voiceInterview.cleanup();
    speechRecognition.stop();
  };

  const endInterview = () => {
    if (confirm('End interview?')) {
      voiceInterview.endInterview();
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold">🎤 Voice Interview</h1>
            <p className="text-sm text-gray-400">Session: {sessionId.slice(0, 8)}...</p>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-2xl font-mono font-bold">{formatTime(elapsedTime)}</div>
              <div className="text-xs text-gray-400">Elapsed</div>
            </div>
            <div className={`w-3 h-3 rounded-full ${interviewState.status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'}`} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Connecting */}
        {interviewState.status === 'connecting' && (
          <div className="text-center py-20">
            <div className="text-xl mb-4">Connecting to AI interviewer...</div>
            <div className="animate-spin w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
          </div>
        )}

        {/* Ready */}
        {interviewState.status === 'ready' && (
          <div className="text-center py-20">
            <div className="text-2xl font-bold mb-4">🎤 Interview Ready!</div>
            <div className="text-gray-400">AI is introducing the interview...</div>
          </div>
        )}

        {/* Upload Progress */}
        {showUpload && (
          <div className="text-center py-20">
            <div className="text-3xl font-bold mb-4">✅ Interview Complete!</div>
            <div className="text-gray-400 mb-6">Uploading your recording...</div>
            <div className="max-w-md mx-auto">
              <div className="h-4 bg-gray-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <div className="text-sm text-gray-500 mt-2">{Math.round(uploadProgress)}%</div>
            </div>
          </div>
        )}

        {/* Active Interview */}
        {interviewState.status === 'active' && !showUpload && (
          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2 space-y-6">
              {/* AI Avatar */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 text-center">
                <div className={`w-32 h-32 mx-auto rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-5xl mb-4 transition-all ${interviewState.aiSpeaking ? 'ring-4 ring-blue-400 animate-pulse scale-110' : ''}`}>
                  👨‍💼
                </div>
                <div className="text-sm text-gray-400">
                  {interviewState.aiSpeaking ? (
                    <span className="flex items-center gap-2 justify-center">
                      🎤 <span className="animate-pulse">AI Speaking...</span>
                    </span>
                  ) : (
                    '👂 AI Listening...'
                  )}
                </div>
                {interviewState.aiSpeaking && (
                  <div className="flex items-center gap-1 mt-3 justify-center">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div
                        key={i}
                        className="w-1 bg-blue-500 rounded-full animate-pulse"
                        style={{
                          height: `${Math.random() * 20 + 10}px`,
                          animationDelay: `${i * 0.1}s`
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Question */}
              <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
                <div className="text-sm text-gray-400 mb-2">Question {interviewState.questionIndex}</div>
                <div className="text-xl font-medium leading-relaxed">{interviewState.currentQuestion}</div>
              </div>

              {/* Video */}
              <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
                <video
                  id="interview-video"
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-64 object-cover"
                  style={{ transform: 'scaleX(-1)' }}
                />
                <div className="p-3 bg-gray-800/50 flex justify-between items-center text-xs">
                  <div className="flex items-center gap-3">
                    {candidateSpeaking ? (
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((i) => (
                          <div
                            key={i}
                            className="w-1 bg-green-500 rounded-full"
                            style={{
                              height: `${Math.min(micLevel / 10, 20)}px`,
                              transition: 'height 0.1s'
                            }}
                          />
                        ))}
                        <span className="ml-2 text-green-400">🎤 You're speaking...</span>
                      </div>
                    ) : (
                      <span>⏸️ Waiting for your response...</span>
                    )}
                  </div>
                  <span className={cameraActive ? 'text-green-400' : 'text-red-400'}>
                    {cameraActive ? '● Recording' : '● Off'}
                  </span>
                </div>
              </div>

              <button 
                onClick={endInterview} 
                className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 rounded-lg font-medium transition-colors"
              >
                End Interview
              </button>
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-sm font-medium text-gray-400 mb-3">💡 Tips</h3>
                <ul className="text-xs text-gray-500 space-y-2">
                  <li>• Wait for AI to finish speaking</li>
                  <li>• Speak clearly and naturally</li>
                  <li>• Pause 2.5s when done</li>
                  <li>• Look at camera</li>
                  <li>• Avoid filler words</li>
                  <li>• Use STAR method</li>
                </ul>
              </div>

              <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                <h3 className="text-sm font-medium text-gray-400 mb-3">📊 Stats</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Events Logged</span>
                    <span className="text-blue-400 font-bold">{videoRecorder.getTimeline().length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Recording</span>
                    <span className="text-green-400">● Active</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Speech Recognition</span>
                    <span className={speechRecognition.isListening ? 'text-green-400' : 'text-gray-500'}>
                      {speechRecognition.isListening ? '● On' : '○ Off'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}