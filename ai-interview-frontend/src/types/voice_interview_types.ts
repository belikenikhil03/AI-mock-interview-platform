// ai-interview-frontend/src/types/voice-interview.ts

export interface TimelineEvent {
  timestamp: number;
  type: 'filler_word' | 'low_eye_contact' | 'fidgeting' | 'long_pause' | 'question_asked';
  data: {
    word?: string;
    question?: string;
    index?: number;
    score?: number;
    intensity?: number;
    duration?: number;
  };
  severity: 'info' | 'warning' | 'critical';
}

export interface GroupedEvents {
  start_time: number;
  end_time: number;
  count: number;
  events: TimelineEvent[];
}

export interface VideoData {
  url: string | null;
  duration_seconds: number;
  total_events: number;
}

export interface FeedbackWithTimeline {
  feedback: {
    id: number;
    interview_id: number;
    overall_score: number;
    content_score: number;
    communication_score: number;
    confidence_score: number;
    what_went_right: Array<{ metric: string; message: string }>;
    what_went_wrong: Array<{ metric: string; message: string }>;
    strengths: string[];
    weaknesses: string[];
    detailed_feedback: string;
    improvement_suggestions: string[];
  };
  video: VideoData;
  timeline: GroupedEvents[];
}

export interface WebSocketMessage {
  type: 'ready' | 'question' | 'ai_audio' | 'ai_done_speaking' | 'ended' | 'error';
  session_id?: string;
  job_role?: string;
  text?: string;
  index?: number;
  audio?: string;
  interview_id?: number;
  message?: string;
}
