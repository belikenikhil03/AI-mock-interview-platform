// ai-interview-frontend/src/components/BrowserWarning.tsx
'use client';

import { useEffect, useState } from 'react';
import { checkBrowserSupport, getBrowserName } from '@/utils/browserCheck';

export default function BrowserWarning() {
  const [show, setShow] = useState(false);
  const [issues, setIssues] = useState<string[]>([]);

  useEffect(() => {
    const check = checkBrowserSupport();
    if (!check.supported) {
      setIssues(check.issues);
      setShow(true);
    }
  }, []);

  if (!show) return null;

  return (
    <div className="fixed top-0 left-0 right-0 bg-yellow-500 text-black px-4 py-3 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <div className="font-bold">Browser Compatibility Issues</div>
            <div className="text-sm">
              You're using {getBrowserName()}. Some features may not work:
            </div>
            <ul className="text-sm mt-1">
              {issues.map((issue, i) => (
                <li key={i}>• {issue}</li>
              ))}
            </ul>
            <div className="text-sm mt-1 font-medium">
              ✅ Recommended: Use Chrome or Edge for best experience
            </div>
          </div>
        </div>
        <button
          onClick={() => setShow(false)}
          className="px-3 py-1 bg-black text-yellow-500 rounded hover:bg-gray-800"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
