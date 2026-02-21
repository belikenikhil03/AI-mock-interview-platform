// CRITICAL FIX: Audio player with proper queuing
// REPLACE: src/utils/audioUtils.ts

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private audioQueue: AudioBuffer[] = [];
  private isPlaying = false;

  constructor() {
    if (typeof window !== 'undefined') {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
      this.audioContext = new AudioContext();
    }
  }

  async initialize() {
    if (this.audioContext && this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
  }

  async playChunk(audioBase64: string): Promise<void> {
    if (!this.audioContext) {
      console.error('No audio context');
      return;
    }

    try {
      await this.initialize();

      // Convert and queue
      const audioData = this.base64ToArrayBuffer(audioBase64);
      const audioBuffer = await this.pcm16ToAudioBuffer(audioData, 24000, 1);
      
      this.audioQueue.push(audioBuffer);
      
      // Start playing if not already
      if (!this.isPlaying) {
        this.playNext();
      }

    } catch (err) {
      console.error('Audio error:', err);
    }
  }

  private playNext() {
    if (this.audioQueue.length === 0) {
      this.isPlaying = false;
      return;
    }

    this.isPlaying = true;
    const buffer = this.audioQueue.shift()!;

    const source = this.audioContext!.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext!.destination);

    source.onended = () => {
      this.playNext(); // Play next chunk
    };

    source.start(0);
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  private async pcm16ToAudioBuffer(
    arrayBuffer: ArrayBuffer, 
    sampleRate: number, 
    numberOfChannels: number
  ): Promise<AudioBuffer> {
    if (!this.audioContext) throw new Error('No audio context');

    const pcm16Data = new Int16Array(arrayBuffer);
    const floatData = new Float32Array(pcm16Data.length);

    for (let i = 0; i < pcm16Data.length; i++) {
      floatData[i] = pcm16Data[i] / 32768.0;
    }

    const audioBuffer = this.audioContext.createBuffer(
      numberOfChannels,
      floatData.length,
      sampleRate
    );

    audioBuffer.getChannelData(0).set(floatData);
    return audioBuffer;
  }

  stopAll() {
    this.audioQueue = [];
    this.isPlaying = false;
  }

  close() {
    this.stopAll();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

export class MicrophoneRecorder {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animationFrame: number = 0;
  
  onLevelChange?: (level: number) => void;

  async initialize(stream: MediaStream) {
    const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
    this.audioContext = new AudioContext();
    
    const source = this.audioContext.createMediaStreamSource(stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    
    source.connect(this.analyser);
    this.monitorLevel();
  }

  private monitorLevel() {
    if (!this.analyser) return;

    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    
    const update = () => {
      if (!this.analyser) return;
      
      this.analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      
      if (this.onLevelChange) {
        this.onLevelChange(average);
      }
      
      this.animationFrame = requestAnimationFrame(update);
    };
    
    update();
  }

  stop() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}