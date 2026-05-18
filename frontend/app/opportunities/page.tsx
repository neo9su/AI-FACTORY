'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import api from '@/lib/api';
import { OpportunityCard } from '@/components/opportunity-card';
import {
  type OpportunityReport,
  type TrendScanResponse,
  type TrendScanJob,
} from '@/types/neurotrend';

// ---------- 数据源配置 ----------
interface SourceOption {
  value: string
  label: string
  emoji: string
}

const SOURCE_OPTIONS: SourceOption[] = [
  { value: 'reddit',              label: 'Reddit (通用)',       emoji: '🔴' },
  { value: 'reddit_mbti',         label: 'MBTI/人格',           emoji: '💭' },
  { value: 'reddit_healing',      label: '情绪疗愈',            emoji: '💚' },
  { value: 'reddit_sidehustle',   label: '副业赚钱',            emoji: '💰' },
  { value: 'huggingface',         label: 'HuggingFace (AI趋势)', emoji: '🤖' },
];

// ---------- Tab 过滤配置 ----------
type FilterTab = 'all' | 'roi8' | 'roi7' | 'ebook' | 'mbti' | 'shortvideo';

interface TabOption {
  key: FilterTab
  label: string
}

const TAB_OPTIONS: TabOption[] = [
  { key: 'all',        label: '全部' },
  { key: 'roi8',       label: 'ROI > 8' },
  { key: 'roi7',       label: 'ROI > 7' },
  { key: 'ebook',      label: '电子书' },
  { key: 'mbti',       label: '人格测试' },
  { key: 'shortvideo', label: '短视频' },
];

function filterOpportunities(
  opps: OpportunityReport[],
  tab: FilterTab,
): OpportunityReport[] {
  switch (tab) {
    case 'roi8':
      return opps.filter((o) => o.roi_score > 8);
    case 'roi7':
      return opps.filter((o) => o.roi_score > 7);
    case 'ebook':
      return opps.filter((o) =>
        o.product_suggestions.some((p) =>
          p.type.toLowerCase().includes('ebook') ||
          p.type.toLowerCase().includes('电子书') ||
          p.title.toLowerCase().includes('电子书'),
        ),
      );
    case 'mbti':
      return opps.filter((o) =>
        o.topic.toLowerCase().includes('mbti') ||
        o.topic.toLowerCase().includes('人格') ||
        o.product_suggestions.some((p) =>
          p.type.toLowerCase().includes('mbti') ||
          p.type.toLowerCase().includes('人格') ||
          p.title.toLowerCase().includes('人格测试'),
        ),
      );
    case 'shortvideo':
      return opps.filter((o) =>
        o.product_suggestions.some((p) =>
          p.type.toLowerCase().includes('video') ||
          p.type.toLowerCase().includes('视频') ||
          p.title.toLowerCase().includes('短视频'),
        ),
      );
    default:
      return opps;
  }
}

// ---------- 扫描进度条组件 ----------
function ScanProgressBar({ job }: { job: TrendScanJob | null }) {
  if (!job) return null;

  const isRunning = job.status === 'queued' || job.status === 'running';
  const isFailed = job.status === 'failed';
  const isDone = job.status === 'done';

  return (
    <div
      className={`mt-4 rounded-xl border px-4 py-3 flex flex-wrap items-center gap-4 text-sm transition-all ${
        isFailed
          ? 'border-red-500/30 bg-red-500/10'
          : isDone
          ? 'border-emerald-500/30 bg-emerald-500/10'
          : 'border-indigo-500/30 bg-indigo-500/10'
      }`}
    >
      {isRunning && (
        <span className="inline-flex items-center gap-2 text-indigo-300 font-medium">
          <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-400" />
          扫描中…
        </span>
      )}
      {isDone && (
        <span className="text-emerald-400 font-semibold">✅ 扫描完成</span>
      )}
      {isFailed && (
        <span className="text-red-400 font-semibold">❌ 扫描失败</span>
      )}

      <span className="text-white/60">
        已抓取{' '}
        <span className="text-white font-bold">{job.scanned_count}</span> 条信号
      </span>
      <span className="text-white/60">
        已生成{' '}
        <span className="text-white font-bold">{job.opportunities_count}</span>{' '}
        条商机
      </span>

      {isFailed && job.error_msg && (
        <span className="text-red-300 text-xs">{job.error_msg}</span>
      )}
    </div>
  );
}

// ---------- 主页面 ----------
export default function OpportunitiesPage() {
  const [opportunities, setOpportunities] = useState<OpportunityReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scanMessage, setScanMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>('all');
  const [scanJob, setScanJob] = useState<TrendScanJob | null>(null);

  // 多源选择
  const [sources, setSources] = useState<Record<string, boolean>>(
    Object.fromEntries(SOURCE_OPTIONS.map((s) => [s.value, s.value === 'reddit'])),
  );

  // 轮询计时器 ref
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // 清理轮询
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // 启动轮询
  const startPolling = useCallback(
    (jobId: string) => {
      stopPolling();

      const poll = async () => {
        try {
          const res = await api.get<TrendScanJob>(`/trends/scan/${jobId}`);
          const job = res.data;
          setScanJob(job);

          if (job.status === 'done') {
            stopPolling();
            setScanning(false);
            setScanMessage(`扫描完成！共生成 ${job.opportunities_count} 条商机`);
            setLoading(true);
            fetchOpportunities();
          } else if (job.status === 'failed') {
            stopPolling();
            setScanning(false);
            setError(job.error_msg ?? '扫描任务失败');
          }
        } catch (err) {
          stopPolling();
          setScanning(false);
          setError(err instanceof Error ? err.message : '轮询扫描状态失败');
        }
      };

      // 立即执行一次，再每 3 秒
      poll();
      pollTimerRef.current = setInterval(poll, 3000);
    },
    [stopPolling, fetchOpportunities],
  );

  // 组件卸载时清理
  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  const handleScan = async (): Promise<void> => {
    setScanning(true);
    setScanMessage(null);
    setError(null);
    setScanJob(null);
    stopPolling();

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

      if (data.job_id) {
        // 异步任务模式 → 启动轮询
        setScanJob({
          job_id: data.job_id,
          status: (data.status as TrendScanJob['status']) ?? 'queued',
          sources: selectedSources,
          scanned_count: 0,
          opportunities_count: 0,
          error_msg: null,
          created_at: new Date().toISOString(),
        });
        startPolling(data.job_id);
      } else if (data.opportunities && data.opportunities.length > 0) {
        // 同步返回模式
        setScanMessage(data.message ?? '扫描完成');
        setOpportunities((prev) => {
          const existingIds = new Set(prev.map((o) => o.id));
          const newItems = data.opportunities!.filter(
            (o) => !existingIds.has(o.id),
          );
          return [...newItems, ...prev];
        });
        setScanning(false);
      } else {
        setScanMessage(data.message ?? '扫描已启动，稍后刷新查看结果');
        setTimeout(() => {
          setLoading(true);
          fetchOpportunities();
        }, 3000);
        setScanning(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '扫描失败，请重试');
      setScanning(false);
    }
  };

  const toggleSource = (source: string): void => {
    setSources((prev) => ({ ...prev, [source]: !prev[source] }));
  };

  const filteredOpportunities = filterOpportunities(opportunities, activeTab);

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

          {/* 多源选择 */}
          <div className="flex flex-wrap gap-3 mb-5">
            {SOURCE_OPTIONS.map((src) => (
              <label
                key={src.value}
                className={`flex items-center gap-2 cursor-pointer select-none px-3 py-1.5 rounded-lg border transition-colors ${
                  sources[src.value]
                    ? 'border-indigo-500 bg-indigo-500/20 text-white'
                    : 'border-white/10 bg-white/5 text-white/50 hover:border-white/30'
                }`}
              >
                <input
                  type="checkbox"
                  className="w-3.5 h-3.5 rounded accent-indigo-500 sr-only"
                  checked={sources[src.value] ?? false}
                  onChange={() => toggleSource(src.value)}
                />
                <span className="text-sm font-medium">
                  <span className="mr-1">{src.emoji}</span>
                  {src.label}
                </span>
              </label>
            ))}
          </div>

          {/* 操作按钮 */}
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

          {/* 扫描进度条 */}
          <ScanProgressBar job={scanJob} />
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
            {/* 分类 Tab 过滤 */}
            <div className="flex items-center gap-2 flex-wrap mb-5">
              {TAB_OPTIONS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors border ${
                    activeTab === tab.key
                      ? 'bg-indigo-600 border-indigo-500 text-white shadow shadow-indigo-900/40'
                      : 'border-white/10 bg-white/5 text-white/50 hover:border-white/30 hover:text-white/80'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-indigo-300">
                共发现{' '}
                <span className="text-white font-bold">
                  {filteredOpportunities.length}
                </span>{' '}
                个商机
                {activeTab !== 'all' && (
                  <span className="text-white/40 ml-1">
                    （共 {opportunities.length} 个）
                  </span>
                )}
              </p>
            </div>

            {filteredOpportunities.length === 0 ? (
              <div className="text-center py-20 text-indigo-300 text-sm">
                当前过滤条件下暂无商机，请切换其他分类或重新扫描
              </div>
            ) : (
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredOpportunities.map((opp) => (
                  <OpportunityCard key={opp.id} opportunity={opp} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
