// ai-interview-frontend/src/config/env.ts

export const config = {
  apiUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  wsUrl: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  environment: process.env.NODE_ENV || 'development',
  
  // Feature flags
  features: {
    voiceInterview: true,
    videoRecording: true,
    speechRecognition: true
  },
  
  // Interview settings
  interview: {
    maxDuration: 480, // 8 minutes in seconds
    silenceThreshold: 2500, // 2.5 seconds
    videoBitrate: 2500000, // 2.5 Mbps
    audioSampleRate: 24000 // 24kHz for Azure
  }
};
