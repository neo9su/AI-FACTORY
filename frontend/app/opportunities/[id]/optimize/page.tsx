'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';

interface ProductPerformance {
  product_id: string;
  product_type: string;
  performance_grade: string;
  hook_retention_rate: number;
  angle_click_rate: number;
  engagement_efficiency: number;
  recommendation: string | null;
}

interface OptimizationReport {
  opportunity_id: string;
  total_products: number;
  grade_distribution: Record<string, number>;
  average_engagement_efficiency: number;
  top_recommendations: string[];
  products: ProductPerformance[];
}

function GradeBadge({ grade }: { grade: string }) {
  const colors: Record<string, string> = {
    S: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    A: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    B: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    C: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    D: 'bg-red-500/20 text-red-300 border-red-500/30',
  };
  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-bold border ${colors[grade] || colors.D}`}
    >
      {grade}
    </span>
  );
}

function GradeBar({ grades }: { grades: Record<string, number> }) {
  const order = ['S', 'A', 'B', 'C', 'D'];
  const total = Object.values(grades).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="flex h-3 rounded-full overflow-hidden">
      {order.map((g) => {
        const pct = ((grades[g] || 0) / total) * 100;
        if (pct === 0) return null;
        const colors: Record<string, string> = {
          S: 'bg-yellow-500',
          A: 'bg-emerald-500',
          B: 'bg-blue-500',
          C: 'bg-orange-500',
          D: 'bg-red-500',
        };
        return (
          <div
            key={g}
            className={colors[g]}
            style={{ width: `${pct}%` }}
            title={`${g}: ${grades[g] || 0}`}
          />
        );
      })}
    </div>
  );
}

export default function OptimizePage() {
  const params = useParams();
  const oppId = params.id as string;
  const [report, setReport] = useState<OptimizationReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get(`/optimizer/opportunities/${oppId}/report`)
      .then((r) => setReport(r.data))
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [oppId]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      {/* Top bar */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center gap-3">
          <Link
            href={`/opportunities/${oppId}`}
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 返回商机详情
          </Link>
          <span className="text-white/20">/</span>
          <span className="text-sm text-white/80">优化看板</span>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-5xl">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
          </div>
        ) : report ? (
          <div className="space-y-8">
            {/* Overview */}
            <div className="rounded-2xl bg-gradient-to-br from-indigo-900/40 to-purple-900/40 border border-indigo-500/30 p-6">
              <h1 className="text-xl font-bold mb-4">📊 优化总览</h1>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">产品总数</p>
                  <p className="text-2xl font-extrabold">{report.total_products}</p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">平均互动效率</p>
                  <p className="text-2xl font-extrabold">
                    {report.average_engagement_efficiency}%
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-gray-400">S 级产品</p>
                  <p className="text-2xl font-extrabold text-yellow-300">
                    {report.grade_distribution.S || 0}
                  </p>
                </div>
              </div>
              <GradeBar grades={report.grade_distribution} />
              <div className="flex gap-2 mt-2 text-xs text-gray-500">
                {Object.entries(report.grade_distribution).map(([g, c]) =>
                  c > 0 ? (
                    <span key={g} className="flex items-center gap-1">
                      <GradeBadge grade={g} /> {c}
                    </span>
                  ) : null
                )}
              </div>
            </div>

            {/* Product performance table */}
            <div className="space-y-4">
              <h2 className="text-sm font-bold text-indigo-300 uppercase tracking-wider">
                产品表现
              </h2>
              {report.products.map((p) => (
                <div
                  key={p.product_id}
                  className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-3 hover:bg-white/[0.07] transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">
                        {p.product_type}
                      </span>
                      <GradeBadge grade={p.performance_grade} />
                    </div>
                    <Link
                      href={`/opportunities/${oppId}/products/${p.product_id}`}
                      className="text-xs text-indigo-400 hover:text-indigo-300"
                    >
                      查看 →
                    </Link>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-xs">
                    <div>
                      <span className="text-gray-400">完播率</span>
                      <p className="font-bold">{p.hook_retention_rate}/10</p>
                    </div>
                    <div>
                      <span className="text-gray-400">点击率</span>
                      <p className="font-bold">{p.angle_click_rate}/10</p>
                    </div>
                    <div>
                      <span className="text-gray-400">互动效率</span>
                      <p className="font-bold">{p.engagement_efficiency}%</p>
                    </div>
                  </div>

                  {p.recommendation && (
                    <p className="text-xs text-indigo-200 italic">
                      💡 {p.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Recommendations */}
            {report.top_recommendations.length > 0 && (
              <div className="rounded-xl bg-gradient-to-br from-amber-900/20 to-orange-900/20 border border-amber-500/20 p-4">
                <h2 className="text-sm font-bold text-amber-300 mb-3">
                  💡 优化建议汇总
                </h2>
                <ul className="space-y-2">
                  {report.top_recommendations.map((rec, i) => (
                    <li
                      key={i}
                      className="text-xs text-gray-200 flex items-start gap-2"
                    >
                      <span className="text-amber-400">{i + 1}.</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-400">暂无优化数据</p>
            <p className="text-xs text-gray-500 mt-2">
              发布产品并产生互动后，这里会显示分析结果
            </p>
            <Link
              href={`/opportunities/${oppId}/products`}
              className="inline-block mt-4 px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm"
            >
              去生成产品
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
