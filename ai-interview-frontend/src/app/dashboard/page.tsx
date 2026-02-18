// src/app/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/store';

export default function DashboardPage() {
  const router = useRouter();
  const { user, setUser, logout } = useAuthStore();
  const [resumes, setResumes] = useState<any[]>([]);
  const [interviews, setInterviews] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [userData, resumesData, interviewsData] = await Promise.all([
        api.getMe(),
        api.getResumes(),
        api.getInterviews(),
      ]);
      setUser(userData);
      setResumes(resumesData);
      setInterviews(interviewsData);
    } catch (err) {
      console.error(err);
      router.push('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await api.uploadResume(file);
      await loadData();
      alert('Resume uploaded successfully!');
    } catch (err: any) {
      alert(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleStartInterview = async (resumeId?: number) => {
    try {
      const session = await api.createInterview(resumeId);
      router.push(`/interview/${session.session_id}`);
    } catch (err: any) {
      alert(err.message || 'Failed to create interview');
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600">{user?.full_name}</span>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Quick Start */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-8 text-white mb-8">
          <h2 className="text-3xl font-bold mb-2">Ready to practice?</h2>
          <p className="text-blue-100 mb-6">
            Start a new mock interview session with AI-powered feedback
          </p>
          <button
            onClick={() => handleStartInterview()}
            className="bg-white text-blue-600 px-6 py-3 rounded-lg font-medium hover:bg-blue-50"
          >
            🎤 Start Interview Now
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Resumes Section */}
          <div>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">My Resumes</h2>
              <label className="cursor-pointer">
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={uploading}
                />
                <span className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
                  {uploading ? 'Uploading...' : '+ Upload Resume'}
                </span>
              </label>
            </div>

            <div className="space-y-3">
              {resumes.length === 0 ? (
                <div className="bg-white rounded-lg p-6 text-center text-gray-500">
                  No resumes uploaded yet
                </div>
              ) : (
                resumes.map((resume) => (
                  <div
                    key={resume.id}
                    className="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900">{resume.filename}</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          {resume.job_role || 'No role detected'}
                        </p>
                        {resume.skills && resume.skills.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {resume.skills.slice(0, 5).map((skill: string, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded"
                              >
                                {skill}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleStartInterview(resume.id)}
                        className="ml-4 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                      >
                        Interview
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Interview History */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Interviews</h2>
            <div className="space-y-3">
              {interviews.length === 0 ? (
                <div className="bg-white rounded-lg p-6 text-center text-gray-500">
                  No interviews yet
                </div>
              ) : (
                interviews.slice(0, 5).map((interview) => (
                  <div
                    key={interview.id}
                    className="bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => router.push(`/feedback/${interview.id}`)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-1 text-xs rounded font-medium ${
                              interview.status === 'COMPLETED'
                                ? 'bg-green-100 text-green-700'
                                : interview.status === 'IN_PROGRESS'
                                ? 'bg-yellow-100 text-yellow-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {interview.status}
                          </span>
                          <span className="text-sm text-gray-600">
                            {interview.job_role || 'General Interview'}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          {new Date(interview.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      {interview.status === 'COMPLETED' && (
                        <span className="text-blue-600 text-sm font-medium">
                          View Feedback →
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
