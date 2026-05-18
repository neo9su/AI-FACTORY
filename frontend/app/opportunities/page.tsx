'use client';

import { useEffect, useState, useCallback } from 'react';
import api from '@/lib/api';
import { OpportunityCard } from '@/components/opportunity-card';
import { type OpportunityReport, type TrendScanResponse } from '@/types/neurotrend';

export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<OpportunityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [sources, setSources] = useState<Record<string, boolean>>({
    reddit: true,
  });

  const fetchOpportunities = useCallback(async (): Promise<void> => {
    try {
      const response = await api.get<OpportunityReport[]>(
        '/opportunities?min_roi=0&limit=20',
      );
      setOpportunities(response.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载商机失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOpportunities();
  }, [fetchOpportunities]);

  const handleScan = async (): Promise<void> => {
    setScanning(true);
    setScanMessage(null);
    setError(null);

    const selectedSources = Object.entries(sources)
      .filter(([, checked]) => checked)
      .map(([src]) => src);

    if (selectedSources.length === 0) {
      setError('请至少选择一个数据源');
      setScanning(false);
      return;
    }

    try {
      const response = await api.post<TrendScanResponse>('/trends/scan', {
        sources: selectedSources,
        limit: 20,
      });
      const data = response.data;
      setScanMessage(data.message ?? '扫描已启动，稍后刷新查看结果');

      // If scan returns opportunities directly, merge them
      if (data.opportunities && data.opportunities.length > 0) {
        setOpportunities((prev) => {
          const existingIds = new Set(prev.map((o) => o.id));
          const newItems = data.opportunities!.filter(
            (o) => !existingIds.has(o.id),
          );
          return [...newItems, ...prev];
        });
      } else {
        // Otherwise re-fetch after a short delay
        setTimeout(() => {
          setLoading(true);
          fetchOpportunities();
        }, 3000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '扫描失败，请重试');
    } finally {
      setScanning(false);
    }
  };

  const toggleSource = (source: string): void => {
    setSources((prev) => ({ ...prev, [source]: !prev[source] }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-5 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              🧠 NeuroTrend — 商机发现引擎
            </h1>
            <p className="text-indigo-300 text-sm mt-1">
              分析社交趋势，挖掘高价值产品商机
            </p>
          </div>
          <a
            href="/"
            className="text-sm text-indigo-300 hover:text-white transition-colors"
          >
            ← 返回主页
          </a>
        </div>
      </div>

      {/* Controls */}
      <div className="container mx-auto px-4 py-6">
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 mb-8">
          <h2 className="text-sm font-semibold text-indigo-300 uppercase tracking-widest mb-4">
            扫描设置
          </h2>

          {/* Source checkboxes */}
          <div className="flex flex-wrap gap-4 mb-5">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                className="w-4 h-4 rounded accent-indigo-500"
                checked={sources.reddit ?? false}
                onChange={() => toggleSource('reddit')}
              />
              <span className="text-sm font-medium">
                <span className="mr-1">🟠</span> Reddit
              </span>
            </label>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <button
              onClick={handleScan}
              disabled={scanning}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed font-semibold text-sm transition-colors shadow-lg shadow-indigo-900/40"
            >
              {scanning ? (
                <>
                  <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                  扫描中…
                </>
              ) : (
                <>🔍 开始扫描</>
              )}
            </button>

            <button
              onClick={() => {
                setLoading(true);
                fetchOpportunities();
              }}
              disabled={loading}
              className="px-4 py-2.5 rounded-xl border border-white/20 hover:border-white/40 text-sm transition-colors disabled:opacity-50"
            >
              ↻ 刷新
            </button>

            {scanMessage && (
              <span className="text-sm text-emerald-400">{scanMessage}</span>
            )}
            {error && (
              <span className="text-sm text-red-400">⚠ {error}</span>
            )}
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-400" />
            <p className="text-indigo-300 text-sm">正在加载商机数据…</p>
          </div>
        ) : opportunities.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-center gap-6">
            <div className="text-6xl">🔭</div>
            <div>
              <h3 className="text-2xl font-bold text-white mb-2">
                暂无商机数据
              </h3>
              <p className="text-indigo-300 max-w-md mx-auto">
                点击「开始扫描」按钮，NeuroTrend 将自动抓取 Reddit
                等社交平台的热点趋势，并分析潜在的高 ROI 产品商机。
              </p>
            </div>
            <button
              onClick={handleScan}
              disabled={scanning}
              className="px-8 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 font-semibold text-sm transition-colors shadow-lg"
            >
              {scanning ? '扫描中…' : '🔍 立即开始扫描'}
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-indigo-300">
                共发现{' '}
                <span className="text-white font-bold">
                  {opportunities.length}
                </span>{' '}
                个商机
              </p>
            </div>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {opportunities.map((opp) => (
                <OpportunityCard key={opp.id} opportunity={opp} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
