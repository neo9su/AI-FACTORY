'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { type OpportunityReport, type ContentProduct } from '@/types/neurotrend';

// ─── Types ────────────────────────────────────────────────────────────────────

type ProductType = 'ebook' | 'personality_test' | 'short_video_scripts';

interface GenerateProductResponse {
  product_id: string;
  job_id: string;
  status: string;
}

// ─── Product type config ──────────────────────────────────────────────────────

const PRODUCT_TYPES: Array<{
  type: ProductType;
  icon: string;
  name: string;
  description: string;
  estimatedTime: string;
  color: string;
  gradient: string;
}> = [
  {
    type: 'ebook',
    icon: '📖',
    name: '电子书',
    description: '完整章节结构 + 营销文案 + 销售页标题',
    estimatedTime: '约 2-3 分钟',
    color: 'border-indigo-500/40 bg-indigo-500/10',
    gradient: 'from-indigo-600 to-blue-600',
  },
  {
    type: 'personality_test',
    icon: '🧠',
    name: '人格测试',
    description: '互动测题 + 结果类型 + 可嵌入 H5 页面',
    estimatedTime: '约 1-2 分钟',
    color: 'border-purple-500/40 bg-purple-500/10',
    gradient: 'from-purple-600 to-pink-600',
  },
  {
    type: 'short_video_scripts',
    icon: '🎬',
    name: '短视频脚本',
    description: '多条完整分镜脚本 + 话题标签 + 传播评分',
    estimatedTime: '约 1-2 分钟',
    color: 'border-rose-500/40 bg-rose-500/10',
    gradient: 'from-rose-600 to-orange-600',
  },
];

// ─── Status indicator ─────────────────────────────────────────────────────────

function StatusDot({ status }: { status: ContentProduct['status'] }) {
  if (status === 'pending') {
    return <span className="inline-block w-2.5 h-2.5 rounded-full bg-gray-400 flex-shrink-0" />;
  }
  if (status === 'generating') {
    return (
      <span className="inline-block w-2.5 h-2.5 rounded-full bg-orange-400 flex-shrink-0 animate-pulse" />
    );
  }
  if (status === 'ready') {
    return <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400 flex-shrink-0" />;
  }
  // failed
  return <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-400 flex-shrink-0" />;
}

const STATUS_LABEL: Record<ContentProduct['status'], string> = {
  pending: '排队中',
  generating: 'AI 生成中…',
  ready: '已生成',
  failed: '生成失败',
};

const PRODUCT_TYPE_LABEL: Record<ProductType, string> = {
  ebook: '电子书',
  personality_test: '人格测试',
  short_video_scripts: '短视频脚本',
};

const PRODUCT_TYPE_ICON: Record<ProductType, string> = {
  ebook: '📖',
  personality_test: '🧠',
  short_video_scripts: '🎬',
};

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ProductsPage() {
  const params = useParams();
  const opportunityId = params.id as string;

  const [opportunity, setOpportunity] = useState<OpportunityReport | null>(null);
  const [products, setProducts] = useState<ContentProduct[]>([]);
  const [loadingPage, setLoadingPage] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<Set<ProductType>>(new Set());

  // ── fetch opportunity once
  useEffect(() => {
    api
      .get<OpportunityReport>(`/opportunities/${opportunityId}`)
      .then((r) => setOpportunity(r.data))
      .catch((e) => setPageError(e instanceof Error ? e.message : '加载商机失败'))
      .finally(() => setLoadingPage(false));
  }, [opportunityId]);

  // ── poll products every 5 s
  const fetchProducts = useCallback(() => {
    api
      .get<ContentProduct[]>(`/opportunities/${opportunityId}/products`)
      .then((r) => setProducts(r.data))
      .catch(() => {
        // silently ignore polling errors
      });
  }, [opportunityId]);

  useEffect(() => {
    fetchProducts();
    const id = setInterval(fetchProducts, 5000);
    return () => clearInterval(id);
  }, [fetchProducts]);

  // ── generate handler
  const handleGenerate = async (productType: ProductType) => {
    if (generating.has(productType)) return;
    setGenerating((prev) => new Set(prev).add(productType));
    try {
      await api.post<GenerateProductResponse>(
        `/opportunities/${opportunityId}/generate-product`,
        { product_type: productType },
      );
      // immediately refresh list
      fetchProducts();
    } catch (e) {
      alert(e instanceof Error ? e.message : '生成失败，请重试');
    } finally {
      setGenerating((prev) => {
        const next = new Set(prev);
        next.delete(productType);
        return next;
      });
    }
  };

  // ─── Loading / Error states ────────────────────────────────────────────────

  if (loadingPage) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center gap-4 flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
          <p className="text-indigo-300 text-sm">正在加载…</p>
        </div>
      </div>
    );
  }

  if (pageError || !opportunity) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">⚠ {pageError ?? '商机不存在'}</p>
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

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-3">
          <Link
            href={`/opportunities/${opportunityId}`}
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 商机详情
          </Link>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white/60 truncate max-w-xs">{opportunity.topic}</span>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white/80">产品生成</span>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-4xl space-y-10">
        {/* Hero */}
        <div className="space-y-1">
          <h1 className="text-2xl font-extrabold tracking-tight">🚀 AI 产品生成</h1>
          <p className="text-gray-400 text-sm">
            基于商机「{opportunity.topic}」一键生成可商用内容产品
          </p>
        </div>

        {/* Generate buttons */}
        <div className="grid sm:grid-cols-3 gap-4">
          {PRODUCT_TYPES.map((pt) => {
            const isGenerating = generating.has(pt.type);
            return (
              <div
                key={pt.type}
                className={`rounded-2xl border p-5 flex flex-col gap-4 ${pt.color}`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{pt.icon}</span>
                  <div>
                    <h3 className="font-bold text-base">{pt.name}</h3>
                    <p className="text-xs text-gray-400">{pt.estimatedTime}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-300 leading-relaxed flex-1">{pt.description}</p>
                <button
                  onClick={() => handleGenerate(pt.type)}
                  disabled={isGenerating}
                  className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all bg-gradient-to-r ${pt.gradient} hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed`}
                >
                  {isGenerating ? (
                    <>
                      <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                      AI 生成中…
                    </>
                  ) : (
                    <>✨ 立即生成</>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Products list */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white/90">
            📦 已生成产品
            {products.length > 0 && (
              <span className="ml-2 text-sm font-normal text-indigo-300">
                ({products.length} 个)
              </span>
            )}
          </h2>

          {products.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 py-12 text-center text-gray-400 text-sm">
              暂无产品 — 点击上方按钮生成第一个内容产品
            </div>
          ) : (
            <ul className="space-y-3">
              {products.map((product) => (
                <li
                  key={product.id}
                  className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 flex items-center gap-4"
                >
                  {/* Cover thumbnail or type icon */}
                  {product.cover_image_url ? (
                    <div className="flex-shrink-0 w-12 h-12 rounded-xl overflow-hidden border border-white/10">
                      <img
                        src={product.cover_image_url}
                        alt={product.title ?? '封面'}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <span className="text-2xl flex-shrink-0">
                      {PRODUCT_TYPE_ICON[product.product_type]}
                    </span>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                        {PRODUCT_TYPE_LABEL[product.product_type]}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(product.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    <p className="font-medium text-sm mt-0.5 truncate">
                      {product.title ?? '生成中…'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <StatusDot status={product.status} />
                    <span
                      className={`text-xs font-medium ${
                        product.status === 'ready'
                          ? 'text-emerald-400'
                          : product.status === 'failed'
                            ? 'text-red-400'
                            : product.status === 'generating'
                              ? 'text-orange-400'
                              : 'text-gray-400'
                      }`}
                    >
                      {STATUS_LABEL[product.status]}
                    </span>
                  </div>

                  {product.status === 'ready' && (
                    <Link
                      href={`/opportunities/${opportunityId}/products/${product.id}`}
                      className="flex-shrink-0 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors"
                    >
                      查看详情 →
                    </Link>
                  )}

                  {product.status === 'failed' && (
                    <span className="flex-shrink-0 text-xs text-red-400 bg-red-500/10 border border-red-500/20 px-3 py-1.5 rounded-lg">
                      ✗ 生成失败
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
