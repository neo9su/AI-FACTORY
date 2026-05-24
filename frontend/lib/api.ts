import axios, { type AxiosInstance } from 'axios';
import type { TopOpportunityItem, ProductStatsResponse } from '@/types/neurotrend';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ProjectCreate {
  name: string;
  user_requirement: string;
  goal?: string;
  tech_stack?: string;
  template?: string;
}

export interface Project {
  id: string;
  name: string;
  user_requirement: string;
  goal: string | null;
  tech_stack: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  status: string;
  priority: number;
  role: string | null;
}

export interface ProjectDetail extends Project {
  tasks: Task[];
  agent_runs_count: number;
  test_runs_count: number;
}

export interface AgentRun {
  id: string;
  agent_name: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  task_id: string | null;
}

export interface TestRun {
  id: string;
  test_type: string;
  command: string;
  status: string;
  error_log: string | null;
  created_at: string;
}

export interface Deployment {
  id: string;
  environment: string;
  preview_url: string | null;
  status: string;
  logs: string | null;
  created_at: string;
}

export interface DeliveryReport {
  id: string;
  summary: string;
  passed_tests: Record<string, unknown> | null;
  failed_tests: Record<string, unknown> | null;
  deployment_url: string | null;
  known_issues: string | null;
  final_status: string;
  created_at: string;
}

export interface ReviewIssue {
  severity: string;
  category: string;
  file: string;
  line: number | null;
  description: string;
  suggestion: string;
}

export interface ReviewReport {
  id: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  review: {
    passed: boolean;
    score: number;
    issues: ReviewIssue[];
    summary: string;
    suggestions: string[];
  };
}

export interface WorkspaceFile {
  path: string;
  size: number;
  extension: string;
}

export interface FileContent {
  path: string;
  content: string;
  size: number;
  extension: string;
  lines: number;
}

export const projectsApi = {
  create: async (data: ProjectCreate): Promise<Project> => {
    const response = await api.post<Project>('/projects', data);
    return response.data;
  },

  list: async (params?: { status?: string; search?: string; limit?: number }): Promise<Project[]> => {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.set('status', params.status);
    if (params?.search) queryParams.set('search', params.search);
    if (params?.limit) queryParams.set('limit', String(params.limit));
    const qs = queryParams.toString();
    const response = await api.get<Project[]>(`/projects${qs ? `?${qs}` : ''}`);
    return response.data;
  },

  get: async (id: string): Promise<ProjectDetail> => {
    const response = await api.get<ProjectDetail>(`/projects/${id}`);
    return response.data;
  },

  start: async (id: string): Promise<{ status: string; project_id: string; job_id: string }> => {
    const response = await api.post(`/projects/${id}/start`);
    return response.data;
  },

  getAgentRuns: async (id: string): Promise<AgentRun[]> => {
    const response = await api.get<AgentRun[]>(`/projects/${id}/agent-runs`);
    return response.data;
  },

  getTestRuns: async (id: string): Promise<TestRun[]> => {
    const response = await api.get<TestRun[]>(`/projects/${id}/test-runs`);
    return response.data;
  },

  getDeployment: async (id: string): Promise<Deployment> => {
    const response = await api.get<Deployment>(`/projects/${id}/deployment`);
    return response.data;
  },

  getDeliveryReport: async (id: string): Promise<DeliveryReport> => {
    const response = await api.get<DeliveryReport>(`/projects/${id}/delivery-report`);
    return response.data;
  },

  getReview: async (id: string): Promise<ReviewReport> => {
    const response = await api.get<ReviewReport>(`/projects/${id}/review`);
    return response.data;
  },

  getFiles: async (id: string): Promise<WorkspaceFile[]> => {
    const response = await api.get<WorkspaceFile[]>(`/projects/${id}/files`);
    return response.data;
  },

  getFileContent: async (id: string, filePath: string): Promise<FileContent> => {
    const response = await api.get<FileContent>(`/projects/${id}/files/${filePath}`);
    return response.data;
  },
};

export interface NotifyTestRequest {
  webhook_url?: string;
  sign_secret?: string;
  message?: string;
}

export interface NotifyTestResponse {
  success: boolean;
  mode: string;
  status_code: number;
  error: string | null;
  response_body: string | null;
}

export interface NotifyConfigResponse {
  webhook_configured: boolean;
  sign_secret_configured: boolean;
  app_bot_configured: boolean;
  active_mode: string;
}

export const notifyApi = {
  test: async (data: NotifyTestRequest): Promise<NotifyTestResponse> => {
    const response = await api.post<NotifyTestResponse>('/notify/test', data);
    return response.data;
  },

  getConfig: async (): Promise<NotifyConfigResponse> => {
    const response = await api.get<NotifyConfigResponse>('/notify/config');
    return response.data;
  },
};

// ─── Phase 5-A: Analytics API ────────────────────────────────────────────────

export const analyticsApi = {
  /**
   * Fire-and-forget engagement event log.
   * Uses a silent best-effort approach — ignores errors to avoid
   * blocking UI interactions.
   */
  logEvent: async (
    productId: string,
    eventType: 'view' | 'audio_play' | 'ebook_download' | 'test_complete',
    sessionId?: string,
    metadata?: Record<string, unknown>,
  ): Promise<void> => {
    try {
      await api.post('/events', {
        product_id: productId,
        event_type: eventType,
        session_id: sessionId,
        metadata,
      });
    } catch {
      // intentionally silent — tracking failure must never break UX
    }
  },

  getTopOpportunities: async (limit = 20): Promise<TopOpportunityItem[]> => {
    const res = await api.get<TopOpportunityItem[]>(
      `/analytics/top-opportunities?limit=${limit}`,
    );
    return res.data;
  },

  getProductStats: async (productId: string): Promise<ProductStatsResponse> => {
    const res = await api.get<ProductStatsResponse>(
      `/analytics/products/${productId}/stats`,
    );
    return res.data;
  },

  // ───── Dashboard Stats ─────

  getOverviewStats: async (): Promise<OverviewStats> => {
    const res = await api.get<OverviewStats>('/stats/overview');
    return res.data;
  },

  getTimeline: async (days = 7): Promise<TimelineEntry[]> => {
    const res = await api.get<TimelineEntry[]>(`/stats/timeline?days=${days}`);
    return res.data;
  },
};

// ───── Stats types ─────

export interface OverviewStats {
  total_projects: number;
  success_rate: number;
  avg_duration_seconds: number;
  status_distribution: Record<string, number>;
  token_usage: {
    total_tokens: number;
    total_llm_calls: number;
    avg_tokens_per_call: number;
  };
  recent: {
    projects_last_24h: number;
    total_tasks: number;
    total_test_runs: number;
  };
}

export interface TimelineEntry {
  date: string;
  count: number;
}

export default api;
