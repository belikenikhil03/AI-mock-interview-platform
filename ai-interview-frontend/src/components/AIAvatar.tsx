// ai-interview-frontend/src/components/AIAvatar.tsx
'use client';

import { useEffect, useRef } from 'react';

interface AIAvatarProps {
  speaking: boolean;
  name?: string;
}

export default function AIAvatar({ speaking, name = "AI Interviewer" }: AIAvatarProps) {
  const avatarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load Lottie dynamically
    const loadLottie = async () => {
      // Using a simple animated avatar JSON (you can replace with custom Lottie file)
      const lottieScript = document.createElement('script');
      lottieScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js';
      lottieScript.onload = () => {
        if (avatarRef.current && (window as any).lottie) {
          (window as any).lottie.loadAnimation({
            container: avatarRef.current,
            renderer: 'svg',
            loop: speaking,
            autoplay: speaking,
            path: 'https://lottie.host/4f3f5e3e-5c5d-4b8e-9c3e-2e8f5e3e5c5d/animation.json' // Professional avatar
          });
        }
      };
      document.head.appendChild(lottieScript);
    };

    loadLottie();

    return () => {
      const scripts = document.querySelectorAll('script[src*="lottie"]');
      scripts.forEach(script => script.remove());
    };
  }, []);

  return (
    <div className="flex flex-col items-center">
      <div 
        className={`relative w-40 h-40 rounded-full overflow-hidden transition-all ${
          speaking ? 'ring-4 ring-blue-400 ring-offset-4 ring-offset-gray-900' : ''
        }`}
      >
        {/* Fallback: Simple gradient avatar if Lottie fails */}
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <div className="text-6xl">👨‍💼</div>
        </div>
        
        {/* Lottie container (overlays fallback) */}
        <div ref={avatarRef} className="absolute inset-0" />
      </div>

      <div className="mt-4 text-center">
        <div className="font-medium text-white">{name}</div>
        <div className="text-sm text-gray-400 mt-1">
          {speaking ? (
            <span className="flex items-center gap-2 justify-center">
              🎤 <span className="animate-pulse">Speaking...</span>
            </span>
          ) : (
            '👂 Listening'
          )}
        </div>
      </div>

      {/* Speaking indicator waveform */}
      {speaking && (
        <div className="flex items-center gap-1 mt-3">
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
  );
}
