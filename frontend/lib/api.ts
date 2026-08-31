const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  email: string;
  name: string;
  target_role: string;
  domain: string;
  goal_skill: string;
  confidence: Record<string, number>;
  known_skills?: string[];
}

export interface QuizQuestion {
  id: string;
  skill_id: string;
  difficulty: 'easy' | 'medium' | 'hard';
  question: string;
  options: Record<string, string>;
}

export interface QuizStartResponse {
  session_id: string;
  question_number: number;
  total_questions: number;
  question: QuizQuestion;
}

export interface QuizSubmitResponse {
  completed: boolean;
  is_correct: boolean;
  correct_answer?: string;
  explanation?: string;
  question_number?: number;
  total_questions?: number;
  next_question?: QuizQuestion;
  confidence?: Record<string, number>;
  total_answered?: number;
  correct_count?: number;
}

export interface Course {
  course_id: string;
  title: string;
  provider: string;
  url: string;
  domain: string;
  skills_taught: string;
  level: string;
}

export interface Milestone {
  order: number;
  skill_id: string;
  skill_name: string;
  domain?: string;
  courses: Course[];
  status: 'not_started' | 'in_progress' | 'completed' | 'skipped';
}

export interface RoadmapResponse {
  goal_skill: string;
  total_milestones: number;
  narration?: string;
  milestones: Milestone[];
}

export interface CompareResponse {
  goal_a: { goal: string; path: { skill_id: string; name: string }[]; length: number };
  goal_b: { goal: string; path: { skill_id: string; name: string }[]; length: number };
  shared_skills: { skill_id: string; name: string }[];
  only_in_a: { skill_id: string; name: string }[];
  only_in_b: { skill_id: string; name: string }[];
  explanation: string;
}

export const getToken = () => (typeof window !== 'undefined' ? localStorage.getItem('nexora_token') : null);
export const setToken = (token: string) => {
  if (typeof window !== 'undefined') localStorage.setItem('nexora_token', token);
};
export const removeToken = () => {
  if (typeof window !== 'undefined') localStorage.removeItem('nexora_token');
};

const authHeaders = () => {
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export async function registerUser(data: { email: string; password: string; name: string; target_role?: string; goal_skill?: string }) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Registration failed');
  }
  return res.json();
}

export async function loginUser(data: { email: string; password: string }) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Login failed');
  }
  return res.json();
}

export async function getCurrentUser(): Promise<User | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: authHeaders(),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function startQuiz(domain = 'backend', maxQuestions = 6, learnerId = 'guest'): Promise<QuizStartResponse> {
  const res = await fetch(`${API_BASE}/quiz/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain, max_questions: maxQuestions, learner_id: learnerId }),
  });
  if (!res.ok) throw new Error('Failed to start quiz');
  return res.json();
}

export async function submitQuizAnswer(sessionId: string, questionId: string, selectedOption: string): Promise<QuizSubmitResponse> {
  const res = await fetch(`${API_BASE}/quiz/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question_id: questionId, selected_option: selectedOption }),
  });
  if (!res.ok) throw new Error('Failed to submit answer');
  return res.json();
}

export async function getRoadmap(knownSkills: string[], goalSkill: string): Promise<RoadmapResponse> {
  const res = await fetch(`${API_BASE}/roadmap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ known_skills: knownSkills, goal_skill: goalSkill, courses_per_skill: 2 }),
  });
  if (!res.ok) throw new Error('Failed to fetch roadmap');
  return res.json();
}

export async function submitFeedback(learnerId: string, skillId: string, eventType: 'quiz_score' | 'completion' | 'skip', score?: number) {
  const res = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ learner_id: learnerId, skill_id: skillId, event_type: eventType, score }),
  });
  if (!res.ok) throw new Error('Failed to submit feedback');
  return res.json();
}

export async function compareGoals(knownSkills: string[], goalA: string, goalB: string): Promise<CompareResponse> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ known_skills: knownSkills, goal_a: goalA, goal_b: goalB }),
  });
  if (!res.ok) throw new Error('Failed to compare goals');
  return res.json();
}

export async function sendCopilotMessage(message: string, learnerId?: string) {
  const res = await fetch(`${API_BASE}/api/copilot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, learner_id: learnerId }),
  });
  if (!res.ok) throw new Error('Failed to communicate with Copilot');
  return res.json();
}
