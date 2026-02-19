// REPLACE: ai-interview-frontend/src/app/feedback/[interviewId]/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { api } from '@/lib/api';
import VideoTimeline from '@/components/VideoTimeline';

export default function FeedbackPage() {
  const router = useRouter();
  const params = useParams();
  const interviewId = parseInt(params.interviewId as string);

  const [feedbackData, setFeedbackData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [activeTab, setActiveTab] = useState<'scores' | 'video'>('scores');

  useEffect(() => {
    loadFeedback();
  }, []);

  const loadFeedback = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(
        `http://localhost:8000/api/feedback/${interviewId}/with-timeline`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setFeedbackData(data);
      } else {
        setFeedbackData(null);
      }
    } catch (err) {
      console.error('Error loading feedback:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateFeedback = async () => {
    setGenerating(true);
    try {
      await api.generateFeedback(interviewId);
      await loadFeedback();
    } catch (err: any) {
      alert(err.message || 'Failed to generate feedback');
    } finally {
      setGenerating(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-500';
    if (score >= 60) return 'text-yellow-500';
    return 'text-red-500';
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading feedback...</div>
      </div>
    );
  }

  if (!feedbackData || !feedbackData.feedback) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold mb-2">Generate Feedback Report</h2>
          <p className="text-gray-600 mb-6">
            Your interview is complete. Click below to generate your detailed feedback report.
          </p>
          <button
            onClick={generateFeedback}
            disabled={generating}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
          >
            {generating ? 'Generating Report...' : '✨ Generate Feedback'}
          </button>
        </div>
      </div>
    );
  }

  const { feedback, video, timeline } = feedbackData;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Interview Feedback</h1>
          <button
            onClick={() => router.push('/dashboard')}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            ← Back to Dashboard
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setActiveTab('scores')}
            className={`px-6 py-3 rounded-lg font-medium ${
              activeTab === 'scores'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            📊 Scores & Feedback
          </button>
          <button
            onClick={() => setActiveTab('video')}
            className={`px-6 py-3 rounded-lg font-medium ${
              activeTab === 'video'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            🎥 Video Review
          </button>
        </div>

        {/* Scores Tab */}
        {activeTab === 'scores' && (
          <>
            {/* Overall Score */}
            <div className="bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl p-8 text-white mb-8">
              <div className="text-center">
                <div className="text-6xl font-bold mb-2">{feedback.overall_score}</div>
                <div className="text-blue-100 text-lg">Overall Score</div>
              </div>

              <div className="grid grid-cols-3 gap-4 mt-8">
                <div className="bg-white/10 rounded-lg p-4 text-center backdrop-blur">
                  <div className="text-3xl font-bold">{feedback.content_score}</div>
                  <div className="text-sm text-blue-100 mt-1">Content</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center backdrop-blur">
                  <div className="text-3xl font-bold">{feedback.communication_score}</div>
                  <div className="text-sm text-blue-100 mt-1">Communication</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4 text-center backdrop-blur">
                  <div className="text-3xl font-bold">{feedback.confidence_score}</div>
                  <div className="text-sm text-blue-100 mt-1">Confidence</div>
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              {/* What Went Right */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-2xl">✅</span> What Went Right
                </h2>
                {feedback.what_went_right && feedback.what_went_right.length > 0 ? (
                  <ul className="space-y-3">
                    {feedback.what_went_right.map((item: any, i: number) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="text-green-500 text-xl">•</span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{item.metric}</div>
                          <div className="text-sm text-gray-600">{item.message}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">
                    {feedback.strengths?.map((s: string, i: number) => (
                      <div key={i} className="mb-2">• {s}</div>
                    ))}
                  </p>
                )}
              </div>

              {/* What Needs Improvement */}
              <div className="bg-white rounded-xl shadow-sm p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span className="text-2xl">💡</span> Areas for Improvement
                </h2>
                {feedback.what_went_wrong && feedback.what_went_wrong.length > 0 ? (
                  <ul className="space-y-3">
                    {feedback.what_went_wrong.map((item: any, i: number) => (
                      <li key={i} className="flex items-start gap-3">
                        <span className="text-yellow-500 text-xl">•</span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{item.metric}</div>
                          <div className="text-sm text-gray-600">{item.message}</div>
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-gray-500">
                    {feedback.weaknesses?.map((w: string, i: number) => (
                      <div key={i} className="mb-2">• {w}</div>
                    ))}
                  </p>
                )}
              </div>
            </div>

            {/* Detailed Feedback */}
            {feedback.detailed_feedback && (
              <div className="bg-white rounded-xl shadow-sm p-6 mt-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4">📝 Detailed Feedback</h2>
                <p className="text-gray-700 leading-relaxed">{feedback.detailed_feedback}</p>
              </div>
            )}

            {/* Improvement Suggestions */}
            {feedback.improvement_suggestions && feedback.improvement_suggestions.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm p-6 mt-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4">🎯 Action Items</h2>
                <ul className="space-y-3">
                  {feedback.improvement_suggestions.map((suggestion: string, i: number) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium">
                        {i + 1}
                      </span>
                      <p className="text-gray-700 flex-1">{suggestion}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {/* Video Review Tab */}
        {activeTab === 'video' && (
          <div>
            {video.url ? (
              <>
                <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-2">🎥 Interview Recording Analysis</h2>
                  <p className="text-gray-600 mb-4">
                    Click on any event in the timeline to jump to that moment in the video.
                  </p>
                </div>

                <VideoTimeline
                  videoUrl={video.url}
                  duration={video.duration_seconds}
                  events={timeline}
                />

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-6">
                  <div className="flex items-start gap-3">
                    <span className="text-2xl">💡</span>
                    <div>
                      <div className="font-medium text-blue-900">How to Use Video Review</div>
                      <ul className="text-sm text-blue-800 mt-2 space-y-1">
                        <li>• Yellow markers = Minor issues (filler words, brief pauses)</li>
                        <li>• Red markers = Major issues (poor eye contact, excessive fidgeting)</li>
                        <li>• Blue markers = Informational (question timestamps)</li>
                        <li>• Click any marker to jump to that moment</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="bg-white rounded-xl shadow-sm p-12 text-center">
                <div className="text-6xl mb-4">📹</div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">Video Not Available</h3>
                <p className="text-gray-600">
                  Video recording was not uploaded for this interview.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={() => router.push('/dashboard')}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            🎤 Practice Again
          </button>
        </div>
      </main>
    </div>
  );
}