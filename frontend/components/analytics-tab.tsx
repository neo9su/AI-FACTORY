'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { analyticsApi } from '@/lib/api'
import { type TopOpportunityItem } from '@/types/neurotrend'
import { EngagementBar } from '@/components/engagement-bar'

export function AnalyticsTab() {
  const [items, setItems] = useState<TopOpportunityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    analyticsApi
      .getTopOpportunities(20)
      .then(setItems)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-red-400 text-sm text-center py-12">⚠ {error}</div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-20 text-indigo-300">
        <p className="text-4xl mb-3">📊</p>
        <p>暂无参与度数据 — 等待用户互动后每小时自动更新</p>
      </div>
    )
  }

  // max values for relative bar sizing
  const maxComposite = Math.max(...items.map((i) => i.composite_score), 1)
  const maxViews = Math.max(...items.map((i) => i.total_views), 1)
  const maxPlays = Math.max(...items.map((i) => i.total_plays), 1)
  const maxDownloads = Math.max(...items.map((i) => i.total_downloads), 1)
  const maxTests = Math.max(...items.map((i) => i.total_test_completes), 1)

  return (
    <div className="space-y-4">
      {/* Table header */}
      <div className="grid grid-cols-12 gap-2 text-xs text-white/40 font-medium px-4">
        <span className="col-span-4">商机主题</span>
        <span className="col-span-2 text-right">综合评分</span>
        <span className="col-span-2 text-right">ROI</span>
        <span className="col-span-2 text-right">参与度</span>
        <span className="col-span-2 text-right">总浏览</span>
      </div>

      {items.map((item, idx) => (
        <div
          key={item.opportunity_id}
          className="bg-white/5 border border-white/10 rounded-xl p-4 hover:border-indigo-500/40 transition-colors"
        >
          {/* Row summary */}
          <div className="grid grid-cols-12 gap-2 items-center mb-3">
            <div className="col-span-4 flex items-center gap-2 min-w-0">
              <span className="text-white/30 text-sm font-bold w-5 shrink-0">
                #{idx + 1}
              </span>
              <Link
                href={`/opportunities/${item.opportunity_id}`}
                className="text-sm font-semibold text-white hover:text-indigo-300 transition-colors line-clamp-2"
              >
                {item.topic}
              </Link>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-emerald-400 font-bold text-sm">
                {item.composite_score.toFixed(2)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-indigo-300 text-sm">
                {item.roi_score.toFixed(1)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-amber-400 text-sm">
                {item.engagement_score.toFixed(2)}
              </span>
            </div>
            <div className="col-span-2 text-right">
              <span className="text-white/60 text-sm">
                {item.total_views.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Composite score bar */}
          <EngagementBar
            label="综合评分"
            value={Math.round(item.composite_score * 10)}
            maxValue={Math.round(maxComposite * 10)}
            colorClass="bg-gradient-to-r from-emerald-500 to-indigo-500"
            icon="🏆"
          />

          {/* Engagement breakdown */}
          <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-white/5">
            <EngagementBar
              label="浏览"
              value={item.total_views}
              maxValue={maxViews}
              colorClass="bg-blue-500"
              icon="👁"
            />
            <EngagementBar
              label="试听"
              value={item.total_plays}
              maxValue={maxPlays}
              colorClass="bg-purple-500"
              icon="🎵"
            />
            <EngagementBar
              label="下载"
              value={item.total_downloads}
              maxValue={maxDownloads}
              colorClass="bg-amber-500"
              icon="📥"
            />
            <EngagementBar
              label="测试完成"
              value={item.total_test_completes}
              maxValue={maxTests}
              colorClass="bg-rose-500"
              icon="✅"
            />
          </div>

          {/* Product count badge */}
          <div className="mt-2 text-xs text-white/30">
            {item.product_count} 个内容产品 ·{' '}
            参与度加成 +{item.engagement_boost.toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  )
}
