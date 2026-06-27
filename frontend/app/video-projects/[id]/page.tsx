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
  const [faceUploading, setFaceUploading] = useState(false);
  const [faceUploaded, setFaceUploaded] = useState(false);
  const [faceSwapProgress, setFaceSwapProgress] = useState<number | null>(null);
  const [faceSwapStatus, setFaceSwapStatus] = useState("");
  const [watermarkProgress, setWatermarkProgress] = useState<{progress: number; status: string; current_frame?: number; total_frames?: number} | null>(null);
  const [watermarkConfig, setWatermarkConfig] = useState<Record<string, unknown> | null>(null);
  const [dedupConfig, setDedupConfig] = useState<Record<string, unknown> | null>(null);
  const [previewFrames, setPreviewFrames] = useState<Array<{segment_index: number; time_seconds: number; filepath: string; filename: string}> | null>(null);
  const [ocrTime, setOcrTime] = useState(1);
  const [ocrResults, setOcrResults] = useState(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrHasWatermark, setOcrHasWatermark] = useState(null);
  const [activeTab, setActiveTab] = useState<'pipeline' | 'assets' | 'ocr' | 'publish' | 'preview'>('pipeline');

  const fetchProject = async () => {
    try {
      setLoading(true);
      const data = await videoProjectsApi.get(projectId);
      setProject(data);
      // Load watermark config and preview frames
      try {
        const wm = await videoProjectsApi.getWatermarkConfig(projectId);
        setWatermarkConfig(wm.params);
        const pframes = wm.params?.preview_frames as Array<{segment_index: number; time_seconds: number; filepath: string; filename: string}> | undefined;
        if (pframes && pframes.length > 0) {
          setPreviewFrames(pframes);
        }
      } catch {}
      try {
        const dc = await videoProjectsApi.getDedupConfig(projectId);
        setDedupConfig(dc.params);
      } catch {}
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  // Poll face swap progress when face_swap stage is running
  useEffect(() => {
    if (!project) return;
    const faceSwapStage = project.stages.find(s => s.stage_name === 'face_swap');
    if (!faceSwapStage || faceSwapStage.status !== 'running') {
      setFaceSwapProgress(null);
      setFaceSwapStatus('');
      return;
    }

    const interval = setInterval(async () => {
      try {
        const data = await videoProjectsApi.getFaceSwapProgress(projectId);
        setFaceSwapProgress(data.progress);
        setFaceSwapStatus(data.status);
        if (data.progress >= 100) {
          setTimeout(() => fetchProject(), 2000);
        }
      } catch {
        // ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [project?.stages]);

  // Poll watermark progress when remove_watermark stage is running
  useEffect(() => {
    if (!project) return;
    const wmStage = project.stages.find(s => s.stage_name === 'remove_watermark');
    if (!wmStage || wmStage.status !== 'running') {
      if (wmStage?.status === 'completed' || wmStage?.status === 'failed') {
        setWatermarkProgress(null);
      }
      return;
    }

    const interval = setInterval(async () => {
      try {
        const data = await videoProjectsApi.getWatermarkProgress(projectId);
        setWatermarkProgress(data);
        if (data.progress >= 100) {
          setTimeout(() => fetchProject(), 2000);
        }
      } catch {
        // ignore polling errors
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [project?.stages]);

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

  const handleUploadFace = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !project) return;
    setFaceUploading(true);
    try {
      const res = await videoProjectsApi.uploadFace(projectId, file);
      setFaceUploaded(true);
      alert('参考人脸上传成功: ' + res.filepath);
    } catch (err) {
      alert('上传失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setFaceUploading(false);
    }
  };

  const handleStartPipeline = async () => {
    if (!project) return;
    setStageLoading(true);
    try {
      const stages = [...project.stages].sort((a, b) => a.stage_order - b.stage_order);
      await videoProjectsApi.startPipeline(projectId);
      // Run all stages sequentially (backend blocks until each completes)
      for (let i = 0; i < stages.length; i++) {
        const stage = stages[i];
        try {
          await videoProjectsApi.runStage(projectId, stage.stage_name);
        } catch (apiErr) {
          // runStage may timeout for long stages (face_swap etc.); poll instead
          console.warn('runStage API error, falling back to poll:', apiErr);
        }
        // Poll until this stage completes or fails (handles both fast and slow stages)
        let polls = 0;
        while (polls < 600) {
          await new Promise(r => setTimeout(r, 2000));
          polls++;
          const updated = await videoProjectsApi.get(projectId);
          const s = updated.stages.find(s => s.stage_name === stage.stage_name);
          if (s?.status === 'completed') break;
          if (s?.status === 'failed') {
            throw new Error(`阶段 ${s.display_name} 失败: ${s.error_log || ''}`);
          }
          if (updated.status !== 'pipeline_running') break;
        }
      }
      await fetchProject();
      alert('全部管线执行完成！');
    } catch (err) {
      alert('执行失败: ' + (err instanceof Error ? err.message : '未知错误'));
    } finally {
      setStageLoading(false);
    }
  };

  const handleSaveWatermarkConfig = async (config: Record<string, unknown>) => {
    if (!project) return;
    try {
      await videoProjectsApi.saveWatermarkConfig(projectId, config);
      alert('✅ 水印配置已保存');
      await fetchProject();
    } catch (err) {
      alert('保存失败: ' + (err instanceof Error ? err.message : JSON.stringify(err)));
    }
  };

  const handleSaveDedupConfig = async (config: Record<string, unknown>) => {
    if (!project) return;
    try {
      await videoProjectsApi.saveDedupConfig(projectId, config);
      alert('✅ 去重配置已保存');
      await fetchProject();
    } catch (err) {
      alert('保存失败: ' + (err instanceof Error ? err.message : JSON.stringify(err)));
    }
  };

  const handleGeneratePreviewFrames = async () => {
    if (!project) return;
    try {
      const data = await videoProjectsApi.getWatermarkPreviewFrames(projectId);
      setPreviewFrames(data.frames);
      await fetchProject();
      alert('✅ 生成了 ' + data.frames.length + ' 张预览帧，请在面板中配置轨迹点');
    } catch (err) {
      alert('生成失败: ' + (err instanceof Error ? err.message : JSON.stringify(err)));
    }
  };

  const handleOcrCheck = async () => {
    if (!project) return;
    setOcrLoading(true);
    setOcrResults(null);
    setOcrHasWatermark(null);
    try {
      const data = await videoProjectsApi.ocrFrame(projectId, ocrTime, true);
      setOcrResults(data.results);
    } catch (err) {
      alert('OCR识别失败: ' + (err instanceof Error ? err.message : JSON.stringify(err)));
    } finally {
      setOcrLoading(false);
    }
  };

  const handleVerifyWatermark = async () => {
    if (!project) return;
    setOcrLoading(true);
    setOcrResults(null);
    setOcrHasWatermark(null);
    try {
      const data = await videoProjectsApi.verifyWatermark(projectId, ocrTime);
      setOcrHasWatermark(data.has_text);
      setOcrResults(data.results);
    } catch (err) {
      alert('水印验证失败: ' + (err instanceof Error ? err.message : JSON.stringify(err)));
    } finally {
      setOcrLoading(false);
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
            { key: 'preview' as const, label: '▶️ 预览视频', icon: '' },
            { key: 'publish' as const, label: '🚀 发布', icon: '' },
            { key: 'ocr' as const, label: '🔍 OCR检查', icon: '' },
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
            {/* Reference Face Upload */}
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">🔄 换脸 - 参考人脸</h3>
              <p className="text-xs text-gray-500 mb-3">
                上传一张包含目标人脸的照片（JPG/PNG），用于换脸阶段替换视频中的人脸
              </p>
              <div className="flex items-center space-x-3">
                <label className={`px-4 py-2 text-sm font-medium rounded-lg cursor-pointer transition-colors ${
                  faceUploaded
                    ? 'bg-green-100 text-green-700 border border-green-300'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}>
                  {faceUploading ? '上传中...' : faceUploaded ? '✅ 已上传，点击更换' : '📷 选择人脸照片'}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    className="hidden"
                    onChange={handleUploadFace}
                    disabled={faceUploading}
                  />
                </label>
                {faceUploaded && (
                  <span className="text-xs text-green-600">人脸照片已就绪，可执行换脸阶段</span>
                )}
                {!faceUploaded && (
                  <span className="text-xs text-amber-600">⚠️ 执行换脸前必须先上传参考人脸</span>
                )}
              </div>
            </div>

            {/* Face Swap Progress Bar */}
            {faceSwapProgress !== null && (
              <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h3 className="text-sm font-semibold text-blue-700 mb-2">[换脸] 处理中</h3>
                <div className="flex items-center mb-2">
                  <div className="flex-1 bg-blue-200 rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-blue-600 h-full rounded-full transition-all duration-500 ease-in-out"
                      style={{ width: `${Math.min(faceSwapProgress, 100)}%` }}
                    />
                  </div>
                  <span className="ml-3 text-sm font-medium text-blue-700 min-w-[3rem] text-right">
                    {faceSwapProgress}%
                  </span>
                </div>
                <p className="text-xs text-blue-600">
                  {faceSwapStatus === '提取中' && '(提取中) 提取视频帧...'}
                  {faceSwapStatus === '处理中' && '(换脸中) 逐帧换脸...'}
                  {faceSwapStatus === '合成中' && '(合成中) 合成最终视频...'}
                  {!['提取中','处理中','合成中'].includes(faceSwapStatus) && faceSwapStatus}
                </p>
              </div>
            )}

            <PipelineVisualizer
              stages={project.stages}
              currentStage={project.current_stage}
              onRunStage={handleRunStage}
              onStartPipeline={handleStartPipeline}
              running={stageLoading}
              watermarkConfig={watermarkConfig || undefined}
              onSaveWatermarkConfig={handleSaveWatermarkConfig}
              onGeneratePreviewFrames={handleGeneratePreviewFrames}
              previewFrames={previewFrames || undefined}
              watermarkProgress={watermarkProgress}
              dedupConfig={dedupConfig || undefined}
              onSaveDedupConfig={handleSaveDedupConfig}
              projectId={projectId}
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
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">操作</th>
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
                        <td className="py-3 px-4">
                          <a
                            href={"/api/v1/video-projects/" + projectId + "/assets/" + asset.id + "/download"}
                            target="_blank"
                            className="inline-flex items-center px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg"
                          >
                            Download
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'preview' && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">▶️ 视频预览</h2>
            {(() => {
              // Get latest completed output video asset
              const outputAssets = project?.assets?.filter(a => a.asset_type === 'output') || [];
              const latestVideo = outputAssets.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
              
              if (!latestVideo) {
                return (
                  <div className="text-center py-16">
                    <span className="text-6xl">🎬</span>
                    <p className="text-gray-500 mt-4 text-lg">暂无完成视频</p>
                    <p className="text-gray-400 text-sm mt-2">运行管线后，生成的视频将在这里预览</p>
                  </div>
                );
              }

              const videoUrl = `/api/v1/video-projects/${projectId}/assets/${latestVideo.id}/download`;
              const stageLabels: Record<string,string> = {
                remove_watermark: '去水印', dub: '配音', face_swap: '换脸',
                lip_sync: '唇形同步', dedup: '去重处理', overlay_stickers: '叠加贴纸+字幕'
              };
              const stageName = stageLabels[latestVideo.source_stage || ''] || latestVideo.source_stage || '未知';

              return (
                <div>
                  <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-blue-800">
                          <span className="font-medium">当前预览：</span>
                          {latestVideo.filename}
                        </p>
                        <p className="text-xs text-blue-600 mt-1">
                          来源: {stageName}
                          {latestVideo.duration_seconds ? ` | 时长: ${latestVideo.duration_seconds.toFixed(1)}s` : ''}
                          {latestVideo.file_size_bytes ? ` | 大小: ${(latestVideo.file_size_bytes/1024/1024).toFixed(1)}MB` : ''}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <a href={videoUrl} target="_blank"
                           className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-white border border-blue-300 hover:bg-blue-50 rounded-lg">
                          📥 下载
                        </a>
                      </div>
                    </div>
                  </div>

                  <div className="relative bg-black rounded-xl overflow-hidden">
                    <video
                      src={videoUrl}
                      controls
                      autoPlay
                      className="w-full max-h-[70vh] mx-auto"
                      style={{ maxWidth: '100%', height: 'auto' }}
                    >
                      您的浏览器不支持视频播放
                    </video>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {activeTab === 'ocr' && (
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 mb-2">🔍 OCR 文字识别</h2>
            <p className="text-xs text-gray-500 mb-4">从视频帧中识别文字，检测水印残留</p>

            <div className="flex items-center space-x-3 mb-4">
              <label className="text-sm font-medium text-gray-700">时间位置（秒）:</label>
              <input
                type="number"
                min={0}
                max={60}
                value={ocrTime}
                onChange={(e) => setOcrTime(Number(e.target.value))}
                className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
              <button
                onClick={handleOcrCheck}
                disabled={ocrLoading}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {ocrLoading ? '识别中...' : '🔍 识别文字'}
              </button>
              <button
                onClick={handleVerifyWatermark}
                disabled={ocrLoading}
                className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 disabled:opacity-50"
              >
                {ocrLoading ? '检测中...' : '🚫 检测水印'}
              </button>
            </div>

            {ocrHasWatermark !== null && (
              <div className={'mb-4 px-4 py-3 rounded-lg text-sm font-medium ' + (ocrHasWatermark
                ? 'bg-red-50 text-red-700 border border-red-200'
                : 'bg-green-50 text-green-700 border border-green-200')}>
                {ocrHasWatermark
                  ? '⚠️ 水印区域检测到文字！水印可能未完全去除。'
                  : '✅ 水印区域未检测到文字，去水印效果良好。'}
              </div>
            )}

            {ocrResults && ocrResults.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-2 px-3 text-gray-600 font-medium">文本</th>
                      <th className="text-left py-2 px-3 text-gray-600 font-medium">置信度</th>
                      <th className="text-left py-2 px-3 text-gray-600 font-medium">位置 (x,y,w,h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ocrResults.map((r, i) => (
                      <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium text-gray-900">{r.text}</td>
                        <td className="py-2 px-3">
                          <span className={'px-2 py-0.5 rounded-full text-xs font-medium ' + (
                            r.confidence > 0.8 ? 'bg-green-100 text-green-700' :
                            r.confidence > 0.5 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          )}>
                            {(r.confidence * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td className="py-2 px-3 text-gray-500 text-xs font-mono">
                          {r.position.join(', ')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : ocrResults && ocrResults.length === 0 ? (
              <div className="text-center py-8">
                <span className="text-3xl">💬</span>
                <p className="text-gray-500 mt-2">该帧未识别到文字</p>
              </div>
            ) : null}
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
