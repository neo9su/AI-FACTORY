'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { videoProjectsApi, type VideoProjectDetail, type VideoAsset } from '@/lib/api';
import PipelineVisualizer from '@/components/video-pipeline-visualizer';

const STATUS_LABELS: Record<string, { label: string; emoji: string; color: string }> = {
  created: { label: '待开始', emoji: '📋', color: 'bg-gray-100 text-gray-700' },
  pipeline_running: { label: '生产中', emoji: '⚙️', color: 'bg-blue-100 text-blue-700' },
  pipeline_completed: { label: '已完成', emoji: '✅', color: 'bg-green-100 text-green-700' },
  published: { label: '已发布', emoji: '🚀', color: 'bg-purple-100 text-purple-700' },
  failed: { label: '失败', emoji: '❌', color: 'bg-red-100 text-red-700' },
};

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '-';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '-';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s.toFixed(0)}s`;
}

export default function VideoProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<VideoProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stageLoading, setStageLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'pipeline' | 'assets' | 'publish'>('pipeline');

  const fetchProject = async () => {
    try {
      setLoading(true);
      const data = await videoProjectsApi.get(projectId);
      setProject(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const handleRunStage = async (stageName: string) => {
    if (!project) return;
    setStageLoading(true);
    try {
      await videoProjectsApi.runStage(projectId, stageName);
      await fetchProject();
    } catch (err) {
      alert('执行失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStageLoading(false);
    }
  };

  const handleStartPipeline = async () => {
    if (!project) return;
    setStageLoading(true);
    try {
      await videoProjectsApi.startPipeline(projectId);
      // Start first stage
      if (project.stages.length > 0) {
        await videoProjectsApi.runStage(projectId, project.stages[0].stage_name);
      }
      await fetchProject();
    } catch (err) {
      alert('启动失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStageLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!project) return;
    if (!confirm(`确认删除项目"${project.title}"？此操作不可撤销。`)) return;
    try {
      await videoProjectsApi.delete(projectId);
      router.push('/video-projects');
    } catch (err) {
      alert('删除失败: ' + (err instanceof Error ? err.message : '未知错误'));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || '项目不存在'}</p>
          <Link href="/video-projects" className="text-blue-600 hover:underline">
            ← 返回视频项目列表
          </Link>
        </div>
      </div>
    );
  }

  const statusInfo = STATUS_LABELS[project.status] || { label: project.status, emoji: '❓', color: 'bg-gray-100 text-gray-700' };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Breadcrumb */}
        <div className="mb-6">
          <Link href="/video-projects" className="text-blue-600 hover:text-blue-700 font-medium">
            ← 视频项目列表
          </Link>
        </div>

        {/* Project Header */}
        <div className="bg-white rounded-xl shadow-md p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <h1 className="text-2xl font-bold text-gray-900">{project.title}</h1>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusInfo.color}`}>
                  {statusInfo.emoji} {statusInfo.label}
                </span>
              </div>
              {project.description && (
                <p className="text-gray-600">{project.description}</p>
              )}
            </div>
            <button
              onClick={handleDelete}
              className="px-3 py-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg border border-red-200"
            >
              删除
            </button>
          </div>

          {/* Source Info */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">源文件</p>
              <p className="text-sm font-medium text-gray-900 truncate">{project.source_filename || '-'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">分辨率</p>
              <p className="text-sm font-medium text-gray-900">{project.source_resolution || '-'}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">时长</p>
              <p className="text-sm font-medium text-gray-900">
                {project.source_duration ? `${project.source_duration.toFixed(1)}s` : '-'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500">管线进度</p>
              <p className="text-sm font-medium text-gray-900">
                {project.current_stage !== null
                  ? `${project.current_stage + 1}/${project.total_stages}`
                  : '-'
                }
              </p>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-1 bg-white rounded-xl shadow-sm p-1 mb-6">
          {[
            { key: 'pipeline' as const, label: '🎬 管线执行', icon: '' },
            { key: 'assets' as const, label: '📦 生成资产', icon: '' },
            { key: 'publish' as const, label: '🚀 发布', icon: '' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 px-6 py-3 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.key
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'pipeline' && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <PipelineVisualizer
              stages={project.stages}
              currentStage={project.current_stage}
              onRunStage={handleRunStage}
              onStartPipeline={handleStartPipeline}
              running={stageLoading}
            />
          </div>
        )}

        {activeTab === 'assets' && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">生成资产列表</h2>
            {project.assets.length === 0 ? (
              <div className="text-center py-12">
                <span className="text-4xl">📂</span>
                <p className="text-gray-500 mt-4">暂无生成资产，运行管线后文件将出现在这里</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">文件名</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">类型</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">大小</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">时长</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">分辨率</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">来源阶段</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">生成时间</th>
                    </tr>
                  </thead>
                  <tbody>
                    {project.assets.map((asset: VideoAsset) => (
                      <tr key={asset.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium text-gray-900">{asset.filename}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            asset.asset_type === 'source' ? 'bg-blue-100 text-blue-700' :
                            asset.asset_type === 'output' ? 'bg-green-100 text-green-700' :
                            asset.asset_type === 'publish_ready' ? 'bg-purple-100 text-purple-700' :
                            'bg-gray-100 text-gray-600'
                          }`}>
                            {asset.asset_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-600">{formatFileSize(asset.file_size_bytes)}</td>
                        <td className="py-3 px-4 text-gray-600">{formatDuration(asset.duration_seconds)}</td>
                        <td className="py-3 px-4 text-gray-600">{asset.resolution || '-'}</td>
                        <td className="py-3 px-4 text-gray-600">{asset.source_stage || '-'}</td>
                        <td className="py-3 px-4 text-gray-500 text-xs">
                          {new Date(asset.created_at).toLocaleString('zh-CN')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'publish' && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">发布到平台</h2>
            <div className="grid grid-cols-3 gap-4">
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-red-300 hover:bg-red-50 transition-colors cursor-pointer">
                <span className="text-3xl">📕</span>
                <p className="font-medium text-gray-900 mt-2">小红书</p>
                <p className="text-sm text-gray-500 mt-1">发布图文/视频笔记</p>
                <span className="inline-block mt-3 px-3 py-1 text-xs bg-gray-100 text-gray-500 rounded-full">即将开放</span>
              </div>
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-blue-300 hover:bg-blue-50 transition-colors cursor-pointer">
                <span className="text-3xl">🎵</span>
                <p className="font-medium text-gray-900 mt-2">抖音</p>
                <p className="text-sm text-gray-500 mt-1">发布短视频</p>
                <span className="inline-block mt-3 px-3 py-1 text-xs bg-gray-100 text-gray-500 rounded-full">即将开放</span>
              </div>
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:bg-gray-50 transition-colors cursor-not-allowed opacity-50">
                <span className="text-3xl">🌊</span>
                <p className="font-medium text-gray-900 mt-2">TikTok</p>
                <p className="text-sm text-gray-500 mt-1">发布到海外版</p>
                <span className="inline-block mt-3 px-3 py-1 text-xs bg-gray-100 text-gray-500 rounded-full">即将开放</span>
              </div>
            </div>
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-blue-700">
                💡 发布功能需要先在「设置」中配置对应平台的 API Key 和 OAuth 认证。
                产线完成后，选择最终输出资产即可一键发布到已配置的平台。
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
