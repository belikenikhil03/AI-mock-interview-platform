// src/lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiClient {
  private token: string | null = null;

  constructor() {
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async register(email: string, full_name: string, password: string) {
    return this.request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, full_name, password }),
    });
  }

  async getMe() {
    return this.request('/api/auth/me');
  }

  // Resumes
  async uploadResume(file: File) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/api/resumes/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  async getResumes() {
    return this.request('/api/resumes/');
  }

  // Interviews
  async createInterview(resumeId?: number) {
    return this.request('/api/interviews/', {
      method: 'POST',
      body: JSON.stringify({ resume_id: resumeId, interview_type: 'job_role' }),
    });
  }

  async getInterviews() {
    return this.request('/api/interviews/');
  }

  async getInterview(sessionId: string) {
    return this.request(`/api/interviews/${sessionId}`);
  }

  // Feedback
  async generateFeedback(interviewId: number) {
    return this.request(`/api/feedback/${interviewId}/generate`, {
      method: 'POST',
    });
  }

  async getFeedback(interviewId: number) {
    return this.request(`/api/feedback/${interviewId}`);
  }
}

export const api = new ApiClient();
