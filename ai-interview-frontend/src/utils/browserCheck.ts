// ai-interview-frontend/src/utils/browserCheck.ts

export function checkBrowserSupport() {
  const issues: string[] = [];
  
  // Check Speech Recognition
  const SpeechRecognition = 
    (window as any).SpeechRecognition || 
    (window as any).webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    issues.push('Speech recognition not supported. Use Chrome or Edge.');
  }
  
  // Check Media Devices
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    issues.push('Camera/microphone access not supported.');
  }
  
  // Check Audio Context
  const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
  if (!AudioContext) {
    issues.push('Audio playback not supported.');
  }
  
  // Check MediaRecorder
  if (!window.MediaRecorder) {
    issues.push('Video recording not supported.');
  }
  
  return {
    supported: issues.length === 0,
    issues
  };
}

export function getBrowserName() {
  const userAgent = navigator.userAgent;
  
  if (userAgent.includes('Chrome') && !userAgent.includes('Edg')) {
    return 'Chrome';
  } else if (userAgent.includes('Edg')) {
    return 'Edge';
  } else if (userAgent.includes('Firefox')) {
    return 'Firefox';
  } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
    return 'Safari';
  }
  
  return 'Unknown';
}
