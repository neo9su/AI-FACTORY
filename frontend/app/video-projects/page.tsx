'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { videoProjectsApi, type VideoProject } from '@/lib/api';

const STATUS_LABELS: Record<string, { label: string; emoji: string; color: string }> = {
  created: { label: '待开始', emoji: '📋', color: 'bg-gray-100 text-gray-700' },
  pipeline_running: { label: '生产中', emoji: '⚙️', color: 'bg-blue-100 text-blue-700' },
  pipeline_completed: { label: '已完成', emoji: '✅', color: 'bg-green-100 text-green-700' },
  published: { label: '已发布', emoji: '🚀', color: 'bg-purple-100 text-purple-700' },
  failed: { label: '失败', emoji: '❌', color: 'bg-red-100 text-red-700' },
};

function formatDate(date: string): string {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}小时前`;
  return d.toLocaleDateString('zh-CN');
}

const STAGE_EMOJIS = ['💧', '🎙️', '🔄', '👄', '✨'];
const STAGE_NAMES = ['去水印', '配音', '换脸', '唇形同步', '去重处理'];

export default function VideoProjectsPage() {
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await videoProjectsApi.list(statusFilter ? { status: statusFilter } : undefined);
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [statusFilter]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link href="/dashboard" className="text-blue-600 hover:text-blue-700 font-medium mb-2 inline-block">
              ← 返回仪表盘
            </Link>
            <h1 className="text-3xl font-bold text-gray-900">视频生产管线</h1>
            <p className="text-gray-600 mt-1">管理视频内容生产全流程：去水印 → 配音 → 换脸 → 唇形同步 → 去重处理</p>
          </div>
          <Link
            href="/video-projects/new"
            className="px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-md"
          >
            + 新建视频项目
          </Link>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          {STAGE_NAMES.map((name, i) => (
            <div key={name} className="bg-white rounded-lg shadow-sm p-4 text-center">
              <span className="text-2xl">{STAGE_EMOJIS[i]}</span>
              <p className="text-sm text-gray-600 mt-1">{name}</p>
            </div>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex space-x-2 mb-6">
          <button
            onClick={() => setStatusFilter('')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              !statusFilter ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
            }`}
          >
            全部
          </button>
          {Object.entries(STATUS_LABELS).map(([key, val]) => (
            <button
              key={key}
              onClick={() => setStatusFilter(key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === key ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {val.emoji} {val.label}
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading && (
          <div className="text-center py-20">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center mb-6">
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={fetchProjects}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              重试
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && projects.length === 0 && (
          <div className="bg-white rounded-xl shadow-md p-12 text-center">
            <span className="text-6xl">🎬</span>
            <h3 className="text-xl font-bold text-gray-900 mt-4 mb-2">还没有视频项目</h3>
            <p className="text-gray-600 mb-6">创建一个视频项目，开始全自动内容生产管线</p>
            <Link
              href="/video-projects/new"
              className="inline-block px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700"
            >
              新建视频项目
            </Link>
          </div>
        )}

        {/* Project List */}
        {!loading && !error && projects.length > 0 && (
          <div className="grid gap-4">
            {projects.map((project) => {
              const statusInfo = STATUS_LABELS[project.status] || { label: project.status, emoji: '❓', color: 'bg-gray-100 text-gray-700' };
              return (
                <Link
                  key={project.id}
                  href={`/video-projects/${project.id}`}
                  className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow p-6 block"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{project.title}</h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusInfo.color}`}>
                          {statusInfo.emoji} {statusInfo.label}
                        </span>
                      </div>
                      {project.description && (
                        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{project.description}</p>
                      )}
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        {project.source_filename && (
                          <span>🎬 {project.source_filename}</span>
                        )}
                        <span>📅 {formatDate(project.created_at)}</span>
                        {project.current_stage !== null && (
                          <span>
                            进度 {STAGE_EMOJIS[project.current_stage]} {STAGE_NAMES[project.current_stage]}
                            {' '}({project.current_stage + 1}/{project.total_stages})
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-gray-400 ml-4">→</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
