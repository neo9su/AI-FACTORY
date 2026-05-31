'use client';

import { useState } from 'react';
import type { ContentProduct, EbookMeta, PersonalityTestMeta, VideoScriptMeta } from '@/types/neurotrend';
import PublishDialog from './publish-dialog';

interface Props {
  product: ContentProduct;
}

// ─── Emoji per type ───────────────────────────────────────────────────────

const TYPE_ICON: Record<string, string> = {
  personality_test: '🧪',
  ebook: '📖',
  short_video_scripts: '🎬',
};

const TYPE_LABEL: Record<string, string> = {
  personality_test: '人格测试',
  ebook: '电子书',
  short_video_scripts: '短视频脚本',
};

// ─── Status badge ─────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending: { label: '等待中', cls: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30' },
    generating: { label: '生成中…', cls: 'bg-blue-500/20 text-blue-300 border-blue-500/30 animate-pulse' },
    ready: { label: '✅ 已就绪', cls: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
    failed: { label: '❌ 失败', cls: 'bg-red-500/20 text-red-300 border-red-500/30' },
  };
  const s = map[status] ?? map.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${s.cls}`}>
      {s.label}
    </span>
  );
}

// ─── Content previews ─────────────────────────────────────────────────────

function PersonalityTestView({ meta }: { meta: PersonalityTestMeta }) {
  const td = meta.test_data!;
  return (
    <div className="space-y-4">
      <p className="text-indigo-200 text-sm font-medium">{meta.tagline}</p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {td.result_types?.map((r) => (
          <div key={r.id} className="bg-white/5 border border-white/10 rounded-xl p-3 text-center">
            <span className="text-2xl block mb-1">{r.emoji}</span>
            <p className="text-xs font-bold text-white">{r.name}</p>
            <p className="text-[10px] text-gray-400 mt-0.5 line-clamp-2">{r.description}</p>
          </div>
        ))}
      </div>

      <details className="group">
        <summary className="cursor-pointer text-xs text-indigo-400 hover:text-indigo-300 font-medium">
          预览题目（{td.questions?.length ?? 0} 题）
        </summary>
        <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
          {td.questions?.slice(0, 5).map((q) => (
            <div key={q.id} className="bg-white/5 rounded-lg p-2 text-xs">
              <p className="text-white font-medium mb-1">Q{q.id}. {q.text}</p>
              <div className="flex flex-wrap gap-1">
                {q.options.map((o) => (
                  <span key={o.id} className="px-1.5 py-0.5 bg-white/10 rounded text-gray-300">{o.text.slice(0, 15)}</span>
                ))}
              </div>
            </div>
          ))}
          {(td.questions?.length ?? 0) > 5 && (
            <p className="text-[10px] text-gray-500 text-center">…还有 {td.questions!.length - 5} 题</p>
          )}
        </div>
      </details>

      <div className="flex gap-2">
        <a
          href={`data:text/html;charset=utf-8,${encodeURIComponent(meta.html_content)}`}
          download={`${meta.title}.html`}
          className="flex-1 text-center px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors"
        >
          ⬇ 下载 HTML 文件
        </a>
      </div>
    </div>
  );
}

function EbookView({ meta }: { meta: EbookMeta }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-indigo-200 font-medium">{meta.subtitle}</p>
      <p className="text-xs text-gray-400 italic">{meta.tagline}</p>

      {/* Chapters */}
      <div className="space-y-2">
        {meta.chapters?.map((ch) => (
          <div key={ch.number} className="bg-white/5 border border-white/10 rounded-xl p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold text-indigo-300">第{ch.number}章</span>
              <span className="text-xs text-gray-400">·</span>
              <span className="text-sm font-semibold text-white">{ch.title}</span>
              {ch.written && <span className="text-[10px] text-emerald-400">✅ 已写</span>}
            </div>
            <p className="text-xs text-gray-400">{ch.hook}</p>
            {ch.content && (
              <details className="mt-1">
                <summary className="cursor-pointer text-[10px] text-indigo-400 hover:text-indigo-300">
                  阅读全文
                </summary>
                <p className="mt-1 text-xs text-gray-300 leading-relaxed whitespace-pre-wrap max-h-32 overflow-y-auto">
                  {ch.content.slice(0, 500)}
                  {ch.content.length > 500 && '…'}
                </p>
              </details>
            )}
          </div>
        ))}
      </div>

      {/* Marketing */}
      <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
        <p className="text-xs font-bold text-amber-300 mb-1">📢 销售页标题</p>
        <p className="text-sm text-gray-200">{meta.sales_page_headline}</p>
        <p className="text-xs text-gray-400 mt-2">营销角度: {meta.marketing_angles?.join(' · ')}</p>
      </div>
    </div>
  );
}

function VideoScriptView({ meta }: { meta: VideoScriptMeta }) {
  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-400">{meta.series_concept}</p>

      <div className="space-y-3">
        {meta.scripts?.map((s) => (
          <div key={s.id} className="bg-white/5 border border-white/10 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-sm font-bold text-white">#{s.id} {s.title}</p>
              <div className="flex items-center gap-2 text-[10px] text-gray-400">
                <span>⏱ {s.duration_seconds}s</span>
                <span className={`px-1.5 py-0.5 rounded ${s.tts_suitable ? 'bg-emerald-500/20 text-emerald-300' : 'bg-gray-500/20 text-gray-400'}`}>
                  {s.tts_suitable ? '🎤 TTS' : '需要真人'}
                </span>
              </div>
            </div>

            <p className="text-xs text-pink-300 font-medium italic">&ldquo;{s.hook_line}&rdquo;</p>

            {/* Script scene-by-scene */}
            <details>
              <summary className="cursor-pointer text-[10px] text-indigo-400 hover:text-indigo-300">
                查看脚本（{s.script?.length ?? 0} 镜）
              </summary>
              <div className="mt-1 space-y-1">
                {s.script?.map((scene, i) => (
                  <div key={i} className="grid grid-cols-[40px_1fr_1fr_50px] gap-1 text-[10px] bg-white/5 rounded p-1.5">
                    <span className="text-gray-500">{scene.timestamp}</span>
                    <span className="text-gray-300 truncate">{scene.visual}</span>
                    <span className="text-gray-200 truncate">{scene.narration}</span>
                    <span className="text-gray-400 text-right">{scene.emotion}</span>
                  </div>
                ))}
              </div>
            </details>

            <div className="flex flex-wrap gap-1">
              {s.hashtags?.map((tag) => (
                <span key={tag} className="text-[10px] text-indigo-300">#{tag}</span>
              ))}
            </div>

            {s.caption && (
              <p className="text-[10px] text-gray-400 italic line-clamp-1">📝 {s.caption}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────

export default function GeneratedProductCard({ product }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [showPublish, setShowPublish] = useState(false);

  const icon = TYPE_ICON[product.product_type] ?? '📦';
  const label = TYPE_LABEL[product.product_type] ?? product.product_type;

  return (
    <>
      <div className="bg-white/5 border border-white/10 rounded-xl hover:border-indigo-500/50 transition-colors">
        {/* Header bar */}
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-xl">{icon}</span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">
                {product.title ?? `${label} #${product.id.slice(0, 6)}`}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] text-gray-500">{label}</span>
                <StatusBadge status={product.status} />
                {product.tts_status && (
                  <span className="text-[10px] text-gray-500">
                    TTS: {product.tts_status === 'ready' ? '✅' : product.tts_status === 'failed' ? '❌' : '⏳'}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {product.status === 'ready' && (
              <>
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="px-3 py-1.5 rounded-lg border border-white/20 hover:border-white/40 text-xs text-white/70 hover:text-white transition-colors"
                >
                  {expanded ? '收起' : '查看内容'}
                </button>
                <button
                  onClick={() => setShowPublish(true)}
                  className="px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-500 hover:to-green-500 text-xs font-semibold text-white transition-colors"
                >
                  🚀 发布
                </button>
              </>
            )}
            {product.status === 'generating' && (
              <span className="text-xs text-blue-300 animate-pulse">AI 生成中…</span>
            )}
            {product.status === 'failed' && (
              <span className="text-xs text-red-400">生成失败</span>
            )}
          </div>
        </div>

        {/* Expanded content */}
        {expanded && product.meta && product.status === 'ready' && (
          <div className="border-t border-white/10 px-4 py-4">
            {product.product_type === 'personality_test' && (
              <PersonalityTestView meta={product.meta as PersonalityTestMeta} />
            )}
            {product.product_type === 'ebook' && (
              <EbookView meta={product.meta as EbookMeta} />
            )}
            {product.product_type === 'short_video_scripts' && (
              <VideoScriptView meta={product.meta as VideoScriptMeta} />
            )}
          </div>
        )}
      </div>

      {showPublish && (
        <PublishDialog
          product={product}
          onClose={() => setShowPublish(false)}
        />
      )}
    </>
  );
}
