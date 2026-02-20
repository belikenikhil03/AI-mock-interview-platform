// ai-interview-frontend/src/app/interview/[sessionId]/layout.tsx
import { ErrorBoundary } from '@/components/ErrorBoundary';

export default function InterviewLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}
