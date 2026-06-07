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

interface StageStat {
  name: string;
  executions: number;
  avg_duration_seconds: number;
  success_count: number;
  fail_count: number;
  failure_rate: number;
}

interface PipelineHistory {
  id: string;
  name: string;
  status: string;
  created_at: string;
  duration_seconds: number;
  agent_runs: number;
  tasks: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function formatDuration(seconds: number) {
  if (seconds < 60) return `${seconds.toFixed(0)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  return `${(seconds / 3600).toFixed(2)}h`;
}

function formatTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

const STATUS_UI: Record<string, { label: string; emoji: string; color: string; bg: string }> = {
  delivered: { label: '已交付', emoji: '✅', color: 'text-green-700', bg: 'bg-green-100' },
  failed: { label: '失败', emoji: '❌', color: 'text-red-700', bg: 'bg-red-100' },
  developing: { label: '开发中', emoji: '⚙️', color: 'text-blue-700', bg: 'bg-blue-100' },
  testing: { label: '测试中', emoji: '🧪', color: 'text-yellow-700', bg: 'bg-yellow-100' },
  fixing: { label: '修复中', emoji: '🔧', color: 'text-orange-700', bg: 'bg-orange-100' },
  reviewing: { label: '审查中', emoji: '🔍', color: 'text-purple-700', bg: 'bg-purple-100' },
  planning: { label: '规划中', emoji: '📋', color: 'text-indigo-700', bg: 'bg-indigo-100' },
  created: { label: '已创建', emoji: '📋', color: 'text-gray-700', bg: 'bg-gray-100' },
};

export default function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [stages, setStages] = useState<StageStat[]>([]);
  const [history, setHistory] = useState<PipelineHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchAll = async () => {
    try {
      const [overviewRes, timelineRes, stagesRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/stats/overview`),
        fetch(`${API_BASE}/stats/timeline?days=14`),
        fetch(`${API_BASE}/stats/stages`),
        fetch(`${API_BASE}/stats/history?limit=15`),
      ]);
      if (overviewRes.ok) setStats(await overviewRes.json());
      if (timelineRes.ok) setTimeline(await timelineRes.json());
      if (stagesRes.ok) {
        const data = await stagesRes.json();
        setStages(data.stages || []);
      }
      if (historyRes.ok) setHistory(await historyRes.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  // Auto-refresh every 30s
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">加载监控面板...</p>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button onClick={fetchAll} className="px-4 py-2 bg-blue-600 text-white rounded-lg">重试</button>
        </div>
      </div>
    );
  }

  const maxTimelineCount = Math.max(...timeline.map((t) => t.count), 1);
  const maxStageDuration = Math.max(...stages.map((s) => s.avg_duration_seconds), 1);
  const stageColors = ['bg-blue-500', 'bg-purple-500', 'bg-green-500', 'bg-orange-500', 'bg-red-500', 'bg-yellow-500', 'bg-pink-500', 'bg-indigo-500'];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">工厂监控面板</h1>
            <p className="text-gray-500 mt-1">AI 软件工厂运行状态全景</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
                autoRefresh ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-50 border-gray-200 text-gray-500'
              }`}
            >
              {autoRefresh ? '🟢 自动刷新' : '⏸️ 已暂停'}
            </button>
            <Link href="/projects/new" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
              + 新建项目
            </Link>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">总项目数</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stats?.total_projects || 0}</p>
              </div>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">📦</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              <span className="text-green-600 font-medium">+{stats?.recent.projects_last_24h || 0}</span> 近24小时
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">成功率</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{stats?.success_rate || 0}%</p>
              </div>
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                (stats?.success_rate || 0) >= 70 ? 'bg-green-100' : (stats?.success_rate || 0) >= 40 ? 'bg-yellow-100' : 'bg-red-100'
              }`}>
                <span className="text-2xl">{(stats?.success_rate || 0) >= 70 ? '✅' : (stats?.success_rate || 0) >= 40 ? '⚠️' : '❌'}</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {stats?.status_distribution['delivered'] || 0} 交付 / {(stats?.status_distribution['delivered'] || 0) + (stats?.status_distribution['failed'] || 0)} 完成
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">平均耗时</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{formatDuration(stats?.avg_duration_seconds || 0)}</p>
              </div>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">⏱️</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">从需求到交付</p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">Token 消耗</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">{formatTokens(stats?.token_usage.total_tokens || 0)}</p>
              </div>
              <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                <span className="text-2xl">🔤</span>
              </div>
            </div>
            <p className="text-sm text-gray-500 mt-3">
              {stats?.token_usage.total_llm_calls || 0} 次调用 (均 {formatTokens(stats?.token_usage.avg_tokens_per_call || 0)})
            </p>
          </div>
        </div>

        {/* Row 2: Status + Timeline + Stage Duration */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Status Distribution */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">状态分布</h3>
            {stats && Object.keys(stats.status_distribution).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(stats.status_distribution).map(([status, count]) => {
                  const total = stats.total_projects || 1;
                  const pct = (count / total) * 100;
                  const ui = STATUS_UI[status] || { label: status, emoji: '❓', color: 'text-gray-700', bg: 'bg-gray-100' };
                  return (
                    <div key={status}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-700">{ui.emoji} {ui.label}</span>
                        <span className="text-gray-500">{count} ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${ui.bg.replace('bg-', 'bg-')}`}
                          style={{ width: `${pct}%`, backgroundColor: status === 'delivered' ? '#22c55e' : status === 'failed' ? '#ef4444' : undefined }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-gray-400 text-center py-8">暂无数据</p>
            )}
          </div>

          {/* Timeline */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">项目创建趋势 (14天)</h3>
            {timeline.length === 0 ? (
              <p className="text-gray-400 text-center py-8">近14天无项目</p>
            ) : (
              <div className="flex items-end justify-between h-40 gap-1.5">
                {timeline.map((entry) => (
                  <div key={entry.date} className="flex-1 flex flex-col items-center">
                    <span className="text-xs text-gray-500 mb-1">{entry.count}</span>
                    <div
                      className="w-full bg-gradient-to-t from-blue-500 to-blue-400 rounded-t transition-all"
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

          {/* Stage Duration */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">阶段平均耗时</h3>
            {stages.length === 0 ? (
              <p className="text-gray-400 text-center py-8">暂无管线执行记录</p>
            ) : (
              <div className="space-y-3">
                {[...stages].sort((a, b) => b.avg_duration_seconds - a.avg_duration_seconds).slice(0, 6).map((stage, i) => (
                  <div key={stage.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 truncate flex-1">{stage.name.replace(/_/g, ' ')}</span>
                      <span className="text-gray-500 ml-2">{formatDuration(stage.avg_duration_seconds)}</span>
                    </div>
                    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${stageColors[i % stageColors.length]}`}
                        style={{ width: `${(stage.avg_duration_seconds / maxStageDuration) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Row 3: Stage Failure Rate + Bottom Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Stage Failure Rate */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">阶段失败率</h3>
            {stages.length === 0 ? (
              <p className="text-gray-400 text-center py-8">暂无数据</p>
            ) : (
              <div className="space-y-3">
                {[...stages].sort((a, b) => b.failure_rate - a.failure_rate).map((stage, i) => (
                  <div key={stage.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-700 truncate flex-1">{stage.name.replace(/_/g, ' ')}</span>
                      <span className={`ml-2 font-medium ${stage.failure_rate > 20 ? 'text-red-600' : stage.failure_rate > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                        {stage.failure_rate}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${stage.failure_rate > 20 ? 'bg-red-500' : stage.failure_rate > 0 ? 'bg-yellow-500' : 'bg-green-500'}`}
                        style={{ width: `${Math.min(stage.failure_rate, 100)}%` }}
                      />
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {stage.success_count} 成功 / {stage.fail_count} 失败 / {stage.executions} 总执行
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">工厂概况</h3>
            <div className="grid grid-cols-2 gap-4">
              {[
                { label: '总任务数', value: stats?.recent.total_tasks || 0, emoji: '📋', color: 'bg-indigo-100' },
                { label: '测试执行数', value: stats?.recent.total_test_runs || 0, emoji: '🧪', color: 'bg-teal-100' },
                { label: 'LLM 调用', value: stats?.token_usage.total_llm_calls || 0, emoji: '🤖', color: 'bg-rose-100' },
                { label: 'Agent 执行', value: stages.reduce((s, st) => s + st.executions, 0), emoji: '⚙️', color: 'bg-amber-100' },
              ].map((item) => (
                <div key={item.label} className="bg-gray-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-8 h-8 ${item.color} rounded-lg flex items-center justify-center`}>
                      <span className="text-sm">{item.emoji}</span>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{typeof item.value === 'number' ? item.value.toLocaleString() : item.value}</p>
                  <p className="text-xs text-gray-500 mt-1">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline History */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">最近管线运行</h3>
            {history.length === 0 ? (
              <p className="text-gray-400 text-center py-8">暂无管线记录</p>
            ) : (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {history.map((row) => {
                  const ui = STATUS_UI[row.status] || { label: row.status, emoji: '❓', color: 'text-gray-700', bg: 'bg-gray-100' };
                  return (
                    <Link
                      key={row.id}
                      href={`/projects/${row.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{row.name}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {formatDate(row.created_at)}
                          {row.agent_runs > 0 && ` · ${row.agent_runs} agents`}
                        </p>
                      </div>
                      <div className="flex items-center space-x-3 ml-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ui.bg} ${ui.color}`}>
                          {ui.emoji} {ui.label}
                        </span>
                        {row.duration_seconds > 0 && (
                          <span className="text-xs text-gray-400">{formatDuration(row.duration_seconds)}</span>
                        )}
                      </div>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Error Distribution (if any failures) */}
        {stats && (stats.status_distribution['failed'] || 0) > 0 && (
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">⚠️ 失败项目</h3>
            <p className="text-sm text-gray-500 mb-4">
              共 {stats.status_distribution['failed']} 个项目失败，建议检查 Gatekeeper 配置和 LLM 连接状态。
            </p>
            <Link href="/projects?status=failed" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
              查看失败项目 →
            </Link>
          </div>
        )}

        {/* Empty state */}
        {stats && stats.total_projects === 0 && (
          <div className="bg-white rounded-xl p-12 text-center shadow-sm border border-gray-100">
            <span className="text-6xl">🏭</span>
            <h3 className="text-xl font-bold text-gray-900 mt-4 mb-2">工厂还没开工</h3>
            <p className="text-gray-600 mb-6">创建第一个项目，开始体验全自动 AI 软件工厂</p>
            <Link
              href="/projects/new"
              className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700"
            >
              创建项目
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
