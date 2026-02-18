// src/hooks/useMediaPipe.ts
import { useEffect, useRef, useState } from 'react';

interface MediaPipeMetrics {
  eyeContact: number;      // 0-1 (1 = perfect eye contact)
  movement: number;        // 0-1 (1 = large movement)
  fidgeting: number;       // count of sudden movements
  postureScore: number;    // 0-1 (1 = perfect posture)
}

export function useMediaPipe(videoElement: HTMLVideoElement | null, enabled: boolean) {
  const [metrics, setMetrics] = useState<MediaPipeMetrics>({
    eyeContact: 0,
    movement: 0,
    fidgeting: 0,
    postureScore: 0,
  });
  
  const previousLandmarksRef = useRef<any>(null);
  const movementHistoryRef = useRef<number[]>([]);
  const fidgetCountRef = useRef(0);

  useEffect(() => {
    if (!videoElement || !enabled) return;

    let animationId: number;
    let faceMesh: any = null;

    const loadMediaPipe = async () => {
      // Dynamically import MediaPipe (loaded from CDN in production)
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js';
      script.async = true;
      
      script.onload = () => {
        // @ts-ignore - MediaPipe loaded globally
        if (window.FaceMesh) {
          // @ts-ignore
          faceMesh = new window.FaceMesh({
            locateFile: (file: string) => 
              `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
          });

          faceMesh.setOptions({
            maxNumFaces: 1,
            refineLandmarks: false,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
          });

          faceMesh.onResults(handleResults);
          processFrame();
        }
      };

      document.head.appendChild(script);
    };

    const handleResults = (results: any) => {
      if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
        return;
      }

      const landmarks = results.multiFaceLandmarks[0];

      // Calculate metrics
      const eyeContact = calculateEyeContact(landmarks);
      const movement = calculateMovement(landmarks, previousLandmarksRef.current);
      const posture = calculatePosture(landmarks);

      // Track movement for fidgeting detection
      movementHistoryRef.current.push(movement);
      if (movementHistoryRef.current.length > 30) {
        movementHistoryRef.current.shift(); // Keep last 30 frames
      }

      // Detect fidgeting (sudden spike in movement)
      if (movement > 0.3 && movementHistoryRef.current.length > 5) {
        const avgPrevious = 
          movementHistoryRef.current.slice(-6, -1).reduce((a, b) => a + b, 0) / 5;
        if (movement > avgPrevious * 2) {
          fidgetCountRef.current += 1;
        }
      }

      setMetrics({
        eyeContact: eyeContact,
        movement: movement,
        fidgeting: fidgetCountRef.current,
        postureScore: posture
      });

      previousLandmarksRef.current = landmarks;
    };

    const processFrame = async () => {
      if (videoElement && videoElement.readyState === 4 && faceMesh) {
        await faceMesh.send({ image: videoElement });
      }
      animationId = requestAnimationFrame(processFrame);
    };

    loadMediaPipe();

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
      if (faceMesh) faceMesh.close();
    };
  }, [videoElement, enabled]);

  return metrics;
}

// Helper functions for calculating metrics

function calculateEyeContact(landmarks: any[]): number {
  // Use nose tip and eye landmarks to estimate head rotation
  const nose = landmarks[1];        // nose tip
  const leftEye = landmarks[33];    // left eye
  const rightEye = landmarks[263];  // right eye

  // Calculate horizontal deviation (yaw)
  const eyeMidX = (leftEye.x + rightEye.x) / 2;
  const yawDeviation = Math.abs(nose.x - eyeMidX);

  // Calculate vertical deviation (pitch)
  const eyeMidY = (leftEye.y + rightEye.y) / 2;
  const pitchDeviation = Math.abs(nose.y - eyeMidY - 0.05); // 0.05 = natural nose position

  // Convert to score (0-1)
  const yawScore = Math.max(0, 1 - yawDeviation * 5);
  const pitchScore = Math.max(0, 1 - pitchDeviation * 3);

  return (yawScore + pitchScore) / 2;
}

function calculateMovement(current: any[] | null, previous: any[] | null): number {
  if (!current || !previous) return 0;

  // Calculate average movement of key points
  const keyPoints = [1, 33, 263, 61, 291]; // nose, eyes, mouth corners
  let totalMovement = 0;

  for (const idx of keyPoints) {
    const dx = current[idx].x - previous[idx].x;
    const dy = current[idx].y - previous[idx].y;
    totalMovement += Math.sqrt(dx * dx + dy * dy);
  }

  return Math.min(1, totalMovement / keyPoints.length * 20);
}

function calculatePosture(landmarks: any[]): number {
  // Use eye landmarks to detect head tilt
  const leftEye = landmarks[33];
  const rightEye = landmarks[263];

  const yDiff = Math.abs(leftEye.y - rightEye.y);
  
  // Good posture: eyes level (yDiff < 0.02)
  return Math.max(0, 1 - yDiff * 30);
}
