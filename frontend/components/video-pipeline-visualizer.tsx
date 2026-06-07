'use client';

import { useState } from 'react';
import type { VideoPipelineStage } from '@/lib/api';

interface PipelineVisualizerProps {
  stages: VideoPipelineStage[];
  currentStage: number | null;
  onRunStage: (stageName: string) => void;
  onStartPipeline: () => void;
  running: boolean;
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
    desc: '精准人脸替换，自然无违和',
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
}: PipelineVisualizerProps) {
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

              {/* Expanded Details */}
              {isExpanded && stage.output_asset && (
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
