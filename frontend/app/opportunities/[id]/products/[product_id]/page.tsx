'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import {
  type ContentProduct,
  type EbookMeta,
  type PersonalityTestMeta,
  type VideoScriptMeta,
} from '@/types/neurotrend';
import TTSPlayer from '@/components/tts-player';
import { useEngagement } from '@/lib/useEngagement';

// ─── Shared helpers ───────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold uppercase tracking-widest text-indigo-400 mb-3">
      {children}
    </h2>
  );
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white/5 border border-white/10 rounded-2xl p-5 ${className}`}>
      {children}
    </div>
  );
}

// ─── Ebook viewer ─────────────────────────────────────────────────────────────

function EbookViewer({ meta }: { meta: EbookMeta }) {
  const [expandedChapters, setExpandedChapters] = useState<Set<number>>(new Set());

  const toggleChapter = useCallback((num: number) => {
    setExpandedChapters((prev) => {
      const next = new Set(prev);
      if (next.has(num)) {
        next.delete(num);
      } else {
        next.add(num);
      }
      return next;
    });
  }, []);

  return (
    <div className="space-y-6">
      {/* Hero block */}
      <Card>
        <div className="space-y-2">
          <div className="flex flex-wrap items-start gap-3 justify-between">
            <div className="space-y-1 flex-1 min-w-0">
              <h1 className="text-2xl font-extrabold leading-snug">{meta.title}</h1>
              {meta.subtitle && (
                <p className="text-gray-400 text-base leading-snug">{meta.subtitle}</p>
              )}
            </div>
            <span className="flex-shrink-0 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-sm font-bold">
              💰 {meta.price_suggestion}
            </span>
          </div>
          {meta.tagline && (
            <p className="text-indigo-300 italic text-sm mt-2">「{meta.tagline}」</p>
          )}
        </div>
      </Card>

      {/* Sales headline */}
      <Card className="bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border-indigo-500/30">
        <SectionTitle>📣 销售页主标题</SectionTitle>
        <p className="text-xl font-extrabold text-white leading-snug">{meta.sales_page_headline}</p>
      </Card>

      {/* Marketing angles */}
      {meta.marketing_angles.length > 0 && (
        <Card>
          <SectionTitle>🎯 营销角度</SectionTitle>
          <ul className="space-y-2">
            {meta.marketing_angles.map((angle, idx) => (
              <li key={idx} className="flex items-start gap-3 text-sm text-gray-200">
                <span className="flex-shrink-0 font-bold text-indigo-400">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                {angle}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Chapters */}
      <Card>
        <SectionTitle>📚 章节目录</SectionTitle>
        <div className="space-y-2">
          {meta.chapters.map((ch) => (
            <div
              key={ch.number}
              className="rounded-xl border border-white/10 bg-white/5 overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors"
                onClick={() => ch.written && toggleChapter(ch.number)}
                disabled={!ch.written}
              >
                <span className="flex-shrink-0 text-xs font-bold text-indigo-400 w-6">
                  {ch.number}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm">{ch.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5 truncate">{ch.hook}</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {ch.written ? (
                    <span className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      ✓ 已写作
                    </span>
                  ) : (
                    <span className="text-xs text-gray-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full">
                      大纲
                    </span>
                  )}
                  {ch.written && (
                    <span className="text-xs text-indigo-400">
                      {expandedChapters.has(ch.number) ? '▲' : '▼'}
                    </span>
                  )}
                </div>
              </button>

              {ch.written && expandedChapters.has(ch.number) && ch.content && (
                <div className="px-4 pb-4 pt-1 border-t border-white/10">
                  <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {ch.content}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Intro sample */}
      {meta.intro_sample && (
        <Card>
          <SectionTitle>✍️ 开篇示例</SectionTitle>
          <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
            {meta.intro_sample}
          </p>
        </Card>
      )}
    </div>
  );
}

// ─── Personality Test viewer ──────────────────────────────────────────────────

function PersonalityTestViewer({ meta }: { meta: PersonalityTestMeta }) {
  const { test_data } = meta;

  const handlePreviewH5 = () => {
    const encoded = encodeURIComponent(meta.html_content);
    window.open(`data:text/html;charset=utf-8,${encoded}`, '_blank');
  };

  const previewQuestions = test_data.questions.slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 flex-1">
            <h1 className="text-2xl font-extrabold">{meta.title}</h1>
            {meta.tagline && (
              <p className="text-indigo-300 italic text-sm">「{meta.tagline}」</p>
            )}
          </div>
          <button
            onClick={handlePreviewH5}
            className="flex-shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 hover:opacity-90 text-sm font-semibold text-white transition-all"
          >
            📱 预览 H5
          </button>
        </div>
      </Card>

      {/* Viral hook */}
      {test_data.viral_hook && (
        <Card className="bg-gradient-to-br from-fuchsia-900/30 to-purple-900/30 border-fuchsia-500/30">
          <SectionTitle>🪡 传播钩子</SectionTitle>
          <p className="text-lg font-bold text-white leading-snug">{test_data.viral_hook}</p>
        </Card>
      )}

      {/* Question preview */}
      <Card>
        <SectionTitle>❓ 题目预览（前 3 题）</SectionTitle>
        <div className="space-y-5">
          {previewQuestions.map((q, qi) => (
            <div key={q.id} className="space-y-2">
              <p className="text-sm font-semibold text-white">
                <span className="text-indigo-400 mr-2">Q{qi + 1}.</span>
                {q.text}
              </p>
              <ul className="space-y-1.5 pl-6">
                {q.options.map((opt) => (
                  <li
                    key={opt.id}
                    className="text-xs text-gray-300 flex items-start gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                  >
                    <span className="font-bold text-indigo-400 flex-shrink-0">{opt.id}.</span>
                    {opt.text}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {test_data.questions.length > 3 && (
            <p className="text-xs text-gray-500 text-center">
              … 还有 {test_data.questions.length - 3} 道题，预览 H5 查看完整版
            </p>
          )}
        </div>
      </Card>

      {/* Result types */}
      <div>
        <SectionTitle>🏅 结果类型</SectionTitle>
        <div className="grid sm:grid-cols-2 gap-3">
          {test_data.result_types.map((rt) => (
            <div
              key={rt.id}
              className="rounded-xl border border-purple-500/20 bg-purple-500/10 p-4 space-y-1"
            >
              <div className="flex items-center gap-2">
                <span className="text-2xl">{rt.emoji}</span>
                <span className="font-bold text-sm">{rt.name}</span>
              </div>
              <p className="text-xs text-gray-300 leading-relaxed">{rt.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Video Scripts viewer ─────────────────────────────────────────────────────

function ViralPotentialBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 10)));
  const color =
    value >= 8 ? 'bg-emerald-500' : value >= 6 ? 'bg-indigo-500' : 'bg-orange-500';
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs text-gray-500">
        <span>传播潜力</span>
        <span className="font-bold text-white">{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/10">
        <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function VideoScriptsViewer({
  meta,
  opportunityId,
  productId,
  ttsStatus,
  ttsAudioUrls,
}: {
  meta: VideoScriptMeta
  opportunityId: string
  productId: string
  ttsStatus?: string | null
  ttsAudioUrls?: Array<{ script_id: number; script_title: string; url: string; lines_count: number }> | null
}) {
  return (
    <div className="space-y-6">
      {/* Series concept */}
      <Card>
        <SectionTitle>🎬 系列概念</SectionTitle>
        <h1 className="text-xl font-extrabold mb-2">{meta.title}</h1>
        <p className="text-gray-300 text-sm leading-relaxed">{meta.series_concept}</p>
        <div className="mt-3 text-xs text-indigo-400">
          共 {meta.scripts_count} 条脚本
        </div>
      </Card>

      {/* TTS Player */}
      <TTSPlayer
        opportunityId={opportunityId}
        productId={productId}
        initialTtsStatus={ttsStatus}
        initialAudioUrls={ttsAudioUrls}
      />

      {/* Script cards */}
      <div className="space-y-5">
        {meta.scripts.map((script, idx) => (
          <Card key={script.id}>
            {/* Script header */}
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="space-y-0.5 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold text-rose-400 uppercase tracking-widest">
                    #{idx + 1}
                  </span>
                  <span className="text-xs text-gray-500 bg-white/5 border border-white/10 px-2 py-0.5 rounded-full">
                    {script.format}
                  </span>
                  <span className="text-xs text-gray-500">
                    ⏱ {script.duration_seconds}s
                  </span>
                  {script.tts_suitable && (
                    <span className="text-xs font-medium text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded-full">
                      🎙 可配音
                    </span>
                  )}
                </div>
                <h3 className="font-bold text-base">{script.title}</h3>
              </div>
            </div>

            {/* Hook line */}
            <div className="rounded-xl bg-gradient-to-r from-rose-900/40 to-orange-900/30 border border-rose-500/20 px-4 py-3 mb-4">
              <p className="text-xs font-semibold text-rose-400 mb-1">🎣 开场钩子</p>
              <p className="text-base font-bold text-white leading-snug">{script.hook_line}</p>
            </div>

            {/* Storyboard */}
            <div className="space-y-2 mb-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">分镜</p>
              <div className="rounded-xl border border-white/10 overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/10 bg-white/5">
                      <th className="text-left px-3 py-2 text-gray-400 w-16">时间</th>
                      <th className="text-left px-3 py-2 text-gray-400">画面</th>
                      <th className="text-left px-3 py-2 text-gray-400">旁白</th>
                      <th className="text-left px-3 py-2 text-gray-400 w-20">情感</th>
                    </tr>
                  </thead>
                  <tbody>
                    {script.script.map((frame, fi) => (
                      <tr
                        key={fi}
                        className="border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors"
                      >
                        <td className="px-3 py-2 text-indigo-400 font-mono">{frame.timestamp}</td>
                        <td className="px-3 py-2 text-gray-300">{frame.visual}</td>
                        <td className="px-3 py-2 text-gray-200">{frame.narration}</td>
                        <td className="px-3 py-2 text-orange-300">{frame.emotion}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Caption */}
            {script.caption && (
              <div className="rounded-xl bg-white/5 border border-white/10 px-3 py-2 mb-4">
                <p className="text-xs text-gray-500 mb-1">📝 文案</p>
                <p className="text-sm text-gray-200">{script.caption}</p>
              </div>
            )}

            {/* Hashtags */}
            {script.hashtags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-4">
                {script.hashtags.map((tag) => (
                  <span
                    key={tag}
                    className="text-xs text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full"
                  >
                    {tag.startsWith('#') ? tag : `#${tag}`}
                  </span>
                ))}
              </div>
            )}

            {/* BGM + viral */}
            <div className="flex items-end justify-between gap-4">
              {script.bgm_style && (
                <p className="text-xs text-gray-400">
                  🎵 BGM: <span className="text-white">{script.bgm_style}</span>
                </p>
              )}
              <div className="flex-1 max-w-xs">
                <ViralPotentialBar value={script.viral_potential} />
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function ProductDetailPage() {
  const params = useParams();
  const opportunityId = params.id as string;
  const productId = params.product_id as string;

  const [product, setProduct] = useState<ContentProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { trackView } = useEngagement();

  useEffect(() => {
    api
      .get<ContentProduct[]>(`/opportunities/${opportunityId}/products`)
      .then((r) => {
        const found = r.data.find((p) => p.id === productId);
        if (found) {
          setProduct(found);
        } else {
          setError('产品不存在');
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : '加载失败'))
      .finally(() => setLoading(false));
  }, [opportunityId, productId]);

  // Track view on mount once product is loaded
  useEffect(() => {
    if (product?.id) {
      trackView(product.id, opportunityId, { referrer: document.referrer });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center gap-4 flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
          <p className="text-indigo-300 text-sm">正在加载产品…</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">⚠ {error ?? '产品不存在'}</p>
          <Link
            href={`/opportunities/${opportunityId}/products`}
            className="inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-500 transition-colors"
          >
            ← 返回产品列表
          </Link>
        </div>
      </div>
    );
  }

  if (product.status !== 'ready' || !product.meta) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-orange-400 text-lg">⏳ 产品尚未生成完成</p>
          <p className="text-gray-400 text-sm">当前状态：{product.status}</p>
          <Link
            href={`/opportunities/${opportunityId}/products`}
            className="inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-500 transition-colors"
          >
            ← 返回产品列表
          </Link>
        </div>
      </div>
    );
  }

  const meta = product.meta;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-3">
          <Link
            href="/opportunities"
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 商机列表
          </Link>
          <span className="text-white/20">/</span>
          <Link
            href={`/opportunities/${opportunityId}`}
            className="text-sm text-indigo-300 hover:text-white transition-colors truncate max-w-[8rem]"
          >
            商机详情
          </Link>
          <span className="text-white/20">/</span>
          <Link
            href={`/opportunities/${opportunityId}/products`}
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            产品列表
          </Link>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white/80 truncate max-w-xs">
            {product.title ?? '产品详情'}
          </span>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {meta.product_type === 'ebook' && <EbookViewer meta={meta as EbookMeta} />}
        {meta.product_type === 'personality_test' && (
          <PersonalityTestViewer meta={meta as PersonalityTestMeta} />
        )}
        {meta.product_type === 'short_video_scripts' && (
          <VideoScriptsViewer
            meta={meta as VideoScriptMeta}
            opportunityId={opportunityId}
            productId={productId}
            ttsStatus={product.tts_status}
            ttsAudioUrls={product.tts_audio_urls}
          />
        )}
      </div>
    </div>
  );
}
