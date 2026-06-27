'use client';

import { useState } from 'react';
import type { VideoPipelineStage } from '@/lib/api';

interface PipelineVisualizerProps {
  stages: VideoPipelineStage[];
  currentStage: number | null;
  onRunStage: (stageName: string) => void;
  onStartPipeline: () => void;
  running: boolean;
  watermarkConfig?: Record<string, unknown>;
  onSaveWatermarkConfig?: (config: Record<string, unknown>) => void;
  onGeneratePreviewFrames?: () => void;
  previewFrames?: Array<{segment_index: number; time_seconds: number; filepath: string; filename: string}>;
  watermarkProgress?: {progress: number; status: string; current_frame?: number; total_frames?: number} | null;
  dedupConfig?: Record<string, unknown>;
  onSaveDedupConfig?: (config: Record<string, unknown>) => void;
  dedupProgress?: {progress?: number; status?: string} | null;
  projectId?: string;
  faceSwapConfig?: Record<string, unknown>;
  onSaveFaceSwapConfig?: (config: Record<string, unknown>) => void;
}

const STAGE_META: Record<string, { emoji: string; color: string; desc: string }> = {
  remove_watermark: {
    emoji: '💧',
    color: 'from-cyan-400 to-blue-500',
    desc: '智能去除视频水印，保持画质',
  },
  dub: {
    emoji: '🎙️',
    color: 'from-purple-400 to-pink-500',
    desc: 'AI 配音合成，支持多种声音风格',
  },
  face_swap: {
    emoji: '🔄',
    color: 'from-orange-400 to-red-500',
    desc: '精准人脸替换，支持单人或多人身份匹配',
  },
  lip_sync: {
    emoji: '👄',
    color: 'from-pink-400 to-rose-500',
    desc: '唇形同步匹配，视音频对齐（需 GPU）',
  },
  dedup: {
    emoji: '✨',
    color: 'from-green-400 to-emerald-500',
    desc: '去重处理：画中画 + 光扫 + BGM + 帧重生成',
  },
  overlay_stickers: {
    emoji: '🎨',
    color: 'from-yellow-400 to-orange-500',
    desc: '叠加动态贴纸 + 新字幕样式（右上角标 + 卖点高亮）',
  },
};

function StageStatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <span className="text-green-500 text-lg">✅</span>;
    case 'running':
      return <span className="inline-block animate-spin text-lg">⏳</span>;
    case 'failed':
      return <span className="text-red-500 text-lg">❌</span>;
    case 'skipped':
      return <span className="text-gray-400 text-lg">⏭️</span>;
    default:
      return <span className="text-gray-300 text-lg">⏸️</span>;
  }
}

export default function PipelineVisualizer({
  stages,
  currentStage,
  onRunStage,
  onStartPipeline,
  running,
  watermarkConfig,
  onSaveWatermarkConfig,
  onGeneratePreviewFrames,
  previewFrames,
  watermarkProgress,
  dedupConfig,
  onSaveDedupConfig,
  dedupProgress,
  projectId,
  faceSwapConfig,
  onSaveFaceSwapConfig,
}: PipelineVisualizerProps) {
  const [wmForm, setWmForm] = useState({
    name: (watermarkConfig?.watermark_name as string) || "",
    type: (watermarkConfig?.watermark_type as string) || "text",
    movement: (watermarkConfig?.movement_type as string) || "moving",
    description: (watermarkConfig?.trajectory_description as string) || "",
  });
  const [dedupForm, setDedupForm] = useState({
    saturation: (dedupConfig?.saturation as number) ?? 1.05,
    brightness: (dedupConfig?.brightness as number) ?? 1.01,
    contrast: (dedupConfig?.contrast as number) ?? 1.02,
    speed_variation: (dedupConfig?.speed_variation as number) ?? 0.02,
    pixel_shift: (dedupConfig?.pixel_shift as number) ?? 1,
    noise_level: (dedupConfig?.noise_level as number) ?? 0.001,
  });
  const [fsForm, setFsForm] = useState({
    swapMode: (faceSwapConfig?.swap_mode as string) || "simple",
    faceSrc1: (faceSwapConfig?.source_faces as Record<string, string>)?.["person1"] || "",
    faceSrc2: (faceSwapConfig?.source_faces as Record<string, string>)?.["person2"] || "",
    refFrame1: (faceSwapConfig?.ref_frames as Record<string, string>)?.["person1"] || "",
    refFrame2: (faceSwapConfig?.ref_frames as Record<string, string>)?.["person2"] || "",
  });
  const [expandedStage, setExpandedStage] = useState<string | null>(null);

  const allPending = stages.every((s) => s.status === 'pending');
  const pipelineComplete = stages.every((s) => s.status === 'completed');
  const hasFailed = stages.some((s) => s.status === 'failed');

  return (
    <div className="space-y-3">
      {/* Pipeline Actions */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">管线状态</h3>
        <div className="flex space-x-3">
          {/* Show "重置并启动全管线" unless all are pending */}
          {!allPending && !pipelineComplete && !hasFailed && (
            <button
              onClick={() => {
                if (confirm('重置管线会清空所有已完成的阶段，确定继续？')) {
                  onStartPipeline();
                }
              }}
              disabled={running}
              className="px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 disabled:bg-gray-300 transition-colors"
            >
              {running ? '⏳ 重置中...' : '🔄 重置管线 & 全量执行'}
            </button>
          )}
          {allPending && (
            <button
              onClick={onStartPipeline}
              disabled={running}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 transition-colors"
            >
              {running ? '⏳ 启动中...' : '▶ 启动全管线'}
            </button>
          )}
          {pipelineComplete && (
            <span className="px-4 py-2 bg-green-100 text-green-700 text-sm font-medium rounded-lg">
              🎉 全部完成
            </span>
          )}
        </div>
      </div>

      {/* Stage List */}
      <div className="space-y-2">
        {stages.map((stage, index) => {
          const meta = STAGE_META[stage.stage_name] || {
            emoji: '❓',
            color: 'from-gray-400 to-gray-500',
            desc: '',
          };
          const isActive = currentStage === index;
          const isExpanded = expandedStage === stage.stage_name;

          return (
            <div
              key={stage.id}
              className={`bg-white rounded-xl border transition-all ${
                isActive
                  ? 'border-blue-400 shadow-md ring-1 ring-blue-200'
                  : stage.status === 'completed'
                    ? 'border-green-200'
                    : stage.status === 'failed'
                      ? 'border-red-200'
                      : 'border-gray-200'
              }`}
            >
              {/* Stage Header */}
              <div
                className="flex items-center p-4 cursor-pointer hover:bg-gray-50 rounded-xl"
                onClick={() => setExpandedStage(isExpanded ? null : stage.stage_name)}
              >
                {/* Stage Number */}
                <div
                  className={`w-10 h-10 rounded-full bg-gradient-to-br ${meta.color} flex items-center justify-center text-white font-bold text-sm shrink-0`}
                >
                  {index + 1}
                </div>

                {/* Name & Status */}
                <div className="ml-4 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{meta.emoji}</span>
                    <span className="font-semibold text-gray-900">{stage.display_name}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      stage.status === 'completed' ? 'bg-green-100 text-green-700' :
                      stage.status === 'running' ? 'bg-blue-100 text-blue-700' :
                      stage.status === 'failed' ? 'bg-red-100 text-red-700' :
                      stage.status === 'skipped' ? 'bg-gray-100 text-gray-500' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {stage.status === 'completed' ? '已完成' :
                       stage.status === 'running' ? '执行中' :
                       stage.status === 'failed' ? '失败' :
                       stage.status === 'skipped' ? '已跳过' :
                       '待执行'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">{meta.desc}</p>
                </div>

                {/* Duration */}
                <div className="text-right mr-4">
                  <div className="text-sm text-gray-500">
                    {stage.completed_at ? (
                      <span>⏱ {stage.duration_seconds?.toFixed(1) || '-'}s</span>
                    ) : stage.started_at ? (
                      <span className="text-blue-500">执行中...</span>
                    ) : null}
                  </div>
                  <StageStatusIcon status={stage.status} />
                </div>

                {/* Run Button */}
                {stage.status !== 'running' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onRunStage(stage.stage_name);
                    }}
                    disabled={running}
                    className="px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {stage.status === 'completed' ? '↻ 重跑' : '▶ 执行'}
                  </button>
                )}
              </div>

              {/* Watermark Config (remove_watermark only, expanded) */}
              {isExpanded && stage.stage_name === 'remove_watermark' && (
                <div className="border-t border-gray-100 px-4 py-3 bg-white rounded-b-xl">
                  {watermarkProgress && watermarkProgress.status === 'processing' ? (
                    <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <h4 className="text-sm font-semibold text-blue-700 mb-2">⏳ 去水印处理中...</h4>
                      <div className="flex items-center mb-2">
                        <div className="flex-1 bg-blue-200 rounded-full h-4 overflow-hidden">
                          <div className="bg-blue-600 h-full rounded-full transition-all duration-500 ease-in-out" style={{ width: `${Math.min(watermarkProgress.progress, 100)}%` }} />
                        </div>
                        <span className="ml-3 text-sm font-medium text-blue-700 min-w-[3rem] text-right">{watermarkProgress.progress}%</span>
                      </div>
                      <p className="text-xs text-blue-600">帧 {watermarkProgress.current_frame || 0}/{watermarkProgress.total_frames || 0}</p>
                    </div>
                  ) : null}

                  <h4 className="text-sm font-semibold text-gray-700 mb-3">💧 水印配置</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 mb-1">水印名称</label>
                      <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="如: 小登好物推荐" value={wmForm.name} onChange={(e) => setWmForm(f => ({...f, name: e.target.value}))} />
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">水印类型</label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" value={wmForm.type} onChange={(e) => setWmForm(f => ({...f, type: e.target.value}))}>
                        <option value="text">文字</option>
                        <option value="pattern">图案</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">运动类型</label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" value={wmForm.movement} onChange={(e) => setWmForm(f => ({...f, movement: e.target.value}))}>
                        <option value="moving">移动</option>
                        <option value="static">固定</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">轨迹描述</label>
                      <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="如: 从左进→右下→出屏→从右进→左下" value={wmForm.description} onChange={(e) => setWmForm(f => ({...f, description: e.target.value}))} />
                    </div>
                  </div>

                  <div className="mt-4 flex items-center space-x-3">
                    <button
                      onClick={() => {
                        if (onSaveWatermarkConfig) {
                          onSaveWatermarkConfig({
                            watermark_name: wmForm.name,
                            watermark_type: wmForm.type,
                            movement_type: wmForm.movement,
                            trajectory_description: wmForm.description,
                            subtitle_zone: { y1: 710, y2: 745 },
                            segments: watermarkConfig?.segments || [],
                          });
                        }
                      }}
                      className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      💾 保存配置
                    </button>
                    {onGeneratePreviewFrames && (
                      <button
                        onClick={onGeneratePreviewFrames}
                        className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors"
                      >
                        🖼️ 生成预览帧
                      </button>
                    )}
                  </div>

                  {previewFrames && previewFrames.length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">分段预览帧（{previewFrames.length}张）</h4>
                      <p className="text-xs text-gray-500 mb-2">每段的首帧，可拖动标注水印位置（轨迹点：时间t + 坐标x,y）</p>
                      <div className="grid grid-cols-5 gap-2">
                        {previewFrames.map((f, i) => (
                          <div key={i} className="border border-gray-200 rounded-lg p-1 bg-white text-center">
                            <img
                              src={`/api/v1/video-projects/${projectId}/watermark-preview/${encodeURIComponent(f.filename)}`}
                              alt={`Frame at ${f.time_seconds}s`}
                              className="w-full h-20 object-cover rounded bg-gray-100"
                              loading="lazy"
                              onError={(e) => {
                                (e.target as HTMLImageElement).style.display = "none";
                                const p = (e.target as HTMLImageElement).parentElement;
                                if (p) {
                                  const div = document.createElement("div");
                                  div.className = "bg-gray-100 rounded h-20 flex items-center justify-center text-xs text-gray-400";
                                  div.textContent = "❌";
                                  p.appendChild(div);
                                }
                              }}
                            />
                            <p className="text-[10px] text-gray-500 mt-1">{f.time_seconds.toFixed(1)}s</p>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-400 mt-2">💡 预览帧可用于标记水印位置，然后通过 API 配置轨迹点</p>
                    </div>
                  )}

                  {stage.output_asset && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">输出文件</h4>
                      <p className="text-sm text-gray-600">{stage.output_asset.filename}</p>
                      {stage.output_asset.file_size_bytes && (
                        <p className="text-xs text-gray-500">大小: {(stage.output_asset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</p>
                      )}
                    </div>
                  )}
                  {stage.error_log && (
                    <div className="mt-4 pt-4 border-t border-red-200">
                      <h4 className="text-sm font-medium text-red-700 mb-2">错误信息</h4>
                      <pre className="text-xs text-red-600 whitespace-pre-wrap bg-red-50 p-2 rounded">{stage.error_log}</pre>
                    </div>
                  )}
                </div>
              )}

              {/* Face Swap Config (expanded) */}
              {isExpanded && stage.stage_name === 'face_swap' && (
                <div className="border-t border-gray-100 px-4 py-3 bg-white rounded-b-xl">
                  <h4 className="text-sm font-semibold text-gray-700 mb-3">🔄 换脸参数配置</h4>

                  {/* Swap mode selector */}
                  <div className="mb-4">
                    <label className="block text-gray-600 mb-1 text-sm">换脸模式</label>
                    <div className="flex space-x-3">
                      <label className={`flex items-center px-4 py-2 rounded-lg border cursor-pointer text-sm ${
                        fsForm.swapMode === 'simple'
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 text-gray-600'
                      }`}>
                        <input type="radio" name="swapMode" value="simple"
                          checked={fsForm.swapMode === 'simple'}
                          onChange={() => setFsForm(f => ({...f, swapMode: 'simple'}))}
                          className="mr-2" />
                        简单模式<br/><span className="text-[10px] text-gray-400">单人换脸，一张源图</span>
                      </label>
                      <label className={`flex items-center px-4 py-2 rounded-lg border cursor-pointer text-sm ${
                        fsForm.swapMode === 'smart'
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-300 text-gray-600'
                      }`}>
                        <input type="radio" name="swapMode" value="smart"
                          checked={fsForm.swapMode === 'smart'}
                          onChange={() => setFsForm(f => ({...f, swapMode: 'smart'}))}
                          className="mr-2" />
                        智能模式<br/><span className="text-[10px] text-gray-400">多人身份匹配 (embedding)</span>
                      </label>
                    </div>
                  </div>

                  {fsForm.swapMode === 'smart' && (
                    <div className="space-y-4">
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-700">
                        💡 智能模式需要先运行 <code className="bg-amber-100 px-1 rounded">find_best_reference_frames.py</code>
                        对视频进行身份聚类，然后设置以下路径：
                      </div>

                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <label className="block text-gray-600 mb-1">Person 1 换脸源图路径</label>
                          <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
                            placeholder="/tmp/face_gen_p1_crop768.jpg"
                            value={fsForm.faceSrc1}
                            onChange={(e) => setFsForm(f => ({...f, faceSrc1: e.target.value}))} />
                        </div>
                        <div>
                          <label className="block text-gray-600 mb-1">Person 2 换脸源图路径</label>
                          <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
                            placeholder="/tmp/face_gen_p2_crop768.jpg"
                            value={fsForm.faceSrc2}
                            onChange={(e) => setFsForm(f => ({...f, faceSrc2: e.target.value}))} />
                        </div>
                        <div>
                          <label className="block text-gray-600 mb-1">Person 1 参考帧路径</label>
                          <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
                            placeholder="/tmp/young_ref.jpg"
                            value={fsForm.refFrame1}
                            onChange={(e) => setFsForm(f => ({...f, refFrame1: e.target.value}))} />
                        </div>
                        <div>
                          <label className="block text-gray-600 mb-1">Person 2 参考帧路径</label>
                          <input className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
                            placeholder="/tmp/older_ref.jpg"
                            value={fsForm.refFrame2}
                            onChange={(e) => setFsForm(f => ({...f, refFrame2: e.target.value}))} />
                        </div>
                      </div>
                    </div>
                  )}

                  {fsForm.swapMode === 'simple' && (
                    <div className="text-sm text-gray-500 bg-gray-50 rounded-lg p-3">
                      简单模式：上传一张参考人脸图，所有检测到的人脸均替换为该图。
                      请通过"上传参考人脸"按钮上传。
                    </div>
                  )}

                  {onSaveFaceSwapConfig && (
                    <div className="mt-4">
                      <button
                        onClick={() => {
                          if (fsForm.swapMode === 'smart') {
                            onSaveFaceSwapConfig({
                              swap_mode: 'smart',
                              swap_config: {
                                mode: 'multi',
                                source_faces: {
                                  person1: fsForm.faceSrc1,
                                  person2: fsForm.faceSrc2,
                                },
                                ref_frames: {
                                  person1: fsForm.refFrame1,
                                  person2: fsForm.refFrame2,
                                },
                                similarity_threshold: 0.35,
                              },
                            });
                          } else {
                            onSaveFaceSwapConfig({ swap_mode: 'simple' });
                          }
                        }}
                        className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        💾 保存换脸配置
                      </button>
                    </div>
                  )}

                  {stage.output_asset && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">输出文件</h4>
                      <p className="text-sm text-gray-600">{stage.output_asset.filename}</p>
                      {stage.output_asset.file_size_bytes && (
                        <p className="text-xs text-gray-500">大小: {(stage.output_asset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</p>
                      )}
                    </div>
                  )}
                  {stage.error_log && (
                    <div className="mt-4 pt-4 border-t border-red-200">
                      <h4 className="text-sm font-medium text-red-700 mb-2">错误信息</h4>
                      <pre className="text-xs text-red-600 whitespace-pre-wrap bg-red-50 p-2 rounded">{stage.error_log}</pre>
                    </div>
                  )}
                </div>
              )}

              {/* Dedup Config (expanded) */}
              {isExpanded && stage.stage_name === 'dedup' && (
                <div className="border-t border-gray-100 px-4 py-3 bg-white rounded-b-xl">
                  {dedupProgress && dedupProgress.status === 'processing' && (
                    <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                      <h4 className="text-sm font-semibold text-blue-700 mb-2">⏳ 去重处理中...</h4>
                      <div className="flex items-center mb-2">
                        <div className="flex-1 bg-blue-200 rounded-full h-4 overflow-hidden">
                          <div className="bg-blue-600 h-full rounded-full transition-all duration-500 ease-in-out"
                            style={{ width: `${Math.min(dedupProgress.progress || 0, 100)}%` }} />
                        </div>
                        <span className="ml-3 text-sm font-medium text-blue-700 min-w-[3rem] text-right">
                          {dedupProgress.progress || 0}%
                        </span>
                      </div>
                    </div>
                  )}

                  <h4 className="text-sm font-semibold text-gray-700 mb-3">✨ 去重参数配置</h4>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <label className="block text-gray-600 mb-1">饱和度 <span className="text-xs text-gray-400">({dedupForm.saturation.toFixed(2)})</span></label>
                      <input type="range" min="0.95" max="1.15" step="0.01" className="w-full"
                        value={dedupForm.saturation}
                        onChange={(e) => setDedupForm(f => ({...f, saturation: parseFloat(e.target.value)}))} />
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">亮度 <span className="text-xs text-gray-400">({dedupForm.brightness.toFixed(2)})</span></label>
                      <input type="range" min="0.95" max="1.05" step="0.01" className="w-full"
                        value={dedupForm.brightness}
                        onChange={(e) => setDedupForm(f => ({...f, brightness: parseFloat(e.target.value)}))} />
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">对比度 <span className="text-xs text-gray-400">({dedupForm.contrast.toFixed(2)})</span></label>
                      <input type="range" min="0.95" max="1.10" step="0.01" className="w-full"
                        value={dedupForm.contrast}
                        onChange={(e) => setDedupForm(f => ({...f, contrast: parseFloat(e.target.value)}))} />
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">速度微调 <span className="text-xs text-gray-400">({(dedupForm.speed_variation*100).toFixed(0)}%)</span></label>
                      <input type="range" min="0" max="0.10" step="0.005" className="w-full"
                        value={dedupForm.speed_variation}
                        onChange={(e) => setDedupForm(f => ({...f, speed_variation: parseFloat(e.target.value)}))} />
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">像素偏移</label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                        value={dedupForm.pixel_shift}
                        onChange={(e) => setDedupForm(f => ({...f, pixel_shift: parseInt(e.target.value)}))}>
                        <option value={0}>0px</option>
                        <option value={1}>1px</option>
                        <option value={2}>2px</option>
                        <option value={3}>3px</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-600 mb-1">噪音注入 <span className="text-xs text-gray-400">(×10⁻³)</span></label>
                      <input type="range" min="0" max="10" step="1" className="w-full"
                        value={Math.round(dedupForm.noise_level * 1000)}
                        onChange={(e) => setDedupForm(f => ({...f, noise_level: parseInt(e.target.value) / 1000}))} />
                    </div>
                  </div>

                  <div className="mt-4">
                    <button
                      onClick={() => {
                        if (onSaveDedupConfig) {
                          onSaveDedupConfig({
                            saturation: dedupForm.saturation,
                            brightness: dedupForm.brightness,
                            contrast: dedupForm.contrast,
                            speed_variation: dedupForm.speed_variation,
                            pixel_shift: dedupForm.pixel_shift,
                            noise_level: dedupForm.noise_level,
                          });
                        }
                      }}
                      className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      💾 保存去重配置
                    </button>
                  </div>

                  {stage.output_asset && (
                    <div className="mt-4 pt-4 border-t border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">输出文件</h4>
                      <p className="text-sm text-gray-600">{stage.output_asset.filename}</p>
                      {stage.output_asset.file_size_bytes && (
                        <p className="text-xs text-gray-500">大小: {(stage.output_asset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB</p>
                      )}
                    </div>
                  )}
                  {stage.error_log && (
                    <div className="mt-4 pt-4 border-t border-red-200">
                      <h4 className="text-sm font-medium text-red-700 mb-2">错误信息</h4>
                      <pre className="text-xs text-red-600 whitespace-pre-wrap bg-red-50 p-2 rounded">{stage.error_log}</pre>
                    </div>
                  )}
                </div>
              )}

              {/* Other stages: expanded details */}
              {isExpanded && stage.stage_name !== 'remove_watermark' && stage.stage_name !== 'dedup' && stage.stage_name !== 'face_swap' && stage.output_asset && (
                <div className="border-t border-gray-100 px-4 py-3 bg-gray-50 rounded-b-xl">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <h4 className="font-medium text-gray-700 mb-2">输出文件</h4>
                      <p className="text-gray-600">{stage.output_asset.filename}</p>
                      {stage.output_asset.file_size_bytes && (
                        <p className="text-gray-500">
                          大小: {(stage.output_asset.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                        </p>
                      )}
                      {stage.output_asset.duration_seconds && (
                        <p className="text-gray-500">
                          时长: {stage.output_asset.duration_seconds.toFixed(1)}s
                        </p>
                      )}
                    </div>
                    {stage.error_log && (
                      <div>
                        <h4 className="font-medium text-red-700 mb-2">错误信息</h4>
                        <pre className="text-xs text-red-600 whitespace-pre-wrap bg-red-50 p-2 rounded">
                          {stage.error_log}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Error summary for failed stages (collapsed) */}
              {!isExpanded && stage.status === 'failed' && stage.error_log && (
                <div className="border-t border-red-100 px-4 py-2 bg-red-50 rounded-b-xl">
                  <p className="text-xs text-red-600 truncate">{stage.error_log}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pipeline Summary */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <div className="flex items-center justify-between text-sm">
          <div className="flex space-x-6">
            <span>
              ✅ 完成: <strong className="text-green-600">{stages.filter((s) => s.status === 'completed').length}</strong>
            </span>
            <span>
              ⏳ 待执行: <strong className="text-gray-600">{stages.filter((s) => s.status === 'pending').length}</strong>
            </span>
            <span>
              ❌ 失败: <strong className="text-red-600">{stages.filter((s) => s.status === 'failed').length}</strong>
            </span>
          </div>
          <div className="text-gray-500">
            {currentStage !== null
              ? `当前: 第 ${currentStage + 1}/${stages.length} 阶段`
              : pipelineComplete
                ? '🎉 全部阶段已完成'
                : '待启动'}
          </div>
        </div>
      </div>
    </div>
  );
}
