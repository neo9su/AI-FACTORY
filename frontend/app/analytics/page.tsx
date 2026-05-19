import { AnalyticsTab } from '@/components/analytics-tab'

export default function AnalyticsPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-5 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              📊 热门商机排行榜
            </h1>
            <p className="text-indigo-300 text-sm mt-1">
              按真实用户互动数据重新排名的商机评分（每小时自动更新）
            </p>
          </div>
          <a
            href="/opportunities"
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 商机列表
          </a>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8">
        {/* Score formula explanation */}
        <div className="bg-white/5 border border-white/10 rounded-xl px-5 py-4 mb-8 text-sm text-white/60">
          <span className="text-white font-semibold mr-2">📐 综合评分公式:</span>
          <code className="text-emerald-400 font-mono">
            composite = roi_score × 0.6 + engagement_score × 0.4
          </code>
          <span className="ml-3">
            参与度 = views×40% + plays×30% + downloads×20% + test_completes×10%
          </span>
        </div>

        <AnalyticsTab />
      </div>
    </div>
  )
}
