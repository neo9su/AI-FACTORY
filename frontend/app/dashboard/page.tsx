'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface OverviewStats {
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

interface TimelineEntry {
  date: string;
  count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const [overviewRes, timelineRes] = await Promise.all([
          fetch(`${API_BASE}/stats/overview`),
          fetch(`${API_BASE}/stats/timeline?days=7`),
        ]);
        if (overviewRes.ok) setStats(await overviewRes.json());
        if (timelineRes.ok) setTimeline(await timelineRes.json());
      } catch (e) {
        console.error('Failed to fetch stats:', e);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500 text-lg">Loading dashboard...</div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-red-500">Failed to load statistics. Is the backend running?</div>
      </div>
    );
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    return `${(seconds / 60).toFixed(1)}m`;
  };

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return n.toString();
  };

  const maxTimelineCount = Math.max(...timeline.map((t) => t.count), 1);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Factory Dashboard</h1>
            <p className="text-gray-500 mt-1">AI Software Factory performance overview</p>
          </div>
          <div className="flex gap-3">
            <Link
              href="/projects"
              className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              View Projects
            </Link>
            <Link
              href="/projects/new"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              + New Project
            </Link>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Total Projects</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stats.total_projects}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📦</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              <span className="text-green-600 font-medium">+{stats.recent.projects_last_24h}</span> last 24h
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Success Rate</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stats.success_rate}%</p>
              </div>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">✅</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {stats.status_distribution['delivered'] || 0} delivered / {(stats.status_distribution['delivered'] || 0) + (stats.status_distribution['failed'] || 0)} total
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Avg Duration</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{formatDuration(stats.avg_duration_seconds)}</p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">⏱️</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              From requirements to delivery
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Token Usage</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{formatTokens(stats.token_usage.total_tokens)}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🔤</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {stats.token_usage.total_llm_calls} LLM calls ({formatTokens(stats.token_usage.avg_tokens_per_call)} avg)
            </p>
          </div>
        </div>

        {/* Middle row: Status distribution + Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Status Distribution */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Status Distribution</h3>
            <div className="space-y-3">
              {Object.entries(stats.status_distribution).map(([status, count]) => {
                const total = stats.total_projects || 1;
                const pct = (count / total) * 100;
                const colors: Record<string, string> = {
                  delivered: 'bg-green-500',
                  failed: 'bg-red-500',
                  developing: 'bg-blue-500',
                  testing: 'bg-yellow-500',
                  reviewing: 'bg-purple-500',
                  created: 'bg-gray-400',
                };
                return (
                  <div key={status}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 capitalize">{status.replace(/_/g, ' ')}</span>
                      <span className="text-gray-500">{count} ({pct.toFixed(0)}%)</span>
                    </div>
                    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${colors[status] || 'bg-gray-400'}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Timeline */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Projects (Last 7 Days)</h3>
            {timeline.length === 0 ? (
              <p className="text-gray-400 text-center py-8">No projects in the last 7 days</p>
            ) : (
              <div className="flex items-end justify-between h-40 gap-2">
                {timeline.map((entry) => (
                  <div key={entry.date} className="flex-1 flex flex-col items-center">
                    <span className="text-xs text-gray-500 mb-1">{entry.count}</span>
                    <div
                      className="w-full bg-blue-500 rounded-t transition-all"
                      style={{
                        height: `${(entry.count / maxTimelineCount) * 100}%`,
                        minHeight: entry.count > 0 ? '8px' : '2px',
                      }}
                    />
                    <span className="text-xs text-gray-400 mt-2 truncate w-full text-center">
                      {entry.date.slice(5)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Bottom row: Quick stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                <span className="text-xl">📋</span>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Tasks</p>
                <p className="text-xl font-bold text-gray-900">{stats.recent.total_tasks}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-teal-100 rounded-lg flex items-center justify-center">
                <span className="text-xl">🧪</span>
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Test Runs</p>
                <p className="text-xl font-bold text-gray-900">{stats.recent.total_test_runs}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
                <span className="text-xl">🤖</span>
              </div>
              <div>
                <p className="text-sm text-gray-500">LLM Calls</p>
                <p className="text-xl font-bold text-gray-900">{stats.token_usage.total_llm_calls}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
