// SIMPLIFIED: ai-interview-frontend/src/components/VideoTimeline.tsx
// Works with SAS URLs (no auth needed)
'use client';

import { useRef, useState } from 'react';

interface TimelineEvent {
  timestamp: number;
  type: string;
  data: any;
  severity: string;
}

interface VideoTimelineProps {
  videoUrl: string;
  duration: number;
  events: Array<{
    start_time: number;
    end_time: number;
    count: number;
    events: TimelineEvent[];
  }>;
}

export default function VideoTimeline({ videoUrl, duration, events }: VideoTimelineProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const jumpToTimestamp = (timestamp: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.play();
      setPlaying(true);
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (playing) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setPlaying(!playing);
    }
  };

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'filler_word': return '!';
      case 'low_eye_contact': return '⚠';
      case 'fidgeting': return '⚠';
      case 'long_pause': return '⏸';
      case 'question_asked': return '●';
      default: return '•';
    }
  };

  const getEventColor = (severity: string) => {
    switch (severity) {
      case 'warning': return 'text-yellow-400 bg-yellow-900/20';
      case 'critical': return 'text-red-400 bg-red-900/20';
      default: return 'text-blue-400 bg-blue-900/20';
    }
  };

  if (!videoUrl) {
    return (
      <div className="bg-gray-800 rounded-xl p-8 text-center border border-gray-700">
        <div className="text-6xl mb-4">📹</div>
        <div className="text-xl font-bold mb-2">No Video Available</div>
        <div className="text-gray-400">Video was not recorded for this interview.</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-xl overflow-hidden border border-gray-700">
      {/* Video Player */}
      <div className="relative bg-black">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full"
          onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onError={(e) => {
            console.error('Video error:', e);
            setError('Failed to load video');
          }}
          style={{ transform: 'scaleX(-1)' }}
          controls={false}
          crossOrigin="anonymous"
        />
        
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-center">
              <div className="text-6xl mb-4">⚠️</div>
              <div className="text-xl font-bold mb-2">Video Load Error</div>
              <div className="text-gray-400">{error}</div>
              <div className="text-sm text-gray-500 mt-2">
                The video may have expired or been deleted.
              </div>
            </div>
          </div>
        )}
        
        {/* Play/Pause Overlay */}
        {!error && (
          <button
            onClick={togglePlay}
            className="absolute inset-0 flex items-center justify-center bg-black/20 hover:bg-black/40 transition-colors group"
          >
            <div className="w-20 h-20 bg-white/90 rounded-full flex items-center justify-center text-gray-900 text-3xl group-hover:scale-110 transition-transform">
              {playing ? '⏸' : '▶'}
            </div>
          </button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="p-4 bg-gray-900">
        <div className="flex items-center gap-3 mb-2">
          <button 
            onClick={togglePlay} 
            className="text-2xl hover:text-blue-400 transition-colors"
            disabled={!!error}
          >
            {playing ? '⏸' : '▶'}
          </button>
          <div className="text-sm text-gray-400 font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
          <div 
            className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden cursor-pointer"
            onClick={(e) => {
              if (error) return;
              const rect = e.currentTarget.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const percent = x / rect.width;
              const time = percent * duration;
              jumpToTimestamp(time);
            }}
          >
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${(currentTime / duration) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Timeline Events */}
      <div className="p-4 border-t border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 mb-3">📍 Timeline Events</h3>
        <div className="max-h-96 overflow-y-auto space-y-2">
          {events.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No events recorded
            </div>
          ) : (
            events.map((group, idx) => (
              <div key={idx} className="bg-gray-900 rounded-lg p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-gray-500">
                    {formatTime(group.start_time)} - {formatTime(group.end_time)}
                  </span>
                  <span className="text-xs bg-gray-800 px-2 py-1 rounded">
                    {group.count} events
                  </span>
                </div>

                <div className="space-y-1">
                  {group.events.map((event, eventIdx) => (
                    <button
                      key={eventIdx}
                      onClick={() => jumpToTimestamp(event.timestamp)}
                      disabled={!!error}
                      className={`w-full text-left px-3 py-2 rounded text-xs hover:bg-gray-800 transition-colors flex items-center gap-2 ${getEventColor(event.severity)} disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                      <span className="font-bold">[{getEventIcon(event.type)}]</span>
                      <span className="flex-1">
                        {formatTime(event.timestamp)} - {event.type.replace('_', ' ')}
                        {event.data.word && `: "${event.data.word}"`}
                      </span>
                      <span className="text-gray-500">→</span>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}