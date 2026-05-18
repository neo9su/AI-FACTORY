'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import {
  type OpportunityReport,
  type ProductSuggestion,
  EMOTION_COLORS,
} from '@/types/neurotrend';

// ---------- helpers ----------

function EmotionTag({ emotion }: { emotion: string }) {
  const colorClass = EMOTION_COLORS[emotion.toLowerCase()] ?? 'bg-gray-500';
  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold text-white',
        colorClass,
      )}
    >
      {emotion.replace(/_/g, ' ')}
    </span>
  );
}

function MiniScoreBar({
  label,
  value,
  color = 'bg-indigo-500',
}: {
  label: string;
  value: number;
  color?: string;
}) {
  const pct = Math.min(100, Math.max(0, Math.round(value * 10)));
  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-xs text-gray-500">
        <span>{label}</span>
        <span className="font-bold text-gray-700">{value.toFixed(1)}</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-100">
        <div
          className={cn('h-1.5 rounded-full transition-all', color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ProductCard({ product }: { product: ProductSuggestion }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow p-5 flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-bold text-gray-900 text-base leading-snug flex-1">
          {product.title}
        </h3>
        <span className="flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-md bg-indigo-100 text-indigo-700 text-xs font-semibold">
          {product.type}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 line-clamp-3">{product.description}</p>

      {/* Meta row */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        <span>
          💰 <span className="font-medium text-gray-700">{product.price_range}</span>
        </span>
        <span>
          ⏱ <span className="font-medium text-gray-700">{product.time_to_build}</span>
        </span>
        <span>
          👤 <span className="font-medium text-gray-700">{product.target_user}</span>
        </span>
      </div>

      {/* Scores */}
      <div className="space-y-1.5 pt-1">
        <MiniScoreBar label="ROI 评分" value={product.roi_score} color="bg-emerald-500" />
        <MiniScoreBar
          label="自动化评分"
          value={product.automation_score}
          color="bg-indigo-500"
        />
        <MiniScoreBar
          label="传播评分"
          value={product.viral_score}
          color="bg-pink-500"
        />
      </div>

      {/* Why it works */}
      <div className="rounded-lg bg-amber-50 border border-amber-100 px-3 py-2">
        <p className="text-xs text-amber-700 font-semibold mb-0.5">为什么有效</p>
        <p className="text-xs text-amber-800 line-clamp-3">{product.why_this_works}</p>
      </div>

      {/* Composite score badge */}
      {product.composite_score !== undefined && (
        <div className="self-start inline-flex items-center gap-1 text-xs font-bold text-white bg-gradient-to-r from-indigo-500 to-purple-600 px-2.5 py-0.5 rounded-full">
          ⭐ 综合分 {product.composite_score.toFixed(1)}
        </div>
      )}
    </div>
  );
}

// ---------- main page ----------

export default function OpportunityDetailPage() {
  const params = useParams();
  const opportunityId = params.id as string;

  const [opportunity, setOpportunity] = useState<OpportunityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOpportunity = async (): Promise<void> => {
      try {
        const response = await api.get<OpportunityReport>(
          `/opportunities/${opportunityId}`,
        );
        setOpportunity(response.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载商机详情失败');
      } finally {
        setLoading(false);
      }
    };
    fetchOpportunity();
  }, [opportunityId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center gap-4 flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
          <p className="text-indigo-300 text-sm">正在加载商机详情…</p>
        </div>
      </div>
    );
  }

  if (error || !opportunity) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">⚠ {error ?? '商机不存在'}</p>
          <Link
            href="/opportunities"
            className="inline-block px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-500 transition-colors"
          >
            ← 返回商机列表
          </Link>
        </div>
      </div>
    );
  }

  const sortedProducts = [...opportunity.product_suggestions].sort(
    (a, b) =>
      (b.composite_score ?? b.roi_score) - (a.composite_score ?? a.roi_score),
  );

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
          <span className="text-sm text-white/60 truncate max-w-xs">
            {opportunity.topic}
          </span>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-5xl space-y-8">
        {/* Hero section */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-6 space-y-4">
          <h1 className="text-3xl font-extrabold tracking-tight leading-snug">
            {opportunity.topic}
          </h1>

          {/* Overall scores */}
          <div className="flex flex-wrap gap-4">
            <div className="flex flex-col items-center bg-emerald-500/20 border border-emerald-500/30 rounded-xl px-5 py-3">
              <span className="text-2xl font-black text-emerald-300">
                {opportunity.roi_score.toFixed(1)}
              </span>
              <span className="text-xs text-emerald-400 mt-0.5">ROI 评分</span>
            </div>
            <div className="flex flex-col items-center bg-indigo-500/20 border border-indigo-500/30 rounded-xl px-5 py-3">
              <span className="text-2xl font-black text-indigo-300">
                {opportunity.automation_score.toFixed(1)}
              </span>
              <span className="text-xs text-indigo-400 mt-0.5">自动化评分</span>
            </div>
            {opportunity.lifecycle && (
              <div className="flex flex-col items-center bg-purple-500/20 border border-purple-500/30 rounded-xl px-5 py-3">
                <span className="text-base font-bold text-purple-300">
                  {opportunity.lifecycle}
                </span>
                <span className="text-xs text-purple-400 mt-0.5">生命周期</span>
              </div>
            )}
            {opportunity.seo_value && (
              <div className="flex flex-col items-center bg-yellow-500/20 border border-yellow-500/30 rounded-xl px-5 py-3">
                <span className="text-base font-bold text-yellow-300">
                  {opportunity.seo_value}
                </span>
                <span className="text-xs text-yellow-400 mt-0.5">SEO 价值</span>
              </div>
            )}
          </div>

          {/* Why viral */}
          <div>
            <h2 className="text-xs font-semibold text-indigo-400 uppercase tracking-widest mb-2">
              🔥 为什么会火
            </h2>
            <p className="text-gray-200 leading-relaxed">{opportunity.why_viral}</p>
          </div>
        </div>

        {/* Emotions & Pain points */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Core emotions */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
            <h2 className="text-xs font-semibold text-pink-400 uppercase tracking-widest">
              💢 核心情绪触发
            </h2>
            <div className="flex flex-wrap gap-2">
              {opportunity.core_emotions.map((emotion) => (
                <EmotionTag key={emotion} emotion={emotion} />
              ))}
            </div>
          </div>

          {/* Core pain points */}
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-3">
            <h2 className="text-xs font-semibold text-orange-400 uppercase tracking-widest">
              🩹 核心痛点
            </h2>
            <ul className="space-y-1.5">
              {opportunity.core_pain_points.map((pain, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-gray-200">
                  <span className="text-orange-400 mt-0.5 flex-shrink-0">•</span>
                  {pain}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Willingness to pay */}
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 space-y-2">
          <h2 className="text-xs font-semibold text-green-400 uppercase tracking-widest">
            💳 用户付费心理触发点
          </h2>
          <p className="text-gray-200 leading-relaxed">{opportunity.willingness_to_pay}</p>
        </div>

        {/* Product suggestions */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold">
              🛠 产品建议
              <span className="ml-2 text-sm font-normal text-indigo-300">
                ({sortedProducts.length} 个，按综合分排序)
              </span>
            </h2>

            <button
              onClick={() => alert('Phase 3 即将接入：AI 自动生成产品！')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-sm font-semibold transition-colors shadow-lg"
            >
              🚀 生成产品
            </button>
          </div>

          {sortedProducts.length === 0 ? (
            <div className="text-center py-12 text-indigo-300 text-sm">
              暂无产品建议
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {sortedProducts.map((product, idx) => (
                <ProductCard key={idx} product={product} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
