// ai-interview-frontend/src/hooks/useVideoRecorder.ts

import { useRef, useState } from 'react';

interface TimelineEvent {
  timestamp: number;
  type: string;
  data: any;
  severity: string;
}

export function useVideoRecorder() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timelineRef = useRef<TimelineEvent[]>([]);
  const startTimeRef = useRef<number>(0);
  const [isRecording, setIsRecording] = useState(false);

  const startRecording = async (stream: MediaStream) => {
    try {
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp9',
        videoBitsPerSecond: 2500000 // 2.5 Mbps for 720p
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(1000); // Chunk every second
      mediaRecorderRef.current = mediaRecorder;
      startTimeRef.current = Date.now();
      setIsRecording(true);

      console.log('✅ Recording started');
    } catch (err) {
      console.error('Recording error:', err);
      throw err;
    }
  };

  const stopRecording = (): Promise<Blob> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current) {
        resolve(new Blob([]));
        return;
      }

      mediaRecorderRef.current.onstop = () => {
        const videoBlob = new Blob(chunksRef.current, { type: 'video/webm' });
        setIsRecording(false);
        console.log(`✅ Recording stopped: ${(videoBlob.size / 1024 / 1024).toFixed(2)}MB`);
        resolve(videoBlob);
      };

      mediaRecorderRef.current.stop();
    });
  };

  const logEvent = (event: Omit<TimelineEvent, 'timestamp'>) => {
    const timestamp = (Date.now() - startTimeRef.current) / 1000;
    timelineRef.current.push({
      timestamp,
      ...event
    });
  };

  const getTimeline = () => {
    return timelineRef.current;
  };

  const getDuration = () => {
    return Math.floor((Date.now() - startTimeRef.current) / 1000);
  };

  return {
    startRecording,
    stopRecording,
    logEvent,
    getTimeline,
    getDuration,
    isRecording
  };
}
